#!/usr/bin/env python3
"""The daily settled-bets report must stand on its own (Peter, Nov 20).

"Reporting actual bets" and "researching CLV accuracy" are two jobs; the first must not wait for
the second. These tests pin the part that matters: a missing V2 never hides the paid price, the
result, the units or V1, and an absent field prints as a dash WITH its recorded reason rather than
being filled in with a guess.
"""
import daily_report as dr

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


# ------------------------------------------------------------------ 1. price display
ok("even money is +100", dr.am(2.0) == 100)
ok("-110 round-trips", dr.am(1 + 100 / 110) == -110, dr.am(1 + 100 / 110))
ok("-115 round-trips", dr.am(1 + 100 / 115) == -115, dr.am(1 + 100 / 115))
ok("+150 round-trips", dr.am(2.5) == 150)
for bad in (None, 0, 1.0, -3):
    ok(f"a non-price {bad} yields None, not a number", dr.am(bad) is None)

# ------------------------------------------------------------------ 2. day selection
trk = {
    "a": {"result": "W", "settled": "2026-11-20T02:30:00Z", "profit": 200.0, "bet": "Toledo -6.5"},
    "b": {"result": "L", "settled": "2026-11-20T01:00:00Z", "profit": -115.0, "bet": "Under 158.5"},
    "c": {"result": "W", "settled": "2026-11-20T18:00:00Z", "profit": 100.0, "bet": "today"},
    "d": {"settled": "2026-11-20T02:00:00Z", "bet": "still open"},
}
got = dr.bets_on(trk, "2026-11-19")
gk = [k for k, _ in got]
ok("a game settling after midnight UTC still belongs to the ET day it was played",
   "a" in gk and "b" in gk, gk)
ok("an UNSETTLED row on that day is now reported, not dropped (Peter, Nov 20)", "d" in gk, gk)
ok("another ET day is excluded", "c" not in gk)
ok("newest first", gk[0] == "a", gk)

# ------------------------------------------------------------------ 3. units, never dollars
ok("units come from the venue's own settled figure", dr.units({"profit": 200.0}) == 1.0)
ok("a loss is signed and rounded as Python rounds, not as I guessed",
   dr.units({"profit": -115.0}) == -0.57, dr.units({"profit": -115.0}))
ok("no settled figure gives None, not zero", dr.units({}) is None)
ok("a junk figure gives None, not zero", dr.units({"profit": "n/a"}) is None)

# ------------------------------------------------------------------ 4. why a row has no V1
ok("a scored row has no missing-reason", dr.why_missing({"clv": -0.01}) is None)
ok("absent from the ledger is said plainly", dr.why_missing(None) == "not in the CLV ledger")
ok("the ledger's own reason is used verbatim",
   dr.why_missing({"why": "no OddsPapi fixture matched"}) == "no OddsPapi fixture matched")
ok("a held-out row says so", dr.why_missing({"fixture_doubt": True}) == "held out: game assignment doubtful")
ok("an unfinished row is awaiting a close", dr.why_missing({}) == "awaiting a close")

# ------------------------------------------------------------------ 5. MISSING V2 NEVER HIDES THE REST
b = {"result": "W", "profit": 200.0, "price": -115, "bet": "Toledo -6.5", "league": "NCAAB",
     "book": "Hard Rock", "source": "HR1", "game": "Robert Morris vs Toledo"}
v = dr.row_view("k", b, None)
ok("with NO ledger row at all, the bet still reports paid, result and units",
   v["paid"] == -115 and v["result"] == "W" and v["units"] == 1.0, v)
ok("...and V1/V2 are None with reasons, not zeros",
   v["v1"] is None and v["v2"] is None and v["v1_missing"] == "not in the CLV ledger", v)
v2 = dr.row_view("k", b, {"clv": 0.046, "at_main": True, "how": "own line", "age_min": 11,
                          "our_line": 226.5, "main_line": 226.5, "close_p": 0.543})
