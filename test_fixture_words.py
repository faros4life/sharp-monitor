#!/usr/bin/env python3
"""
OFFLINE TEST for the fixture-matching fix (Peter/Muse, Nov 12, Priority 2).

No network, no credentials, no state file. It uses the REAL tracker_build.toks/WEAK and the REAL
clv_ledger._qualifies, so it tests the shipped logic rather than a copy of it.

THE DEFECT. find_fixture built its match words as:

    words = (toks(teams) or toks(game)) - WEAK

`or` short-circuits. A row whose `teams` list holds only ONE side still yields tokens, so the game
text was never consulted - and _qualifies requires BOTH fixture participants to intersect `words`.
The second side could therefore never match. Measured on real data: 46 of 54 unscored rows failed
on "one side matched nothing", including rows whose closest fixture was exactly the right game:

    bet   "Atlanta Hawks @ Orlando Magic"   (teams list carried Atlanta only)
    fixture "Orlando Magic Orlando ORL" v "Atlanta Hawks Atlanta ATL"
    -> p1 hit []   because "orlando"/"magic" were in the GAME TEXT, which `or` skipped

MUSE'S CONSTRAINT: fix it "without allowing false matches". So this tests BOTH directions. The
widening must admit the correct fixture AND still refuse: a different game, a one-sided coincidence,
a sub-two-token brush, and an ambiguous tie. None of _qualifies' guards is relaxed by the fix - it
only changes which words the guards are applied to.
"""
import sys

import clv_ledger as cl
import tracker_build as tb


def words_fixed(b):
    """find_fixture's word set, as it now stands: union of teams and game text."""
    return (tb.toks(" ".join(t.get("name", "") for t in b.get("teams") or []))
            | tb.toks(b.get("game"))) - tb.WEAK


def words_old(b):
    """The pre-fix form, kept so the regression it caused stays visible."""
    return (tb.toks(" ".join(t.get("name", "") for t in b.get("teams") or []))
            or tb.toks(b.get("game"))) - tb.WEAK


def fixture(p1, p2, lg="NBA", start="2026-10-21T23:00:00Z"):
    return {"lg": lg, "start": start, "p1": p1, "p2": p2}


def main():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if got == want else 'FAIL'} {name}")

    print("OFFLINE TEST - fixture matching words (real toks/WEAK/_qualifies)")
    print("=" * 88)

    # The real failing row from production: teams carries ONE side, game text carries both.
    bet = {"league": "NBA", "game": "Atlanta Hawks @ Orlando Magic",
           "teams": [{"name": "Atlanta Hawks"}]}
    right = fixture("Orlando Magic Orlando ORL", "Atlanta Hawks Atlanta ATL")
    gs = cl.tp("2026-10-21T23:00:00Z")

    # 1 - the regression is real and still demonstrable
    check("OLD words miss the second side", cl._qualifies(right, "NBA", gs, words_old(bet)), False)

    # 2 - the fix admits the correct fixture
    check("NEW words match the correct fixture", cl._qualifies(right, "NBA", gs, words_fixed(bet)),
          True)

    # 3 - a DIFFERENT game must still be refused
    other = fixture("Boston Celtics Boston BOS", "Miami Heat Miami MIA")
    check("a different game is still refused", cl._qualifies(other, "NBA", gs, words_fixed(bet)),
          False)

    # 4 - one side coinciding is not enough: both must intersect
    half = fixture("Atlanta Hawks Atlanta ATL", "Denver Nuggets Denver DEN")
    check("one matching side alone is refused", cl._qualifies(half, "NBA", gs, words_fixed(bet)),
          False)

    # 5 - wrong league is still refused even with a perfect name match
    check("wrong league is refused", cl._qualifies(dict(right, lg="NHL"), "NBA", gs,
                                                   words_fixed(bet)), False)

    # 6 - outside the 36h window is still refused
    far = fixture("Orlando Magic Orlando ORL", "Atlanta Hawks Atlanta ATL",
                  start="2026-10-25T23:00:00Z")
    check("a fixture outside 36h is refused", cl._qualifies(far, "NBA", gs, words_fixed(bet)),
          False)

    # 7 - the two-token floor still bites. "New York" is WEAK-stripped to "york" on one side only.
    thin = {"league": "NBA", "game": "York A @ York B", "teams": []}
    tf = fixture("York A", "York B")
    a = (tb.toks("York A") - tb.WEAK) & words_fixed(thin)
    c = (tb.toks("York B") - tb.WEAK) & words_fixed(thin)
    check("two-token floor still enforced", max(len(a), len(c)) >= 2,
          cl._qualifies(tf, "NBA", gs, words_fixed(thin)))

    # 8 - a side carried only by words the other also matched is still refused
    shared = fixture("Los Angeles Lakers", "Los Angeles Clippers")
    bet2 = {"league": "NBA", "game": "Los Angeles Lakers @ Los Angeles Clippers", "teams": []}
    w2 = words_fixed(bet2)
    aa = (tb.toks("Los Angeles Lakers") - tb.WEAK) & w2
    cc = (tb.toks("Los Angeles Clippers") - tb.WEAK) & w2
    check("each side keeps a distinctive token", bool((aa - cc) and (cc - aa)), True)
    check("shared-city fixture still qualifies on its distinctive words",
          cl._qualifies(shared, "NBA", gs, w2), True)

    # 9 - the OKC/SAS row from production, teams empty, both sides in the game text only
    bet3 = {"league": "NBA", "game": "Oklahoma City Thunder @ San Antonio Spurs", "teams": []}
    f3 = fixture("San Antonio Spurs San Antonio SAS", "Oklahoma City Thunder Oklahoma City OKC")
    check("OKC @ SAS matches with teams empty", cl._qualifies(f3, "NBA", gs, words_fixed(bet3)),
          True)

    # 10 - widening must not make an unrelated fixture match that game
    f4 = fixture("Portland Trail Blazers Portland POR", "Utah Jazz Utah UTA")
    check("unrelated fixture still refused for OKC @ SAS",
          cl._qualifies(f4, "NBA", gs, words_fixed(bet3)), False)

    print("=" * 88)
    if fails:
        for f in fails:
            print("  " + f)
        print("  FAIL - do not commit")
        return 1
    print("  PASS - the union admits the correct fixture that `or` was hiding, and every guard")
    print("  still refuses: wrong game, one-sided coincidence, wrong league, outside 36h, the")
    print("  two-token floor and the distinctive-token rule are all unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
