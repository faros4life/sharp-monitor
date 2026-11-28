#!/usr/bin/env python3
"""12K lane: NFL 12K all-three-books ML trigger, spread play, 12-24h first print. Offline.

Peter's decision, 28 Nov 2026, and his instruction when commissioning it: "build it but don't turn
it on." So the first thing asserted is that it ships OFF, and the second is that the one input that
is NOT settled - what "12K" filters on - fails CLOSED rather than guessing a cohort.

The lane RESTS at the alert number. It was built take-only from the spec's "one attempt per book";
Peter then asked for both lanes "running the right way with resting bids at the alert number"
(28 Nov), so it is registered in rest_bid's _REST_LANE_GATES with its own gate. Registration there
is asserted below, because a lane absent from that table is silently refused - which was the
deliberate behaviour before and would now be a lane that never rests while looking as if it does."""
import inspect
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
ok("RESTS: registered in _REST_LANE_GATES, with its OWN gate",
   '"12k": k12_gate' in _rg, _rg)
ok("...so an unproven lane is still refused there (the fail-closed default is intact)",
   "resting bid whose lane could not be proven" in SRC)
# The price a resting bid goes out at IS the alert's own after-fee number, with no tolerance added -
# which is this lane's price gate. Asserted at the source of the price, not from a comment.
_rb = inspect.getsource(ex.rest_bid)
ok("a resting bid is priced at the alert's after-fee number",
   'af = e.get("price_after_fee")' in _rb and "p_star = american_to_prob(int(af))" in _rb)
ok("...with no price tolerance applied on the resting path", "TOL" not in _rb)
ok("...on Novig and Kalshi only, Polymarket US blocked",
   'if b == "kalshi"' in _rb and 'elif b == "novig"' in _rb and "resting BLOCKED" in _rb)
ok("...with T-30 expiry, the shared ledger and the separate |rest claim",
   ex.REST_BEFORE_MIN == 30 and '_unit_ledger_guard(r, "rest_bid"' in _rb
   and '_pkey + "|rest"' in _rb)

# --- 8. THE PRODUCTION PATH (added after a review found the lane had none) ---------------------
# k12_select existed, was tested 66 ways, and was called by NOTHING but tests: no producer, so the
# lane selected nothing in production and flipping EXEC_12K_LIVE would have placed nothing. The
# "46 plays" replay called k12_select directly - it proved the function, not the lane.
ok("a producer exists", hasattr(ex, "k12_plays"))
ok("...and the pipeline calls it", "k12plays = k12_plays(now)" in SRC
   and "+ k12plays +" in SRC)
ok("...behind its own try/except, like every other lane", '12k unavailable' in SRC)
_pick = None
_el = sorted([x for x in FEED if ex.iso_t(x.get("alerted_utc"))], key=lambda x: ex.iso_t(x["alerted_utc"]))
_tk = []
for _x in _el:
    if not ex.k12_qualifies(_x) or any(ex.k12_same_game(_x, _t) for _t in _tk):
        continue
    _tk.append(_x)
    _a, _s2 = ex.iso_t(_x["alerted_utc"]), ex.iso_t(_x.get("start_utc"))
    if _a and _s2 and ex.K12_LEAD_LO <= (_s2 - _a).total_seconds() / 60.0 < ex.K12_LEAD_HI:
        _pick = _x
        break
_prod = ex.k12_plays(ex.iso_t(_pick["alerted_utc"]) + timedelta(seconds=1)) if _pick else []
ok("the producer yields PLAY DICTS, not feed rows", _prod and all(
   {"source", "play_key", "bet", "k12_entry", "rules", "start_utc"} <= set(x) for x in _prod), len(_prod))
ok("every play is tagged source '12k'", all(x["source"] == "12k" for x in _prod))
ok("every play_key carries the 12k| prefix", all(x["play_key"].startswith("12k|") for x in _prod))
ok("every play carries a k12_entry price - without it rest_bid refuses 'price unknown'",
   all(x["k12_entry"]["price_after_fee"] is not None for x in _prod))
ok("...and the entry's price is the SELECTED row's, so a mirrored play is priced at its complement",
   all(x["k12_entry"]["price_after_fee"] == x["k12_entry"]["alert_price_raw"] for x in _prod))
