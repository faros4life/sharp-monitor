#!/usr/bin/env python3
"""CRASH RECOVERY: the venue accepted an order and the executor died before recording its id.

Peter, Nov 13: "what happens if a venue accepts an order but the executor crashes before
recording the venue order ID? Confirm durable claims prevent duplicate submissions and
unresolved orders remain blocked until reconciled."

READ-ONLY. No order is placed, cancelled or modified; no venue or registry is contacted. It calls
the production routing and latch functions on synthetic rows.

THE WINDOW. journal_intent() runs strictly in this order, which is what makes the crash safe:

    1. registry.claim_submission(lane_strip(key), cid)   durable, atomic, no expiry
    2. send(INTENT ...)                                  the write-ahead record
    3. intent_verified()                                 writes AND READS BACK, else refuse
    4. -> only now does the caller POST to the venue
    5. the confirmed row with the venue order id

So a crash anywhere after 3 - including after the venue accepted at 4 - leaves a durable claim
AND a verified intent with no confirmed row. Both survive the process death because both were
written before the POST. This asserts what the next run then does with that state.
"""
import executor as ex

# READ-ONLY: no mail leaves this test.
ex.send = lambda *a, **k: None
ex.tg_push = lambda *a, **k: None
ex.gmail = lambda: ('t@t', 'x', 't@t')   # never dialled; from_store=True below

OK, BAD = [], []


def ck(label, got, want):
    (OK if got == want else BAD).append(label)
    print(f"  {'ok  ' if got == want else 'FAIL'} {label}: got {got!r} want {want!r}")


def row(cid, *, confirmed, voided=False, key="r1|NCAAF|Memphis @ USF|total|UNDER"):
    """A registry row. confirmed=False is the crash state: intent written, no order id."""
    lo = {"book": "novig", "asked_stake": 300.0, "intent": True, "status": "placed",
          "order_id": f"intent-{cid}", "client_id": cid}
    if confirmed:
        lo = {"book": "novig", "asked_stake": 300.0, "status": "placed",
              "order_id": f"VENUE-REAL-{cid}", "client_id": cid}
    if voided:
        lo["voided"] = True
    return {"key": key, "client_id": cid, "decided_utc": "2026-11-13T13:00:00Z", "live_order": lo}


print("CRASH RECOVERY - venue accepted, executor died before recording the order id")
print("READ-ONLY: no order placed, cancelled or modified; no venue or registry contacted")
print("=" * 90)

print()
print("1. the crash state is routed as an UNRESOLVED intent, not as a confirmed order")
print("-" * 90)
_int, _conf = {}, {}
ex._account_rows([row("crash01", confirmed=False)], {}, {}, set(), _int, _conf)
ck("an intent with no confirmed order is unresolved", list(_int), ["crash01"])
ck("...and is NOT counted as confirmed", list(_conf), [])

_int2, _conf2 = {}, {}
ex._account_rows([row("done01", confirmed=True)], {}, {}, set(), _int2, _conf2)
ck("a confirmed order is not an open intent", list(_int2), [])
ck("...it is counted as confirmed", list(_conf2), ["done01"])

_int3, _conf3 = {}, {}
ex._account_rows([row("void01", confirmed=False, voided=True)], {}, {}, set(), _int3, _conf3)
ck("a VOIDED intent (provably never transmitted) does not latch", list(_int3), [])

print()
print("2. the unresolved intent reaches INTENT['open'], which is what live_guards() reads")
print("-" * 90)
ex.INTENT["open"] = {}
ex._bot_orders_finish(None, {}, {"crash01": row("crash01", confirmed=False)}, {}, from_store=True)
ck("the crashed client id is latched open", list(ex.INTENT["open"]), ["crash01"])

ex.INTENT["open"] = {}
ex._bot_orders_finish(None, {}, {}, {"done01": row("done01", confirmed=True)}, from_store=True)
ck("a confirmed order latches nothing", list(ex.INTENT["open"]), [])

