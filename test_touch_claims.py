#!/usr/bin/env python3
"""Priority 1 (Peter, Nov 12): the completeness claims are re-stamped on BOTH of main()'s exit
paths, and re-stamping can never manufacture completeness.

The loop this closes: handled_pids() already prefers the private store, gated on
registry.tokens_complete(). That claim was re-stamped only on the BUSY exit path, after orders.
The executor is idle on most runs, so FRESH_MIN (12 min) routinely elapsed between one candidate
run and the next, the claim expired, and the next candidate pass fell back to Gmail - 44.7s of
dedupe search on the one path where latency decides whether a bet reaches the book. The orders
fast path made it permanent, because set_tokens_complete() is reachable only inside bot_orders()'
GMAIL backfill, which the fast path skips.

The safety property under test is that the fix is REFRESH-ONLY. If it could create a claim, a store
that had never been reconciled with Gmail would start answering the duplicate-bet guard.

Nothing is placed, submitted or replayed.
"""
import ast
import sys
from datetime import datetime, timedelta, timezone

import executor as ex
import registry as rg

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


print("1. Both exit paths re-stamp")
src = open("executor.py").read()
tree = ast.parse(src)
calls = [n.lineno for n in ast.walk(tree)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "touch_claims"]
check("touch_claims() is called from two places", len(calls) == 2)
check("it is defined once", src.count("def touch_claims(") == 1)
check("the inline duplicate is gone", src.count("token completeness not re-stamped") == 1)

print("\n2. Refresh-only: a claim that is not already valid is NOT created")
NOW = datetime.now(timezone.utc)
store = {"meta": {}, "handled": {}, "orders": [], "intents": [], "strikes": {}, "manual": []}
_load, _commit, _en = rg.load, rg._commit, rg.enabled
rg.enabled = lambda: True
rg.load = lambda: store


def fake_commit(merge, tries=4):
    out = merge(store)
    return True if out is not False else True


rg._commit = fake_commit

store["meta"] = {}
check("no claim at all -> tokens_complete() stays False",
      rg.touch_tokens_complete() is False and rg.tokens_complete() is False)

old = (NOW - timedelta(days=rg.KEEP_DAYS + 3)).strftime("%Y-%m-%d")
store["meta"] = {"tok_complete_through": old,
                 "tok_complete_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}
check("a claim for an EXPIRED window is not refreshed", rg.touch_tokens_complete() is False)

print("\n3. An EXPIRED stamp is NOT revived - only the backfill may assert completeness again")
good = NOW.strftime("%Y-%m-%d")
stale = (NOW - timedelta(minutes=rg.FRESH_MIN + 20)).strftime("%Y-%m-%dT%H:%M:%SZ")
store["meta"] = {"tok_complete_through": good, "tok_complete_at": stale}
check("it is stale", rg.tokens_complete() is False)
check("touch REFUSES to resurrect it", rg.touch_tokens_complete() is False)
check("so it still does not answer", rg.tokens_complete() is False)

print("\n   A claim that is still FRESH is extended - this is what keeps the chain alive")
fresh = (NOW - timedelta(minutes=max(1, rg.FRESH_MIN - 7))).strftime("%Y-%m-%dT%H:%M:%SZ")
store["meta"] = {"tok_complete_through": good, "tok_complete_at": fresh}
check("it answers before", rg.tokens_complete() is True)
check("touch extends it", rg.touch_tokens_complete() is True)
check("and it still answers", rg.tokens_complete() is True)
# This is precisely why the IDLE path had to re-stamp: runs fire every ~5 minutes and FRESH_MIN is
# 12, so idle runs hand the claim forward hop by hop. Busy runs alone are far rarer than 12 minutes
# apart, so the chain broke every time and the next candidate pass paid 44.7s to Gmail.
check("the schedule is inside FRESH_MIN, so idle runs can carry the claim", rg.FRESH_MIN > 5)

print("\n4. An UNREADABLE store asserts nothing")
rg.load = lambda: None
check("tokens_complete() is False", rg.tokens_complete() is False)
check("touch_tokens_complete() is False", rg.touch_tokens_complete() is False)
check("touch_complete() is False", rg.touch_complete() is False)

print("\n5. touch_claims() swallows failures rather than killing the run")
rg.load = lambda: (_ for _ in ()).throw(RuntimeError("store down"))
ex.LOG.clear()
ex.touch_claims()          # must not raise: re-stamping is an optimisation, never a gate
check("it did not raise", True)
check("and it said so in the log", any("touch" in l or "not re-stamped" in l for l in ex.LOG))

rg.load, rg._commit, rg.enabled = _load, _commit, _en
ex.LOG.clear()

print()
if fails:
    print(f"FAIL  test_touch_claims.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
