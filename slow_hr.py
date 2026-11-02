#!/usr/bin/env python3
"""
SLOW-HR LOGGER (Nov 2, 2026; Muse re-registration 10:36 ET: OddsPapi history replaces the live 5-minute poller).
Paper / measurement only. Leagues: NFL, NCAAF, NHL (NBA / NCAAB excluded). Floor: 2026-11-02 15:00 UTC.

From OddsPapi's free history, Pinnacle and Hard Rock tick series for each started game. REGISTERED TEST (Muse 10:36,
corrected 12:19 - the sighting definition IS the test):
- Type L = Pinnacle's main line (largest limit) moves >= 0.5 points while Hard Rock still shows the old line.
- Type P = same line, Pinnacle's price moves >= 8 cents (within 15 minutes) while Hard Rock sits within 2 cents of its
  pre-move price.
- Persistence >= 3 minutes, plus a confirmation read 2 minutes later (+5 min). One sighting per move.
- LATE if confirmed inside the final 30 minutes before start (own split).
- DEVIATION (accepted by Muse for v1): grade = price CLV in cents of Hard Rock's price vs Pinnacle's no-vig close at that
  line (Pinnacle as the consensus proxy until a consensus close is wired). W/L not wired.
- DEVIATION (accepted by Muse for v1): FEED-LAG sampling (Hard Rock bookmakerChangedAt) not wired: no day excluded yet.
- Timestamps are OddsPapi capture times (createdAt), as Muse required.
Billable: /fixtures per league, at most once per run, only when the shared cache lacks the games. Private email; state
encrypted (slowhr/state.enc). The log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import hist_cache as hc
import sharp_monitor as sm
import tracker_build as tb

ET = tb.ET
STATE = "slowhr/state.enc"
CACHE = "oddspapi/fixtures.json"
LEAGUES = ("NFL", "NCAAF", "NHL")
FLOOR = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
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


def cents(dec):
    """Decimal price on the American 'cents' scale (-110 -> -10, +110 -> +10), so -105 to +105 is 10 cents."""
    am = cl.dec_to_am(dec)
    return am + 100 if am < 0 else am - 100


def sightings(fid, f, lg, pin, hr, mkmap, start):
    """Registered test (Muse 10:36 / 12:19). Type L: Pinnacle's main line moves >= 0.5 while Hard Rock still shows the
    old line. Type P: same line, Pinnacle's price moves >= 8 cents while Hard Rock sits within 2 cents of its pre-move
    price. Both must persist 3 minutes and hold again at a confirmation read 2 minutes later (+5 min)."""
    sid = cl.SPORT[lg]
    out = []
    by_type, memo = {}, {}
    for mid, (s, typ, hcap, outs) in mkmap.items():
        if s == sid and (mid in pin or mid in hr):
            by_type.setdefault(typ, []).append((mid, hcap, outs))

    def two(book, mid, outs, typ, when):
        names = {v: k for k, v in outs.items()}
        a, b = (names.get("Over"), names.get("Under")) if typ == "totals" else (names.get("1"), names.get("2"))
        if mid not in book or not a or not b:
            return None
        P = {}
        for o in (a, b):
            k = (id(book), mid, o)
            if k not in memo:
                memo[k] = ticks((book[mid].get("outcomes") or {}).get(o) or {})
            P[o] = at(memo[k], when)
        if not all(P.values()) or when - min(x[0] for x in P.values()) > timedelta(hours=24):
            return None
        return {"a": a, "b": b, "pa": P[a], "pb": P[b]}

    def main_of(book, typ, when, by_limit=True):
        best = None
        for mid, hcap, outs in by_type.get(typ, []):
            t = two(book, mid, outs, typ, when)
            if not t:
                continue
            key = ((t["pa"][2] or 0) if by_limit else 0, -abs(1 / t["pa"][1] - 1 / t["pb"][1]))
            if best is None or key > best[0]:
                best = (key, mid, hcap, outs, t)
        return best[1:] if best else None

    def fair(side_name, typ, line, when):
        """Pinnacle no-vig chance for a side at a number: own market, else main line moved by half-point values."""
        for mid, hcap, outs in by_type.get(typ, []):
            if (line is None and typ == "moneyline") or (line is not None and abs(hcap - line) < 1e-9):
                t = two(pin, mid, outs, typ, when)
                if t:
                    ia, ib = 1 / t["pa"][1], 1 / t["pb"][1]
                    p = ia / (ia + ib)
                    return p if side_name in ("Over", "1") else 1 - p
        if typ == "moneyline" or (typ == "spreads" and lg == "NHL"):
            return None
        m = main_of(pin, typ, when)
        if not m:
            return None
        _, ml, _, t = m
        ia, ib = 1 / t["pa"][1], 1 / t["pb"][1]
        p = ia / (ia + ib)
        p = p if side_name in ("Over", "1") else 1 - p
        if typ == "totals":
            v = sm.half_point_value(lg, "tot", ml, line, ml)
            better = (line < ml) if side_name == "Over" else (line > ml)
        else:
            mine, want = (ml, line) if side_name == "1" else (-ml, -line)
            v = sm.half_point_value(lg, "spr", mine, want, mine)
            better = want > mine
        return min(max(p + (v if better else -v), .01), .99)

    times = set()
    for b in (pin,):
        for m in b.values():
            for o in (m.get("outcomes") or {}).values():
                for x in (o.get("players") or {}).get("0") or []:
                    c = tb.tparse(x.get("createdAt"))
                    if c and FLOOR <= c <= start:
                        times.add(c)
    times = sorted(times)
    last_key = {}

    def record(kind, typ, line, side_name, hr_dec, hr_tick, t, detail):
        team = (f.get("participant1Name") if side_name == "1" else f.get("participant2Name")) if side_name in ("1", "2") else side_name
        pf = fair(side_name, typ, line, t + CONFIRM)
        pc = fair(side_name, typ, line, start)
        rec = {"fixture": fid, "league": lg, "game": f"{f.get('participant1Name')} vs {f.get('participant2Name')}",
               "start": cl.iso(start), "type": typ, "line": line, "side": side_name, "team": team, "kind": kind,
               "t_move": cl.iso(t), "t_confirm": cl.iso(t + CONFIRM),
               "mins_before": round((start - t - CONFIRM).total_seconds() / 60), "late": (start - (t + CONFIRM)) < LATE,
               "hr_price": hr_dec, "hr_am": cl.dec_to_am(hr_dec), "hr_tick": cl.iso(hr_tick), "detail": detail,
               "pin_fair": round(pf, 4) if pf is not None else None,
               "ev_pct": round(100 * (pf * hr_dec - 1), 2) if pf is not None else None,
               "close_fair": round(pc, 4) if pc is not None else None}
        if pc is not None:
            rec["clv_cents"] = round(100 * (pc - 1 / hr_dec), 2)
        out.append(rec)

    for t in times:
        if t + CONFIRM > start:
            break
        # ---- Type L (spreads / totals): Pinnacle's main number moves >= 0.5; Hard Rock still on the old number
        for typ in ("spreads", "totals"):
            before = main_of(pin, typ, t - timedelta(seconds=1))
            now_ = main_of(pin, typ, t)
            if not before or not now_ or abs(now_[1] - before[1]) < 0.5:
                continue
            old, new = before[1], now_[1]
            if last_key.get(("L", typ)) == (old, new):
                continue

            def held(when):
                p_ = main_of(pin, typ, when)
                h_ = main_of(hr, typ, when, by_limit=False)
                return p_ and h_ and abs(p_[1] - old) >= 0.5 and (p_[1] - old) * (new - old) > 0 and abs(h_[1] - old) < 1e-9 and h_
            h0 = held(t)
            if not (h0 and held(t + PERSIST) and held(t + CONFIRM)):
                continue
            last_key[("L", typ)] = (old, new)
            if typ == "totals":
                side_name = "Over" if new > old else "Under"
            else:
                side_name = "1" if new < old else "2"
            hv = h0[3]
            pick = hv["pa"] if side_name in ("Over", "1") else hv["pb"]
            record("L", typ, old, side_name, pick[1], pick[0], t, f"Pinnacle {old:g} -> {new:g}; Hard Rock still {old:g}")
        # ---- Type P (all markets): same number, Pinnacle price moves >= 8 cents; Hard Rock within 2 cents of pre-move
        for typ, lst in by_type.items():
            for mid, hcap, outs in lst:
                if typ != "moneyline":
                    m_ = main_of(pin, typ, t)
                    if not m_ or m_[0] != mid:
                        continue
                p0, p1 = two(pin, mid, outs, typ, t - MOVE_WIN), two(pin, mid, outs, typ, t)
                h_pre = two(hr, mid, outs, typ, t - MOVE_WIN)
                if not p0 or not p1 or not h_pre:
                    continue
                for leg, side_name in (("pa", "Over" if typ == "totals" else "1"), ("pb", "Under" if typ == "totals" else "2")):
                    if p1[leg][0] != t:
                        continue
                    mv = cents(p0[leg][1]) - cents(p1[leg][1])   # positive = Pinnacle shortened this side
                    if mv < 8 or last_key.get(("P", mid, leg)) == round(p0[leg][1], 3):
                        continue
                    base = cents(h_pre[leg][1])

                    def heldp(when):
                        pp, hh = two(pin, mid, outs, typ, when), two(hr, mid, outs, typ, when)
                        return pp and hh and cents(p0[leg][1]) - cents(pp[leg][1]) >= 8 and abs(cents(hh[leg][1]) - base) <= 2 and hh
                    h0 = heldp(t)
                    if not (h0 and heldp(t + PERSIST) and heldp(t + CONFIRM)):
                        continue
                    last_key[("P", mid, leg)] = round(p0[leg][1], 3)
                    record("P", typ, hcap if typ != "moneyline" else None, side_name, h0[leg][1], h0[leg][0], t,
                           f"Pinnacle {cl.dec_to_am(p0[leg][1]):+d} -> {cl.dec_to_am(p1[leg][1]):+d} ({mv:g}c); Hard Rock {cl.dec_to_am(h0[leg][1]):+d}")
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
    if st.get("v") != "reg2":   # 12:19 correction: re-derive everything under the registered test
        st = {"v": "reg2"}
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
        hp = hh = hc.get_hist(fid, ["pinnacle", "hardrockbet"], s)   # shared history cache
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
         "Registered test: L = Pinnacle main line moves >= 0.5 while Hard Rock shows the old line; P = same line, Pinnacle price",
         "moves >= 8c while Hard Rock is within 2c of its pre-move price; persists 3 min + confirmation read at +5 min.",
         "DEVIATION: grade = CLV vs Pinnacle no-vig close at that line (consensus close not wired yet).",
         "DEVIATION: FEED-LAG sampling not wired: no day excluded yet. Times are OddsPapi capture times (createdAt).", "",
         f"This run: {len(todo[:MAX_FIX])} games read, sightings +{len(new)}.",
         f"All sightings: {stats(S)}",
         f"  judged (not LATE): {stats([x for x in S if not x['late']])}",
         f"  LATE (final 30 min): {stats([x for x in S if x['late']])}",
         f"  Type L: {stats([x for x in S if x['kind'] == 'L'])} | Type P: {stats([x for x in S if x['kind'] == 'P'])}"]
    for lg in LEAGUES:
        L.append(f"  {lg}: {stats([x for x in S if x['league'] == lg])}")
    L += ["", "NEWEST 20 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-20:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {x['league']} {x['game']} | {x['type']} {x['team']} {x['line'] if x['line'] is not None else ''} | "
                 f"HR {x['hr_am']:+d} | {x['detail']} | Type {x['kind']}{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start"
                 + (f" | EV {x['ev_pct']:+.1f}%" if x.get('ev_pct') is not None else "")
                 + (f" | CLV {x['clv_cents']:+.2f}c" if x.get('clv_cents') is not None else ""))
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
