#!/usr/bin/env python3
"""
ACTUAL PLAYS: FLAT vs KELLY, BY BUCKET (Nov 2, 2026; Peter 18:56: "now do the same for actual plays broken down by buckets").
HYPOTHESIS ONLY - a look back; no sizing or betting change. Reads the encrypted CLV ledger (every real bet the tracker has
seen: bot, ntfy alerts played, Street Value, Peter's own), so it runs in Actions with TRACKER_PASSPHRASE. Private email
(dollar amounts); the log prints counts only.
For each window (last month / 3 weeks / 2 weeks) and each standard bucket (BUCKETS.md fields these records carry):
  FLAT        = 1 unit per bet at the bet's own after-fee price (W: price - 1, L: -1, P: 0)
  ACTUAL      = the real dollar result (stake x outcome) as recorded
  KELLY (now) = quarter Kelly sized on the edge known at the time: running ROI of earlier graded plays (>= 20), capped 2%
  KELLY (hindsight) = quarter / full Kelly on the bet's own CLV vs Pinnacle's close (known only after the close: upper bound)
Bankroll for the Kelly runs starts at 100 units; results are % of that bankroll.
"""
import json
import statistics as stt
from datetime import datetime, timedelta, timezone

import buckets as bkt
import clv_ledger as cl
import executor as ex
import tracker_build as tb

ET = tb.ET
WINDOWS = (("last month (Oct 5 on)", "2026-10-05"), ("last 3 weeks (Oct 12 on)", "2026-10-12"), ("last 2 weeks (Oct 19 on)", "2026-10-19"))


def plays():
    st = tb.dec(json.load(open(cl.STATE)))
    try:
        sv = cl.sv_registry()
    except (Exception, SystemExit):
        sv = []
    out = []
    for k, rec in (st.get("bets") or {}).items():
        s = rec.get("snap") or {}
        res = s.get("result")
        if res not in ("W", "L", "P"):
            continue
        d = cl.eff_dec(s)
        if not d or d <= 1:
            continue
        t = cl.tp(s.get("placed")) or cl.tp(s.get("game_start")) or cl.tp(s.get("settled"))
        if not t:
            continue
        pz = cl.parsed(s)
        mk = {"total": "totals", "spread": "spreads", "ml": "moneyline"}.get(pz[0]) if pz else None
        line = None
        if pz and pz[0] in ("total", "spread"):
            line = pz[2]
            if pz[0] == "spread" and line is not None and len(pz) > 3 and pz[3]:
                line = -line
        stake = tb.num(s.get("stake"))
        actual = None
        if stake:
            actual = stake * (d - 1) if res == "W" else (-stake if res == "L" else 0.0)
        gs = cl.tp(s.get("game_start"))
        out.append({"t": t, "day": t.astimezone(ET).strftime("%Y-%m-%d"), "res": res, "d": d,
                    "flat": (d - 1) if res == "W" else (-1.0 if res == "L" else 0.0), "actual": actual,
                    "clv": None if rec.get("clv") is None else round(100 * rec["clv"], 2),
                    "lane": cl.lane_of(s, sv), "book": s.get("book") or "?", "lg": s.get("league"), "mk": mk,
                    "sc": bkt.side_class(mk, pz[1] if pz else None, line), "key": bkt.key_class(s.get("league"), mk, line),
                    "lead": (gs - cl.tp(s.get("placed"))).total_seconds() / 60 if gs and cl.tp(s.get("placed")) else None,
                    "am": cl.dec_to_am(d)})
    return sorted(out, key=lambda x: x["t"])


