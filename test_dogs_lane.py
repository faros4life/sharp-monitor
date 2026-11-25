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
SELKEY = {}
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
        SELKEY[(ex.lane_strip(p["play_key"]), x["market"])] = x.get("result")
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
# x0 must be a row dogs_bet ACCEPTS. This block tests freshness and first-print, nothing else,
# but the feed it draws from is live production data that the bot rewrites continuously, so
# want[-1] is whichever alert happened to land last. About 4.4% of rows carry a side the code
# deliberately refuses - "Miami" against "Pittsburgh vs Miami (FL)", "MIZ (0)", "Bethune" for
# Bethune-Cookman, the pre-formatted Novig "M-OH +4.5 (-4.5)" shape - which section 4 above
# allows up to 6% of. Landing on one made "a fresh print fires" fail for a side-parsing reason,
# so the suite went red roughly one run in twenty with nothing wrong (Nov 24-25, 2026).
x0 = next((x for x in reversed(want) if ex.dogs_bet(x) is not None), None)
ok("the feed still carries a bettable row to test freshness with", x0 is not None)
t0 = ex.iso_t(x0["alerted_utc"])
later = dict(x0, alerted_utc=(t0 + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), new_money=30000)
bad_first = dict(x0, new_money=90000)
p_, _ = ex.dogs_select([bad_first, later], t0 + timedelta(minutes=6))
ok("a later print never qualifies when the FIRST print did not", p_ == [])
p_, _ = ex.dogs_select([x0], t0 + timedelta(minutes=ex.DOGS_MAX_AGE_MIN + 1))
ok("a stale print does not fire (no backlog when the switch is first turned on)", p_ == [])
p_, _ = ex.dogs_select([x0], t0 + timedelta(minutes=2))
ok("a fresh print fires", len(p_) == 1)
# ...and not just for whichever row landed last. Sampling one row out of a live feed is what made
# this block flaky; asserting the PROPERTY over every bettable row is both deterministic and
# strictly stronger, and it costs two dogs_select calls per row.
_bettable = [x for x in want if ex.dogs_bet(x) is not None]
_bad = [x.get("game") for x in _bettable
        if len(ex.dogs_select([x], ex.iso_t(x["alerted_utc"]) + timedelta(minutes=2))[0]) != 1
        or ex.dogs_select([x], ex.iso_t(x["alerted_utc"]) + timedelta(minutes=ex.DOGS_MAX_AGE_MIN + 1))[0] != []]
ok("EVERY bettable row fires fresh and not stale, whatever order the feed is in",
   not _bad, f"{len(_bad)} of {len(_bettable)}: {_bad[:3]}")
ok("the refused rows stay inside the 6% the selection allows",
   len(want) - len(_bettable) <= 0.06 * len(want), f"{len(want) - len(_bettable)} of {len(want)}")
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
ex.DOGS_KILL["state"] = {"blocked": False, "why": "kill bar ok (test)"}   # section 8 tests the bar itself
_ulm = ex._unit_ledger_mode
ex._unit_ledger_mode = lambda: "on"
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
    ex.DOGS.update(risk=0.0, keys=set())
    for _m in ("off", "record"):
        ex._unit_ledger_mode = lambda _m=_m: _m
        ok(f"shared unit ledger '{_m}' (not enforced): a live DOGS order is refused", ex.dogs_gate(100, "z")[0] is False)
    ex._unit_ledger_mode = lambda: "on"
    ok("shared unit ledger enforced: the gate can pass", ex.dogs_gate(100, "z")[0] is True)
finally:
    ex._unit_ledger_mode = _ulm
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

# --- 8. the kill bar is CODE, and fails closed on grading it cannot trust (Peter, Nov 23) ---------
from datetime import datetime, timezone
NOW = datetime(2026, 12, 20, tzinfo=timezone.utc)
OLD, RECENT = "2026-12-10T00:00:00Z", "2026-12-19T12:00:00Z"


def _o(i, am=100, fs=100.0, start=OLD, live=True, status="placed", oid=None):
    return {"key": f"K{i}", "source": "dogs", "live": live, "start_utc": start, "live_px_price_after_fee": am, "alert_line": None,
            "live_order": {"status": status, "filled_stake": fs, "order_id": oid or f"o{i}", "book": "kalshi"}}


