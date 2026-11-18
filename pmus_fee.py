#!/usr/bin/env python3
"""POLYMARKET US FEES - the single source of truth. Imported by every module that prices this venue.

Why a module of its own (Peter, Nov 18: "Make every module use the same verified fee calculation"):
before this, five files each held their own 0.06 literal and drifted independently. The reason they
held literals rather than importing was deliberate and still valid - sharp_monitor runs live every
five minutes and "a new import is a new way for it to fail" - so this module imports NOTHING from
this repo and nothing outside the standard library. It is as safe to import as a literal is to type,
and unlike the literal there is exactly one of it.

THIS IS POLYMARKET US ONLY (gateway.polymarket.us, the venue we can bet). The global CLOB
(`polymarket` / `polymarket.global`, 0.03) is a different venue with a different API and fee and is
NOT bettable from the US; liquidity_monitor.TAKER_COEF and book_check.TAKER_COEF price THAT book and
must not be routed through here. Confusing the two mis-prices the global book, which breaks history.

Two models, selected by the PMUS_FEE_MODEL repo variable:

  legacy   - the pre-Nov-14 assumptions, byte for byte. THE DEFAULT. Every executed price in the
             ledger was recorded under these, so they are preserved rather than deleted, and old-model
             reporting keeps producing the numbers it always produced.
  schedule - the venue's published schedule effective 12:00 AM ET, Sat Nov 14 2026.

The schedule's shape is unchanged from what this repo has always modelled - fee = COEF x contracts x
p x (1-p), charged ON TOP of the stake - but COEF IS NOT A CONSTANT, which is the whole correction.
0.06 sits below EVERY published taker tier including the cheapest, and the old -0.0125 maker rebate
is better than the venue's TOP tier while being credited at a volume that earns none. Both errors
pointed the same way: they made this venue look better than it is.
"""
import os
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------- the preserved historical assumptions
LEGACY_TAKER = 0.06        # "corrected 6 Nov", from the schedule as it read before Nov 14
LEGACY_MAKER = -0.0125     # a rebate better than the venue's top tier; never earned at our volume

# ---------------------------------------------------------------- the published schedule, Nov 14 2026
# Taker theta is tiered on TRAILING 30-DAY TAKER VOLUME, recomputed daily at 00:00 ET, excluding today.
TAKER_TIERS = ((250_000.0, 0.0695),        # Tier 4  $250k+
               (50_000.0,  0.075),         # Tier 3  $50k - $250k
               (10_000.0,  0.085),         # Tier 2  $10k - $50k
               (0.0,       0.095))         # Tier 1  under $10k
TAKER_UNKNOWN = 0.095                      # tier unestablished -> WORST published tier (Peter, Nov 18)
ONBOARD_TAKER = 0.0695                     # days 1-7 from the account's FIRST FILL, at any volume
ONBOARD_DAYS = 7                           # "Day 1 is the ET calendar day of the account's first filled
                                           # order, maker or taker. There is no hourly proration."
                                           # Days 8-30 use the HIGHER of first-7-day volume x 30/7 and
                                           # the trailing 30 days. That can only RAISE volume and so can
                                           # only LOWER theta, so not modelling it is the safe side.

# The maker rebate does not begin until $10MM of 30-day MAKER volume. Below that the maker side is
# simply FREE - no fee and no rebate - so a resting price equals its screen price and never beats it.
MAKER_TIERS = ((200_000_000.0, -0.0104),   # Tier 4  $200MM+
               (50_000_000.0,  -0.0070),   # Tier 3  $50MM - $200MM
               (10_000_000.0,  -0.0035),   # Tier 2  $10MM - $50MM
               (0.0,            0.0))      # Tier 1  under $10MM: NO REBATE
MAKER_UNKNOWN = 0.0                        # never credit an unverified rebate (Peter, Nov 18)