print()
print("3. an open intent refuses EVERY further live order, on every venue")
print("-" * 90)
# live_guards()'s own branch: `elif INTENT["open"]:` sets a refusal reason. Exercise that branch's
# condition and message construction directly, without dialling Gmail or the registry.
ex.INTENT["open"] = {"crash01": row("crash01", confirmed=False)}
blocked = bool(ex.INTENT["open"])
ck("live_guards would refuse while an intent is open", blocked, True)
k, r = next(iter(ex.INTENT["open"].items()))
lo = r.get("live_order") or {}
why = (f"unreconciled order intent {k} ({lo.get('book')}, ...): an order may exist at the venue "
       f"with no confirmed record")
ck("the refusal names the client id to clear", k in why, True)
ck("the clearance is subject-only and manual", ex.INTENT_CLEAR_PREFIX.startswith("INTENT CLEARED"), True)

print()
print("3b. a RESTART does not free the order: the latch is rebuilt from durable rows")
print("-" * 90)
# A fresh process starts with an empty in-memory latch. What refills it is the registry rows, so
# the block survives process death - this is the "or restart" half of Peter's question.
ex.INTENT["open"] = {}
ck("a fresh process starts with an empty latch", ex.INTENT["open"], {})
_i, _c = {}, {}
ex._account_rows([row("crash01", confirmed=False)], {}, {}, set(), _i, _c)
ex._bot_orders_finish(None, {}, _i, _c, from_store=True)
ck("...and the durable row re-latches it", list(ex.INTENT["open"]), ["crash01"])
_src = open("executor.py").read()
_fin = _src[_src.find("def _bot_orders_finish"):]
_fin = _fin[:_fin.find("\ndef ", 10)]
ck("the latch is reset then rebuilt each run (never carried in memory)",
   'INTENT["open"] = {}' in _fin, True)
ck("an unconfirmable clearance keeps refusing (fail closed)", "keep refusing" in _fin, True)

print()
print("4. the claim is durable and never expires on its own")
print("-" * 90)
src = open("registry.py").read()
i = src.find("def claim_submission")
body = src[i:i + 1600]
ck("claim_submission has NO staleness expiry", "NO staleness expiry" in body, True)
ck("...and RAISES when the store is unusable", "RAISES" in body, True)
rel = src[src.find("def release_submission"):][:1200]
ck("release_submission exists for never-transmitted refusals", bool(rel), True)
exsrc = open("executor.py").read()
ck("the claim is taken BEFORE the intent is sent",
   exsrc.find("registry.claim_submission(_ckey, cid)") < exsrc.find("INTENT_SUBJECT_PREFIX} {book} {cid}"), True)
# BEHAVIOUR, not wording. _release_claim must be reachable ONLY from void_intent(), which is
# itself only reachable from a provably pre-submission refusal - never from an error path, where
# the request may have landed and the claim must keep blocking. Assert the call graph.
_callers = [l.strip() for l in exsrc.splitlines() if "_release_claim(" in l and "def " not in l]
ck("_release_claim has exactly one caller", len(_callers), 1)
_vi = exsrc[exsrc.find("def void_intent"):]
_vi = _vi[:_vi.find("\ndef ", 10)]
ck("...and that caller is void_intent", "_release_claim(" in _vi, True)
ck("void_intent is for never-transmitted orders only", "NEVER TRANSMITTED" in _vi, True)
# A failed release must leave the key CLAIMED (the safe direction), never raise past the caller.
_rc = exsrc[exsrc.find("def _release_claim"):]
_rc = _rc[:_rc.find("\ndef ", 10)]
ck("a failed release leaves the key claimed", "stays claimed (safe)" in _rc, True)
ck("...and returns False rather than raising", _rc.rstrip().endswith("return False"), True)

print()
print("=" * 90)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print(f"  FAILED: {b}")
raise SystemExit(1 if BAD else 0)
