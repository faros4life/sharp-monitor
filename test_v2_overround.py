#!/usr/bin/env python3
"""Pinnacle alt overround + V2 model-vs-market calibration screen (v2_overround.py).

Peter, Nov 20: "disagreement between two estimates does not prove which is accurate." These
tests pin the arithmetic and, more importantly, the VERDICT rules from the pre-registered spec -
that thin coverage can never PASS, and that point estimates inside the thresholds with a 95% CI
that escapes them are INCONCLUSIVE rather than a pass.

The de-vig convention is the part worth testing hardest. novig_p splits a book's margin in
PROPORTION to probability, which is an assumption, not a measurement. On a deep alt the even-split
convention gives a materially different fair, so the two are reported side by side.
"""
import v2_overround as vo
import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


# ---------------------------------------------------------------- 1. overround arithmetic
even = 1 / 0.52                       # 52c a side: a 4% hold at even money
ok("overround of a 52/52 market is 4%", abs(vo.overround(even, even) - 0.04) < 1e-12)
ok("a fair 50/50 book has zero overround", abs(vo.overround(2.0, 2.0)) < 1e-12)
for bad in ((0, 2.0), (2.0, 0), (1.0, 2.0), (2.0, 0.5)):
    try:
        vo.overround(*bad)
        ok(f"a non-price {bad} is refused", False, "no error raised")
    except ValueError:
        ok(f"a non-price {bad} is refused", True)

# ---------------------------------------------------------------- 2. the de-vig conventions
a, b = 1 / 0.85, 1 / 0.19             # skewed alt: 85c / 19c, still a 4% hold
ok("proportional de-vig IS clv_ledger.novig_p - not a second way to price",
   abs(vo.devig_proportional(a, b) - cl.novig_p(a, b)) < 1e-15)
ok("proportional de-vig on the skewed alt is 81.73%",
   abs(vo.devig_proportional(a, b) - 0.85 / 1.04) < 1e-12)
ok("even-split de-vig on the skewed alt is 83.00%", abs(vo.devig_even(a, b) - 0.83) < 1e-12)
ok("the two conventions differ by ~1.27pp on a deep alt - more than the +/-1pp threshold",
   1.2 < (vo.devig_even(a, b) - vo.devig_proportional(a, b)) * 100 < 1.3,
   (vo.devig_even(a, b) - vo.devig_proportional(a, b)) * 100)
ok("the conventions agree at even money",
   abs(vo.devig_even(even, even) - vo.devig_proportional(even, even)) < 1e-12)
ok("proportional de-vig FORCES margin share to equal the fair chance (an identity, not a finding)",
   abs(vo.margin_share_a(a, b) - vo.devig_proportional(a, b)) < 1e-12)

# ---------------------------------------------------------------- 3. key numbers and distance
ok("crossing 7 counts (NFL -7.5 from main -6.5)", vo.crosses_key(-7.5, -6.5, "NFL"))
ok("crossing 3 counts", vo.crosses_key(-3.5, -2.5, "NCAAF"))
ok("crossing 10 counts", vo.crosses_key(-10.5, -9.5, "NFL"))
ok("crossing 14 counts", vo.crosses_key(-14.5, -13.5, "NFL"))
ok("landing ON the key number without crossing does not count", not vo.crosses_key(-7.0, -7.0, "NFL"))
ok("a move between keys does not count", not vo.crosses_key(-6.5, -4.5, "NFL"))
ok("basketball has no football key numbers", not vo.crosses_key(-7.5, -6.5, "NBA"))
ok("distance buckets", [vo.distance_bucket(-7.5, -7.0), vo.distance_bucket(-7.5, -6.5),
                        vo.distance_bucket(-7.5, -6.0), vo.distance_bucket(-7.5, -4.5),
                        vo.distance_bucket(-7.5, -3.0)] == ["<=0.5", "0.5-1", "1-2", "2-3", ">3"],
   [vo.distance_bucket(-7.5, -7.0), vo.distance_bucket(-7.5, -6.0)])

