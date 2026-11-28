#!/usr/bin/env python3
"""A play charges its lane as soon as it is placed, so the next play in the SAME pass is gated truly.

Peter, 27 Nov: "Fix in-run accumulation of daily exposure and unique plays... verify that filled,
pending, partially filled and resting orders all consume the applicable daily capacity. Multiple
submissions in the same run must not exceed the daily risk cap or unique-play maximum. Count multiple
legs on the same play as one unique play, while accounting for their combined exposure."

MEASURED GAP: BOARD["risk"] += and BOARD["keys"].add appear ONLY inside _account_rows(), the run-start
ledger read. Nothing updated them after a placement, so every play in a pass was gated against the same
baseline. With a $2,000 cap, $1,700 already at risk and two $200 plays, each gate saw 1700+200 <= 2000
and allowed it - the day ended at $2,100. The play maximum had the same hole: at 9 of 10, two new plays
each computed 10 <= 10 and both passed.

The catch-up passes are separate processes (the workflow shell loops `python -u executor.py`), so module
state starts fresh per pass and there is no cross-pass double count. Asserted below, because "reset the
state" would have been the wrong fix and would have hidden this one.
"""
import executor as ex


def leg(status="placed", asked=200.0, filled=None):
    return {"status": status, "asked_stake": asked, "filled_stake": filled, "book": "novig"}


def play(src="board", key="NCAAF|A @ B|spread|A"):
    return {"source": src, "play_key": f"{src}|{key}", "sport": "NCAAF",
            "game": "A @ B", "bet": "A -7.5 (-110)"}


def with_state(attr, state, fn):
    prev = dict(getattr(ex, attr))
    try:
        getattr(ex, attr).clear()
        getattr(ex, attr).update(state)
        return fn()
    finally:
        getattr(ex, attr).clear()
        getattr(ex, attr).update(prev)


def fresh():
    """A brand-new lane state. NOT fresh(): that shallow-copies, so every caller would share one
    `keys` set and plays charged in one section would leak into the next - which is exactly what the
    first run of this file did, and it looked like a defect in lane_consume.
    """
    return {"risk": 0.0, "keys": set(), "known": True}


