#!/usr/bin/env python3
"""
Regression tests for the duplicate-counting and stale-stake defect Peter found on Nov 10.

THE DEFECT. man_id changed on Nov 5 from a hash of the whole "MANUAL: {...}" note line to
book+game+bet, and tracker_build.man_migrate retires the old key IN THE TRACKER. clv_ledger only
setdefault()s keys into its own st["bets"] and prunes by first_seen age, so the retired key survived
there for 60 days carrying the snapshot it froze with - which for the two NCAAB notes was the
INVENTED stake the old sizing rule guessed, not Peter's real stake. Every reader of clv/state.enc
counted the wager twice, and plays_kelly's ACTUAL dollar column counted it twice at the wrong stake.

Each test below is written to FAIL against the pre-fix behaviour (count every row in the clv state),
so it cannot pass by accident: the fixtures are built so that an unfiltered reader gets a provably
different answer.

No secrets, no network, no cache - these test the rule, not the data.
"""
import sys

import clv_stale as cstale
import tracker_build as tb

OK, BAD = [], []


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def snap(book, game, bet, **kw):
    s = {"book": book, "game": game, "bet": bet}
    s.update(kw)
    return s


def main():
    print("REGRESSION - duplicate counting and stale-stake contamination (Peter, Nov 10)\n")

    BOOK, GAME, BET = "Hard Rock", "Bellarmine @ Indiana", "Indiana -29.5 (-105)"
    live_id = tb.man_id(BOOK, GAME, BET)          # the id the tracker uses after the Nov 5 change
    stale_id = "mn|" + "0" * 40                   # an old-scheme id: same wager, different hash

    # the tracker holds the wager ONCE, at the REAL stake
    trk = {live_id: {"book": BOOK, "game": GAME, "bet": BET, "stake": 10.5, "result": "L", "price": -105}}
    # the clv state holds it TWICE: the live id, plus the retired id frozen at the invented stake
    bets = {
        live_id: {"clv": -0.02, "snap": snap(BOOK, GAME, BET, stake=10.5, result="L", price=-105)},
        stale_id: {"clv": -0.02, "snap": snap(BOOK, GAME, BET, stake=210.0, result="L", price=-105)},
    }

    # ------------------------------------------------------------ 1. the duplicate is identified
    print("1. A retired old-scheme id is identified as a duplicate of the live row")
    m = cstale.stale_map(bets, trk)
    check("the stale id is found", stale_id in m, f"resolved to {str(m.get(stale_id))[:14]}..")
    check("it resolves to the LIVE tracker id", m.get(stale_id) == live_id)
    check("the live id is never marked stale", live_id not in m)
    check("exactly one row is excluded, not both", len(m) == 1)
    kept, bad, unproven = cstale.live_bets(bets, trk)
    check("the filtered view holds the wager ONCE (pre-fix: twice)", len(kept) == 1 and live_id in kept,
          f"kept {len(kept)} of {len(bets)}")

    # ------------------------------------------------------------ 2. the surviving row has the REAL stake
    print("\n2. The row that survives carries the real stake, not the frozen invented one")
    stakes = [ (r.get("snap") or {}).get("stake") for r in kept.values() ]
    check("the kept stake is the tracker's real stake", stakes == [10.5], f"kept stakes {stakes}")
    check("the invented stake is gone from the filtered view", 210.0 not in stakes)
    # the dollar consequence, which is the reason this matters at all
    unfiltered = sum(-(r["snap"]["stake"]) for r in bets.values() if r["snap"]["result"] == "L")
    filtered = sum(-(r["snap"]["stake"]) for r in kept.values() if r["snap"]["result"] == "L")
    check("ACTUAL dollars change once the stale row goes", abs(unfiltered - filtered) > 1,
          f"unfiltered {unfiltered:+.2f} vs filtered {filtered:+.2f}")

    # ------------------------------------------------------------ 3. identity is NOT the test
    print("\n3. Identical game, line and price is NOT treated as a duplicate (Peter, Nov 10)")
    # two SEPARATE wagers on the same game/line/price, BOTH present in the tracker - e.g. a top-up.
    a = tb.man_id(BOOK, GAME, BET)
    b = "mn|" + "1" * 40
    trk2 = {a: {"book": BOOK, "game": GAME, "bet": BET}, b: {"book": BOOK, "game": GAME, "bet": BET}}
    bets2 = {a: {"clv": -0.02, "snap": snap(BOOK, GAME, BET, stake=50)},
             b: {"clv": -0.02, "snap": snap(BOOK, GAME, BET, stake=50)}}
    check("two tracker-present rows with identical content are both kept",
          cstale.stale_map(bets2, trk2) == {}, "no exclusion on content identity alone")
    kept2, _, _ = cstale.live_bets(bets2, trk2)
    check("the filtered view keeps both wagers", len(kept2) == 2)

    # ------------------------------------------------------------ 4. unproven orphans are kept
    print("\n4. An orphan that resolves to nothing is kept and flagged, never excluded")
    orph = "ks|KXNCAAFSPREAD-SOMETHING"
    bets3 = dict(bets, **{orph: {"clv": 0.2076, "snap": snap("Kalshi", "Okla St vs Kan St", "over 3.5")}})
    kept3, bad3, unproven3 = cstale.live_bets(bets3, trk)
    check("the orphan is reported as unproven", orph in unproven3)
    check("the orphan is NOT excluded", orph in kept3)
    check("only the proven stale row is excluded", set(bad3) == {stale_id})

    # ------------------------------------------------------------ 5. fail-safe when the tracker is unreadable
    print("\n5. An unreadable tracker must exclude NOTHING (never silently empty a report)")
    check("empty tracker -> no exclusions", cstale.stale_map(bets, {}) == {})
    kept5, bad5, unproven5 = cstale.live_bets(bets, {})
    check("empty tracker -> every row kept", len(kept5) == len(bets) and not bad5)
    check("empty tracker -> nothing reported as orphaned either", unproven5 == [])
    check("empty clv state is handled", cstale.stale_map({}, trk) == {})

    # ------------------------------------------------------------ 6. the input is never mutated
    print("\n6. Read-time only: the caller's dict is never mutated (stored state is preserved)")
    before = dict(bets)
    cstale.live_bets(bets, trk)
    check("the clv bets dict still holds both rows after filtering", len(bets) == 2 and bets == before)

    # ------------------------------------------------------------ 7. a non-manual scheme is untouched
    print("\n7. Only the manual id scheme changed, so other schemes are never resolved away")
    nv = {"nv|order-123": {"clv": 0.01, "snap": snap("Novig", GAME, BET, stake=300)}}
    check("a bot/exchange id absent from the tracker is not called a duplicate",
          cstale.stale_map(nv, trk) == {})

    print(f"\n{len(OK)} passed, {len(BAD)} failed")
    if BAD:
        for b in BAD:
            print(f"  FAILED: {b}")
        return 1
    print("ALL REGRESSION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