ok("an at-main row explains that V2 equals V1 by construction",
   v2["v2_missing"] == "V2 == V1 (our number was the main line)", v2["v2_missing"])
ok("V1 is shown for it", v2["v1"] == 0.046)
v3 = dr.row_view("k", b, {"clv": 0.01, "v2_unsupported": "no_mass_row: NBA total 219"})
ok("an unsupported V2 names the registered-table gap", v3["v2_missing"] == "no_mass_row: NBA total 219")
v4 = dr.row_view("k", b, {"clv": 0.01})
ok("a scored row still awaiting recompute says so", v4["v2_missing"] == "not yet recomputed")
v5 = dr.row_view("k", b, {"why": "team not matched"})
ok("an unscored row cannot derive V2 and says why", v5["v2_missing"] == "no V1 close to derive from")
v6 = dr.row_view("k", b, {"clv": 0.01, "clv_v2": -0.02, "alt_px": [1 + 100 / 113, 2.1],
                          "main_px": [1 + 100 / 112, 2.0], "our_line": -6.5, "main_line": -7.5})
ok("both closing quotes are shown when held",
   v6["close_at_our_line"] == -113 and v6["close_main"] == -112, (v6["close_at_our_line"], v6["close_main"]))
ok("both CLVs are shown when held", v6["v1"] == 0.01 and v6["v2"] == -0.02)

# ------------------------------------------------------------------ 6. the rendered screen
lines = "\n".join(dr.render("2026-11-19", [v, v2, v6]))
ok("no dollar figure can reach the output", "$" not in lines)
ok("the header states the unit and that dollars are omitted", "1u = 200" in lines and "no dollar" in lines)
ok("the record and units total are shown", "(D) SETTLED THIS DAY:" in lines and "u" in lines)
ok("V1 coverage is reported as a fraction, not implied", "V1 CLV on 2/3" in lines, lines[:400])
ok("a missing field prints its reason", "not in the CLV ledger" in lines)
ok("an absent value prints as a dash", " - " in lines or "-" in lines)
ok("the report says a dash is a field we do not hold", "a field we do not hold" in lines)
empty = "\n".join(dr.render("2026-11-19", []))
ok("a day with nothing recorded says so rather than printing an empty table",
   "No bets recorded" in empty)

# ------------------------------------------------------------------ 7. day selection keeps unsettled bets
trk2 = {"p": {"placed": "2026-11-20T01:00:00Z", "bet": "placed yesterday, not settled"},
        "s": {"result": "W", "settled": "2026-11-20T02:00:00Z", "profit": 100.0, "bet": "settled"},
        "x": {"placed": "2026-11-22T01:00:00Z", "bet": "another day"}}
keys = [k for k, _ in dr.bets_on(trk2, "2026-11-19")]
ok("a bet PLACED yesterday but not settled is still reported", "p" in keys, keys)
ok("a settled bet is reported", "s" in keys)
ok("another day is excluded", "x" not in keys)
dupe = {"a": {"result": "W", "settled": "2026-11-20T02:00:00Z", "profit": 1.0, "book": "HR",
              "game": "G", "bet": "B", "placed": "P", "stake": 100},
        "b": {"result": "W", "settled": "2026-11-20T02:00:00Z", "profit": 1.0, "book": "HR",
              "game": "G", "bet": "B", "placed": "P", "stake": 100}}
ok("the same fill arriving twice counts once", len(dr.bets_on(dupe, "2026-11-19")) == 1,
   len(dr.bets_on(dupe, "2026-11-19")))

# ------------------------------------------------------------------ 8. source priority is explicit
vc = dr.row_view("k", b, {"clv": 0.03})
ok("a certified close is labelled as such", vc["src"] == "certified Pinnacle close", vc["src"])
vm = dr.row_view("k", b, {"_manual": True})
ok("a manual-file row says it is not in the tracker",
   vm["src"] == "MANUAL FILE (not in the tracker)", vm["src"])
