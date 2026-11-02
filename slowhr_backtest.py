#!/usr/bin/env python3
"""
SLOW-HR BACKTEST (Nov 2, 2026; Peter 15:46: "can we backtest?"). HYPOTHESIS ONLY. Runs the registered SLOW-HR test
(slow_hr.sightings, unchanged: Type L = Pinnacle main line moves >= 0.5 while Hard Rock shows the old line; Type P = same
line, Pinnacle price moves >= 8c while Hard Rock stays within 2c; persistence 3 min + confirmation at +5 min) over every
finished NFL / NCAAF / NHL game since Oct 12 (OddsPapi's history depth), Pinnacle vs Hard Rock, from the shared history
cache. Graded on Pinnacle's no-vig close at Hard Rock's line (CLV in cents, plus % at Hard Rock's price). FIT = first half
of game dates, CHECK = second half. Bar shown (house): >= 100, CLV > 0 and beat-close >= 53% in BOTH halves.
DEVIATIONS as in SLOW-HR: Pinnacle close as the consensus proxy; FEED-LAG not wired. Hard Rock limits Peter on NBA / NCAAB,
so those leagues are excluded. Private email; the log prints counts only.
"""
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import hist_cache as hc
import slow_hr as sh
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NFL", "NCAAF", "NHL")
FROM = datetime.fromisoformat(os.environ.get("BT_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("slow-hr backtest: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    todo = sorted((cl.tp(f["start"]), fid, f) for fid, f in (st.get("fixtures") or {}).items()
                  if f.get("lg") in LEAGUES and cl.tp(f.get("start")) and FROM <= cl.tp(f["start"]) <= now - hc.FINAL_AFTER)
    sh.FLOOR = FROM
    S, games, no_hr, errs = [], 0, 0, 0
    for s, fid, f in todo:
        h = hc.get_hist(fid, ["pinnacle", "hardrockbet"], s)
        if isinstance(h, dict) and h.get("_error"):
            errs += 1
            continue
        pin, hr = cl.book_markets(h, "pinnacle"), cl.book_markets(h, "hardrockbet")
        if not pin or not hr:
            no_hr += 1
            continue
        games += 1
        for x in sh.sightings(fid, {"participant1Name": f.get("n1"), "participant2Name": f.get("n2")}, f["lg"], pin, hr, mkmap, s):
            x["day"] = s.astimezone(ET).strftime("%Y-%m-%d")
            if x.get("close_fair") is not None:
                x["clv_pct"] = round(100 * (x["close_fair"] * x["hr_price"] - 1), 2)
            S.append(x)
    days = sorted({x["day"] for x in S})
    mid = days[(len(days) - 1) // 2] if days else ""

    def stats(xs):
        c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
        p = [x["clv_pct"] for x in xs if x.get("clv_pct") is not None]
        if not c:
            return f"n {len(xs)}"
        return (f"n {len(xs)} | CLV {stt.mean(c):+.2f}c ({stt.mean(p):+.2f}% at HR price) | beat close "
                f"{sum(1 for v in c if v > 0)}/{len(c)} ({100 * sum(1 for v in c if v > 0) / len(c):.0f}%)")

    def ok(xs):
        c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
        return bool(c) and stt.mean(c) > 0 and sum(1 for v in c if v > 0) / len(c) >= 0.53
    J = [x for x in S if not x["late"]]
    F, C = [x for x in J if x["day"] <= mid], [x for x in J if x["day"] > mid]
    L = [f"SLOW-HR BACKTEST - HYPOTHESIS ONLY | Pinnacle vs Hard Rock | NFL / NCAAF / NHL | games {FROM.date()} to now | FIT <= {mid} < CHECK",
         "Registered SLOW-HR test, unchanged (L: line moved >= 0.5, HR on old line; P: price moved >= 8c, HR within 2c; persist 3 min + confirm +5).",
         "Grade: Pinnacle no-vig close at Hard Rock's line. DEVIATIONS: Pinnacle close as consensus proxy; FEED-LAG not wired.", "",
         f"Games read: {games} (no Hard Rock or Pinnacle history: {no_hr}; errors: {errs}); cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}",
         f"ALL (not LATE): {stats(J)}  | bar: {'MEETS' if len(J) >= 100 and ok(F) and ok(C) else 'does not meet'}",
         f"  FIT  {stats(F)}", f"  CHECK {stats(C)}",
         f"  LATE (final 30 min, own split): {stats([x for x in S if x['late']])}"]
    for k in ("L", "P"):
        L.append(f"  Type {k}: {stats([x for x in J if x['kind'] == k])}")
    for lg in LEAGUES:
        for typ in ("totals", "spreads", "moneyline"):
            xs = [x for x in J if x["league"] == lg and x["type"] == typ]
            if xs:
                L.append(f"  {lg} {typ}: {stats(xs)}")
    for lo, hi in ((2, 4), (4, 8), (8, 99)):
        xs = [x for x in J if x.get("ev_pct") is not None and lo <= x["ev_pct"] < hi]
        L.append(f"  EV vs Pinnacle fair at sighting {lo}-{hi if hi < 99 else '+'}%: {stats(xs)}")
    mb = [x["mins_before"] for x in J]
    if mb:
        L.append(f"  Minutes before start (median): {stt.median(mb):.0f}")
    L += ["", "NEWEST 25 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-25:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {x['league']} {x['game']} | {x['type']} {x['team']} {x['line'] if x['line'] is not None else ''} | "
                 f"HR {x['hr_am']:+d} | {x['detail']} | Type {x['kind']}{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start"
                 + (f" | CLV {x['clv_cents']:+.2f}c" if x.get("clv_cents") is not None else ""))
    L += ["", f"Calls: {len(cl.CALLS)} (billable {cl.STATS['billable']})"]
    ex.send("Bets SLOW-HR BACKTEST (HYPOTHESIS)", "\n".join(L))
    print(f"slow-hr backtest: games {games}, sightings {len(S)}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
