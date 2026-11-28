#!/usr/bin/env python3
"""12K execution: immediate take AND a resting bid at the fee-adjusted alert price. Offline.

Peter, 28 Nov: "12K must support both immediate execution and resting bids at the fee-adjusted
alert price. Keep the approved $200 unit, $1,200 daily risk cap and five-play maximum."

The lane had NO resting coverage of any kind when this file was written - `grep -l 12k` matched no
rest test - so every claim about 12K resting was an inference from the fact that rest_wanted() is
not lane-gated. That is the same no-op-that-looks-like-success this repo keeps paying for, so each
claim below is driven through the production functions rather than read off the source.

Driven here: rest_wanted() for the three ways a 12K play reaches the resting path, rest_bid() for
the price it rests at, the unit it sizes to, and each of the three caps, and the OFF switch on BOTH
submission paths."""
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


RB = inspect.getsource(ex.rest_bid)

KP = {"source": "12k", "play_key": "12k|NFL|Chicago @ Detroit|side|Detroit", "sport": "NFL",
      "game": "Chicago @ Detroit", "bet": "Detroit +2.5 (-108)", "start_utc": "2030-01-01T00:00:00Z"}

# The alert's own after-fee number for this play. -108 is what k12_plays puts in k12_entry as
# price_after_fee, and it is the ONLY price the resting leg may use.
_DEF = {"price_after_fee": -108, "line": 2.5}


def _r(live, verdict="WOULD PLACE", reason=None, books=None, entry=_DEF):
    # entry={} is the unknown-price case under test and {} is falsy, so `entry or _DEF` would
    # silently restore a price and the measurement would be the bug.
    return {"play": dict(KP), "books": books if books is not None else {}, "verdict": verdict,
            "reason": reason, "live": live, "entry": _DEF if entry is _DEF else entry}


# --- 1. THE LANE IS WIRED INTO THE RESTING PATH AT ALL -----------------------------------------
# _REST_LANE_GATES is a local inside rest_bid, not a module attribute, so it is read from the
# source here - but every behavioural claim below drives the function instead.
ok("12k has a resting-path gate", '"12k": k12_gate' in RB, RB.count("k12_gate"))
ok("the approved unit is $200", ex.K12_UNIT == 200.0, ex.K12_UNIT)
ok("the approved daily risk cap is $1,200", ex.K12_DAILY_RISK == 1200.0, ex.K12_DAILY_RISK)
ok("the approved play maximum is 5", ex.K12_MAX_PLAYS == 5, ex.K12_MAX_PLAYS)
ok("the resting leg sizes to the 12K unit, not the default",
   ex.unit_for("12k") == 200.0 and ex.unit_for(None) != 200.0,
   (ex.unit_for("12k"), ex.unit_for(None)))

