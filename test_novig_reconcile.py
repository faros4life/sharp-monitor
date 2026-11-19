#!/usr/bin/env python3
"""Registry <-> Novig reconciliation (Peter, Nov 18). IMPLEMENTED, NOT ACTIVATED.

The trap this module exists for: the registry stores the venue's CLIENT ID in its own `order_id`
field. Joining registry.order_id to the venue's order_id matched 0 of 31 legs on the Nov 18 snapshot;
joining to the venue's client_id matched 31 of 31. A reconciliation written the obvious way would
find no record for any leg - and if it treated absence as evidence, would have "confirmed" zero fills
on eleven legs that were FILLED at the venue.

So the central assertion here is the negative one: a missing venue record NEVER releases money.
"""
from datetime import datetime, timezone

import novig_reconcile as nr

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


ASOF = datetime(2026, 11, 18, 23, 59, tzinfo=timezone.utc)
ORDERS = {"orders": [
    {"order_id": "01a1ef55-VENUE", "client_id": "fa7a84cb-CLIENT", "status": "OPEN",
     "filled_qty": 0, "qty": "41500", "price": "0.515", "placed_utc": "2026-11-18T15:45:06Z"},
    {"order_id": "01a1ef2c-VENUE", "client_id": "18aefa75-CLIENT", "status": "FILLED",
     "filled_qty": 18200, "qty": "18200", "price": "0.525", "placed_utc": "2026-11-18T15:00:59Z"},
    {"order_id": "0001-VENUE", "client_id": "d24d0e03-CLIENT", "status": "refused",
     "filled_qty": 0, "qty": "75000", "price": "0.5198", "placed_utc": "2026-11-14T01:00:00Z"},
    {"order_id": "0002-VENUE", "client_id": "5ab5d4ad-CLIENT", "status": "REJECTED",
     "filled_qty": 0, "qty": "40000", "price": "0.51", "placed_utc": "2026-11-15T01:00:00Z"},
    {"order_id": "0003-VENUE", "client_id": "partial-CLIENT", "status": "CANCELED",
     "filled_qty": 5000, "qty": "20000", "price": "0.50", "placed_utc": "2026-11-16T01:00:00Z"},
    {"order_id": "0004-VENUE", "client_id": "cancel-nofill-but-filled", "status": "CANCELED",
     "filled_qty": 0, "qty": "10000", "price": "0.50", "placed_utc": "2026-11-16T01:00:00Z"},
]}
FILLS = {"fills": [{"clientId": "18aefa75-CLIENT", "orderId": "01a1ef2c-VENUE", "fillId": "f1"},
                   {"clientId": "partial-CLIENT", "orderId": "0003-VENUE", "fillId": "f2"},
                   {"clientId": "cancel-nofill-but-filled", "orderId": "0004-VENUE", "fillId": "f3"}]}
BY, FB = nr.venue_index(ORDERS, FILLS)

# ---------------------------------------------------------------- 1. identifier normalization
ok("the index is keyed on the venue CLIENT id", set(BY) >= {"fa7a84cb-CLIENT", "18aefa75-CLIENT"})
ok("the venue ORDER id is not an index key", "01a1ef55-VENUE" not in BY)
ok("a registry order_id is read as a client id",
   nr.normalize_ids({"order_id": "fa7a84cb-CLIENT"})["client_id"] == "fa7a84cb-CLIENT")
ok("the true venue order id is carried separately, not overwritten",
   nr.normalize_ids({"order_id": "fa7a84cb-CLIENT", "venue_order_id": "01a1ef55-VENUE"})
   == {"client_id": "fa7a84cb-CLIENT", "venue_order_id": "01a1ef55-VENUE"})
ok("a leg with no identifier is UNKNOWN, never released",
   nr.classify({}, BY, FB)[0] == nr.UNKNOWN)

# ---------------------------------------------------------------- 2. classification
cases = [("fa7a84cb-CLIENT", nr.OPEN, "venue OPEN"),
         ("18aefa75-CLIENT", nr.FILLED, "venue FILLED"),
         ("d24d0e03-CLIENT", nr.TERMINAL, "refused, zero filled, no fill record"),
         ("5ab5d4ad-CLIENT", nr.TERMINAL, "REJECTED, zero filled, no fill record"),
         ("partial-CLIENT", nr.PARTIAL, "CANCELED after a partial fill"),
         ("cancel-nofill-but-filled", nr.UNKNOWN, "CANCELED at zero BUT a fill record exists")]
for cid, want, why in cases:
    got, ev = nr.classify({"order_id": cid}, BY, FB)
    ok(f"{why} -> {want}", got == want, got)

# ---------------------------------------------------------------- 3. the negative assertions
got, ev = nr.classify({"order_id": "NOT-IN-ANY-SNAPSHOT"}, BY, FB)
ok("a MISSING venue record is UNKNOWN, never TERMINAL", got == nr.UNKNOWN, got)
ok("a missing record releases NOTHING",
   nr.exposure_for({"order_id": "NOT-IN-ANY-SNAPSHOT", "asked_stake": 214.0, "resting": True},
                   got, ev) == 214.0)
