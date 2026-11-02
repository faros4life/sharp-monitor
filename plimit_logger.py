#!/usr/bin/env python3
"""
PLIMIT LOGGER (Nov 2, 2026; Muse registration accepted 10:28 ET, amended to P + B at 10:36, Q2 props at 10:33).
Paper / measurement only: nothing here places, sizes or blocks a bet.

Source: OddsPapi free /v4/historical-odds, read once a day for games that have started (the whole pre-game tick series
is there, so nothing is polled live). Books: Pinnacle (P) and BookMaker.eu (B), each its own split.
Every record keeps the RAW limit and the IMPLIED BASE = raw limit x (decimal price - 1), as registered, plus the
OddsJam scale factor seen on Nov 2 (OddsJam limit = OddsPapi limit x 4/3 on all six markets checked); absolute tests
are left to the report so the scale ruling can be applied either way.

Q1 (main markets: full-game moneyline, spreads, totals incl. overtime): an EVENT is the first tick where an outcome's
implied base has moved >= 25% from that outcome's FIRST SNAPSHOT OF THE GAME'S ET DAY (CUT down, RAISE up; Muse 11:35). One record per fixture / book / bet type /
side / tick time (the line with the largest pre-move limit stands for the cluster, since Pinnacle moves every line).
Q2 (player props, Pinnacle only): implied base vs the prop's FIRST snapshot of the ET day; MINOR cut 25-39%, MAJOR
>= 40%; PERSISTENT = the reduced base holds on ticks spanning >= 10 min; TIMING = confirmed >= 2 h before start (later:
LATE); SIZE = pre-cut base >= $100 (raw OddsPapi dollars; x4/3 on OddsJam's scale); first qualifying cut per player +
market per ET day. Play = the cut side. Gate metric = price CLV (cents) of the cut-time price vs Pinnacle's no-vig close
on that prop (both sides' last tick before start at the same line).

Billable calls: /fixtures once per league per run (NBA, NFL, NHL, NCAAF). State encrypted (plimit/state.enc, the
tracker's scheme). Private email; the Actions log prints counts only.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import executor as ex
import tracker_build as tb

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
STATE = "plimit/state.enc"
ET = tb.ET
LEAGUES = {"NBA": (132, 11), "NFL": (31, 14), "NHL": (234, 15)}
BOOKS = ("pinnacle", "bookmaker.eu")
MAIN_TYPES = ("moneyline", "spreads", "totals")
MOVE = 0.25
OJ_SCALE = 4 / 3
MAX_FIX = int(os.environ.get("PLIMIT_MAX_FIX", "") or "40")
CALLS = []


def api(path, **params):
    params["apiKey"] = KEY
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"Accept": "application/json", "User-Agent": "sharp-monitor-plimit"})
    time.sleep(8.0 if path == "/historical-odds" else 1.1)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                CALLS.append((path, r.status))
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(20)
                continue
            CALLS.append((path, e.code))
            return {"_error": e.code, "_body": e.read().decode()[:200]}
        except Exception as e:
            CALLS.append((path, type(e).__name__))
            return {"_error": type(e).__name__, "_body": str(e)[:200]}


def tp(x):
    return tb.tparse(x)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def am(d):
    d = float(d)
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def ncaaf_tid(st):
    if st.get("ncaaf_tid"):
        return st["ncaaf_tid"]
    ts = api("/tournaments", sportId=14)
    best = None
    for t in ts if isinstance(ts, list) else []:
        nm = (t.get("tournamentName") or "").lower()
        if ("ncaa" in nm or "college" in nm) and "usa" in (t.get("categorySlug") or "").lower():
            n = (t.get("upcomingFixtures") or 0) + (t.get("futureFixtures") or 0)
            if not best or n > best[0]:
                best = (n, t.get("tournamentId"))
    if best and best[0] > 0:
        st["ncaaf_tid"] = best[1]
    return st.get("ncaaf_tid")


def series(o, start):
    """Pre-start ticks of one outcome (player key '0'), time-ordered: [(time, price, limit, base)]."""
    out = []
    for t in (o.get("players") or {}).get("0") or []:
        ct, pr, lim = tp(t.get("createdAt")), tb.num(t.get("price")), tb.num(t.get("limit"))
        if ct and pr and pr > 1 and lim is not None and ct <= start:
            out.append((ct, pr, lim, lim * (pr - 1)))
    return sorted(out)


def close_two_way(m, start):
    """{outcome_id: no-vig close prob} from both sides' last pre-start tick."""
    last = {}
    for oid, o in (m.get("outcomes") or {}).items():
        s = series(o, start)
        if s:
            last[oid] = s[-1][1]
    if len(last) != 2:
        return {}
    inv = {k: 1 / v for k, v in last.items()}
    tot = sum(inv.values())
    return {k: v / tot for k, v in inv.items()}


