#!/usr/bin/env python3
"""The uniqueness-gated one-token relaxation: opt-in, and it must still refuse the Nov 5 traps.

Measured Nov 23 on the liquidity feed: 398 of 596 rows (67%) were unambiguous near-misses - both
sides hit a correct distinctive token, the sides were distinct, and the match was refused only for
not reaching TWO tokens on either side. The feed names games by city while the Nov 5 floor was
tuned on bet rows carrying full team names.

The floor's real job is done here by UNIQUENESS, not by the token count.
"""
import clv_ledger as cl

P, F = [], []
def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


def fx(fid, lg, p1, p2, start="2026-11-22T00:00:00Z"):
    return {fid: {"lg": lg, "p1": p1, "p2": p2, "start": start, "status": "scheduled"}}


def bet(lg, game, teams=(), start="2026-11-22T00:00:00Z"):
    return {"league": lg, "game": game, "teams": [{"name": t} for t in teams], "game_start": start}


# --- the dominant class: city-only strings, one token a side, exactly one fixture ---------------
NBA = fx("f1", "NBA", "Toronto Raptors Toronto TOR", "Milwaukee Bucks Milwaukee MIL")
b = bet("NBA", "Milwaukee vs Toronto: Spread")
ok("STRICT still refuses a one-token-per-side match", cl.find_fixture({"fixtures": NBA}, b) is None)
ok("RELAXED matches it when exactly one fixture qualifies",
   cl.find_fixture({"fixtures": NBA}, b, relax_unique=True) == "f1")

NHL = fx("n1", "NHL", "New York Islanders New York Islanders NYI", "Toronto Maple Leafs Toronto TOR")
ok("the real NHL near-miss from the feed now joins",
   cl.find_fixture({"fixtures": NHL}, bet("NHL", "Toronto vs New York I"), relax_unique=True) == "n1")

# --- Nov 5 trap 1: Penn State / Pennsylvania ------------------------------------------------------
PENN = {}
PENN.update(fx("p_real", "NCAAF", "Penn State Nittany Lions Penn State PSU", "Purdue Boilermakers Purdue PUR"))
PENN.update(fx("p_junk", "NCAAF", "Pennsylvania Quakers Pennsylvania PENN", "Columbia Lions Columbia CLMB"))
pb = bet("NCAAF", "Penn State Nittany Lions @ Purdue Boilermakers")
ok("STRICT resolves Penn State to the real game (the junk fails the floor)",
   cl.find_fixture({"fixtures": PENN}, pb) == "p_real")
ok("RELAXED does not change that - the strict rule already answered",
   cl.find_fixture({"fixtures": PENN}, pb, relax_unique=True) == "p_real")
pb2 = bet("NCAAF", "Penn @ Lions")
ok("and with only the coincidental tokens, the junk fixture is REFUSED - the carrying tokens "
   "belong to another fixture in the window",
   cl.find_fixture({"fixtures": PENN}, pb2, relax_unique=True) is None,
   str(cl.find_fixture({"fixtures": PENN}, pb2, relax_unique=True)))
ok("even with the real game ABSENT, a coincidental one-token-a-side match is refused",
   cl.find_fixture({"fixtures": dict(fx("p_junk", "NCAAF", "Pennsylvania Quakers Pennsylvania PENN",
                                        "Columbia Lions Columbia CLMB"),
                                     **fx("other", "NCAAF", "Penn State Nittany Lions PSU",
                                          "Ohio State Buckeyes OSU"))},
                   pb2, relax_unique=True) is None)
ok("a token shared with ANY other fixture in the window cannot carry a relaxed match",
   "if not shared:" in open("clv_ledger.py", encoding="utf-8").read())

# --- Nov 5 trap 2: the shared-word collision ------------------------------------------------------
FLA = fx("fl", "NCAAF", "Florida Atlantic Owls Florida Atlantic FAU", "South Florida Bulls South Florida USF")
fb = bet("NCAAF", "North Carolina State @ Florida State")
ok("a side carried by a word the OTHER side also matched is refused, strict",
   cl.find_fixture({"fixtures": FLA}, fb) is None)
