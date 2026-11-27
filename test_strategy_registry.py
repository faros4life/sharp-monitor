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

# ---- 2. THE GATE.
# Nov 27 (Peter): "Fix the completeness gate so an enabled strategy cannot bypass integration requirements
# simply because it has no fills. Verify the actual live-switch configuration. Keep NCS disabled; defer its
# remaining integration work."
#
# The bypass this removes: the gate used to require completeness only for a lane that was switched on OR
# appeared in the hand-written HAS_LIVE_RECORD list below. Both halves failed for the case that matters.
# switched_on() read an unset variable as "off", so in a job that is passed no EXEC_*_LIVE variables EVERY
# lane looked off - and a brand-new lane that Peter had switched on but which had not filled yet is in no
# hand-written list either. So a lane could be enabled, incomplete, and silently skipped. That is the DOGS
# case exactly: switched on 23 Nov, zero fills, invisible to every report for four days.
#
# The rule now: a lane must be complete unless its switch is EXPLICITLY off. Unknown counts as live and
# fails closed, so a job that cannot see the configuration cannot wave a lane through. "No fills" is no
# longer a reason for anything - it is not consulted.
#
# A live record still forces completeness on top of that, for a lane deliberately switched off that has
# already placed real orders (R1, paused 23 Nov) - its history still has to be graded and reported.
#
# One more distinction, so this is enforceable rather than merely strict. A job that is passed NO switch
# variables at all (a local run, run_tests.py, any other workflow) cannot verify the configuration, and
# failing there would paint every suite red for something that is not a defect. A job passed SOME of them
# has had one dropped, which IS a defect and fails closed per lane. So:
#   - some switches visible -> every unknown fails closed as live
#   - none visible          -> this run cannot verify; say so, enforce the live-record rule, and instead
#                             assert statically that the authoritative workflow passes all five.
# The static check below is what keeps the bypass shut everywhere, including here.
HAS_LIVE_RECORD = ("rules", "r1", "board", "dogs")
_STATES = {ln: SR.switch_state(ln) for ln in SR.LIVE_LANES}
_ANY_VISIBLE = any(v != "unknown" for v in _STATES.values())
if not _ANY_VISIBLE:
    print("NOTE  no EXEC_*_LIVE variable reached this job, so the live configuration is NOT verified here."
          " The strategy-completeness workflow passes them; the static check below asserts that it does.")

_WF = open(".github/workflows/strategy-completeness.yml", encoding="utf-8").read()
for lane, (_const, _switch) in sorted(SR.LIVE_LANES.items()):
    ok(f"the completeness workflow passes {_switch} to the gate",
       f"{_switch}: ${{{{ vars.{_switch} }}}}" in _WF,
       "not in strategy-completeness.yml env - that job cannot see this lane's real switch")

for lane in sorted(SR.LIVE_LANES):
    state, rec = _STATES[lane], lane in HAS_LIVE_RECORD
    if state == "unknown" and not _ANY_VISIBLE:
        state = "off"          # unverifiable here; the static check above carries the enforcement
    m = SR.missing(lane)
    if state != "off" or rec:
        why = ("is switched on" if state == "on" else
               "has an UNREADABLE switch, which fails closed as live" if state == "unknown" else
               "has a live record")
        ok(f"{lane} {why}, so every required integration is present",
           not m, "; ".join(f"{k} ({x})" for k, _d, x in m))
    else:
        print(f"DEFERRED  {lane} is explicitly switched off and has no live record"
              + (f" - {len(m)} integration(s) still missing: " + ", ".join(k for k, _d, _x in m) if m
                 else " - complete"))
        ok(f"{lane} is correctly reported as NOT ready to go live", not SR.live_ready(lane)[0] or not m)

# ---- 2b. the gate's own teeth, proved rather than assumed: an enabled incomplete lane must FAIL, and an
# unreadable switch must behave like enabled. Asserted against a synthetic lane so it holds for the NEXT
# trigger, not just today's five. These are the two properties Peter asked for.
import os as _os


def _demands_completeness(value):
    """Would the gate demand completeness for a lane whose switch reads `value`? (value None = unset)"""
    _sw = "EXEC_GATEPROBE_LIVE"
    _prev = _os.environ.get(_sw)
    SR.LIVE_LANES["_gateprobe"] = ("GATEPROBE_UNIT", _sw)
    try:
        if value is None:
            _os.environ.pop(_sw, None)
        else:
            _os.environ[_sw] = value
        return SR.switch_state("_gateprobe") != "off"
    finally:
        SR.LIVE_LANES.pop("_gateprobe", None)
        _os.environ.pop(_sw, None)
        if _prev is not None:
            _os.environ[_sw] = _prev


ok("an ENABLED lane is held to completeness whatever its fill count", _demands_completeness("on"))
ok("an UNSET switch fails closed as live, never as off", _demands_completeness(None))
ok("an EMPTY switch (missing repo variable) fails closed as live", _demands_completeness(""))
ok("an UNRECOGNISED switch value fails closed as live", _demands_completeness("maybe"))
ok("only an EXPLICIT off defers a lane", not _demands_completeness("off"))
ok("and 'false' is an explicit off too", not _demands_completeness("false"))

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
