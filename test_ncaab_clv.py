#!/usr/bin/env python3
"""NCAAB live CLV scoring (Peter, Nov 16): same certified close, cache-only fixtures, reopen exactly four."""
import copy
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl

BAD = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        BAD.append(name)


START = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)


def tick(when, price, limit=500):
    return {"createdAt": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "price": price, "limit": limit}


def market(a, b, age_min=10, limit=500):
    t = START - timedelta(minutes=age_min)
    return {"outcomes": {"o1": {"players": {"0": [tick(t, a, limit)]}}, "o2": {"players": {"0": [tick(t, b, limit)]}}}}


MK = {"9001": [11, "totals", 141.5, {"o1": "Over", "o2": "Under"}],
      "9002": [11, "spreads", -6.5, {"o1": "1", "o2": "2"}]}
PM = {"9001": market(1.95, 1.87), "9002": market(1.91, 1.91)}
FX = {"p1": "Duke Blue Devils", "p2": "North Carolina Tar Heels", "n1": "Duke Blue Devils",
      "n2": "North Carolina Tar Heels", "lg": "NCAAB", "start": "2026-11-14T00:00:00.000Z"}

# ---- gates
check("SPORT (other jobs' league list) is unchanged", cl.SPORT == {"NBA": 11, "NFL": 14, "NCAAF": 14, "NHL": 15})
check("NCAAB is scored on basketball's sport id", cl.SCORE_SPORT.get("NCAAB") == 11)
check("NCAAB fixtures are cache-only (no paid lookup)", "NCAAB" in cl.CACHE_ONLY_FX)
src = open("clv_ledger.py").read()
need = src[src.index("    beyond = {}\n    for k, rec in pend:"):src.index("    fetched = set()")]
check("the fixture-need loop skips cache-only leagues before any refresh is queued",
      need.index("if lg in CACHE_ONLY_FX") < need.index("need[lg] ="))

# ---- same certified close as every other league
r, why = cl.close_for({"bet": "Over 141.5", "game": "North Carolina @ Duke"}, FX, PM, MK, START, "NCAAB")
exp = cl.novig_p(1.95, 1.87)
check("NCAAB total, own line: no-vig Pinnacle close", r and abs(r["p"] - exp) < 1e-12 and r["how"] == "own line")
r_nba, _ = cl.close_for({"bet": "Over 141.5", "game": "x"}, dict(FX, lg="NBA"), PM, MK, START, "NBA")
check("identical inputs give the identical close under NBA (one formula)", r_nba and abs(r_nba["p"] - r["p"]) < 1e-12)
r, why = cl.close_for({"bet": "Duke -6.5", "game": "North Carolina @ Duke"}, FX, PM, MK, START, "NCAAB")
check("NCAAB spread, held team resolved, own line", r and r["how"] == "own line" and abs(r["p"] - 0.5) < 1e-12)
r2, _ = cl.close_for({"bet": "North Carolina +6.5", "game": "North Carolina @ Duke"}, FX, PM, MK, START, "NCAAB")
check("opposite side reads the complement", r2 and abs(r2["p"] - 0.5) < 1e-12)
r, why = cl.close_for({"bet": "Kentucky -6.5", "game": "North Carolina @ Duke"}, FX, PM, MK, START, "NCAAB")
check("a team not in the fixture is never certified", r is None)
r, why = cl.close_for({"bet": "Over 158.5", "game": "x"}, FX, PM, MK, START, "NCAAB")
check("a line far from Pinnacle's main is refused (wrong game/market)", r is None and "far from" in why)
stale = {"9001": market(1.95, 1.87, age_min=cl.FRESH_MIN + 5)}
r, why = cl.close_for({"bet": "Over 141.5", "game": "x"}, FX, stale, MK, START, "NCAAB")
check("a stale close (older than FRESH_MIN) is refused", r is None)
r, why = cl.close_for({"bet": "…", "game": "x"}, FX, PM, MK, START, "NCAAB")
check("a bet with no recorded side is refused", r is None and ("not parsed" in why or "side was never recorded" in why))


# ---- reopen exactly the four
def row(lg="NCAAB", src="bot", why="league NCAAB not covered", day="2026-11-14T00:30:00Z", done=True, clv=None):
    return {"snap": {"league": lg, "source": src, "game_start": day}, "done": done, "clv": clv, "why": why, "tries": 1}


NOW = datetime(2026, 11, 16, 19, 0, tzinfo=timezone.utc)
four = {f"b{i}": row() for i in range(4)}
noise = {"peter": row(src="manual"), "old": row(day="2026-11-05T00:30:00Z"), "other": row(why="no Pinnacle totals close"),
         "nba": row(lg="NBA", why="league NBA not covered"), "scored": row(clv=0.01)}
st = {"bets": dict(copy.deepcopy(four), **copy.deepcopy(noise))}
check("exactly four qualifying rows are reopened", cl.ncaab_reopen(st, NOW) == "reopened 4")
check("each reopened row is open again with tries reset and stamped",
      all(not st["bets"][k]["done"] and st["bets"][k]["tries"] == 0 and st["bets"][k]["ncaab_reopened"] for k in four))
check("no other row is touched", all(st["bets"][k] == noise[k] for k in noise))
check("it runs once only", cl.ncaab_reopen(st, NOW) == "already applied")
for n in (3, 5):
    st = {"bets": {f"b{i}": row() for i in range(n)}}
    before = copy.deepcopy(st)
    check(f"{n} qualifying rows -> refused, nothing reopened (fail closed)",
          cl.ncaab_reopen(st, NOW).startswith("refused") and st == before)

print(f"\n{'ALL PASS' if not BAD else str(len(BAD)) + ' FAILED'}")
sys.exit(1 if BAD else 0)
