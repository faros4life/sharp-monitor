#!/usr/bin/env python3
"""Nov 17 (Peter, Option A): home-runner Novig fill snapshot - usable only when complete and fresh, compared by
identity not count, per-row gaps fail closed, and a snapshot failure can never touch the positions snapshot."""
import sys
from datetime import datetime, timedelta, timezone

import p2_audit_core as pc

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
ms = lambda d: int(d.timestamp() * 1000)
F = lambda i, mk, oc, t, **k: dict({"fillId": i, "orderId": "o" + i, "clientId": "c" + i, "marketId": mk, "outcomeId": oc, "ts": ms(t)}, **k)

# usable
good = {"fills_utc": iso(NOW - timedelta(minutes=10)), "complete": True, "fills": []}
check("complete and 10 min old -> usable", pc.snapshot_usable(good, NOW)[0])
check("older than 30 min -> not usable", not pc.snapshot_usable(dict(good, fills_utc=iso(NOW - timedelta(minutes=31))), NOW)[0])
check("incomplete (truncated / ids lost) -> not usable", not pc.snapshot_usable(dict(good, complete=False, note="TRUNCATED"), NOW)[0])
check("missing / malformed -> not usable", not pc.snapshot_usable(None, NOW)[0] and not pc.snapshot_usable({"complete": True}, NOW)[0])

# identity, not count
t1 = NOW - timedelta(hours=5)
cloud = [F("1", "m1", "a", t1), F("2", "m2", "b", t1), F("9", "m9", "z", NOW - timedelta(minutes=1))]
home_same = [F("1", "m1", "a", t1), F("2", "m2", "b", t1)]
c = pc.snapshot_compare(cloud, home_same, NOW - timedelta(minutes=10))
check("same fills -> equal 2, nothing else (a fill newer than the cutoff is ignored)", c == {"equal": 2, "field_mismatch": 0, "cloud_only": 0, "home_only": 0})
home_swap = [F("1", "m1", "a", t1), F("3", "m2", "b", t1)]
c = pc.snapshot_compare(cloud, home_swap, NOW - timedelta(minutes=10))
check("same COUNT but different fill -> detected (cloud-only 1, home-only 1)", c["cloud_only"] == 1 and c["home_only"] == 1)
home_field = [F("1", "m1", "a", t1), F("2", "m2", "b", t1, orderId="oX")]
check("same id, different order id -> field mismatch", pc.snapshot_compare(cloud, home_field, NOW)["field_mismatch"] == 1)
check("duplicate fill rows collapse by fillId", pc.snapshot_compare(cloud + [cloud[0]], home_same, NOW - timedelta(minutes=10))["equal"] == 2)

# per-row coverage fails closed
rows = [{"id": "nv|m1|a", "ingest_checked": iso(t1)}, {"id": "nv|m7|q", "ingest_checked": iso(t1)},
        {"id": "nv|m8|r", "ingest_checked": iso(NOW)}, {"id": "nv|m2|b"}, {"id": "px|55"}]
g = pc.snapshot_row_gaps(rows, home_same, iso(NOW - timedelta(minutes=10)))
check("row seen before the snapshot with a fill -> vouched", "nv|m1|a" not in g)
check("row seen before the snapshot with NO fill -> incomplete", "nv|m7|q" in g)
check("row first seen after the snapshot -> incomplete", "nv|m8|r" in g)
check("row with no first-seen time -> incomplete", "nv|m2|b" in g)
check("non-Novig rows untouched", "px|55" not in g)
links = pc.link_index(home_same, [], {"nv": True})
links["_incomplete_ids"] = g
check("a gap row resolves link_source_incomplete, never no_venue_link",
      pc.resolve_link({"id": "nv|m7|q", "book": "Novig"}, links, {}, pc._norm)[0] == "link_source_incomplete")
check("market/outcome alone never makes EXACT (needs a registry claim on the fill's own ids)",
      pc.resolve_link({"id": "nv|m1|a", "book": "Novig"}, links, {}, pc._norm)[0] == "link_order_not_in_registry")

# runner isolation + default shadow
src = open("novig_positions_snapshot.py").read()
check("fills go to their own file, never the positions snapshot", 'FILLS_PATH = "snapshot/novig_fills.json"' in src)
tail = src[src.index("def main():"):]
check("a fill failure is caught before the positions exit status", tail.index("write_fills(now)") < tail.index("sys.exit(1)")
      and "except Exception as ex:\n        print(f\"Fills snapshot not written" in tail)
body = src[src.index("def read_fills"):src.index("def write_fills")]
check("snapshot stores only ids, time and wallet tag - no price, size or cost",
      'FILL_KEYS = ("fillId", "orderId", "clientId", "marketId", "outcomeId")' in src
      and 'row = {k: f.get(k) for k in FILL_KEYS}' in body
      and not any(f'row["{k}"]' in body for k in ("price", "cost", "qty", "size", "amount")))
wf = open(".github/workflows/p2-audit.yml").read()
check("audit gets the NARROW read token only, not the broad snapshot token",
      "NOVIG_READ_TOKEN: ${{ secrets.NOVIG_READ_TOKEN }}" in wf and "NOVIG_SNAPSHOT_TOKEN" not in wf)
check("fallback is SHADOW by default", "P2_NV_FALLBACK: shadow" in wf)
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