def sims(xs, allx):
    """(flat units, actual $, kelly-now %, q-kelly hindsight %, full-kelly hindsight %, max drawdowns)."""
    def run(fn, cap):
        B, peak, mdd, n = 100.0, 100.0, 0.0, 0
        for x in xs:
            f = fn(x)
            if f and f > 0:
                f = min(f, cap)
                s = B * f
                n += 1
                B += s * (x["d"] - 1) if x["res"] == "W" else (-s if x["res"] == "L" else 0)
                peak, mdd = max(peak, B), max(mdd, (peak - B) / peak)
        return B - 100, 100 * mdd, n

    def now_edge(x):
        prior = [y["flat"] for y in allx if y["t"] < x["t"]]
        return 0.25 * (stt.mean(prior) if len(prior) >= 20 else 0) / (x["d"] - 1)
    flat = sum(x["flat"] for x in xs)
    act = [x["actual"] for x in xs if x["actual"] is not None]
    kn = run(now_edge, 0.02)
    kq = run(lambda x: None if x["clv"] is None else 0.25 * x["clv"] / 100 / (x["d"] - 1), 0.02)
    kf = run(lambda x: None if x["clv"] is None else x["clv"] / 100 / (x["d"] - 1), 1.0)
    w, l, p = (sum(x["res"] == r for x in xs) for r in ("W", "L", "P"))
    return (f"n {len(xs)} ({w}-{l}-{p}) | FLAT {flat:+.2f}u ({100 * flat / max(len(xs), 1):+.1f}% per bet) | ACTUAL "
            f"USD {sum(act):+,.0f} on {len(act)} with stakes | KELLY now {kn[0]:+.1f}% (dd {kn[1]:.0f}%) | q-KELLY hindsight "
            f"{kq[0]:+.1f}% (dd {kq[1]:.0f}%, {kq[2]} bets) | full hindsight {kf[0]:+.1f}% (dd {kf[1]:.0f}%)")


def main():
    now = datetime.now(timezone.utc)
    P = plays()
    L = [f"ACTUAL PLAYS - FLAT vs KELLY BY BUCKET - HYPOTHESIS ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET | {len(P)} graded real bets",
         "FLAT = 1u at the bet's own after-fee price. ACTUAL = real dollars. KELLY now = quarter Kelly on the edge known at the time",
         "(running ROI of earlier plays, >= 20), cap 2%. Hindsight = Kelly on the bet's own CLV vs Pinnacle close (upper bound; not",
         "knowable when betting). Kelly bankroll starts at 100 units. Small cells are noise: under ~50 bets, read nothing into it.", ""]
    for wl, d0 in WINDOWS:
        xs = [x for x in P if x["day"] >= d0]
        L += [f"===== {wl} =====", "  ALL: " + sims(xs, P)]
        groups = [("Lane", "lane", None), ("Book", "book", None), ("League", "lg", None), ("Market", "mk", None),
                  ("Side (by points)", "sc", None), ("Football key numbers", "key", None)]
        for lab, k, _ in groups:
            vals = sorted({x[k] for x in xs if x.get(k)})
            if not vals:
                L.append(f"  {lab}: not in these records")
                continue
            for v in vals:
                L.append(f"  {lab} {v}: " + sims([x for x in xs if x.get(k) == v], P))
        L.append("  Price -110 or worse: " + sims([x for x in xs if x["am"] is not None and x["am"] <= -110], P))
        L.append("  Price better than -110: " + sims([x for x in xs if x["am"] is not None and x["am"] > -110], P))
        for lo, hi, lab in ((0, 30, "LATE (final 30 min)"), (30, 120, "30m-2h"), (120, 360, "2-6h"), (360, 1440, "6-24h"), (1440, 1e9, "24h+")):
            ys = [x for x in xs if x.get("lead") is not None and lo <= x["lead"] < hi]
            if ys:
                L.append(f"  Time before start {lab}: " + sims(ys, P))
        L.append("")
    L += bkt.section("actual plays, CLV % vs Pinnacle close (all windows)", [dict(x, edge=None) for x in P], "%")
    ex.send("Bets ACTUAL PLAYS - FLAT vs KELLY BY BUCKET (HYPOTHESIS)", "\n".join(L))
    print(f"plays kelly: graded plays {len(P)}")   # counts only


if __name__ == "__main__":
    main()
