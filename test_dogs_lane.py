#!/usr/bin/env python3
"""DOGS lane: liquidity underdogs, $25-50k print, no sharp tag, spread/ML (Peter, Nov 23 2026). Offline.

Three things are checked: (1) the selection reproduces the record the ruling was made on, row for row, from the
feed itself; (2) every bet string names the row's own side and number - read a sign backwards and the lane bets
the other team; (3) every dispatch point knows the lane, because a lane added to a list but not to a dispatch
point is a no-op that looks like success."""
import json
import os
import sys
from datetime import timedelta

import executor as ex

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "executor.py")).read()
FEED = [x for x in json.load(open(os.path.join(HERE, "liquidity", "alerts.json")))["alerts"] if isinstance(x, dict)]

# --- 1. ships OFF, own unit and limits ---------------------------------------------------------
ok("ships OFF with the variable unset", ex.DOGS_LIVE is False or os.environ.get("EXEC_DOGS_LIVE", "").lower() == "on")
ok("unit is $100 and nothing else's", ex.DOGS_UNIT == 100.0 and ex.unit_for("dogs") == 100.0
   and ex.unit_for("r1") == ex.R1_UNIT and ex.unit_for(None) == ex.LIVE_UNIT)
ok("a +money dog risks exactly one unit", ex.live_stake(120, ex.DOGS_UNIT)[0] == 100.0, ex.live_stake(120, ex.DOGS_UNIT))

# --- 2. the row conditions ---------------------------------------------------------------------
B = {"market": "spread", "price_american": 104, "new_money": 30000, "sharp_agree": [], "sharp_oppose": []}
ok("qualifies: dog, $30k, no tags, spread", ex.dogs_qualifies(B))
ok("moneyline qualifies too", ex.dogs_qualifies(dict(B, market="moneyline")))
ok("total never qualifies", not ex.dogs_qualifies(dict(B, market="total")))
ok("+100 is a dog, -101 is not", ex.dogs_qualifies(dict(B, price_american=100)) and not ex.dogs_qualifies(dict(B, price_american=-101)))
ok("money window is [25k, 50k)", ex.dogs_qualifies(dict(B, new_money=25000)) and not ex.dogs_qualifies(dict(B, new_money=24999))
   and not ex.dogs_qualifies(dict(B, new_money=50000)))
ok("a sharp-agree tag disqualifies", not ex.dogs_qualifies(dict(B, sharp_agree=["x"])))
ok("a sharp-oppose tag disqualifies", not ex.dogs_qualifies(dict(B, sharp_oppose=["x"])))
ok("missing price or money never qualifies", not ex.dogs_qualifies(dict(B, price_american=None))
   and not ex.dogs_qualifies(dict(B, new_money=None)) and not ex.dogs_qualifies(dict(B, new_money="abc")))

# --- 3. bet strings ----------------------------------------------------------------------------
ok("Kalshi dog: 'NOT Air Force wins by over 5.5' is Wyoming +5.5",
   ex.dogs_bet({"side": "Wyoming", "game": "Air Force vs Wyoming: Spread", "line": 5.5, "price_american": 104, "market": "spread"})
   == "Wyoming +5.5 (+104)")
ok("Kalshi plus-priced favorite keeps its minus number",
   ex.dogs_bet({"side": "Boston", "game": "New York vs Boston: Spread", "line": -2.5, "price_american": 104, "market": "spread"})
   == "Boston -2.5 (+104)")
ok("Novig ' @ ' game", ex.dogs_bet({"side": "Kansas City Chiefs", "game": "Kansas City Chiefs @ Seattle Seahawks", "line": 2.5,
                                    "price_american": 115, "market": "spread"}) == "Kansas City Chiefs +2.5 (+115)")
ok("ProphetX ' at ' game", ex.dogs_bet({"side": "New York Jets", "game": "Buffalo Bills at New York Jets", "line": 7.5,
                                        "price_american": 101, "market": "spread"}) == "New York Jets +7.5 (+101)")
ok("moneyline", ex.dogs_bet({"side": "Columbus", "game": "Vegas vs Columbus", "line": None, "price_american": 117,
                             "market": "moneyline"}) == "Columbus ML (+117)")
ok("a name containing ' at ' is not split inside the name",
   ex.dogs_teams({"game": "University at Albany vs Holy Cross: Spread"}) == ["University at Albany", "Holy Cross"])
ok("side that is not one of the two teams -> None (pre-formatted Novig shape)",
   ex.dogs_bet({"side": "UVA -3.5 (-3.5)", "game": "UVA @ Duke", "line": -3.5, "price_american": 110, "market": "spread"}) is None)
