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

    print("8. the ledger exposes the recovery hooks it needs")
    check("ALT_FX exists", hasattr(cl, "ALT_FX"))
    check("ALT_SRC exists for provenance", hasattr(cl, "ALT_SRC"))
    check("recover_leagues exists", callable(getattr(cl, "recover_leagues", None)))

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all shared-matcher checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
