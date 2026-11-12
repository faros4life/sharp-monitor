#!/usr/bin/env python3
"""Read-only historical Kalshi reconciliation (Peter, Nov 12). Flags; never fixes, never places.

TWO DIRECTIONS, because each one is blind to a different failure:

  FORWARD  every Kalshi order_id stored in the private registry -> does Kalshi still resolve it?
           An id the venue cannot resolve is a record we could never report a fill against again.

  REVERSE  every recent Kalshi fill at the venue -> is its order_id one of ours?
           A fill with no stored order is the MISSED FILL direction, and a forward-only check
           cannot see it. This is the direction that matters for "no missed fills".

An order the API cannot be read for is reported UNREADABLE, never UNMATCHED and never "no fills":
unavailable venue data is not evidence of absence. That distinction is the whole point of keeping
the two buckets apart - they have opposite remedies, and merging them is how this repo has hidden
bugs before.

Nothing is placed, cancelled or modified. Counts only, plus truncated ids so a flag can be chased.
No dollar amounts anywhere.
"""
import collections
import sys

import book_live as bl
import registry as rg

FILL_SCAN = 200   # recent venue fills to walk for the reverse direction


def kget(path, params=None):
    """(ok, data). Never raises: an unreadable order must not look like a missing one."""
    try:
        _st, d = bl._k_call("GET", path, params or {})
        return True, (d or {})
    except Exception as e_:
        return False, {"_err": str(e_)[:60]}


rows = rg.rows()
if rows is None:
    print("RECONCILE BLOCKED: the private registry is unreadable - stored orders cannot be enumerated.")
    print("Nothing is concluded. Gmail checks stay exactly as they are.")
    sys.exit(0)   # a read-only diagnostic never fails the workflow

stored = collections.OrderedDict()
for r in rows:
    for fld in ("live_order", "live_rest", "live_more"):
        v = r.get(fld)
        # live_more is a LIST of order records while the other two are single dicts. Normalising
        # here rather than assuming: the first version of this script assumed all three were dicts
        # and died on .get() against the list.
        for o in (v if isinstance(v, list) else [v]):
            if not isinstance(o, dict):
                continue
            if o.get("book") == "kalshi" and o.get("order_id"):
                stored.setdefault(str(o["order_id"]), []).append(f"{fld}:{o.get('status') or '?'}")

print(f"ledger rows in the registry: {len(rows)}")
print(f"stored Kalshi order ids:     {len(stored)}")

matched, unmatched, unreadable = [], [], []
fills_seen = collections.Counter()
status_counts = collections.Counter()

for oid in stored:
    ok, d = kget(f"/portfolio/orders/{oid}")
    o = (d.get("order") or {}) if ok else {}
    if not ok:
        unreadable.append(oid)
        continue
    if o.get("order_id") or o.get("status"):
        matched.append(oid)
        status_counts[str(o.get("status") or "?").lower()] += 1
        ok2, d2 = kget("/portfolio/fills", {"order_id": oid})
        if ok2:
            fills_seen[oid] = len(d2.get("fills") or [])
        else:
            unreadable.append(oid + " (order ok, fills unreadable)")
    else:
        unmatched.append(oid)   # the venue answered and does not know this id

print()
print("FORWARD  registry -> Kalshi")
print(f"  matched at the venue:      {len(matched)}")
print(f"  UNMATCHED (flag):          {len(unmatched)}")
print(f"  unreadable (not a flag):   {len(unreadable)}")
if status_counts:
    print("  venue status of matched:   " + ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
if fills_seen:
    withf = sum(1 for v in fills_seen.values() if v)
    print(f"  orders with >=1 fill event: {withf} of {len(fills_seen)} read"
          f" ({sum(fills_seen.values())} fill event(s) total)")
for oid in unmatched:
    print(f"  FLAG unmatched order id {oid[:8]}...  stored as: {', '.join(stored[oid])}")
for oid in unreadable:
    print(f"  note unreadable order id {oid[:8]}...  (retry next run; NOT treated as missing)")

print()
print(f"REVERSE  Kalshi -> registry (last {FILL_SCAN} venue fills)")
ok, d = kget("/portfolio/fills", {"limit": FILL_SCAN})
if not ok:
    print(f"  venue fill list UNREADABLE ({d.get('_err')}) - the missed-fill direction is UNVERIFIED this run.")
    print("  Reported as unverified, never as zero.")
else:
    vf = d.get("fills") or []
    by_oid = collections.Counter(str(f.get("order_id") or "") for f in vf)
    by_oid.pop("", None)
    ours = [o for o in by_oid if o in stored]
    theirs = [o for o in by_oid if o not in stored]
    print(f"  venue fills read:          {len(vf)} across {len(by_oid)} order id(s)")
    print(f"  attributable to our store: {len(ours)}")
    print(f"  NOT in our store (flag):   {len(theirs)}")
    for o in theirs:
        print(f"  FLAG venue fill on unknown order id {o[:8]}...  ({by_oid[o]} fill event(s))")
    if not vf:
        print("  (no venue fills in range - this says nothing about whether any order exists)")

print()
# Nov 12, corrected within the hour: this verdict consulted ONLY the forward list, so the first run
# printed "no unmatched records in either direction" directly beneath 20 reverse FLAGS. A result
# line that contradicts the evidence above it is worse than no result line.
rev_flags = 0 if not ok else len([o for o in (collections.Counter(
    str(f.get("order_id") or "") for f in (d.get("fills") or [])).keys()) if o and o not in stored])
if not stored:
    # The forward direction is VACUOUS, not clean: there is nothing stored to reconcile. Saying
    # "matched" here would read as proof when no comparison was possible.
    print("RECONCILE RESULT: NOT POSSIBLE - the registry holds no Kalshi order ids, so there is "
          "nothing to reconcile forward.")
    if rev_flags:
        print(f"  The {rev_flags} venue order id(s) with fills are therefore NOT evidence of missed bot "
              "fills: with zero stored bot orders they are consistent with Peter's own Kalshi trades, "
              "and the venue exposes no field that distinguishes the two.")
    print("  Retiring the Gmail ledger for Kalshi stays BLOCKED - not because anything is broken, "
          "but because this check cannot be performed.")
elif unmatched or rev_flags or not ok:
    print(f"RECONCILE RESULT: FLAGS RAISED ({len(unmatched)} forward, {rev_flags} reverse"
          + ("" if ok else ", reverse direction unreadable") + ") - investigate before retiring any Gmail check")
else:
    print("RECONCILE RESULT: every stored order matched, and every venue fill was attributable")
print("Read-only: nothing was placed, cancelled or modified.")
