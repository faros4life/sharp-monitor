#!/usr/bin/env python3
"""REVIEW ONLY. The ledger is a superset of every order attempt - with no pause and no cutoff.

THE ROWS IN THIS TEST COME FROM THE PRODUCTION WRITERS. The first version built its own
"intent" fixtures and put them in the registry's `intents` list, which is where the sweep looked
and where nothing in the order path writes; the tests passed and the first production dry run
read zero rows. Here the pre-order row is written by executor.journal_intent(), the confirmed row
by executor.journal_order() and the void by executor.void_intent(), all through the real
registry.put_rows() merge into `orders`. Only the network is stubbed.

Cases: an older run still in flight; a ledger write that fails; an order placed between the last
check and activation; a resting order (which leaves BOTH a pending and a confirmed record in one
row); a voided attempt; a refused attempt; top-ups that share a row.
"""
import copy
import os

os.environ.pop("EXEC_UNIT_LEDGER", None)
import executor as ex
import registry as _registry
import review_integration as ri
import review_intents as RI
import review_replay as RR
import review_seed as S
import review_store_registry as _rs
import review_unit_reservation as R

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


PLAY = {"sport": "NBA", "game": "Los Angeles Lakers @ Boston Celtics", "bet": "Under 225.5 (-110)",
        "source": "r1", "start_utc": "2026-11-24T00:00:00Z"}
DK = ex.derive_key(PLAY)
KEY = ri.key_from_registry(DK)


class Reg:
    """The registry file - order rows and the ledger in ONE blob with one sha, as in production."""

    def __init__(self, seeded=True):
        self.data = {"orders": [], "intents": [],
                     "unit_reservations": {"legs": [], **({"seeded": True} if seeded else {})}}
        self.n, self.fail_ledger, self.readable, self.venue = 1, 0, True, 0

    def put_rows(self, rows):                      # registry.put_rows()'s own merge, verbatim
        for r in rows:
            rid = _registry._rid(r)
            if rid:
                _registry._upsert(self.data["orders"], dict(r, _rid=rid), key="_rid")
        self.n += 1
        return True

    def _fetch(self):
        return (copy.deepcopy(self.data), f"s{self.n}") if self.readable else (None, None)

    def _put_with_sha(self, merged, sha):
        if self.fail_ledger:
            self.fail_ledger -= 1
            return False
        if sha != f"s{self.n}":
            return False
        self.data, self.n = copy.deepcopy(merged), self.n + 1
        return True

    def store(self):
        return _rs.RegistryStore(self)

    def legs(self):
        return self.data["unit_reservations"]["legs"]

    def rows(self):
        return self.data["orders"]


def wire(reg):
    keep = {k: getattr(_registry, k) for k in ("_fetch", "_put_with_sha", "put_rows", "load",
                                               "enabled", "claim_submission",
                                               "release_submission", "invalidate")}
    keep_ex = {k: getattr(ex, k) for k in ("send", "tg_push", "intent_readable")}
    _registry._fetch, _registry._put_with_sha = reg._fetch, reg._put_with_sha
    _registry.put_rows, _registry.load = reg.put_rows, (lambda: reg.data)
    _registry.enabled = lambda: True
    _registry.claim_submission = lambda k, c: True
    _registry.release_submission = lambda *a, **k: True
    _registry.invalidate = lambda: None
    ex.send = lambda *a, **k: None
    ex.tg_push = lambda *a, **k: None
    ex.intent_readable = lambda cid: False

    def undo():
        for k, v in keep.items():
            setattr(_registry, k, v)
        for k, v in keep_ex.items():
            setattr(ex, k, v)
        os.environ.pop("EXEC_UNIT_LEDGER", None)
    return undo


