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
        {"id": "c", "ingest_checked": "2026-11-14T20:00:00Z", "game_start": "2026-11-15T01:00:00Z"},
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
check("Lane 1 units only on EXACT Phase 1 plays dated on/after 9 Nov",
      core.units_for("EXACT:LANE 1", ["2026-11-12T00:00:00+00:00", "x"], -300.0) == -1.0)
check("a segment reaching back before 9 Nov gets no units",
      core.units_for("EXACT:LANE 1", ["2026-11-01T00:00:00+00:00", "x"], 300.0) is None)
check("FUZZY Phase 1 never gets units", core.units_for("FUZZY:LANE 1", ["2026-11-12T00:00:00+00:00"], 300.0) is None)
check("R1 units at 200 from 11 Nov", core.units_for("EXACT:R1", ["2026-11-12T00:00:00+00:00"], 200.0) == 1.0)
check("Board V3 before 11 Nov gets no units", core.units_for("EXACT:BOARD V4", ["2026-11-10T00:00:00+00:00"], 200.0) is None)
check("CONFLICT and UNATTRIBUTED never get units", core.units_for("CONFLICT(registry=BOARD V4)", ["2026-11-12T00:00:00+00:00"], 200.0) is None)
# exactly-once over a real build: two partial-fill rows of one order merge into ONE play, never two
idx = {"o1": [("novig", "board|NFL|a+b|side|a", "board")]}
rws = [{"id": "r1", "source": "bot", "order_ref": "o1", "book": "novig", "result": "W", "stake": 50, "profit": 45, "settled": "2026-11-15T21:00:00Z"},
       {"id": "r2", "source": "bot", "order_ref": "o1", "book": "novig", "result": "W", "stake": 50, "profit": 45, "settled": "2026-11-15T21:00:00Z"},
       {"id": "r3", "source": "bot", "book": "novig", "result": "L", "stake": 100, "profit": -100, "settled": "2026-11-15T21:00:00Z"}]
rep = core.build(rws, idx, lambda x: x, None, {"r1": 0.01})
eo = rep["exactly_once"]
check("every bot row lands in exactly one play", eo["ok"] and eo["rows"] == 3 and eo["distinct"] == 3, eo)
check("each row's bucket is recorded", set(rep["row_bucket"]) == {"r1", "r2", "r3"})
so, sp = rs.day_selections("2026-11-15",
    [{"key": "board|NFL|a+b|side|a", "source": "board", "et_day": "2026-11-15", "live_order": {"status": "placed", "order_id": "o1"}},
     {"key": "r1|NCAAF|c+d|side|c", "source": "r1", "et_day": "2026-11-14"}],
    {"o1": {"state": "PARTIAL"}},
    [dict(r, game="A @ B", bet="A +3", game_start="2026-11-15T18:00:00Z") for r in rws[:1]] +
    [{"id": "r9", "source": "bot", "game": "X @ Y", "bet": "Over 232.5", "game_start": "2026-11-16T01:00:00Z"}],
    {"r1": 0.01}, rep["row_bucket"])
check("only orders decided that ET day are listed", len(so) == 1 and so[0]["fill_state"] == "PARTIAL", so)
check("an 8 PM ET game (01:00Z next day) belongs to the ET day it is played", len(sp) == 2, sp)
check("an unsettled position shows OPEN and missing CLV, never zero",
      any(p["result"] == "OPEN" and p["clv"] == "MISSING" for p in sp))
od = [{"key": "board|NFL|a|side|a", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "v1", "book": "novig"}},
      {"key": "r1|NCAAF|b|side|b", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "p1", "book": "prophetx"}},
      {"key": "r1|NCAAF|c|side|c", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "n2", "book": "novig"}},
      {"key": "rule|NBA|d|total|U", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "f1", "book": "novig"}}]
fx = rs.fill_exceptions(od, {"f1": {"state": "FILLED"}}, {"v1"}, False)
cats = {e["key"]: e["category"] for e in fx}
check("an order with a fill record is not an exception", "rule|NBA|d|total|U" not in cats)
check("venue evidence of a fill = record gap, position real", cats["board|NFL|a|side|a"].startswith("VENUE SHOWS A FILL"))
check("ProphetX with a capped read = UNKNOWN, never 'no fill'", cats["r1|NCAAF|b|side|b"].startswith("UNKNOWN"))
check("complete Novig read with no fill = NO FILL AT VENUE", cats["r1|NCAAF|c|side|c"].startswith("NO FILL AT VENUE"))
br = [{"id": "a", "result": "W", "game_start": "2026-11-13T18:00:00Z"}, {"id": "b", "result": "L", "game_start": "2026-11-13T18:00:00Z"},
      {"id": "c", "result": "W", "game_start": "2026-11-13T18:00:00Z"}, {"id": "d", "result": "W", "game_start": "2026-11-13T18:00:00Z"},
      {"id": "e", "result": "W", "game_start": "2026-11-13T18:00:00Z"}, {"id": "old", "result": "W", "game_start": "2026-11-01T18:00:00Z"}]
