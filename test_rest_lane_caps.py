#!/usr/bin/env python3
"""Every lane's daily cap, play maximum and kill bar must bind on a RESTING bid, not just a take.

Peter, 27 Nov: "Complete resting-path risk enforcement across all applicable lanes."

MEASURED before this change: board_gate, r1_gate, ncs_gate and dogs_gate are each called at exactly ONE
site, and every one of those sites sits inside `if not why and r["verdict"] == "WOULD PLACE" and
r.get("lc")` - the TAKE branch, which requires a live candidate. rest_bid() is reached from a different
place, so no lane gate had ever been asked about a resting bid. executor.py's own note says it:
"There is ONE call site and it is not lane-gated."

What that dropped on every resting bid, per lane: the daily risk cap, the maximum plays, and - because
the kill check is the gate's first question - the kill bar. BOARD V4 is live and posts resting bids under
Peter's 11 Nov pilot rules, so its $2,000 cap and 10-play maximum were not binding there. The 27 Nov
audit found no actual breach (peak day $225.77 against $2,000), but an unenforced control is not a safe
control.

These tests drive the REAL rest_bid() with the venue stubbed, and assert on what reaches the venue -
because a gate being called is not the same as an order being stopped.
"""
import os
import types
from datetime import datetime, timedelta, timezone

import executor as ex

SUBMITTED = {}
KEY = "NCAAF|New Mexico Lobos @ Wyoming Cowboys|spread|New Mexico Lobos"