def attempt(reg, mode, bet="Under 225.5 (-110)", risk=220.0, shown=-110, line=225.5,
            book="prophetx", confirm=True, void=False, rest=False):
    """One order, start to finish, as the executor does it: pre-order row, ledger, venue, journal."""
    undo = wire(reg)
    os.environ["EXEC_UNIT_LEDGER"] = mode
    r = {"live": {"risk": risk, "shown": shown, "unit": 200.0, "book": book, "line": line},
         "play": dict(PLAY, bet=bet, play_key="r1|" + DK)}
    try:
        okk, cid = ex.journal_intent(r, book, risk)          # PRODUCTION pre-order writer
        assert okk and cid, "journal_intent refused"
        r["live"]["client_id"] = cid
        try:
            ex._unit_ledger_guard(r, "rest_bid" if rest else "live_order", book)
            out = None
        except Exception as e:
            out = e
        if out is None and void:
            ex.void_intent(cid, book, "refused before submission", key=r["play"]["play_key"])
        elif out is None and confirm:
            reg.venue += 1
            ex.journal_order(r, {"order_id": f"venue-{reg.venue}", "book": book,
                                 "asked_stake": risk, "limit": shown, "filled_stake": None},
                             is_rest=rest, cid=cid)           # PRODUCTION confirmed-row writer
        return out, cid
    finally:
        undo()


# ---------------------------------------------------------------- the production row shapes
reg = Reg()
_, cid = attempt(reg, "off", confirm=False)
row = reg.rows()[0]
ok("journal_intent writes the pre-order row into `orders`, not `intents`",
   len(reg.rows()) == 1 and reg.data["intents"] == [])
ok("keyed by the executor's client id, with an intent-<cid> order id",
   row.get("client_id") == cid and row["live_order"]["order_id"] == "intent-" + cid
   and row["live_order"].get("intent") is True, str(row)[:200])
ok("the old reader's source is empty for this row - which is why it saw nothing",
   not hasattr(RI, "read_intents") and RI.read_rows(reg) == reg.rows())
reg = Reg()
_, cid = attempt(reg, "off")
ok("journal_order upserts the confirmed row over the pre-order row: one row per attempt",
   len(reg.rows()) == 1 and reg.rows()[0]["live_order"]["order_id"] == "venue-1"
   and reg.rows()[0]["live_order"].get("client_id") == cid, str(reg.rows())[:300])
reg = Reg()
attempt(reg, "off", rest=True)
legs, _, _ = RR.backfill_candidates(reg.rows())
ok("a RESTING order leaves a pending record AND a confirmed record in the same row",
   sorted((l["field"], l["intent_only"]) for l in legs) == [("live_order", True), ("live_rest", False)],
   str([(l["field"], l["intent_only"]) for l in legs]))
seed, sm, why = S.build(legs, [])
ok("the seed proves them one order BY CLIENT ID and retains it once",
   why is None and sm["retained"] == 1 and sm["duplicate"] == 1
   and list(sm["dup_reasons"]) == ["same client id, same row in two fields: pending record "
                                   "and its confirmed order"], f"{why} {sm}")
ok("the CONFIRMED record is the one kept, at its real price",
   seed[0]["venue_order_id"] == "venue-1" and seed[0]["american"] == -110
   and sm["pending_valued_as_risk"] == 0, str(seed))
ok("and its accounting closes: retained + zero + never-submitted + duplicate = input",
   sm["retained"] + sm["proven_zero"] + sm["never_submitted"] + sm["duplicate"] == sm["input"])

# ---------------------------------------------------------------- CASE 1: an older run in flight
reg = Reg()
attempt(reg, "off")                                  # a flag-OFF run: order rows, no ledger entry
ok("an order from a flag-off run is in no ledger entry - the hole", reg.legs() == [])
out, _ = attempt(reg, "on", bet="Under 226.5 (-110)", line=226.5)
ok("CASE 1: the next order on that play - an ADJACENT line - is REFUSED once enforcing",
   isinstance(out, R.ReservationRefused), repr(out))
ok("because the older run's order was swept in first, under its venue order id, at full stake",
   [(l["order_id"], l["asked_stake"], l["status"], l.get("swept")) for l in reg.legs()]
   == [("prophetx|venue-1", 220.0, "open", True)], str(reg.legs()))

reg = Reg()
attempt(reg, "off", confirm=False, book="novig")     # an older run mid-send: pre-order row only
out, _ = attempt(reg, "on", bet="Under 226.5 (-110)", line=226.5)
ok("CASE 1: an in-flight order whose send is NOT YET CONFIRMED is counted at its full stake",
   isinstance(out, R.ReservationRefused)
   and [(l["asked_stake"], l["american"]) for l in reg.legs()] == [(220.0, 100)], str(reg.legs()))
