#!/usr/bin/env python3
"""
SHARED MATCHER REGRESSION (Peter, Nov 13 2026).

The live scorer and the scorecard must use ONE fixture matcher and ONE closing-price
calculation. Two implementations of the same rule is how the first fixture exclusion went wrong,
so this pins that they are literally the same objects, and pins the ordered-sides behaviour that
recovers the Nov 12 Louisiana row without loosening anything.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_fallback as fb    # noqa: E402
import clv_ledger as cl      # noqa: E402
import fixture_match as fxm  # noqa: E402

BAD = []
LOU = {"id1402765370899062": {
    "lg": "NCAAF", "start": "2026-11-13T02:00:00.000Z",
    "p1": "Louisiana-Monroe Warhawks Louisiana-Monroe ULM",
    "p2": "Louisiana Ragin Cajuns Ragin Cajuns LOU"}}
ROW = {"league": "NCAAF", "game": "Louisiana @ UL Monroe", "bet": "Under 48.5",
       "game_start": "2026-11-13T02:00:00Z"}


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def main():
    print("1. both callers use the SAME matcher object, not a copy of the rule")
    check("fallback uses fixture_match.ordered_match", fb.fxm.ordered_match is fxm.ordered_match)
    check("ledger uses fixture_match.ordered_match", cl.fxm.ordered_match is fxm.ordered_match)
    check("both use the same alt_fixtures", fb.fxm.alt_fixtures is cl.fxm.alt_fixtures)
    check("both use the same sides_of", fb.fxm.sides_of is cl.fxm.sides_of)

    print("2. the Louisiana row resolves through the shared matcher")
    fid, note = fxm.ordered_match(ROW, LOU, cl.tp)
    check("matched", fid == "id1402765370899062", (fid, note))
    check("note says ordered one-to-one", "ordered one-to-one" in note, note)

    print("3. the ORIGINAL matcher still refuses it - nothing was loosened")
    check("find_fixture still returns None", cl.find_fixture({"fixtures": LOU}, ROW) is None)

    print("4. the ordered test is stricter, not looser, everywhere else")
    check("wrong league refused",
          fxm.ordered_match(dict(ROW, league="NBA"), LOU, cl.tp)[0] is None)
    check("start 13h away refused",
          fxm.ordered_match(dict(ROW, game_start="2026-11-13T16:00:00Z"), LOU, cl.tp)[0] is None)
    check("no league on the row refused",
          fxm.ordered_match(dict(ROW, league=None), LOU, cl.tp)[0] is None)
    two = dict(LOU)
    two["dupe"] = dict(LOU["id1402765370899062"])
    fid2, note2 = fxm.ordered_match(ROW, two, cl.tp)
    check("two one-to-one matches refused", fid2 is None, (fid2, note2))
    check("and the reason counts them", "2 fixtures" in note2, note2)

    print("5. a genuinely ambiguous pair is refused with its shared token named")
    amb = {"x": {"lg": "NCAAF", "start": "2026-11-13T02:00:00.000Z",
                 "p1": "Louisiana Tigers", "p2": "Louisiana Bears"}}
    fid3, note3 = fxm.ordered_match({"league": "NCAAF", "game": "Louisiana @ Louisiana",
                                     "bet": "Under 48.5",
                                     "game_start": "2026-11-13T02:00:00Z"}, amb, cl.tp)
    check("refused", fid3 is None, fid3)
    check("names the ambiguity", "AMBIGUOUS" in note3, note3)

    print("6. snap.teams wins over game text, and order is respected")
    rows = {"league": "NCAAF", "game": "", "game_start": "2026-11-13T02:00:00Z",
            "bet": "Under 48.5",
            "teams": [{"name": "Louisiana Ragin Cajuns"}, {"name": "Louisiana-Monroe Warhawks"}]}
    fid4, note4 = fxm.ordered_match(rows, LOU, cl.tp)
    check("matched from snap.teams", fid4 == "id1402765370899062", (fid4, note4))
    check("source reported", "snap.teams" in note4, note4)

    print("7. alt_fixtures reads the stores the live scorer previously ignored")
    alt = fxm.alt_fixtures()
    check("returns a mapping", isinstance(alt, dict))
    if alt:
        srcs = {src for _f, src in alt.values()}
        check("sources are named for the audit trail", all(isinstance(x, str) for x in srcs), srcs)
        check("the Louisiana fixture is among them", "id1402765370899062" in alt,
              "not in alt_fixtures - check oddspapi/fixtures.json")
    else:
        print("  skip alt_fixtures content (no alternate store on disk in this checkout)")

    print("7b. resolve_side lives in the LEAF module, so importing it cannot cycle")
    # clv_basis imports clv_std, which imports exchange_lag -> hist_cache -> clv_ledger. So
    # clv_ledger CANNOT import clv_basis at module level: the first attempt did and broke 8 test
    # files with "module 'clv_ledger' has no attribute 'KEY'" mid-import. resolve_side therefore
    # lives in fixture_match, whose only import is tracker_build, and clv_basis re-exports it.
    check("fixture_match owns resolve_side", callable(getattr(fxm, "resolve_side", None)))
    check("clv_basis re-exports the same object", __import__("clv_basis").resolve_side is fxm.resolve_side)
    check("the ledger uses it", cl.fxm.resolve_side is fxm.resolve_side)
    fm_src = __import__("pathlib").Path("fixture_match.py").read_text()
    check("fixture_match imports no heavy module at top level",
          "import clv_std" not in fm_src and "import clv_ledger" not in fm_src,
          "fixture_match gained a heavy import")

    print("8. the ledger exposes the recovery hooks it needs")
    check("ALT_FX exists", hasattr(cl, "ALT_FX"))
    check("ALT_SRC exists for provenance", hasattr(cl, "ALT_SRC"))
    check("recover_leagues exists", callable(getattr(cl, "recover_leagues", None)))

    print("TRUNCATED AND RENAMED TEAMS (Nov 14) - five credits proved the cache was fine")
    # Every unresolved NBA unit in the registered-candidate tier was a Los Angeles game, and five
    # billable /fixtures calls bought 79 fixtures and resolved none. Two naming facts, not a
    # missing fixture: Kalshi truncates the title to "Los Angeles C", and OddsPapi spells the team
    # "LA Clippers" - so the row's {los, angeles} shares NOTHING with {la, clippers, lac} and the
    # fixture was skipped before the ambiguity test was ever reached.
    _FX = {"lac": {"lg": "NBA", "start": "2026-11-14T03:30:00Z",
                   "p1": "LA Clippers LA Clippers LAC",
                   "p2": "Oklahoma City Thunder Oklahoma City OKC"},
           "other": {"lg": "NBA", "start": "2026-11-14T01:00:00Z",
                     "p1": "Miami Heat Miami MIA", "p2": "Cleveland Cavaliers Cleveland CLE"}}
    _snap = {"league": "NBA", "game_start": "2026-11-14T03:30:00Z",
             "teams": [{"name": "Oklahoma City"}, {"name": "Los Angeles C"}],
             "ticker": "KXNBATOTAL-26NOV13OKCLAC-223"}
    fid, why = fxm.ordered_match(_snap, _FX, cl.tp)
    check("the venue ticker resolves what the prose cannot", fid == "lac", f"{fid} {why}")
    check("and the reason names the ticker", "ticker" in why, why)

    print("  the ticker path refuses rather than guessing")
    nt = dict(_snap); nt.pop("ticker")
    fid, why = fxm.ordered_match(nt, _FX, cl.tp)
    check("no ticker and no usable prose -> refused", fid is None, f"{fid} {why}")
    check("and the message blames the names, not the cache",
          "none maps onto the row" in why or "identifies neither" in why, why)

    bad = dict(_snap, ticker="KXNBATOTAL-26NOV13MIACLE-223")
    fid, why = fxm.ordered_match(bad, _FX, cl.tp)
    check("a ticker naming a DIFFERENT game does not resolve this row", fid != "lac", f"{fid} {why}")

    one = dict(_snap, ticker="KXNBATOTAL-26NOV13LAC-223")   # one code only
    fid, why = fxm.ordered_match(one, _FX, cl.tp)
    check("one code alone is never enough", fid is None, f"{fid} {why}")

    print("  a full, consistent name still goes through the ordinary token path")
    full = {"league": "NBA", "game_start": "2026-11-14T01:00:00Z",
            "teams": [{"name": "Miami Heat"}, {"name": "Cleveland Cavaliers"}]}
    fid, why = fxm.ordered_match(full, _FX, cl.tp)
    check("token match wins and is attributed to itself", fid == "other" and "ticker" not in why,
          f"{fid} {why}")

    print("  an LA derby with no distinguishing text is refused")
    derby = {"lg": "NBA", "start": "2026-11-14T03:30:00Z",
             "p1": "Los Angeles Lakers Los Angeles LAL", "p2": "LA Clippers LA Clippers LAC"}
    fid, why = fxm.ordered_match({"league": "NBA", "game_start": "2026-11-14T03:30:00Z",
                                  "teams": [{"name": "Los Angeles"}, {"name": "Los Angeles"}]},
                                 {"d": derby}, cl.tp)
    check("'Los Angeles' twice, no ticker -> refused", fid is None, f"{fid} {why}")
    fid, why = fxm.ordered_match({"league": "NBA", "game_start": "2026-11-14T03:30:00Z",
                                  "teams": [{"name": "Los Angeles L"}, {"name": "Los Angeles C"}],
                                  "ticker": "KXNBATOTAL-26NOV13LALLAC-230"}, {"d": derby}, cl.tp)
    check("but the derby DOES resolve once the ticker carries both codes", fid == "d", f"{fid} {why}")

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all shared-matcher checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
