#!/usr/bin/env python3
"""COMPLETENESS GATE: a trigger may not be live unless it is wired into everything a live trigger needs.

Peter, 27 Nov 2026, after DOGS spent four days live and invisible: "Make complete trigger integration a
mandatory requirement for every new strategy going forward... Automated completeness tests must prevent a new
trigger from going live if any required integration is missing."

This test FAILS when a lane is switched on, or already has a live record, and strategy_registry.missing()
returns anything. A lane that is switched OFF and has no live record is reported but does not fail - it is not
yet a live trigger, and flipping its switch is what makes this test block it.

The strategy-completeness workflow runs this on every push, so an incomplete lane cannot reach main switched on.
Read-only: nothing here places, sizes, grades or kills anything.
"""
import os

import executor as ex
import strategy_registry as SR
import p2_audit_core as PC
import report_sections as RS

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


# ---- 1. the registry is the executor's list, not a second opinion.
ok("the registry's lanes are exactly the lanes the executor names",
   set(SR.LIVE_LANES) | set(SR.PAPER_LANES) == set(ex.LANE_NAME),
   sorted(set(ex.LANE_NAME) ^ (set(SR.LIVE_LANES) | set(SR.PAPER_LANES))))
for lane, (const, switch) in sorted(SR.LIVE_LANES.items()):
    ok(f"{lane}: the executor defines {const}", hasattr(ex, const))
    ok(f"{lane}: the executor has a {switch} switch", switch in open("executor.py", encoding="utf-8").read())
    ok(f"{lane}: the registry gives it the executor's label", SR.label(lane) == ex.LANE_NAME.get(lane))

# ---- 2. THE GATE. A lane that is live, or has a live record, must have no missing integration.
# LANE 1, R1, BOARD V4 and DOGS have placed real orders or been switched on; NCS never has.
HAS_LIVE_RECORD = ("rules", "r1", "board", "dogs")
for lane in sorted(SR.LIVE_LANES):
    on, rec = SR.switched_on(lane), lane in HAS_LIVE_RECORD
    m = SR.missing(lane)
    if on or rec:
        why = "is switched on" if on else "has a live record"
        ok(f"{lane} {why}, so every required integration is present",
           not m, "; ".join(f"{k} ({x})" for k, _d, x in m))
    else:
        print(f"SKIP  {lane} is not live and has no live record - {len(m)} integration(s) still missing"
              + (": " + ", ".join(k for k, _d, _x in m) if m else ""))
        ok(f"{lane} is correctly reported as NOT ready to go live", not SR.live_ready(lane)[0] or not m)

# ---- 3. the paper lane must stay out of the live scorecard and the unit schedule.
for lane in SR.PAPER_LANES:
    name = ex.LANE_NAME.get(lane)
    ok(f"{name} is absent from the live scorecard", name not in RS.LANES_LIVE, str(RS.LANES_LIVE))
    ok(f"{name} has no reporting unit", name not in PC.UNIT_SCHEDULE, sorted(PC.UNIT_SCHEDULE))

# ---- 4. historical units: both of Dogs' approved units, each from its own verified date.
h = PC.unit_history("DOGS")
ok("DOGS records two units", len(h) == 2, str(h))
ok("the $100 pilot unit is preserved, dated 23 Nov",
   h and h[0][1] == 100.0 and h[0][0].startswith("2026-11-23"), str(h))
ok("the $300 unit is recorded from the 25 Nov spec change",
   len(h) == 2 and h[1][1] == 300.0 and h[1][0].startswith("2026-11-25"), str(h))
ok("the current DOGS unit equals executor.DOGS_UNIT",
   abs(PC.UNIT_SCHEDULE["DOGS"][1] - float(ex.DOGS_UNIT)) < 1e-9,
   f"{PC.UNIT_SCHEDULE['DOGS'][1]} vs {ex.DOGS_UNIT}")
ok("a 24 Nov Dogs play is valued at $100", PC.unit_at("DOGS", "2026-11-24T20:00:00+00:00") == 100.0,
   str(PC.unit_at("DOGS", "2026-11-24T20:00:00+00:00")))
ok("a 26 Nov Dogs play is valued at $300", PC.unit_at("DOGS", "2026-11-26T20:00:00+00:00") == 300.0,
   str(PC.unit_at("DOGS", "2026-11-26T20:00:00+00:00")))
ok("a play before the pilot started gets NO unit, never a guessed one",
   PC.unit_at("DOGS", "2026-11-20T20:00:00+00:00") is None)
ok("a segment straddling the $100 -> $300 change reports UNAVAILABLE",
   PC.units_for("EXACT:DOGS", ["2026-11-24T00:00:00+00:00", "2026-11-26T00:00:00+00:00"], 300.0) is None)
ok("a segment wholly inside the $300 era is valued at $300",
   PC.units_for("EXACT:DOGS", ["2026-11-26T00:00:00+00:00", "2026-11-27T00:00:00+00:00"], 300.0) == 1.0,
   str(PC.units_for("EXACT:DOGS", ["2026-11-26T00:00:00+00:00", "2026-11-27T00:00:00+00:00"], 300.0)))
ok("a segment wholly inside the $100 pilot is valued at $100",
   PC.units_for("EXACT:DOGS", ["2026-11-23T20:00:00+00:00", "2026-11-24T20:00:00+00:00"], 100.0) == 1.0,
   str(PC.units_for("EXACT:DOGS", ["2026-11-23T20:00:00+00:00", "2026-11-24T20:00:00+00:00"], 100.0)))
ok("the single-unit lanes are unchanged",
   PC.units_for("EXACT:LANE 1", ["2026-11-12T00:00:00+00:00", "x"], -300.0) == -1.0
   and PC.units_for("EXACT:LANE 1", ["2026-11-01T00:00:00+00:00", "x"], 300.0) is None)

# ---- 5. the registry invents nothing.
ok("an unknown lane has no label", SR.label("newlane") is None)
ok("an unknown lane is not ready to go live", not SR.live_ready("newlane")[0])
ok("report() covers every live lane", set(SR.report()) == set(SR.LIVE_LANES))

print(f"\n{len(P)} passed, {len(F)} failed")
if F:
    print("A lane cannot go live with a missing integration. Wire it in, or do not flip its switch.")
raise SystemExit(1 if F else 0)
