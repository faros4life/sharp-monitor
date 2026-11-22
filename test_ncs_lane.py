#!/usr/bin/env python3
"""NCS lane: NCAAB spreads on Kalshi, board v3 PLAY conditions (Peter, Nov 22 2026).

The check that matters most is the BET STRING. A spread row carries `side` (a team), a SIGNED `line`
and a `side_label` in Kalshi's own words. Read the sign backwards and the lane places the opposite
bet, silently, at a price that still looks right. So every row in the live feed is asserted against
its own label here, not a sample.

The rest guards the wiring. A new lane that is added to a list but not to one of the dispatch points
is the repo's worst failure mode - a no-op that looks like success - so each integration point has
its own assertion.
"""
import json
import os
import sys

import executor as ex

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


# --- bet string: the sign of `line` carries the side -----------------------------------------
ok("dog: positive line becomes a plus number",
   ex.ncs_bet({"side": "NJIT", "game": "NJIT vs Boston College: Spread", "line": 23.5,
               "price_american": -108}) == "NJIT +23.5 (-108)")
ok("favorite: negative line becomes a minus number",
   ex.ncs_bet({"side": "St. Thomas", "game": "Southeast Missouri St. vs St. Thomas: Spread", "line": -6.5,
               "price_american": -104}) == "St. Thomas -6.5 (-104)")
ok("plus-money price keeps its sign",
   ex.ncs_bet({"side": "Rice", "game": "Rice vs Stephen F. Austin: Spread", "line": 9.5,
               "price_american": 117}) == "Rice +9.5 (+117)")

# --- fail closed on every malformed shape (the Novig rows) ------------------------------------
ok("Novig pre-formatted side is refused",
   ex.ncs_bet({"side": "UVA -3.5 (-3.5)", "game": "Arkansas vs Virginia: Spread", "line": -3.5,
               "price_american": -110}) is None)
ok("a side that is only a FRAGMENT of a team name is refused (the 'X at Y vs Z' mis-split)",
   ex.ncs_bet({"side": "University", "teams": ["University", "Albany vs Holy Cross"],
               "game": "University at Albany vs Holy Cross: Spread", "line": 2.5,
               "price_american": 104}) is None)
ok("teams come from the game string, not the teams field",
   ex.ncs_teams({"game": "University at Albany vs Holy Cross: Spread",
                 "teams": ["University", "Albany vs Holy Cross"]}) == ["University at Albany", "Holy Cross"])
ok("an unsplittable game string yields no teams", ex.ncs_teams({"game": "something odd"}) == [])
ok("missing line is refused", ex.ncs_bet({"side": "NJIT", "game": "NJIT vs BC: Spread", "price_american": -108}) is None)
ok("missing price is refused", ex.ncs_bet({"side": "NJIT", "game": "NJIT vs BC: Spread", "line": 2.5}) is None)
ok("missing side is refused", ex.ncs_bet({"game": "NJIT vs BC: Spread", "line": 2.5, "price_american": -108}) is None)
ok("unreadable line is refused",
   ex.ncs_bet({"side": "NJIT", "game": "NJIT vs BC: Spread", "line": "n/a", "price_american": -108}) is None)

# --- every real row in the feed, against its own label ----------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in ("liquidity-extra/alerts.json", "liquidity/alerts.json"):
    try:
        d = json.load(open(os.path.join(HERE, f), encoding="utf-8"))
    except Exception:
        continue
    r = d.get("alerts") if isinstance(d, dict) else d
    rows += list(r.values()) if isinstance(r, dict) else (r or [])
sp = [r for r in rows if r.get("league") == "NCAAB" and r.get("market") == "spread"
      and (r.get("book") or "").lower() == ex.NCS_BOOK]
ok("the feed still holds Kalshi NCAAB spread rows to check", len(sp) > 0, str(len(sp)))

