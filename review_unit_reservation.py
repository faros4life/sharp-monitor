"""REVIEW ONLY. Atomic per-play unit reservation shared by BOTH execution systems.

NOT WIRED TO ANYTHING. No production path imports this, no order is placed, no venue is contacted,
no setting is read or written. It is a design artifact on draft PR #10, for review.

WHY A SECOND MODULE. review_unit_exposure.py computes how much of a unit is already spent. That is
a CALCULATION, and its own docstring says so: it "DOES NOT provide atomic locking or authorize a new
order". Two runners can each compute the same correct answer at the same moment and both proceed.
This module is the missing half - the protocol that makes one of them lose.

THE GAP IT CLOSES (Peter, Nov 22):
  1. Both execution systems use ONE authoritative per-play exposure budget.
  2. Every order reserves capacity ATOMICALLY BEFORE submission.
  3. Open orders stay reserved until their status is VERIFIED.
  4. Unknown exposure BLOCKS additional orders.
  5. A failed reservation CANNOT BE BYPASSED by either runner.
  6. Nothing here cancels or shrinks an existing venue order. There is no cancel path at all.

WHY IT IS NEEDED AT ALL. The guard today lives only on the resting path, counts stake DOLLARS
rather than fractions of a unit, and the shared taker path never calls it. And the second execution
system - faros4life/novig-runner - does not share the count: it has its own registry file, its own
order journal, no reference to committed_risk/claim_submission/submission_held, and its own limits
(MAX_COST 275.0, a bundled LIVE_UNIT of 50.0) that disagree with this repo's 300/200. A guard added
to executor.py alone would pass its tests and still let one play exceed its unit across two venues.
New Mexico -7.5 on Nov 20 is consistent with exactly that: $348.20 on one side across ProphetX and
Novig, 1.49 R1 units.

THE STORE IS INJECTED. This module performs NO I/O. `store` must offer:
    read()                 -> (state_dict, version)   version is opaque; None means UNREADABLE
    write(state, version)  -> True on success, False when the version no longer matches
Anything satisfying that - a durable registry row with a SHA compare-and-swap, which is what
registry.claim_submission already uses - works. The store must be reachable and writable by BOTH
runners, or requirement 1 is not met no matter what this code does. That is an infrastructure
decision, not a code one, and it is called out in REVIEW_UNIT_EXPOSURE.md.

FAIL CLOSED EVERYWHERE. Unreadable store, unknown leg state, missing identity, unreadable price,
or a lost compare-and-swap all REFUSE. Refusal is never "proceed with less"; it is "do not send".
"""
import math

from review_unit_exposure import ExposureUnknown, fraction, maximum_stake, remaining

BUDGET = 1.0            # one unit per play, per the existing convention
EPS = 1e-9


class ReservationRefused(Exception):
    """A reservation was NOT granted. The caller must not submit an order.

    Separate from ExposureUnknown on purpose: this one means the state was read successfully and
    the answer is no. Both are refusals; neither is ever a partial go-ahead."""


class Grant:
    """Proof that capacity was reserved. An order path cannot submit without one.

    This is the mechanism for requirement 5. authorize() is the only thing that converts a stake
    into permission, and it only accepts a Grant that this module issued for that exact leg. A
    runner that skips the reservation has no Grant and therefore cannot produce an authorized
    stake - there is no code path that returns permission without one."""

    __slots__ = ("key", "leg_id", "units", "max_stake", "version", "actor")

    def __init__(self, key, leg_id, units, max_stake, version, actor):
        self.key, self.leg_id, self.units = key, leg_id, units
        self.max_stake, self.version, self.actor = max_stake, version, actor

    def __repr__(self):
        return f"Grant({self.key}, leg={self.leg_id}, units={self.units:.4f}, max_stake={self.max_stake:.2f})"


def _legs(state, key):
    return [l for l in (state.get("legs") or []) if l.get("key") == key]


def available(store, key, unit):
    """Units still free for `key`, or raise. Reads only; grants nothing.

    Open and unknown-fill orders reserve their FULL asked exposure - requirement 3 - because an
    order whose outcome has not been verified may still fill in full. Only review_unit_exposure's
    own terminal-verified rule releases anything."""
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    state, _version = got
    return remaining(_legs(state, key), unit, key)


