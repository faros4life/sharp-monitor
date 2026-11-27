#!/usr/bin/env python3
"""DOGS resting bids: Peter's eight terms for lifting the no-rest rule (Nov 27 2026). Offline.

Until Nov 27 a DOGS play filled at the alert number or not at all - rest_wanted() returned False on
sight of the lane. Peter lifted ONLY that half of the dogs_strict bundle. Every term he attached is
one check below, each named with the term it enforces, so a later change that quietly drops one
fails here instead of on live money.

The point of the file is the terms, not the removal: the removal is two lines, and all eight terms
are things the resting path must still do afterwards."""
import inspect
import math
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


HERE = os.path.dirname(os.path.abspath(__file__))
RW = inspect.getsource(ex.rest_wanted)
RB = inspect.getsource(ex.rest_bid)

DP = {"source": "dogs", "play_key": "dogs|NBA|A @ B|side|A", "sport": "NBA", "game": "A @ B",
      "bet": "A ML (+140)", "start_utc": "2030-01-01T00:00:00Z"}


_DEF = {"price_after_fee": 140, "line": None}


def _r(live, verdict="WOULD PLACE", reason=None, books=None, entry=_DEF):
    # `entry or _DEF` would be wrong: entry={} is the unknown-price case under test and {} is falsy,
    # so the default would silently restore a price. Caught by this file's own TERM 1 check.
    return {"play": dict(DP), "books": books if books is not None else {}, "verdict": verdict,
            "reason": reason, "live": live, "entry": _DEF if entry is _DEF else entry}


def _code(src):
    """Executable lines only. The removal left a long comment that names dogs_strict, so a plain
    substring test on the source would read that comment as the gate still being there - the
    measurement would be the bug. Checks the code, not the prose."""
    out = []
    for ln in src.splitlines():
        t = ln.split("#", 1)[0].rstrip()
        if t.strip():
            out.append(t)
    body = "\n".join(out)
    return body.split('"""')[-1] if body.count('"""') >= 2 else body


# --- the removal itself ------------------------------------------------------------------------
ok("the lane test is gone from rest_wanted", "dogs_strict" not in _code(RW))
ok("...and the reason it is gone is written where it was",
   "Peter lifted the no-rest half" in RW and "Nov 27" in RW)
ok("dogs_strict itself is untouched and still bundles the other three rules",
   ex.dogs_strict({"source": "dogs"}) is True and ex.dogs_strict({"source": "board"}) is False)

# --- TERM 1: rest only at the original alert-based limit, accounting for fees -------------------
# One source of price in this path and it is the alert's after-fee number. No tolerance is applied
# here for ANY lane, so the DOGS no-tolerance rule needs nothing added to stay true.
ok("TERM 1: the resting price is the alert's after-fee number",
   'af = e.get("price_after_fee")' in RB and "p_star = american_to_prob(int(af))" in RB)
ok("TERM 1: no price tolerance is applied on the resting path",
   "dogs_tol" not in RB and "TOL" not in RB)

