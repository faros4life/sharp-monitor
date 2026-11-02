#!/usr/bin/env python3
"""
SLOW-HR LOGGER (Nov 2, 2026; Muse re-registration 10:36 ET: OddsPapi history replaces the live 5-minute poller).
Paper / measurement only. Leagues: NFL, NCAAF, NHL (NBA / NCAAB excluded). Floor: 2026-11-02 15:00 UTC.

From OddsPapi's free history, Pinnacle and Hard Rock tick series for each started game:
- At every Pinnacle tick before the start, Pinnacle's no-vig win chance for each side AT HARD ROCK'S LINE (Pinnacle's
  own line or its alt line of the same number) is compared with Hard Rock's price at that moment.
- STALE = Hard Rock's price is worth >= +2% against Pinnacle's no-vig chance, Hard Rock has not ticked since before the
  Pinnacle move that created the gap, and Pinnacle's chance for that side moved >= 1.5 points in the prior 15 minutes.
- SIGHTING = stale state that PERSISTS 3 minutes (still stale, Hard Rock unchanged) and is CONFIRMED 2-4 minutes after
  that (stale again at +5 min). One sighting per move (a new one needs the previous gap to close first).
- Type L if Pinnacle's main line (largest limit) changed number in the move window; Type P if only the price moved.
- LATE if the sighting is inside the final 30 minutes before start (own split).
- Grade: price CLV in cents of Hard Rock's stale price vs Pinnacle's no-vig close at that line ("consensus" proxy:
  Pinnacle only until a consensus close is wired; flagged in the report). W/L secondary, not wired in v1.
- Timestamps are OddsPapi capture times (createdAt), as Muse required. FEED-LAG (daily live sample of Hard Rock's
  bookmakerChangedAt) is not wired in v1: every report says so, and no day is excluded yet.
Billable: /fixtures per league, at most once per run, only when the shared cache lacks the games. Private email; state
encrypted (slowhr/state.enc). The log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import tracker_build as tb

ET = tb.ET
STATE = "slowhr/state.enc"
CACHE = "oddspapi/fixtures.json"
LEAGUES = ("NFL", "NCAAF", "NHL")
FLOOR = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
EV_MIN = 0.02
MOVE_PTS = 0.015
MOVE_WIN = timedelta(minutes=15)
PERSIST = timedelta(minutes=3)
CONFIRM = timedelta(minutes=5)
LATE = timedelta(minutes=30)
MAX_FIX = int(os.environ.get("SLOWHR_MAX_FIX", "") or "60")


def ticks(o):
    out = []
    for t in (o.get("players") or {}).get("0") or []:
        ct, pr = tb.tparse(t.get("createdAt")), tb.num(t.get("price"))
        if ct and pr and pr > 1:
            out.append((ct, pr, tb.num(t.get("limit"))))
    return sorted(out)


def at(series, when):
    """Last tick at or before that time (time, price, limit) or None."""
    best = None
    for x in series:
        if x[0] <= when:
            best = x
        else:
            break
    return best


def sightings(fid, f, lg, pin, hr, mkmap, start):
    sid = cl.SPORT[lg]
    out = []
    for mid, (s, typ, hcap, outs) in mkmap.items():
        if s != sid or mid not in hr or mid not in pin:
            continue
        names = {v: k for k, v in outs.items()}
        a_id, b_id = (names.get("1"), names.get("2")) if typ != "totals" else (names.get("Over"), names.get("Under"))
        if not a_id or not b_id:
            continue
        P = {oid: ticks((pin[mid].get("outcomes") or {}).get(oid) or {}) for oid in (a_id, b_id)}
        H = {oid: ticks((hr[mid].get("outcomes") or {}).get(oid) or {}) for oid in (a_id, b_id)}
        if not all(P.values()) or not any(H.values()):
            continue
        times = sorted({x[0] for v in P.values() for x in v if FLOOR <= x[0] <= start})

        def fair(oid, when):
            pa, pb = at(P[a_id], when), at(P[b_id], when)
            if not pa or not pb:
                return None
            ia, ib = 1 / pa[1], 1 / pb[1]
            p = ia / (ia + ib)
            return p if oid == a_id else 1 - p

        def stale(oid, when, since):
            p, h = fair(oid, when), at(H[oid], when)
            if p is None or not h or h[0] > since:   # Hard Rock ticked after the move: not stale
                return None
            ev = p * h[1] - 1
            return (ev, p, h) if ev >= EV_MIN else None

        for oid in (a_id, b_id):
            open_until = None
            for t in times:
                if open_until and t <= open_until:
                    continue
                p_now, p_then = fair(oid, t), fair(oid, t - MOVE_WIN)
                if p_now is None or p_then is None or p_now - p_then < MOVE_PTS:
                    continue
                s0 = stale(oid, t, t - MOVE_WIN)
                if not s0:
                    continue
                s1 = stale(oid, t + PERSIST, t - MOVE_WIN)
                s2 = stale(oid, t + CONFIRM, t - MOVE_WIN)
                if not (s1 and s2) or t + CONFIRM > start:
                    continue
                ev, p, h = s2
                # close: Pinnacle no-vig at this line, last ticks before start
                pc = fair(oid, start)
                def main_line(when):
                    best = None
                    for k, (s_, ty_, hc_, o_) in mkmap.items():
                        if s_ != sid or ty_ != typ or k not in pin:
                            continue
                        x = at(ticks((pin[k].get("outcomes") or {}).get(next(iter(o_))) or {}), when)
                        if x and (best is None or (x[2] or 0) > best[1]):
                            best = (hc_, x[2] or 0)
                    return best[0] if best else None
                main_then, main_now = main_line(t - MOVE_WIN), main_line(t)
                kind = "L" if (typ != "moneyline" and main_then is not None and main_now is not None and main_then != main_now) else "P"
                side = outs.get(oid)
                rec = {"fixture": fid, "league": lg, "game": f"{f.get('participant1Name')} vs {f.get('participant2Name')}",
                       "start": cl.iso(start), "type": typ, "line": hcap, "side": side,
                       "team": (f.get("participant1Name") if side == "1" else f.get("participant2Name")) if side in ("1", "2") else side,
                       "kind": kind, "t_move": cl.iso(t), "t_confirm": cl.iso(t + CONFIRM),
                       "mins_before": round((start - t - CONFIRM).total_seconds() / 60),
                       "late": (start - (t + CONFIRM)) < LATE, "hr_price": h[1], "hr_am": cl.dec_to_am(h[1]),
                       "hr_tick": cl.iso(h[0]), "pin_fair": round(p, 4), "ev_pct": round(100 * ev, 2),
                       "pin_move_pts": round(100 * (p_now - p_then), 2), "hr_limit": h[2],
                       "close_fair": round(pc, 4) if pc is not None else None}
                if pc is not None:
                    rec["clv_cents"] = round(100 * (pc - 1 / h[1]), 2)
                out.append(rec)
                # one per move: skip until Hard Rock catches up (ticks) or the gap closes
                nxt = [x[0] for x in H[oid] if x[0] > h[0]]
                open_until = min(nxt) if nxt else start
    return out


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY or not tb.PASS:
        print("SLOW-HR: ODDSPAPI_KEY or TRACKER_PASSPHRASE not set; skipped")
        return
    try:
        st = tb.dec(json.load(open(STATE)))
    except Exception:
        st = {}
    st.setdefault("done", {})
    st.setdefault("sightings", [])
    try:
        cache = json.load(open(CACHE))
    except Exception:
        cache = {}
    cst = {"fixtures": cache.get("fixtures") or {}, "fx_last": {}, "billable": {}}
    mkmap = cl.load_markets(cst, now)
    lo, hi = (now - timedelta(days=2)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET)
    for lg in LEAGUES:
        have = [k for k, v in cst["fixtures"].items() if v.get("lg") == lg and tb.tparse(v.get("start"))
                and now - timedelta(hours=40) <= tb.tparse(v["start"]) <= now]
        if not have:
            cl.refresh_fixtures(cst, now, lg, lo, hi)
    todo = []
    for fid, f in cst["fixtures"].items():
        s = tb.tparse(f.get("start"))
        if f.get("lg") in LEAGUES and s and max(FLOOR, now - timedelta(hours=40)) <= s <= now - timedelta(minutes=5) and fid not in st["done"]:
            todo.append((s, fid, f))
    todo.sort()
    new = []
    for s, fid, f in todo[:MAX_FIX]:
        hp = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
        hh = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="hardrockbet")
        if any(isinstance(h, dict) and h.get("_error") for h in (hp, hh)):
            continue
        f2 = {"participant1Name": f.get("n1"), "participant2Name": f.get("n2")}
        new += sightings(fid, f2, f["lg"], cl.book_markets(hp, "pinnacle"), cl.book_markets(hh, "hardrockbet"), mkmap, s)
        st["done"][fid] = cl.iso(now)
    st["sightings"] += new
    S = st["sightings"]
    today = now.astimezone(ET).strftime("%Y-%m-%d")

    def stats(xs):
        c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
        return (f"n {len(xs)}, with close {len(c)}" + (f", avg CLV {sum(c) / len(c):+.2f}c, beat close {sum(1 for v in c if v > 0)}/{len(c)}" if c else ""))

    L = ["SLOW-HR LOGGER (paper; OddsPapi history; Pinnacle vs Hard Rock; NFL / NCAAF / NHL; floor 2026-11-02 15:00 UTC)",
         "Times are OddsPapi capture times (createdAt). Close = Pinnacle no-vig at the same line (consensus close not wired yet).",
         "FEED-LAG sampling not wired in v1: no day excluded yet.", "",
         f"This run: {len(todo[:MAX_FIX])} games read, sightings +{len(new)}.",
         f"All sightings: {stats(S)}",
         f"  judged (not LATE): {stats([x for x in S if not x['late']])}",
         f"  LATE (final 30 min): {stats([x for x in S if x['late']])}",
         f"  Type L: {stats([x for x in S if x['kind'] == 'L'])} | Type P: {stats([x for x in S if x['kind'] == 'P'])}"]
    for lg in LEAGUES:
        L.append(f"  {lg}: {stats([x for x in S if x['league'] == lg])}")
    L += ["", "NEWEST 20 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-20:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {x['league']} {x['game']} | {x['type']} {x['team']} {x['line']} | HR {x['hr_am']:+d} vs Pinnacle fair "
                 f"{tb.p_to_american(x['pin_fair'])} (EV {x['ev_pct']:+.1f}%, Pinnacle moved {x['pin_move_pts']:+.1f} pts) | Type {x['kind']}"
                 f"{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start" + (f" | CLV {x['clv_cents']:+.2f}c" if x.get('clv_cents') is not None else ""))
    if new or os.environ.get("EMAIL_NOW") == "1" or st.get("emailed") != today:
        ex.send(f"Bets SLOW-HR LOG {today}", "\n".join(L))
        st["emailed"] = today
    os.makedirs("slowhr", exist_ok=True)
    cut = cl.iso(now - timedelta(days=120))
    st["done"] = {k: v for k, v in st["done"].items() if v >= cut}
    json.dump(tb.enc(st), open(STATE, "w"))
    print(f"SLOW-HR: games {len(todo[:MAX_FIX])}, sightings +{len(new)} (total {len(S)}), calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
