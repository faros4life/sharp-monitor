"""REVIEW ONLY. Atomic per-play unit reservation shared by BOTH execution systems.

NOT WIRED TO ANYTHING. No production path imports this, no order is placed, no venue is contacted,
no setting is read or written. It is a design artifact on draft PR #10, for review.

WHY A SECOND MODULE. review_unit_exposure.py computes how much of a unit is already spent. That is
a CALCULATION, and its own docstring says so: it "DOES NOT provide atomic locking or authorize a new
order". Two runners can each compute the same correct answer at the same moment and both proceed.
This module is the missing half - the protocol that makes one of them lose.

WHAT IT IS NOT. These are SOURCE-REVIEW findings about a gap in control flow. Nothing here is
evidence that a live exploit occurred. The New Mexico -7.5 position on Nov 20 ($348.20 on one side
across ProphetX and Novig, 1.49 R1 units) has the SHAPE this would prevent; proving it came through
this path needs private registry rows and venue fills that no one has reconciled yet.

REQUIREMENTS (Peter, Nov 22): one authoritative per-play budget across both systems; reserve
atomically before submission; open orders stay reserved until status is VERIFIED; unknown exposure
blocks; a failed reservation cannot be bypassed; nothing cancels or shrinks a venue order.

FOUR DEFECTS FOUND IN REVIEW OF THE FIRST DRAFT (head 6f182a2ee), all fixed here:
  1. The idempotent leg_id path returned a Grant for the NEWLY REQUESTED stake without checking it
     against the recorded leg. A retry with a larger stake, different odds, different unit or a
     different actor was granted on identity alone. Now every field must match or it refuses.
  2. Grant was publicly constructible and authorize() checked only isinstance and amount, so the
     "cannot be forged" claim was wrong. authorize() now REQUIRES the store and re-verifies the leg
     against it. The claim is corrected below: enforcement comes from every send path consulting the
     authoritative store, never from trusting an object it was handed.
  3. remaining() took the CALLER'S lane unit, so one play holding a Lane 1 $300 leg and an R1 $200
     leg had no coherent 1.0 budget. Each leg now carries its OWN unit and contributes its own
     fraction, which preserves per-lane sizing while making the shared budget add up.
  4. record_outcome() accepted any status string, non-finite or negative fills, and
     terminal_verified=True with no proof, and allowed a terminal leg to regress. All now validated.

THE STORE IS INJECTED. This module performs NO I/O. `store` must offer:
    read()                 -> (state_dict, version)   version opaque; None means UNREADABLE
    write(state, version)  -> True on success, False when the version no longer matches
It must be reachable and writable by BOTH runners, or requirement 1 is not met whatever this code
does. Choosing that store is an infrastructure decision and is still open.

FAIL CLOSED EVERYWHERE. Unreadable store, unknown leg state, missing identity, unreadable price, a
mismatched retry, or a lost compare-and-swap all REFUSE. Refusal is never "proceed with less".
"""
import math

from review_unit_exposure import ExposureUnknown, fraction, maximum_stake

BUDGET = 1.0
EPS = 1e-9

# Mirrors review_unit_exposure.remaining()'s vocabulary deliberately - one vocabulary, not two.
IGNORED = ("refused", "void", "dry")
LIVE_STATES = ("open", "placed", "partially_filled")
TERMINAL_STATES = ("filled", "settled", "canceled", "cancelled", "expired")
KNOWN_STATES = IGNORED + LIVE_STATES + TERMINAL_STATES


class ReservationRefused(Exception):
    """Read succeeded and the answer is no. The caller must not submit. Never a partial go-ahead."""


class Grant:
    """A reservation receipt. NOT a capability on its own - see authorize().

    Finding 2 was that this being constructible made "unforgeable" false. It is not a bearer token
    and nothing trusts it by itself: authorize() re-reads the shared store and checks that the leg
    is really recorded there with these values. A Grant a caller builds by hand fails that check.
    The real enforcement is that EVERY send path in BOTH repositories must call authorize() with the
    authoritative store - a property of the wiring, which does not exist yet."""

    __slots__ = ("key", "leg_id", "units", "max_stake", "american", "unit", "actor", "version")

    def __init__(self, key, leg_id, units, max_stake, american, unit, actor, version):
        self.key, self.leg_id, self.units, self.max_stake = key, leg_id, units, max_stake
        self.american, self.unit, self.actor, self.version = american, unit, actor, version

    def __repr__(self):
        return (f"Grant({self.key}, leg={self.leg_id}, units={self.units:.4f}, "
                f"max_stake={self.max_stake:.2f}, unit={self.unit:g})")