ok("spread with no line -> None", ex.dogs_bet({"side": "Duke", "game": "UVA @ Duke", "line": None, "price_american": 110,
                                               "market": "spread"}) is None)
ok("unknown market -> None", ex.dogs_bet({"side": "Duke", "game": "UVA @ Duke", "line": 1, "price_american": 110, "market": "total"}) is None)

# --- 4. the selection reproduces the record, row for row ----------------------------------------
elig = sorted([x for x in FEED if not x.get("artifact") and not x.get("close_suspect")
               and str(x.get("book") or "").lower() not in ex.DOGS_NOT_BETTABLE and ex.iso_t(x.get("alerted_utc"))],
              key=lambda x: ex.iso_t(x["alerted_utc"]))
first = {}
for x in elig:
    first.setdefault((str(x.get("game")).lower(), x.get("market"), str(x.get("side")).lower()), x)
want = [x for x in first.values() if ex.dogs_qualifies(x) and ex.iso_t(x.get("start_utc"))
        and ex.iso_t(x["start_utc"]) > ex.iso_t(x["alerted_utc"]) + timedelta(minutes=1)]
got_n, wrong, unread, by_mk = 0, [], 0, {"spread": 0, "moneyline": 0}
_cap = ex.DOGS_MAX_PLAYS
ex.DOGS_MAX_PLAYS = 10 ** 6
try:
    for x in want:
        now = ex.iso_t(x["alerted_utc"]) + timedelta(minutes=1)        # the bot looks one minute after the print
        plays, _sk = ex.dogs_select([y for y in FEED if ex.iso_t(y.get("alerted_utc")) and ex.iso_t(y["alerted_utc"]) <= now], now)
        mine = [p for p in plays if p["alert_utc"] == x["alerted_utc"] and p["game"] == x["game"]
                and p["dogs_entry"]["dogs_market"] == x["market"]]
        if not mine:
            unread += 1
            continue
        p = mine[0]
        got_n += 1
        by_mk[x["market"]] += 1
        k = p["play_key"].split("|")
        if not (k[0] == "dogs" and k[-1] == str(x["side"]) and k[-2] == "side" and p["source"] == "dogs"
                and p["dogs_entry"]["price_after_fee"] == x["price_american"]
                and (p["dogs_entry"]["point"] == x.get("line") if x["market"] == "spread" else p["dogs_entry"]["point"] is None)):
            wrong.append(p["play_key"][:5])
finally:
    ex.DOGS_MAX_PLAYS = _cap
graded = [x for x in want if x.get("result") in ("W", "L", "P") and x.get("units_flat") is not None]
refused = [x for x in want if ex.dogs_bet(x) is None]
ok("every qualifying first print with a readable side is selected one minute after it fires",
   got_n == len(want) - len(refused) and unread == len(refused), f"selected {got_n} of {len(want)}, refused {len(refused)}, missed {unread}")
ok("the only rows refused are those whose side is not one of the game's two team names (never guessed)",
   all(str(x.get("side")) not in ex.dogs_teams(x) for x in refused) and len(refused) <= 0.06 * len(want), len(refused))
sel = [x for x in want if ex.dogs_bet(x) is not None and x.get("result") in ("W", "L", "P") and x.get("units_flat") is not None]
print(f"      selectable record (refused rows out): n {len(sel)}, {sum(x['result'] == 'W' for x in sel)}-{sum(x['result'] == 'L' for x in sel)}, "
      f"{sum(x['units_flat'] for x in sel):+.2f}u, {sum(x['units_flat'] for x in sel) / max(len(sel), 1):+.3f}/play; refused {len(refused)}")
ok("every selected play is keyed to the row's OWN side, with the row's own price and line", not wrong, len(wrong))
w = sum(x["result"] == "W" for x in graded); l = sum(x["result"] == "L" for x in graded)
u = sum(x["units_flat"] for x in graded)
print(f"      record on the feed as it stands today: n {len(graded)}, {w}-{l}, {u:+.2f}u, {u / max(len(graded), 1):+.3f}/play "
      f"(ruling basis 23 Nov: n128, 76-52, +39.62u)")
ok("the selection covers at least the ruling's record (the feed only grows)", len(graded) >= 128 and w >= 76, f"n {len(graded)} W {w}")
ok("both markets are represented", by_mk["spread"] > 0 and by_mk["moneyline"] > 0, by_mk)

