"""REVIEW ONLY. The call both execution systems make before dispatching an order.

ON THE REVIEW BRANCH, UNMERGED, AND FLAG-GATED OFF EVEN IF MERGED. `EXEC_UNIT_LEDGER` defaults to
"off". With it off, guard_or_refuse() returns None and every caller behaves exactly as it does on
main today - the integration is inert. Nothing is activated by landing this code; activation is a
separate decision with its own plan (see REVIEW_UNIT_EXPOSURE.md).

WHY ONE SHARED HELPER AND NOT TWO IMPLEMENTATIONS. The gap being closed is that two systems kept
their own accounting. Writing the guard twice - once in executor.py, once in the runner - would
recreate the thing it is fixing in a subtler form: two codebases that agree today and drift later.
Both call this, or the budget is not shared.

WHAT A CALLER MUST DO, in this order, with no step skipped:
    g = guard_or_refuse(store, key, leg_id, stake, american, unit, actor)   # reserves, atomically
    if g is REFUSED: do not submit. The reason is on the exception.
    stake = authorize(store, g, stake)        # single use; marks dispatched under compare-and-swap
    ... submit to the venue ...
    record_outcome(store, key, leg_id, venue_status, filled, verified, evidence)

The order matters. The reservation is taken BEFORE submission, and authorization is consumed
BEFORE the venue call, so a crash between authorize and submit leaves the capacity held rather than
free. That is the safe direction to fail: a held reservation blocks a second order until the
outcome is read, whereas a released one would let a duplicate through.

A refusal is never "send a smaller order". The stake that was reserved is the stake that may be
sent, or nothing.
"""
import os
import re

from review_unit_exposure import ExposureUnknown
from review_unit_reservation import ReservationRefused, authorize, reserve

FLAG = "EXEC_UNIT_LEDGER"


def enabled():
    """OFF unless explicitly switched on. A repo variable Peter flips, like every other money
    switch in this system - never a code default that turns itself on at merge."""
    return (os.environ.get(FLAG) or "off").strip().lower() == "on"


def play_key(sport, game, market, side):
    """The canonical identity both systems must agree on, or they are not sharing a budget.

    LANE IS NOT IN IT, deliberately: Lane 1 and R1 betting the same side of the same game are one
    exposure, not two. Venue is not in it either - that is precisely the New Mexico shape, one side
    across ProphetX and Novig.

    NEITHER IS THE LINE (finding 2 of the fifth review). Under 225.5 and Under 226.5 on the same
    side of one game are overlapping exposure, not two budgets; keying on the line would hand each
    its own unit and reproduce the bug one decimal place away. The side is normalised to drop the
    number it carries, so "Under 225.5" and "Under 226.5" collapse to the same key."""
    parts = [str(p).strip().lower() for p in (sport, game, market, _side_only(side))]
    if not all(parts):
        raise ExposureUnknown("incomplete play identity - fail closed")
    return "|".join(parts)


def _side_only(side):
    """'Under 225.5 (-110)' -> 'under'; 'New Mexico Lobos -7.5' -> 'new mexico lobos'.

    Strips the number and price so adjacent lines on one side share a budget."""
    t = re.sub(r"\(.*?\)", " ", str(side or ""))
    t = re.sub(r"[+-]?\d+(?:\.\d+)?", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def key_from_registry(raw):
    """THE identity, from the key every system already carries: derive_key()'s
    SPORT|game|market|side, with or without a lane prefix.

    Nov 23: three callers built the identity three ways and two of them disagreed. The cloud guard
    called play_key(sport, game, p.get("market") or "total", bet); a play carries no "market", so
    every SPREAD and MONEYLINE was keyed as a total with the price words left on the side, while
    the backfill and the Novig runner keyed the same play from its registry key as market "side".
    Totals happened to agree, which is why it was not seen. Existing exposure and new reservations
    for one spread would have sat in two budgets.

    So nobody assembles the four fields by hand any more. The cloud passes derive_key(p), the
    runner passes the IN_KEY it was dispatched with, the backfill passes the stored key, and all
    three come through here. A lane prefix is dropped by ARITY, not from a list, so a lane added
    later cannot quietly start its own budget. Anything else raises: fail closed."""
    parts = str(raw or "").strip().split("|")
    if len(parts) == 5:
        parts = parts[1:]
    if len(parts) != 4 or not all(p.strip() for p in parts):
        raise ExposureUnknown("play key is not sport|game|market|side - fail closed")
    return play_key(*parts)


def actor_for(system, path, book):
    """Who holds a reservation, INCLUDING THE VENUE it is for. The runner may only claim a
    reservation made for Novig; without the venue on the record, a Novig order could ride a
    ProphetX reservation on the same play - which is the overbet this exists to stop."""
    b = str(book or "").strip().lower()
    if not b:
        raise ExposureUnknown("reservation has no venue - fail closed")
    return f"{system}:{path}:{b}"


def guard_or_refuse(store, key, leg_id, stake, american, unit, actor):
    """Reserve capacity, or raise. Returns the Grant the caller must pass to authorize().

    Returns None ONLY when the ledger is switched off, which means "the old behaviour applies".
    It never returns None as a way of saying yes while switched on - with the flag on, the only
    ways out of this function are a Grant or an exception."""
    if not enabled():
        return None
    return reserve(store, key, leg_id, stake, american, unit, actor)


def authorized_stake(store, grant, stake):
    """Consume the reservation and return the stake that may be sent.

    With the ledger off, the stake passes through unchanged - the pre-existing behaviour. With it
    on, a missing grant is a REFUSAL: a caller that skipped guard_or_refuse() cannot submit."""
    if not enabled():
        return stake
    if grant is None:
        raise ReservationRefused("no shared reservation - submission refused")
    return authorize(store, grant, stake)


# The dispatch paths that must call this, in both repositories. Kept here so the list is checkable
# against the source rather than taken on trust; test_review_integration asserts each one.
DISPATCH_PATHS = (
    ("sharp-monitor", "executor.py", "live_order", "shared taker path for every lane"),
    ("sharp-monitor", "executor.py", "live_remainder", "additional venues inside one run"),
    ("sharp-monitor", "executor.py", "rest_bid", "resting path"),
    ("novig-runner", "novig_live_order.py", "place", "the home runner's own send"),
)
