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
got = dr.settled_on(trk, "2026-11-19")
ok("a game settling after midnight UTC still belongs to the ET day it was played",
   [k for k, _ in got] == ["a", "b"], [k for k, _ in got])
ok("an unsettled row is excluded", "d" not in [k for k, _ in got])
ok("another ET day is excluded", "c" not in [k for k, _ in got])
ok("newest first", [k for k, _ in got][0] == "a")

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
ok("the record and units total are shown", "3 settled" in lines and "+" in lines)
ok("V1 coverage is reported as a fraction, not implied", "V1 CLV on 2/3" in lines, lines[:400])
ok("a missing field prints its reason", "not in the CLV ledger" in lines)
ok("an absent value prints as a dash", " - " in lines or "-" in lines)
ok("the report says a dash is a field we do not hold", "a field we do not hold" in lines)
empty = "\n".join(dr.render("2026-11-19", []))
ok("a day with nothing settled says so rather than printing an empty table",
   "No settled bets recorded" in empty)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