ok("the spread source is recorded on the entry (it read a pre-rename key and was silently None)",
   {x["k12_entry"]["k12_spread_source"] for x in _prod} <= {"direct", "mirrored"}
   and None not in {x["k12_entry"]["k12_spread_source"] for x in _prod},
   sorted({str(x["k12_entry"]["k12_spread_source"]) for x in _prod}))
ok("the bet string names the side and its signed line",
   all(" " in x["bet"] and "(" in x["bet"] for x in _prod))
# the duplicate guards must SEE this lane's prefix, or both are blind - "two vigs for a guaranteed
# loss" in lane_strip's own words. Proved blind by a review before LANE_PREFIXES carried "12k|".
ok("12k| is registered in LANE_PREFIXES", "12k|" in ex.LANE_PREFIXES)
_k = "NFL|A @ B|spread|A"
ok("same_bet sees a 12k| key (duplicate guard)", ex.same_bet("12k|" + _k, _k) is True)
ok("opp_bet sees a 12k| key (first-side guard)",
   ex.opp_bet("12k|" + _k, "NFL|A @ B|spread|B") is True)
ok("lane_strip strips it", ex.lane_strip("12k|" + _k) == _k)

# --- 9. ELIGIBILITY FILTERS, which nothing pinned ---------------------------------------------
# A review mutated away the non-bettable-book filter and the whole suite stayed green; Polymarket
# Global is not bettable from the US and clv_std refuses to price it at all.
_base = _row(_G, "Detroit Lions", 1000, teams=_T)
_bspr = _row(_G, "Detroit Lions", 1000, teams=_T, market="spread")
for _fld, _val, _why in (("book", "polymarket", "a non-bettable book"),
                         ("artifact", True, "an artifact row"),
                         ("close_suspect", True, "a close-suspect row")):
    _p, _ = ex.k12_select([dict(_base, **{_fld: _val}), dict(_bspr, **{_fld: _val})], _t0)
    ok(f"{_why} is not selected", _p == [], _p)
ok("a game that has already started is not selected",
   ex.k12_select([_base, _bspr], datetime(2026, 11, 29, 0, 0, tzinfo=timezone.utc))[0] == [])
ok("a side matching NEITHER team yields no bet string, never a guess",
   ex.k12_bet(dict(_bspr, side="Nobody FC")) is None)

# --- 10. SAME-CITY SIDES MUST NOT CROSS -------------------------------------------------------
# A bare token intersection matched "New York Giants" to "New York Jets" on {new, york}. In a
# Giants-vs-Jets game that picked the JETS spread row for a GIANTS trigger - a live bet on the
# opposite outcome. Found by driving the helper, not by reading it.
for _a, _b in (("New York Giants", "New York Jets"), ("Los Angeles Chargers", "Los Angeles Rams"),
               ("Los Angeles C", "Los Angeles R"), ("New York G", "New York J")):
    ok(f"{_a!r} does not match {_b!r}", ex.k12_same_side(_a, _b, others=[_a]) is False)
    ok(f"...and {_a!r} still matches itself", ex.k12_same_side(_a, _a, others=[_b]) is True)
ok("dialects still match (Detroit Lions == Detroit)",
   ex.k12_same_side("Detroit Lions", "Detroit", others=["Chicago Bears"]) is True)
ok("an ambiguous tie fails CLOSED rather than guessing",
   ex.k12_same_side("New York", "New York Jets", others=["New York Giants"]) is False)
# end to end: a Giants trigger in a Giants/Jets game must never be priced from the Jets row
_GJ, _GJT = "New York Giants @ New York Jets", ["New York Giants", "New York Jets"]
_trigG = _row(_GJ, "New York Giants", 1000, teams=_GJT)
_sprJ = _row(_GJ, "New York Jets", 1000, teams=_GJT, market="spread", line=3.5,
             label="New York Jets +3.5")
_p, _ = ex.k12_select([_trigG, _sprJ], _t0)
ok("a Giants trigger is NOT priced from the Jets spread row",
   all("jets" not in str(x.get("side")).lower() for x in _p), [x.get("side") for x in _p])

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
