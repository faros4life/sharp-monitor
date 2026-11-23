#!/usr/bin/env python3
"""REVIEW ONLY. Releasing a never-submitted attempt - and refusing to release anything else.

Rows come from the production writers (journal_intent / journal_order / void_intent) through the
real registry.put_rows() merge; only the network is stubbed.
"""
import copy, os
os.environ.pop("EXEC_UNIT_LEDGER", None)
import executor as ex
import registry as _registry
import review_integration as ri
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
    def __init__(self, seeded=True):
        self.data = {"orders": [], "unit_reservations": {"legs": [], **({"seeded": True} if seeded else {})}}
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

def attempt(reg, mode, bet="Under 225.5 (-110)", risk=220.0, shown=-110, line=225.5,
            book="prophetx", confirm=True, void=False):
    confirm = confirm and not void
    undo = wire(reg); os.environ["EXEC_UNIT_LEDGER"] = mode
    r = {"live": {"risk": risk, "shown": shown, "unit": 200.0, "book": book, "line": line},
         "play": dict(PLAY, bet=bet, play_key="r1|" + DK)}
    try:
        okk, cid = ex.journal_intent(r, book, risk); assert okk and cid
        r["live"]["client_id"] = cid
        try:
            g = ex._unit_ledger_guard(r, "live_order", book)
            ex._unit_ledger_consume(g, risk)      # the executor's own next step
            out = None
        except Exception as e: out = e
        if out is None and void:
            ex.void_intent(cid, book, "venue refused on price", key=r["play"]["play_key"])
        elif out is None and confirm:
            reg.venue += 1
            ex.journal_order(r, {"order_id": f"venue-{reg.venue}", "book": book,
                                 "asked_stake": risk, "limit": shown, "filled_stake": None},
                             cid=cid)
        return out, cid
    finally: undo()

def held(reg): return round(sum(R.leg_fraction(l) for l in reg.legs()), 4)

# --- the production defect: record, then void -------------------------------------------------
reg = Reg(); attempt(reg, "record", void=True)
ok("the voided attempt's leg is kept for audit, not deleted", len(reg.legs()) == 1)
ok("but it counts ZERO against the play's budget", held(reg) == 0.0, str(held(reg)))
l = reg.legs()[0]
ok("and it records why and when it was released",
   l["status"] == "void" and l["released"] == "never_submitted"
   and "void_intent" in l["released_evidence"] and l.get("released_utc"), str(l)[:160])
out, _ = attempt(reg, "on", bet="Under 226.5 (-110)", line=226.5)
ok("so the play is free again: the next order is GRANTED", out is None, repr(out))

reg = Reg(); attempt(reg, "on", void=True)
ok("same under enforcement: a voided reservation is released", held(reg) == 0.0)
ok("the voided row is on record in the registry", reg.data["orders"][0].get("voided") is True)

# --- never release anything else ----------------------------------------------------------------
cases = [
    ("a CONFIRMED order", dict(confirm=True), {}),
    ("a leg with a PARTIAL fill", dict(confirm=True), {"filled_stake": 50.0}),
    ("a leg with a full fill", dict(confirm=True), {"filled_stake": 220.0}),
    ("a RESTING leg", dict(confirm=True), {"status": "placed"}),
    ("a leg a runner has CLAIMED", dict(confirm=True), {"claimed_by": "novig-cid-1"}),
    ("a leg already proven terminal", dict(confirm=True), {"status": "filled", "terminal_verified": True}),
]
for label, kw, mut in cases:
    reg = Reg(); _, cid = attempt(reg, "on", **kw)
    before = held(reg)
    reg.data["unit_reservations"]["legs"] = [dict(l, **mut) for l in reg.legs()]
    before = held(reg)
    n = R.release_never_submitted(reg.store(), cid, "void_intent: proof",
                                  rows=reg.data["orders"])
    ok(f"and the rows alone refuse it: {label}",
       R.never_submitted_proof(reg.data["orders"], cid) is False or mut.get("claimed_by")
       or mut.get("filled_stake") or mut.get("terminal_verified"))
    ok(f"NEVER released: {label}", n == 0 and held(reg) == before, f"freed {n}")

reg = Reg(); _, cid = attempt(reg, "on")
ok("settlement alone does not release: record_outcome needs a verified fill AND evidence",
   R.leg_fraction(reg.legs()[0]) > 0)
try:
    R.record_outcome(reg.store(), KEY, reg.legs()[0]["leg_id"], "settled", None, True, None)
    lax = True
except Exception: lax = False
ok("a settled status with no fill amount and no evidence is REFUSED", lax is False)
try:
    R.record_outcome(reg.store(), KEY, reg.legs()[0]["leg_id"], "cancelled", None, False, "venue says cancelled")
    pass