def _num(v, label):
    if isinstance(v, bool):
        raise ExposureUnknown(label)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ExposureUnknown(label) from None
    if not math.isfinite(x) or x < 0:
        raise ExposureUnknown(label)
    return x


def _legs(state, key):
    return [l for l in (state.get("legs") or []) if l.get("key") == key]


def leg_fraction(leg):
    """One leg's share of the budget, at ITS OWN lane unit. Finding 3.

    A Lane 1 leg is $300-based and an R1 leg is $200-based. Measuring both against whichever unit
    the current caller happens to hold produces a budget that does not add up. Per-lane sizing is
    preserved exactly - only the accounting is made common."""
    status = str(leg.get("status") or "").lower()
    if status not in KNOWN_STATES:
        raise ExposureUnknown("unknown order state")
    if status in IGNORED:
        return 0.0
    if not (leg.get("order_id") or leg.get("leg_id")):
        raise ExposureUnknown("missing order identity")
    ask = _num(leg.get("asked_stake"), "asked")
    raw = leg.get("filled_stake")
    filled = _num(raw, "filled") if raw is not None else None
    if filled is not None and filled > ask + 0.011:
        raise ExposureUnknown("fill above ask")
    terminal = status in TERMINAL_STATES
    committed = filled if (terminal and leg.get("terminal_verified") is True
                           and filled is not None) else ask
    return fraction(committed, leg.get("american"), _num(leg.get("unit"), "leg unit"))


def remaining_mixed(legs, key):
    """Budget left for `key`, each leg counted at its own unit. Worst case per order id."""
    if not key:
        raise ExposureUnknown("missing canonical key")
    by_order = {}
    for leg in legs:
        if leg.get("key") != key:
            continue
        used = leg_fraction(leg)
        oid = str(leg.get("order_id") or leg.get("leg_id"))
        by_order[oid] = max(used, by_order.get(oid, 0.0))
    return max(0.0, BUDGET - sum(by_order.values()))


def available(store, key):
    """Units still free, or raise. Reads only; grants nothing.

    Open and unknown-fill orders hold their FULL asked exposure - requirement 3 - because an order
    whose outcome is unverified may still fill in full."""
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    return remaining_mixed(_legs(got[0], key), key)


def _same_request(leg, stake, american, unit, actor):
    """Finding 1: identity alone must not grant. Every field of the retry must match the record."""
    try:
        return (abs(_num(leg.get("asked_stake"), "asked") - float(stake)) <= 0.011
                and float(leg.get("american")) == float(american)
                and abs(_num(leg.get("unit"), "unit") - float(unit)) <= EPS
                and str(leg.get("actor") or "") == str(actor or ""))
    except (TypeError, ValueError, ExposureUnknown):
        return False


def reserve(store, key, leg_id, stake, american, unit, actor, attempts=3):
    """Atomically reserve capacity for ONE leg, BEFORE submission. Returns a Grant or raises.

    The compare-and-swap is the point: between reading and writing, another runner may have
    reserved. A lost write never proceeds on the stale answer - it re-reads, and if it still cannot
    win, it REFUSES."""
    if not key or not leg_id:
        raise ExposureUnknown("missing canonical key or leg identity")
    u = _num(unit, "unit")
    want = fraction(stake, american, u)
    if want <= 0:
        raise ExposureUnknown("non-positive reservation")
    for _ in range(max(1, attempts)):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise ExposureUnknown("reservation store unreadable - fail closed")
        state, version = got
        legs = _legs(state, key)
        prior = next((l for l in legs if str(l.get("leg_id")) == str(leg_id)), None)
        if prior is not None:
            # Finding 1. A repeat of the SAME intent is idempotent; anything else is refused.
            if not _same_request(prior, stake, american, u, actor):
                raise ReservationRefused(
                    f"leg {leg_id} is already reserved with different terms - refused, not re-granted")
            return Grant(key, leg_id, leg_fraction(prior), _num(prior.get("asked_stake"), "asked"),
                         american, u, actor, version)
        free = remaining_mixed(legs, key)
        if want > free + EPS:
            raise ReservationRefused(
                f"per-play unit budget: {free:.4f}u free, {want:.4f}u requested for {key}")
        new = dict(state)
        new["legs"] = list(state.get("legs") or []) + [{
            "key": key, "leg_id": str(leg_id), "status": "open", "asked_stake": round(float(stake), 2),
            "american": american, "unit": u, "order_id": str(leg_id), "actor": actor}]
        if store.write(new, version):
            return Grant(key, leg_id, want, round(float(stake), 2), american, u, actor, version)
    raise ReservationRefused("could not win the reservation write - another runner holds it")


