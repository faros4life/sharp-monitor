#!/usr/bin/env python3
"""REVIEW ONLY. The ledger is a superset of every order attempt - with no pause and no cutoff.

The two cases Peter's review raised, plus the one behind them:
  1. an OLDER RUN still in flight submits after recording began, and writes nothing to the ledger;
  2. a ledger WRITE FAILS and the order goes through, between the last check and activation;
  3. (the same hole, generally) any order attempt the ledger did not hear about.
Each still wrote a write-ahead intent. The sweep turns that intent into counted exposure before
the next order is judged.
"""
import copy
import os

os.environ.pop("EXEC_UNIT_LEDGER", None)
import executor as ex
import registry as _registry
import review_integration as ri
import review_intents as RI
import review_store_registry as _rs
import review_unit_reservation as R

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


PLAY = {"sport": "NBA", "game": "Los Angeles Lakers @ Boston Celtics", "bet": "Under 225.5 (-110)"}
DK = ex.derive_key(PLAY)
KEY = ri.key_from_registry(DK)


def intent(cid, stake=220.0, book="prophetx", key=None, source="r1", when="2026-11-23T11:00:00Z"):
    return {"key": key if key is not None else "r1|" + DK, "source": source, "intent": True,
            "client_id": cid, "decided_utc": when,
            "live_order": {"status": "placed", "order_id": "intent-" + cid, "book": book,
                           "asked_stake": stake, "filled_stake": None, "client_id": cid,
                           "intent": True}}


class Reg:
    """The registry file: intents and the ledger in one blob, one sha."""

    def __init__(self, seeded=True, intents=None):
        self.data = {"intents": list(intents or []),
                     "unit_reservations": {"legs": [], **({"seeded": True} if seeded else {})}}
        self.n, self.fail_puts, self.readable = 1, 0, True

    def _fetch(self):
        return (copy.deepcopy(self.data), f"s{self.n}") if self.readable else (None, None)

    def _put_with_sha(self, merged, sha):
        if self.fail_puts:
            self.fail_puts -= 1
            return False
        if sha != f"s{self.n}":
            return False
        self.data, self.n = copy.deepcopy(merged), self.n + 1
        return True

    def store(self):
        return _rs.RegistryStore(self)

    def legs(self):
        return self.data["unit_reservations"]["legs"]


def run(reg, mode, fn):
    keep = (_registry._fetch, _registry._put_with_sha)
    _registry._fetch, _registry._put_with_sha = reg._fetch, reg._put_with_sha
    os.environ["EXEC_UNIT_LEDGER"] = mode
    try:
        return fn()
    except Exception as e:
        return e
    finally:
        _registry._fetch, _registry._put_with_sha = keep
        os.environ.pop("EXEC_UNIT_LEDGER", None)


def order(cid, bet="Under 225.5 (-110)", risk=220.0, shown=-110, line=225.5, book="prophetx"):
    return {"live": {"risk": risk, "shown": shown, "unit": 200.0, "book": book, "line": line,
                     "client_id": cid}, "play": dict(PLAY, bet=bet)}


def place(reg, mode, cid, **kw):
    """What the executor does for one order: write the intent FIRST, then consult the ledger."""
    reg.data["intents"].append(intent(cid, stake=kw.get("risk", 220.0), book=kw.get("book", "prophetx")))
    return run(reg, mode, lambda: ex._unit_ledger_guard(order(cid, **kw), "live_order",
                                                        kw.get("book", "prophetx")))


# ---------------------------------------------------------------- CASE 1: an older run in flight
reg = Reg()
place(reg, "off", "old-run-1")                      # a flag-OFF run places: intent only, no ledger
ok("an order from a flag-off run is in no ledger entry - the hole", reg.legs() == [])
out = place(reg, "on", "new-1", bet="Under 226.5 (-108)", shown=-108, line=226.5)
ok("CASE 1: the next order on that play - an ADJACENT line - is REFUSED once enforcing",
   isinstance(out, R.ReservationRefused), repr(out))