# ---------------------------------------------------------------- 4. summarize
s = vo.summarize([0.01] * 4)
ok("the mean is reported in probability POINTS, not fractions", abs(s["mean"] - 1.0) < 1e-12)
ok("a zero-spread sample has a zero-width CI", abs(s["ci_hi"] - s["ci_lo"]) < 1e-12)
s2 = vo.summarize([0.08, -0.08])
ok("mean absolute gap ignores sign", abs(s2["mean_abs"] - 8.0) < 1e-12)
ok("the share beyond 3pp is counted", abs(s2["share_over_3"] - 1.0) < 1e-12)
ok("an empty sample reports n 0 and nothing else", vo.summarize([]) == {"n": 0})

# ---------------------------------------------------------------- 5. THE VERDICT RULES
ok("n below 30 is INCONCLUSIVE however good the mean",
   vo.verdict(vo.summarize([0.0] * 29))[0] == "INCONCLUSIVE")
ok("...and is never PASS", vo.verdict(vo.summarize([0.0] * 29))[0] != "PASS")
ok("a tight sample inside both thresholds PASSes",
   vo.verdict(vo.summarize([0.002] * 40))[0] == "PASS")
ok("a signed mean beyond 1pp FAILs", vo.verdict(vo.summarize([0.015] * 40))[0] == "FAIL")
ok("a signed mean beyond -1pp FAILs", vo.verdict(vo.summarize([-0.015] * 40))[0] == "FAIL")
ok("a mean absolute gap above 2pp FAILs even with a centred mean",
   vo.verdict(vo.summarize([0.025, -0.025] * 20))[0] == "FAIL")
# heavy tails: mean 0 and mean|gap| 1.6pp, but the CI escapes +/-1pp
heavy = [0.0] * 24 + [0.08] * 3 + [-0.08] * 3
hs = vo.summarize(heavy)
ok("a centred mean with a CI that escapes the threshold is INCONCLUSIVE, not PASS",
   vo.verdict(hs)[0] == "INCONCLUSIVE", vo.verdict(hs))
ok("...and that sample really is inside the point thresholds",
   abs(hs["mean"]) <= 1.0 and hs["mean_abs"] <= 2.0, (hs["mean"], hs["mean_abs"]))
ok("subgroups use the lower minimum of 20",
   vo.verdict(vo.summarize([0.002] * 20), vo.MIN_N_SUBGROUP)[0] == "PASS"
   and vo.verdict(vo.summarize([0.002] * 19), vo.MIN_N_SUBGROUP)[0] == "INCONCLUSIVE")
ok("the registered thresholds are the ones in the spec",
   (vo.MIN_N_OVERALL, vo.MIN_N_SUBGROUP, vo.GAP_SIGNED_MAX, vo.GAP_ABS_MAX, vo.GAP_OUTLIER)
   == (30, 20, 1.0, 2.0, 3.0))
ok("a PASS says in words that it is a screen, not authorization",
   "not authorization" in vo.verdict(vo.summarize([0.002] * 40))[1])

# ---------------------------------------------------------------- 6. unrecoverable rows
row = {"league": "NFL", "our_line": -7.5, "main_line": -6.5, "v2_p": 0.52,
       "alt_a": a, "alt_b": b, "main_a": even, "main_b": even, "better": True}
res = vo.analyze([row, dict(row, alt_a=None), dict(row, main_b=None), dict(row, v2_p=None)])
ok("a row with no two-sided quote is counted unrecoverable, not estimated",
   res["unrecoverable"] == 3 and len(res["gap_prop"]) == 1, res["unrecoverable"])
ok("an unsupported V2 row is unrecoverable too, never scored as agreement",
   vo.analyze([dict(row, v2_p=None)])["unrecoverable"] == 1)
ok("both de-vig conventions are carried for every scored row",
   len(res["gap_even"]) == 1 and res["gap_even"][0] != res["gap_prop"][0])
ok("the overround pair is recorded per row", len(res["or_main"]) == 1 and len(res["or_alt"]) == 1)
ok("buckets cover league, direction, distance and key-number crossing",
   set(res["by"]) == {"league NFL", "move favourable", "distance 0.5-1",
                      "football crosses a key number"}, sorted(res["by"]))
