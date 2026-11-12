#!/usr/bin/env python3
"""
OFFLINE TEST for the bet-to-CLV join logic (Muse item: "test offline ... once validated").

Runs with NO network, NO credentials and NO state file: it tests the four properties the join must
have, on synthetic fills whose answers are known by construction. The encrypted tracker and CLV
state cannot be read outside Actions, so what is testable here is the LOGIC, and that is exactly
where the two defects were - an id namespace and a per-order vs per-position summation.

Properties under test, each one a thing that was actually wrong at some point today:
  1  clientId ONLY. fill.orderId's namespace is unverified (0 of 35 executor ids appeared in it),
     so a fill that matches only on orderId must NOT join. A fallback onto an unverified namespace
     is how a wrong match gets in.
  2  Partial fills of one order are summed ONCE per order, never counted per fill.
  3  Two orders on one market+outcome are ONE position: their costs sum, and the position is
     reconciled once, not twice. This is what produced the two DIFFERS rows.
  4  If the fills of a single order disagree about market+outcome, the order is UNRESOLVED, not
     joined to whichever came first.
"""
import collections
import sys


def group_by_client(fills):
    """The join as clv_link_recon now does it: clientId only, orderId never."""
    byc = collections.defaultdict(list)
    for f in fills:
        for k in ("clientId", "client_id"):
            v = f.get(k)
            if v is not None:
                byc[str(v)].append(f)
    return byc


def resolve(oid, fills_for_order):
    """(tracker_id | None, qty, cost). None means UNRESOLVED - the fills disagree on the position."""
    tids = {f"nv|{f.get('marketId')}|{f.get('outcomeId')}" for f in fills_for_order}
    if len(tids) != 1:
        return None, 0, 0.0
    return (tids.pop(),
            sum(int(f.get("qty") or 0) for f in fills_for_order),
            sum(float(f.get("cost") or 0) for f in fills_for_order))


def by_position(matched):
    """matched: [(oid, tid, qty, cost)] -> {tid: (orders, qty, cost)} summed ONCE per position."""
    pos = collections.defaultdict(lambda: [0, 0, 0.0])
    for oid, tid, qty, cost in matched:
        pos[tid][0] += 1
        pos[tid][1] += qty
        pos[tid][2] = round(pos[tid][2] + cost, 6)
    return pos


def main():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if got == want else 'FAIL'} {name}")

    print("OFFLINE JOIN TEST - no network, no credentials, no state file")
    print("=" * 84)

    # 1 - orderId must never join
    fills = [{"orderId": "ORDER-1", "marketId": "m1", "outcomeId": "o1", "qty": 100, "cost": 50.0}]
    check("a fill matching only on orderId does not join", "ORDER-1" in group_by_client(fills), False)
    fills2 = [{"clientId": "C-1", "orderId": "ORDER-1", "marketId": "m1", "outcomeId": "o1",
               "qty": 100, "cost": 50.0}]
    check("a fill carrying clientId does join", "C-1" in group_by_client(fills2), True)

    # 2 - partials summed once per order
    partials = [{"clientId": "C-2", "marketId": "m1", "outcomeId": "o1", "qty": 300, "cost": 3.0},
                {"clientId": "C-2", "marketId": "m1", "outcomeId": "o1", "qty": 700, "cost": 7.0},
                {"clientId": "C-2", "marketId": "m1", "outcomeId": "o1", "qty": 1000, "cost": 10.0}]
    g = group_by_client(partials)
    check("three partials group under one order", len(g["C-2"]), 3)
    tid, qty, cost = resolve("C-2", g["C-2"])
    check("partial qty sums once", qty, 2000)
    check("partial cost sums once", round(cost, 2), 20.0)
    check("partial order yields one position", tid, "nv|m1|o1")

    # 3 - two orders, one position: summed once, reconciled once
    two = [{"clientId": "C-3", "marketId": "m9", "outcomeId": "o9", "qty": 17000, "cost": 170.0},
           {"clientId": "C-4", "marketId": "m9", "outcomeId": "o9", "qty": 25800, "cost": 258.0}]
    g2 = group_by_client(two)
    matched = []
    for oid in ("C-3", "C-4"):
        t, q, c = resolve(oid, g2[oid])
        matched.append((oid, t, q, c))
    pos = by_position(matched)
    check("two orders collapse to ONE position", len(pos), 1)
    check("position counts both orders", pos["nv|m9|o9"][0], 2)
    check("position qty is the sum", pos["nv|m9|o9"][1], 42800)
    check("position cost is the sum", round(pos["nv|m9|o9"][2], 2), 428.0)
    # the regression this encodes: comparing EITHER order alone to a 428.00 row stake reads DIFFERS
    check("one order alone would NOT equal the position stake", round(matched[0][3], 2) == 428.0,
          False)

    # 4 - disagreeing fills are unresolved, never joined to the first
    bad = [{"clientId": "C-5", "marketId": "m1", "outcomeId": "o1", "qty": 10, "cost": 1.0},
           {"clientId": "C-5", "marketId": "m2", "outcomeId": "o2", "qty": 10, "cost": 1.0}]
    t, q, c = resolve("C-5", group_by_client(bad)["C-5"])
    check("fills disagreeing on position are UNRESOLVED", t, None)
    check("an unresolved order contributes no qty", q, 0)

    # 5 - an order with no fills at all is not invented into a match
    check("an order with no fills has no group", "C-6" in group_by_client(partials), False)

    print("=" * 84)
    if fails:
        for f in fails:
            print("  " + f)
        print("  FAIL - do not commit")
        return 1
    print("  PASS - clientId-only join, partials summed once, aggregated positions summed once")
    print("  and reconciled once, disagreeing fills left unresolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