undo = wire(reg)
reg.put_rows([{"client_id": reg.rows()[0]["client_id"],
               "live_order": {"status": "placed", "order_id": "venue-late", "book": "novig",
                              "asked_stake": 220.0, "limit": -110, "client_id": reg.rows()[0]["client_id"],
                              "intent": False}}])
c = RI.sweep(reg.store(), reg.rows())
undo()
ok("when its confirmation arrives LATE, the same order is recognised by client id, not re-added",
   c["represented_by_client_id"] == 1 and c["added"] == 0 and len(reg.legs()) == 1, str(c))

# ---------------------------------------------------------------- CASE 2: a failed ledger write
reg = Reg()
reg.fail_ledger = 99
out, _ = attempt(reg, "record")
ok("CASE 2: a record-only write that fails does not block the order", out is None, repr(out))
ok("and the order went through with nothing in the ledger", reg.legs() == [] and len(reg.rows()) == 1)
reg.fail_ledger = 0
out, _ = attempt(reg, "on", bet="Under 226.5 (-110)", line=226.5)
ok("CASE 2: it still counts - the next order on that play is REFUSED",
   isinstance(out, R.ReservationRefused), repr(out))

reg = Reg()
attempt(reg, "record", risk=110.0)
reg.fail_ledger = 99
attempt(reg, "record", risk=110.0, bet="Under 226.5 (-110)", line=226.5)
reg.fail_ledger = 0
ok("between the last check and activation: one recorded, one lost", len(reg.legs()) == 1)
out, _ = attempt(reg, "on", risk=110.0, bet="Under 224.5 (-110)", line=224.5)
ok("the FIRST order after activation is judged against both, and refused",
   isinstance(out, R.ReservationRefused), repr(out))
ok("with each of the two earlier orders in the ledger exactly once",
   len(reg.legs()) == 2 and abs(sum(R.leg_fraction(l) for l in reg.legs()) - 1.0) < 1e-9,
   str([(l["order_id"], l["asked_stake"]) for l in reg.legs()]))

# ---------------------------------------------------------------- exactly once, through confirmation
reg = Reg()
out, cid = attempt(reg, "on", risk=110.0)
ok("an enforced order is reserved under its client id", out is None
   and [l.get("intent_cid") for l in reg.legs()] == [cid])
undo = wire(reg)
c = RI.sweep(reg.store(), reg.rows())
undo()
ok("its confirmed row is the same order: represented by client id, not added again",
   c["represented_by_client_id"] == 1 and c["added"] == 0 and len(reg.legs()) == 1, str(c))
out, _ = attempt(reg, "on", risk=110.0, bet="Under 226.5 (-110)", line=226.5)
ok("a second half unit on the play is granted", out is None, repr(out))
out, _ = attempt(reg, "on", risk=110.0, bet="Under 224.5 (-110)", line=224.5, confirm=False)
ok("a third is refused", isinstance(out, R.ReservationRefused), repr(out))
undo = wire(reg)
c = RI.sweep(reg.store(), reg.rows())
undo()
ok("a REFUSED attempt's pre-order row is never counted as an order",
   c["refused_unsent"] == 1 and c["added"] == 0, str(c))
ok("so the play holds exactly one unit", abs(sum(R.leg_fraction(l) for l in reg.legs()) - 1.0) < 1e-9)

reg = Reg()
attempt(reg, "off", void=True)
legs, _, _ = RR.backfill_candidates(reg.rows())
ok("void_intent marks the row voided", len(legs) == 1 and legs[0]["voided"] is True, str(legs))
undo = wire(reg)
c = RI.sweep(reg.store(), reg.rows())
undo()
ok("a VOIDED attempt was never submitted and is not counted", c["never_submitted"] == 1
   and c["added"] == 0 and reg.legs() == [], str(c))
seed, sm, why = S.build(legs, [])
ok("the seed gives it the never_submitted disposition", why is None and sm["never_submitted"] == 1
   and sm["retained"] == 0)

# top-ups: two real orders in one row must stay two orders
legs = [{"key": KEY, "field": "live_order", "order_id": "v-1", "book": "prophetx", "cid": "c1",
         "asked_stake": 110.0, "american": -110, "unit": 200.0, "lane": "r1", "row_index": 0,
         "evidence_class": RR.PROVEN, "venue_class": "FILLED"},
        {"key": KEY, "field": "live_more", "order_id": "v-2", "book": "prophetx", "cid": "c1",
         "asked_stake": 110.0, "american": -110, "unit": 200.0, "lane": "r1", "row_index": 0,
         "evidence_class": RR.PROVEN, "venue_class": "FILLED"}]