ok("a non-football row gets no key-number bucket",
   not any("key number" in k for k in vo.analyze([dict(row, league="NBA")])["by"]))
ok("an unfavourable move is bucketed separately",
   "move unfavourable" in vo.analyze([dict(row, better=False)])["by"])

# ---------------------------------------------------------------- 7. the report's own guards
lines = "\n".join(vo.report(res))
ok("the report never claims distance separates vig from model error", "CANNOT separate" in lines)
ok("the report states a higher alt overround is not proof", "does NOT prove V2 is right" in lines)
ok("the report says a PASS does not authorize promotion", "does not authorize promotion" in lines)
ok("the report names the unrecoverable count", "unrecoverable rows" in lines)
ok("a thin sample reports INCONCLUSIVE in the headline", "INCONCLUSIVE" in lines)
ok("estimated-mass leagues are labelled in the breakdown",
   "[MASS = published estimate]" in "\n".join(vo.report(vo.analyze([dict(row, league="NCAAF")]))))
empty = vo.report({"gap_prop": [], "gap_even": [], "or_main": [], "or_alt": [], "or_diff": [],
                   "margin_share_a": [], "unrecoverable": 7, "by": {}, "rows": []})
ok("no recoverable rows reports INCONCLUSIVE and the count, not a pass",
   "INCONCLUSIVE" in empty[0] and "7" in empty[0], empty)
ok("no dollar figure can reach the log", "$" not in lines)

# ---------------------------------------------------------------- 8. the capture in clv_ledger
src = open("clv_ledger.py").read()
cf = src[src.index("def close_for("):src.index("MAX_NEW_MAIL")]
ok("the raw two-sided decimals are captured from the SAME two_way call",
   "tw[a_id][0], tw[b_id][0]" in cf)
ok("both exact branches carry the quote pairs", cf.count('"alt_px": _apx, "main_px": _mpx') == 2)
ok("the held side is put first in both branches", cf.count("# held side first") == 2)
ok("V1's official p is still read at our own number", cf.count('"p": _p1v') == 2)
ok("the main-line index access is unchanged by the wider tuple",
   "main = max(cands, key=lambda c: (c[3], -abs(c[1] - 0.5)))" in cf)

rec, c = {}, {"v2_p": 0.52, "at_main": False, "v2_better": True,
              "alt_px": (1.9, 2.1), "main_px": (1.95, 1.95), "v2_src": ["NFL spread 7"]}
ok("record_v2 persists both observed pairs on a moved row", cl.record_v2(rec, c, 2.0)
   and rec["alt_px"] == [1.9, 2.1] and rec["main_px"] == [1.95, 1.95] and rec["v2_better"] is True,
   rec)
rec2 = {}
cl.record_v2(rec2, dict(c, at_main=True), 2.0)
ok("an at-main row stores no quote pair - V2 == V1 there, so there is nothing to calibrate",
   "alt_px" not in rec2 and "main_px" not in rec2)

st = {"bets": {
    "a": {"clv_v2": 0.01, "v2_derived": True, "close_p_v2": 0.52, "our_line": -7.5,
          "main_line": -6.5, "alt_px": [1 / 0.85, 1 / 0.19], "main_px": [1 / 0.52, 1 / 0.52],
          "v2_better": True, "snap": {"league": "NFL"}},
    "b": {"clv_v2": 0.01, "v2_derived": True, "close_p_v2": 0.52, "our_line": -7.5,
          "main_line": -6.5, "snap": {"league": "NFL"}},                      # no pairs held
    "c": {"clv_v2": 0.01, "v2_derived": True, "close_p_v2": 0.52,
          "alt_px": [1.9, 2.1], "main_px": [1.95, 1.95], "snap": {"league": "NFL"}},  # no lines
    "d": {"clv_v2": 0.01, "v2_derived": False, "close_p_v2": 0.52, "snap": {"league": "NFL"}},
    "e": {"clv": -0.01, "snap": {"league": "NFL"}}}}                          # V1 only
lines = "\n".join(cl.v2_calibration(st))
ok("v2_calibration counts the unrecoverable moved rows and skips at-main and V1-only rows",
   "unrecoverable rows (no two-sided quote held, never estimated): 2" in lines, lines)
