"""game_start for Kalshi / Polymarket US rows (Peter, Nov 18).

THE DEFECT. clv_ledger never attempts a row with no game_start ("no game_start on the row - never
attempted, not failed"), which is correct: a closing line cannot be read without knowing when the game
started. 353 rows sat there permanently against a scored basis of 149 selections.

WHY THOSE TWO VENUES. Novig's settled row carries the SAME id as its open row, so it merges onto it and
inherits game_start for free. ProphetX sets the field on its own row (the Nov 12 fix). Kalshi and
Polymarket US mint a settled row under a DIFFERENT id (`ks|TK|settled` vs `ks|TK|yes`), so the start the
open row knew is lost.

THE RULE THESE TESTS DEFEND: a start time is only ever taken from a field that means "when the game
starts", or inherited from the same venue's own row for the same market. Never from a date, a slug, a
settle time or a market expiry - each of those would invent a time of day, and a wrong start pins the
wrong closing tick and corrupts the no-look-ahead basis.
"""
import tracker_build as tb


# --------------------------------------------------------------- venue_start_iso: real start fields only
def test_kalshi_start_fields_are_read():
    for f in ("occurrence_datetime", "event_start_time", "game_start_time"):
        got = tb.venue_start_iso({f: "2026-11-17T23:30:00Z"}.get)
        assert got, f"{f} must be read as a start"
        assert "2026-11-17" in got


def test_polymarket_gamestarttime_is_read():
    got = tb.venue_start_iso({"gameStartTime": "2026-11-17T23:30:00Z"}.get)
    assert got and "2026-11-17" in got


def test_no_start_field_returns_none_and_sets_nothing():
    assert tb.venue_start_iso({}.get) is None
    assert tb.venue_start_iso({"title": "Jazz at Clippers"}.get) is None


def test_a_date_is_never_a_start():
    """ps._date knows the DAY, not the time of day. Using it would invent a kickoff."""
    assert tb.venue_start_iso({"date": "2026-11-17"}.get) is None


def test_expiry_and_settle_time_are_never_a_start():
    """A market expiry is after the game; a settle time is long after it. Either would pin a tick
    past the close, which is worse than not scoring the row at all."""
    assert tb.venue_start_iso({"close_time": "2026-11-18T04:00:00Z"}.get) is None
    assert tb.venue_start_iso({"expected_expiration_time": "2026-11-18T04:00:00Z"}.get) is None
    assert tb.venue_start_iso({"settled_time": "2026-11-18T04:10:00Z"}.get) is None
    assert tb.venue_start_iso({"endDate": "2026-11-18T04:00:00Z"}.get) is None


def test_unparseable_value_returns_none():
    assert tb.venue_start_iso({"gameStartTime": "tomorrow night"}.get) is None
    assert tb.venue_start_iso({"gameStartTime": ""}.get) is None


# --------------------------------------------------------------- market_key: ties settled back to open
def test_market_key_uses_the_venue_market_id():
    assert tb.market_key({"book": "Kalshi", "ticker": "KXNBA-26NOV17LACUTA-UTA"}) == \
        ("Kalshi", "KXNBA-26NOV17LACUTA-UTA")
    assert tb.market_key({"book": "Polymarket US", "slug": "jazz-clippers-u2255"}) == \
        ("Polymarket US", "jazz-clippers-u2255")


def test_market_key_none_without_an_id_or_for_other_venues():
    assert tb.market_key({"book": "Kalshi"}) is None
    assert tb.market_key({"book": "Polymarket US", "slug": ""}) is None
    assert tb.market_key({"book": "Novig", "ticker": "x"}) is None, "Novig inherits by id; not this path"


def test_kalshi_and_polymarket_keys_never_collide():
    assert tb.market_key({"book": "Kalshi", "ticker": "SAME"}) != \
        tb.market_key({"book": "Polymarket US", "slug": "SAME"})


