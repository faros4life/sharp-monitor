#!/usr/bin/env python3
"""Step 2 (Peter, Nov 12): one-time reconciliation of the REAL Gmail manual-hold window against the
private registry, deletions and clearances included. Gmail is read ONCE, here, for this purpose.

Read-only with respect to holds and orders: it places nothing, cancels nothing, clears nothing and
writes no manual note of its own. The only write it causes is the mirror snapshot that read_manual()
already performs on every executor pass - this script deliberately goes through the SAME
read_manual() the executor uses rather than re-implementing the parser, because a second parser
would reconcile itself rather than production. ("Do not invent a second way.")

PUBLIC LOG: counts only, plus an 8-char hash per differing key. Play keys and bet text never
appear, which is the same rule _mirror_manual() follows.

Exit code is always 0: a diagnostic never fails the workflow.
"""
import hashlib
import sys

import executor as ex
import registry as rg


def h(k):
    return hashlib.sha1(str(k).encode()).hexdigest()[:8]


print("MANUAL-HOLD RECONCILIATION (Gmail vs private registry)")

if not rg.enabled():
    print("  FAIL  no REGISTRY_TOKEN: the store cannot be read at all")
    print("RECONCILIATION: FAIL")
    sys.exit(0)

# ---- Gmail side, through production's own reader -------------------------------------------
ex.MANUAL_HELD.clear()
try:
    M = ex.imap_open()
except Exception as e:
    print(f"  FAIL  Gmail unreachable: {str(e)[:70]}")
    print("RECONCILIATION: FAIL")
    sys.exit(0)
try:
    ex.read_manual(M)          # parses the window, applies holds, and runs the mirror
finally:
    try:
        ex.imap_close(M)
    except Exception:
        pass
gmail_held = dict(ex.MANUAL_HELD)

# ---- Store side, replayed through the SAME accounting ---------------------------------------
stored = rg.manual_notes()
if stored is None:
    print("  FAIL  the store is UNREADABLE - that is not an empty window, and must never be read as one")
    print("RECONCILIATION: FAIL")
    sys.exit(0)

store_held = {}
for n in stored:
    ex._apply_manual(n, store_held)

print(f"  notes in store            : {len(stored)}")
print(f"  gmail holds (keys)        : {len(gmail_held)}")
print(f"  store holds (keys)        : {len(store_held)}")

gonly = sorted(set(gmail_held) - set(store_held))
sonly = sorted(set(store_held) - set(gmail_held))
diff = sorted(k for k in set(gmail_held) & set(store_held) if gmail_held[k] != store_held[k])

print(f"  gmail-only keys           : {len(gonly)}  {[h(k) for k in gonly[:8]]}")
print(f"  store-only keys (STALE)   : {len(sonly)}  {[h(k) for k in sonly[:8]]}")
print(f"  same key, different state : {len(diff)}  {[h(k) for k in diff[:8]]}")

# A store-only key is the DELETION failure: a hold the store still believes and Gmail no longer
# has. It is the dangerous direction - the bot would keep refusing a bet Peter is no longer on -
# and it is exactly what an upsert-shaped mirror would produce.
ok = not gonly and not sonly and not diff

# Completeness must ALSO be claimed, not merely equal: an agreeing store that cannot assert
# completeness is still not safe to switch to.
comp = rg.manual_complete()
print(f"  store claims completeness : {comp}")

for line in ex.LOG:
    if "manual mirror" in line:
        print(f"  mirror said               : {line}")

print()
print("RECONCILIATION:", "PASS" if (ok and comp) else "FAIL")
if not ok:
    print("  MISMATCH - do not switch. The hashes above identify the keys; store-only keys are")
    print("  holds the store would keep enforcing after Peter cleared them.")
elif not comp:
    print("  Holds agree, but the store does not claim completeness, so the switch is not safe yet.")
sys.exit(0)