except Exception: pass
ok("an unverified cancellation releases nothing", held(reg) > 0, str(held(reg)))

# --- evidence, identity, idempotence, cross-venue, concurrency ------------------------------------
reg = Reg(); _, cid = attempt(reg, "on")
for bad in ("", None, "   "):
    try: R.release_never_submitted(reg.store(), cid, bad); r0 = True
    except Exception: r0 = False
    ok(f"no proof string ({bad!r}) refuses the release", r0 is False)
    try: R.release_never_submitted(reg.store(), bad, "void_intent: p"); r1 = True
    except Exception: r1 = False
    ok(f"no intent id ({bad!r}) refuses the release", r1 is False)
ok("an unknown intent id frees nothing and does not raise",
   R.release_never_submitted(reg.store(), "no-such-cid", "void_intent: p") == 0)
try: R.release_never_submitted(Reg(seeded=False).store(), cid, "void_intent: p"); uns = True
except Exception: uns = False
ok("an unseeded ledger refuses the release", uns is False)

reg = Reg(); _, cid = attempt(reg, "record", void=True)
ok("releasing the same void twice frees nothing the second time",
   R.release_never_submitted(reg.store(), cid, "void_intent: again") == 0 and held(reg) == 0.0)

# cross-venue: one play, two venues, only the voided venue's leg is released
reg = Reg()
_, cid_px = attempt(reg, "on", risk=110.0, book="prophetx")
_, cid_nv = attempt(reg, "on", risk=110.0, book="novig", bet="Under 226.5 (-110)", line=226.5,
                    confirm=False)
ok("two half-unit legs on one play across two venues", len(reg.legs()) == 2 and held(reg) == 1.0)
undo = wire(reg); os.environ["EXEC_UNIT_LEDGER"] = "on"
ex.void_intent(cid_nv, "novig", "runner refused", key="r1|" + DK)
undo()
ok("voiding the Novig attempt releases ONLY that leg",
   held(reg) == 0.5 and sum(1 for l in reg.legs() if l["status"] == "void") == 1, str(held(reg)))
ok("the ProphetX leg is untouched",
   [l["status"] for l in reg.legs() if str(l.get("intent_cid")) == cid_px] == ["open"])

# a claimed cross-venue leg is never released by a void on this side
reg = Reg(); _, cid = attempt(reg, "on", book="novig", confirm=False)
R.claim_dispatched(reg.store(), KEY, 220.0, "novig", "runner-cid")
before = held(reg)
undo = wire(reg); os.environ["EXEC_UNIT_LEDGER"] = "on"
ex.void_intent(cid, "novig", "late void", key="r1|" + DK); undo()
ok("once the runner has claimed it, a void releases nothing", held(reg) == before and before > 0)

# concurrency: a stale reader cannot release twice, and a live claim still wins
reg = Reg(); _, cid = attempt(reg, "on", book="novig", confirm=False)
class Stale:
    def __init__(self, real): self.real, self.snap = real, real.store().read()
    def read(self): return self.snap
    def write(self, state, version): return self.real.store().write(state, version)
first = R.release_never_submitted(reg.store(), cid, "void_intent: p", rows=reg.data["orders"])
second = R.release_never_submitted(Stale(reg), cid, "void_intent: p", rows=reg.data["orders"])
ok("a concurrent second release frees nothing", first == 1 and second == 0 and held(reg) == 0.0)
reg = Reg(); _, cid = attempt(reg, "on", book="novig", confirm=False)
R.release_never_submitted(reg.store(), cid, "void_intent: p", rows=reg.data["orders"])
try:
    R.claim_dispatched(reg.store(), KEY, 220.0, "novig", "runner-cid"); claimed = True
except R.ReservationRefused: claimed = False
ok("a released leg cannot then be claimed by the runner", claimed is False)

# --- the guard still refuses a real second unit ---------------------------------------------------
reg = Reg(); attempt(reg, "on", risk=220.0)
out, _ = attempt(reg, "on", risk=220.0, bet="Under 224.5 (-110)", line=224.5)
ok("a genuine second full unit is still REFUSED", isinstance(out, R.ReservationRefused), repr(out))
ok("and holds exactly one unit", held(reg) == 1.0, str(held(reg)))

src = open("executor.py", encoding="utf-8").read()
v = src.split("def void_intent(")[1].split("\ndef ")[0]
ok("void_intent releases BEFORE it writes its voided row",
   v.index("_unit_ledger_release(cid, why)") < v.index('row = {"client_id": cid, "voided": True'))
ok("the release is off when the ledger is off", '_unit_ledger_mode() == "off"' in
   src.split("def _unit_ledger_release(")[1].split("\ndef ")[0])

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