def _ev(orders, res, fills=(), seen=NOW):
    return ex.dogs_kill_eval(orders, set(fills), {(k, "moneyline"): v for k, v in res.items()}, NOW, seen)


ok("bar constants are the ruling", (ex.DOGS_KILL_N, ex.DOGS_KILL_BAR) == (30, -0.10))
ok("units: +150 win, loss, push", (ex.dogs_units(150, "W"), ex.dogs_units(150, "L"), ex.dogs_units(150, "P")) == (1.5, -1.0, 0.0))
ok("no fills yet: not blocked", _ev([], {})["blocked"] is False)
o30 = [_o(i) for i in range(30)]
r_bad = {f"K{i}": ("W" if i < 13 else "L") for i in range(30)}      # 13-17 at +100 = -4u = -0.133/play
r_edge = {f"K{i}": ("W" if i < 14 else "L") for i in range(30)}     # 14-16 = -2u = -0.067/play
k = _ev(o30, r_bad)
ok("30 verified fills at -0.133u/play: lane stopped", k["blocked"] and k["n"] == 30 and "KILL BAR HIT" in k["why"], k)
ok("30 fills at -0.067u/play: runs", _ev(o30, r_edge)["blocked"] is False)
ok("29 fills, same losing rate: bar not reached yet", _ev(o30[:29], r_bad)["blocked"] is False)
o_exact = [_o(i, am=100) for i in range(30)]
r_m3 = {f"K{i}": ("L" if i < 3 else "P") for i in range(30)}       # -3u / 30 = exactly -0.10
ok("exactly -0.10u/play at 30: stopped (bar is inclusive)", _ev(o_exact, r_m3)["blocked"] is True)
ok("a fill never read back, game 10 days old: fail closed",
   _ev([_o(1, fs=None)], {"K1": "W"})["blocked"] is True)
ok("the same unread fill is verified by a FILLED fill record", _ev([_o(1, fs=None)], {"K1": "W"}, fills={"o1"})["n"] == 1)
ok("an unread fill on a game not yet 72h old: waits, not counted", (lambda x: (x["blocked"], x["n"], x["unverified"]))(
    _ev([_o(1, fs=None, start=RECENT)], {})) == (False, 0, 1))
ok("verified fill ungraded 10 days after the start: fail closed", _ev([_o(1)], {})["blocked"] is True)
ok("read back with zero filled: not a fill at all", (lambda x: (x["blocked"], x["n"]))(_ev([_o(1, fs=0.0)], {})) == (False, 0))
ok("dry-run rows (live False) never count", _ev([_o(i, live=False) for i in range(40)], r_bad)["n"] == 0)
ok("verified fill with no price: fail closed", _ev([_o(1, am=None)], {"K1": "W"})["blocked"] is True)
ok("ledger not refreshed for 3 days: fail closed", _ev([], {}, seen=NOW - timedelta(hours=72))["blocked"] is True)
import reporting_ledger as _rl
_ll, _kg = _rl.load_ledger, dict(ex.DOGS)
try:
    def _boom(*a, **k):
        raise RuntimeError("cannot decrypt")
    _rl.load_ledger = _boom
    ex.DOGS_KILL["state"] = None
    st = ex.dogs_kill_state(NOW)
    ok("ledger unreadable: kill state is BLOCKED", st["blocked"] is True and "unreadable" in st["why"], st)
    ex.DOGS.update(known=True, risk=0.0, keys=set())
    _g = ex.dogs_gate(100, "x")
    ok("...and dogs_gate refuses the order on it, naming the kill bar", _g[0] is False and "kill bar" in _g[1], _g[1])
    _rl.load_ledger = lambda *a, **k: {"events": [], "head": {}}
    ex.DOGS_KILL["state"] = None
    ok("ledger empty or missing: BLOCKED, never 'no fills so fine'", ex.dogs_kill_state(NOW)["blocked"] is True)
finally:
    _rl.load_ledger = _ll
    ex.DOGS_KILL["state"] = None
    ex.DOGS.clear(); ex.DOGS.update(_kg)