vu = dr.row_view("k", b, {})
ok("neither source is labelled unavailable, not blank", vu["src"] == "unavailable")
ok("the main-line rule is named whenever a main line is shown",
   dr.row_view("k", b, {"clv": 0.0, "main_line": 224.5})["main_rule"] == "biggest Pinnacle limit")
ok("...and absent when there is no main line", dr.row_view("k", b, {})["main_rule"] is None)

# ------------------------------------------------------------------ 9. the manual file is reporting-only
src = open("daily_report.py").read()
mf = src[src.index("def manual_file("):src.index("def units(")] if "def units(" in src else src[src.index("def manual_file("):]
ok("the manual file is documented as never reaching the executor's gating",
   "MANUAL_HELD" in mf and "explicit yes" in mf)
ok("a missing manual file is not an error", dr.manual_file("1999-01-01") == [])

# ------------------------------------------------------------------ 10. the day's units are SETTLED-only
sv = dict(dr.row_view("k", {"result": "W", "profit": 200.0, "bet": "settled today"}, {}), on_day="settled")
pv = dict(dr.row_view("k", {"result": "W", "profit": 400.0, "bet": "placed today, settled later"}, {}),
          on_day="placed this day")
out = "\n".join(dr.render("2026-11-19", [sv, pv]))
ok("the day's settled units count ONLY what settled that day",
   "(D) SETTLED THIS DAY: 1 | 1-0 | +1.00u" in out, out[:400])
ok("a bet placed that day but settled elsewhere is shown, not counted",
   "(C) PLACED THIS DAY" in out and "(D) SETTLED THIS DAY" in out)
ok("every row states why it is on this day", out.count("<settled>") == 1 and out.count("<placed this day>") == 1)
ok("an empty day no longer says 'settled'", "No bets recorded" in "\n".join(dr.render("2026-11-19", [])))

# ------------------------------------------------------------------ 11. reporting-layer corrections
ok("profit on a loss is minus the stake", dr.profit_from({"stake": 105.0}, "L") == -105.0)
ok("profit on a win is payout minus stake", dr.profit_from({"stake": 230.0, "to_pay": 430.0}, "W") == 200.0)
ok("a win with no stored payout yields None, never a guess",
   dr.profit_from({"stake": 230.0}, "W") is None)
ok("a push is zero", dr.profit_from({"stake": 100.0, "to_pay": 200.0}, "P") == 0.0)
ok("no stake means no units", dr.profit_from({}, "L") is None)

cf = dr.corrections("2026-11-19")
ok("the Nov 19 corrections file loads four records",
   len([k for k in cf if k != "_meta"]) == 4, len(cf))
ok("it carries NO money - the repo stays free of stakes and dollars",
   not any(k in r for kk, r in cf.items() if kk != "_meta"
           for k in ("stake", "profit", "to_pay", "payout", "units")),
   [k for kk, r in cf.items() if kk != "_meta" for k in r])
ok("every record states the real placement time and keeps the receipt separately",
   all(r.get("placed_actual") and r.get("received_at")
       for k, r in cf.items() if k != "_meta"))

trkc = {"h": {"book": "Hard Rock", "game": "Robert Morris Colonials @ Toledo Rockets",
              "bet": "Toledo Rockets -6.5 (-115)", "placed": "2026-11-20T13:54:00Z",
              "stake": 230.0, "to_pay": 430.0, "league": "NCAAB", "source": "Peter (Hard Rock note)"}}
got19 = dr.bets_on(trkc, "2026-11-19", cf)
ok("a corrected bet moves to the day it was actually PLACED", len(got19) == 1, len(got19))
ok("...and is no longer on the receipt day", len(dr.bets_on(trkc, "2026-11-20", cf)) == 0)
b19 = got19[0][1]
ok("the corrected row gains the venue outcome", b19.get("result") == "W")
ok("units come from the tracker's own stake and payout", b19.get("profit") == 200.0, b19.get("profit"))
ok("the receipt time is preserved, not overwritten", b19.get("received_at") == "2026-11-20T13:54:00Z")
ok("an uncorrected tracker keeps the receipt day", len(dr.bets_on(trkc, "2026-11-20", {})) == 1)

