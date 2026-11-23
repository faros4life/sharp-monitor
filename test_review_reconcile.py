#!/usr/bin/env python3
"""REVIEW ONLY. A leg stops holding a whole unit once the venue says what it matched.

Rows come from the production writers; only the network is stubbed. The question every test asks
is how much of the play's unit is still held.
"""
import copy, os
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

PLAY = {"sport": "NBA", "game": "Los Angeles Lakers @ Boston Celtics", "bet": "Under 225.5 (-110)",
        "source": "r1", "start_utc": "2026-11-24T00:00:00Z"}
DK = ex.derive_key(PLAY); KEY = ri.key_from_registry(DK)

class Reg:
    def __init__(self):
        self.data = {"orders": [], "unit_reservations": {"legs": [], "seeded": True}}
        self.n, self.venue = 1, 0
    def put_rows(self, rows):
        for r in rows:
            rid = _registry._rid(r)
            if rid: _registry._upsert(self.data["orders"], dict(r, _rid=rid), key="_rid")
        self.n += 1; return True
    def _fetch(self): return (copy.deepcopy(self.data), f"s{self.n}")
    def _put_with_sha(self, merged, sha):
        if sha != f"s{self.n}": return False
        self.data, self.n = copy.deepcopy(merged), self.n + 1; return True
    def store(self): return _rs.RegistryStore(self)
    def legs(self): return self.data["unit_reservations"]["legs"]

def wire(reg):
    keep = {k: getattr(_registry, k) for k in ("_fetch","_put_with_sha","put_rows","load","enabled",
                                               "claim_submission","release_submission","invalidate")}
    kex = {k: getattr(ex, k) for k in ("send","tg_push","intent_readable")}
    _registry._fetch, _registry._put_with_sha = reg._fetch, reg._put_with_sha
    _registry.put_rows, _registry.load = reg.put_rows, (lambda: reg.data)
    _registry.enabled = lambda: True
    _registry.claim_submission = lambda k, c: True
    _registry.release_submission = lambda *a, **k: True
    _registry.invalidate = lambda: None
    ex.send = lambda *a, **k: None; ex.tg_push = lambda *a, **k: None
    ex.intent_readable = lambda cid: False
    def undo():
        for k, v in keep.items(): setattr(_registry, k, v)
        for k, v in kex.items(): setattr(ex, k, v)
        os.environ.pop("EXEC_UNIT_LEDGER", None)
    return undo

def order(reg, risk=220.0, bet="Under 225.5 (-110)", line=225.5, book="prophetx", mode="on"):
    undo = wire(reg); os.environ["EXEC_UNIT_LEDGER"] = mode
    r = {"live": {"risk": risk, "shown": -110, "unit": 200.0, "book": book, "line": line},
         "play": dict(PLAY, bet=bet, play_key="r1|" + DK)}
    try:
        okk, cid = ex.journal_intent(r, book, risk); assert okk
        r["live"]["client_id"] = cid
        try:
            g = ex._unit_ledger_guard(r, "live_order", book); ex._unit_ledger_consume(g, risk); out = None
        except Exception as e: out = e
        reg.venue += 1
        return out, cid, f"venue-{reg.venue}", r
    finally: undo()

def settle(reg, r, cid, oid, status, filled, fill_read=None, book="prophetx"):
    """The executor's own confirmed-row writer, then the venue outcome on that row."""
    undo = wire(reg)
    try:
        ex.journal_order(r, {"order_id": oid, "book": book, "asked_stake": r["live"]["risk"],
                             "limit": -110, "filled_stake": filled}, cid=cid)
        row = next(x for x in reg.data["orders"] if str(x.get("client_id")) == cid)
        lo = row.get("live_order") or {}
        lo["status"], lo["filled_stake"] = status, filled
        if fill_read is not None: lo["fill_read"] = fill_read
    finally: undo()

def held(reg): return round(sum(R.leg_fraction(l) for l in reg.legs()), 4)
def recon(reg): return RI.reconcile_outcomes(reg.store(), reg.data["orders"])

# --- a cancelled order with a READ zero frees the play ------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
ok("the order holds a full unit while it is live", held(reg) == 1.0, str(held(reg)))
settle(reg, r, cid, oid, "canceled", 0.0, fill_read=True)
c = recon(reg)
ok("a cancelled order with a READ zero is released", c["released_zero_fill"] == 1 and held(reg) == 0.0,
   f"{c} {held(reg)}")
out, _, _, _ = order(reg, bet="Under 226.5 (-110)", line=226.5)
ok("so the play takes a new order again", out is None, repr(out))

# --- an UNREAD zero keeps holding ----------------------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "canceled", 0.0)                      # no fill_read flag
c = recon(reg)
ok("a cancelled order whose fill was never READ keeps the full hold",
   c["unread_zero_held"] == 1 and held(reg) == 1.0, f"{c} {held(reg)}")