_live, _rb = ex.px_live.LIVE, ex.REST_BOOKS
try:
    ex.px_live.LIVE, ex.REST_BOOKS = True, ("novig", "kalshi")

    # --- 2. THE THREE WAYS A 12K PLAY REACHES A RESTING BID ------------------------------------
    ok("no live book at the alert number -> rest",
       ex.rest_wanted(_r({"go": False, "lane": "12k",
                          "why": ["no live book has the alert number or better"]})) is True)
    ok("a price skip -> rest",
       ex.rest_wanted(_r({"go": False, "lane": "12k", "why": ["price: moved"]},
                         verdict="SKIP", reason="price: moved")) is True)
    ok("an EMPTY fill-or-kill rests the full unit",
       ex.rest_wanted(_r({"go": True, "lane": "12k", "risk": 200.0,
                          "order": {"status": "placed", "fills_read": True, "filled_stake": 0}})) is True)
    _part = _r({"go": True, "lane": "12k", "risk": 200.0,
                "order": {"status": "placed", "fills_read": True, "filled_stake": 75.0}})
    ok("a PARTIAL fill rests only the unfilled part, so take+rest cannot exceed the unit",
       ex.rest_wanted(_part) is True and _part["live"]["rest_risk"] == 125.0,
       _part["live"].get("rest_risk"))

    # --- 3. WHAT MUST NEVER REST --------------------------------------------------------------
    ok("an unexplained venue refusal does not rest",
       ex.rest_wanted(_r({"go": True, "lane": "12k", "risk": 200.0,
                          "order": {"status": "refused", "fills_read": True, "filled_stake": 0}})) is False)
    ok("an errored leg anywhere in the play does not rest",
       ex.rest_wanted(_r({"go": True, "lane": "12k", "risk": 200.0,
                          "order": {"status": "placed", "fills_read": True, "filled_stake": 0},
                          "more": [{"status": "error"}]})) is False)
    # An UNREAD fill is not an empty one. _got() prices it at the full asked stake, so the
    # remainder is zero and nothing rests - the same fail-closed rule the ProphetX unknown-fill
    # correction put on the take path.
    ok("an unread fill does not rest (fail closed, never assume empty)",
       ex.rest_wanted(_r({"go": True, "lane": "12k", "risk": 200.0,
                          "order": {"status": "placed", "asked_stake": 200.0}})) is False)

    # --- 4. THE PRICE, THE UNIT AND THE CAPS, DRIVEN THROUGH rest_bid() -----------------------
    class _Reg:
        enabled = staticmethod(lambda: True)
        submission_held = staticmethod(lambda k: None)
        claim_submission = staticmethod(lambda k, c: True)
        released = []

        @staticmethod
        def release_submission(k, c):
            _Reg.released.append(k)
            return True

    _saved = (ex.registry, ex.committed_risk, ex.live_guards, ex.journal_latch_why,
              ex.rest_pre_alert, dict(ex.K12), ex.K12_DAILY_RISK, ex._unit_ledger_mode,
              ex._unit_ledger_guard, ex.rest_revalidate)
    _seen_price = {}
    try:
        ex.registry = _Reg
        ex.committed_risk = lambda k: (0.0, None)
        ex.live_guards = lambda: (True, "")
        ex.journal_latch_why = lambda: None
        ex._unit_ledger_mode = lambda: "on"

        ex.rest_pre_alert = lambda *a, **k: True   # a capped bid must refuse BEFORE this
        # The price, the unit and the venue all arrive together at the shared-ledger guard, which
        # is the last thing rest_bid does before the venue's place() call. Spying there reads the
        # production values rather than re-deriving them.
        _realguard = ex._unit_ledger_guard

        def _spy(r, path, book=None, stake=None, shown=None, unit=None):
            _seen_price[book] = (shown, stake, unit)
            raise RuntimeError("spy: stop before any venue call")
        ex._unit_ledger_guard = _spy
        ex.rest_revalidate = lambda r, b, ln: (True, "", (r.get("books") or {}).get(b) or {})
        _BOOKS = {b: {"status": "ok", "exact_line": True, "line": 2.5, "alert_line": 2.5,
                      "am": -108, "kalshi_buy": [], "novig": {}} for b in ("novig", "kalshi")}
        ex.K12_DAILY_RISK = 1200.0
        _far = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")

        def _bid(entry=_DEF, books=None, **k12):
            ex.K12.clear()
            ex.K12.update({"known": True, "keys": set(), "risk": 0.0, **k12})
            _seen_price.clear()
            r = _r({"go": False, "lane": "12k",
                    "why": ["no live book has the alert number or better"]}, entry=entry,
                   books=_BOOKS if books is None else books)
            r["play"]["start_utc"] = _far
            return ex.rest_bid(r)

        res = _bid(entry={})
        ok("an unknown after-fee price refuses rather than guessing a resting number",
           str(res.get("reason") or "").startswith("alert after-fee price unknown"), res)

        _Reg.released = []
        res = _bid(risk=1200.0)
        ok("a resting 12K bid refuses at the $1,200 daily risk cap",
           res["status"] == "refused" and "daily risk limit" in res["reason"], res)
        ok("...and the submission claim is released on that refusal",
           _Reg.released == [ex.lane_strip(KP["play_key"]) + "|rest"], _Reg.released)
        ok("...before any venue was quoted a price", _seen_price == {}, _seen_price)

        res = _bid(keys={f"k{i}" for i in range(5)})
        ok("a resting 12K bid refuses at the five-play maximum",
           res["status"] == "refused" and "play cap" in res["reason"], res)

        res = _bid(known=False)
        ok("unknown 12K exposure refuses (fail closed)",
           res["status"] == "refused" and "exposure unknown" in res["reason"], res)

        res = _bid()
        ok("within every cap the lane gate does NOT refuse the bid",
           "daily risk limit" not in str(res.get("reason") or "")
           and "play cap" not in str(res.get("reason") or "")
           and "exposure unknown" not in str(res.get("reason") or ""), res)
        ok("...and the price it reserves against is the alert's own after-fee number",
           _seen_price and {p for p, _s, _u in _seen_price.values()} == {-108}, _seen_price)
        ok("...sized at the lane's $200 unit, not the $300 default",
           _seen_price and {u for _p, _s, u in _seen_price.values()} == {200.0}, _seen_price)
        ok("...on Novig or Kalshi only - PMUS is never quoted a resting bid",
           set(_seen_price) <= {"novig", "kalshi"}, sorted(_seen_price))

        # --- 5. THE OFF SWITCH BLOCKS THE RESTING PATH, NOT JUST THE TAKE --------------------
        # The switch does NOT live in k12_gate - it is read in the dispatch branch, which writes
        # "12K lane not switched on" into live.why. rest_wanted() admits exactly one non-go
        # reason, so that message is what stops the maker leg. Asserting the gate here instead
        # would have tested the wrong mechanism and called a working switch broken.
        ok("k12_gate itself does not read the switch (the dispatch branch does)",
           ex.k12_gate(200.0, "12k|probe")[0] is True)
        ex.K12.clear()
        ex.K12.update({"known": True, "keys": set(), "risk": 0.0})
        ok("a 12K play blocked by the OFF switch never reaches a resting bid",
           ex.rest_wanted(_r({"go": False, "lane": "12k",
                              "why": ["12K lane not switched on (EXEC_12K_LIVE)"]})) is False)
        ok("...and that is the exact string the dispatch branch writes",
           "12K lane not switched on (EXEC_12K_LIVE)"
           in inspect.getsource(ex.main))
    finally:
        (ex.registry, ex.committed_risk, ex.live_guards, ex.journal_latch_why,
         ex.rest_pre_alert, _k, ex.K12_DAILY_RISK, ex._unit_ledger_mode,
         ex._unit_ledger_guard, ex.rest_revalidate) = _saved
        ex.K12.clear()
        ex.K12.update(_k)
finally:
    ex.px_live.LIVE, ex.REST_BOOKS = _live, _rb

# --- 6. NO PRICE TOLERANCE, AND THE LANE IS NAMED IN THE RESTING GATE MAP ----------------------
ok("the resting price is the alert's after-fee number and nothing else",
   'af = e.get("price_after_fee")' in RB and "p_star = american_to_prob(int(af))" in RB)
ok("no price tolerance is applied on the resting path for any lane",
   "dogs_tol" not in RB and "TOL" not in RB)
ok("an unproven lane still cannot reach a venue", "could not be proven" in RB)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
