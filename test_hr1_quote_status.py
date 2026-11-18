"""HR1 quote verification (Peter, 18 Nov 2026) - agree_rules.hr1_quote_status.

THE INCIDENT. HR1's first live push told Peter to risk a real stake on Hard Rock Under 132.5 (-110).
Two minutes later Hard Rock's board showed a main total of 129.5 (-105). The play did not exist.

The line/price pairing was ruled out first: each book contributes ONE (point, price) tuple from its own
main total, so they can never be mixed. What separates that alert from the two good ones is cross-book
agreement, on the alert's own stored evidence:

    18 Nov Under 132.5    Hard Rock -110  vs ProphetX -178 on the SAME 132.5   -> 72c
    17 Nov Utah -12.5     Hard Rock -110  vs Kalshi -113 / ProphetX -118       -> 11c
    17 Nov Fordham -11.5  Hard Rock -115  vs Kalshi -108                       ->  1c

The three cases below are the REAL stored rows. They are the regression: the bad one must be blocked and
BOTH good ones must still pass. A gate that blocks everything is as useless as one that passes everything.
"""
import agree_rules as ar

# --- the three real HR1 alerts carrying prices_at_alert, verbatim from alerts.json -------------------
BAD_18NOV = {"kalshi": {"point": 128.5, "price": 104, "after_fee": -103.1},
             "novig": {"point": 129.5, "price": -104, "after_fee": -104},
             "prophetx": {"point": 132.5, "price": -178, "after_fee": -181.6}}
GOOD_UTAH = {"kalshi": {"point": -12.5, "price": -113, "after_fee": -121.2},
             "novig": {"point": -13.5, "price": 108, "after_fee": 108},
             "prophetx": {"point": -12.5, "price": -118, "after_fee": -120.4}}
GOOD_FORDHAM = {"kalshi": {"point": -11.5, "price": -108, "after_fee": -115.8},
                "novig": {"point": -12.5, "price": 106, "after_fee": 106},
                "prophetx": {"point": -12.5, "price": 102, "after_fee": 102}}


# the real Cincinnati row: Hard Rock a FULL POINT better than both other books, on a number nobody shares.
# The first gate dropped this silently; it is exactly the slow line HR1 exists to catch.
CINCINNATI = {"novig": {"point": -28.5, "price": 104, "after_fee": 104},
              "prophetx": {"point": -28.5, "price": -102, "after_fee": -102}}
# the real Chicago St / UIC row: corroborated on the same number, 6c better.
UIC = {"prophetx": {"point": 140.5, "price": -116, "after_fee": -116},
       "novig": {"point": 139.5, "price": -104, "after_fee": -104},
       "kalshi": {"point": 137.5, "price": 117, "after_fee": 117}}


def test_the_incident_is_blocked():
    st, why = ar.hr1_quote_status(132.5, -110, BAD_18NOV)
    assert st == "blocked"
    assert "implausible" in why and "prophetx" in why, why


def test_the_full_point_spread_is_sent_unverified_not_dropped():
    """Cincinnati -27.5: plausible number, no book on it. Must be SENT and labelled, never discarded."""
    st, why = ar.hr1_quote_status(-27.5, -110, CINCINNATI)
    assert st == "unverified", why
    assert "not corroborated" in why and "-28.5" in why, why


def test_a_corroborated_quote_is_verified():
    assert ar.hr1_quote_status(140.5, -110, UIC) == ("verified", "")


def test_the_three_states_are_distinct():
    """Suspicious and uncorroborated have opposite remedies and must never be one message."""
    got = {ar.hr1_quote_status(132.5, -110, BAD_18NOV)[0],
           ar.hr1_quote_status(-27.5, -110, CINCINNATI)[0],
           ar.hr1_quote_status(140.5, -110, UIC)[0]}
    assert got == {"blocked", "unverified", "verified"}, got


def test_both_good_alerts_still_pass():
    """The gate must not suppress genuinely corroborated quotes - that is the whole point."""
    for pt, af, pa, nm in ((-12.5, -110, GOOD_UTAH, "Utah"), (-11.5, -115, GOOD_FORDHAM, "Fordham")):
        st, why = ar.hr1_quote_status(pt, af, pa)
        assert st == "verified", f"{nm} wrongly {st}: {why}"


