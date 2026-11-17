#!/usr/bin/env python3
"""Nov 17 (Peter): a failed Novig read is labelled as such and never replaces a valid scorecard."""
import sys

import p2_audit as pa
import p2_audit_core as pc

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


rows = [{"id": "nv|m1|o1", "book": "Novig", "result": "W", "stake": 100.0, "profit": 90.0}]
inc = pc.link_index([], [], {"nv": False})
items, st, _c = pc.classify(rows, {}, pc._norm, inc, None)
check("incomplete Novig read -> UNATTRIBUTED(venue_read_unavailable), not no_order_ref",
      items[0][1] == "UNATTRIBUTED(venue_read_unavailable)" and st.get("venue_read_unavailable") == 1)
ok = pc.link_index([], [], {"nv": True})
items2, _s, _c = pc.classify(rows, {}, pc._norm, ok, None)
check("complete read with no link -> still no_order_ref (unchanged)", items2[0][1] == "UNATTRIBUTED(no_order_ref)")
rows_l = [dict(rows[0], lane="R1")]
items3, _s, _c = pc.classify(rows_l, {}, pc._norm, inc, None)
check("a tracker text lane during an outage stays FUZZY, never EXACT", items3[0][1].startswith("FUZZY:"))
check("degraded when Novig incomplete", pa.degraded_reason(False, "novig read key not ready").startswith("Novig venue read unavailable"))
check("not degraded when Novig complete", pa.degraded_reason(True, "ok") is None)
src = open("p2_audit.py").read()
tail = src[src.index("why_deg = degraded_reason(nok, nf)"):]
check("a degraded run sends only the notice, never the scorecard",
      tail.index("send_notice(") < tail.index("return 0 if send_private(text, csv_rows)") and "return 0 if send_notice(" in tail)
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