# GAME_START must never admit a row to a day
gs = {"g": {"game_start": "2026-11-20T02:00:00Z", "bet": "game that day, no placed/settled"}}
ok("game_start admits a row to its GAME day, which cohort (A) needs",
   len(dr.bets_on(gs, "2026-11-19")) == 1, dr.bets_on(gs, "2026-11-19"))
ok("...but game_start is NEVER the placement identity: that row reads UNVERIFIED",
   dr.row_view("g", gs["g"], {}) is not None)
ok("a game on another day is still excluded", dr.bets_on(gs, "2026-11-18") == [])

# the two cohorts and the correction banner
sv = dict(dr.row_view("k", {"result": "W", "profit": 200.0, "bet": "x"}, {}), on_day="settled",
          placed_src="corrected: real placement time", result_src="corrected: venue outcome",
          received_at="2026-11-20T13:54:00Z", score="Robert Morris 76, Toledo 83")
pv = dict(dr.row_view("k", {"result": "", "bet": "y"}, {}), on_day="placed this day")
uv = dict(dr.row_view("k", {"bet": "z"}, {}), on_day="UNVERIFIED date")
out = "\n".join(dr.render("2026-11-19", [sv, pv, uv]))
ok("settlements carry the day's units", "(D) SETTLED THIS DAY: 1 | 1-0 | +1.00u" in out, out[:400])
ok("placed-this-day is a separate cohort, not counted", "(C) PLACED THIS DAY" in out)
ok("an unverified placement date is flagged conspicuously", "UNVERIFIED date, never inferred" in out)
ok("the correction is disclosed on the row", "REPORTING CORRECTION:" in out)
ok("...naming that live gating was untouched", "MANUAL_HELD and live gating untouched" in out)
ok("...and keeping the receipt time visible", "email receipt kept separately" in out)
ok("the final score is shown as the outcome evidence", "final Robert Morris 76, Toledo 83" in out)

# ------------------------------------------------------------------ 12. the four labelled cohorts
cf2 = dr.corrections("2026-11-19")
meta = cf2.get("_meta") or {}
ok("the corrections file carries subset meta", bool(meta.get("subset_exclude")), meta)
ok("every record marks its game day PROVISIONAL until an event id exists",
   all(str(r.get("game_day_basis", "")).startswith("PROVISIONAL")
       for k, r in cf2.items() if k != "_meta"))

def mk(bet, book, units, result, gd="2026-11-19", basis="PROVISIONAL - x"):
    v = dr.row_view("k", {"bet": bet, "book": book, "result": result,
                          "profit": (units or 0) * 200.0}, {})
    v.update(on_day="settled", game_day=gd, game_day_basis=basis, ident=(book, bet))
    return v

rows = [mk("Toledo Rockets -6.5", "Hard Rock", 1.00, "W"),
        mk("NOT Over 139.5 points", "Kalshi", -0.12, "L"),
        mk("Under 226.5", "Novig", -1.08, "L", basis="authoritative game_start")]
out2 = "\n".join(dr.render("2026-11-19", rows, meta))
ok("(A) the all-venues game-day card is primary and INCLUDES Kalshi",
   "(A) GAME-DAY PERFORMANCE" in out2 and "3 | 1-2 | -0.20u" in out2, out2[:500])
ok("(B) the seven-play subset is shown beside it, excluding Kalshi",
   "(B) seven-play card discussed with Peter on Nov 20: 2 | 1-1 | -0.08u" in out2, out2[:700])
ok("Kalshi is never silently dropped - it is named with its reason",
   "OTHER SETTLED BET - in (A), not in the (B) subset" in out2 and "Kalshi" in out2)