def q1_events(fid, fx, lg, bk, pm, meta, start):
    """CUT / RAISE events on main markets: one record per (type, side, tick time) cluster."""
    clusters = {}
    for mid, m in pm.items():
        md = meta.get(str(mid))
        if not md or md.get("period") != "result" or md.get("marketType") not in MAIN_TYPES or md.get("playerProp"):
            continue
        names = {str(x["outcomeId"]): x.get("outcomeName") for x in md.get("outcomes") or []}
        close = close_two_way(m, start)
        for oid, o in (m.get("outcomes") or {}).items():
            s = series(o, start)
            if not s:
                continue
            # Muse 11:35 ruling: the reference is the outcome's FIRST SNAPSHOT OF THE ET DAY (game day), not the previous tick
            ref = next((x for x in s if x[0].astimezone(ET).date() == start.astimezone(ET).date()), s[0])
            t0, p0, l0, b0 = ref
            if b0 <= 0:
                continue
            fired = set()
            for (t1, p1, l1, b1) in s:
                if t1 <= t0:
                    continue
                ch = b1 / b0 - 1
                if abs(ch) < MOVE or (ch < 0) in fired:
                    continue
                fired.add(ch < 0)   # first CUT and first RAISE from the reference, per outcome
                side = names.get(oid, oid)
                k = (md["marketType"], side, "CUT" if ch < 0 else "RAISE", iso(t1))
                rec = {"fixture": fid, "league": lg, "game": f"{fx.get('participant1Name')} vs {fx.get('participant2Name')}",
                       "start": iso(start), "book": "P" if bk == "pinnacle" else "B", "type": md["marketType"],
                       "side": side, "team": (fx.get("participant1Name") if side == "1" else fx.get("participant2Name")) if side in ("1", "2") else side,
                       "line": md.get("handicap"), "event": "CUT" if ch < 0 else "RAISE", "move_pct": round(100 * ch, 1),
                       "t": iso(t1), "mins_before": round((start - t1).total_seconds() / 60),
                       "limit_before": l0, "limit_after": l1, "base_before": round(b0, 1), "base_after": round(b1, 1),
                       "price_after": p1, "am_after": am(p1),
                       "close_fair": round(close[oid], 4) if oid in close else None}
                if rec["close_fair"] is not None:
                    rec["clv_cents_after"] = round(100 * (rec["close_fair"] - 1 / p1), 2)   # + = the price beat the close
                old = clusters.get(k)
                if not old or l0 > old["limit_before"]:
                    clusters[k] = rec
    return list(clusters.values())