def run(play_key, source=None, lane_state=None, lane_attr=None, unit_price=-117, rest_risk=None,
        dogs_preconditions=False):
    """Drive production rest_bid(). Returns (result, dollars submitted or None, released claims).

    dogs_preconditions clears the kill bar, which fails closed on grading data it cannot read - correctly,
    in any test environment. It deliberately does NOT enable EXEC_UNIT_LEDGER: doing so engages
    review_unit_exposure, which raises without a real ledger. So a DOGS resting bid here always refuses,
    and the assertions below check WHICH gate refused it - a refusal naming dogs_gate's own ledger-mode
    requirement is itself proof that rest_bid consulted dogs_gate, which is the thing under test. The
    cap arithmetic is then asserted directly against dogs_gate, the same function rest_bid now calls.
    """
    SUBMITTED.clear()
    # Nov 27 (item 2): the lane caps now sum the registry SNAPSHOT with what this run has already
    # committed (executor.LANE_RUN), and journal_order commits on every successful post. This
    # harness pins the snapshot per case via lane_state, so it must pin the in-run tally too -
    # otherwise exposure from an earlier case in this process eats the headroom a later case sets
    # up, which is how section 4's $60 of headroom went missing. Resetting it keeps each case the
    # isolated scenario it was written as; the accumulation itself is asserted in
    # test_review_ledger_on_scenarios.py, where it is the subject rather than a side effect.
    for _l in ex.LANE_RUN:
        ex.LANE_RUN[_l] = {"risk": 0.0, "keys": set()}
    start = datetime.now(timezone.utc) + timedelta(hours=5)
    play = {"sport": "NCAAF", "game": "New Mexico Lobos @ Wyoming Cowboys",
            "bet": "New Mexico Lobos -7.5 (-117)", "play_key": play_key,
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")}
    if source is not None:
        play["source"] = source
    live = {"lane": "r1", "client_id": "this-run"}
    if rest_risk is not None:
        live["rest_risk"] = rest_risk
    ladder = {"status": "ok", "exact_line": True, "line": -7.5, "alert_line": -7.5,
              "outcome_id": "OC1", "buy_levels": [{"price": 0.50, "size": 100000}]}
    r = {"play": play, "entry": {"price_after_fee": unit_price}, "live": live,
         "reval": {"al": {"bet": play["bet"]}, "mtype": "spread", "side": "New Mexico Lobos",
                   "price": unit_price, "teams": ["New Mexico Lobos", "Wyoming Cowboys"], "line": -7.5},
         "books": {"novig": dict(ladder)}}

    released = []
    reg = types.SimpleNamespace(
        enabled=lambda: True, rows=lambda: [],
        submission_held=lambda k: None,
        claim_submission=lambda k, c: True,
        release_submission=lambda k, c: released.append((k, c)) or True)

    def fake_place(outcome_id, cost, qty, label, ms, key):
        SUBMITTED["dollars"] = round(qty / 100.0 * cost, 2)
        return {"status": "placed", "order_id": "N1", "book": "novig",
                "asked_stake": SUBMITTED["dollars"]}

    saved = (ex.registry, ex.REST_BOOKS, ex.book_live.novig_place, ex.live_guards, ex.rest_pre_alert,
             ex.journal_latch_why, ex.novig_grid_floor, ex.gmail, ex.send, ex.push, ex.tg_push,
             ex.reread_book)
    prev_state = dict(getattr(ex, lane_attr)) if lane_attr else None
    prev_kill = dict(ex.DOGS_KILL)
    prev_ul = os.environ.get("EXEC_UNIT_LEDGER")
    try:
        if dogs_preconditions:
            ex.DOGS_KILL["state"] = {"blocked": False}
        ex.gmail = lambda: ("u", "p", "t")
        ex.send = ex.push = ex.tg_push = lambda *a, **k: None
        ex.registry = reg
        ex.REST_BOOKS = ("novig",)
        ex.book_live.novig_place = fake_place
        ex.live_guards = lambda: (True, "")
        ex.rest_pre_alert = lambda *a, **k: None
        ex.journal_latch_why = lambda: None
        ex.novig_grid_floor = lambda p_star, levels: 0.50
        ex.reread_book = lambda b, ln, rv: dict(ladder) if b == "novig" else None
        if lane_attr:
            getattr(ex, lane_attr).update(lane_state or {})
        res = ex.rest_bid(r)
    finally:
        (ex.registry, ex.REST_BOOKS, ex.book_live.novig_place, ex.live_guards, ex.rest_pre_alert,
         ex.journal_latch_why, ex.novig_grid_floor, ex.gmail, ex.send, ex.push, ex.tg_push,
         ex.reread_book) = saved
        if lane_attr:
            getattr(ex, lane_attr).clear()
            getattr(ex, lane_attr).update(prev_state)
        ex.DOGS_KILL.clear()
        ex.DOGS_KILL.update(prev_kill)
        if prev_ul is None:
            os.environ.pop("EXEC_UNIT_LEDGER", None)
        else:
            os.environ["EXEC_UNIT_LEDGER"] = prev_ul
    return res, SUBMITTED.get("dollars"), released


def check(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    return bool(cond)


def main():
    ok = True
    OPEN = {"risk": 0.0, "keys": set(), "known": True}

    print("1. THE GATE IS CONSULTED AT ALL, PER LANE")
    for pk, attr, label in (("r1|" + KEY, "R1", "R1"), ("board|" + KEY, "BOARD", "BOARD V4"),
                            ("dogs|" + KEY, "DOGS", "DOGS")):
        res, got, _ = run(pk, lane_state=OPEN, lane_attr=attr, dogs_preconditions=(attr == "DOGS"))
        if attr == "DOGS":
            # cannot post in a test env (dogs_gate requires the shared unit ledger enforced), but that
            # refusal comes FROM dogs_gate, which proves rest_bid consulted it.
            ok &= check("DOGS: rest_bid consults dogs_gate (refusal is dogs_gate's own)",
                        got is None and "unit ledger" in str(res.get("reason", "")).lower(),
                        str(res.get("reason"))[:80])
        else:
            ok &= check(f"{label}: an in-budget resting bid still posts", got is not None, str(res)[:60])
        # the lane ledger not read this run -> the gate fails closed -> nothing is posted
        res, got, rel = run(pk, lane_state={"risk": 0.0, "keys": set(), "known": False}, lane_attr=attr)
        ok &= check(f"{label}: lane ledger UNREAD refuses and posts nothing",
                    got is None and res.get("status") == "refused", str(res)[:70])
        ok &= check(f"{label}: and the claim is released on that refusal", rel != [])

    print("\n2. THE DAILY RISK CAP BINDS ON A RESTING BID")
    res, got, rel = run("board|" + KEY, lane_state={"risk": ex.BOARD_DAILY_RISK, "keys": set(), "known": True},
                        lane_attr="BOARD")
    ok &= check("BOARD V4 at its daily cap refuses the bid", got is None
                and res.get("status") == "refused", str(res)[:70])
    ok &= check("  and the reason names the cap", "risk" in str(res.get("reason", "")).lower())
    ok &= check("  and the claim is released", rel != [])
    _pk, _pul = dict(ex.DOGS_KILL), os.environ.get("EXEC_UNIT_LEDGER")
    _pd = dict(ex.DOGS)
    try:
        ex.DOGS_KILL["state"] = {"blocked": False}
        os.environ["EXEC_UNIT_LEDGER"] = "on"
        ex.DOGS.update(risk=ex.DOGS_DAILY_RISK, keys=set(), known=True)
        dok, dwhy = ex.dogs_gate(100.0, "k")
        ok &= check("dogs_gate at its daily cap refuses", not dok and "risk" in dwhy.lower(), dwhy[:70])
        ex.DOGS.update(risk=0.0, keys={f"k{i}" for i in range(ex.DOGS_MAX_PLAYS)}, known=True)
        dok, dwhy = ex.dogs_gate(100.0, "new")
        ok &= check("dogs_gate at its play cap refuses", not dok and "play cap" in dwhy.lower(), dwhy[:70])
        ex.DOGS.update(risk=0.0, keys=set(), known=True)
        dok, dwhy = ex.dogs_gate(100.0, "k")
        ok &= check("dogs_gate in budget allows", dok, dwhy[:70])
    finally:
        ex.DOGS.clear(); ex.DOGS.update(_pd)
        ex.DOGS_KILL.clear(); ex.DOGS_KILL.update(_pk)
        if _pul is None: os.environ.pop("EXEC_UNIT_LEDGER", None)
        else: os.environ["EXEC_UNIT_LEDGER"] = _pul

    print("\n3. THE PLAY MAXIMUM BINDS ON A RESTING BID")
    full = {"risk": 0.0, "keys": {f"k{i}" for i in range(ex.BOARD_MAX_PLAYS)}, "known": True}
    res, got, _ = run("board|" + KEY, lane_state=full, lane_attr="BOARD")
    ok &= check(f"BOARD V4 with {ex.BOARD_MAX_PLAYS} plays today refuses a new resting play",
                got is None and res.get("status") == "refused", str(res)[:70])
    # dogs_gate's own cap and play-max behaviour is asserted in section 2 above, directly.
    import ast as _ast
    _src = open("executor.py", encoding="utf-8").read()
    _fn = next(n for n in _ast.walk(_ast.parse(_src))
               if isinstance(n, _ast.FunctionDef) and n.name == "rest_bid")
    _body = _ast.dump(_fn)
    for _g in ("board_gate", "r1_gate", "dogs_gate"):
        ok &= check(f"rest_bid's dispatch table carries {_g}", _g in _body)
    ok &= check("and the gate is consulted BEFORE the pre-alert",
                _src.index("_REST_LANE_GATES") < _src.index("rest_pre_alert(r, risk, expire, REST_BOOKS)"))

    print("\n4. THE GATE SEES THE AMOUNT THAT WILL ACTUALLY BE POSTED, NOT THE UNTRIMMED UNIT")
    # A trimmed bid that fits must pass where the untrimmed unit would not. rest_risk trims to $50;
    # headroom is $60. If the gate were handed the full unit it would refuse.
    unit, _ = ex.live_stake(-117, ex.unit_for("board"))
    res, got, _ = run("board|" + KEY, rest_risk=50.0, lane_attr="BOARD",
                      lane_state={"risk": ex.BOARD_DAILY_RISK - 60.0, "keys": set(), "known": True})
    ok &= check(f"a $50 trimmed bid posts with $60 of headroom (unit is ${unit:,.2f})",
                got == 50.0, got)
    ok &= check("  and that headroom is less than the untrimmed unit, so the trim mattered",
                60.0 < unit, (60.0, unit))

    print("\n5. AN UNPROVEN LANE FAILS CLOSED")
    res, got, rel = run(KEY, lane_state=OPEN, lane_attr="R1")       # no lane prefix, no source
    ok &= check("no lane prefix and no source: refused, nothing posted",
                got is None and res.get("status") == "refused", str(res)[:70])
    ok &= check("  and the reason says the lane could not be proven",
                "could not be proven" in str(res.get("reason", "")), str(res.get("reason"))[:70])
    ok &= check("  and the claim is released", rel != [])
    res, got, _ = run("r1|" + KEY, source="board", lane_state=OPEN, lane_attr="R1")
    ok &= check("prefix and source DISAGREE: refused (prove nothing)", got is None, got)
    res, got, _ = run("ncs|" + KEY, lane_state=OPEN, lane_attr="NCS")
    ok &= check("NCS resting bid refused (its lane attribution is the deferred work)", got is None, got)
    res, got, _ = run("muse|" + KEY, lane_state=OPEN, lane_attr="R1")
    ok &= check("an unknown lane name is refused, not waved through", got is None, got)

    print("\n6. LANE 1 HAS NO LANE CAP BY DESIGN AND STILL POSTS")
    res, got, _ = run("rules|" + KEY)
    ok &= check("Lane 1 (rules) posts with no lane gate", got is not None, str(res)[:60])
    res, got, _ = run(KEY, source="rules")
    ok &= check("  and resolves from `source` alone when the key carries no prefix", got is not None,
                str(res)[:60])

    print("\nALL PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