ok("an empty venue index releases nothing",
   nr.classify({"order_id": "d24d0e03-CLIENT"}, {}, {})[0] == nr.UNKNOWN)
ok("a CANCELED order WITH a fill record is not terminal",
   nr.classify({"order_id": "cancel-nofill-but-filled"}, BY, FB)[0] == nr.UNKNOWN)
# requirement 6: age releases nothing
old = {"orders": [{"order_id": "v", "client_id": "ancient", "status": "OPEN", "filled_qty": 0,
                   "qty": "1000", "price": "0.5", "placed_utc": "2020-01-01T00:00:00Z"}]}
b2, f2 = nr.venue_index(old, {"fills": []})
ok("an OLD but OPEN order is still a live commitment, not released",
   nr.classify({"order_id": "ancient"}, b2, f2)[0] == nr.OPEN)

# ---------------------------------------------------------------- 4. exposure arithmetic
cls, ev = nr.classify({"order_id": "d24d0e03-CLIENT"}, BY, FB)
ok("a terminal zero-fill leg counts nothing",
   nr.exposure_for({"order_id": "d24d0e03-CLIENT", "asked_stake": 389.85, "resting": True}, cls, ev) == 0.0)
cls, ev = nr.classify({"order_id": "18aefa75-CLIENT"}, BY, FB)
ok("a filled leg counts the ACTUAL filled amount, not the ask",
   nr.exposure_for({"order_id": "18aefa75-CLIENT", "asked_stake": 96.0, "resting": True}, cls, ev) == 95.55,
   nr.exposure_for({"order_id": "18aefa75-CLIENT", "asked_stake": 96.0, "resting": True}, cls, ev))
cls, ev = nr.classify({"order_id": "partial-CLIENT"}, BY, FB)
ok("a partial fill counts what filled", nr.exposure_for({"order_id": "partial-CLIENT", "asked_stake": 100.0,
                                                         "resting": True}, cls, ev) == 25.0)
cls, ev = nr.classify({"order_id": "fa7a84cb-CLIENT"}, BY, FB)
ok("an OPEN order counts the whole commitment",
   nr.exposure_for({"order_id": "fa7a84cb-CLIENT", "asked_stake": 214.0, "resting": True}, cls, ev) == 214.0)

# ---------------------------------------------------------------- 5. idempotency + audit history
cls, ev = nr.classify({"order_id": "18aefa75-CLIENT"}, BY, FB)
leg = {"order_id": "18aefa75-CLIENT", "filled_stake": None, "asked_stake": 96.0, "book": "novig",
       "status": "placed"}
p1 = nr.reconciliation_patch(leg, cls, ev, asof=ASOF)
once = nr.apply_patch(leg, p1)
twice = nr.apply_patch(once, nr.reconciliation_patch(once, cls, ev, asof=ASOF))
ok("applying the patch twice changes nothing", once == twice)
ok("the patch carries status, filled amount and a timestamp",
   {"venue_status", "venue_filled_usd", "reconciled_utc", "venue_order_id"} <= set(p1), p1)
ok("the registry's original order_id is preserved", once["order_id"] == "18aefa75-CLIENT")
ok("the registry's original filled_stake is preserved", once["filled_stake"] is None)
ok("the true venue order id is recorded alongside", once["venue_order_id"] == "01a1ef2c-VENUE")
ok("a patch never rewrites the audit fields",
   nr.apply_patch(leg, {"order_id": "HACKED", "filled_stake": 999})["order_id"] == "18aefa75-CLIENT")
ok("an UNKNOWN leg produces no patch at all",
   nr.reconciliation_patch(leg, nr.UNKNOWN, {}, asof=ASOF) == {})

# ---------------------------------------------------------------- 6. nothing is wired in
exr = open("executor.py").read()
# Nov 18: ACTIVATED by Peter. These assertions previously pinned the module as NOT wired in; they now
# pin the opposite, and the safety property that replaces inertness - every failure path in the
# caller keeps the registry's figure, so a bad read cannot release money.
ok("executor imports the reconciler", "import novig_reconcile as nvr" in exr)
ok("the live gate reads the reconciled figure", 'book_live.set_exposure(NONPX["today"])' in exr)
ok("the caller falls back to the registry figure when there is no evidence",
   'return amt, "no venue evidence"' in exr)
ok("the caller never counts MORE than the pre-fix figure", "got if got <= amt else amt" in exr)
# Checked on the IMPORT LINES, not the prose: the first version scanned the whole source and failed
# on the docstring, which necessarily discusses the registry. Same over-blunt grep as earlier today.
_src = open("novig_reconcile.py").read()
_imports = [l.strip() for l in _src.splitlines() if l.startswith(("import ", "from "))]
ok("the reconciler imports only the standard library", _imports == ["from datetime import datetime, timezone"], _imports)
ok("the reconciler performs no network or store call",
   not any(t in _src for t in ("urllib", "requests", "registry._call", "gh api", "subprocess")))

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
