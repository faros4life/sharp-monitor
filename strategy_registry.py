#!/usr/bin/env python3
"""THE SHARED STRATEGY REGISTRY - one authoritative list of live triggers, and what each must be wired into.

Peter, 27 Nov 2026: "Make complete trigger integration a mandatory requirement for every new strategy going
forward... Use a shared authoritative strategy registry wherever practical. Automated completeness tests must
prevent a new trigger from going live if any required integration is missing."

WHY THIS EXISTS. DOGS went live on 23 Nov and placed nothing for four days while being invisible to every
report, because each reporting module kept a PRIVATE COPY of a four-lane list written before DOGS and NCS
existed. Two guards already existed and both did their job inside their own scope - test_lane_units_complete.py
for the exposure units, registry.LANE_PREFIX for attribution - but nothing asked the one question that matters:
is this lane wired into EVERYTHING before its switch can be flipped?

WHAT IS AUTHORITATIVE. The executor, and only the executor:
    executor.LANE_NAME       source -> display label (the set of lanes that exist)
    executor.LANE_PREFIXES   the play_key prefix each lane stamps
    executor.<LANE>_UNIT     the lane's unit
    EXEC_<LANE>_LIVE         the money switch Peter flips
This module never defines a lane. It reads the executor and checks that everything else agrees. If a name here
and a name in the executor disagree, the executor wins and the other module gets corrected - the same rule
REGISTRY.md already applies to the registry of tests.

HOW TO USE IT. `missing(lane)` returns the unmet requirements for one lane; `report()` returns them for every
lane. test_strategy_registry.py fails when a lane whose switch is ON has any unmet requirement, and the
strategy-completeness workflow runs that test on every push, so an incomplete lane cannot reach main switched on.

READ-ONLY. Nothing here places, sizes, routes, grades, promotes or kills anything. It imports the modules it
checks and inspects their constants; it changes none of them.
"""
import os

# Every lane the executor can place live money with: source -> (unit constant, money switch).
# The list is asserted against executor.LANE_NAME, so a new lane fails the test until it is added here too.
LIVE_LANES = {
    "rules": ("LIVE_UNIT", "EXEC_LIVE"),
    "board": ("BOARD_UNIT", "EXEC_BOARD_LIVE"),
    "r1": ("R1_UNIT", "EXEC_R1_LIVE"),
    "ncs": ("NCS_UNIT", "EXEC_NCS_LIVE"),
    "dogs": ("DOGS_UNIT", "EXEC_DOGS_LIVE"),
    # Nov 28: ALL-3 (NFL 12K all-three-books ML trigger, spread play, 12-24h first print). Ships OFF
    # - EXEC_ALL3_LIVE is unset - and its base 12K trigger is still unconfirmed, so it selects
    # nothing. It is registered here anyway: a live lane missing from this registry is absent from
    # the scorecard and the unit schedule, which is how a lane goes live unwatched.
    "all3": ("ALL3_UNIT", "EXEC_ALL3_LIVE"),
}
# Dry-run only, deliberately not live: it must NOT appear in the live scorecard or the unit schedule.
PAPER_LANES = ("lane2",)


def _ex():
    import executor
    return executor


def label(lane):
    """The lane's display label, from the executor. None for a lane the executor does not name."""
    return _ex().LANE_NAME.get(lane)


def switch_state(lane):
    """"on" | "off" | "unknown" - the lane's ACTUAL money-switch configuration in this environment.

    Nov 27 (Peter): "Fix the completeness gate so an enabled strategy cannot bypass integration
    requirements simply because it has no fills. Verify the actual live-switch configuration."

    The distinction between off and unknown is the whole point and must not be collapsed. This used to
    read `os.environ.get(sw) or "off"`, so a variable that was never passed to the job was indistinguishable
    from one Peter had deliberately switched off - and the gate ran every lane as "off", printing `switch off`
    for LANE 1 and BOARD V4 while both were live. That is fail-OPEN on a safety gate: an enabled, incomplete
    lane read as off and was skipped.

    UNSET is therefore "unknown", never "off", and the caller fails closed on it. An EMPTY value is also
    unknown: GitHub renders a missing repository variable as the empty string, so `EXEC_X_LIVE: ''` means the
    variable does not exist, not that it is off. Only an explicit word decides.
    """
    sw = (LIVE_LANES.get(lane) or (None, None))[1]
    if not sw:
        return "unknown"
    raw = os.environ.get(sw)
    if raw is None or not raw.strip():
        return "unknown"
    v = raw.strip().lower()
    if v in ("on", "1", "true", "yes"):
        return "on"
    if v in ("off", "0", "false", "no"):
        return "off"
    return "unknown"                       # an unrecognised value is not evidence of off


