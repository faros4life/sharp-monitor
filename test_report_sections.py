"""Synthetic tests for report_sections.py. No secrets, no network."""
import sys
import report_sections as rs
import p2_audit_core as core
fails = []
def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"  {extra}" if extra else ""))
    if not cond: fails.append(label)

reg_rows = [{"key": "board|a", "decided_utc": "2026-11-15T12:00:00Z"}]
led = [{"key": "board|a", "decided_utc": "2026-11-15T12:00:00Z"}, {"key": "r1|b", "decided_utc": "2026-11-12T15:00:00Z"}]
m, extra = rs.merge_orders(reg_rows, led)
check("ledger restores pruned orders, never duplicates live ones", len(m) == 2 and extra == 1)

rows = [{"id": "a", "result": "W", "settled": "2026-11-13T05:00:00Z", "ingest_checked": "2026-11-12T20:00:00Z"},
        {"id": "b", "result": "L", "settled": "2026-11-14T05:00:00Z", "ingest_checked": "2026-11-13T20:00:00Z"},
        {"id": "c", "ingest_checked": "2026-11-14T20:00:00Z"},
        {"id": "d", "result": "W", "settled": "2026-11-10T05:00:00Z", "ingest_checked": "2026-11-09T20:00:00Z"}]
clv = {"a": 0.01, "d": 0.05}
p1 = rs.project1(rows, clv, None)
check("only rows first seen from 12 Nov ET count", p1["first_seen_since_start"] == 3, p1)
check("graded / pending / missing close separated", p1["graded"] == 2 and p1["pending"] == 1 and p1["missing_close"] == 1, p1)
check("a missing close is never a zero CLV", p1["clv_mean_pct"] == 1.0, p1)
check("qualifying withheld while the baseline is unconfirmed", p1["qualifying"] is None and "NOT CONFIRMED" in p1["qualifying_why"])
check("with a baseline, only rows first seen after it qualify",
      rs.project1(rows, clv, "2026-11-13T00:00:00Z")["qualifying"] == 1)

orders = [{"key": "board|a", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "o1"}},
          {"key": "board|b", "et_day": "2026-11-13", "live_order": {"status": "placed", "client_id": "c9"}},
          {"key": "board|z", "et_day": "2026-11-10", "live_order": {"status": "placed", "order_id": "old"}}]
fills = {"o1": {"state": "FILLED"}, "x": {"state": "RESTING"}}
ig = rs.integrity(orders, fills, rows, clv, {"buckets": {}}, False)
check("placed orders since 12 Nov counted, older excluded", ig["placed_orders_since_start"] == 2, ig)
check("an order with no fill record is flagged", ig["placed_orders_without_fill_record"] == 1, ig)
check("non-terminal fills flagged", ig["fill_records_not_terminal"] == 1)
check("settled rows missing certified CLV flagged", ig["settled_missing_certified_clv"] == 1, ig)
check("ProphetX completeness carried", ig["prophetx_read_complete"] is False)

play = core._combine([{"id": "a", "result": "W", "stake": 100, "profit": 90}, {"id": "b", "result": "W", "stake": 100, "profit": 90}])
check("a play with any row missing a close is counted missing", core._clv([play], clv)["clv_n"] == 0)
check("CLV off by default keeps the old shape", core._agg([play])["clv_n"] is None)
txt = rs.render(p1, ig, 1)
check("render carries no currency sign", "$" not in txt)
o2 = [{"key": "board|NBA|a+b|total|OVER", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "zz"}}]
ig2 = rs.integrity(o2, {"f": {"state": "FILLED", "play_key": "NBA|a+b|total|OVER"}}, [], {}, {}, True)
check("a fill joined by unprefixed play_key is NOT reported missing",
      ig2["placed_orders_without_fill_record"] == 0 and ig2["fill_record_by_play_key"] == 1, ig2)
check("the baseline is the Phase 1 capture commit time", rs.P1_BASELINE_UTC == "2026-11-14T17:57:29Z")
check("rows stamped before the baseline never qualify",
      rs.project1([{"id": "q", "result": "W", "ingest_checked": "2026-11-13T00:00:00Z"}], {})["qualifying"] == 0)
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_report_sections: all passed")
