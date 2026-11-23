#!/usr/bin/env python3
"""Nov 17 (Project 3): live fill rate - registry record first, venue evidence next, never guessed."""
import sys

import report_sections as rs

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


orders = [
    {"key": "board|NBA|A vs B: Total Points|total|OVER", "et_day": "2026-11-13", "decided_utc": "2026-11-13T15:00:00Z",
     "start_utc": "2026-11-14T00:00:00Z", "latency_s": 1200, "alert_price_after_fee": -110, "live_px_price_after_fee": -112,
     "live_order": {"status": "placed", "order_id": "o1", "book": "novig"},
     "live_more": [{"status": "placed", "order_id": "o1b", "book": "prophetx"}]},
    {"key": "board|NBA|C vs D: Total Points|total|UNDER", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "o2", "book": "novig"}},
    {"key": "r1|NCAAB|E @ F|side|E", "et_day": "2026-11-14", "live_order": {"status": "placed", "order_id": "o3", "book": "prophetx"}},
    {"key": "rule|NBA|G @ H|total|UNDER", "et_day": "2026-11-14", "live_order": {"status": "placed", "order_id": "o4", "book": "prophetx"}},
    {"key": "board|NBA|X|total|OVER", "et_day": "2026-11-14", "live_order": {"status": "refused"}},
    {"key": "board|NBA|Y|total|OVER", "et_day": "2026-11-10", "live_order": {"status": "placed", "order_id": "old"}}]
fills = {"o1": {"state": "FILLED"}, "o2": {"state": "NO_FILL"}}
fx = [{"ids": ["o3"], "category": "FILLED - ProphetX matching detail shows a match"},
      {"ids": ["o1b"], "category": "NO FILL AT VENUE - complete venue read shows none"}]
legs, summ = rs.fill_rate(orders, fills, fx, "2026-11-12")
by = {(l["key"][:8], l["kind"]): l for l in legs}
check("only placed legs from the start date (refused and older excluded)", len(legs) == 5)
check("registry FILLED -> FILLED", any(l["outcome"] == "FILLED" and l["venue"] == "novig" and l["kind"] == "first" for l in legs))
check("registry NO_FILL -> NOT FILLED", summ[("BOARD V4", "novig")]["NOT FILLED"] == 1)
check("balance leg classified from venue evidence", any(l["kind"] == "balance" and l["outcome"] == "NOT FILLED" for l in legs))
check("no record and venue says filled -> FILLED", summ[("R1", "prophetx")]["FILLED"] == 1)
check("no record and no evidence -> UNKNOWN, never guessed", summ[("LANE 1", "prophetx")]["UNKNOWN"] == 1)
l1 = next(l for l in legs if l["kind"] == "first" and l["outcome"] == "FILLED")
check("price gap in cents of probability, + = worse than the alert", l1["gap_c"] is not None and l1["gap_c"] > 0)
check("timing in minutes", l1["latency_min"] == 20 and l1["to_start_min"] == 540)
check("no currency sign", "$" not in rs.render_fill_rate(legs, summ))
o5 = [{"key": "board|NBA|P vs Q: Total Points|total|OVER", "et_day": "2026-11-15", "live_order": {"status": "placed", "client_id": "c9", "book": "novig"}}]
lg5, sm5 = rs.fill_rate(o5, {"f1": {"play_key": "NBA|P vs Q: Total Points|total|OVER", "state": "FILLED"}}, [], "2026-11-12")
check("Novig fill found by play key (lane prefix optional)", lg5[0]["outcome"] == "FILLED")
o6 = [{"key": "board|NBA|Orlando vs Boston: Total Points|total|OVER", "et_day": "2026-11-16", "live_order": {"status": "placed", "client_id": "c7", "book": "novig"}}]
pos = {"BOARD V4": [{"game": "Orlando Magic @ Boston Celtics", "bet": "Over 210.5"}]}
lg6, _s = rs.fill_rate(o6, {"f": {"play_key": "NBA|Orlando vs Boston: Total Points|total|OVER", "state": "PLACED"}}, [], "2026-11-12", rows_by_lane=pos)
check("venue-confirmed live position beats a stale PLACED fill record", lg6[0]["outcome"] == "FILLED")
lg7, _s = rs.fill_rate(o6, {}, [], "2026-11-12", rows_by_lane={"BOARD V4": pos["BOARD V4"] * 2})
check("two matching positions -> not guessed", lg7[0]["outcome"] == "UNKNOWN")
cx = [{"id": "a", "why": "the bet text is '-15.50', not a team - the side was never recorded", "league": "NCAAF"},
      {"id": "b", "why": "NCAAB fixture not in any cached store; waiting", "league": "NCAAB"},
      {"id": "c", "why": "no fixture in any basketball competition", "league": "NCAAB"}]
tr = rs.clv_trend(cx, lambda i: "EXACT:R1")
check("trend groups by reason, lane, league", tr == {("side not captured", "EXACT:R1", "NCAAF"): 1, ("fixture not yet fetched", "EXACT:R1", "NCAAB"): 1,
                                                    ("fixture unmatched", "EXACT:R1", "NCAAB"): 1})
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
