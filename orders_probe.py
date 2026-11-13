#!/usr/bin/env python3
"""READ-ONLY: outstanding orders, intents and submission claims in the private registry.

Peter, Nov 13, Priority 3: "Check all outstanding orders, actual fills, and duplicate claims.
Verify whether any orders were placed after the 8:30:55 AM GO. Do not assume a prior refusal
guarantees no subsequent order."

Writes nothing. Places, cancels and clears nothing. Times, books, lanes, statuses and counts only -
no stake, price, payout or balance - so it is safe for the public Actions log.

THE GO: 2026-11-13T13:30:55Z. Every order row is classified against it, because a refusal observed
at 13:21-13:27Z says nothing about what happened after the switch flipped.
"""
import os
import sys
from datetime import datetime, timezone

import registry as rg

GO_UTC = os.environ.get("GO_UTC") or "2026-11-13T13:30:55Z"


def t(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None


print("ORDERS / INTENTS / CLAIMS PROBE (read-only; nothing written)")
print(f"  reference GO: {GO_UTC}")
print(f"  now         : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")

if not rg.enabled():
    print("  FAIL  no REGISTRY_TOKEN - cannot read; that is NOT 'no orders'")
    sys.exit(0)

d = rg.load()
if d is None:
    print("  FAIL  registry UNREADABLE - fail closed; this is NOT 'no orders'")
    sys.exit(0)

go = t(GO_UTC)
orders = d.get("orders") or []
intents = d.get("intents") or []
subs = d.get("submissions") or {}

print(f"\n  orders      : {len(orders)}")
print(f"  intents     : {len(intents)}   (an OPEN intent blocks every further live order)")
print(f"  submissions : {len(subs) if hasattr(subs, '__len__') else '?'}  (duplicate claims)")


def row_t(o):
    for k in ("decided_utc", "placed_utc", "sent_utc", "ts", "et_day"):
        v = t(o.get(k))
        if v:
            return v, k
    return None, ""


after, before, undated = [], [], []
for o in orders:
    ts, src = row_t(o)
    if ts is None:
        undated.append(o)
    elif go and ts > go:
        after.append((ts, src, o))
    else:
        before.append((ts, src, o))

print(f"\n  AFTER the GO : {len(after)}   <- the question that matters")
for ts, src, o in sorted(after):
    lo = o.get("live_order") or o.get("live_rest") or {}
    print(f"    {ts.strftime('%Y-%m-%dT%H:%M:%SZ')} [{src}] book={lo.get('book') or o.get('book')} "
          f"status={lo.get('status') or o.get('status')} lane={o.get('lane') or '-'} "
          f"oid={'yes' if (lo.get('order_id') or o.get('order_id')) else 'no'}")
print(f"  before the GO: {len(before)}")
print(f"  undated      : {len(undated)}  (kept, never dropped - a row with no date still counts)")

print("\n  NEWEST 8 ORDER ROWS (any side of the GO)")
for ts, src, o in sorted(before + after, reverse=True)[:8]:
    lo = o.get("live_order") or o.get("live_rest") or {}
    print(f"    {ts.strftime('%Y-%m-%dT%H:%M:%SZ')} book={lo.get('book') or o.get('book')} "
          f"status={lo.get('status') or o.get('status')} lane={o.get('lane') or '-'}")

print("\n  UNRESOLVED INTENTS (an order may exist at the venue with no confirmed record)")
if not intents:
    print("    none")
for i in intents:
    lo = i.get("live_order") or {}
    print(f"    {i.get('decided_utc')} book={lo.get('book')} voided={bool(i.get('voided') or lo.get('voided'))}")

print("\n  SUBMISSION CLAIMS (held = a key that cannot be submitted again until released)")
try:
    items = list(subs.items()) if isinstance(subs, dict) else []
    if not items:
        print("    none held")
    for k, v in items[:20]:
        wt = (v or {}).get("ts") if isinstance(v, dict) else None
        print(f"    held key hash={abs(hash(k)) % 10**8:08d} since={wt}")
except Exception as ex:
    print(f"    unreadable: {str(ex)[:60]}")

print("\nNothing was written, placed, cancelled or cleared.")
sys.exit(0)