ok("because the older run's order was swept in at its full asked stake first",
   [(l["intent_cid"], l["asked_stake"], l["status"]) for l in reg.legs()]
   == [("old-run-1", 220.0, "open")], str(reg.legs()))
ok("with no time cutoff involved: the sweep is by identity, whenever the order was placed",
   "cutoff" not in open("review_intents.py", encoding="utf-8").read().split('"""', 2)[2].lower())

reg = Reg()
place(reg, "record", "rec-1")
reg.data["intents"].append(intent("zombie-1", book="novig"))    # a zombie run, during recording
out = place(reg, "on", "new-2", bet="Under 224.5 (-112)", shown=-112, line=224.5)
ok("CASE 1: an older run that submits DURING recording is counted too",
   isinstance(out, R.ReservationRefused)
   and {l.get("intent_cid") for l in reg.legs()} == {"rec-1", "zombie-1"})

# ---------------------------------------------------------------- CASE 2: a failed ledger write
reg = Reg()
reg.fail_puts = 99
out = place(reg, "record", "lost-1")
ok("CASE 2: a record-only write that fails does not block the order", out is None)
ok("and leaves nothing in the ledger - the order went through unrecorded", reg.legs() == [])
reg.fail_puts = 0
out = place(reg, "on", "after-1", bet="Under 226.5 (-108)", shown=-108, line=226.5)
ok("CASE 2: the unrecorded order still counts - the next order on that play is REFUSED",
   isinstance(out, R.ReservationRefused), repr(out))
ok("it is in the ledger at its full asked stake, whatever its fill turns out to be",
   any(l.get("intent_cid") == "lost-1" and l["asked_stake"] == 220.0 and l["status"] == "open"
       for l in reg.legs()))

reg = Reg()
place(reg, "record", "ok-1", risk=110.0)
reg.fail_puts = 99
place(reg, "record", "lost-2", risk=110.0, bet="Under 226.5 (-108)", shown=-108, line=226.5)
reg.fail_puts = 0
ok("between the last check and activation: one recorded, one lost",
   [l.get("intent_cid") for l in reg.legs()] == ["ok-1"])
out = place(reg, "on", "act-1", risk=110.0, bet="Under 224.5 (-112)", shown=-112, line=224.5)
ok("the FIRST order after activation is judged against both, and refused",
   isinstance(out, R.ReservationRefused), repr(out))

# ---------------------------------------------------------------- the sweep itself
reg = Reg()
place(reg, "on", "a-1", risk=110.0)
ok("an order's own intent is not swept in ahead of its own reservation",
   [(l.get("intent_cid"), l.get("swept")) for l in reg.legs()] == [("a-1", None)], str(reg.legs()))
c = RI.sweep(reg.store(), reg.data["intents"])
ok("a reserved order is represented by its client id and never added twice",
   c["represented"] == 1 and c["added"] == 0 and len(reg.legs()) == 1, str(c))
out = place(reg, "on", "a-2", risk=110.0, bet="Under 226.5 (-110)", shown=-110, line=226.5)
ok("a second half-unit on the play is granted", not isinstance(out, Exception), repr(out))
out = place(reg, "on", "a-3", risk=110.0, bet="Under 224.5 (-112)", shown=-112, line=224.5)
ok("a third is refused", isinstance(out, R.ReservationRefused))
n_before = len(reg.legs())
c = RI.sweep(reg.store(), reg.data["intents"])
ok("a REFUSED attempt is never counted as an order by a later sweep",
   c["refused_unsent"] == 1 and c["added"] == 0 and len(reg.legs()) == n_before, str(c))
ok("so the play holds exactly one unit, not one and a half",
   abs(sum(R.leg_fraction(l) for l in reg.legs()) - 1.0) < 1e-9)