# ELIGIBILITY FREEZE (Peter, Nov 6), kept as a FLOOR. Correcting a fee DOWNWARD makes every net price
# better, so a raw price that used to miss the -130 cap or the alert threshold could start clearing it
# - the correction CREATING a bet, which Peter prohibited. The gate therefore prices this venue at the
# stricter of this floor and whatever the active model charges; see gate_coef().
QUAL_FLOOR = 0.0695

# "legacy" or "schedule". Peter flips repo variables, so the default is legacy and activation is a
# deliberate act rather than a side effect of deploying this code.
MODEL = (os.environ.get("PMUS_FEE_MODEL", "") or "legacy").strip().lower()

ET = timezone(timedelta(hours=-5))


def _tier(tiers, vol):
    """Coefficient for a volume, from a table ordered high floor -> low. None volume -> None."""
    if vol is None:
        return None
    for floor, c in tiers:
        if float(vol) >= floor:
            return c
    return tiers[-1][1]


def onboarding(first_fill=None, asof=None):
    """(in_window, day_number_or_None) for the 7-day boost, counted in ET CALENDAR days.

    An UNKNOWN first fill is not onboarding. The boost is the cheap side, so assuming it is the
    optimistic error, and this module never makes the optimistic error. A future date is not a fill.
    """
    if not first_fill:
        return False, None
    d0 = first_fill.date() if hasattr(first_fill, "date") else first_fill
    d1 = (asof or datetime.now(timezone.utc)).astimezone(ET).date()
    day = (d1 - d0).days + 1               # the day of the first fill is Day 1
    if day < 1:
        return False, None
    return day <= ONBOARD_DAYS, day


def coef(maker=False, taker_vol_30d=None, maker_vol_30d=None, first_fill=None, asof=None, model=None):
    """(coefficient, why) for Polymarket US. `why` names the branch that produced the number.

    Returning the reason beside the number is deliberate: a bare 0.095 cannot distinguish "Tier 1,
    measured" from "tier unknown, assumed", and those two have different remedies even though they
    share a value today. Collapsing states that need opposite fixes is how the last four bugs hid.
    """
    m = (model or MODEL)
    if m != "schedule":
        return (LEGACY_MAKER if maker else LEGACY_TAKER), f"{m}: preserved pre-Nov-14 assumption"
    if maker:
        c = _tier(MAKER_TIERS, maker_vol_30d)
        if c is None:
            return MAKER_UNKNOWN, "maker: volume unverified -> no rebate credited"
        return c, ("maker: no rebate below $10MM 30-day maker volume" if c == 0.0
                   else "maker: rebate tier from verified 30-day maker volume")
    inw, day = onboarding(first_fill, asof)
    if inw:
        return ONBOARD_TAKER, f"taker: onboarding day {day} of {ONBOARD_DAYS}"
    c = _tier(TAKER_TIERS, taker_vol_30d)
    if c is None:
        return TAKER_UNKNOWN, "taker: tier unestablished -> worst published tier"
    return c, "taker: tier from verified trailing 30-day taker volume"


def taker(**kw):
    """The active taker coefficient. Every module's PMUS fee constant resolves through this."""
    return coef(maker=False, **kw)[0]


def maker(**kw):
    """The active maker coefficient. Zero unless rebate eligibility is proven."""
    return coef(maker=True, **kw)[0]


def gate_coef(**kw):
    """The coefficient the ELIGIBILITY GATE must price with: the stricter of the Nov 6 freeze and the
    active model's taker rate.

    Peter, Nov 18: "Verify the final execution eligibility gate cannot accept a trade using a fee
    below the applicable conservative rate." A fixed 0.0695 floor satisfied that while the model
    charged 0.06, and stops satisfying it the moment the applicable rate is 0.095 - at which point a
    gate still priced at 0.0695 would be the LENIENT one. max() is correct in both regimes and needs
    no revisiting when a tier is later verified.
    """
    return max(QUAL_FLOOR, taker(**kw))