cx = {e["game"] or "": e for e in []}
cx = rs.clv_exceptions([dict(r, game=r["id"]) for r in br],
                       {"b": {"clv": None, "tries": 2, "why": "no Pinnacle tick within 60 min"}, "c": {"clv": 0.01},
                        "d": {"clv": None, "done": True, "why": "league XYZ not covered"}, "e": {"clv": 0.02, "fixture_doubt": {"why": "x"}}},
                       {"a": 0.01}, {"c"})
cc = {e["game"]: e["category"] for e in cx}
check("certified rows and pre-12-Nov rows are not exceptions", "a" not in cc and "old" not in cc and len(cc) == 4, cc)
check("not scored yet = PENDING with tries", cc["b"].startswith("PENDING") and "tries 2" in cc["b"])
check("stale-excluded named as such", cc["c"].startswith("EXCLUDED AS STALE"))
check("done without a close = UNRECOVERABLE with the reason", cc["d"].startswith("UNRECOVERABLE") and "not covered" in cc["d"])
check("fixture doubt named as such", cc["e"].startswith("FIXTURE DOUBT"))
check("category counts are names only", rs.category_counts(fx) == {"VENUE SHOWS A FILL": 1, "UNKNOWN": 1, "NO FILL AT VENUE": 1})
# ProphetX matching detail
r1 = {"data": {"matching_details": [{"wager_id": "p1", "matched_stake": 50}, {"wager_id": "z9", "matched_stake": 0}],
               "next_cursor": "abc"}}
check("records found anywhere in the response", len(core.px_match_records(r1)) == 2)
check("cursor found", core.px_next_cursor(r1) == "abc" and core.px_next_cursor({"data": {"next_cursor": ""}}) is None)
m = core.px_matched_ids(core.px_match_records(r1))
check("a zero-quantity record is not a fill", m == {"p1"}, m)
check("matched -> FILLED", core.px_classify(["p1"], m, False) == "FILLED")
check("no match on an INCOMPLETE read -> UNKNOWN, never UNFILLED", core.px_classify(["p2"], m, False) == "UNKNOWN")
check("no match on a complete paged read -> UNFILLED", core.px_classify(["p2"], m, True) == "UNFILLED")
fx2 = rs.fill_exceptions(od, {"f1": {"state": "FILLED"}}, {"v1"}, False, {"matched": {"p1"}, "complete": False}, set())
c2 = {e["key"]: e for e in fx2}
check("ProphetX order upgraded to FILLED by matching detail", c2["r1|NCAAF|b|side|b"]["category"].startswith("FILLED"))
check("a confirmed fill with no tracker row is flagged missing from Project 2", c2["r1|NCAAF|b|side|b"]["in_project2"] is False)
fx3 = rs.fill_exceptions(od, {"f1": {"state": "FILLED"}}, {"v1"}, False, {"matched": set(), "complete": False}, {"p1"})
check("incomplete matching read leaves UNKNOWN", {e["key"]: e for e in fx3}["r1|NCAAF|b|side|b"]["category"].startswith("UNKNOWN"))
check("cursor field detected even when empty", core.px_has_cursor_field({"data": {"next_cursor": None}}))
check("no cursor field is not proof of the end", not core.px_has_cursor_field({"data": {"cursor": "x"}}))
old = {"id": "h", "result": "W", "settled": "2026-10-20T05:00:00Z", "ingest_checked": "2026-11-16T13:37:00Z"}
check("a historical bet discovered today is NOT a new fill", rs.project1([old], {"h": 0.01})["first_seen_since_start"] == 0)
check("and never qualifies", rs.project1([old], {"h": 0.01})["qualifying"] == 0)
nt = {"id": "n", "result": "W", "ingest_checked": "2026-11-16T13:37:00Z"}
check("a row with no bet time cannot qualify", rs.project1([nt], {})["first_seen_since_start"] == 0)
pmo = [{"key": "r1|NCAAF|s+v|side|s", "et_day": "2026-11-14", "live_order": {"status": "placed", "order_id": "pm1", "book": "polymarket_us"}}]
check("Polymarket US order with a linked venue row -> FILLED and in Project 2",
      (lambda e: e["category"].startswith("FILLED") and e["in_project2"] is True)(rs.fill_exceptions(pmo, {}, set(), True, None, {"pm1"})[0]))
check("Polymarket US order with no linked row stays UNKNOWN",
      rs.fill_exceptions(pmo, {}, set(), True, None, set())[0]["category"].startswith("UNKNOWN"))
Y = core.text_label_yields
check("text label vs exact registry claim, no other-lane order -> registry wins",
      Y({"lane": "LANE 1", "lane_src": None}, "BOARD V4", set()) is True)
check("a registry-derived tracker label never yields", Y({"lane": "LANE 1", "lane_src": "registry-order-id"}, "BOARD V4", set()) is False)
check("a registry order under the label's lane for the same event keeps it CONFLICT",
      Y({"lane": "LANE 1", "lane_src": None}, "BOARD V4", {"LANE 1"}) is False)