def check(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    return bool(cond)


def main():
    ok = True

    print("1. A PLACEMENT CHARGES THE LANE IMMEDIATELY")

    def t1():
        amt = ex.lane_consume(play(), {"live": {"order": leg(filled=180.0)}})
        return amt, dict(ex.BOARD)
    amt, st = with_state("BOARD", fresh(), t1)
    ok &= check("a filled take charges its fill", amt == 180.0, amt)
    ok &= check("  and the lane risk reflects it", st["risk"] == 180.0, st["risk"])
    ok &= check("  and it consumes exactly one play slot", len(st["keys"]) == 1, st["keys"])

    print("\n2. EVERY LEG KIND CONSUMES CAPACITY")
    cases = [("a known fill", {"order": leg(filled=120.0)}, 120.0),
             ("a pending/unknown take (reserves the ask)", {"order": leg(filled=None)}, 200.0),
             ("a resting bid (reserves the ask)", {"rest": leg(filled=None)}, 200.0),
             ("a PARTIALLY filled resting bid (still reserves the full ask)",
              {"rest": leg(asked=200.0, filled=50.0)}, 200.0),
             ("a partially filled take", {"order": leg(asked=200.0, filled=75.0)}, 75.0)]
    for label, live, want in cases:
        got = with_state("BOARD", fresh(), lambda: ex.lane_consume(play(), {"live": live}))
        ok &= check(f"{label} charges ${want}", got == want, got)

    print("\n3. MULTIPLE LEGS ON ONE PLAY = ONE UNIQUE PLAY, COMBINED EXPOSURE")

    def t3():
        amt = ex.lane_consume(play(), {"live": {"order": leg(filled=80.0),
                                                "more": [leg(filled=60.0)],
                                                "rest": leg(asked=60.0, filled=None)}})
        return amt, dict(ex.BOARD)
    amt, st = with_state("BOARD", fresh(), t3)
    ok &= check("three legs charge their combined exposure", amt == 200.0, amt)
    ok &= check("  but consume ONE play slot, not three", len(st["keys"]) == 1, st["keys"])

    print("\n4. THE ACTUAL BUG: TWO PLAYS IN ONE PASS CANNOT BOTH FIT THE LAST SLOT OF BUDGET")
    # $2,000 cap, $1,700 already at risk, two $200 plays. Before this change both passed the gate.
    def t4():
        ex.BOARD.update(risk=ex.BOARD_DAILY_RISK - 300.0, keys=set(), known=True)
        ok1, why1 = ex.board_gate(200.0, "k1")
        ex.lane_consume(play(key="G1|spread|A"), {"live": {"order": leg(asked=200.0, filled=200.0)}})
        ok2, why2 = ex.board_gate(200.0, "k2")
        return ok1, ok2, why2, ex.BOARD["risk"]
    ok1, ok2, why2, risk = with_state("BOARD", fresh(), t4)
    ok &= check("the first $200 play is allowed", ok1)
    ok &= check("the SECOND $200 play is now REFUSED (was allowed before this change)", not ok2, why2)
    ok &= check("  because the first play's money is already charged",
                risk == ex.BOARD_DAILY_RISK - 100.0, risk)

    print("\n5. THE PLAY MAXIMUM ALSO BINDS WITHIN ONE PASS")

    def t5():
        ex.BOARD.update(risk=0.0, keys={f"k{i}" for i in range(ex.BOARD_MAX_PLAYS - 1)}, known=True)
        ok1, _ = ex.board_gate(10.0, "new1")
        ex.lane_consume(play(key="G9|spread|A"), {"live": {"order": leg(asked=10.0, filled=10.0)}})
        ok2, why2 = ex.board_gate(10.0, "new2")
        return ok1, ok2, why2
    ok1, ok2, why2 = with_state("BOARD", fresh(), t5)
    ok &= check(f"at {ex.BOARD_MAX_PLAYS - 1} plays the next one is allowed", ok1)
    ok &= check("after it is charged, a DIFFERENT new play is refused", not ok2, why2)

    print("\n6. NOTHING PLACED CHARGES NOTHING AND CONSUMES NO SLOT")
    for label, live in (("a refused order", {"order": leg(status="refused")}),
                        ("an empty live block", {}),
                        ("a None order", {"order": None})):
        def t6():
            amt = ex.lane_consume(play(), {"live": live})
            return amt, dict(ex.BOARD)
        amt, st = with_state("BOARD", fresh(), t6)
        ok &= check(f"{label}: charges nothing", amt == 0.0, amt)
        ok &= check(f"{label}: consumes no play slot", len(st["keys"]) == 0, st["keys"])

    print("\n7. THE KEY FORM MATCHES THE LEDGER'S, SO A PLAY IS NOT COUNTED TWICE")

    def t7():
        p = play()
        ex.lane_consume(p, {"live": {"order": leg(filled=10.0)}})
        return set(ex.BOARD["keys"]), (ex.derive_key(p) or p["play_key"])
    keys, want = with_state("BOARD", fresh(), t7)
    ok &= check("the charged key is derive_key(p), the form the gates and the ledger use",
                keys == {want}, keys)
    ok &= check("  and it carries NO lane prefix", not list(keys)[0].startswith("board|"), keys)

    print("\n8. LANES WITHOUT A CAP, AND UNPROVEN LANES, CHARGE NOTHING")
    ok &= check("Lane 1 (rules) charges nothing - it has no lane cap",
                ex.lane_consume(play(src="rules"), {"live": {"order": leg(filled=99.0)}}) == 0.0)
    ok &= check("an unknown lane charges nothing",
                ex.lane_consume({"source": "muse", "play_key": "muse|X"},
                                {"live": {"order": leg(filled=99.0)}}) == 0.0)
    ok &= check("a play whose prefix and source DISAGREE charges nothing",
                ex.lane_consume({"source": "board", "play_key": "r1|X|spread|A"},
                                {"live": {"order": leg(filled=99.0)}}) == 0.0)

    print("\n9. THE CATCH-UP PASSES ARE SEPARATE PROCESSES (so no cross-pass double count to fix)")
    wf = open(".github/workflows/executor-dry-run.yml", encoding="utf-8").read()
    ok &= check("the pass loop is in the workflow shell, not in Python",
                "pass(es)" in wf and "python -u executor.py" in wf)
    src = open("executor.py", encoding="utf-8").read()
    ok &= check("and bot_orders does NOT reset the lane dicts (it does not need to)",
                "BOARD.update(" not in src.split("def bot_orders")[1][:600])

    print("\nALL PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