bad_sign, bad_team, built = [], [], 0
for r in sp:
    bet = ex.ncs_bet(r)
    if bet is None:
        continue
    built += 1
    lab, ln, side = str(r.get("side_label") or ""), float(r.get("line")), str(r.get("side"))
    # Kalshi's label says either "NOT <other> wins by over N" (our side is getting the points) or
    # "<our side> wins by over N" (our side is laying them). The sign of `line` must agree.
    if lab.startswith("NOT "):
        if ln <= 0:
            bad_sign.append((side, ln, lab))
        other = [t for t in ex.ncs_teams(r) if t != side]
        if other and other[0] not in lab:    # a "NOT" label must name the OTHER team
            bad_team.append((side, lab))
    elif lab:
        if ln >= 0:
            bad_sign.append((side, ln, lab))
        if side not in lab:                  # a laying label must name OUR team
            bad_team.append((side, lab))

ok(f"line sign agrees with the label on every readable row ({built} rows)", not bad_sign, str(bad_sign[:3]))
ok("the label names the right team on every readable row", not bad_team, str(bad_team[:3]))
ok("bet string is built for the great majority of Kalshi rows", built >= 0.9 * len(sp), f"{built}/{len(sp)}")

# --- the lane ships OFF ------------------------------------------------------------------------
ok("EXEC_NCS_LIVE defaults off", ex.NCS_LIVE is False)
ok("unit is $200, never Lane 1's $300", ex.NCS_UNIT == 200.0)
ok("daily risk starts at half R1's", ex.NCS_DAILY_RISK == 1000.0 and ex.R1_DAILY_RISK == 2000.0)
ok("$200 to win at -110 risks $220", ex.live_stake(-110, ex.NCS_UNIT) == (220.0, 200.0))
ok("risks $200 at plus money", ex.live_stake(140, ex.NCS_UNIT) == (200.0, 280.0))

# --- the gate fails closed ---------------------------------------------------------------------
saved = dict(ex.NCS)
try:
    ex.NCS.update({"known": False, "risk": 0.0, "keys": set()})
    ok("gate refuses when exposure is unknown", ex.ncs_gate(220.0)[0] is False)
    ex.NCS.update({"known": True, "risk": 0.0, "keys": set()})
    ok("gate allows a first order", ex.ncs_gate(220.0)[0] is True)
    ok("gate refuses zero risk", ex.ncs_gate(0)[0] is False)
    ok("gate refuses unreadable risk", ex.ncs_gate("x")[0] is False)
    ex.NCS.update({"known": True, "risk": 900.0, "keys": set()})
    ok("gate refuses an order that would breach the daily risk", ex.ncs_gate(220.0)[0] is False)
    ex.NCS.update({"known": True, "risk": 0.0, "keys": {f"k{i}" for i in range(ex.NCS_MAX_PLAYS)}})
    ok("gate refuses past the play cap", ex.ncs_gate(220.0, "new")[0] is False)
    ok("a retry of a key already counted is not an extra play", ex.ncs_gate(220.0, "k0")[0] is True)
finally:
    ex.NCS.clear()
    ex.NCS.update(saved)

# --- wiring: every integration point the lane needs --------------------------------------------
ok("play_key prefix is registered", "ncs|" in ex.LANE_PREFIXES)
ok("lane_strip removes the prefix", ex.lane_strip("ncs|NCAAB|x") == "NCAAB|x")
ok("unit_for maps the lane", ex.unit_for("ncs") == ex.NCS_UNIT)
ok("unit_for is unchanged for the other lanes",
   ex.unit_for("r1") == ex.R1_UNIT and ex.unit_for("board") == ex.BOARD_UNIT and ex.unit_for(None) == ex.LIVE_UNIT)
ok("lane has a name for notifications", ex.LANE_NAME.get("ncs") == "NCS")

src = open(os.path.join(HERE, "executor.py"), encoding="utf-8").read()
for needle, what in (('ncsplays = ncs_plays(now)', "selection runs"),
                     ('+ ncsplays +', "candidates include the lane"),
                     ('elif p.get("source") == "ncs":', "dispatch branch exists"),
                     ('"[NCS] "', "notifications carry the lane tag"),
                     ('NCS["known"] = True', "exposure is marked known"),
                     ('NCS["keys"].add(row["key"])', "ledger rows feed the day's exposure"),
                     ('("ncs", "NCS (NCAAB spreads)"', "lane report lists it"),
                     ('("board", "r1", "ncs")', "line floor and unit lookup include it")):
    ok(f"wired: {what}", needle in src)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
