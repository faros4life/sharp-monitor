#!/usr/bin/env python3
"""Priority 1 confirmation (Peter, Nov 12): unresolved intents, duplicate prevention and risk
limits stay FAIL-CLOSED when the private store cannot be read, and the read-back requirement is
not weakened by tonight's change.

An unreadable store must never be read as an EMPTY store. Empty means "no orders, no intents, no
manual holds", which is indistinguishable from "nothing is blocking this bet" - and that is the
one mistake that places money on a duplicate or past a risk limit.

Nothing is submitted, nothing is placed, no historical order is replayed.
"""
import sys

import registry as rg

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


_orig_fetch, _orig_enabled = rg._fetch, rg.enabled
rg.enabled = lambda: True


def unreadable():
    return None, None


print("1. An UNREADABLE store is None everywhere - never an empty result")
rg._fetch = unreadable
check("load() is None, not {}", rg.load() is None)
check("manual_notes() is None, not [] (manual holds)", rg.manual_notes() is None)
check("is_complete() is False (no fast path on an unreadable store)", rg.is_complete("2026-11-09") is False)
check("manual_complete() is False", rg.manual_complete() is False)

print("\n2. Duplicate prevention: the submission claim RAISES rather than returning a free pass")
raised = False
try:
    rg.claim_submission("NBA|A @ B|total|UNDER", "cid-test")
except Exception:
    raised = True
check("claim_submission() raises when the store cannot be read", raised)
check("a raise is not a claim: no caller can mistake it for a win", raised)

print("\n3. Writes refuse to overwrite what cannot be seen")
check("_commit() returns False on an unreadable store", rg._commit(lambda d: None) is False)
check("put_manual() returns False (no silent empty snapshot)", rg.put_manual([{"x": 1}]) is False)

print("\n4. The read-back requirement is NOT weakened - every failure mode still reports FAILED")
out = rg.selftest()
# An unreadable store short-circuits BEFORE the probe is ever written: there is nothing to read
# back, and the message says so rather than claiming a read-back result it never obtained.
check("an unreadable store says UNREADABLE and would fail closed",
      "UNREADABLE" in out and "would fail closed" in out)
check("and it does not report a read-back verdict it never took", "read-back" not in out)

# A store that reads fine but never contains the probe: the LOST UPDATE case.
rg._fetch = lambda: (dict(rg.EMPTY), "sha1")
rg.mark_handled = lambda toks, outcome: True      # claim the write confirmed
out = rg.selftest()
check("write ok + probe absent twice reports LOST UPDATE", "LOST UPDATE" in out)
check("and it is still reported as FAILED, not downgraded", "read-back FAILED" in out)
check("the four states are distinguishable, not one bucket",
      "LOST UPDATE" in out and "UNREADABLE" not in out)

print("\n5. A STALE read is still a FAILURE, not an excuse")
src = open("registry.py").read()
i = src.index("STALE READ")
check("the stale branch sets FAILED", 'verdict, detail = "FAILED"' in src[max(0, i - 200):i + 40])
check("the GET now carries a cache directive", '"Cache-Control": "no-cache"' in src)

rg._fetch, rg.enabled = _orig_fetch, _orig_enabled

print()
if fails:
    print(f"FAIL  test_registry_failclosed.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