def switched_on(lane):
    """True only when the switch is explicitly on. Use switch_state() where unknown must fail closed."""
    return switch_state(lane) == "on"


# ---------------------------------------------------------------- the required integrations
# Peter's list of 27 Nov, in his order. Each entry: (key, one-line description, checker).
# A checker takes the lane source ("dogs") and returns (ok, detail). It must never raise: an import
# failure is an UNMET requirement, not a crash, because a missing module is exactly the gap being looked for.

def _safe(fn):
    def run(lane):
        try:
            return fn(lane)
        except Exception as ex:
            return False, f"{type(ex).__name__}: {str(ex)[:70]}"
    return run


@_safe
def _registry_and_scorecard(lane):
    import registry_export as RE
    md = open("SCORECARD.md", encoding="utf-8").read() + open("REGISTRY.md", encoding="utf-8").read()
    name = label(lane) or ""
    ok = lane in RE.LANES and (name.lower() in md.lower() or lane.lower() in md.lower())
    return ok, f"registry_export.LANES={lane in RE.LANES}, named in SCORECARD/REGISTRY={name.lower() in md.lower() or lane.lower() in md.lower()}"


@_safe
def _attribution(lane):
    import registry as RG
    return lane in set(RG.LANE_PREFIX.values()), f"registry.LANE_PREFIX values={sorted(set(RG.LANE_PREFIX.values()))}"


@_safe
def _key_prefix(lane):
    ex = _ex()
    import live_ledger as LL
    pre = lane + "|"
    stamped = pre in ex.LANE_PREFIXES
    stripped = LL.strip_key(pre + "NFL|A @ B|side|A") == "NFL|A @ B|side|A"
    return (not stamped) or stripped, f"executor stamps {pre!r}={stamped}, live_ledger strips it={stripped}"


@_safe
def _ledger_label(lane):
    import live_ledger as LL
    import bot_live_export as BLE
    name = LL.LANES.get(lane)
    return bool(name) and name in BLE.LANES, f"live_ledger={name!r}, bot_live_export knows it={name in BLE.LANES}"


@_safe
def _unit_sizing(lane):
    ex, const = _ex(), LIVE_LANES[lane][0]
    import review_replay as RR
    rl = RR.SOURCE_LANE.get(lane)
    u = RR.LANE_UNIT.get(rl)
    want = float(getattr(ex, const))
    return u is not None and abs(u - want) < 1e-9, f"review_replay unit={u}, executor.{const}={want}"


@_safe
def _unit_history(lane):
    import p2_audit_core as PC
    name = label(lane)
    h = PC.unit_history(name)
    return bool(h), f"p2_audit_core.unit_history({name!r})={h}"


@_safe
def _exposure_ledger(lane):
    import review_replay as RR
    k = RR.lane_unit({"key": lane + "|NFL|A @ B|side|A"})
    k2 = RR.lane_unit({"key": "NFL|A @ B|side|A", "source": lane})
    return k[1] is not None and k2[1] is not None, f"by prefix={k[:2]}, by source={k2[:2]}"


@_safe
def _risk_caps(lane):
    src = open("executor.py", encoding="utf-8").read()
    up = lane.upper()
    # Lane 1 has no lane-specific cap by design: it runs under the global stop alone (px_live.DAILY_STOP).
    cap = f"EXEC_{up}_DAILY_RISK" in src or lane == "rules"
    plays = f"EXEC_{up}_MAX_PLAYS" in src or lane == "rules"
    import px_live
    stop = float(getattr(px_live, "DAILY_STOP", 0) or 0) > 0
    return cap and plays and stop, f"daily risk={cap}, play cap={plays}, global stop={stop}"