ok("and refused under the relaxation too - distinctness is untouched",
   cl.find_fixture({"fixtures": FLA}, fb, relax_unique=True) is None)

# --- the other Nov 5 traps, still refused ----------------------------------------------------------
BAY = {}
BAY.update(fx("b1", "NFL", "Tampa Bay Buccaneers Tampa Bay TB", "Carolina Panthers Carolina CAR"))
BAY.update(fx("b2", "NFL", "Green Bay Packers Green Bay GB", "Chicago Bears Chicago CHI"))
ok("'Bay' alone cannot carry a match across Tampa Bay and Green Bay",
   cl.find_fixture({"fixtures": BAY}, bet("NFL", "Bay vs Bay"), relax_unique=True) is None)

ONE = fx("o1", "NBA", "Los Angeles Lakers LA Lakers LAL", "Utah Jazz Utah UTA")
ok("ONE SIDE ONLY is still a refusal under the relaxation",
   cl.find_fixture({"fixtures": ONE}, bet("NBA", "Los Angeles C vs Houston"),
                   relax_unique=True) is None)
ok("a genuinely absent game is still a refusal",
   cl.find_fixture({"fixtures": NBA}, bet("NBA", "Denver vs Phoenix"), relax_unique=True) is None)

TWO = {}
TWO.update(fx("t1", "NBA", "Toronto Raptors Toronto TOR", "Milwaukee Bucks Milwaukee MIL"))
TWO.update(fx("t2", "NBA", "Toronto Raptors Toronto TOR", "Milwaukee Bucks Milwaukee MIL",
              start="2026-11-22T03:00:00Z"))
ok("two soft-qualifying fixtures is AMBIGUOUS and refused",
   cl.find_fixture({"fixtures": TWO}, b, relax_unique=True) is None)

ok("a fixture in the wrong league is never considered",
   cl.find_fixture({"fixtures": fx("w", "NHL", "Toronto Raptors Toronto TOR",
                                   "Milwaukee Bucks Milwaukee MIL")}, b, relax_unique=True) is None)
ok("a fixture more than 36h from the game is never considered",
   cl.find_fixture({"fixtures": fx("f9", "NBA", "Toronto Raptors Toronto TOR",
                                   "Milwaukee Bucks Milwaukee MIL",
                                   start="2026-11-26T00:00:00Z")}, b, relax_unique=True) is None)
ok("no team words means no match, relaxed or not",
   cl.find_fixture({"fixtures": NBA}, bet("NBA", ""), relax_unique=True) is None)

# --- the shared default must not move ---------------------------------------------------------------
import inspect
ok("find_fixture defaults to the strict rule", "relax_unique=False" in inspect.signature(
   cl.find_fixture).__str__() or cl.find_fixture.__defaults__ == (False,))
ok("_qualifies still defaults to the two-token floor", cl._qualifies.__defaults__ == (2,))
SRC = open("clv_ledger.py", encoding="utf-8").read()
ok("the relaxation runs ONLY when the strict rule found nothing",
   "if relax_unique and not hit:" in SRC)
ok("and it demands exactly one soft match", "if len(soft) == 1:" in SRC)
ok("fixture_check is untouched - a scored row validates by the strict rule",
   "_qualifies(f, lg, gs, words)" in SRC.split("def fixture_check")[1])

x2 = open("x2_tag.py", encoding="utf-8").read()
ok("the 2X tagger opts in", x2.count("relax_unique=True") == 2)
for mod in ("clv_report.py", "clv_day_audit.py", "clv_coverage.py", "executed_clv.py",
            "board_clv_check.py", "clv_basis.py"):
    ok(f"{mod} does NOT opt in - the CLV path keeps today's behaviour",
       "relax_unique" not in open(mod, encoding="utf-8").read())

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