ok("dogs_gate asks the kill bar before anything else", SRC.split("def dogs_gate(")[1].split("if not DOGS")[0].count("dogs_kill_state()") == 1)
_fr = ex.dogs_feed_results()
_g = {k: v for k, v in SELKEY.items() if v in ("W", "L", "P")}
ok("every graded play the lane selects is graded under the SAME key and market by the kill bar",
   len(_g) >= 120 and all(_fr.get(k) == v for k, v in _g.items()), (len(_g), sum(_fr.get(k) != v for k, v in _g.items())))
ok("a spread loss is never read as the moneyline's result on the same team",
   ex.dogs_kill_eval([dict(_o(1), alert_line=3.5)], set(), {("K1", "moneyline"): "W"}, NOW, NOW)["n"] == 0)

# --- 9. alert line and alert price or better: no tolerance, no other line, trigger then Novig ------
EV = SRC.split("def evaluate(")[1].split("\ndef fmt_line(")[0]
RV = SRC.split("def revalidate(")[1].split("\ndef px_limit(")[0]
ok("evaluate: DOGS tolerance is zero on every book", "strict = dogs_strict(p)" in EV and "if strict:\n        px_tol = 0.0" in EV
   and "if strict:\n            tol = 0.0" in EV and "PX_TOL_CENTS if b in TOL_BOOKS else 0," not in EV)
ok("evaluate: any line but the alert's is refused for DOGS", '"dogs_alert_line_only"' in EV)
ok("order-time recheck carries the same rule", '"strict": strict' in EV and 'tol = 0.0 if rv.get("strict")' in RV
   and "DOGS orders only at the alert line" in RV)


def _reval(strict, now_am, book="novig", line=None, mtype="moneyline", rvline=None):
    alert = 120
    r = {"live": {"book": book, "line": line, "px": {"thr": alert}},
         "reval": {"mtype": mtype, "side": "A", "line": rvline, "alert_af": alert, "alert_cost": ex.american_to_prob(alert),
                   "px_tol": 0.0 if strict else ex.american_to_prob(ex.cents_worse(alert, ex.PX_TOL_CENTS)) - ex.american_to_prob(alert),
                   "strict": strict, "hp": 0.0, "lv_mode": "legacy", "al": {"sport": "NBA"}}}
    _rb = ex.reread_book
    try:
        ex.reread_book = lambda b, ln, rv: {"status": "ok", "best_price_american": now_am, "best_price_american_qual": now_am,
                                            "line": line, "buy_levels": []}
        return ex.revalidate(r, 100)
    finally:
        ex.reread_book = _rb


a = _reval(True, 118)
ok("DOGS: Novig 2c worse than the alert at order time is REFUSED", a[0] is False and "moved worse" in a[1], a[1])
b = _reval(False, 118)
ok("(control) another lane keeps its 2c on Novig - the refusal above is the DOGS rule", "moved worse" not in b[1], b[1])
c = _reval(True, 120)
ok("DOGS: the alert price itself passes the price gate", "moved worse" not in c[1], c[1])
d = _reval(True, 125, mtype="spread", line=4.0, rvline=3.5)
ok("DOGS: a different line at order time is refused even at a better price", d[0] is False and "only at the alert line" in d[1], d[1])
rr = {"lcs": [{"book": "prophetx"}, {"book": "novig"}, {"book": "kalshi"}, {"book": "polymarket_us"}], "route": {"trigger": "kalshi"}}
ex.dogs_route(rr)
ok("route: trigger venue, then Novig, nothing else", [c["book"] for c in rr["lcs"]] == ["kalshi", "novig"] and rr["lc"]["book"] == "kalshi")
rr = {"lcs": [{"book": "prophetx"}, {"book": "novig"}], "route": {"trigger": "kalshi"}}
ex.dogs_route(rr)
ok("route: trigger off the number -> Novig only (it passed on its own)", [c["book"] for c in rr["lcs"]] == ["novig"])
rr = {"lcs": [{"book": "prophetx"}, {"book": "polymarket_us"}], "route": {"trigger": "kalshi"}}
ex.dogs_route(rr)
ok("route: neither available -> no venue, no order", rr["lcs"] == [] and rr["lc"] is None)
ok("the live branch applies the route", "trigger_first(r, ent)\n                dogs_route(r)" in SRC)
_live = ex.px_live.LIVE
try:
    ex.px_live.LIVE = True
    _rw = lambda v, why, reason=None: ex.rest_wanted({"play": {"source": "dogs"}, "books": {}, "verdict": v, "reason": reason,
                                                     "live": {"go": False, "why": why}})
    ok("DOGS never rests a bid (price skip)", _rw("SKIP", ["price: x"], "price: x") is False)
    ok("DOGS never rests a bid (no live book at the number)", _rw("WOULD PLACE", ["no live book has the alert number or better"]) is False)