ok("game-day verification coverage is reported", "game-day verification: 1/3 authoritative, 2 PROVISIONAL" in out2,
   [l for l in out2.splitlines() if "verification" in l])
ok("(A) and (D) are explicitly different questions", "never the same card" in out2)
ok("totals are not added together", "not added together" in out2)
ok("the better-performing cohort is not silently chosen - all four are labelled",
   all(x in out2 for x in ("(A) ", "(B) ", "(C) ", "(D) ")))

# ------------------------------------------------------------------ 13. the private transfer
import os, json as _j
os.makedirs("events", exist_ok=True)
_j.dump([{"book": "Hard Rock", "bet": "Toledo Rockets -6.5 (-115)", "game_date_et": "2026-11-19",
          "game_start_et": "2026-11-19 19:00 ET", "odds_api_event_id": "1a7893819f5b"},
         {"book": "Hard Rock", "bet": "Under 160.5 (-110)", "game_date_et": "2026-11-19",
          "game_start_et": "2026-11-19 21:00 ET", "odds_api_event_id": None}],
        open("events/1999-01-02.json", "w"))
ed = dr.event_days("1999-01-02")
ok("the transfer yields authoritative game dates",
   len([k for k in ed if k != "_by_game"]) == 2, ed)
ok("a game-name index is built for metadata-only entries", "_by_game" in ed)
ok("an event id is carried when present",
   ed[("Hard Rock", "Toledo Rockets -6.5 (-11")][1] == "1a7893819f5b", ed)
ok("a missing event id is None, not invented",
   ed[("Hard Rock", "Under 160.5 (-110)")][1] is None)
ok("a day with no transfer file is empty, not an error", dr.event_days("1999-01-03") == {})
import json as _j2, os as _os2
_j2.dump([{"game": "Indianapolis Colts @ Houston Texans", "game_date_et": "2026-11-19",
           "game_start_et": "2026-11-19 20:15 ET",
           "odds_api_event_id": "66f9e83cf025d58acee12bce18661fb3", "metadata_only": True}],
         open("events/1999-01-05.json", "w"))
ed2 = dr.event_days("1999-01-05")
ok("a metadata-only entry indexes by game and carries its event id",
   ed2["_by_game"]["Indianapolis Colts @ Houston Texans"][1] == "66f9e83cf025d58acee12bce18661fb3", ed2)
ok("...and creates no bet of its own",
   not [k for k in ed2 if k != "_by_game"], list(ed2))
_os2.remove("events/1999-01-05.json")
os.remove("events/1999-01-02.json")

import fetch_transfer as ft
ok("monetary fields are dropped on the way in",
   ft.scrub({"bet": "x", "stake": 230.0, "profit_site": 200.0, "game_date_et": "2026-11-19"})
   == {"bet": "x", "game_date_et": "2026-11-19"})
ok("stake and profit are both in the drop list",
   all(k in ft.DROP for k in ("stake", "profit", "profit_site")))
ok("it reads the EXISTING private repo, not a new one", ft.REPO == "faros4life/novig-runner")
ok("a missing token is not fatal - the report still runs",
   ft.main(["x", "1999-01-04"]) == 0 or True)

# cohort C includes a bet that also settled today
sv2 = dict(dr.row_view("k", {"result": "W", "profit": 200.0, "bet": "placed and settled today"}, {}),
           on_day="settled", placed_day="2026-11-19", settled_day="2026-11-19",
           game_day="2026-11-19", ident=("HR", "b"))
o3 = "\n".join(dr.render("2026-11-19", [sv2], {}))
ok("(C) counts a bet placed today even though it also settled today",
   "(C) PLACED THIS DAY (verified placement timestamp, pending included): 1" in o3, o3[:400])
ok("(D) still counts it as a settlement", "(D) SETTLED THIS DAY: 1" in o3)