_live = ex.px_live.LIVE
_rb = ex.REST_BOOKS
try:
    ex.px_live.LIVE, ex.REST_BOOKS = True, ("novig", "kalshi")

    # --- TERM 2: rest when immediate execution is unavailable, or an FOK comes back empty -------
    ok("TERM 2: no live book at the alert number -> rest",
       ex.rest_wanted(_r({"go": False, "lane": "dogs",
                          "why": ["no live book has the alert number or better"]})) is True)
    ok("TERM 2: a price skip -> rest",
       ex.rest_wanted(_r({"go": False, "lane": "dogs", "why": ["price: moved"]},
                         verdict="SKIP", reason="price: moved")) is True)
    ok("TERM 2: an EMPTY fill-or-kill rests the full unit",
       ex.rest_wanted(_r({"go": True, "lane": "dogs", "risk": 300.0,
                          "order": {"status": "placed", "fills_read": True, "filled_stake": 0}})) is True)
    _part = _r({"go": True, "lane": "dogs", "risk": 300.0,
                "order": {"status": "placed", "fills_read": True, "filled_stake": 110.0}})
    ok("TERM 2: a PARTIAL fill rests only the unfilled part",
       ex.rest_wanted(_part) is True and _part["live"]["rest_risk"] == 190.0)

    # --- TERM 3: never rest following an unexplained venue refusal -----------------------------
    ok("TERM 3: a refusal does not rest (the order was never placed)",
       ex.rest_wanted(_r({"go": True, "lane": "dogs", "risk": 300.0,
                          "order": {"status": "refused", "fills_read": True, "filled_stake": 0}})) is False)
    ok("TERM 3: an errored leg anywhere in the play does not rest",
       ex.rest_wanted(_r({"go": True, "lane": "dogs", "risk": 300.0,
                          "order": {"status": "placed", "fills_read": True, "filled_stake": 0},
                          "more": [{"status": "error"}]})) is False)
    # The unread state is filled_stake ABSENT (or sent_to_runner), which _got() prices at the full
    # asked stake - so the remainder is zero and nothing rests. An explicit filled_stake of 0 is a
    # READ zero and is the empty-FOK case above; the two must not be conflated.
    ok("TERM 3: an unread fill does not rest (fail closed, never assume empty)",
       ex.rest_wanted(_r({"go": True, "lane": "dogs", "risk": 300.0,
                          "order": {"status": "placed", "asked_stake": 300.0}})) is False)
    ok("TERM 3: a fill sent to the home runner does not rest either",
       ex.rest_wanted(_r({"go": True, "lane": "dogs", "risk": 300.0,
                          "order": {"status": "placed", "fills_read": True, "filled_stake": 0,
                                    "sent_to_runner": True, "asked_stake": 300.0}})) is False)

    # --- TERM 8 (behavioural): the $2,400 daily cap, 8-play maximum and kill bar still bind ----
    # These three live in dogs_gate(), which the resting path had never asked. Each is driven here
    # through rest_bid() itself, not asserted from source, because the whole defect was that the
    # call site did not exist.
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
              ex.dogs_kill_state, ex.rest_pre_alert, dict(ex.DOGS), ex.DOGS_DAILY_RISK,
              ex._unit_ledger_mode)
    try:
        ex.registry = _Reg
        ex.committed_risk = lambda k: (0.0, None)
        ex.live_guards = lambda: (True, "")
        ex.journal_latch_why = lambda: None
        ex.dogs_kill_state = lambda: {"blocked": False, "why": "ok"}
        ex._unit_ledger_mode = lambda: "on"
        ex.rest_pre_alert = lambda *a, **k: True        # a capped bid must refuse BEFORE this
        ex.DOGS_DAILY_RISK = 2400.0
        _far = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")

        def _bid(**dogs):
            ex.DOGS.clear()
            ex.DOGS.update({"known": True, "keys": set(), "risk": 0.0, **dogs})
            r = _r({"go": False, "lane": "dogs", "why": ["no live book has the alert number or better"]})
            r["play"]["start_utc"] = _far
            return ex.rest_bid(r)

        res = ex.rest_bid(_r({"go": False, "lane": "dogs"}, entry={}))
        ok("TERM 1: an unknown after-fee price refuses rather than guessing",
           str(res.get("reason") or "").startswith("alert after-fee price unknown"), res)
        _Reg.released = []
        res = _bid(risk=2400.0)
        ok("TERM 8: a resting DOGS bid refuses at the daily risk cap",
           res["status"] == "refused" and "daily risk limit" in res["reason"], res)
        ok("TERM 8: ...and the submission claim is released on that refusal",
           _Reg.released == [ex.lane_strip(DP["play_key"]) + "|rest"], _Reg.released)
        res = _bid(keys={f"k{i}" for i in range(8)})
        ok("TERM 8: a resting DOGS bid refuses at the eight-play maximum",
           res["status"] == "refused" and "play cap" in res["reason"], res)
        res = _bid(known=False)
        ok("TERM 8: unknown DOGS exposure refuses (fail closed)",
           res["status"] == "refused" and "exposure unknown" in res["reason"], res)
        ex.dogs_kill_state = lambda: {"blocked": True, "why": "DOGS kill bar: 0-9 last 9"}
        res = _bid()
        ok("TERM 8: the DOGS kill bar refuses a resting bid too",
           res["status"] == "refused" and "kill bar" in res["reason"], res)
        ex.dogs_kill_state = lambda: {"blocked": False, "why": "ok"}
        res = _bid()
        ok("TERM 8: within every cap the bid is NOT refused by the lane gate",
           "daily risk limit" not in str(res.get("reason") or "")
           and "play cap" not in str(res.get("reason") or ""), res)
        # Scope, UPDATED 27 Nov. This originally asserted the resting-path gate was DOGS-only, and
        # recorded the other three lanes' identical gap as an observation left unfixed. Peter then
        # instructed: "Complete resting-path risk enforcement across all applicable lanes." So the
        # assertion is inverted rather than deleted - the gate must now reach EVERY lane with a cap,
        # and dogs_gate must still be among them, which is what this file is really protecting.
        ok("scope: the resting-path gate now covers every lane with a cap, dogs included",
           all(g in _code(RB) for g in ("dogs_gate", "board_gate", "r1_gate")))
        ok("and an unproven lane cannot reach a venue without one",
           "could not be proven" in _code(RB))
    finally:
        (ex.registry, ex.committed_risk, ex.live_guards, ex.journal_latch_why,
         ex.dogs_kill_state, ex.rest_pre_alert, _d, ex.DOGS_DAILY_RISK,
         ex._unit_ledger_mode) = _saved
        ex.DOGS.clear()
        ex.DOGS.update(_d)
