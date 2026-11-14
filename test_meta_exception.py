#!/usr/bin/env python3
"""
PRIORITY 4 REGRESSION (Peter, Nov 14 2026): missing metadata is flagged at CREATION.

100 ledger rows carry neither a league nor a game, so they can never match a fixture and their
CLV is unreachable forever - and by the time a settlement report would have noticed, the venue
data needed to repair them was gone. Checked when the order is recorded, the same gap is a
notification while the information still exists.

It must REPORT and never gate: put_order stores the order whatever it finds.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import registry  # noqa: E402

BAD = []
FULL = {"key": "r1|NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER",
        "source": "r1", "fill_line": 48.5, "fill_book": "novig",
        "live_order": {"book": "novig", "order_id": "abc", "client_id": "cid"}}


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def captured_put(rec):
    got = {}

    def fake_commit(merge, tries=4):
        d = {}
        merge(d)
        got.update({"orders": d.get("orders") or []})
        return True

    real = registry._commit
    registry._commit = fake_commit
    try:
        registry.put_order(rec)
    finally:
        registry._commit = real
    return (got.get("orders") or [{}])[0]


def main():
    print("1. a complete order record has no gaps")
    check("no gaps", registry.meta_gaps(FULL) == [], registry.meta_gaps(FULL))
    stored = captured_put(FULL)
    check("and nothing is stamped on it", "meta_missing" not in stored, stored.get("meta_missing"))

    print("2. each missing field is named individually")
    cases = {
        "lane": dict(FULL, key="NCAAF|A @ B|total|UNDER", source=""),
        "line": {k: v for k, v in FULL.items() if k != "fill_line"},
        "venue": dict(FULL, fill_book=None, live_order={"order_id": "abc"}),
        "order_id": dict(FULL, live_order={"book": "novig"}),
    }
    for field, rec in cases.items():
        gaps = registry.meta_gaps(rec)
        check(f"{field} reported missing", field in gaps, gaps)

    print("3. a record with no key loses league AND teams")
    gaps = registry.meta_gaps({"source": "r1", "fill_line": 1.5, "fill_book": "novig",
                               "live_order": {"order_id": "x"}})
    check("league missing", "league" in gaps, gaps)
    check("teams missing", "teams" in gaps, gaps)

    print("4. the gap is stamped on the record at creation, not later")
    stored = captured_put(cases["venue"])
    check("meta_missing stored", stored.get("meta_missing") == ["venue"], stored.get("meta_missing"))
    check("with a timestamp", bool(stored.get("meta_checked")), stored)

    print("5. it is NOT a gate - the order is always recorded")
    bare = {"key": "", "live_order": {}}
    stored = captured_put(bare)
    check("order still stored", stored != {}, stored)
    check("every field flagged", set(stored.get("meta_missing") or []) == set(registry.META_REQUIRED),
          stored.get("meta_missing"))

    print("6. a broken check never stops an order being recorded")
    real_gaps = registry.meta_gaps
    registry.meta_gaps = lambda rec: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        stored = captured_put(FULL)
        check("stored despite the check raising", stored != {}, stored)
        check("and nothing bogus is stamped", "meta_missing" not in stored, stored)
    finally:
        registry.meta_gaps = real_gaps

    print("7. fixture identity and execution are not demanded at creation")
    check("fixture not required", "fixture" not in registry.META_REQUIRED, registry.META_REQUIRED)
    check("filled_stake not required", "filled_stake" not in registry.META_REQUIRED,
          registry.META_REQUIRED)

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all metadata-exception checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