# --- 5. first print only, freshness, no backlog --------------------------------------------------
x0 = want[-1]
t0 = ex.iso_t(x0["alerted_utc"])
later = dict(x0, alerted_utc=(t0 + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), new_money=30000)
bad_first = dict(x0, new_money=90000)
p_, _ = ex.dogs_select([bad_first, later], t0 + timedelta(minutes=6))
ok("a later print never qualifies when the FIRST print did not", p_ == [])
p_, _ = ex.dogs_select([x0], t0 + timedelta(minutes=ex.DOGS_MAX_AGE_MIN + 1))
ok("a stale print does not fire (no backlog when the switch is first turned on)", p_ == [])
p_, _ = ex.dogs_select([x0], t0 + timedelta(minutes=2))
ok("a fresh print fires", len(p_) == 1)
p_, _ = ex.dogs_select([dict(x0, start_utc=(t0 - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))], t0 + timedelta(minutes=2))
ok("a started game never fires", p_ == [])
p_, _ = ex.dogs_select([dict(x0, book="polymarket")], t0 + timedelta(minutes=2))
ok("a Polymarket GLOBAL print never fires", p_ == [])
p_, _ = ex.dogs_select([dict(x0, artifact=True)], t0 + timedelta(minutes=2))
ok("an artifact never fires", p_ == [])
many = [dict(x0, game=f"Team{i}a vs Team{i}b", side=f"Team{i}a", market="moneyline", line=None) for i in range(20)]
p_, _ = ex.dogs_select(many, t0 + timedelta(minutes=2))
ok("selection stops at the play cap", len(p_) <= ex.DOGS_MAX_PLAYS, len(p_))

# --- 6. the gate fails closed --------------------------------------------------------------------
_s = dict(ex.DOGS)
try:
    ex.DOGS.update(risk=0.0, keys=set(), known=False)
    ok("unknown exposure refuses", ex.dogs_gate(100)[0] is False)
    ex.DOGS["known"] = True
    ok("known and empty allows one unit", ex.dogs_gate(100)[0] is True)
    ok("zero / unreadable risk refuses", ex.dogs_gate(0)[0] is False and ex.dogs_gate("x")[0] is False)
    ex.DOGS["risk"] = ex.DOGS_DAILY_RISK - 50
    ok("daily risk limit refuses", ex.dogs_gate(100)[0] is False)
    ex.DOGS.update(risk=0.0, keys={f"k{i}" for i in range(ex.DOGS_MAX_PLAYS)})
    ok("play cap refuses a new key", ex.dogs_gate(100, "new")[0] is False)
    ok("a key already counted is not counted twice", ex.dogs_gate(100, "k0")[0] is True)
finally:
    ex.DOGS.clear(); ex.DOGS.update(_s)

# --- 7. wiring: every dispatch point knows the lane ------------------------------------------------
ok("play_key prefix registered", "dogs|" in ex.LANE_PREFIXES)
ok("lane name (drives the Telegram tag)", ex.LANE_NAME.get("dogs") == "DOGS" and ex.src_tag({"source": "dogs"}) == "[DOGS] ")
ok("lane_tag on a result", ex.lane_tag({"play": {"source": "dogs"}, "live": {}}) == "[DOGS] ")
ok("candidates include the lane", "+ ncsplays + dogsplays + l2plays" in SRC and "dogsplays = dogs_plays(now)" in SRC)
ok("own live-decision branch", 'elif p.get("source") == "dogs":' in SRC and "dogs_gate(lr, lk)" in SRC
   and '"lane": "dogs", "unit": DOGS_UNIT' in SRC)
ok("alert-line floor applies to the lane", 'p.get("source") in ("board", "r1", "ncs", "dogs")' in SRC)
ok("exposure is read from the ledger for the lane", 'row.get("source") == "dogs"' in SRC and 'DOGS["known"] = True' in SRC)
ok("not treated as a Muse/sharp play for taken_now", '("rules", "board", "r1", "lane2", "ncs", "dogs")' in SRC)
ok("per-lane report and header list the lane", '("dogs", "DOGS (liquidity dogs)"' in SRC and '("DOGS", DOGS_LIVE, DOGS_UNIT)' in SRC)
ok("reads LIQ-MAIN only", ex.DOGS_FEED == "liquidity/alerts.json")
wf = open(os.path.join(HERE, ".github", "workflows", "executor-dry-run.yml")).read()
ok("the workflow passes the switch, default off", "EXEC_DOGS_LIVE: ${{ vars.EXEC_DOGS_LIVE || 'off' }}" in wf)
import registry as rg
ok("registry lane map knows the lane (reporting)", rg.row_lane({"key": "NBA|A @ B|side|A", "source": "dogs"}) == "dogs")

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