def q2_events(fid, fx, lg, pm, meta, start):
    """Player-prop limit cuts vs the prop's first snapshot of the ET day (Pinnacle only)."""
    out, seen = [], set()
    for mid, m in pm.items():
        md = meta.get(str(mid))
        if not md or not (md.get("playerProp") or "player" in str(md.get("marketType"))):
            continue
        names = {str(x["outcomeId"]): x.get("outcomeName") for x in md.get("outcomes") or []}
        # per player: both sides' series at this line, for the close
        byp = {}
        for oid, o in (m.get("outcomes") or {}).items():
            for pid, ticks in (o.get("players") or {}).items():
                byp.setdefault(pid, {})[oid] = ticks
        for pid, sides in byp.items():
            ser = {}
            for oid, ticks in sides.items():
                s = []
                for t in ticks if isinstance(ticks, list) else []:
                    ct, pr, lim = tp(t.get("createdAt")), tb.num(t.get("price")), tb.num(t.get("limit"))
                    if ct and pr and pr > 1 and lim is not None and ct <= start:
                        s.append((ct, pr, lim, lim * (pr - 1)))
                ser[oid] = sorted(s)
            close = {}
            if len(ser) == 2 and all(ser.values()):
                inv = {k: 1 / v[-1][1] for k, v in ser.items()}
                close = {k: v / sum(inv.values()) for k, v in inv.items()}
            for oid, s in ser.items():
                if not s:
                    continue
                day0 = s[0][0].astimezone(ET).date()
                first = next((x for x in s if x[0].astimezone(ET).date() == start.astimezone(ET).date()), s[0])
                b_first = first[3]
                if b_first <= 0:
                    continue
                for i, (ct, pr, lim, b) in enumerate(s):
                    if ct <= first[0]:
                        continue
                    cut = 1 - b / b_first
                    if cut < MOVE:
                        continue
                    band = "MAJOR" if cut >= 0.40 else "MINOR"
                    later = [x for x in s[i:] if x[0] >= ct]
                    held = [x for x in later if x[3] <= b * 1.0001 + 1e-9 or 1 - x[3] / b_first >= MOVE]
                    span = (held[-1][0] - ct).total_seconds() / 60 if held else 0
                    persistent = len(held) >= 2 and span >= 10 and all(1 - x[3] / b_first >= MOVE for x in held[:2])
                    conf = held[1][0] if len(held) >= 2 else None
                    mins_before = round((start - (conf or ct)).total_seconds() / 60)
                    key = (pid, md.get("marketType"), str(day0))
                    first_of_day = key not in seen
                    seen.add(key)
                    judged = (band == "MAJOR" and persistent and mins_before >= 120 and b_first * OJ_SCALE >= 100 and first_of_day)   # floor in OddsJam dollars (Muse 11:35)
                    rec = {"fixture": fid, "league": lg, "game": f"{fx.get('participant1Name')} vs {fx.get('participant2Name')}",
                           "start": iso(start), "type": md.get("marketType"), "player_id": pid, "line": md.get("handicap"),
                           "side": names.get(oid, oid), "band": band, "cut_pct": round(100 * cut, 1), "t": iso(ct),
                           "confirmed_t": iso(conf), "mins_before": mins_before, "persistent": persistent,
                           "late": mins_before < 120, "base_first": round(b_first, 1), "base_cut": round(b, 1),
                           "limit_first": first[2], "limit_cut": lim, "price_cut": pr, "am_cut": am(pr),
                           "first_of_day": first_of_day, "judged": judged,
                           "close_fair": round(close[oid], 4) if oid in close else None}
                    if rec["close_fair"] is not None:
                        rec["clv_cents"] = round(100 * (rec["close_fair"] - 1 / pr), 2)
                    out.append(rec)
                    break   # one record per prop side per day (the first cut); persistence judged from there
    return out


