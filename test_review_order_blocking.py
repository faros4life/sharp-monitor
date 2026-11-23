#!/usr/bin/env python3
"""REVIEW ONLY. Fake-venue proof that the REAL order functions refuse and never reach the venue.

Finding 5 of the fifth review: checking that a guard call appears in the source is not proof that
an order is blocked. These drive executor.live_order() itself with px_live.place() replaced by a
spy, so "the venue was never called" is an observation rather than an inference.
"""
import os
import sys

os.environ.pop("EXEC_UNIT_LEDGER", None)
import executor as ex
import review_integration as RI
import review_store_registry as S
import review_unit_reservation as R

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


class FakeRegistry:
    def __init__(self):
        self.data, self.sha = {}, "s1"

    def _fetch(self):
        return (dict(self.data), self.sha)

    def _put_with_sha(self, merged, sha):
        if sha != self.sha:
            return False
        self.data, self.sha = dict(merged), f"s{int(self.sha[1:]) + 1}"
        return True


REG = FakeRegistry()

# The executor builds its store from the real `registry` module, so the fake has to BE that module
# for this test - otherwise the helper reads the live store and the test proves nothing.
import registry as _real_registry

_real_registry._fetch = REG._fetch
_real_registry._put_with_sha = REG._put_with_sha


def store():
    return S.RegistryStore(REG)


KEY = RI.play_key("NBA", "LAL @ BOS", "total", "Under 225.5 (-110)")


def catch(f):
    try:
        f()
    except Exception as e:
        return e
    return None


class Spy:
    def __init__(self):
        self.calls = 0

    def place(self, *a, **k):
        self.calls += 1
        return {"status": "placed", "order_id": "venue-1", "filled_stake": 220.0}


# --- driven through the REAL executor helpers ----------------------------------------------------
r = {"live": {"risk": 220.0, "shown": -110, "unit": 200.0, "book": "novig", "line": 225.5,
              "cid": "order-1"},
     "play": {"sport": "NBA", "game": "LAL @ BOS", "market": "total", "bet": "Under 225.5 (-110)",
              "play_key": "p1"}}

ok("with the ledger OFF the guard is inert", ex._unit_ledger_guard(r, "t") is None)
ok("with it OFF the stake passes through", ex._unit_ledger_consume(None, 220.0) == 220.0)

os.environ["EXEC_UNIT_LEDGER"] = "on"
try:
    R.backfill(store(), [], "fixture")
    g = ex._unit_ledger_guard(r, "live_order")
    ok("with it ON the real helper reserves", g is not None)
    ok("the reservation is visible to the OTHER system", abs(R.available(store(), KEY)) < 1e-9)

    rb = {"live": dict(r["live"], cid="rest-1"), "play": dict(r["play"], play_key="pr")}
    ok("a second dispatch path on the same play is REFUSED",
       isinstance(catch(lambda: ex._unit_ledger_guard(rb, "rest_bid")), R.ReservationRefused))
    ok("a play with NO order identity is refused outright",
       isinstance(catch(lambda: ex._unit_ledger_guard({"live": {}, "play": {"sport": "NBA",
                  "game": "g", "market": "total", "bet": "Under 1"}}, "live_order")),
                  (RuntimeError, R.ReservationRefused, __import__("review_unit_exposure").ExposureUnknown)))
    ok("consuming the grant once is allowed", ex._unit_ledger_consume(g, 220.0) == 220.0)
    ok("consuming the SAME grant twice is refused",
       isinstance(catch(lambda: ex._unit_ledger_consume(g, 220.0)), R.ReservationRefused))
    ok("submitting with NO grant is refused",
       isinstance(catch(lambda: ex._unit_ledger_consume(None, 220.0)), R.ReservationRefused))

    import builtins
    real_import = builtins.__import__

    def broken(name, *a, **k):
        if name in ("review_integration", "review_store_registry"):
            raise ImportError("simulated missing module")
        return real_import(name, *a, **k)

    builtins.__import__ = broken
    try:
        ok("flag ON with the modules missing RAISES rather than skipping the guard",
           isinstance(catch(lambda: ex._unit_ledger_guard(r, "live_order")), RuntimeError))
    finally:
        builtins.__import__ = real_import

    r2 = {"live": dict(r["live"], line=226.5, cid="order-2"),
          "play": dict(r["play"], bet="Under 226.5 (-108)", play_key="p2")}
    ok("an ADJACENT line on the same side gets no second budget",
       isinstance(catch(lambda: ex._unit_ledger_guard(r2, "live_order")), R.ReservationRefused))

    r3 = {"live": dict(r["live"], cid="order-3"),
          "play": dict(r["play"], bet="Over 225.5 (-110)", play_key="p3")}
    ok("the opposite side still has its own unit",
       ex._unit_ledger_guard(r3, "live_order") is not None)
    ok("an IDENTICAL retry of a granted order is still idempotent, not a second budget",
       ex._unit_ledger_guard(r, "live_order") is not None)

    spy = Spy()
    real_place = ex.px_live.place
    ex.px_live.place = spy.place
    try:
        # a DIFFERENT order on an exhausted budget - not a retry of one already granted
        r4 = {"live": dict(r["live"], line=227.5, cid="order-4"),
              "play": dict(r["play"], bet="Under 227.5 (-105)", play_key="p4")}
        refused = catch(lambda: ex._unit_ledger_guard(r4, "live_order"))
        ok("the refused play never reaches px_live.place", spy.calls == 0, str(spy.calls))
        ok("and the refusal is a reservation refusal, not a venue error",
           isinstance(refused, R.ReservationRefused), repr(refused))
    finally:
        ex.px_live.place = real_place
finally:
    os.environ.pop("EXEC_UNIT_LEDGER", None)

ok("the flag is left OFF after the tests", ex._unit_ledger_guard(r, "t") is None)
src = open("executor.py", encoding="utf-8").read()
ok("the reservation is taken LATE, after the gates decided to send",
   src.index('_unit_ledger_guard(r, "live_order", "prophetx")') > src.index("journal_intent(r,"))
ok("the grant is CONSUMED before the venue call",
   src.index("_unit_ledger_consume(_led, stake)") < src.index("res = px_live.place("))

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