def test_edge_is_measured_against_the_best_same_line_book():
    pa = {"prophetx": {"point": 100.5, "after_fee": -150}, "kalshi": {"point": 100.5, "after_fee": -120}}
    assert ar.hr1_quote_status(100.5, -108, pa)[0] == "verified"           # 12c over the BEST (-120), inside 25c
    assert ar.hr1_quote_status(100.5, -90, pa)[0] == "blocked"           # 30c over the best, blocked


def test_boundary_at_the_stated_tolerance():
    pa = {"novig": {"point": 50.5, "after_fee": -135}}
    assert ar.hr1_quote_status(50.5, -110, pa)[0] == "verified"            # exactly 25c
    assert ar.hr1_quote_status(50.5, -109, pa)[0] == "blocked"           # 26c


def test_a_worse_hard_rock_price_is_never_blocked_for_being_worse():
    """Only an implausibly GOOD price is a bad quote. A worse one is just a worse bet."""
    pa = {"novig": {"point": 20.5, "after_fee": -102}}
    assert ar.hr1_quote_status(20.5, -118, pa)[0] == "verified"


def test_line_far_from_the_market_is_blocked():
    pa = {"novig": {"point": 129.5, "after_fee": -104}, "kalshi": {"point": 128.5, "after_fee": -103},
          "prophetx": {"point": 129.5, "after_fee": -105}}
    st, why = ar.hr1_quote_status(132.5, -110, pa)
    assert st == "blocked" and "median" in why, why


def test_line_inside_the_gap_still_passes_when_corroborated():
    pa = {"novig": {"point": 129.5, "after_fee": -104}, "kalshi": {"point": 130.5, "after_fee": -106}}
    assert ar.hr1_quote_status(130.5, -108, pa)[0] == "verified"


def test_no_book_on_our_number_is_sent_unverified():
    """Nothing corroborates the price, but the number is plausible - send it labelled, never drop it."""
    pa = {"novig": {"point": 129.5, "after_fee": -104}, "kalshi": {"point": 129.5, "after_fee": -103}}
    st, why = ar.hr1_quote_status(130.5, -110, pa)
    assert st == "unverified" and "not corroborated" in why, why


def test_fails_safe_on_missing_or_unreadable_input():
    for pa in (None, {}, "nonsense", {"hardrockbet": {"point": 1, "after_fee": -110}}):
        assert ar.hr1_quote_status(132.5, -110, pa)[0] == "blocked", pa
    assert ar.hr1_quote_status(None, -110, BAD_18NOV)[0] == "blocked"
    assert ar.hr1_quote_status(132.5, None, BAD_18NOV)[0] == "blocked"
    assert ar.hr1_quote_status("x", "y", BAD_18NOV)[0] == "blocked"
    assert ar.hr1_quote_status(132.5, -110, {"novig": {"point": None, "after_fee": None}})[0] == "blocked"
    assert ar.hr1_quote_status(132.5, -110, {"novig": "not a dict"})[0] == "blocked"


def test_hard_rock_itself_never_counts_as_its_own_corroboration():
    pa = {"hardrockbet": {"point": 132.5, "after_fee": -110},
          "hardrockbet_fl": {"point": 132.5, "after_fee": -110}}
    assert ar.hr1_quote_status(132.5, -110, pa)[0] == "blocked"


def test_eligibility_is_untouched_by_verification():
    """hr1() decides what QUALIFIES; hr1_quote_status decides only what is safe to push."""
    a = {"sport": "NCAAB", "book_key": "hardrockbet", "kind": "tot", "bet": "Under ", "top25": False,
         "late": False, "price_after_fee": -110,
         "alert_utc": "2026-11-18T14:30:22Z", "start_utc": "2026-11-19T01:00:00Z"}
    assert ar.hr1(a)[0] is True, "the incident alert still QUALIFIES - it just cannot be verified"
    assert ar.hr1_quote_status(132.5, -110, BAD_18NOV)[0] == "blocked"
