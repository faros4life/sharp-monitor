#!/usr/bin/env python3
"""ALL-3 lane: NFL 12K all-three-books ML trigger, spread play, 12-24h first print. Offline.

Peter's decision, 28 Nov 2026, and his instruction when commissioning it: "build it but don't turn
it on." So the first thing asserted is that it ships OFF, and the second is that the one input that
is NOT settled - what "12K" filters on - fails CLOSED rather than guessing a cohort.

The lane is TAKE-ONLY by spec ("one attempt per book", nothing about resting), which is enforced by
ABSENCE from rest_bid's _REST_LANE_GATES. A lane absent from that table is refused there. That is
the behaviour wanted, but an absence is exactly what CLAUDE.md warns silently becomes a no-op, so it
is asserted here rather than assumed."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import executor as ex

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "executor.py"), encoding="utf-8").read()
FEED = [x for x in json.load(open(os.path.join(HERE, "liquidity", "alerts.json")))["alerts"]
        if isinstance(x, dict)]
NOW = datetime.now(timezone.utc)

# --- 1. ships OFF, and two independent stops -------------------------------------------------
ok("ships OFF with the variable unset",
   ex.ALL3_LIVE is False or os.environ.get("EXEC_ALL3_LIVE", "").lower() == "on")
ok("the code default is off, whatever the variable says",
   '(os.environ.get("EXEC_ALL3_LIVE") or "off")' in SRC)
ok("OFF puts a reason in `why` before any gate is asked",
   'why = [] if ALL3_LIVE else ["ALL-3 lane not switched on (EXEC_ALL3_LIVE)"]' in SRC)

# --- 2. the unit is Peter's: to win $200, $200 risked at plus --------------------------------
ok("the lane unit is $200", ex.ALL3_UNIT == 200.0 and ex.unit_for("all3") == 200.0)
_r, _w = ex.live_stake(-130, ex.ALL3_UNIT)
ok("at minus money it sizes to WIN $200", round(_w, 2) == 200.0 and round(_r, 2) == 260.0, (_r, _w))
_r, _w = ex.live_stake(140, ex.ALL3_UNIT)
ok("at plus money it RISKS $200", round(_r, 2) == 200.0, (_r, _w))
ok("the branch sizes from ALL3_UNIT, never another lane's",
   "live_stake(lc[\"shown\"], ALL3_UNIT)" in SRC)

# --- 3. the 12K trigger: all three books, on the ML print -------------------------------------
ok("the trigger books are Kalshi, Novig and ProphetX",
   ex.ALL3_TRIGGER_BOOKS == ("kalshi", "novig", "prophetx"))
_ml = {"league": "NFL", "market": "moneyline", "price_american": -110,
       "depth_by_book": {b: {"new_this_side": 20000} for b in ex.ALL3_TRIGGER_BOOKS}}
ok("$12k+ on all three books on the ML print qualifies", ex.all3_trigger_ok(_ml) is True)
for _miss in ex.ALL3_TRIGGER_BOOKS:
    _d = {b: {"new_this_side": 20000} for b in ex.ALL3_TRIGGER_BOOKS}
    _d[_miss] = {"this_side": 999999}        # depth only, no NEW money - the real feed shape
    ok(f"...and it does NOT qualify when {_miss} did not print",
       ex.all3_trigger_ok(dict(_ml, depth_by_book=_d)) is False)
_d = {b: {"new_this_side": 20000} for b in ex.ALL3_TRIGGER_BOOKS}
_d["novig"] = {"new_this_side": 11999}
ok("...nor when one book is a dollar short of 12K",
   ex.all3_trigger_ok(dict(_ml, depth_by_book=_d)) is False)
ok("the trigger is read on the MONEYLINE, never the spread",
   ex.all3_trigger_ok(dict(_ml, market="spread")) is False)
ok("a non-NFL row never qualifies",
   ex.all3_qualifies(dict(_ml, league="NCAAF")) is False and ex.all3_qualifies(_ml) is True)
ok("the league is read from `league`, not `sport` (every feed row has sport None)",
   all(x.get("sport") is None for x in FEED[:200]) and 'x.get("league")' in SRC)

# --- 4. FAIL CLOSED on today's feed: the conjunction is not satisfiable row-by-row ------------
# This is the honest state of the lane: Peter's base 12K definition is registered with him, not in
# this repo, and one feed row can only ever prove ONE book's print. So the lane selects nothing.
_plays, _skipped = ex.all3_select(FEED, NOW)
ok("on the real feed the lane selects NOTHING, and that is fail-closed not broken",
   _plays == [] and _skipped > 0, (len(_plays), _skipped))
_ml_rows = [x for x in FEED if str(x.get("league") or "").upper() == "NFL"
            and x.get("market") == "moneyline"]
ok("...because no NFL ML row carries new money for more than one book",
   _ml_rows and all(sum(1 for b in ex.ALL3_TRIGGER_BOOKS
                        if ex.all3_book_new_money(x, b) is not None) <= 1 for x in _ml_rows),
   len(_ml_rows))
ok("the reason is recorded in the code, not left for someone to rediscover",
   "cannot be evaluated from these rows" in SRC and "Nov 25-26" in SRC)

# --- 5. first-side-only, and the 12-24h window on the FIRST print -----------------------------
def _row(game, side, lead_min, teams=None, market="moneyline", money=20000, alerted="2026-11-28T00:00:00Z"):
    st = (datetime.fromisoformat(alerted.replace("Z", "+00:00")) + timedelta(minutes=lead_min))
    return {"league": "NFL", "market": market, "game": game, "side": side,
            "teams": teams or [side, "Other"], "line": -2.5, "price_american": -110,
            "alerted_utc": alerted, "start_utc": st.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "book": "prophetx", "new_money": money,
            "depth_by_book": {b: {"new_this_side": money} for b in ex.ALL3_TRIGGER_BOOKS}}


_t0 = datetime(2026, 11, 27, 23, 0, tzinfo=timezone.utc)
_g = "Chiefs @ Bills"
_trig = _row(_g, "Bills", 1000, teams=["Bills", "Chiefs"])
_spr = _row(_g, "Bills", 1000, teams=["Bills", "Chiefs"], market="spread")
_plays, _ = ex.all3_select([_trig, _spr], _t0)
ok("a qualifying trigger with a 12-24h lead selects ONE play", len(_plays) == 1, len(_plays))
ok("...and the play is the SPREAD, not the moneyline the trigger was read on",
   _plays and _plays[0]["market"] == "spread", _plays and _plays[0]["market"])
ok("...carrying the trigger's lead and its per-book money, for the record",
   _plays and _plays[0]["all3_lead_min"] == 1000.0
   and set(_plays[0]["all3_trigger_money"]) == set(ex.ALL3_TRIGGER_BOOKS))
for _lead, _want in ((719, 0), (720, 1), (1440, 1), (1441, 0), (300, 0), (2000, 0)):
    _p, _ = ex.all3_select([_row(_g, "Bills", _lead, teams=["Bills", "Chiefs"]),
                            _row(_g, "Bills", _lead, teams=["Bills", "Chiefs"], market="spread")], _t0)
    ok(f"a {_lead}-minute lead selects {_want}", len(_p) == _want, len(_p))
# first-side-only is per GAME: once a game's first qualifying print is taken, the other side cannot.
_early = _row(_g, "Bills", 1000, teams=["Bills", "Chiefs"], alerted="2026-11-28T00:00:00Z")
_late = _row(_g, "Chiefs", 1000, teams=["Chiefs", "Bills"], alerted="2026-11-28T01:00:00Z")
_p, _ = ex.all3_select([_early, _late, _spr], _t0)
ok("first-side-only: one play per GAME, the earliest print's side",
   len(_p) == 1 and str(_p[0]["side"]).lower() == "bills", [(x["side"]) for x in _p])
# a later print on the same side is the same opportunity moving, not a second one
_p, _ = ex.all3_select([_early, _row(_g, "Bills", 1000, teams=["Bills", "Chiefs"],
                                     alerted="2026-11-28T02:00:00Z"), _spr], _t0)
ok("a later print on the same side is not a second play", len(_p) == 1, len(_p))
# a trigger with no spread entry is SKIPPED, never bet as a moneyline
_p, _sk = ex.all3_select([_trig], _t0)
ok("a trigger with no spread entry is skipped, never bet on the ML instead", _p == [] and _sk >= 1)
# mirrored: only the other team's spread is listed
_mir = _row(_g, "Chiefs", 1000, teams=["Chiefs", "Bills"], market="spread")
_p, _ = ex.all3_select([_trig, _mir], _t0)
ok("mirrored: the other team's spread is accepted when the direct side is not listed",
   len(_p) == 1 and str(_p[0]["side"]).lower() == "chiefs", _p and _p[0]["side"])

# --- 6. the lane's own cap, play maximum and fail-closed exposure -----------------------------
_s = dict(ex.ALL3)
try:
    ex.ALL3.clear(); ex.ALL3.update({"known": False, "keys": set(), "risk": 0.0})
    ok("unknown exposure refuses (fail closed)", ex.all3_gate(200.0, "k")[0] is False)
    ex.ALL3.update({"known": True})
    ok("a clean lane admits one play", ex.all3_gate(200.0, "k1")[0] is True)
    ex.ALL3.update({"risk": ex.ALL3_DAILY_RISK})
    _o, _w = ex.all3_gate(200.0, "k2")
    ok("the daily risk limit refuses", _o is False and "daily risk limit" in _w, _w)
    ex.ALL3.update({"risk": 0.0, "keys": {f"k{i}" for i in range(ex.ALL3_MAX_PLAYS)}})
    _o, _w = ex.all3_gate(200.0, "new")
    ok("the play maximum refuses", _o is False and "play cap" in _w, _w)
    ex.ALL3.update({"risk": 0.0, "keys": set()})
    ok("zero risk refuses", ex.all3_gate(0.0, "k")[0] is False)
    ok("unreadable risk refuses", ex.all3_gate("x", "k")[0] is False)
    # In-run accumulation: lane_consume must CHARGE this lane, or two plays in one pass are both
    # measured on the run-start figure. Driven through lane_consume itself, not asserted from source.
    ex.ALL3.update({"risk": 0.0, "keys": set()})
    _p = {"source": "all3", "play_key": "all3|NFL|A @ B|spread|A", "game": "A @ B",
          "sport": "NFL", "bet": "A -2.5 (-110)"}
    _charged = ex.lane_consume(_p, {"live": {"lane": "all3",
                                             "order": {"status": "placed", "fills_read": True,
                                                       "filled_stake": 200.0,
                                                       "asked_stake": 200.0}}})
    ok("lane_consume charges this lane in-run", _charged == 200.0 and ex.ALL3["risk"] == 200.0,
       (_charged, ex.ALL3["risk"]))
    ok("...and consumes exactly one play slot", len(ex.ALL3["keys"]) == 1, ex.ALL3["keys"])
    ok("...so the gate now measures against it",
       "200.00 already at risk" in ex.all3_gate(ex.ALL3_DAILY_RISK, "other")[1],
       ex.all3_gate(ex.ALL3_DAILY_RISK, "other")[1])
finally:
    ex.ALL3.clear(); ex.ALL3.update(_s)

# --- 7. registered everywhere a lane must be, and TAKE-ONLY -----------------------------------
import registry as rg
ok("registry.LANE_PREFIX knows the lane (or row_lane returns None and every cap silently skips it)",
   rg.row_lane({"key": "all3|NFL|A @ B|spread|A", "source": "all3"}) == "all3")
ok("LANE_STATE maps it, so lane_consume charges it", ex.LANE_STATE.get("all3") == "ALL3")
ok("LANE_NAME maps it, so reports and notifications name it", ex.LANE_NAME.get("all3") == "ALL-3")
ok("unit_for knows it", ex.unit_for("all3") == 200.0)
ok("the exposure snapshot reads it", 'row.get("source") == "all3"' in SRC and 'ALL3["known"] = True' in SRC)
ok("the snapshot stores both key spellings (item 3)", 'ALL3["keys"].add(lane_strip(row["key"]))' in SRC)
ok("there is exactly ONE dispatch branch for it", SRC.count('elif p.get("source") == "all3":') == 1)
_rg = SRC.split("_REST_LANE_GATES = ")[1].split("}")[0]
ok("TAKE-ONLY: absent from _REST_LANE_GATES, so a resting bid is REFUSED there",
   '"all3"' not in _rg, _rg)
ok("...and that absence is a refusal, not a silent skip",
   "resting bid whose lane could not be proven" in SRC)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
