"""Both reports must attribute, window and count identically. Peter, Nov 27 2026.

bot_live_export knew four lane spellings; the tracker carries "rules", "PHASE 1", "r1" and
"BOARD V3", and it had no Dogs or NCS at all. 47 settled bot rows landed in Unattributed and R1
graded 2 plays against 21 confirmed - so every per-strategy ROI and unit figure was wrong, and the
confidence intervals computed from them inherited it."""
import bot_live_export as x
import executed_clv as xc

FAILED = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


def row(**kw):
    b = {"source": "bot", "result": "W", "stake": 100.0, "profit": 90.0, "lane": "PHASE 1",
         "game": "A @ B", "bet": "u", "book": "px", "date": "2026-11-20"}
    b.update(kw)
    return b


# --- one shared map, imported not copied: the two reports cannot drift --------------------------
ok("the lane map is imported from executed_clv", x.LANE_CANON == dict(xc.LANE_NAME))
ok("every tracker spelling resolves",
   all(s in x.LANE_CANON for s in ("rules", "phase 1", "lane 1", "r1", "board v3", "board v4")))
ok("Dogs and NCS are included", x.LANE_CANON.get("dogs") == "Dogs" and x.LANE_CANON.get("ncs") == "NCS")
for raw, want in (("PHASE 1", "Lane 1"), ("rules", "Lane 1"), ("r1", "R1"), ("R1", "R1"),
                  ("BOARD V3", "Board V3"), ("dogs", "Dogs"), ("NCS", "NCS")):
    ok(f"{raw!r} -> {want}", x.lane_of(row(lane=raw))[0] == want, x.lane_of(row(lane=raw))[0])

# --- never guess ---------------------------------------------------------------------------------
ok("an unknown tag is NOT attributed", x.lane_of(row(lane="mystery"))[0] is None)
ok("a missing tag is NOT attributed", x.lane_of(row(lane=None))[0] is None)

# --- the window is pinned, and a dateless row is OUT ----------------------------------------------
ok("window pinned to 2026-11-12", x.WINDOW_ET == "2026-11-12")
ok("on the boundary is IN", x.in_window(row(date="2026-11-12")))
ok("the day before is OUT", not x.in_window(row(date="2026-11-11")))
ok("a row with no date is OUT, never assumed recent",
   not x.in_window({"date": None, "settled": None, "game_start": None}))

# --- counting -------------------------------------------------------------------------------------
P = x.performance([
    row(lane="PHASE 1", stake=220.0, profit=200.0, game="A @ B", bet="u1"),
    row(lane="PHASE 1", stake=50.0, profit=45.0, game="A @ B", bet="u1"),      # partial of the same play
    row(lane="r1", result="L", stake=200.0, profit=-200.0, game="C @ D", bet="u2"),
    row(lane="dogs", stake=300.0, profit=312.0, game="G @ H", bet="u4"),
    row(source="Peter", stake=500.0, profit=450.0, game="K @ L", bet="m"),      # manual
    row(date="2026-11-01", game="M @ N", bet="u6"),                            # before the window
    row(lane="mystery", game="O @ P", bet="u7"),                               # unattributable
    row(result=None, game="Q @ R", bet="u8"),                                  # unsettled
], {})
L1 = P["by_lane"]["Lane 1"]
ok("partial fills MERGE into one play", L1["n"] == 1, L1["n"])
ok("merged stake is summed", L1["dollars_staked"] == 270.0, L1["dollars_staked"])
ok("merged profit is summed", L1["dollars_pnl"] == 245.0, L1["dollars_pnl"])
ok("manual bets are excluded", all("K @ L" != u["game"] for u in P["unresolved"])
   and sum(v["n"] for v in P["by_lane"].values()) == 3, P["by_lane"].keys())
ok("pre-window rows are excluded", L1["from"] >= "2026-11-12", L1["from"])
ok("unsettled rows are excluded", "Q @ R" not in str(P))
ok("unattributable settled fills go to an explicit bucket",
   P["unresolved_n"] == 1 and P["unresolved"][0]["game"] == "O @ P", P["unresolved"])
ok("and are counted in NO lane", sum(v["n"] for v in P["by_lane"].values()) == 3)

# --- dollars and units stay apart -----------------------------------------------------------------
ok("dollar P&L is reported", L1["dollars_pnl"] == 245.0)
ok("units are reported separately", L1["units"] is not None and L1["units"] != L1["dollars_pnl"])
ok("ROI is dollars over dollars staked", L1["roi_pct"] == round(100 * 245.0 / 270.0, 2), L1["roi_pct"])
D = P["by_lane"]["Dogs"]
ok("a $300 lane and a $100 lane are comparable in UNITS, not dollars",
   abs(D["units_per_play"] - 1.04) < 1e-6, D["units_per_play"])

# --- both halves ------------------------------------------------------------------------------------
H = x.performance([row(game=f"G{i}", bet=f"b{i}", date=f"2026-11-{12 + i:02d}",
                       result="W" if i < 2 else "L", profit=90.0 if i < 2 else -100.0) for i in range(4)], {})["by_lane"]["Lane 1"]
ok("both chronological halves are reported", "first_half" in H and "second_half" in H)
ok("the halves split chronologically", H["first_half"]["to"] <= H["second_half"]["from"])
ok("the halves sum to the whole", H["first_half"]["n"] + H["second_half"]["n"] == H["n"])

# --- the export carries it, log stays counts-only ----------------------------------------------------
src = open("bot_live_export.py", encoding="utf-8").read()
ok("performance is published in the export", '"performance": perf' in src)
ok("the log prints records and counts, no dollars",
   'perf["unresolved_n"]' in src and "dollars_pnl" not in src.split("print(\"performance")[1][:300])

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