finally:
    ex.px_live.LIVE, ex.REST_BOOKS = _live, _rb

# --- TERM 4: strict resting-order revalidation preserved ---------------------------------------
ok("TERM 4: every venue is revalidated before pricing, and a failure skips that venue",
   "_rok, _rwhy, _fresh = rest_revalidate(r, b, x.get(\"line\", e.get(\"line\")))" in RB
   and "if not _rok:" in RB and "x = _fresh" in RB)
ok("TERM 4: revalidation is maker-safe (no depth test) so a legitimate bid is not starved",
   "Maker-safe - no depth test" in RB)

# --- TERM 5: Novig and Kalshi only; PMUS resting prohibited ------------------------------------
ok("TERM 5: the resting venue loop dispatches kalshi and novig and nothing else",
   RB.count('if b == "kalshi"') == 1 and RB.count('elif b == "novig"') == 1)
ok("TERM 5: Polymarket US resting is explicitly BLOCKED, not merely absent from a list",
   'elif b == "polymarket_us"' in RB and "resting BLOCKED" in RB)
ok("TERM 5: a venue with no dispatch branch cannot silently place (CLAUDE.md: check the caller)",
   "why_not.append" in RB)

# --- TERM 6: T-30 expiry, the shared unit ledger, duplicate protection -------------------------
ok("TERM 6: the bid expires at T-30", ex.REST_BEFORE_MIN == 30
   and "expire = st - timedelta(minutes=REST_BEFORE_MIN)" in RB)
ok("TERM 6: the shared unit ledger is claimed for the resting leg",
   '_unit_ledger_guard(r, "rest_bid", b)' in RB and "_unit_ledger_consume(_rb_grant, risk)" in RB)
ok("TERM 6: a separate |rest claim stops two runs posting the same bid",
   '_pkey + "|rest"' in RB and "claim_submission(_rkey, REST_CID)" in RB)
ok("TERM 6: ...and it refuses while another run holds the immediate claim",
   "registry.submission_held(_pkey)" in RB and "another run holds the immediate submission claim" in RB)
ok("TERM 6: no durable store means no resting bid at all",
   "no durable store for the resting submission claim" in RB)

# --- TERM 7: $300 maximum combined exposure per play, across venues ---------------------------
ok("TERM 7: the DOGS unit is $300", ex.unit_for("dogs") == 300.0 and ex.DOGS_UNIT == 300.0)
ok("TERM 7: the ceiling is the intended unit minus what is already committed anywhere",
   "_allowed = round(_unit_risk - _committed, 2)" in RB and "if _allowed < risk:" in RB)
ok("TERM 7: committed risk that cannot be established refuses the bid",
   "cross-venue committed risk could not be established" in RB)
ok("TERM 7: take + rest cannot exceed the unit by arithmetic",
   'rem = round(float(lv.get("risk") or 0) - sum(_got(x) for x in allo), 2)' in RW)
_r300, _ = ex.live_stake(140, ex.DOGS_UNIT)
ok("TERM 7: at plus money a DOGS play risks $300 total (Peter's rule, unchanged)", _r300 == 300.0, _r300)
_r120, _w120 = ex.live_stake(-120, ex.DOGS_UNIT)
ok("TERM 7: at minus money it sizes to WIN $300 (unchanged)", round(_w120, 2) == 300.0, (_r120, _w120))

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
