#!/usr/bin/env python3
"""Nov 17 (Peter): certified CLV = same-line Pinnacle or exact moneyline only; line-move-adjusted = ESTIMATED, apart."""
import sys

import report_sections as rs

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


cb = {"a": {"clv": 0.04, "how": "own line"}, "b": {"clv": 0.01, "how": "moneyline"},
      "c": {"clv": 0.03, "how": "main 141.5 moved to 143.5"}, "d": {"clv": -0.02, "how": "main -3 moved to -2.5"},
      "e": {"clv": 0.05, "how": None}, "f": {"clv": 0.02, "how": "own line", "fixture_doubt": True},
      "g": {"clv": 0.02, "how": "own line"}, "h": {"how": "own line"}}
cert, est, unk = rs.split_clv(cb, {"g"})
check("certified = own line + moneyline only", set(cert) == {"a", "b"})
check("line-move adjusted closes are ESTIMATED", set(est) == {"c", "d"})
check("unknown method is neither", set(unk) == {"e"})
check("fixture doubt, stale and unscored rows are excluded everywhere", not ({"f", "g", "h"} & (set(cert) | set(est) | set(unk))))
check("ledger rows are not modified", cb["c"] == {"clv": 0.03, "how": "main 141.5 moved to 143.5"})

# scorecard: estimated never enters the certified mean / gate input
plays = [{"result": "W", "stake": 100.0, "profit": 90.0, "game_start": "2026-11-13T00:00:00+00:00", "ids": ["a"]},
         {"result": "L", "stake": 100.0, "profit": -100.0, "game_start": "2026-11-14T00:00:00+00:00", "ids": ["c"]},
         {"result": "L", "stake": 100.0, "profit": -100.0, "game_start": "2026-11-15T00:00:00+00:00", "ids": ["c", "a"]}]
rep = {"buckets": {"EXACT:R1": {"_settled_timed": plays, "open_or_ambiguous": 1}}}
sc = rs.lane_scope(rep, "R1", cert, {"R1": ("2026-11-11T00:00:00+00:00", 200.0)}, est)
check("certified mean uses only the same-line play", sc["whole"]["clv_n"] == 1 and sc["whole"]["clv"] == 4.0)
check("a play mixing certified and estimated components is not certified", sc["whole"]["clv_missing"] == 2)
check("estimated reported separately", sc["est"]["whole"]["clv_n"] == 1 and sc["est"]["whole"]["clv"] == 3.0)
cmb = rs.combined_scope({"R1": sc, "BOARD V4": None})
check("combined counts each play once", cmb["whole"]["n"] == 3 and cmb["whole"]["W"] == 1 and cmb["whole"]["L"] == 2)
check("combined units are the lane-unit sum", cmb["whole"]["units"] == round((90 - 200) / 200, 2))
txt = rs.render_scorecard([("X", {"R1": sc})], {}, {})
check("scorecard labels estimated CLV as NOT certified", "ESTIMATED CLV (line-move adjusted, NOT certified" in txt)
check("qualification is labelled certified-only", "QUALIFICATION (certified CLV only)" in txt)
check("no currency sign in the scorecard", "$" not in txt)

g = rs.grade_rows([{"id": "c", "result": "L", "stake": 100.0, "profit": -100.0, "book": "Novig",
                    "game_start": "2026-11-14T00:00:00+00:00"}], {"c": "EXACT:R1"}, cert, cb, set(),
                  {"R1": ("2026-11-11T00:00:00+00:00", 200.0)}, estimated=est)[0]
check("a line-move-adjusted bet is graded ESTIMATED, not certified", g["clv"] is None and g["clv_status"].startswith("ESTIMATED only"))
check("and it is not fully graded", g["fully_graded"] is False)

# Section J by POSITION (Nov 17): a 2-row position counts once, and only when every row qualifies
grs = [{"id": "x1", "fully_graded": True}, {"id": "x2", "fully_graded": True}, {"id": "y1", "fully_graded": True},
       {"id": "z1", "fully_graded": False}]
pls = [{"ids": ["x1", "x2"]}, {"ids": ["y1"]}, {"ids": ["z1"]}]
pc = rs.position_counts(grs, pls, {"x1": .01, "x2": .02, "y1": .0}, {"z1": .03})
check("fully graded counts positions, not fill rows", pc["fully_graded"] == 2)
check("certified positions need every row certified", pc["certified_clv_positions"] == 2)
check("estimated positions counted apart", pc["estimated_clv_positions"] == 1)
pc2 = rs.position_counts([{"id": "x1", "fully_graded": True}, {"id": "x2", "fully_graded": False}], [{"ids": ["x1", "x2"]}], {"x1": .01}, {})
check("one ungraded row makes the whole position incomplete", pc2["fully_graded"] == 0 and pc2["certified_clv_positions"] == 0)

src = open("p2_audit.py").read()
check("Section H carries the previous ET day as its own scope, beside Nov 12-forward",
      'ET ONLY (one day - halves statistically insufficient)' in src and '("SINCE 12 NOV ET", rep_f)' in src)

print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