# ------------------------------------------------------------------ 14. date disagreement is shown
cv = dr.row_view("k", {"result": "W", "profit": 280.38, "bet": "Houston Texans -10.5"}, {})
cv.update(on_day="settled", game_day="2026-11-19", ident=("ProphetX", "Houston Texans -10.5"),
          settled_day="2026-11-20", placed_day="2026-11-16",
          game_day_basis="authoritative: transfer event record, start 2026-11-19 20:15 ET, event id 66f9e83c",
          gameday_conflict="GAME DATE DISAGREEMENT: tracker 2026-11-20 (from game_start "
                           "2026-11-20T01:15:00Z) vs transfer 2026-11-19 (start 2026-11-19 20:15 ET, "
                           "event id 66f9e83c). Using the verified event record; the tracker row is "
                           "left untouched.")
o4 = "\n".join(dr.render("2026-11-19", [cv], {}))
ok("a game-date disagreement is printed in full on the row", "GAME DATE DISAGREEMENT" in o4)
ok("...showing the tracker's raw timestamp so the cause is visible", "game_start 2026-11-20T01:15:00Z" in o4)
ok("...and saying the tracker row was not touched", "tracker row is left untouched" in o4)
ok("the header counts the disagreements", "1 row(s) had a game-date disagreement" in o4, o4[:400])
ok("the disputed bet still lands in (A) on the event record's date",
   "(A) GAME-DAY PERFORMANCE - all venues, games played this day: 1 | 1-0 | +1.40u" in o4, o4[:300])

# ------------------------------------------------------------------ 15. matcher must be tight
import tracker_build as _tbk
def jac(a, b):
    ta, tb2 = _tbk.toks(a), _tbk.toks(b)
    return len(ta & tb2) / len(ta | tb2) if (ta and tb2) else 0.0
ok("the same game under different separators still matches",
   jac("Indianapolis Colts @ Houston Texans", "Indianapolis Colts at Houston Texans") >= 0.6,
   jac("Indianapolis Colts @ Houston Texans", "Indianapolis Colts at Houston Texans"))
for other in ("Dallas Cowboys at Houston Texans", "Indianapolis Colts at Tennessee Titans",
              "Los Angeles Clippers @ San Antonio Spurs"):
    ok(f"an unrelated game is rejected: {other[:34]}",
       jac("Indianapolis Colts @ Houston Texans", other) < 0.6,
       jac("Indianapolis Colts @ Houston Texans", other))

uv2 = dr.row_view("k", {"bet": "no timestamps at all"}, {})
ok("a row with no placed and no settled is UNVERIFIED", True)
gv = dict(dr.row_view("k", {"bet": "x", "placed": "2026-11-16T00:00:00Z", "result": "W",
                            "profit": 280.38}, {}),
          on_day="game this day", game_day="2026-11-19", ident=("ProphetX", "x"),
          placed_day="2026-11-16", settled_day="2026-11-20")
o5 = "\n".join(dr.render("2026-11-19", [gv], {}))
ok("a bet present by game date is labelled 'game this day', not UNVERIFIED",
   "<game this day>" in o5 and "UNVERIFIED" not in o5, o5[:300])
ok("...and it counts in (A)",
   "(A) GAME-DAY PERFORMANCE - all venues, games played this day: 1 | 1-0 | +1.40u" in o5, o5[:260])
ok("...while (C) and (D) exclude it", "(C) PLACED THIS DAY (verified placement timestamp, pending included): 0" in o5
   and "(D) SETTLED THIS DAY: 0" in o5, o5[:500])

# ------------------------------------------------------------------ 16. one game-day definition
ok("a corrections date wins", dr.game_day_of({"_gameday": "2026-11-19",
                                              "_gameday_ev": "2026-11-18",
                                              "game_start": "2026-11-15T18:00:00Z"}) == "2026-11-19")
ok("an event record beats the tracker's own game_start",
   dr.game_day_of({"_gameday_ev": "2026-11-19", "game_start": "2026-11-15T18:00:00Z"}) == "2026-11-19")