settle(reg, r, cid, oid, "canceled", None)
ok("and a missing fill figure keeps it too", recon(reg)["unread_zero_held"] == 1 and held(reg) == 1.0)

# --- a partial fill frees only the unmatched part -------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "filled", 55.0)
c = recon(reg)
ok("a partly filled order holds only what it matched",
   c["reduced_to_fill"] == 1 and held(reg) == 0.25, f"{c} {held(reg)}")
ok("the leg records the fill and that it is verified",
   reg.legs()[0]["filled_stake"] == 55.0 and reg.legs()[0]["terminal_verified"] is True)
out, _, _, _ = order(reg, risk=165.0, bet="Under 226.5 (-110)", line=226.5)
ok("the freed three quarters can be used", out is None, repr(out))

# --- a fully filled order keeps its unit ----------------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "filled", 220.0)
recon(reg)
ok("a FULLY filled order still holds the whole unit", held(reg) == 1.0, str(held(reg)))
out, _, _, _ = order(reg, bet="Under 224.5 (-110)", line=224.5)
ok("and the play is still refused", isinstance(out, R.ReservationRefused), repr(out))

# --- settlement is not a release ------------------------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "settled", 220.0)
recon(reg)
ok("a SETTLED fill still holds what it matched - settling is not releasing", held(reg) == 1.0)
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "settled", 0.0)
ok("a settled row with an unread zero releases nothing",
   recon(reg)["unread_zero_held"] == 1 and held(reg) == 1.0)

# --- live rows are never touched ------------------------------------------------------------------
for st in ("placed", "open", "resting", "working"):
    reg = Reg(); _, cid, oid, r = order(reg)
    settle(reg, r, cid, oid, st, None)
    c = recon(reg)
    ok(f"a {st.upper()} row is left alone", c["still_live"] == 1 and held(reg) == 1.0, f"{c}")

# --- idempotence, regression and bad data ----------------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "filled", 55.0)
recon(reg); before = held(reg); c = recon(reg)
ok("a second pass changes nothing", c["already_settled"] == 1 and held(reg) == before)
settle(reg, r, cid, oid, "filled", 10.0)
recon(reg)
ok("a later callback cannot REDUCE a verified fill", held(reg) == before, str(held(reg)))
settle(reg, r, cid, oid, "placed", None)
recon(reg)
ok("and cannot reopen a verified terminal leg", reg.legs()[0]["status"] == "filled")
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "filled", 9999.0)
c = recon(reg)
ok("a fill ABOVE the ask is refused, and the leg keeps its hold",
   c["refused"] == 1 and held(reg) == 1.0, f"{c} {held(reg)}")

# --- a leg with no row, and an unseeded ledger ------------------------------------------------------
reg = Reg(); order(reg)
reg.data["orders"] = []
ok("a leg whose row is gone is left holding", recon(reg)["matched"] == 0 and held(reg) == 1.0)
reg2 = Reg(); reg2.data["unit_reservations"].pop("seeded")
try: RI.reconcile_outcomes(reg2.store(), []); uns = True
except Exception: uns = False
ok("an unseeded ledger refuses to reconcile", uns is False)

# --- cross-venue: only the settled venue's leg moves --------------------------------------------------
reg = Reg()
_, cid_a, oid_a, ra = order(reg, risk=110.0, book="prophetx")
_, cid_b, oid_b, rb = order(reg, risk=110.0, book="novig", bet="Under 226.5 (-110)", line=226.5)
settle(reg, rb, cid_b, oid_b, "canceled", 0.0, fill_read=True, book="novig")
recon(reg)
ok("only the cancelled venue's leg is released, the other still holds",
   held(reg) == 0.5 and sum(1 for l in reg.legs() if l.get("terminal_verified")) == 1, str(held(reg)))

# --- it runs inside the executor, before the guard -----------------------------------------------------
reg = Reg(); _, cid, oid, r = order(reg)
settle(reg, r, cid, oid, "canceled", 0.0, fill_read=True)
out, _, _, _ = order(reg, bet="Under 224.5 (-110)", line=224.5)
ok("the executor reconciles on its own pass: the next order is GRANTED without a manual step",
   out is None, repr(out))
ok("the cancelled leg was released by that pass, and the new order holds the unit instead",
   [(l["status"], l.get("terminal_verified")) for l in reg.legs()] == [("canceled", True), ("open", None)]
   and held(reg) == 1.0, str([(l["status"], l.get("filled_stake")) for l in reg.legs()]))
src = open("executor.py", encoding="utf-8").read()
g = src.split("def _unit_ledger_sweep(")[1].split("\ndef ")[0]
ok("reconciliation runs in the same pre-dispatch pass as the sweep", "reconcile_outcomes(store, rows)" in g)
ok("its log line is counts only", "unit ledger: reconciled" in g and "key" not in g.split("reconciled")[1][:120])

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