# seeded positions absorb their own intents, one for one
reg = Reg(seeded=False)
R.backfill(reg.store(), [{"key": KEY, "order_id": "prophetx|v1", "asked_stake": 220.0,
                          "american": -110, "unit": 200.0,
                          "actor": ri.actor_for("backfill", "live_order", "prophetx")}], "seed")
c = RI.sweep(reg.store(), [intent("pre-1"), intent("pre-2")])
ok("an intent for an order the SEED already holds is absorbed, not double-counted",
   c["absorbed_by_seed"] == 1, str(c))
ok("but a second intent with no seeded order behind it IS added",
   c["added"] == 1 and len(reg.legs()) == 2, str(c))
c = RI.sweep(reg.store(), [intent("pre-1"), intent("pre-2")])
ok("the sweep is idempotent", c["added"] == 0 and len(reg.legs()) == 2, str(c))

# valuation is an upper bound; nothing is guessed
reg = Reg()
c = RI.sweep(reg.store(), [intent("u-1", stake=110.0, source="muse", key=DK)])
ok("an intent whose lane cannot be read is valued at the SMALLEST unit and reported",
   c["added"] == 1 and c["added_lane_unknown"] == 1 and reg.legs()[0]["unit"] == 200.0, str(c))
ok("an intent is counted as stake at risk, which is never below the to-win measure",
   abs(R.leg_fraction(reg.legs()[0]) - 110.0 / 200.0) < 1e-9)
c = RI.sweep(reg.store(), [intent("bad-1", key="not-a-key"), intent("", key=DK),
                           intent("bad-3", stake=0), intent("bad-4", book="")])
ok("an intent that is not an identity is counted and reported, never placed in a budget",
   c["unkeyable"] == 4 and c["added"] == 0, str(c))
try:
    R.claim_dispatched(reg.store(), KEY, 50.0, "novig", "new-cid")
    claimed = True
except R.ReservationRefused:
    claimed = False
ok("a new Novig order cannot claim a swept-in position", claimed is False)

# fail closed when enforcing, never block when recording
for label, broke in (("the intents cannot be read", lambda r: setattr(r, "readable", False)),
                     ("the ledger is not seeded", None)):
    reg = Reg(seeded=(broke is not None))
    if broke:
        reg.data["intents"].append(intent("x"))
    r1 = order("f-1")
    keep = (_registry._fetch, _registry._put_with_sha)
    _registry._fetch, _registry._put_with_sha = reg._fetch, reg._put_with_sha
    if broke:
        broke(reg)
    os.environ["EXEC_UNIT_LEDGER"] = "on"
    try:
        ex._unit_ledger_guard(r1, "live_order", "prophetx")
        res_on = None
    except Exception as e:
        res_on = e
    os.environ["EXEC_UNIT_LEDGER"] = "record"
    try:
        res_rec = ex._unit_ledger_guard(r1, "live_order", "prophetx")
        rec_raised = False
    except Exception:
        rec_raised = True
    _registry._fetch, _registry._put_with_sha = keep
    os.environ.pop("EXEC_UNIT_LEDGER", None)
    ok(f"ENFORCING: when {label}, the order is REFUSED", isinstance(res_on, Exception), repr(res_on))
    ok(f"RECORDING: when {label}, the order is never blocked", rec_raised is False)

src = open("executor.py", encoding="utf-8").read()
g = src.split("def _unit_ledger_guard(")[1].split("\ndef ")[0]
ok("when enforcing, the sweep runs BEFORE the reservation is attempted",
   g.index("_unit_ledger_sweep(store, _reg") < g.index("ri.guard_or_refuse("))
ok("and the reservation carries the intent's client id",
   'intent_cid=lv.get("client_id")' in g)
ok("the sweep's log lines are counts only", "unit ledger: intent sweep added" in src
   and "INTENT SWEEP FAILED" in src)
ok("the guard is still reached only after the write-ahead intent",
   src.index('i_ok, cid = journal_intent(r, lv.get("book", "prophetx")')
   < src.index('_unit_ledger_guard(r, "live_order", "prophetx")'))

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
