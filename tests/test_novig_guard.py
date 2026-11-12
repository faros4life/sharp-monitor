"""Nov 12 (Peter): Novig submissions are PAUSED by default, and the duplicate guard FAILS CLOSED.

Before this, novig_conflict() could miss a real duplicate two ways: a totals position whose outcome name did not
contain "over" was read as UNDER (so holding the OVER looked like a conflict, and holding the UNDER looked like a
duplicate - one of those is wrong), and a spread/moneyline position whose name did not match a team was skipped
entirely, which answers "no duplicate" on a position the guard could not read.
"""
import copy
import inspect
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_check as bc  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


# ---------------------------------------------------------------- 1. submissions paused at ONE chokepoint
import book_live as bl  # noqa: E402

ck("1 the pause lives in book_live.novig_place, the single chokepoint for the live order AND the resting bid",
   "if not NOVIG_SUBMIT:" in inspect.getsource(bl.novig_place))
ck("1 it is read from the repo variable EXEC_NOVIG_SUBMIT and defaults to OFF",
   'os.environ.get("EXEC_NOVIG_SUBMIT") or "off"' in open(bl.__file__).read())
ck("1 with the variable unset, novig_place refuses and submits nothing",
   bl.NOVIG_SUBMIT is False and "paused" in bl.NOVIG_PAUSE_WHY.lower())
ck("1 the refusal is the FIRST gate, so no later check can mask it",
   inspect.getsource(bl.novig_place).index("NOVIG_SUBMIT") < inspect.getsource(bl.novig_place).index("preflight("))
ck("1 the executor adds NO second switch with a different name (one venue, one switch)",
   "NOVIG_SUBMIT" not in inspect.getsource(ex.live_order_other) and "novig_submit_on" not in open(ex.__file__).read())
ck("1 reads, fills and cancellation are not gated by it",
   "NOVIG_SUBMIT" not in inspect.getsource(bl.novig_results) and "NOVIG_SUBMIT" not in inspect.getsource(bl.novig_cancel)
   if hasattr(bl, "novig_cancel") else "NOVIG_SUBMIT" not in inspect.getsource(bl.novig_results))

# ---------------------------------------------------------------- 2. the side of a position is read by outcomeId
TEAMS = ("Charlotte Hornets", "Phoenix Suns")


def mkt(mtype, outs):
    return {"marketId": "M1", "marketType": mtype, "outcomes": outs}


def pos(oid, mid="M1"):
    return {"marketId": mid, "outcomeId": oid, "qty": 100}


T_NAMED = mkt("TOTAL", [{"outcomeId": "o1", "name": "Over 214.5"}, {"outcomeId": "o2", "name": "Under 214.5"}])
T_BLANK = mkt("TOTAL", [{"outcomeId": "o1", "name": ""}, {"outcomeId": "o2", "name": ""}])
T_ODD = mkt("TOTAL", [{"outcomeId": "o1", "name": "Total Points 214.5 - A"}, {"outcomeId": "o2", "name": "Under 214.5"}])
S_NAMED = mkt("SPREAD", [{"outcomeId": "o1", "name": "Charlotte Hornets -2.5"}, {"outcomeId": "o2", "name": "Phoenix Suns +2.5"}])
S_BLANK = mkt("SPREAD", [{"outcomeId": "o1", "name": ""}, {"outcomeId": "o2", "name": ""}])

ck("2 named totals read OVER/UNDER", ex.novig_side_of(T_NAMED, pos("o1"), TEAMS, "NBA") == "OVER"
   and ex.novig_side_of(T_NAMED, pos("o2"), TEAMS, "NBA") == "UNDER")
ck("2 an UNNAMED two-outcome total falls back to list order, documented as such",
   ex.novig_side_of(T_BLANK, pos("o1"), TEAMS, "NBA") == "OVER" and ex.novig_side_of(T_BLANK, pos("o2"), TEAMS, "NBA") == "UNDER")
ck("2 a total whose name says NEITHER over nor under is UNREADABLE (was silently read as UNDER)",
   ex.novig_side_of(T_ODD, pos("o1"), TEAMS, "NBA") is None, str(ex.novig_side_of(T_ODD, pos("o1"), TEAMS, "NBA")))
ck("2 named spreads read the team index", ex.novig_side_of(S_NAMED, pos("o1"), TEAMS, "NBA") == 0
   and ex.novig_side_of(S_NAMED, pos("o2"), TEAMS, "NBA") == 1)
ck("2 an unnamed spread is UNREADABLE (never guessed)", ex.novig_side_of(S_BLANK, pos("o1"), TEAMS, "NBA") is None)
ck("2 an outcomeId that is not in the market definition is UNREADABLE", ex.novig_side_of(T_NAMED, pos("zzz"), TEAMS, "NBA") is None)

# ---------------------------------------------------------------- 3. novig_conflict: duplicate / conflict / unknown
AL = {"sport": "NBA", "game": "Charlotte Hornets @ Phoenix Suns", "bet": "Under 214.5 (-110)", "start_utc": ""}
NRES = {"status": "ok", "market_id": "M1"}
MKS = {"E1": [T_NAMED]}
ck("3 same side -> duplicate", ex.novig_conflict(AL, "total", "UNDER", TEAMS, NRES, [pos("o2")], MKS) == "duplicate")
ck("3 other side -> conflict", ex.novig_conflict(AL, "total", "UNDER", TEAMS, NRES, [pos("o1")], MKS) == "conflict")
u = ex.novig_conflict(AL, "total", "UNDER", TEAMS, NRES, [pos("o1")], {"E1": [T_ODD]})
ck("3 an unreadable position on a comparable market -> ('unknown', why), never None",
   isinstance(u, tuple) and u[0] == "unknown" and "no readable side" in u[1], str(u))
us = ex.novig_conflict({"sport": "NBA", "game": AL["game"], "bet": "", "start_utc": ""}, "spread", 0, TEAMS, NRES, [pos("o1")], {"E1": [S_BLANK]})
ck("3 an unreadable SPREAD position -> unknown (it used to be skipped: fail open)", isinstance(us, tuple) and us[0] == "unknown", str(us))
ck("3 a readable position still decides even when another is unreadable",
   ex.novig_conflict(AL, "total", "UNDER", TEAMS, NRES, [pos("o1", "M9"), pos("o2")], MKS) == "duplicate")
ck("3 no positions -> None (nothing to say)", ex.novig_conflict(AL, "total", "UNDER", TEAMS, NRES, [], MKS) is None)
ck("3 an unreadable NON-comparable market is ignored (a total position cannot duplicate a spread bet)",
   ex.novig_conflict({"sport": "NBA", "game": AL["game"], "bet": "", "start_utc": ""}, "spread", 0, TEAMS, NRES, [pos("o1")], {"E1": [T_ODD]}) is None)

# ---------------------------------------------------------------- 4. evaluate() HOLDS on unknown
NOW = datetime.now(timezone.utc)
PLAY = {"play_key": "NBA|CHA@PHX|total|UNDER", "sport": "NBA", "source": "rules", "game": AL["game"],
        "bet": "Under 214.5 (-110)", "start_utc": (NOW + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}
esrc = inspect.getsource(ex.evaluate)
ck("4 evaluate() turns 'unknown' into a SKIP that says it is failing closed",
   'c[0] == "unknown"' in esrc and "cannot rule out a duplicate (fail closed)" in esrc)
ck("4 ...and it is checked BEFORE the duplicate/conflict branches, so it cannot be masked",
   esrc.index('c[0] == "unknown"') < esrc.index('if c == "conflict"'))
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
