#!/usr/bin/env python3
"""Nov 17: frozen board calls are graded from the FULL feeds, not only today's rows."""
import sys

import board_build as bb

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


C = {"k1|t1": {"call": "PLAY"}, "k2|t2": {"call": "PLAY", "result": "W", "units": 0.9}, "k3|t3": {"call": "PLAY"},
     "k4|t4": {"call": "PLAY"}}
A = [{"key": "k1", "alerted_utc": "t1", "result": "L", "units_flat": -1.0},
     {"key": "k2", "alerted_utc": "t2", "result": "L", "units_flat": -1.0},
     {"key": "k3", "alerted_utc": "t3"},
     {"key": "k4", "alerted_utc": "OTHER", "result": "W", "units_flat": 1.0}]
n = bb.backfill_results(C, A)
check("an ungraded call whose alert now has a result is graded", C["k1|t1"].get("result") == "L" and C["k1|t1"]["units"] == -1.0)
check("an already graded call is never changed", C["k2|t2"]["result"] == "W")
check("no result in the feed -> stays ungraded", "result" not in C["k3|t3"])
check("only an exact key|alerted_utc match counts", "result" not in C["k4|t4"])
check("returns the number graded", n == 1)
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
