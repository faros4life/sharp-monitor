#!/usr/bin/env python3
"""
CLV BASIS AUDIT (Peter Nov 5). READ-ONLY. Writes no state, places nothing, changes no rule or threshold.

Why: clv_ledger.close_for() will convert Pinnacle's main line to the bet's line with sharp_monitor.half_point_value()
when Pinnacle had no close at the bet's own number, and the totals tolerance is max(1.5, 0.03 * ppt) - which for an
NBA total at 219.5 permits a 6.585-point walk, then clamps the result to [0.01, 0.99]. Every report so far has mixed
those MODELED closes into one headline with genuinely observed SAME-LINE closes. This audit separates them.

FIRST DELIVERABLE, and the reason this runs ahead of everything else: Lane 1's kill-switch is

    alert = len(bot) >= 50 and sum(r["clv"] for r in bot[-50:]) / 50 < 0

computed with no regard to "how". Lane 1 is totals-only, which puts its bets in NBA totals - the one market with the
6.6-point tolerance. So the question is not academic: it is whether a live safety signal has been reading a reliable
number. This prints the mixed-basis average the switch actually uses, the verified-only average beside it, and the
sample size of each.

Bases, taken from each row's own "how" field - nothing is inferred:
    VERIFIED    how == "own line" or "moneyline"  -> Pinnacle closed on the bet's exact market and number
    MODELED     how == "main X moved to Y"        -> converted; the distance |Y - X| is parsed out and bucketed
    UNAVAILABLE no clv at all                     -> counted, never averaged into anything

The 1.5-point totals cap and any tighter spread cap are PROPOSALS. This script only prices what they WOULD exclude,
by league, market and basis. It applies neither. Original numbers are reported unchanged beside the split.

Private email: CLV percentages, counts and units only - no stakes, no balances, no dollar figures, no account data.
The log prints counts only.
"""
import json
import os
import re
import statistics as stt
from datetime import datetime, timezone

import executor as ex
import tracker_build as tb

STATE = "clv/state.enc"
ET = tb.ET
SWITCH_N = 50          # the kill-switch window, as clv_ledger defines it
TOT_CAP = 1.5          # PROPOSED totals cap - priced here, never applied
SPR_CAP = 1.5          # PROPOSED spread cap - priced here, never applied
AGE_BUCKETS = ((5, "0-5 min"), (15, "5-15 min"), (60, "15-60 min"), (10 ** 9, "60+ min"))


def basis(r):
    h = (r.get("how") or "").strip()
    if h in ("own line", "moneyline"):
        return "VERIFIED"
    if h.startswith("main ") and " moved to " in h:
        return "MODELED"
    return "OTHER" if h else "UNAVAILABLE"


def conv_of(r):
    """Conversion distance from the row's own 'how' string: 'main 219.5 moved to 225.5' -> 6.0. None if not modeled."""
    m = re.match(r"^main\s+([+-]?\d+(?:\.\d+)?)\s+moved to\s+([+-]?\d+(?:\.\d+)?)$", (r.get("how") or "").strip())
    if not m:
        return None
    try:
        return round(abs(float(m.group(2)) - float(m.group(1))), 2)
    except Exception:
        return None


def cbucket(c):
    if c is None:
        return "n/a"
    return ("0-0.5" if c <= 0.5 else ">0.5-1.0" if c <= 1.0 else ">1.0-1.5" if c <= 1.5
            else ">1.5-3.0" if c <= 3.0 else ">3.0")


def abucket(age):
    if age is None:
        return "unknown"
    for lim, lab in AGE_BUCKETS:
        if age < lim:
            return lab
    return "60+ min"


def mk_of(r):
    s = r.get("snap") or {}
    bet = (s.get("bet") or "").lower()
    if "over" in bet or "under" in bet:
        return "total"
    return "spread/ml"


