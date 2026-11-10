#!/usr/bin/env python3
"""OFFLINE REPORTING HELPERS from the Nov 10 CLV forensic audit. Pure functions: no network, no
credits, no state, no live imports. Nothing here is wired into any live or scheduled path; it exists so
the corrected rules are written down once and regression-tested (test_clv_audit_regress.py) before
any script is migrated onto them. Original reports and thresholds are untouched.

Rules encoded (each maps to an issue in the audit register):
  B  A stored price_after_fee is ALREADY net. It must never go through clv_std.net_dec again.
  A  A venue's own last pregame price is Exchange Self-Close Movement, never Pinnacle CLV.
  C  A Pinnacle close only counts if close_verified(how) AND its tick is fresh enough.
"""
import clv_ledger as cl
import clv_std as cs

STORED_NET = "net"      # price already after the venue's fee (sharp_monitor price_after_fee)
STORED_RAW = "raw"      # displayed quote, fee still to be taken


def entry_net_dec(book, american, basis):
    """Net decimal for a stored American price. basis says whether the fee is already inside it."""
    if american is None:
        return None
    dec = cl.am_to_dec(american)
    if basis == STORED_NET:
        cs.canon(book)                 # still refuse an unknown venue, but add no fee
        return dec
    if basis == STORED_RAW:
        return cs.net_dec(book, dec)
    raise ValueError(f"basis must be {STORED_NET!r} or {STORED_RAW!r}, got {basis!r}")


def pin_clv(pin_close_prob, net_decimal):
    """The one formula. None if either input is missing."""
    if pin_close_prob is None or net_decimal is None:
        return None
    return round(100.0 * (float(pin_close_prob) * float(net_decimal) - 1.0), 3)


def self_close_move_cents(price, close_price):
    """Exchange Self-Close Movement in probability cents. Deliberately NOT named CLV."""
    if price is None or close_price is None:
        return None
    return round(100.0 * (close_price - price), 3)


def pin_close_usable(close, max_age_min=None):
    """close is the dict clv_ledger.close_for returns. Verified same-line AND (optionally) fresh."""
    if not close or not cs.close_verified(close.get("how")):
        return False
    if max_age_min is not None and (close.get("age_min") is None or close["age_min"] > max_age_min):
        return False
    return True
