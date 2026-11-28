#!/usr/bin/env python3
"""12K lane: NFL 12K all-three-books ML trigger, spread play, 12-24h first print. Offline.

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
   ex.K12_LIVE is False or os.environ.get("EXEC_12K_LIVE", "").lower() == "on")
ok("the code default is off, whatever the variable says",
   '(os.environ.get("EXEC_12K_LIVE") or "off")' in SRC)
ok("OFF puts a reason in `why` before any gate is asked",
   'why = [] if K12_LIVE else ["12K lane not switched on (EXEC_12K_LIVE)"]' in SRC)

# --- 2. the unit is Peter's: to win $200, $200 risked at plus --------------------------------
ok("the lane unit is $200", ex.K12_UNIT == 200.0 and ex.unit_for("12k") == 200.0)
_r, _w = ex.live_stake(-130, ex.K12_UNIT)
ok("at minus money it sizes to WIN $200", round(_w, 2) == 200.0 and round(_r, 2) == 260.0, (_r, _w))
_r, _w = ex.live_stake(140, ex.K12_UNIT)
ok("at plus money it RISKS $200", round(_r, 2) == 200.0, (_r, _w))
ok("the branch sizes from K12_UNIT, never another lane's",
   "live_stake(lc[\"shown\"], K12_UNIT)" in SRC)

# --- 3. the 12K trigger: per-book THIS-SIDE depth, all three books, on the ML entry ------------
# Peter's registered definition, relayed 28 Nov. It is NOT the row's new_money and NOT a cross-row
# join: it reads depth_by_book's per-book `this_side` on ONE moneyline entry. My first build read
# `new_this_side` and concluded the cohort was empty; the field was the bug, not the feed.
ok("the trigger books are Kalshi, Novig and ProphetX",
   ex.K12_TRIGGER_BOOKS == ("kalshi", "novig", "prophetx"))
_ml = {"league": "NFL", "market": "moneyline", "price_american": -110,
       "depth_by_book": {b: {"this_side": 20000} for b in ex.K12_TRIGGER_BOOKS}}
ok("$12k+ this-side depth on all three books qualifies", ex.k12_trigger_ok(_ml) is True)
for _b in ex.K12_TRIGGER_BOOKS:
    _d = {k: {"this_side": 20000} for k in ex.K12_TRIGGER_BOOKS}
    _d.pop(_b)
    ok(f"a book ABSENT from depth_by_book counts as $0 and fails ({_b})",
       ex.k12_trigger_ok(dict(_ml, depth_by_book=_d)) is False)
    ok(f"...and ${ex.K12_MIN_MONEY:,.0f} minus a dollar fails too ({_b})",
       ex.k12_trigger_ok(dict(_ml, depth_by_book={**_d, _b: {"this_side": ex.K12_MIN_MONEY - 1}})) is False)
ok("book names are matched case-insensitively",
   ex.k12_trigger_ok(dict(_ml, depth_by_book={"Kalshi": {"this_side": 20000},
                                               "NOVIG": {"this_side": 20000},
                                               "ProphetX": {"this_side": 20000}})) is True)
ok("new_money is NOT the trigger - a huge new_money with thin depth fails",
   ex.k12_trigger_ok(dict(_ml, new_money=5_000_000,
                           depth_by_book={b: {"this_side": 10} for b in ex.K12_TRIGGER_BOOKS})) is False)
ok("the trigger is read on the MONEYLINE, never the spread",
   ex.k12_trigger_ok(dict(_ml, market="spread")) is False)
ok("a non-NFL entry never qualifies",
   ex.k12_qualifies(dict(_ml, league="NCAAF")) is False and ex.k12_qualifies(_ml) is True)
ok("the league is read from `league`, not `sport` (every feed row has sport None)",
   all(x.get("sport") is None for x in FEED[:200]) and 'x.get("league")' in SRC)

# Peter's worked example, which is the acceptance case: Detroit, Kalshi $3,774,670 / Novig $61,428 /
# ProphetX $39,131 - all three over $12k. Kalshi's is full-book depth; his instruction was explicit
# that this is the rule as registered and backtested, so it is asserted, not re-derived.
_det = {"league": "NFL", "market": "moneyline", "price_american": -110,
        "depth_by_book": {"kalshi": {"this_side": 3774670}, "novig": {"this_side": 61428},
                          "prophetx": {"this_side": 39131}}}
ok("ACCEPTANCE: Peter's Detroit example qualifies", ex.k12_trigger_ok(_det) is True)
ok("...and it is present in the real feed with those exact depths",
   any(ex.k12_book_depth(x, "kalshi") == 3774670 and ex.k12_book_depth(x, "novig") == 61428
       and ex.k12_book_depth(x, "prophetx") == 39131 for x in FEED))

# --- 4. the lane fires on the real feed ------------------------------------------------------
# Replayed at one second after a qualifying in-window print, because the snapshot's games have
# started: with the real `now` they are correctly excluded, which is not the same as not working.
_elig = sorted([x for x in FEED if ex.iso_t(x.get("alerted_utc"))],
               key=lambda x: ex.iso_t(x["alerted_utc"]))
_taken, _pick = [], None
for _x in _elig:
    if not ex.k12_qualifies(_x) or any(ex.k12_same_game(_x, _t) for _t in _taken):
        continue
    _taken.append(_x)
    _at, _st = ex.iso_t(_x["alerted_utc"]), ex.iso_t(_x.get("start_utc"))
    if _at and _st and ex.K12_LEAD_LO <= (_st - _at).total_seconds() / 60.0 < ex.K12_LEAD_HI:
        _pick = _x
        break
ok("the real feed contains qualifying in-window triggers", _pick is not None)
_plays, _ = ex.k12_select(FEED, ex.iso_t(_pick["alerted_utc"]) + timedelta(seconds=1))
ok("...and the lane selects plays from them", len(_plays) > 0, len(_plays))
ok("every selected play is a SPREAD, never the moneyline the trigger was read on",
   all(x.get("market") == "spread" for x in _plays))
ok("every selected play carries its trigger's three-book depth, all over the floor",
   all(len(x["k12_trigger_depth"]) == 3
       and min(x["k12_trigger_depth"].values()) >= ex.K12_MIN_MONEY for x in _plays))
ok("every selected play's lead is inside 12h <= lead < 24h",
   all(ex.K12_LEAD_LO <= x["k12_lead_min"] < ex.K12_LEAD_HI for x in _plays))
ok("one play per matchup - no matchup selected twice",
   len(_plays) == len({ex.lm.game_key(x) + tuple(sorted(str(t) for t in (x.get("teams") or [])))
                       for x in _plays}), len(_plays))
ok("both the direct and the mirrored spread forms occur in the real feed",
   {x["k12_spread_source"] for x in _plays} == {"direct", "mirrored"},
   sorted({x["k12_spread_source"] for x in _plays}))

# --- 5. the window, first-print-only, dialects, and the mirrored price ------------------------
def _row(game, side, lead_min, teams=None, market="moneyline", alerted="2026-11-28T00:00:00Z",
         depth=20000, line=-2.5, label=None, best=0.5, league="NFL", date="2026-11-28"):
    st = datetime.fromisoformat(alerted.replace("Z", "+00:00")) + timedelta(minutes=lead_min)
    return {"league": league, "date": date, "market": market, "game": game, "side": side,
            "teams": teams or [side, "Other"], "line": line, "price_american": -110,
            "best_price": best, "side_label": label or f"{side} wins",
            "alerted_utc": alerted, "start_utc": st.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "book": "prophetx",
            "depth_by_book": {b: {"this_side": depth} for b in ex.K12_TRIGGER_BOOKS}}


_t0 = datetime(2026, 11, 27, 23, 0, tzinfo=timezone.utc)
_G, _T = "Chicago Bears vs Detroit Lions", ["Chicago Bears", "Detroit Lions"]
# the window: 12h inclusive, 24h EXCLUSIVE. Peter's relay said my old 1440-inclusive test "matched"
# the spec; it did not, and one minute is one play, so the boundary is pinned here both ways.
for _lead, _want in ((719, 0), (720, 1), (1439, 1), (1440, 0), (1441, 0), (300, 0)):
    _p, _ = ex.k12_select([_row(_G, "Detroit Lions", _lead, teams=_T),
                            _row(_G, "Detroit Lions", _lead, teams=_T, market="spread")], _t0)
    ok(f"a {_lead}-minute lead selects {_want}", len(_p) == _want, len(_p))
# first print only, and first side only - across book dialects
_early = _row(_G, "Detroit Lions", 1000, teams=_T, alerted="2026-11-28T00:00:00Z")
_dialect = _row("Chicago vs Detroit", "Detroit", 1000, teams=["Chicago", "Detroit"],
                alerted="2026-11-28T01:00:00Z")
_opp = _row(_G, "Chicago Bears", 1000, teams=_T, alerted="2026-11-28T02:00:00Z")
_spr = _row(_G, "Detroit Lions", 1000, teams=_T, market="spread")
_p, _ = ex.k12_select([_early, _dialect, _opp, _spr], _t0)
ok("one play per matchup across book dialects ('Chicago vs Detroit' == 'Chicago Bears vs Detroit Lions')",
   len(_p) == 1, len(_p))
ok("...and it is the FIRST print's side", _p and "detroit" in str(_p[0]["side"]).lower(), _p and _p[0]["side"])
# Order in the list is irrelevant - k12_select sorts by alerted_utc - so this case gives CHICAGO
# the earlier print and asserts Detroit's later one does not fire. My first version listed Chicago
# first but timestamped it later, and asserted Chicago: the code was right and the test was wrong.
_chi_first = _row(_G, "Chicago Bears", 1000, teams=_T, alerted="2026-11-27T23:30:00Z")
_det_later = _row(_G, "Detroit Lions", 1000, teams=_T, alerted="2026-11-28T01:00:00Z")
_p, _ = ex.k12_select([_det_later, _chi_first, _spr,
                        _row(_G, "Chicago Bears", 1000, teams=_T, market="spread")], _t0)
ok("first-side-only: the opposite side's later print does not fire",
   len(_p) == 1 and "chicago" in str(_p[0]["side"]).lower(), _p and _p[0]["side"])
# a matchup whose FIRST qualifying print is out of window does not become eligible later
_p, _ = ex.k12_select([_row(_G, "Detroit Lions", 200, teams=_T, alerted="2026-11-28T00:00:00Z"),
                        _row(_G, "Detroit Lions", 1000, teams=_T, alerted="2026-11-28T01:00:00Z"),
                        _spr], _t0)
ok("a matchup whose first qualifying print was out of window does not re-qualify later",
   len(_p) == 0, len(_p))
# a trigger with no spread entry is skipped, never bet as a moneyline
_p, _sk = ex.k12_select([_early], _t0)
ok("a trigger with no spread entry is skipped, never bet on the ML instead", _p == [] and _sk >= 1)
# the mirrored form: <team> -L at the COMPLEMENT price, not the other row as listed
ok("prob_to_american inverts american_to_prob", ex.prob_to_american(ex.american_to_prob(-120)) == -120
   and ex.prob_to_american(ex.american_to_prob(150)) == 150)
_mir = _row(_G, "Chicago Bears", 1000, teams=_T, market="spread", line=3.5, best=0.40,
            label="NOT Detroit Lions wins by over 3.5")
_p, _ = ex.k12_select([_early, _mir], _t0)
ok("mirrored: the play is OUR side at -L, not the other row's side",
   len(_p) == 1 and "detroit" in str(_p[0]["side"]).lower() and _p[0]["line"] == -3.5,
   _p and (_p[0]["side"], _p[0]["line"]))
ok("mirrored: priced at the complement (1 - 0.40 = 0.60 -> -150)",
   _p and _p[0]["price_american"] == ex.prob_to_american(0.60) == -150,
   _p and _p[0]["price_american"])
ok("mirrored: the source is recorded, so a fill can be audited back to the mirror",
   _p and _p[0]["k12_spread_source"] == "mirrored" and _p[0]["k12_mirrored_from"])

# --- 6. the lane's own cap, play maximum and fail-closed exposure -----------------------------
_s = dict(ex.K12)
try:
    ex.K12.clear(); ex.K12.update({"known": False, "keys": set(), "risk": 0.0})
    ok("unknown exposure refuses (fail closed)", ex.k12_gate(200.0, "k")[0] is False)
    ex.K12.update({"known": True})
    ok("a clean lane admits one play", ex.k12_gate(200.0, "k1")[0] is True)
    ex.K12.update({"risk": ex.K12_DAILY_RISK})
    _o, _w = ex.k12_gate(200.0, "k2")
    ok("the daily risk limit refuses", _o is False and "daily risk limit" in _w, _w)
    ex.K12.update({"risk": 0.0, "keys": {f"k{i}" for i in range(ex.K12_MAX_PLAYS)}})
    _o, _w = ex.k12_gate(200.0, "new")
    ok("the play maximum refuses", _o is False and "play cap" in _w, _w)
    ex.K12.update({"risk": 0.0, "keys": set()})
    ok("zero risk refuses", ex.k12_gate(0.0, "k")[0] is False)
    ok("unreadable risk refuses", ex.k12_gate("x", "k")[0] is False)
    # In-run accumulation: lane_consume must CHARGE this lane, or two plays in one pass are both
    # measured on the run-start figure. Driven through lane_consume itself, not asserted from source.
    ex.K12.update({"risk": 0.0, "keys": set()})
    _p = {"source": "12k", "play_key": "k12|NFL|A @ B|spread|A", "game": "A @ B",
          "sport": "NFL", "bet": "A -2.5 (-110)"}
    _charged = ex.lane_consume(_p, {"live": {"lane": "12k",
                                             "order": {"status": "placed", "fills_read": True,
                                                       "filled_stake": 200.0,
                                                       "asked_stake": 200.0}}})
    ok("lane_consume charges this lane in-run", _charged == 200.0 and ex.K12["risk"] == 200.0,
       (_charged, ex.K12["risk"]))
    ok("...and consumes exactly one play slot", len(ex.K12["keys"]) == 1, ex.K12["keys"])
    ok("...so the gate now measures against it",
       "200.00 already at risk" in ex.k12_gate(ex.K12_DAILY_RISK, "other")[1],
       ex.k12_gate(ex.K12_DAILY_RISK, "other")[1])
finally:
    ex.K12.clear(); ex.K12.update(_s)

# --- 7. registered everywhere a lane must be, and TAKE-ONLY -----------------------------------
import registry as rg
ok("registry.LANE_PREFIX knows the lane (or row_lane returns None and every cap silently skips it)",
   rg.row_lane({"key": "k12|NFL|A @ B|spread|A", "source": "12k"}) == "12k")
ok("LANE_STATE maps it, so lane_consume charges it", ex.LANE_STATE.get("12k") == "K12")
ok("LANE_NAME maps it, so reports and notifications name it", ex.LANE_NAME.get("12k") == "12K")
ok("unit_for knows it", ex.unit_for("12k") == 200.0)
ok("the exposure snapshot reads it", 'row.get("source") == "12k"' in SRC and 'K12["known"] = True' in SRC)
ok("the snapshot stores both key spellings (item 3)", 'K12["keys"].add(lane_strip(row["key"]))' in SRC)
ok("there is exactly ONE dispatch branch for it", SRC.count('elif p.get("source") == "12k":') == 1)
_rg = SRC.split("_REST_LANE_GATES = ")[1].split("}")[0]
ok("TAKE-ONLY: absent from _REST_LANE_GATES, so a resting bid is REFUSED there",
   '"12k"' not in _rg, _rg)
ok("...and that absence is a refusal, not a silent skip",
   "resting bid whose lane could not be proven" in SRC)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