def stats(rows):
    if not rows:
        return "n 0"
    cv = [r["clv"] for r in rows]
    return (f"n {len(rows)} | mean CLV {100 * stt.mean(cv):+.2f}% | beat close "
            f"{sum(1 for v in cv if v > 0)}/{len(cv)} ({100 * sum(1 for v in cv if v > 0) / len(cv):.0f}%)")


def main():
    now = datetime.now(timezone.utc)
    if not os.environ.get("TRACKER_PASSPHRASE"):
        print("clv basis audit: TRACKER_PASSPHRASE not set; skipped")
        return
    st = tb.dec(json.load(open(STATE)))
    bets = st.get("bets") or {}

    # the ledger's own definitions, copied verbatim so this audits the same population the switch reads
    scored = sorted([dict(r, id=k) for k, r in bets.items() if r.get("clv") is not None],
                    key=lambda r: r.get("scored") or "")
    bot = [r for r in scored if (r["snap"].get("source") or "") == "bot"]
    man = [r for r in scored if (r["snap"].get("source") or "") != "bot"]
    unavail = [dict(r, id=k) for k, r in bets.items() if r.get("clv") is None]

    L = [f"CLV BASIS AUDIT - READ-ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Separates VERIFIED same-line closes from MODELED (line-converted) ones. Applies nothing; changes no rule,",
         "threshold, stake or execution path. Proposed caps are PRICED here, not enforced.", ""]

    # ---------------------------------------------------------------- 1. the kill-switch
    w = bot[-SWITCH_N:]
    ver = [r for r in w if basis(r) == "VERIFIED"]
    mod = [r for r in w if basis(r) == "MODELED"]
    oth = [r for r in w if basis(r) not in ("VERIFIED", "MODELED")]
    L += ["=" * 60, f"1. LANE 1 KILL-SWITCH AUDIT - last {SWITCH_N} scored BOT bets", "=" * 60,
          f"Bot bets scored in total: {len(bot)}. Window used by the switch: the newest {len(w)}.", ""]
    if not w:
        L.append("No scored bot bets: the switch cannot fire and there is nothing to audit.")
    else:
        mixed = stt.mean([r["clv"] for r in w])
        L += [f"  MIXED BASIS (what the switch actually reads today): {stats(w)}",
              f"  VERIFIED same-line only:                           {stats(ver)}",
              f"  MODELED (line-converted) only:                     {stats(mod)}"]
        if oth:
            L.append(f"  neither (no usable 'how'):                         {stats(oth)}")
        L += ["", f"  Switch arithmetic: mixed average {100 * mixed:+.3f}% -> "
                  f"{'WOULD ALERT' if (len(bot) >= SWITCH_N and mixed < 0) else 'would not alert'}"]
        if ver:
            va = stt.mean([r["clv"] for r in ver])
            L.append(f"  Verified-only average {100 * va:+.3f}% (n {len(ver)}) -> "
                     f"{'WOULD ALERT' if va < 0 else 'would not alert'}")
            L.append("  *** THE TWO DISAGREE - the switch's verdict depends on the basis ***"
                     if (mixed < 0) != (va < 0) else
                     "  The two agree, so the switch's verdict does not turn on the basis in this window.")
        else:
            L.append("  No verified rows in the window: the switch is running entirely on converted closes.")
        if mod:
            cs = [c for c in (conv_of(r) for r in mod) if c is not None]
            if cs:
                L.append(f"  Conversion distances in the window: max {max(cs):g} pt, median {stt.median(cs):g} pt, "
                         f"over {TOT_CAP:g} pt: {sum(1 for c in cs if c > TOT_CAP)} of {len(cs)}")
    L.append("")

    # ---------------------------------------------------------------- 2. basis split, whole ledger
    L += ["=" * 60, "2. BASIS SPLIT - every scored bet", "=" * 60]
    for nm, rows in (("BOT", bot), ("Peter / other", man), ("ALL scored", scored)):
        L.append(f"  {nm}:")
        for b in ("VERIFIED", "MODELED", "OTHER"):
            sub = [r for r in rows if basis(r) == b]
            if sub:
                L.append(f"     {b:<10} {stats(sub)}")
        L.append(f"     original mixed headline, unchanged: {stats(rows)}")
    L.append(f"  UNAVAILABLE (no CLV at all, never averaged anywhere): n {len(unavail)}")
    L.append("")

    # ---------------------------------------------------------------- 3. conversion distance
    L += ["=" * 60, "3. CONVERSION DISTANCE on MODELED rows (parsed from each row's own 'how')", "=" * 60]
    allmod = [r for r in scored if basis(r) == "MODELED"]
    if not allmod:
        L.append("  No modeled closes anywhere in the ledger - every scored bet closed on its own line.")
    else:
        by = {}
        for r in allmod:
            key = f"{(r['snap'].get('league') or '?')} {mk_of(r)}"
            by.setdefault(key, []).append(r)
        for key in sorted(by):
            rows = by[key]
            bk = {}
            for r in rows:
                bk.setdefault(cbucket(conv_of(r)), []).append(r)
            L.append(f"  {key}: {stats(rows)}")
            for b in ("0-0.5", ">0.5-1.0", ">1.0-1.5", ">1.5-3.0", ">3.0", "n/a"):
                if b in bk:
                    L.append(f"       {b:<10} {stats(bk[b])}")
    L.append("")

    # ---------------------------------------------------------------- 4. what a cap would exclude (PRICED, NOT APPLIED)
    L += ["=" * 60, f"4. EXCLUSION PREVIEW - a {TOT_CAP:g}pt totals cap / {SPR_CAP:g}pt spread cap. NOT APPLIED.", "=" * 60,
          "  These are proposals. Nothing below is enforced and no historical result is restated by this run."]
    for nm, rows in (("BOT (real bets)", bot), ("Peter / other (real bets)", man)):
        drop = [r for r in rows if (conv_of(r) or 0) > (TOT_CAP if mk_of(r) == "total" else SPR_CAP)]
        dids = {r["id"] for r in drop}
        keep = [r for r in rows if r["id"] not in dids]
        L += [f"  {nm}: would exclude {len(drop)} of {len(rows)}",
              f"     excluded rows:  {stats(drop)}",
              f"     surviving rows: {stats(keep)}"]
        if drop:
            per = {}
            for r in drop:
                per.setdefault(f"{(r['snap'].get('league') or '?')} {mk_of(r)}", 0)
                per[f"{(r['snap'].get('league') or '?')} {mk_of(r)}"] += 1
            L.append("     by league x market: " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())))
    L += ["  NOTE: paper-test populations (SENT, LIQ-MAIN, SLOW-HR, Lane 2) are NOT in this ledger - it holds real",
          "  bets only. Their exclusion counts come from the per-play exports, reported separately."]
    L.append("")

    # ---------------------------------------------------------------- 5. freshness, by basis
    L += ["=" * 60, "5. CLOSE FRESHNESS by basis (age of Pinnacle's read before start)", "=" * 60]
    for b in ("VERIFIED", "MODELED"):
        rows = [r for r in scored if basis(r) == b]
        if not rows:
            continue
        L.append(f"  {b}:")
        bk = {}
        for r in rows:
            bk.setdefault(abucket(r.get("age_min")), []).append(r)
        for _, lab in AGE_BUCKETS:
            if lab in bk:
                L.append(f"     {lab:<10} {stats(bk[lab])}")
        if "unknown" in bk:
            L.append(f"     {'unknown':<10} {stats(bk['unknown'])}")
    L += ["", "Read-only: this script wrote no state and changed no rule. Verified and modeled CLV are never again to",
          "be combined into a primary headline."]

    body = "\n".join(L)
    ex.send("Bets CLV BASIS AUDIT (read-only)", body)
    print(f"clv basis audit: scored {len(scored)}, bot {len(bot)}, verified "
          f"{sum(1 for r in scored if basis(r) == 'VERIFIED')}, modeled "
          f"{sum(1 for r in scored if basis(r) == 'MODELED')}, no-CLV {len(unavail)}")


if __name__ == "__main__":
    main()