check("no disagreement -> nothing to resolve", Y({"lane": "BOARD V4"}, "BOARD V4", set()) is False)
check("no tracker label -> nothing to resolve", Y({}, "BOARD V4", set()) is False)
mk = lambda i, res, st, pr, gs: {"ids": [i], "result": res, "stake": st, "profit": pr, "game_start": gs, "settled": gs, "rows": 1}
pl = [mk("a", "W", 200, 180, "2026-11-12T18:00:00Z"), mk("b", "L", 200, -200, "2026-11-13T18:00:00Z")]
ss = rs.seg_stats(pl, {"a": 0.02}, 200.0, "2026-11-11T00:00:00+00:00")
check("scorecard units = net/unit when every play is on/after the unit start", ss["units"] == -0.1, ss)
check("scorecard CLV excludes a missing close, never zero", ss["clv"] == 2.0 and ss["clv_n"] == 1 and ss["clv_missing"] == 1, ss)
check("no interval below n=5", ss["clv_ci"] is None and ss["units_ci"] is None)
check("a play before the unit start makes units UNAVAILABLE",
      rs.seg_stats(pl, {}, 200.0, "2026-11-13T00:00:00+00:00")["units"] is None)
check("ROI is net over risked", ss["roi"] == -5.0, ss)
bk = {"buckets": {"EXACT:R1": {"_settled_timed": pl, "open_or_ambiguous": 1}}}
sc = rs.lane_scope(bk, "R1", {"a": 0.02}, {"R1": ("2026-11-11T00:00:00+00:00", 200.0)})
check("a 2-play lane is INSUFFICIENT EVIDENCE under the registered gate", sc["verdict"] == "INSUFFICIENT EVIDENCE", sc["verdict"])
check("H1 + H2 = whole", sc["H1"]["n"] + sc["H2"]["n"] == sc["whole"]["n"])
check("scorecard text carries no currency sign", "$" not in rs.render_scorecard([("X", {"R1": sc})], {}, {}))
from datetime import datetime as _D, timezone as _Z
NOW = _D(2026, 11, 16, 15, 0, tzinfo=_Z.utc)
gr = [{"id": "a", "game": "A @ B", "bet": "A -3", "book": "novig", "result": "W", "stake": 200, "profit": 180, "game_start": "2026-11-13T00:00:00Z"},
      {"id": "b", "game": "C @ D", "bet": "C +4", "book": "prophetx", "result": "L", "stake": 200, "profit": -200, "game_start": "2026-11-13T00:00:00Z"},
      {"id": "c", "game": "E @ F", "bet": "E -1", "book": "novig", "game_start": "2026-11-13T00:00:00Z"},
      {"id": "d", "game": "G @ H", "bet": "G -2", "book": "novig", "game_start": "2026-11-16T23:00:00Z"},
      {"id": "e", "game": "I @ J", "bet": "-15.50", "book": "Polymarket US", "result": "W", "stake": None, "profit": 50, "game_start": "2026-11-14T20:00:00Z"}]
rb = {"a": "EXACT:R1", "b": "EXACT:R1", "c": "EXACT:BOARD V4", "d": "EXACT:BOARD V4", "e": "UNATTRIBUTED(no_order_ref)"}
G = {g["id"]: g for g in rs.grade_rows(gr, rb, {"a": 0.012}, {"b": {"done": True, "why": "league NCAAB not covered"}}, set(),
                                       {"R1": ("2026-11-11T00:00:00+00:00", 200.0)}, NOW)}
check("a settled, linked, priced, certified play is FULLY GRADED", G["a"]["fully_graded"] and G["a"]["units"] == 0.9 and G["a"]["roi"] == 90.0, G["a"])
check("a missing close is reported with the ledger's reason, never zero",
      G["b"]["clv"] is None and "league NCAAB not covered" in G["b"]["clv_status"] and not G["b"]["fully_graded"])
check("unsettled 3 days after the game -> MISSING settlement", G["c"]["settle_status"] == "MISSING")
check("a game not finished -> open, not missing", G["d"]["settle_status"].startswith("open"))
check("invalid stake -> missing realized P/L, never guessed", G["e"]["net"] is None and any("realized P/L" in m for m in G["e"]["missing"]))
check("no exact lane -> missing lane, trigger UNKNOWN", G["e"]["trigger"] == "UNKNOWN" and any(m.startswith("lane") for m in G["e"]["missing"]))
S = rs.grade_summary(list(G.values()))
check("summary counts", S["positions"] == 5 and S["settled"] == 3 and S["open"] == 2 and S["fully_graded"] == 1
      and S["missing_settlement"] == 1 and S["missing_pl"] == 1 and S["missing_certified_clv"] == 2 and S["missing_lane"] == 1, S)
check("the private table carries no currency sign", "$" not in rs.render_grades(list(G.values()), S))
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_report_sections: all passed")