def main():
    now = datetime.now(timezone.utc)
    if not KEY or not tb.PASS:
        print("PLIMIT logger: ODDSPAPI_KEY or TRACKER_PASSPHRASE not set; skipped")
        return
    try:
        st = tb.dec(json.load(open(STATE)))
    except Exception:
        st = {}
    if st.get("v") != 2:   # v2 (Muse 11:35): Q1 reference = first snapshot of the ET day; Q2 floor in OddsJam dollars -> re-derive
        st = {"v": 2, "billable": st.get("billable") or {}, "ncaaf_tid": st.get("ncaaf_tid")}
    st.setdefault("done", {})
    st.setdefault("q1", [])
    st.setdefault("q2", [])
    st.setdefault("billable", {})
    mk = api("/markets")
    st["billable"][now.strftime("%Y-%m")] = st["billable"].get(now.strftime("%Y-%m"), 0) + 1
    meta = {str(m["marketId"]): m for m in (mk if isinstance(mk, list) else [])}
    leagues = dict(LEAGUES)
    tid = ncaaf_tid(st)
    if tid:
        leagues["NCAAF"] = (tid, 14)
    lo, hi = (now - timedelta(days=2)).strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d")
    todo = []
    for lg, (t, sid) in leagues.items():
        fx = api("/fixtures", tournamentId=t, **{"from": lo, "to": hi})
        st["billable"][now.strftime("%Y-%m")] += 1
        for f in fx if isinstance(fx, list) else []:
            s = tp(f.get("startTime"))
            if f.get("fixtureId") and s and now - timedelta(hours=60) <= s <= now - timedelta(minutes=5) and f["fixtureId"] not in st["done"]:
                todo.append((s, lg, f))
    todo.sort(key=lambda x: x[0])
    n1 = n2 = nf = 0
    for s, lg, f in todo[:MAX_FIX]:
        fid = f["fixtureId"]
        for bk in BOOKS:
            h = api("/historical-odds", fixtureId=fid, bookmakers=bk)
            if isinstance(h, dict) and h.get("_error"):
                continue
            pm = ((h.get("bookmakers") or {}).get(bk) or {}).get("markets") or {}
            ev = q1_events(fid, f, lg, bk, pm, meta, s)
            st["q1"] += ev
            n1 += len(ev)
            if bk == "pinnacle" and lg in ("NBA", "NFL"):
                e2 = q2_events(fid, f, lg, pm, meta, s)
                st["q2"] += e2
                n2 += len(e2)
        st["done"][fid] = iso(now)
        nf += 1
    # report
    today = now.astimezone(ET).strftime("%Y-%m-%d")
    q1, q2 = st["q1"], st["q2"]
    L = ["PLIMIT LOGGER (paper; OddsPapi history; Pinnacle = P, BookMaker.eu = B). Raw limits and implied base logged;",
         f"OddsJam scale = OddsPapi x {OJ_SCALE:.4f} (Nov 2 identity check, 6/6 markets).", "",
         f"This run: {nf} games read ({len(todo)} started in the window; cap {MAX_FIX}), Q1 events +{n1}, Q2 prop records +{n2}.",
         f"Q1 to date: {len(q1)} events (CUT {sum(1 for e in q1 if e['event'] == 'CUT')}, RAISE {sum(1 for e in q1 if e['event'] == 'RAISE')}); "
         f"P {sum(1 for e in q1 if e['book'] == 'P')}, B {sum(1 for e in q1 if e['book'] == 'B')}. Readout at 100 CUT events (registered)."]
    cuts = [e for e in q1 if e["event"] == "CUT" and e.get("clv_cents_after") is not None]
    for b in ("P", "B"):
        c = [e for e in cuts if e["book"] == b]
        if c:
            L.append(f"  {b} CUTs with a close: {len(c)}, cut side's post-cut price vs close: avg {sum(e['clv_cents_after'] for e in c) / len(c):+.2f}c, "
                     f"beat close {sum(1 for e in c if e['clv_cents_after'] > 0)}/{len(c)}")
    j = [e for e in q2 if e["judged"]]
    L.append(f"Q2 props to date: {len(q2)} cut records (MAJOR {sum(1 for e in q2 if e['band'] == 'MAJOR')}, MINOR {sum(1 for e in q2 if e['band'] == 'MINOR')}), "
             f"JUDGED {len(j)} (interim at 25, verdict at 50).")
    jc = [e for e in j if e.get("clv_cents") is not None]
    if jc:
        L.append(f"  judged with a close: {len(jc)}, avg CLV {sum(e['clv_cents'] for e in jc) / len(jc):+.2f}c, beat close {sum(1 for e in jc if e['clv_cents'] > 0)}/{len(jc)}")
    L += ["", "LATEST Q1 EVENTS (newest 15):"]
    for e in sorted(q1, key=lambda e: e["t"])[-15:][::-1]:
        L.append(f"  {e['league']} {e['game']} | {e['book']} {e['type']} {e['team']} {e['line']} | {e['event']} {e['move_pct']:+.0f}% "
                 f"base {e['base_before']}->{e['base_after']} (limit {e['limit_before']:g}->{e['limit_after']:g}) | {e['mins_before']} min pre-start | "
                 f"price {e['am_after']:+d}" + (f", vs close {e['clv_cents_after']:+.2f}c" if e.get('clv_cents_after') is not None else ""))
    L += ["", "LATEST Q2 JUDGED (newest 10):"]
    for e in sorted(j, key=lambda e: e["t"])[-10:][::-1]:
        L.append(f"  {e['league']} {e['game']} | {e['type']} player {e['player_id']} {e['side']} {e['line']} | cut {e['cut_pct']:.0f}% "
                 f"base {e['base_first']}->{e['base_cut']} | {e['mins_before']} min pre-start | {e['am_cut']:+d}"
                 + (f", CLV {e['clv_cents']:+.2f}c" if e.get('clv_cents') is not None else ""))
    L += ["", f"OddsPapi calls this run: {len(CALLS)} ({sum(1 for p, _ in CALLS if p != '/historical-odds')} billable); billable this month "
              f"{st['billable'].get(now.strftime('%Y-%m'), 0)}."]
    if os.environ.get("EMAIL_NOW") == "1" or st.get("emailed") != today:
        ex.send(f"Bets PLIMIT LOG {today}", "\n".join(L))
        st["emailed"] = today
    cut = iso(now - timedelta(days=120))
    st["done"] = {k: v for k, v in st["done"].items() if v >= cut}
    os.makedirs("plimit", exist_ok=True)
    json.dump(tb.enc(st), open(STATE, "w"))
    print(f"PLIMIT logger: games {nf}, q1 +{n1} (total {len(q1)}), q2 +{n2} (total {len(q2)}), calls {len(CALLS)}")   # counts only


if __name__ == "__main__":
    main()
