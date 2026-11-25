#!/usr/bin/env python3
"""Every lane that can place live money must have a unit in the exposure ledger.

Nov 23: DOGS went live while review_replay.LANE_UNIT still listed four lanes. The lane's own
reservation was correct, but every path that re-derives the unit from a registry ROW read "lane
unknown" - and the sweep's fallback valued a $100 dog at half a unit, which lets a second order
through on the same play. This test exists so the next lane cannot be added without its unit.
"""
import re

import executor as ex
import review_replay as RR

P, F = [], []
def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))

SRC = open("executor.py", encoding="utf-8").read()

# A lane can place live money when it has BOTH a money switch and a unit constant.
LIVE_LANES = {"rules": ("LIVE_UNIT", "EXEC_LIVE"), "board": ("BOARD_UNIT", "EXEC_BOARD_LIVE"),
              "r1": ("R1_UNIT", "EXEC_R1_LIVE"), "ncs": ("NCS_UNIT", "EXEC_NCS_LIVE"),
              "dogs": ("DOGS_UNIT", "EXEC_DOGS_LIVE")}

ok("the live-lane list still matches the lanes executor names",
   set(LIVE_LANES) | {"lane2"} == set(ex.LANE_NAME), sorted(set(ex.LANE_NAME)))
for src, (const, switch) in sorted(LIVE_LANES.items()):
    ok(f"{src}: executor defines {const} and the {switch} switch",
       hasattr(ex, const) and switch in SRC)
    lane = RR.SOURCE_LANE.get(src)
    ok(f"{src}: the ledger maps the source to a lane", bool(lane), str(lane))
    ok(f"{src}: the ledger knows its unit and it equals executor's {const}",
       lane in RR.LANE_UNIT and RR.LANE_UNIT[lane] == float(getattr(ex, const)),
       f"{RR.LANE_UNIT.get(lane)} vs {getattr(ex, const, None)}")

for pre in ex.LANE_PREFIXES:
    head = pre.rstrip("|")
    if head == "lane2":
        continue
    ok(f"the key prefix {head!r} resolves to a unit",
       RR.LANE_UNIT.get(RR.PREFIX_LANE.get(head)) is not None, str(RR.PREFIX_LANE.get(head)))

u = RR.lane_unit({"key": "dogs|NFL|A @ B|side|A"})
ok("a dogs key now resolves to the $300 unit", u[:2] == ("dogs", 300.0), str(u))
ok("and so does a dogs-sourced row with no prefix",
   RR.lane_unit({"key": "NFL|A @ B|side|A", "source": "dogs"})[:2] == ("dogs", 300.0))
ok("a $100 dog is a FULL unit, not half of one",
   abs(RR.lane_unit({"key": "dogs|NFL|A @ B|side|A"})[1] - ex.DOGS_UNIT) < 1e-9)

ok("LANE 2 is deliberately absent - dry-run only, so it fails closed",
   "lane2" not in RR.LANE_UNIT and RR.lane_unit({"key": "lane2|NFL|A @ B|side|A"})[1] is None)
ok("an unknown lane still fails closed rather than defaulting",
   RR.lane_unit({"key": "newlane|NFL|A @ B|side|A"})[1] is None
   and RR.lane_unit({"key": "NFL|A @ B|side|A", "source": "muse"})[1] is None)

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