finally:
    ex.px_live.LIVE = _live

# --- 10. a DOGS candidate cannot cause a Gmail search (Peter, Nov 23) -------------------------------
class _NoGmail:
    calls = []

    def uid(self, *a, **k):
        _NoGmail.calls.append(a)
        if a[0] == "SEARCH":
            return "OK", [b""]
        raise AssertionError("fetch not expected")


DP = {"source": "dogs", "play_key": "dogs|NBA|A @ B|side|A", "sport": "NBA", "game": "A @ B", "bet": "A ML (+120)"}
BP = {"source": "board", "play_key": "board|NBA|C @ D|total|over", "sport": "NBA", "game": "C @ D", "bet": "Over 220.5 (-110)"}
_en, _tc = ex.registry.enabled, ex.registry.tokens_complete
try:
    ex.registry.enabled = lambda: False                      # the store cannot answer -> the Gmail fallback path
    ok("store cannot answer: DOGS candidates are dropped before the dedupe", ex.dogs_no_gmail([DP, BP], "dedupe") == [BP])
    _NoGmail.calls = []
    m = ex.handled_pids(_NoGmail(), [DP])
    ok("DOGS-only candidates: ZERO Gmail calls on the fallback path", _NoGmail.calls == [] and m and all(m.values()), _NoGmail.calls)
    ok("...and the play is treated as handled, so it sits the run out", ex.already_handled(_NoGmail(), DP, m) is True)
    _NoGmail.calls = []
    m = ex.handled_pids(_NoGmail(), [DP, BP])
    q = " ".join(str(x) for c in _NoGmail.calls for x in c)
    dtok = {t for k in ex.handled_keys(DP) for t in (ex.pid(k), ex.retry_tok(k))}
    ok("mixed candidates: the search carries the other lane's tokens and none of DOGS'", len(_NoGmail.calls) == 1
       and not any(t in q for t in dtok) and all(ex.pid(k) in q for k in ex.handled_keys(BP)), q[:120])
    ex.registry.enabled, ex.registry.tokens_complete = (lambda: True), (lambda *a, **k: True)
    ok("store complete: DOGS candidates are admitted", ex.dogs_no_gmail([DP, BP], "dedupe") == [DP, BP])
finally:
    ex.registry.enabled, ex.registry.tokens_complete = _en, _tc
ok("candidates and the side-taken check both pass through the filter", 'dogsplays = dogs_no_gmail(dogsplays, "dedupe")' in SRC
   and 'new = dogs_no_gmail(new, "side-taken check")' in SRC and "if not dogs_strict(p) and not gsearch(M2, held_tok(dk))" in SRC)

# --- 11. switch OFF = no order, whatever else is true -------------------------------------------------
BR = SRC.split('elif p.get("source") == "dogs":   # DOGS lane')[1].split("elif ent and (p.get")[0]
ok("OFF puts a reason in `why` before any gate is asked", 'why = [] if DOGS_LIVE else ["DOGS lane not switched on (EXEC_DOGS_LIVE)"]' in BR)
ok('"go": True is reachable only with an empty `why`', BR.count('"go": True') == 1
   and 'if not why and r["verdict"] == "WOULD PLACE" and r.get("lc"):\n                    r["live"] = {"go": True' in BR)
ok("code default is off (unset, empty, or anything but 'on')", '(os.environ.get("EXEC_DOGS_LIVE") or "off")' in SRC)
ok("limits unchanged: $100 unit, 8 plays, $800/day, 30-minute freshness",
   (ex.DOGS_UNIT, ex.DOGS_MAX_PLAYS, ex.DOGS_DAILY_RISK, ex.DOGS_MAX_AGE_MIN) == (100.0, 8, 800.0, 30)
   or any(os.environ.get(v) for v in ("EXEC_DOGS_DAILY_RISK", "EXEC_DOGS_MAX_PLAYS", "EXEC_DOGS_MAX_AGE_MIN")))

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
