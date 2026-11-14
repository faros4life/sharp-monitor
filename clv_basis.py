#!/usr/bin/env python3
"""
THE ONE CLV BASIS, versioned (Peter, Nov 14 2026).

Peter: "Create one shared, versioned CLV calculation used by both systems." Until now there were
two. They were never reconciled because the ARITHMETIC already agreed and nobody checked the
INPUTS:

  clv_ledger      matched a fixture, read Pinnacle history, took the no-vig close at the bet's
                  OWN line, and used the row's ACTUAL stake/payout as the after-fee entry.
  clv_scorecard   read a close probability that the alert pipeline had already stored
                  (alerts.json close_fair_prob, liquidity close_price) and used the ALERT's
                  quoted price through the fee model.

The second is the one clv_rootcause.py warns about in its own header: the liquidity population's
stored close is "the TRIGGER VENUE'S OWN last pregame price", which CLV_STANDARD.md section 4
says "stays separate, is never labelled Pinnacle CLV, and is never used as a CLV gate". So the
scorecard's CLV column and the ledger's CLV column were measuring different things under one
name, in opposite directions on some slices.

WHAT IS SHARED HERE: fixture matching, market matching, the exact-line rule, the final valid
two-sided pregame Pinnacle quote, the no-vig conversion, and the CLV arithmetic. ONE
implementation of each.

WHAT IS NOT SHARED, deliberately: the after-fee ENTRY price. Peter: "Actual executable after-fee
entry price APPROPRIATE TO EACH OBSERVATION." A ledger row is a real fill and carries its own
stake and payout; a scorecard sighting is a quoted price at alert time and has no fill. Forcing
one of those onto the other would be the same category error the close suffered from. Both
functions live here so the choice is explicit and auditable at the call site.

NOTHING HERE READS A STORED CLV FIELD, and nothing falls back to a half-point conversion: a
conversion off the main line is a model, not a close, so it returns None with a reason.
"""
import clv_std as cs
import fixture_match as fxm
import tracker_build as tb

# Re-exported so callers can reach it from either module - ONE implementation, in the leaf.
resolve_side = fxm.resolve_side
NON_TEAM = fxm.NON_TEAM

# Bump when any input rule changes - the fixture test, the line rule, the freshness limit, the
# no-vig conversion or the arithmetic. Reports print it so a figure can always be traced to the
# basis that produced it.
BASIS_VERSION = "2026-11-14.1"
BASIS_NOTE = ("Pinnacle verified same-line no-vig close x executable after-fee entry - 1; "
              "exact line only, no half-point conversion; freshness limit applies to both sides")


def clv(close_prob, after_fee_dec):
    """THE arithmetic. One place, so two callers cannot drift.

    Rounded to 4dp ONCE, at the end, from full-precision inputs - rounding the close first moves
    the answer by about a basis point (Dallas Nov 12: -0.64% from full precision, -0.65% from the
    displayed 4dp close).
    """
    if close_prob is None or after_fee_dec is None:
        return None
    try:
        return round(float(close_prob) * float(after_fee_dec) - 1, 4)
    except Exception:
        return None


def after_fee_from_fill(snap, am_to_dec):
    """The after-fee decimal of a REAL fill: what the position actually pays per $1 risked.

    Identical to clv_ledger.eff_dec, which this delegates to via the same precedence: summed
    stake/payout first, then a recorded fill price, then the quoted price with the venue's fee.
    """
    st, pay = tb.num(snap.get("stake")), tb.num(snap.get("to_pay"))
    if st and pay and pay > st:
        return pay / st
    if snap.get("price_af") not in (None, ""):
        return am_to_dec(snap["price_af"])
    if snap.get("price") not in (None, ""):
        d = am_to_dec(snap["price"])
        return 1 + (d - 1) * 0.98 if snap.get("book") == "ProphetX" else d
    return None


def after_fee_from_quote(american, book, am_to_dec, league=None, maker=False):
    """The after-fee decimal of a QUOTED price at a named venue, for an observation with no fill.

    Goes through clv_std.net_dec, so the fee model and its venue table are the registered ones.
    Returns None - never a substitute - when the venue cannot be priced (clv_std refuses
    Polymarket global as NotTradeable, for instance).
    """
    if american is None or not book:
        return None
    try:
        return cs.net_dec(cs.canon(book), am_to_dec(american), maker=maker, league=league)
    except Exception:
        return None


def after_fee_from_cost(cost, book, league=None, maker=False):
    """After-fee decimal for an exchange price quoted as a 0-1 COST to buy the side.

    The liquidity export states its own unit: "price = cost to buy the side when logged (0-1)".
    Passing that through an American-odds converter produces nonsense, which is exactly what the
    first version of the observation audit did - 616 rows were filed UNVERIFIABLE_ENTRY on a unit
    error of mine, not on missing data. A cost of 0.51 is decimal 1/0.51.

    Returns (decimal, None) or (None, why). A venue clv_std refuses - Polymarket GLOBAL is
    NotTradeable from the US - returns None with that reason, which is a real limitation and not
    the same thing as a bad unit.
    """
    c = tb.num(cost)
    if c is None or not (0 < c < 1):
        return None, f"price {cost} is not a 0-1 cost"
    try:
        return cs.net_dec(cs.canon(book), 1.0 / c, maker=maker, league=league), None
    except cs.NotTradeable:
        return None, f"{book} is not tradeable from the US (clv_std refuses to price it)"
    except cs.UnknownVenue:
        return None, f"{book} is not in the venue registry"
    except Exception as ex:
        return None, f"{book} could not be priced ({type(ex).__name__})"


