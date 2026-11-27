#!/usr/bin/env python3
"""Per-lane daily caps and play maximums on the RESTING path (Peter, Nov 27). Offline.

THE DEFECT. board_gate, r1_gate, ncs_gate and dogs_gate were each consulted at exactly one place:
the take branch, which requires verdict WOULD PLACE and a live candidate r["lc"]. A play reaches
rest_bid() precisely BECAUSE there was no live candidate, so no lane gate had ever been asked about
a resting bid. Every one of those gates says in its own docstring that it counts orders "already
submitted OR RESTING today" - they were written expecting this call and never received it. A $200
(board/R1/NCS) or $300 (DOGS) bid therefore reached a venue with no lane cap, no play maximum and,
for DOGS, no kill bar; only the $3,000 global stop was above it.

Driven through rest_bid() itself rather than asserted from source, because the defect WAS a missing
call site - a source-level test for the call would have been the thing that was absent."""
import inspect
import os
import sys
from datetime import datetime, timedelta, timezone

import executor as ex

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


LANES = {            # lane -> (module state dict, gate fn, unit, max-plays, daily-risk)
    "board": (ex.BOARD, ex.board_gate, ex.BOARD_UNIT, ex.BOARD_MAX_PLAYS, ex.BOARD_DAILY_RISK),
    "r1":    (ex.R1,    ex.r1_gate,    ex.R1_UNIT,    ex.R1_MAX_PLAYS,    ex.R1_DAILY_RISK),
    "ncs":   (ex.NCS,   ex.ncs_gate,   ex.NCS_UNIT,   ex.NCS_MAX_PLAYS,   ex.NCS_DAILY_RISK),
    "dogs":  (ex.DOGS,  ex.dogs_gate,  ex.DOGS_UNIT,  ex.DOGS_MAX_PLAYS,  ex.DOGS_DAILY_RISK),
}

# --- 1. the dispatcher in isolation ------------------------------------------------------------
ok("every live lane has a gate wired", sorted(ex.REST_LANE_GATES) == ["board", "dogs", "ncs", "r1"])
ok("the wired objects ARE the lane gates (a rename breaks at import, not on live money)",
   all(ex.REST_LANE_GATES[k] is v[1] for k, v in LANES.items()))
_rg = lambda lane, src, risk=200.0: ex.rest_lane_gate({"live": {"lane": lane}, "play": {"source": src}}, risk)
ok("Lane 1 is exempt and says so (its only limit is the global stop)",
   _rg(None, "rules")[0] is True and "no per-lane cap" in _rg(None, "rules")[1])
ok("Lane 1 with no 'lane' key at all is still Lane 1, not an unknown lane",
   ex.rest_lane_gate({"live": {}, "play": {"source": "rules"}}, 300.0)[0] is True)
_u = _rg("zzz", "zzz")
ok("an unrecognised lane FAILS CLOSED", _u[0] is False and "no risk gate is wired" in _u[1], _u)
ok("...which matters because unit_for() would have sized it at Lane 1's $300",
   ex.unit_for("zzz") == 300.0)
_m = _rg("board", "dogs")
ok("a lane/play disagreement refuses (sized by one lane, capped by another's limits)",
   _m[0] is False and "lane disagreement" in _m[1], _m)
ok("...in both directions", _rg("dogs", "board")[0] is False)
ok("lane2 is never rest-eligible, so it needs no gate", "lane2" not in ex.REST_LANE_GATES)
# Nov 27, closing a gap an independent review found and PROVED with a mutation: hoisting the
# Lane 1 early-out above the lane/play cross-check kept every other assertion in this file green,
# while a DOGS play whose live dict had lost its "lane" key was then treated as Lane 1 - resting
# $300 (unit_for(None)) with no daily cap, no play maximum and no kill bar. The combination neither
# harness covered is lane ABSENT with a capped source, because both always set lane == source.
for _src in ("dogs", "board", "r1", "ncs"):
    _g = ex.rest_lane_gate({"live": {}, "play": {"source": _src}}, 300.0)
    ok(f"a {ex.LANE_NAME.get(_src, _src)} play that has LOST its lane key is refused, not treated as Lane 1",
       _g[0] is False and "lane disagreement" in _g[1], _g)
ok("...so the cross-check must stay ahead of the Lane 1 exemption",
   inspect.getsource(ex.rest_lane_gate).index("lane disagreement")
   < inspect.getsource(ex.rest_lane_gate).index('if lane == "rules"'))

# --- 2. each lane's cap, play maximum and unknown-exposure refusal, through rest_bid() ---------
class _Reg:
    enabled = staticmethod(lambda: True)
    submission_held = staticmethod(lambda k: None)
    claim_submission = staticmethod(lambda k, c: True)
    released = []

    @staticmethod
    def release_submission(k, c):
        _Reg.released.append(k)
        return True


_saved = (ex.registry, ex.committed_risk, ex.live_guards, ex.journal_latch_why, ex.dogs_kill_state,
          ex.rest_pre_alert, ex._unit_ledger_mode, ex.px_live.LIVE, ex.REST_BOOKS,
          {k: dict(v[0]) for k, v in LANES.items()})