def reserve(store, key, leg_id, stake, american, unit, actor, attempts=3):
    """Atomically reserve capacity for ONE leg, BEFORE submission. Returns a Grant or raises.

    The compare-and-swap is the whole point: between reading the ledger and writing the new leg,
    another runner may have reserved. If the version moved, this does NOT proceed with a stale
    answer - it re-reads and re-evaluates, and if it still cannot win the write it REFUSES.

    A leg_id already present is returned idempotently rather than double-counted, so a retry of the
    same intent never reserves twice. That mirrors how the existing claim table treats a key."""
    if not key or not leg_id:
        raise ExposureUnknown("missing canonical key or leg identity")
    want = fraction(stake, american, unit)
    if want <= 0:
        raise ExposureUnknown("non-positive reservation")
    for _ in range(max(1, attempts)):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise ExposureUnknown("reservation store unreadable - fail closed")
        state, version = got
        legs = _legs(state, key)
        for l in legs:
            if str(l.get("leg_id")) == str(leg_id):
                return Grant(key, leg_id, want, round(stake, 2), version, actor)   # idempotent
        free = remaining(legs, unit, key)
        if want > free + EPS:
            raise ReservationRefused(
                f"per-play unit budget: {free:.4f}u free, {want:.4f}u requested for {key}")
        new = dict(state)
        new["legs"] = list(state.get("legs") or []) + [{
            "key": key, "leg_id": str(leg_id), "status": "open", "asked_stake": round(stake, 2),
            "american": american, "order_id": str(leg_id), "actor": actor}]
        if store.write(new, version):
            return Grant(key, leg_id, want, round(stake, 2), version, actor)
        # lost the race: another runner reserved first. Re-read and re-evaluate, never assume.
    raise ReservationRefused("could not win the reservation write - another runner holds it")


def authorize(grant, stake):
    """The ONLY way to turn a stake into permission. Requirement 5.

    Without a Grant there is no authorized stake, so a runner that skipped reserve() cannot submit.
    A stake above what was reserved is refused outright rather than trimmed: silently shrinking an
    order would make the reservation and the submission disagree, which is the condition this whole
    design exists to prevent."""
    if not isinstance(grant, Grant):
        raise ReservationRefused("no reservation grant - submission is not authorized")
    s = float(stake)
    if not math.isfinite(s) or s <= 0:
        raise ExposureUnknown("stake unreadable")
    if s > grant.max_stake + 0.011:
        raise ReservationRefused(
            f"stake {s:.2f} exceeds the reserved {grant.max_stake:.2f} - not trimmed, refused")
    return round(s, 2)


def record_outcome(store, key, leg_id, status, filled_stake=None, terminal_verified=False):
    """Update a reserved leg with what the VENUE said. Never releases on inference.

    Requirement 3 and requirement 6 both live here. Capacity is released only when the caller
    passes terminal_verified=True together with a fill amount - that is, explicit venue evidence.
    Time passing is not evidence. Absence of a fill report is not evidence. And there is no cancel
    or shrink path in this module at all: releasing capacity and cancelling an order are different
    actions, and the second one is not authorized."""
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    state, version = got
    legs = list(state.get("legs") or [])
    hit = False
    for i, l in enumerate(legs):
        if l.get("key") == key and str(l.get("leg_id")) == str(leg_id):
            upd = dict(l, status=str(status))
            if filled_stake is not None:
                upd["filled_stake"] = round(float(filled_stake), 2)
            if terminal_verified:
                upd["terminal_verified"] = True
            legs[i] = upd
            hit = True
            break
    if not hit:
        raise ExposureUnknown("outcome for a leg that was never reserved - fail closed")
    if not store.write(dict(state, legs=legs), version):
        raise ReservationRefused("outcome write lost the compare-and-swap - re-read and retry")
    return True


def cap_for(store, key, american, unit):
    """Largest stake that could be reserved right now. ADVISORY - it grants nothing.

    Published so a caller can size a request before asking. It is deliberately NOT sufficient to
    submit: only reserve() plus authorize() produce permission, and the answer here can be stale by
    the time it is used, which is precisely why the compare-and-swap exists."""
    return maximum_stake(available(store, key, unit), american, unit)
