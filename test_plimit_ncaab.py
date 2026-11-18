"""NCAAB in the Pinnacle-limit read (Peter, Nov 18).

THE DEFECT. plimit_level.pin_limit_at did `sid = cl.SPORT[lg]`, and cl.SPORT has no NCAAB. The KeyError
was caught by plimit_tag's `except Exception` and turned into the literal reason string
"KeyError: 'NCAAB'", which is what 7 rows of the CLV ledger's P-limit section printed instead of a
limit. Same root cause as the 17 Nov clv_obs_audit.classify correction (SPORT -> SCORE_SPORT), which had
filed 29 of R1's 47 plays as LEAGUE_NOT_COVERED.

NCAAB is genuinely readable here: SCORE_SPORT maps it to basketball's sport id 11, the same id as NBA,
and ML_MARKET[11] exists. So this restores a real read rather than prettifying an error.

SEPARATE POINT the second test defends: a limit that IS read but has no frozen Item 56 cut must say so.
It used to fall into plim_stats' bucket as "not tried", which is false - it was tried and it worked. No
NCAAB median is invented: freezing one is a decision and a FIT window, not a side effect of a report.
"""
import clv_ledger as cl
import plimit_level as pl


def test_score_sport_covers_ncaab_and_sport_does_not():
    """The asymmetry that caused it, pinned so the two maps are not confused again."""
    assert "NCAAB" not in cl.SPORT
    assert cl.SCORE_SPORT.get("NCAAB") == 11
    assert cl.SCORE_SPORT.get("NBA") == 11, "NCAAB must share basketball's id, not get one of its own"
    assert cl.ML_MARKET.get(11), "sport 11 must have a moneyline market, or NCAAB is not readable here"


def test_pin_limit_at_does_not_raise_on_ncaab():
    """The regression itself: NCAAB must not raise, and must not return a KeyError reason string."""
    try:
        got = pl.pin_limit_at({"bet": "Under 147.5"}, {}, {}, {}, cl.tp("2026-11-14T00:00:00Z"), "NCAAB")
    except KeyError as e:
        raise AssertionError(f"NCAAB still raises KeyError: {e}")
    assert isinstance(got, tuple) and len(got) == 2


def test_unknown_league_returns_cleanly_rather_than_raising():
    """A league nobody has mapped is a missing read, never an exception string in a report."""
    try:
        got = pl.pin_limit_at({"bet": "Under 147.5"}, {}, {}, {}, cl.tp("2026-11-14T00:00:00Z"), "KBO")
    except KeyError as e:
        raise AssertionError(f"unknown league raises instead of returning: {e}")
    assert got == (None, None)


def test_plimit_tag_reports_no_keyerror_for_ncaab():
    """End to end through the wrapper that writes the report's reason string."""
    out = cl.plimit_tag({"bet": "Under 147.5"}, {}, {}, {}, "NCAAB", cl.tp("2026-11-14T00:00:00Z"))
    assert out is None or "KeyError" not in str(out.get("why") or ""), out


def test_a_read_with_no_frozen_cut_is_not_reported_as_not_tried():
    """NCAAB has no Item 56 cut, so a successful read cannot be grouped - and must say why."""
    assert ("NCAAB", "total") not in cl.PLIM_CUT
    assert "NCAAB" not in cl.PLIM_LEAGUE

    real = pl.pin_limit_at
    try:
        pl.pin_limit_at = lambda *a, **k: (1234.0, "own line")
        out = cl.plimit_tag({"bet": "Under 147.5"}, {}, {}, {}, "NCAAB", cl.tp("2026-11-14T00:00:00Z"))
    finally:
        pl.pin_limit_at = real

    assert out["limit"] == 1234, out
    assert out["grp"] is None, "no frozen cut means no LOW/HIGH group"
    assert out["cut"] is None, "a cut must never be invented for an unfrozen league"
    assert out.get("why"), "a successful read with no cut must carry a reason, or it reads as 'not tried'"
    assert "not grouped" in out["why"] and "NCAAB" in out["why"], out["why"]


def test_a_league_with_a_frozen_cut_still_groups():
    """The working path is unchanged: NBA totals keep their frozen cut and their LOW/HIGH split."""
    assert cl.PLIM_CUT[("NBA", "total")] == 1808
    real = pl.pin_limit_at
    try:
        pl.pin_limit_at = lambda *a, **k: (1000.0, "own line")
        low = cl.plimit_tag({"bet": "Under 220.5"}, {}, {}, {}, "NBA", cl.tp("2026-11-14T00:00:00Z"))
        pl.pin_limit_at = lambda *a, **k: (5000.0, "own line")
        high = cl.plimit_tag({"bet": "Under 220.5"}, {}, {}, {}, "NBA", cl.tp("2026-11-14T00:00:00Z"))
    finally:
        pl.pin_limit_at = real
    assert low["grp"] == "LOW" and low["cut"] == 1808, low
    assert high["grp"] == "HIGH", high
    assert not low.get("why") and not high.get("why"), "a grouped row needs no reason"