# --------------------------------------------------------------- inherit_game_start
def test_settled_row_inherits_from_its_own_open_row():
    """The defect, end to end: the open row knows the start, the settled row is a different id."""
    bets = {
        "ks|TK1|yes": {"book": "Kalshi", "ticker": "TK1", "game_start": "2026-11-17T23:30:00+00:00"},
        "ks|TK1|settled": {"book": "Kalshi", "ticker": "TK1", "result": "L"},
    }
    ok, missing = tb.inherit_game_start(bets)
    assert (ok, missing) == (1, 0)
    assert bets["ks|TK1|settled"]["game_start"] == "2026-11-17T23:30:00+00:00"
    assert bets["ks|TK1|settled"]["game_start_src"] == "sibling row, same venue market id"


def test_polymarket_settled_row_inherits_by_slug():
    bets = {
        "pm|s1|UNDER": {"book": "Polymarket US", "slug": "s1", "game_start": "2026-11-17T23:30:00+00:00"},
        "pm|t [s1]|UNDER|settled": {"book": "Polymarket US", "slug": "s1", "result": "W"},
    }
    ok, _ = tb.inherit_game_start(bets)
    assert ok == 1
    assert bets["pm|t [s1]|UNDER|settled"]["game_start"] == "2026-11-17T23:30:00+00:00"


def test_never_invents_when_no_sibling_knows_the_start():
    """An irrecoverable row stays unscored and stays counted - it is not given a guessed start."""
    bets = {"ks|TK9|settled": {"book": "Kalshi", "ticker": "TK9", "result": "L",
                               "settled": "2026-11-18T04:10:00+00:00", "date": "2026-11-17"}}
    ok, missing = tb.inherit_game_start(bets)
    assert (ok, missing) == (0, 1)
    assert "game_start" not in bets["ks|TK9|settled"]


def test_does_not_cross_market_ids():
    bets = {
        "ks|TK1|yes": {"book": "Kalshi", "ticker": "TK1", "game_start": "2026-11-17T23:30:00+00:00"},
        "ks|TK2|settled": {"book": "Kalshi", "ticker": "TK2", "result": "L"},
    }
    ok, missing = tb.inherit_game_start(bets)
    assert (ok, missing) == (0, 1)
    assert "game_start" not in bets["ks|TK2|settled"]


def test_does_not_cross_venues_on_a_shared_id():
    bets = {
        "ks|X|yes": {"book": "Kalshi", "ticker": "X", "game_start": "2026-11-17T23:30:00+00:00"},
        "pm|X|UNDER|settled": {"book": "Polymarket US", "slug": "X", "result": "L"},
    }
    ok, _ = tb.inherit_game_start(bets)
    assert ok == 0
    assert "game_start" not in bets["pm|X|UNDER|settled"]


def test_existing_game_start_is_never_overwritten():
    """A start already on the row - from the venue or from a verified scoreboard pin - wins."""
    keep = "2026-11-17T23:30:00+00:00"
    bets = {
        "ks|TK1|yes": {"book": "Kalshi", "ticker": "TK1", "game_start": "2026-11-17T20:00:00+00:00"},
        "ks|TK1|settled": {"book": "Kalshi", "ticker": "TK1", "result": "L", "game_start": keep},
    }
    tb.inherit_game_start(bets)
    assert bets["ks|TK1|settled"]["game_start"] == keep


def test_idempotent():
    bets = {
        "ks|TK1|yes": {"book": "Kalshi", "ticker": "TK1", "game_start": "2026-11-17T23:30:00+00:00"},
        "ks|TK1|settled": {"book": "Kalshi", "ticker": "TK1", "result": "L"},
    }
    first = tb.inherit_game_start(bets)
    second = tb.inherit_game_start(bets)
    assert first == (1, 0) and second == (0, 0), "a second pass must adopt nothing new"


def test_other_venues_are_left_alone():
    bets = {"nv|m1|o1": {"book": "Novig", "result": "W"},
            "px|1": {"book": "ProphetX", "result": "L"}}
    assert tb.inherit_game_start(bets) == (0, 0)
    assert "game_start" not in bets["nv|m1|o1"]