ok("one recoverable row is far too thin to pass", "INCONCLUSIVE" in lines)
ok("v2_calibration never reports a dollar figure", "$" not in lines)

# ---------------------------------------------------------------- 9. the timestamp confound
from datetime import datetime, timedelta, timezone
ok("ts_spread is oldest minus newest", vo.ts_spread([5.0, 7.0, 2.0, 40.0]) == 38.0)
ok("a simultaneous reading has zero spread", vo.ts_spread([3.0] * 4) == 0.0)
for bad in (None, [], [1.0, 2.0], [1.0, 2.0, 3.0, None]):
    ok(f"unrecorded timestamps {bad} give None, never 0", vo.ts_spread(bad) is None)

base = dict(league="NFL", our_line=-7.5, main_line=-6.5, v2_p=0.52,
            alt_a=1 / 0.85, alt_b=1 / 0.19, main_a=1 / 0.52, main_b=1 / 0.52, better=True)
r = vo.analyze([dict(base, ts_ages=[2.0, 3.0, 1.0, 4.0]),      # tight
                dict(base, ts_ages=[2.0, 3.0, 1.0, 600.0]),    # stale alt/main mix
                dict(base)])                                   # no timestamps
ok("the tight row feeds the sensitivity subset, the wide one does not",
   len(r["gap_prop_tight"]) == 1 and len(r["ts_spread"]) == 2, (r["gap_prop_tight"], r["ts_spread"]))
ok("a row with no timestamps is counted, not treated as simultaneous", r["ts_missing"] == 1)
ok("a missing-timestamp row is still scored for the main screen", len(r["gap_prop"]) == 3)
lines9 = "\n".join(vo.report(r))
ok("the report prints the timestamp spread and says they are not one quote",
   "TIMESTAMP SPREAD" in lines9 and "NOT one quote" in lines9)
ok("the report runs the near-simultaneous sensitivity check", "SENSITIVITY on near-simultaneous" in lines9)
ok("the report warns that a disagreement means STALENESS, not alt vig",
   "contaminated by STALENESS" in lines9)
ok("the report names how many rows lack timestamps", "no timestamps recorded" in lines9)
no_tight = vo.report(vo.analyze([dict(base, ts_ages=[2.0, 3.0, 1.0, 600.0])]))
ok("with no near-simultaneous row the report says staleness cannot be separated",
   any("cannot be separated from staleness" in x for x in no_tight), no_tight)

# ---------------------------------------------------------------- 10. the ledger capture
src2 = open("clv_ledger.py").read()
cf2 = src2[src2.index("def close_for("):src2.index("MAX_NEW_MAIL")]
ok("the tick timestamps are captured alongside the prices", "tw[a_id][1], tw[b_id][1]" in cf2)
ok("both exact branches record ts_ages", cf2.count('"ts_ages": _ts_ages(start,') == 2)
ok("the held side is first for timestamps too", cf2.count("_ats = (exact[6], exact[7])") == 2)
st_ = datetime(2026, 11, 20, 20, 0, tzinfo=timezone.utc)
ages = cl._ts_ages(st_, (st_ - timedelta(minutes=2), st_ - timedelta(minutes=3)),
                   (st_ - timedelta(minutes=1), st_ - timedelta(minutes=90)))
ok("_ts_ages gives minutes before kick, held side first", ages == [2.0, 3.0, 1.0, 90.0], ages)
ok("_ts_ages never returns a negative age",
   cl._ts_ages(st_, (st_ + timedelta(minutes=5), st_), (st_, st_))[0] == 0.0)
ok("an unreadable timestamp yields None, not a guess", cl._ts_ages(st_, (None, None), (None, None)) is None)
rec3 = {}
cl.record_v2(rec3, {"v2_p": 0.52, "at_main": False, "v2_better": True, "alt_px": (1.9, 2.1),
                    "main_px": (1.95, 1.95), "ts_ages": [2.0, 3.0, 1.0, 90.0]}, 2.0)
