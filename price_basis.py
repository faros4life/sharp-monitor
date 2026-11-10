#!/usr/bin/env python3
"""RAW vs NET PRICE CONTRACT (CLV forensic audit, 10 Nov 2026). Pure, stdlib + clv_std. No network.

The defect this prevents: clv_scorecard.py took `price_after_fee` (already net of the venue's fee) and passed
it to clv_std.net_dec(), which takes the fee off again. Kalshi -2.98 pt, ProphetX -0.91 pt too negative.
The cause was that nothing in a stored price said which kind it was.

THE CONTRACT
  RAW  a displayed quote. The venue's fee has NOT been taken. clv_std.net_dec() applies it, exactly once.
  NET  a price already after the venue's fee. It is used as is; applying a fee again is a bug.
Every stored field a CLV script reads is declared below. An undeclared field raises: it must be classified
before it can reach a CLV figure. Callers hold a Price (book, american, basis), never a bare number.
"""
from typing import NamedTuple

import clv_ledger as cl
import clv_std as cs

RAW, NET = "raw", "net"

# field name -> basis. Evidence: sharp_monitor.py:1290,1330 builds price_after_fee = round(net(price, book));
# executor.py:2053-2054 stores alert/fill *_after_fee; liquidity rows carry the displayed quote in
# price_american; executed fills for money-basis venues are NET by construction (executed_clv.BASIS).
FIELD_BASIS = {
    "price": RAW, "fade_price": RAW, "price_american": RAW, "best_price_american": RAW,
    "price_after_fee": NET, "fade_price_after_fee": NET, "alert_price_after_fee": NET,
    "fill_price_after_fee": NET, "live_px_price_after_fee": NET, "american_after_fee": NET,
}


class Price(NamedTuple):
    book: str
    american: float
    basis: str


class UndeclaredField(KeyError):
    """A stored field with no declared basis tried to reach a CLV figure."""


def price_from_row(row, field, book):
    if field not in FIELD_BASIS:
        raise UndeclaredField(f"{field!r} has no declared RAW/NET basis in price_basis.FIELD_BASIS")
    v = row.get(field)
    return None if v is None else Price(cs.canon(book), float(v), FIELD_BASIS[field])


def best_price(row, book, *fields):
    """First present field, in the order given, as a Price. Mixed bases are fine: each carries its own."""
    for f in fields:
        p = price_from_row(row, f, book)
        if p is not None:
            return p
    return None


def net_decimal(p, league=None, live=False, maker=False):
    """Net decimal. The fee is taken here iff p is RAW, so it can never be taken twice."""
    if p is None:
        return None
    dec = cl.am_to_dec(p.american)
    if p.basis == NET:
        return dec
    if p.basis == RAW:
        return cs.net_dec(p.book, dec, maker=maker, league=league, live=live)
    raise ValueError(f"basis must be {RAW!r} or {NET!r}, got {p.basis!r}")


def pin_clv(pin_close_prob, p, **kw):
    """The one formula, over a Price. Only a Pinnacle no-vig close belongs in pin_close_prob."""
    nd = net_decimal(p, **kw)
    if nd is None or pin_close_prob is None:
        return None
    return 100.0 * (float(pin_close_prob) * nd - 1.0)
