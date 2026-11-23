#!/usr/bin/env python3
"""
STAGE 3 REGRESSION (Peter, Nov 13 2026): PLACED is never read as FILLED.

Pins registry.put_fills' classification and its merge rule. The merge is exercised directly
against the same dict a _commit retry would hand it, so the "only ever move forward" guarantee is
tested rather than asserted - the runner re-reads every five minutes and an older row can arrive
after a newer one.

Nothing here touches the network: put_fills' classification is pure, and the merge closure is
pulled out and driven against a local dict.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import registry   # noqa: E402

BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def classify(rows):
    """Run put_fills' own body with _commit stubbed, and return what it would have merged."""
    captured = {}

    def fake_commit(merge, tries=4):
        d = {}
        merge(d)
        captured.update(d.get("fills") or {})
        return True

    real = registry._commit
    registry._commit = fake_commit
    try:
        registry.put_fills(rows)
    finally:
        registry._commit = real
    return captured


def main():
    print("1. a terminal full fill is FILLED, with stake and price persisted")
    out = classify([{"order_id": "o1", "client_id": "c1", "status": "FILLED",
                     "qty": 40000, "filled_qty": 40000, "filled_cost": 23382, "avg_price": -117}])
    check("state FILLED", out["o1"]["state"] == "FILLED", out["o1"])
    check("filled stake is dollars from cents", out["o1"]["filled_stake"] == 233.82, out["o1"]["filled_stake"])
    check("avg price kept", out["o1"]["avg_price"] == -117)
    check("client id kept for reconciliation", out["o1"]["client_id"] == "c1")
    check("fee basis recorded", bool(out["o1"]["fee_basis"]))

    print("2. an accepted order with no outcome yet is PLACED, and its fill stays UNKNOWN")
    out = classify([{"order_id": "o2", "status": "placed", "qty": 40000}])
    check("state PLACED", out["o2"]["state"] == "PLACED", out["o2"])
    check("filled_stake is None, not 0", out["o2"]["filled_stake"] is None, out["o2"]["filled_stake"])
    check("filled_qty is None, not 0", out["o2"]["filled_qty"] is None, out["o2"]["filled_qty"])

    print("3. the Nov 12 shape: status placed, nothing filled, is NOT counted as a fill")
    out = classify([{"order_id": "ebe82a72", "client_id": "fee2daff", "status": "placed",
                     "qty": 40000, "filled_qty": 0, "filled_cost": None, "avg_price": None}])
    check("state is PLACED, not NO_FILL", out["ebe82a72"]["state"] == "PLACED", out["ebe82a72"])
    check("no stake invented", out["ebe82a72"]["filled_stake"] is None)
    check("no price invented", out["ebe82a72"]["avg_price"] is None)

    print("4. partial, resting and no-fill are distinct states")
    out = classify([
        {"order_id": "p1", "status": "PARTIAL", "qty": 40000, "filled_qty": 15000, "filled_cost": 8000},
        {"order_id": "r1", "status": "OPEN", "qty": 40000, "filled_qty": 0},
        {"order_id": "n1", "status": "CANCELED", "qty": 40000, "filled_qty": 0},
        {"order_id": "n2", "status": "EXPIRED", "qty": 40000, "filled_qty": 0},
        {"order_id": "n3", "status": "REJECTED", "qty": 40000, "filled_qty": 0},
    ])
    check("PARTIAL", out["p1"]["state"] == "PARTIAL", out["p1"]["state"])
    check("RESTING", out["r1"]["state"] == "RESTING", out["r1"]["state"])
    check("cancelled -> NO_FILL", out["n1"]["state"] == "NO_FILL", out["n1"]["state"])
    check("expired -> NO_FILL", out["n2"]["state"] == "NO_FILL", out["n2"]["state"])
    check("rejected -> NO_FILL", out["n3"]["state"] == "NO_FILL", out["n3"]["state"])

    print("5. a terminal status whose filled_qty is not yet confirmed is not called FILLED")
    out = classify([{"order_id": "amb", "status": "FILLED", "qty": 40000, "filled_qty": 0}])
    # executor.novig_reports refuses to report "no fill" for this shape, so the registry must
    # not assert one either: the outcome is simply not known yet.
    check("FILLED with 0 confirmed is PLACED, never FILLED and never NO_FILL",
          out["amb"]["state"] == "PLACED", out["amb"]["state"])
    check("and no stake is invented for it", out["amb"]["filled_stake"] is None)

    print("6. outcomes only move FORWARD across repeated reads")
    merged = {"fills": {"o1": {"state": "FILLED", "filled_qty": 40000, "filled_stake": 233.82}}}

    def apply(rows):
        def fake_commit(merge, tries=4):
            merge(merged)
            return True
        real = registry._commit
        registry._commit = fake_commit
        try:
            registry.put_fills(rows)
        finally:
            registry._commit = real

    apply([{"order_id": "o1", "status": "placed", "qty": 40000}])
    check("a later non-terminal read cannot un-fill a FILLED order",
          merged["fills"]["o1"]["state"] == "FILLED", merged["fills"]["o1"])
    check("its stake is preserved", merged["fills"]["o1"]["filled_stake"] == 233.82)
    apply([{"order_id": "o1", "status": "CANCELED", "qty": 40000, "filled_qty": 0}])
    check("a later TERMINAL read may correct it",
          merged["fills"]["o1"]["state"] == "NO_FILL", merged["fills"]["o1"]["state"])

    print("7. nothing to record writes nothing")
    calls = []

    def count_commit(merge, tries=4):
        calls.append(1)
        return True

    real = registry._commit
    registry._commit = count_commit
    try:
        registry.put_fills([])
        registry.put_fills([{"status": "FILLED"}])        # no id at all
    finally:
        registry._commit = real
    check("no write for empty or id-less input", not calls, calls)

    print("8. an unchanged outcome is not rewritten")
    merged = {"fills": {"o9": {"state": "RESTING", "filled_qty": None}}}
    wrote = []

    def watch_commit(merge, tries=4):
        wrote.append(merge(merged))
        return True

    registry._commit = watch_commit
    try:
        registry.put_fills([{"order_id": "o9", "status": "OPEN", "qty": 40000, "filled_qty": 0}])
    finally:
        registry._commit = real
    check("merge returns False for an unchanged state", wrote == [False], wrote)

    print("9. fills() treats an unreadable store as UNKNOWN, not as 'nothing filled'")
    real_load = registry.load
    registry.load = lambda: None
    try:
        check("unreadable -> {}", registry.fills() == {})
    finally:
        registry.load = real_load

    print()
    print("7. Nov 23 root cause: one order, one record - the client-id twin written while SENDING is retired")
    store = {}

    def keep_commit(merge, tries=4):
        merge(store)
        return True
    real = registry._commit
    registry._commit = keep_commit
    try:
        # pass 1: journalled before the venue call - only the client id exists
        registry.put_fills([{"client_id": "cA", "status": "SENDING", "qty": 100, "play_key": "k"}])
        f = store["fills"]
        check("first write is keyed by client id and is PLACED (fill unknown)", f["cA"]["state"] == "PLACED" and f["cA"]["filled_stake"] is None, f)
        # pass 2: the venue id has arrived and the order filled
        registry.put_fills([{"client_id": "cA", "order_id": "vA", "status": "FILLED", "qty": 100, "filled_qty": 100,
                             "filled_cost": 5200, "avg_price": 108}])
        f = store["fills"]
        check("the FILLED record is stored under the venue id with its price", f["vA"]["state"] == "FILLED" and f["vA"]["avg_price"] == 108)
        check("the stale PLACED twin under the client id is GONE (this was the defect)", "cA" not in f, list(f))
        check("the surviving record still carries the client id for the join", f["vA"]["client_id"] == "cA")
        # an EXISTING orphan (the 15 in production) is healed by an unchanged re-read of the same row
        store["fills"]["cA"] = {"state": "PLACED", "venue_status": "SENDING", "client_id": "cA"}
        registry.put_fills([{"client_id": "cA", "order_id": "vA", "status": "FILLED", "qty": 100, "filled_qty": 100,
                             "filled_cost": 5200, "avg_price": 108}])
        check("an orphan already in the store is retired on the next pass, with no other change", "cA" not in store["fills"]
              and store["fills"]["vA"]["state"] == "FILLED")
        # never the other way: a TERMINAL client-id record is evidence and is kept
        store["fills"]["cB"] = {"state": "NO_FILL", "client_id": "cB"}
        registry.put_fills([{"client_id": "cB", "order_id": "vB", "status": "OPEN", "qty": 10}])
        check("a terminal client-id record is never removed by a later non-terminal row", store["fills"]["cB"]["state"] == "NO_FILL")
        # unknown stays unknown: FILLED with no quantity is not a fill, and its twin's removal invents nothing
        store["fills"]["cC"] = {"state": "PLACED", "client_id": "cC"}
        registry.put_fills([{"client_id": "cC", "order_id": "vC", "status": "FILLED", "qty": 10}])
        check("FILLED with no confirmed amount stays PLACED / unknown - never zero, never filled",
              store["fills"]["vC"]["state"] == "PLACED" and store["fills"]["vC"]["filled_stake"] is None and "cC" not in store["fills"])
        # two different orders never collide
        registry.put_fills([{"client_id": "cD", "status": "SENDING", "qty": 5}, {"client_id": "cE", "order_id": "vE", "status": "FILLED", "qty": 5, "filled_qty": 5}])
        check("another order's client-id record is untouched", store["fills"]["cD"]["state"] == "PLACED")
    finally:
        registry._commit = real

    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all Stage 3 fill-persistence checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
