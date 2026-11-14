#!/usr/bin/env python3
"""
FALLBACK REGRESSION (Peter, Nov 13 2026): the fallback and the scorecard must agree, and the
fallback must never buy coverage with an ambiguous fixture.

Peter: "Both systems must produce identical CLV when given the same fixture, line, entry price
and closing quote." That is asserted here against clv_ledger's own arithmetic rather than
assumed, including the rounding, which is where two independently written formulas usually drift.

The ambiguity cases are modelled on the real Louisiana row: "Louisiana @ UL Monroe" against a
fixture whose participants are "Louisiana-Monroe Warhawks" and "Louisiana Ragin Cajuns". Both
fixture sides contain "louisiana", so nothing in the row distinguishes them - and a fallback that
guessed would produce a confidently wrong CLV on a live-money record.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_fallback as fb   # noqa: E402
import clv_ledger as cl     # noqa: E402

BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def main():
    print("1. the two systems compute the IDENTICAL CLV from the same inputs")
    # clv_ledger's own line is: rec["clv"] = round(c["p"] * d - 1, 4)
    for p, d in ((0.5067, 1.9608), (0.4909, 2.0000), (0.5023, 2.0400), (0.33, 1.5),
                 (0.9, 1.11), (0.01, 50.0), (0.5, 2.0)):
        ledger = round(p * d - 1, 4)
        check(f"p={p} d={d}: fallback == ledger", fb.compute_clv(p, d) == ledger,
              f"{fb.compute_clv(p, d)} vs {ledger}")

    print("2. rounding is applied ONCE, at the end, to full-precision inputs")
    # My first version of this test asserted -0.0064 for Dallas from the DISPLAYED p of 0.5067 and
    # got -0.0065. Both were right: the report prints a rounded p but computes from the
    # unrounded one. Pinning the displayed 4dp values would have baked a rounding error into the
    # test and then into any future "disagreement" hunt, so the agreement is asserted against the
    # ledger formula on identical inputs (case 1) and the precision rule is pinned here instead.
    p_full = cl.novig_p(1.9090, 1.9610)          # Dallas: the actual two closing decimals
    check("full-precision p differs from its 4dp display", round(p_full, 4) == 0.5067 and p_full != 0.5067,
          p_full)
    check("CLV from full precision is -0.64%", fb.compute_clv(p_full, 1.9608) == -0.0064,
          fb.compute_clv(p_full, 1.9608))
    check("CLV from the rounded p would have been -0.65%", fb.compute_clv(0.5067, 1.9608) == -0.0065,
          fb.compute_clv(0.5067, 1.9608))
    p_ch = 1 - cl.novig_p(1.9090, 1.9800)        # Charlotte: held side is the Under
    check("Charlotte from full precision is -1.83%", fb.compute_clv(p_ch, 2.0000) == -0.0183,
          fb.compute_clv(p_ch, 2.0000))

    print("3. no-vig uses the same function as the scorecard")
    check("novig_p is clv_ledger's", fb.cl.novig_p is cl.novig_p)
    check("eff_dec is clv_ledger's", fb.cl.eff_dec is cl.eff_dec)
    check("two_way is clv_ledger's", fb.cl.two_way is cl.two_way)

    print("4. the REAL Louisiana row matches, because the sides are ORDERED")
    # I predicted this would be refused as ambiguous: both fixture participants contain
    # "louisiana", which is what defeats the live matcher's unordered token test. The ordered test
    # resolves it with information the live matcher throws away - "Louisiana @ UL Monroe" names
    # the AWAY side first, and OddsPapi lists the HOME side as p1. away->p2, home->p1, one-to-one.
    # This is not a relaxed rule; it uses a fact the strict rule never consulted.
    fixtures = {"id1402765370899062": {
        "lg": "NCAAF", "start": "2026-11-13T02:00:00.000Z",
        "p1": "Louisiana-Monroe Warhawks Louisiana-Monroe ULM",
        "p2": "Louisiana Ragin Cajuns Ragin Cajuns LOU"}}
    s = {"league": "NCAAF", "game": "Louisiana @ UL Monroe", "bet": "Under 48.5",
         "game_start": "2026-11-13T02:00:00Z"}
    fid, note = fb.strict_match(s, fixtures)
    check("the fixture IS matched", fid == "id1402765370899062", (fid, note))
    check("described as one-to-one", "one-to-one" in note, note)
    # and the live matcher still refuses it, which is why the fallback exists at all
    st_live = {"fixtures": fixtures}
    check("clv_ledger.find_fixture still refuses it", cl.find_fixture(st_live, s) is None,
          cl.find_fixture(st_live, s))

    print("4b. a GENUINELY ambiguous pair is still refused")
    amb = {"fxX": {"lg": "NCAAF", "start": "2026-11-13T02:00:00.000Z",
                   "p1": "Louisiana Tigers", "p2": "Louisiana Bears"}}
    fid, note = fb.strict_match({"league": "NCAAF", "game": "Louisiana @ Louisiana",
                                 "bet": "Under 48.5", "game_start": "2026-11-13T02:00:00Z"}, amb)
    check("refused", fid is None, (fid, note))
    check("reason names the ambiguity", "AMBIGUOUS" in note, note)

    print("5. an unambiguous game DOES match, from any cache")
    fixtures = {"fxA": {"lg": "NBA", "start": "2026-11-13T01:00:00Z",
                        "p1": "Minnesota Timberwolves Minnesota MIN",
                        "p2": "Dallas Mavericks Dallas DAL"}}
    s = {"league": "NBA", "game": "Dallas Mavericks @ Minnesota Timberwolves",
         "bet": "Over 225.5", "game_start": "2026-11-13T01:00:00Z"}
    fid, note = fb.strict_match(s, fixtures)
    check("matched", fid == "fxA", (fid, note))
    check("described as one-to-one", "one-to-one" in note, note)

    print("6. snap.teams is preferred over game text when present")
    s2 = dict(s, game="", teams=[{"name": "Dallas Mavericks"}, {"name": "Minnesota Timberwolves"}])
    fid, note = fb.strict_match(s2, fixtures)
    check("matched from snap.teams", fid == "fxA", (fid, note))
    check("the source is reported", "snap.teams" in note, note)

    print("7. wrong league and wrong date are refused")
    check("league mismatch refused",
          fb.strict_match(dict(s, league="NHL"), fixtures)[0] is None)
    check("date 2 days off refused",
          fb.strict_match(dict(s, game_start="2026-11-15T01:00:00Z"), fixtures)[0] is None)

    print("8. two one-to-one matches are refused as ambiguous, never 'first wins'")
    two = dict(fixtures)
    two["fxB"] = {"lg": "NBA", "start": "2026-11-13T01:30:00Z",
                  "p1": "Minnesota Timberwolves Minnesota MIN",
                  "p2": "Dallas Mavericks Dallas DAL"}
    fid, note = fb.strict_match(s, two)
    check("ambiguous pair refused", fid is None, (fid, note))
    check("reason says how many matched", "2 fixtures" in note, note)

    print("9. a row that cannot be split into two sides is refused")
    fid, note = fb.strict_match({"league": "NBA", "game": "some single team",
                                 "bet": "Over 1.5", "game_start": "2026-11-13T01:00:00Z"}, fixtures)
    check("refused", fid is None, fid)
    check("reason names the split failure", "two distinguishable sides" in note, note)

    print("10. the fallback writes nothing, by construction")
    import ast
    import pathlib
    tree = ast.parse(pathlib.Path("clv_fallback.py").read_text())
    writes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == "open" and len(n.args) > 1]
    check("no open(..., 'w') anywhere", not writes, f"{len(writes)} write-mode opens")
    names = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    check("no api() call", "api" not in names, names & {"api"})
    check("no enc() call", "enc" not in names, names & {"enc"})

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all fallback agreement/ambiguity checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