ok("record_v2 persists the four ages on a moved row", rec3.get("ts_ages") == [2.0, 3.0, 1.0, 90.0], rec3)
ok("the spec records the timestamp confound and the correction",
   "was wrong and is corrected here" in open("v2_validation_spec.md").read())

# ---------------------------------------------------------------- 11. snapshot matching
import snapshot_source as ss
bet_os = {"league": "NCAAB", "game": "UMBC Retrievers @ Ohio State Buckeyes", "bet": "Under 158.5 (-115)"}
bet_or = {"league": "NCAAB", "game": "Oregon State Beavers @ Oregon Ducks", "bet": "Under 160.5 (-110)"}
snap_os = {"day": "2026-11-19", "league": "NCAAB", "game": "UMBC Retrievers @ Ohio State Buckeyes",
           "market": "total", "side": "UNDER", "line": 155.5, "line_type": "main", "t_minus_min": 12}
ok("a snapshot matches its OWN game", ss.matches(snap_os, bet_os, "2026-11-19"))
ok("a snapshot NEVER matches another game's bet - the wrong-game CLV bug",
   not ss.matches(snap_os, bet_or, "2026-11-19"))
ok("a far-away total on the same game is refused",
   not ss.matches(dict(snap_os, line=139.5), bet_os, "2026-11-19"))
ok("the wrong side is refused", not ss.matches(dict(snap_os, side="OVER"), bet_os, "2026-11-19"))
ok("the wrong day is refused", not ss.matches(snap_os, bet_os, "2026-11-18"))
ok("the wrong league is refused", not ss.matches(dict(snap_os, league="NBA"), bet_os, "2026-11-19"))
ok("a same-line quote outranks a main-line one",
   ss.rank({"line_type": "alt_our_line", "t_minus_min": 4}) < ss.rank({"line_type": "main", "t_minus_min": 4}))
ok("among same types, fresher wins",
   ss.rank({"line_type": "main", "t_minus_min": 4}) < ss.rank({"line_type": "main", "t_minus_min": 12}))

# ---------------------------------------------------------------- 12. certification + real quotes
ok("a same-line quote with no conversion is SAME-LINE",
   ss.certification({"line_type": "alt_our_line"}, []).startswith("SAME-LINE"))
ok("a same-line record that still needed rows is NOT certified",
   ss.certification({"line_type": "alt_our_line"}, ["NCAAB spread 7"]).startswith("PROVISIONAL"))
ok("a main-line quote is always PROVISIONAL CONVERTED",
   ss.certification({"line_type": "main"}, []).startswith("PROVISIONAL"))

def devig_clv(our_am, other_am, paid_am):
    """Independent check of the approved method: proportional de-vig, then fair x our payout - 1."""
    def dec(a):
        return 1 + (a / 100.0 if a > 0 else 100.0 / -a)
    p = vo.devig_proportional(dec(our_am), dec(other_am))
    return round((p * dec(paid_am) - 1) * 100, 2)

ok("St Bonaventure -11.5: -115/-103 against our -105 gives +0.19%",
   devig_clv(-115, -103, -105) == 0.19, devig_clv(-115, -103, -105))
ok("Oregon U160.5: -112/-110 against our -110 gives -4.14%",
   devig_clv(-112, -110, -110) == -4.14, devig_clv(-112, -110, -110))
ok("Texans -10.5: -134/+118 against our -114 gives +4.23%",
   devig_clv(-134, 118, -114) == 4.23, devig_clv(-134, 118, -114))
ok("GSW U225.5: -114/-102 against our +100 gives +2.68%",
   devig_clv(-114, -102, 100) == 2.68, devig_clv(-114, -102, 100))
ok("LAC U226.5: -130/+111 against our -108 gives +4.76%",
   devig_clv(-130, 111, -108) == 4.76, devig_clv(-130, 111, -108))
ok("Toledo -6.5: -124/+104 against our -115 gives -0.85%",
   devig_clv(-124, 104, -115) == -0.85, devig_clv(-124, 104, -115))

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
import sys as _sys
_sys.exit(1 if FAILED else 0)   # a soft assertion failure MUST fail the build, not print and pass