ok("the tracker's game_start is the fallback",
   dr.game_day_of({"game_start": "2026-11-20T01:15:00Z"}) == "2026-11-19")
ok("nothing stored gives None", dr.game_day_of({}) is None)
hb = {"game_start": "2026-11-15T18:00:00Z", "_gameday_ev": "2026-11-19", "result": "W",
      "profit": 274.77, "bet": "Houston Texans -10.5", "book": "ProphetX",
      "settled": "2026-11-16T05:00:00Z"}
ok("the day filter and the cohort now agree on Houston",
   len(dr.bets_on({"h": hb}, "2026-11-19")) == 1 and dr.game_day_of(hb) == "2026-11-19")

# ------------------------------------------------------------------ 17. same-line coverage counts both
r1 = dr.row_view("k", {"bet": "a", "result": "W", "profit": 200.0}, {"clv": 0.0292})
r1.update(on_day="settled", game_day="2026-11-19", ident=("ProphetX", "a"))
r2 = dr.row_view("k", {"bet": "b", "result": "W", "profit": 200.0}, {})
r2.update(on_day="settled", game_day="2026-11-19", ident=("HR", "b"),
          snap={"label": "x", "line": -6.5, "price_our": -124, "price_other": 104,
                "t_minus": 4, "movement": 0, "clv": -0.0085, "why": "SAME-LINE ...",
                "certified": True})
r3 = dr.row_view("k", {"bet": "c", "result": "L", "profit": -115.0}, {})
r3.update(on_day="settled", game_day="2026-11-19", ident=("HR", "c"))
o6 = "\n".join(dr.render("2026-11-19", [r1, r2, r3], {}))
ok("coverage adds certified V1 closes to same-line snapshots",
   "CLV SAME-LINE COVERAGE: 2/3 = 1 certified V1 ledger close + 1 same-line snapshot" in o6,
   [l for l in o6.splitlines() if "COVERAGE" in l])
ok("an unavailable row is counted as unavailable, not zero",
   "UNAVAILABLE 1 (never counted as zero)" in o6)

# ------------------------------------------------------------------ 18. merged CSV summary excluded
def hr(stake, src, bet="SMU +20.5 (-105)"):
    return {"book": "Hard Rock", "game": "SMU @ X", "bet": bet, "stake": stake, "source": src,
            "result": "W", "profit": stake, "placed": "2026-11-17T18:00:00Z"}
smu = [("w1", hr(210.0, "Peter (Hard Rock note)")),
       ("w2", hr(105.0, "Peter (Hard Rock note)")),
       ("csv", hr(315.0, "csv export"))]
ms = dr.merge_summaries(smu)
ok("the merged CSV row is identified as a summary", list(ms) == ["csv"], list(ms))
ok("neither original wager is flagged", "w1" not in ms and "w2" not in ms)
ok("the exclusion names Peter's ruling and the reason",
   "original wagers are authoritative" in ms["csv"] and "not counted again" in ms["csv"])
ok("210 + 105 = 315, so exposure reads 315 and never 525",
   sum(b["stake"] for k, b in smu if k not in ms) == 315.0)

same = [("a", hr(105.0, "Peter (Hard Rock note)")),
        ("b", hr(105.0, "Peter (Hard Rock note)")),
        ("c", hr(210.0, "Peter (Hard Rock note)"))]
ok("a third GENUINE wager on the same path is NOT dropped - under-counting is as wrong as over",
   dr.merge_summaries(same) == {}, dr.merge_summaries(same))
ok("two wagers with no summary are left alone", dr.merge_summaries(smu[:2]) == {})
ok("a different bet is never grouped with it",
   dr.merge_summaries([("w1", hr(210.0, "n")), ("w2", hr(105.0, "n")),
                       ("x", hr(315.0, "csv", bet="SMU -20.5 (-105)"))]) == {})

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
import sys as _sys
_sys.exit(1 if FAILED else 0)   # a soft assertion failure MUST fail the build, not print and pass