seed, sm, why = S.build(legs, [])
ok("two CONFIRMED orders with different venue ids are two orders even with one client id",
   why is None and sm["retained"] == 2 and sm["duplicate"] == 0, f"{why} {sm}")
ok("a row's client id is not inherited by its live_more top-ups",
   [l["cid"] for l in RR.backfill_candidates([{"key": "r1|" + DK, "client_id": "rowcid",
        "live_order": {"order_id": "a", "book": "novig", "status": "placed"},
        "live_more": [{"order_id": "b", "book": "novig", "status": "placed"}]}])[0]]
   == ["rowcid", None])
ok("the same play, venue and stake alone never makes a duplicate",
   S.build([dict(legs[0], order_id="x1", cid=None), dict(legs[0], order_id="x2", cid=None)],
           [])[1]["duplicate"] == 0)
seed, sm, why = S.build([dict(legs[0]), dict(legs[0], key="nba|other @ game|total|under")], [])
ok("one venue order id under two different plays is UNRESOLVED and refuses the seed",
   seed == [] and "two play keys" in str(why), str(why))

# the seed's proven-zero exclusions survive the sweep
reg = Reg(seeded=False)
attempt(reg, "off")
attempt(reg, "off", bet="Over 225.5 (-110)")
legs, _, _ = RR.backfill_candidates(reg.rows())
legs[0].update(evidence_class=RR.PROVEN, venue_class="FILLED")
legs[1].update(evidence_class=RR.PROVEN, venue_class="TERMINAL ZERO FILL")
seed, sm, why = S.build(legs, [])
R.backfill(reg.store(), seed, "seed")
zero = [f"{l['book']}|{l['order_id']}" for l in legs if l["disposition"] == "proven_zero"]
RI.note_excluded(reg.store(), zero)
undo = wire(reg)
c = RI.sweep(reg.store(), reg.rows())
undo()
ok("after the seed, the sweep finds every row represented and adds nothing",
   c["added"] == 0 and c["represented_by_order_id"] == 2 and len(reg.legs()) == 1, str(c))
ok("so seed plus sweep account for each existing order exactly once",
   sm["retained"] + sm["proven_zero"] == 2 == c["legs"])

# fail closed when enforcing, never block when recording
for label, prep in (("the order rows cannot be read", lambda r: setattr(r, "readable", False)),
                    ("the ledger is not seeded", None)):
    reg = Reg(seeded=(prep is not None))
    undo = wire(reg)
    if prep:
        prep(reg)
    r1 = {"live": {"risk": 220.0, "shown": -110, "unit": 200.0, "book": "prophetx",
                   "line": 225.5, "client_id": "x1"}, "play": dict(PLAY, play_key="r1|" + DK)}
    os.environ["EXEC_UNIT_LEDGER"] = "on"
    try:
        ex._unit_ledger_guard(r1, "live_order", "prophetx")
        on_res = None
    except Exception as e:
        on_res = e
    os.environ["EXEC_UNIT_LEDGER"] = "record"
    try:
        ex._unit_ledger_guard(r1, "live_order", "prophetx")
        rec_raised = False
    except Exception:
        rec_raised = True
    undo()
    ok(f"ENFORCING: when {label}, the order is REFUSED", isinstance(on_res, Exception), repr(on_res))
    ok(f"RECORDING: when {label}, the order is never blocked", rec_raised is False)

src = open("executor.py", encoding="utf-8").read()
g = src.split("def _unit_ledger_guard(")[1].split("\ndef ")[0]
ok("when enforcing, the sweep runs BEFORE the reservation is attempted",
   g.index("_unit_ledger_sweep(store, _reg") < g.index("ri.guard_or_refuse("))
ok("the executor's sweep reads the order rows", "_ri2.read_rows(registry_module)" in src
   and "read_intents" not in src)
ok("no time cutoff is used", "cutoff" not in open("review_intents.py", encoding="utf-8").read()
   .split('"""', 2)[2].lower())

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