try:
    ex.registry = _Reg
    ex.committed_risk = lambda k: (0.0, None)
    ex.live_guards = lambda: (True, "")
    ex.journal_latch_why = lambda: None
    ex.dogs_kill_state = lambda: {"blocked": False, "why": "ok"}
    ex._unit_ledger_mode = lambda: "on"
    ex.rest_pre_alert = lambda *a, **k: True      # a capped bid must refuse BEFORE it is announced
    ex.px_live.LIVE, ex.REST_BOOKS = True, ("novig", "kalshi")
    _far = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")

    def _bid(lane, **state):
        st, _fn, _unit, _maxp, _risk = LANES[lane]
        st.clear()
        st.update({"known": True, "keys": set(), "risk": 0.0, **state})
        p = {"source": lane, "play_key": f"{lane}|NBA|A @ B|side|A", "sport": "NBA",
             "game": "A @ B", "bet": "A ML (+140)", "start_utc": _far}
        return ex.rest_bid({"play": p, "books": {}, "verdict": "WOULD PLACE", "reason": None,
                            "entry": {"price_after_fee": 140, "line": None},
                            "live": {"go": False, "lane": lane,
                                     "why": ["no live book has the alert number or better"]}})

    for lane, (_st, _fn, _unit, _maxp, _dr) in LANES.items():
        nm = ex.LANE_NAME.get(lane, lane)
        _Reg.released = []
        res = _bid(lane, risk=_dr)                       # the whole day's budget already at risk
        ok(f"{nm}: a resting bid refuses at the daily risk limit",
           res["status"] == "refused" and "daily risk limit" in res["reason"], res)
        ok(f"{nm}: ...and the submission claim is released, not leaked",
           _Reg.released == [ex.lane_strip(f"{lane}|NBA|A @ B|side|A") + "|rest"], _Reg.released)
        res = _bid(lane, keys={f"k{i}" for i in range(_maxp)})
        ok(f"{nm}: a resting bid refuses at the play maximum ({_maxp})",
           res["status"] == "refused" and "play cap" in res["reason"], res)
        res = _bid(lane, known=False)
        ok(f"{nm}: unknown lane exposure refuses (fail closed)",
           res["status"] == "refused" and "unknown" in res["reason"], res)
        res = _bid(lane)                                  # clean slate
        ok(f"{nm}: within every cap the lane gate does not refuse",
           "daily risk limit" not in str(res.get("reason") or "")
           and "play cap" not in str(res.get("reason") or ""), res)

    # DOGS carries one more protection the others do not, and it must also reach the resting path.
    ex.dogs_kill_state = lambda: {"blocked": True, "why": "DOGS kill bar: grading unreadable"}
    res = _bid("dogs")
    ok("DOGS: the kill bar refuses a resting bid too", "kill bar" in str(res.get("reason") or ""), res)
    ex.dogs_kill_state = lambda: {"blocked": False, "why": "ok"}

    # Nov 27, second gap the review proved: of every test file touching rest_bid, none constructed
    # live with `go` truthy, so a change guarding the gate behind `if not lv.get("go")` - a
    # plausible "the take already asked" optimisation - passed the whole suite. That is the
    # take-then-rest path, where the remainder of a partial fill rests, and it must be gated too.
    _st, _fn, _unit, _maxp, _dr = LANES["dogs"]
    _st.clear()
    _st.update({"known": True, "keys": set(), "risk": _dr})          # the day's budget already gone
    _ptr = {"source": "dogs", "play_key": "dogs|NBA|E @ F|side|E", "sport": "NBA", "game": "E @ F",
            "bet": "E ML (+140)", "start_utc": _far}
    res = ex.rest_bid({"play": _ptr, "books": {}, "verdict": "WOULD PLACE", "reason": None,
                       "entry": {"price_after_fee": 140, "line": None},
                       "live": {"go": True, "lane": "dogs", "risk": 300.0, "shown": 140,
                                "unit": 300.0, "rest_risk": 190.0,
                                "order": {"status": "placed", "fills_read": True,
                                          "filled_stake": 110.0, "asked_stake": 300.0}}})
    ok("the take-then-rest remainder is gated too, not waved through as already-approved",
       res["status"] == "refused" and "daily risk limit" in res["reason"], res)

    # Lane 1 must be UNCHANGED by this correction: no per-lane gate, only the global stop.
    p1 = {"source": "rules", "play_key": "NBA|C @ D|total|under", "sport": "NBA", "game": "C @ D",
          "bet": "Under 220.5 (-110)", "start_utc": _far}
    res = ex.rest_bid({"play": p1, "books": {}, "verdict": "WOULD PLACE", "reason": None,
                       "entry": {"price_after_fee": -110, "line": 220.5},
                       "live": {"go": False, "why": ["no live book has the alert number or better"]}})
    ok("Lane 1 is not gated by this change (no lane cap exists for it)",
       "daily risk limit" not in str(res.get("reason") or "")
       and "play cap" not in str(res.get("reason") or "")
       and "no risk gate is wired" not in str(res.get("reason") or ""), res)
finally:
    (ex.registry, ex.committed_risk, ex.live_guards, ex.journal_latch_why, ex.dogs_kill_state,
     ex.rest_pre_alert, ex._unit_ledger_mode, ex.px_live.LIVE, ex.REST_BOOKS, _states) = _saved
    for k, v in _states.items():
        LANES[k][0].clear()
        LANES[k][0].update(v)

# --- 3. the gate is asked where it can still stop the order -----------------------------------
RB = inspect.getsource(ex.rest_bid)
_code = "\n".join(l.split("#", 1)[0] for l in RB.splitlines())
ok("the lane gate is asked before the pre-submission alert",
   _code.index("rest_lane_gate(r, risk)") < _code.index("rest_pre_alert(r, risk"))
ok("...and before any venue is touched",
   _code.index("rest_lane_gate(r, risk)") < _code.index("for b in REST_BOOKS"))
ok("...and after the cross-venue remainder is applied, so it sees the posted amount",
   _code.index("_allowed = round(") < _code.index("rest_lane_gate(r, risk)"))
ok("a refusal releases the submission claim rather than holding it to the next run",
   "registry.release_submission(_rkey, REST_CID)\n        return {\"status\": \"refused\", \"reason\": _lwhy}" in RB)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
