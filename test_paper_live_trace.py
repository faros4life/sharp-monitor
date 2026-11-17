#!/usr/bin/env python3
"""Nov 17 (Project 3): paper Bets Board PLAY calls traced to the executor's record by EXACT play key."""
import sys

import report_sections as rs

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


G1, G2, G3, G4 = "A vs B: Total Points", "C vs D: Total Points", "E vs F: Total Points", "G vs H: Total Points"
calls = {
    "c1": {"call": "PLAY", "day": "2026-11-13", "at": "1", "league": "NBA", "mk": "total", "game": G1, "side": "Over 220.5 points", "price": -108, "result": "W", "units": 0.93},
    "c2": {"call": "PLAY", "day": "2026-11-13", "at": "2", "league": "NBA", "mk": "total", "game": G2, "side": "NOT Over 210.5 points", "price": -100, "result": "W", "units": 1.0},
    "c3": {"call": "PLAY", "day": "2026-11-13", "at": "3", "league": "NBA", "mk": "total", "game": G3, "side": "Over 200.5 points", "price": -110, "result": "L", "units": -1.0},
    "c4": {"call": "PLAY", "day": "2026-11-13", "at": "4", "league": "NBA", "mk": "total", "game": G4, "side": "Over 230.5 points", "price": -110},
    "old": {"call": "PLAY", "day": "2026-11-10", "at": "0", "league": "NBA", "mk": "total", "game": G1, "side": "Over 1", "result": "W", "units": 1},
    "pass": {"call": "PASS", "day": "2026-11-13", "at": "5", "league": "NBA", "mk": "total", "game": G1, "side": "Over 1"}}
orders = [{"key": f"board|NBA|{G1}|total|OVER", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "o1", "book": "novig"}},
          {"key": f"board|NBA|{G2}|total|UNDER", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "o2"}},
          {"key": f"board|NBA|{G3}|total|OVER", "et_day": "2026-11-13", "verdict": "HOLD", "live_why_not": "below alert price", "live_order": {}},
          {"key": "board|NBA|X vs Y: Total Points|total|UNDER", "et_day": "2026-11-13", "live_order": {"status": "placed", "book": "novig"}}]
fills = {"o1": {"state": "FILLED"}, "o2": {"state": "NO_FILL"}}
out, extra, summ = rs.paper_live_trace(calls, orders, fills, "2026-11-12")
by = {r["game"]: r for r in out}
check("only PLAY calls from the start date", len(out) == 4)
check("'NOT Over' maps to UNDER for the exact key", by[G2]["key"].endswith("|total|UNDER"))
check("filled order -> FILLED", by[G1]["cat"] == "FILLED")
check("placed but no fill -> PLACED, NO FILL", by[G2]["cat"] == "PLACED, NO FILL")
check("decided, not placed carries the executor's reason", by[G3]["cat"] == "DECIDED, NOT PLACED" and "below alert price" in by[G3]["detail"])
check("no executor record -> NOT DECIDED", by[G4]["cat"] == "NOT DECIDED")
check("ungraded paper call counted as UNGRADED, never W/L", summ["NOT DECIDED"]["UNGRADED"] == 1 and summ["NOT DECIDED"]["W"] == 0)
check("summary shows winners AND losers per category", summ["DECIDED, NOT PLACED"]["L"] == 1 and summ["PLACED, NO FILL"]["W"] == 1)
check("a placed live board order that was not a paper PLAY is listed", len(extra) == 1 and "X vs Y" in extra[0]["key"])
txt = rs.render_trace(out, extra, summ)
check("no currency sign in the section", "$" not in txt)
# venue evidence wins over a missing registry fill record
live = [{"game": "Charlotte Hornets @ Denver Nuggets", "bet": "Under 210.5", "book": "Novig", "price": -105, "result": "W", "game_start": "2026-11-14T00:30:00Z"}]
calls2 = {"c2": dict(calls["c2"], game="Charlotte vs Denver: Total Points")}
o2 = [{"key": "board|NBA|Charlotte vs Denver: Total Points|total|UNDER", "et_day": "2026-11-13", "live_order": {"status": "placed", "order_id": "o2"}}]
out2, _e, _s = rs.paper_live_trace(calls2, o2, {"o2": {"state": "NO_FILL"}}, "2026-11-12", live_rows=live)
check("a venue-confirmed live position is FILLED even without a registry fill record", out2[0]["cat"] == "FILLED")
live2 = live + [dict(live[0])]
out3, _e, _s = rs.paper_live_trace(calls2, o2, {"o2": {"state": "NO_FILL"}}, "2026-11-12", live_rows=live2)
check("two matching live rows -> not guessed (falls back to the executor record)", out3[0]["cat"] == "PLACED, NO FILL")

print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
