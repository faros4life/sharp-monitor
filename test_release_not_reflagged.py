#!/usr/bin/env python3
"""
STAGE 1 REGRESSION (Peter, Nov 13 2026): a released row must stay released, and a genuinely
new doubt must still exclude.

The defect this pins down: clv_release_verified cleared fixture_doubt correctly, but
clv_ledger step 5 re-ran identity_check on every pass and re-raised the flag whenever it was
merely absent. identity_check reads espn_filled, teams and the bet's own text - none of which a
release changes - so all 25 released rows were held out again on the very next run with the
identical reason string. The release was a no-op that looked like success, and clv_readout's
own "must be 0" check had been reporting 25 for a day.

Every case below drives the REAL clv_ledger.apply_doubt() against a real fixture cache. None of
them mocks the thing under test.
"""
import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_ledger as cl   # noqa: E402

NOW = datetime(2026, 11, 13, 12, 0, 0, tzinfo=timezone.utc)
BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def fixtures():
    """Two NBA fixtures. The second exists so a row can be pointed at a different one."""
    return {
        "fx1": {"lg": "NBA", "start": "2026-11-10T01:00:00Z",
                "p1": "Charlotte Hornets Charlotte CHA", "p2": "Washington Wizards Washington WAS"},
        "fx2": {"lg": "NBA", "start": "2026-11-10T01:00:00Z",
                "p1": "Orlando Magic Orlando ORL", "p2": "Atlanta Hawks Atlanta ATL"},
    }


def espn_row(fixture="fx1", **kw):
    """A scored, ESPN-filled row whose bet text names only ONE of the two assigned teams.

    That is the exact shape identity_check calls doubtful ("the bet's own text supports 1 of the
    2 assigned teams") and the exact shape of all 25 rows Peter released on Nov 12.
    """
    rec = {"clv": 0.0204, "fixture": fixture,
           "snap": {"league": "NBA", "bet": "Under 228.5", "game": "Charlotte Hornets",
                    "game_start": "2026-11-10T01:00:00Z", "espn_filled": True,
                    "teams": [{"name": "Charlotte Hornets"}, {"name": "Washington Wizards"}]}}
    rec.update(kw)
    return rec


def run(st, rec, passes=1):
    out = []
    for _ in range(passes):
        out.append(cl.apply_doubt(st, rec, NOW))
    return out


def main():
    st = {"fixtures": fixtures()}

    print("1. the defect itself: an unreleased doubtful row is still excluded")
    rec = espn_row()
    iv, iw = cl.identity_check(rec)
    check("identity_check still calls the row doubtful", iv == "doubt", f"got {iv}")
    check("unreleased row is flagged", run(st, rec) == ["flagged"])
    check("flag carries the identity reason", "supports 1 of the 2" in (rec["fixture_doubt"]["why"] or ""),
          rec.get("fixture_doubt"))

    print("2. a released row is NOT reflagged, and stays released across repeated passes")
    rec = espn_row(released_from={"since": "2026-11-12T16:31:00Z", "why": iw, "fixture": "fx1"})
    res = run(st, rec, passes=3)
    check("three ledger passes all leave it released", res == ["released"] * 3, res)
    check("no fixture_doubt written", "fixture_doubt" not in rec, rec.get("fixture_doubt"))
    check("CLV untouched", rec["clv"] == 0.0204, rec.get("clv"))

    print("3. a GENUINELY NEW doubt still excludes a released row")
    # Released for the identity doubt, but the row now also fails the FIXTURE test because its
    # stored fixture is no longer in the cache in a way the matcher accepts.
    rec = espn_row(fixture="fx2", released_from={"since": "x", "why": iw, "fixture": "fx2"})
    fv, fw = cl.fixture_check(st, rec)
    check("fixture_check reports a different doubt", fv == "doubt" and fw != iw, f"{fv} {fw}")
    check("row with a new doubt is flagged", run(st, rec) == ["flagged"], rec.get("fixture_doubt"))
    check("the flag carries the NEW reason, not the released one",
          rec["fixture_doubt"]["why"] == fw, rec["fixture_doubt"])

    print("4. a release does not travel to a different fixture")
    rec = espn_row(fixture="fx1", released_from={"since": "x", "why": iw, "fixture": "fx2"})
    check("release recorded against another fixture does not apply",
          run(st, rec) == ["flagged"], rec.get("fixture_doubt"))

    print("5. legacy released_from (no fixture) is honoured ONCE, then pinned")
    rec = espn_row(released_from={"since": "2026-11-12T16:31:00Z", "why": iw})
    check("legacy record is honoured", run(st, rec) == ["released"])
    check("fixture is pinned into the record", rec["released_from"].get("fixture") == "fx1",
          rec["released_from"])
    check("still released on the next pass under the strict test", run(st, rec) == ["released"])
    # and once pinned, moving the row to another fixture must re-exclude it
    rec["fixture"] = "fx2"
    check("after pinning, a fixture change re-excludes", run(st, rec) == ["flagged"],
          rec.get("fixture_doubt"))

    print("6. a release never forgives a DIFFERENT reason string")
    rec = espn_row(released_from={"since": "x", "why": "some other reason entirely", "fixture": "fx1"})
    check("mismatched reason is not covered", run(st, rec) == ["flagged"], rec.get("fixture_doubt"))

    print("7. clean rows are unaffected and still record their validation")
    clean = {"clv": 0.01, "fixture": "fx1",
             "snap": {"league": "NBA", "bet": "Charlotte Hornets -2.5",
                      "game": "Charlotte Hornets @ Washington Wizards",
                      "game_start": "2026-11-10T01:00:00Z"}}
    fv, _ = cl.fixture_check(st, clean)
    iv2, _ = cl.identity_check(clean)
    check("a non-ESPN row is not doubtful on identity", iv2 == "ok", iv2)
    if fv == "ok":
        check("clean row records fixture_ok", run(st, clean) == ["ok"] and
              (clean.get("fixture_ok") or {}).get("fixture") == "fx1", clean.get("fixture_ok"))
    else:
        print(f"  skip clean-row fixture_ok (fixture_check says {fv} in this cache)")

    print("8. release_covers() is not a blanket pass")
    check("no released_from -> never covered", not cl.release_covers({"fixture": "fx1"}, "why"))
    check("empty released_from -> never covered",
          not cl.release_covers({"released_from": {}, "fixture": "fx1"}, "why"))

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all Stage 1 release/reflag checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