@_safe
def _reconciliation(lane):
    src = open("reconcile_live.py", encoding="utf-8").read()
    name = (label(lane) or "").lower()
    return name in src.lower() or lane in src, f"named in reconcile_live.py"


@_safe
def _clv_and_halves(lane):
    import report_sections as RS
    name = label(lane)
    return name in RS.LANES_LIVE, f"report_sections.LANES_LIVE={RS.LANES_LIVE}"


@_safe
def _windows(lane):
    src = open("last50_report.py", encoding="utf-8").read()
    return (label(lane) or "\0") in src, "named in last50_report.py (all-time / last-50 / last-20)"


@_safe
def _dashboard_and_reports(lane):
    name = label(lane) or "\0"
    hits = [f for f in ("clv_dashboard.py", "report_sections.py", "executed_clv.py")
            if name in open(f, encoding="utf-8").read()]
    return bool(hits), f"named in {hits or 'none of clv_dashboard / report_sections / executed_clv'}"


REQUIRED = (
    ("strategy_registry", "named in the strategy registry and the scorecard", _registry_and_scorecard),
    ("order_attribution", "an order row resolves to this lane (registry.LANE_PREFIX)", _attribution),
    ("key_prefix", "its play_key prefix is stripped wherever keys are compared", _key_prefix),
    ("ledger_label", "the live ledger and the tracker page both label it", _ledger_label),
    ("unit_sizing", "the exposure ledger knows its unit and agrees with the executor", _unit_sizing),
    ("unit_history", "its historical unit schedule is recorded with effective dates", _unit_history),
    ("exposure_ledger", "duplicate protection resolves it by prefix AND by source", _exposure_ledger),
    ("risk_caps", "its own daily risk cap and play cap exist, under the global stop", _risk_caps),
    ("reconciliation", "fill and settlement reconciliation covers it", _reconciliation),
    ("clv_and_halves", "certified CLV, beat-close, halves and intervals are computed for it", _clv_and_halves),
    ("windows", "all-time, last-50 and last-20 reporting include it", _windows),
    ("dashboard_and_reports", "the dashboard and the daily reports name it", _dashboard_and_reports),
)


def missing(lane):
    """[(key, description, detail)] - the required integrations this lane does NOT have."""
    out = []
    for key, desc, check in REQUIRED:
        ok, detail = check(lane)
        if not ok:
            out.append((key, desc, detail))
    return out


def report():
    """{lane: {"label":, "on":, "missing": [...]}} for every live lane the executor names."""
    return {ln: {"label": label(ln), "on": switched_on(ln), "state": switch_state(ln),
                 "missing": missing(ln)} for ln in sorted(LIVE_LANES)}


def live_ready(lane):
    """(ok, [reasons]) - whether this lane is wired into everything a live trigger must be wired into.
    NOT CONSULTED BY THE EXECUTOR. Peter approved the requirement on 27 Nov; wiring a refusal into the
    order path is a live change and waits for his separate go."""
    m = missing(lane)
    return (not m), [f"{k}: {d} ({x})" for k, d, x in m]


if __name__ == "__main__":
    _st = {"on": "ON     ", "off": "off    ", "unknown": "UNKNOWN"}
    _unk = [ln for ln, r in report().items() if r["state"] == "unknown"]
    for ln, r in report().items():
        print(f"{ln:7} {str(r['label']):9} switch {_st[r['state']]} "
              f"{'COMPLETE' if not r['missing'] else str(len(r['missing'])) + ' MISSING'}")
        for k, d, x in r["missing"]:
            print(f"          - {k}: {d}\n            {x}")
    if _unk:
        print(f"\n  SWITCH CONFIGURATION NOT VISIBLE for {len(_unk)} lane(s): {', '.join(sorted(_unk))}.")
        print("  The job was not given those EXEC_*_LIVE repository variables, so this report cannot say")
        print("  whether they are live. The gate treats unknown as live and fails closed; it is never read")
        print("  as 'off'. Pass the variables in the workflow env to see the real configuration.")
