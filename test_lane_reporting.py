#!/usr/bin/env python3
"""Every lane that can place live money must be nameable by every REPORTING path.

Nov 27 (Peter: "confirming actual Dogs fills, realized P&L and exposure"): DOGS had been placing real
money since 23 Nov and appeared in none of the live-fill reports. Nothing was wrong with its selection,
its unit reservation or its orders - test_lane_units_complete.py already guards those. The lane maps in
the REPORTING modules were each a private copy of a four-lane list written before DOGS and NCS existed:

  live_ledger.PREFIX      strip_key() left "dogs|" on the play key, so the grouping split read
                          lg="dogs", game="SPORT", mk="game" and every tracker / CLV / result join missed
  live_ledger.LANES       lane printed as raw "dogs"; E2 registry-evidenced Dogs fills were skipped
  bot_live_export.LANES   Dogs plays filed under "Unattributed" on the tracker page
  registry_export.LANES   lane_map and live_strategy_keys never named Dogs
  report_sections.LANES_LIVE   Section H's lane scorecard never graded Dogs
  p2_audit_core.UNIT_SCHEDULE  no Dogs unit, so its ROI could not be computed even once attributed

executor.LANE_NAME and executor.LANE_PREFIXES are the authority for the set. This test asserts the
reporting maps agree with them, so the next lane cannot go live invisible. It reads source; it places
nothing, grades nothing and changes no bar.
"""
import executor as ex
import live_ledger as LL
import bot_live_export as BLE
import registry_export as RE
import report_sections as RS
import p2_audit_core as PC

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


SRC = open("executor.py", encoding="utf-8").read()

# A lane can place live money when the executor gives it both a unit constant and a money switch.
LIVE = {"rules": ("LIVE_UNIT", "EXEC_LIVE"), "board": ("BOARD_UNIT", "EXEC_BOARD_LIVE"),
        "r1": ("R1_UNIT", "EXEC_R1_LIVE"), "ncs": ("NCS_UNIT", "EXEC_NCS_LIVE"),
        "dogs": ("DOGS_UNIT", "EXEC_DOGS_LIVE"),
              "all3": ("ALL3_UNIT", "EXEC_ALL3_LIVE")}   # Nov 28: ALL-3, ships off

ok("the live-lane list still matches the lanes executor names",
   set(LIVE) | {"lane2"} == set(ex.LANE_NAME), sorted(set(ex.LANE_NAME)))
for src, (const, switch) in sorted(LIVE.items()):
    ok(f"{src}: executor defines {const} and the {switch} switch",
       hasattr(ex, const) and switch in SRC)

# ---- 1. the ledger can strip every lane's key prefix.
# This is the one that lost the data: an unstripped prefix shifts every field of the key.
for pre in ex.LANE_PREFIXES:
    head = pre.rstrip("|")
    ok(f"live_ledger.strip_key strips {head!r}", head in LL.PREFIX, str(LL.PREFIX))
k = "dogs|NFL|A @ B|side|A"
ok("a dogs play key strips to the same shape as every other lane's",
   LL.strip_key(k) == "NFL|A @ B|side|A", LL.strip_key(k))
ok("and the stripped key still splits into league, game, market, side",
   len(LL.strip_key(k).split("|")) == 4, LL.strip_key(k))

# ---- 2. every live lane has a display label in each reporting map.
for src in sorted(LIVE):
    ok(f"live_ledger.LANES labels {src!r}", src in LL.LANES, sorted(LL.LANES))
    ok(f"registry_export.LANES labels {src!r}", src in RE.LANES, sorted(RE.LANES))
for src in sorted(LIVE):
    label = LL.LANES.get(src)
    ok(f"bot_live_export.LANES knows the ledger label {label!r} for {src!r}",
       label in BLE.LANES, sorted(BLE.LANES))

# ---- 3. a lane that is currently switched on must be graded and must have a unit.
ON = [s for s, (_c, sw) in sorted(LIVE.items())
      if (__import__("os").environ.get(sw) or "off").strip().lower() == "on"]
for src in ON:   # empty in CI, where no switch is set; the assertions below carry the standing cases
    label = LL.LANES.get(src)
    ok(f"{src} is switched on, so Section H grades {label!r}", label in RS.LANES_LIVE, str(RS.LANES_LIVE))
    ok(f"{src} is switched on, so it has a reporting unit", label in PC.UNIT_SCHEDULE, sorted(PC.UNIT_SCHEDULE))

for label in ("LANE 1", "R1", "BOARD V4", "DOGS"):   # the four with a live record as of 27 Nov
    ok(f"Section H grades {label}", label in RS.LANES_LIVE, str(RS.LANES_LIVE))
    ok(f"{label} has a verified reporting unit", label in PC.UNIT_SCHEDULE, sorted(PC.UNIT_SCHEDULE))

ok("the DOGS reporting unit equals executor.DOGS_UNIT",
   abs(PC.UNIT_SCHEDULE["DOGS"][1] - float(ex.DOGS_UNIT)) < 1e-9,
   f"{PC.UNIT_SCHEDULE['DOGS'][1]} vs {ex.DOGS_UNIT}")
ok("the DOGS unit is dated from the 25 Nov spec change, not the $100 pilot",
   PC.UNIT_SCHEDULE["DOGS"][0].startswith("2026-11-25"), PC.UNIT_SCHEDULE["DOGS"][0])

# ---- 4. nothing above may invent a lane. An unknown source still resolves to nothing.
ok("an unknown lane prefix is still not stripped", LL.strip_key("newlane|NFL|A @ B|side|A")
   == "newlane|NFL|A @ B|side|A", LL.strip_key("newlane|NFL|A @ B|side|A"))
ok("an unknown lane has no label", LL.LANES.get("newlane") is None and RE.LANES.get("newlane") is None)
ok("LANE 2 is still absent from the live scorecard - dry-run only",
   "LANE 2" not in RS.LANES_LIVE and "LANE 2" not in PC.UNIT_SCHEDULE)

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