def authorize(store, grant, stake):
    """Convert a stake into permission, by re-checking the AUTHORITATIVE STORE. Finding 2.

    A Grant is a receipt, not a bearer token. This re-reads the shared store and refuses unless the
    leg is recorded there with the same actor, stake, odds and unit. A hand-built Grant fails.

    This does NOT make bypass impossible on its own: a runner that never calls authorize() is not
    stopped by authorize(). Enforcement is that every send path in BOTH repositories must call it -
    wiring that does not exist yet and is the main open item on this PR."""
    if not isinstance(grant, Grant):
        raise ReservationRefused("no reservation grant - submission is not authorized")
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    leg = next((l for l in _legs(got[0], grant.key)
                if str(l.get("leg_id")) == str(grant.leg_id)), None)
    if leg is None:
        raise ReservationRefused("grant does not correspond to a reservation in the store")
    if not _same_request(leg, grant.max_stake, grant.american, grant.unit, grant.actor):
        raise ReservationRefused("grant disagrees with the stored reservation - refused")
    s = float(stake)
    if not math.isfinite(s) or s <= 0:
        raise ExposureUnknown("stake unreadable")
    if s > _num(leg.get("asked_stake"), "asked") + 0.011:
        raise ReservationRefused(
            f"stake {s:.2f} exceeds the reserved {leg.get('asked_stake')} - not trimmed, refused")
    return round(s, 2)


def record_outcome(store, key, leg_id, status, filled_stake=None, terminal_verified=False,
                   evidence=None):
    """Update a reserved leg with what the VENUE said. Finding 4: everything is validated.

    Capacity is released only on terminal_verified=True WITH a fill amount AND an explicit evidence
    string - that is, venue proof a human or a reader can point at. Time passing is not evidence.
    A missing fill report is not evidence. A terminal leg cannot regress to a live state, so a
    late or stale callback cannot reopen settled capacity. There is no cancel or shrink path here:
    releasing capacity and cancelling an order are different actions and the second is not
    authorized. A lost compare-and-swap refuses rather than retrying blindly."""
    st = str(status or "").lower()
    if st not in KNOWN_STATES:
        raise ExposureUnknown(f"unknown terminal/live status {status!r} - fail closed")
    if terminal_verified:
        if st not in TERMINAL_STATES:
            raise ExposureUnknown("terminal_verified on a non-terminal status - fail closed")
        if filled_stake is None:
            raise ExposureUnknown("terminal_verified without a fill amount - fail closed")
        if not str(evidence or "").strip():
            raise ExposureUnknown("terminal_verified without venue evidence - fail closed")
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    state, version = got
    legs = list(state.get("legs") or [])
    hit = False
    for i, l in enumerate(legs):
        if l.get("key") == key and str(l.get("leg_id")) == str(leg_id):
            was = str(l.get("status") or "").lower()
            if was in TERMINAL_STATES and l.get("terminal_verified") is True and st in LIVE_STATES:
                raise ReservationRefused(
                    "a verified terminal leg cannot regress to a live state - stale callback refused")
            upd = dict(l, status=st)
            if filled_stake is not None:
                f = _num(filled_stake, "filled")
                if f > _num(l.get("asked_stake"), "asked") + 0.011:
                    raise ExposureUnknown("fill above ask - fail closed")
                upd["filled_stake"] = round(f, 2)
            if terminal_verified:
                upd["terminal_verified"] = True
                upd["evidence"] = str(evidence)[:120]
            legs[i] = upd
            hit = True
            break
    if not hit:
        raise ExposureUnknown("outcome for a leg that was never reserved - fail closed")
    if not store.write(dict(state, legs=legs), version):
        raise ReservationRefused("outcome write lost the compare-and-swap - re-read and retry")
    return True


def cap_for(store, key, american, unit):
    """Largest stake that could be reserved right now. ADVISORY - it grants nothing and can be
    stale by the time it is used, which is exactly why the compare-and-swap exists."""
    return maximum_stake(available(store, key), american, _num(unit, "unit"))
