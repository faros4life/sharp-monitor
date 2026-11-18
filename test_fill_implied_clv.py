"""FILL-IMPLIED CLV (Peter, Nov 18) - live_ledger.leg_clv_pct.

The field exists so the reports can show the play priced at what the venues actually FILLED, beside the
certified clv_report basis and never blended into it.

The defect these tests exist to catch is the fee being applied twice. live_ledger builds `am_net` through
net_dec, so it is already after-fee; sc.std_clv applies net_dec again. Feeding am_net to std_clv therefore
charges a commission venue twice and understates it. leg_clv_pct must price each leg at its RAW fill price
with its own venue's fee, exactly once.
"""
import clv_scorecard as sc
import live_ledger as ll


def test_no_certified_close_returns_none():
    """A line-move-adjusted close is not certified, so there is no fill-implied number to report."""
    assert ll.leg_clv_pct(None, [{"am": -110, "book": "novig", "w": 100.0}]) == (None, [])


def test_no_legs_returns_none():
    assert ll.leg_clv_pct(0.52, []) == (None, [])
    assert ll.leg_clv_pct(0.52, None) == (None, [])


def test_single_leg_matches_std_clv_exactly():
    """One leg must be the standard basis applied to the fill price - no extra adjustment of our own."""
    legs = [{"am": -106, "book": "novig", "w": 100.0}]
    mean, out = ll.leg_clv_pct(0.5726, legs)
    assert mean == round(sc.std_clv(0.5726, -106, "novig"), 2)
    assert len(out) == 1 and out[0]["book"] == "novig" and out[0]["am"] == -106


def test_fee_applied_exactly_once_on_a_commission_venue():
    """The double-charge trap. On a venue with a fee, pricing the RAW fill must differ from pricing a
    price that has already been netted - and leg_clv_pct must do the former."""
    cp, am = 0.55, -110
    raw = sc.std_clv(cp, am, "kalshi")
    assert raw is not None, "kalshi must be priceable, or this test proves nothing"
    # what a double-charge would look like: net the price first, then let std_clv net it again
    netted_dec = ll.net_dec("kalshi", sc.cl.am_to_dec(am))
    double = sc.std_clv(cp, ll.am_of(netted_dec), "kalshi")
    assert double is not None
    assert abs(raw - double) > 0.01, "fee model is flat here; pick a venue with a real fee"
    mean, _ = ll.leg_clv_pct(cp, [{"am": am, "book": "kalshi", "w": 100.0}])
    assert mean == round(raw, 2), "leg_clv_pct must price the raw fill, charging the fee once"
    assert mean != round(double, 2)


def test_zero_fee_venue_unaffected_by_the_trap():
    """On Novig the two are identical, which is why the defect would have hidden there."""
    cp, am = 0.52, -105
    raw = sc.std_clv(cp, am, "novig")
    mean, _ = ll.leg_clv_pct(cp, [{"am": am, "book": "novig", "w": 50.0}])
    assert mean == round(raw, 2)


def test_stake_weighted_not_simple_mean():
    """A big leg must move the number more than a small one."""
    cp = 0.52
    legs = [{"am": -120, "book": "novig", "w": 900.0}, {"am": +100, "book": "novig", "w": 100.0}]
    mean, out = ll.leg_clv_pct(cp, legs)
    a = sc.std_clv(cp, -120, "novig")
    b = sc.std_clv(cp, +100, "novig")
    assert mean == round((a * 900.0 + b * 100.0) / 1000.0, 2)
    assert mean != round((a + b) / 2, 2), "weighting must not collapse to a simple mean"
    assert len(out) == 2


def test_equal_weight_when_no_leg_carries_a_stake():
    """A play is never dropped for want of a weight."""
    cp = 0.52
    legs = [{"am": -120, "book": "novig", "w": 0.0}, {"am": +100, "book": "novig", "w": 0.0}]
    mean, out = ll.leg_clv_pct(cp, legs)
    a = sc.std_clv(cp, -120, "novig")
    b = sc.std_clv(cp, +100, "novig")
    assert mean == round((a + b) / 2, 2)
    assert len(out) == 2


def test_mixed_venue_legs_keep_their_own_fee_and_are_reported_separately():
    """The leg-level venue economics Peter asked for: same fill price, different venue, different CLV."""
    cp, am = 0.55, -110
    legs = [{"am": am, "book": "novig", "w": 100.0}, {"am": am, "book": "kalshi", "w": 100.0}]
    mean, out = ll.leg_clv_pct(cp, legs)
    by = {l["book"]: l["clv"] for l in out}
    assert set(by) == {"novig", "kalshi"}
    assert by["novig"] == round(sc.std_clv(cp, am, "novig"), 2)
    assert by["kalshi"] == round(sc.std_clv(cp, am, "kalshi"), 2)
    assert by["novig"] != by["kalshi"], "a fee venue must not price the same as a zero-fee one"
    assert mean == round((by["novig"] * 100.0 + by["kalshi"] * 100.0) / 200.0, 2)


def test_unpriceable_leg_is_skipped_not_counted_as_zero():
    """A leg with no price must not be scored 0% and drag the mean toward nothing."""
    cp = 0.55
    legs = [{"am": -110, "book": "novig", "w": 100.0}, {"am": None, "book": "novig", "w": 100.0}]
    mean, out = ll.leg_clv_pct(cp, legs)
    assert len(out) == 1
    assert mean == round(sc.std_clv(cp, -110, "novig"), 2)


def test_output_carries_no_stakes_or_dollars():
    """Public-repo rule: percentages and prices only - never a stake or a balance."""
    _, out = ll.leg_clv_pct(0.55, [{"am": -110, "book": "novig", "w": 1234.56}])
    assert set(out[0]) == {"book", "am", "clv"}
    assert 1234.56 not in out[0].values()
