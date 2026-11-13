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

import executor as ex
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
    # Nov 13: the row's own `lane` field is usually absent, but row["key"] is LANE-PREFIXED
    # ("r1|NCAAB|...", "board|NBA|..."), which is how _account_rows attributes exposure. Printing
    # the derived lane answers "which lane placed this" without any money figure.
    print(f"    {ts.strftime('%Y-%m-%dT%H:%M:%SZ')} [{src}] book={lo.get('book') or o.get('book')} "
          f"status={lo.get('status') or o.get('status')} "
          f"lane={ex.lane_from_key(o.get('key')) if o.get('key') else (o.get('lane') or '-')} "
          f"rest={'yes' if o.get('live_rest') else 'no'} "
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

# ---------------------------------------------------------------- item 3: oversized fills
# The Nov 12 17:05:06Z STOP has unknown provenance. If it was the AUTOMATIC over-fill pause, a fill
# exceeded MAX_ORDER around then. COUNTS AND TIMES ONLY - the amount itself never enters a public
# log (CLAUDE.md), so this reports whether the condition occurred, not the figure.
try:
    import px_live as _px
    cap = float(getattr(_px, "MAX_ORDER", 0) or 0)
except Exception:
    cap = 0.0
print(f"\n  OVERSIZED-FILL CHECK (per-order maximum configured: {'yes' if cap else 'unknown'})")
over = []
for o in orders:
    lo = o.get("live_order") or o.get("live_rest") or {}
    for k in ("filled_stake", "asked_stake", "stake"):
        v = lo.get(k) if isinstance(lo, dict) else None
        try:
            if cap and v is not None and float(v) > cap + 0.5:
                ts, _s = row_t(o)
                over.append((ts, k, lo.get("book") or o.get("book")))
                break
        except Exception:
            pass
if not cap:
    print("    cannot evaluate: no per-order maximum visible here")
elif not over:
    print("    0 order rows in the window exceed the per-order maximum")
    print("    => no evidence of an automatic over-fill pause from the rows still retained")
for ts, k, bk in sorted(over):
    print(f"    {ts.strftime('%Y-%m-%dT%H:%M:%SZ') if ts else '?'} book={bk} field={k} EXCEEDS the maximum")
print(f"    rows retained span: {min([t for t,_,_ in sorted(before+after)], default=None)} .. "
      f"{max([t for t,_,_ in sorted(before+after)], default=None)}")

# ---------------------------------------------------------------- item 4: claims vs real orders
print("\n  CLAIMS RECONCILED AGAINST ORDER ROWS (a claim is released only by evidence, never by age)")
cids = {}
for o in orders:
    lo = o.get("live_order") or o.get("live_rest") or {}
    c = str(lo.get("client_id") or o.get("client_id") or "")
    if c:
        cids[c] = (lo.get("status") or o.get("status"), lo.get("book") or o.get("book"),
                   bool(lo.get("order_id") or o.get("order_id")))
try:
    for k, v in (subs.items() if isinstance(subs, dict) else []):
        cid = str((v or {}).get("cid") or (v or {}).get("client_id") or "") if isinstance(v, dict) else ""
        hit = cids.get(cid)
        when = (v or {}).get("ts") if isinstance(v, dict) else None
        if hit:
            print(f"    claim since={when} -> order found: status={hit[0]} book={hit[1]} venue_id={'yes' if hit[2] else 'NO'}")
            print("      verdict: " + ("MATCHED a real order - the claim is doing its job, keep it"
                                        if hit[2] else
                                        "order row exists but carries NO venue id - unresolved, KEEP the claim"))
        else:
            print(f"    claim since={when} cid_known={'yes' if cid else 'no'} -> NO matching order row")
            print("      verdict: cannot prove the venue never saw it - KEEP the claim (fail closed)")
except Exception as ex:
    print(f"    unreadable: {str(ex)[:60]}")

print("\nNothing was written, placed, cancelled or cleared.")
sys.exit(0)
