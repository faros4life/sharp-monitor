#!/usr/bin/env python3
"""Project 2 audit runner - READ-ONLY. Reads tracker/state.enc and the private registry (GET only).
No Gmail, no order endpoint, no state change, no commit, no send. Public log = counts only. The full report is written
ENCRYPTED to p2_audit_report.enc on the runner only (not committed); delivery is Peter's decision.
Fails closed: unreadable registry or unresolvable lane logic -> nothing is reported."""
import copy
import json
import sys

import tracker_build as tb
import registry as reg
from p2_audit_core import build

st = tb.dec(json.load(open(tb.STATE)))
raw = copy.deepcopy(st.get("bets") or {})
tb.mark_manual_dups(raw)
# RAW rows, NOT tb.group_fills(): group_fills merges on a ProphetX strike id (a market id), which can span orders and lanes.
rows = [b for b in raw.values() if not b.get("dup_of") and (b.get("source") or "") == "bot"]

rr = reg.rows()
if rr is None:
    sys.exit("registry unreadable - lane identity cannot be proven; nothing reported")
try:
    import executor as ex
except BaseException as e:
    sys.exit(f"executor import failed ({type(e).__name__}) - lane names unavailable; nothing reported")

d = lambda x: x if isinstance(x, dict) else {}
index = {}
for row in rr:
    key = row.get("key")
    more = row.get("live_more")
    los = [d(row.get("live_order")), d(row.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]
    placed = [lo for lo in los if lo.get("status") == "placed" and lo.get("order_id") and not lo.get("intent") and not lo.get("voided")]
    if not key or not placed:
        continue
    safe = dict(row, live=d(row.get("live")), play=d(row.get("play")))
    lane = ex.LANE_NAME.get(ex.lane_of(safe))
    for lo in placed:
        index.setdefault(str(lo["order_id"]), []).append((reg._venue(lo.get("book") or row.get("book")), str(key), lane))

rep = build(rows, index, reg._venue)
json.dump(tb.enc(rep), open("p2_audit_report.enc", "w"))
print("bot rows:", len(rows), "| registry order ids:", len(index), "| join:", rep["join"])
for b, v in rep["buckets"].items():
    a = v["all"]
    print(f"{b}: settled {a['settled']} (verified money {a['verified_money']}), open/ambiguous {v['open_or_ambiguous']}, "
          f"no-time {v['settled_no_time']}, mixed time basis {v['MIXED_TIME_BASIS']}")