def resolve_fixture(snap, state_fixtures, alt_fixtures, find_fixture, ordered_match, tp):
    """(fid, where, note). The SAME two-step resolution both systems now use.

    Step 1 is clv_ledger.find_fixture against our own cache - unchanged, and still the only step
    that can claim a match on its own terms. Step 2 is the ordered-sides test from
    fixture_match, over the fixtures other jobs in this repo already downloaded. Step 2 runs only
    when step 1 has already failed, so nothing about the existing path changes.
    """
    fid = snap.get("fixture")
    if fid and fid in (state_fixtures or {}):
        return fid, "row", "fixture stored on the row"
    try:
        fid = find_fixture({"fixtures": state_fixtures or {}}, snap)
    except Exception:
        fid = None
    if fid:
        return fid, "state", "clv_ledger.find_fixture"
    fid, note = ordered_match(snap, alt_fixtures or {}, tp)
    return (fid, "alt", note) if fid else (None, None, note)




def pinnacle_no_vig_close(fixture, snap, mkmap, pm, parsed, which_team, two_way, novig_p,
                          sport_map, ml_market, fresh_min, tp):
    """(p_held, evidence) at the bet's OWN line, or (None, why).

    The final valid two-sided PREGAME quote: both sides must have a tick at or before the listed
    start, and the older of the two must be inside the freshness limit. No conversion off a
    different number - that is a model, and a model is not a close.
    """
    start = tp(fixture.get("start")) or tp(snap.get("game_start"))
    if not start:
        return None, "no start time on the fixture or the row"
    # A politics market is not a sports bet and must never be priced against a game's close.
    # ks|SENATEMI-26-R ("Michigan Senate winner?" / "Mike Rogers") was ESPN-filled onto
    # Eastern Michigan v Central Michigan on the shared word "Michigan" and reached this
    # function with league NCAAF. tracker_build.is_politics exists for exactly this and was
    # never consulted here, so the row was one successful side match away from a confidently
    # wrong CLV on a live-money record.
    try:
        if tb.is_politics({"game": snap.get("game"), "bet": snap.get("bet")}):
            return None, "politics market, not a sports bet - never scored against a game close"
    except Exception:
        pass
    pz = parsed(snap)
    if not pz:
        return None, "bet text did not parse"
    sid = sport_map.get(snap.get("league"))
    if sid is None:
        return None, f"league {snap.get('league') or 'unknown'} has no sport id in the basis"
    if pz[0] == "ml":
        mid = ml_market.get(sid)
        tw = two_way(pm, mid, start) if mid else {}
        oc = {v: k for k, v in (mkmap.get(mid, [0, 0, 0, {}])[3]).items()} or {}
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return None, "no two-sided Pinnacle moneyline quote before start"
        age = (start - min(tw[o1][1], tw[o2][1])).total_seconds() / 60
        if age > fresh_min:
            return None, f"moneyline close {age / 60:.0f}h stale"
        side, swhy = resolve_side(fixture, pz[1], snap.get("league"), which_team)
        if not side:
            return None, swhy
        if pz[3]:
            side = "2" if side == "1" else "1"
        p = novig_p(tw[o1][0], tw[o2][0])
        return (p if side == "1" else 1 - p), {"how": "moneyline", "age_min": age,
                                               "dec": (tw[o1][0], tw[o2][0]),
                                               "tick": (tw[o1][1], tw[o2][1])}
    typ = "spreads" if pz[0] == "spread" else "totals"
    want = pz[2]
    side_is_a = (pz[1] == "OVER") if typ == "totals" else None
    if typ == "spreads":
        sd, swhy = resolve_side(fixture, pz[1], snap.get("league"), which_team)
        if not sd:
            return None, swhy
        if pz[3]:
            sd, want = ("2" if sd == "1" else "1"), -want
        want = want if sd == "1" else -want
        side_is_a = (sd == "1")
    for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
        if sp != sid or t != typ or mid not in pm or abs(hcap - want) > 1e-9:
            continue
        tw = two_way(pm, mid, start)
        nm = {v: k for k, v in outs.items()}
        a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a not in tw or b not in tw:
            continue
        age = (start - min(tw[a][1], tw[b][1])).total_seconds() / 60
        if age > fresh_min:
            return None, f"closing tick {age / 60:.0f}h stale (limit {fresh_min / 60:.0f}h)"
        p_a = novig_p(tw[a][0], tw[b][0])
        return (p_a if side_is_a else 1 - p_a), {"how": "own line", "line": want, "age_min": age,
                                                 "dec": (tw[a][0], tw[b][0]),
                                                 "tick": (tw[a][1], tw[b][1]),
                                                 "limit": (tw[a][2], tw[b][2])}
    return None, f"Pinnacle did not hang {want:g} with two sides before start"


def stamp():
    return f"CLV basis {BASIS_VERSION}: {BASIS_NOTE}. Fee model {cs.FEE_MODEL}."
