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

MIGRATION, FOUND IN THE FOURTH REVIEW (head d4bca65e), fixed here:
  9. A fresh ledger is not an empty book. Activated against an unseeded ledger this would
     read every play as having its full unit free while real filled and resting orders are
     already outstanding at the venues - it would authorize a SECOND unit on every open play
     on its first pass. An empty store and an unmigrated one look identical, so the
     difference is now recorded explicitly: every read, reservation and authorization BLOCKS
     until backfill() seeds the existing orders and marks the ledger usable. backfill()
     refuses to run twice, because re-seeding a live ledger would drop reservations made
     since.

ONE MORE FOUND IN THE THIRD REVIEW (head b4eeb1a22), fixed here:
  8. authorize() was a READ-ONLY CHECK, so an active grant returned permission every time it
     was called - one reservation could authorize unlimited submissions of the same stake.
     Authorization is now a SINGLE-USE STATE TRANSITION committed under compare-and-swap
     before the caller is told yes. A lost race refuses and is never retried, because a retry
     of a dispatch mark is exactly how one order becomes two. rearm() allows one further
     authorization ONLY on explicit evidence the first submission never reached the venue.

     NOTE on the existing journal: executor.journal_intent() already calls
     registry.claim_submission() before takers, which prevents a duplicate CLAIM on one key.
     It is not the same guarantee - it is per-key exclusivity, not per-reservation single use,
     the taker and rest paths claim different names, and the Novig runner calls none of it.

THREE MORE FOUND IN THE SECOND REVIEW (head a9016085f), all fixed here:
  5. A reserved leg could be moved to void/refused/dry - which contribute ZERO exposure -
     with no evidence, freeing its whole reservation. Those states now need the same proof
     as any release, and a non-zero fill makes them impossible.
  6. A late callback with a SMALLER fill overwrote a verified one and released matched
     exposure. A verified fill may now only hold or grow, and cannot be voided at all.
  7. authorize() checked the terms but not whether the reservation was still ACTIVE, so a
     cancelled, expired, settled or filled leg could authorize another order. It must now be
     open/placed/partially_filled and not terminal-verified.

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


SEEDED = "seeded"


def _require_seeded(state):
    """Finding 9: a FRESH ledger is not an EMPTY book.

    Switching this on against an unseeded ledger would read every play as having its full unit
    available while real filled and resting orders are already outstanding at the venues - the
    guard would authorize a second unit on every open play on its first pass. An empty store and a
    store that has never been migrated are indistinguishable by their contents, so the difference
    has to be recorded explicitly. Until backfill() marks it, every read BLOCKS."""
    if state.get(SEEDED) is not True:
        raise ExposureUnknown(
            "exposure ledger has not been seeded with existing filled and resting orders - "
            "fail closed (see backfill)")


def backfill(store, legs, note):
    """Seed the ledger from orders that ALREADY EXIST, then mark it usable. Run once, before use.

    `legs` are the outstanding filled and resting orders, in the leg shape this module stores.
    They are written as-is and counted exactly like any reservation, so a play that already has a
    unit at a venue starts with zero capacity rather than a full one.

    Refuses to run twice: re-seeding a live ledger would drop reservations made since. Recovering
    from a bad seed is a deliberate act, not an idempotent one."""
    if not str(note or "").strip():
        raise ExposureUnknown("backfill without a provenance note - fail closed")
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    state, version = got
    if state.get(SEEDED) is True:
        raise ReservationRefused("ledger is already seeded - re-seeding would drop live reservations")
    seeded = []
    for l in legs or []:
        leg = dict(l)
        if not leg.get("key") or not (leg.get("leg_id") or leg.get("order_id")):
            raise ExposureUnknown("backfill leg without a play key or identity - fail closed")
        leg.setdefault("leg_id", str(leg.get("order_id")))
        leg.setdefault("order_id", str(leg.get("leg_id")))
        leg.setdefault("status", "open")        # unknown outcome reserves in full
        leg["backfilled"] = True
        leg_fraction(leg)                        # validates unit, price, status, amounts; raises if not
        seeded.append(leg)
    new = dict(state)
    new["legs"] = list(state.get("legs") or []) + seeded
    new[SEEDED] = True
    new["seed_note"] = str(note)[:160]
    if not store.write(new, version):
        raise ReservationRefused("backfill lost the compare-and-swap - refused, not retried")
    return len(seeded)


def available(store, key):
    """Units still free, or raise. Reads only; grants nothing.

    Open and unknown-fill orders hold their FULL asked exposure - requirement 3 - because an order
    whose outcome is unverified may still fill in full."""
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    _require_seeded(got[0])
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
        _require_seeded(state)
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
    _require_seeded(got[0])
    leg = next((l for l in _legs(got[0], grant.key)
                if str(l.get("leg_id")) == str(grant.leg_id)), None)
    if leg is None:
        raise ReservationRefused("grant does not correspond to a reservation in the store")
    if not _same_request(leg, grant.max_stake, grant.american, grant.unit, grant.actor):
        raise ReservationRefused("grant disagrees with the stored reservation - refused")
    # Finding 3 (second review): a grant is good only while its reservation is ACTIVE. A cancelled,
    # expired, settled, filled or voided leg has already had its outcome; re-authorizing against it
    # would send a second order on capacity that is spent or released.
    st = str(leg.get("status") or "").lower()
    if st not in LIVE_STATES or leg.get("terminal_verified") is True:
        raise ReservationRefused(
            f"reservation is no longer active (status {st or 'unknown'}) - authorization refused")
    # Finding 8 (third review): authorization must be SINGLE USE. A read-only check returns
    # permission every time it is called, so one reservation could authorize an unlimited number
    # of submissions of the same stake. Authorization is therefore a STATE TRANSITION, committed
    # under compare-and-swap in the same store, before the caller is told yes.
    if leg.get("dispatched") is True:
        raise ReservationRefused(
            "this reservation has already authorized a submission - one reservation, one order")
    s = float(stake)
    if not math.isfinite(s) or s <= 0:
        raise ExposureUnknown("stake unreadable")
    if s > _num(leg.get("asked_stake"), "asked") + 0.011:
        raise ReservationRefused(
            f"stake {s:.2f} exceeds the reserved {leg.get('asked_stake')} - not trimmed, refused")
    state, version = got
    legs = list(state.get("legs") or [])
    for i, l in enumerate(legs):
        if l.get("key") == grant.key and str(l.get("leg_id")) == str(grant.leg_id):
            legs[i] = dict(l, dispatched=True, dispatched_stake=round(s, 2))
            break
    if not store.write(dict(state, legs=legs), version):
        # Lost the race: another caller consumed this reservation between the read and the write.
        # Fail closed. Never retry a dispatch mark - a retry here is how one becomes two.
        raise ReservationRefused(
            "lost the compare-and-swap marking this reservation dispatched - refused, not retried")
    return round(s, 2)


def claim_dispatched(store, key, stake, book, claimant, attempts=3):
    """The SECOND executor's half: claim a reservation the first one made, or refuse.

    The cloud executor reserves a play's unit and marks it dispatched before it hands a Novig order
    to the runner. The runner must not reserve again - the budget is already held, so a second
    reservation would refuse every legitimate order - and it must not place on trust either, or a
    manual or duplicated dispatch goes straight to the venue. So it CLAIMS: it finds a reservation
    under the same identity that was made for THIS venue, is active, has been dispatched, has not
    been claimed, and covers the stake; and it marks that reservation claimed under
    compare-and-swap before it submits.

      duplicate retry    -> the reservation is already claimed: refused
      simultaneous runs  -> one wins the compare-and-swap; the other re-reads, sees the claim
                            and is refused
      no reservation     -> refused (a Novig order cannot ride a ProphetX reservation)
      unknown fill later -> the reservation keeps its FULL asked exposure until an outcome is
                            verified; claiming releases nothing
    """
    s = float(stake)
    if not math.isfinite(s) or s <= 0:
        raise ExposureUnknown("stake unreadable")
    b = str(book or "").strip().lower()
    who = str(claimant or "").strip()
    if not b or not who:
        raise ExposureUnknown("claim needs a venue and a claimant - fail closed")
    # The registry file is shared with ordinary bookkeeping writes, so a lost compare-and-swap is
    # usually someone else's unrelated commit. Each attempt RE-READS and RE-DECIDES from the fresh
    # state - it never re-applies a stale decision - so a reservation another runner claimed in
    # the meantime is seen as claimed and refused.
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise ExposureUnknown("reservation store unreadable - fail closed")
        _require_seeded(got[0])
        leg_id = _claim_once(store, got, key, s, b, who)
        if leg_id is not None:
            return leg_id
    raise ReservationRefused(
        "lost the compare-and-swap claiming this reservation - refused, not placed")


def _claim_once(store, got, key, s, b, who):
    """One read-decide-write. Returns the leg id, None on a lost write, or raises a refusal."""
    state, version = got
    legs = list(state.get("legs") or [])
    pick, seen_claimed = None, False
    for i, l in enumerate(legs):
        if l.get("key") != key or not str(l.get("actor") or "").endswith(":" + b):
            continue
        if str(l.get("status") or "").lower() not in LIVE_STATES or l.get("terminal_verified") is True:
            continue
        if l.get("dispatched") is not True:
            continue
        if l.get("claimed_by"):
            seen_claimed = True
            continue
        if s > _num(l.get("asked_stake"), "asked") + 0.011:
            continue
        pick = i
        break
    if pick is None:
        raise ReservationRefused(
            "the reservation for this play and venue has already been claimed - one reservation, "
            "one order" if seen_claimed else
            "no active dispatched reservation for this play on this venue covers the stake - "
            "refused")
    legs[pick] = dict(legs[pick], claimed_by=who, claimed_stake=round(s, 2))
    if not store.write(dict(state, legs=legs), version):
        return None
    return str(legs[pick].get("leg_id"))


def rearm(store, key, leg_id, evidence):
    """Allow ONE further authorization, only on proof the first submission never reached the venue.

    A send can fail. But a failed send and a successful send whose acknowledgement was lost look
    identical from here, and the fail-closed reading of that ambiguity is that the order WAS sent.
    So re-arming is not automatic and not time-based: it needs the same explicit venue evidence as
    any other release. Without it, the correct recovery is a NEW reservation under a new leg_id,
    which is counted against the budget like anything else."""
    if not str(evidence or "").strip():
        raise ExposureUnknown("re-arm without evidence the submission never reached the venue")
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise ExposureUnknown("reservation store unreadable - fail closed")
    state, version = got
    legs = list(state.get("legs") or [])
    hit = False
    for i, l in enumerate(legs):
        if l.get("key") == key and str(l.get("leg_id")) == str(leg_id):
            if l.get("terminal_verified") is True:
                raise ReservationRefused("a verified terminal leg cannot be re-armed")
            legs[i] = dict(l, dispatched=False, rearm_evidence=str(evidence)[:120])
            hit = True
            break
    if not hit:
        raise ExposureUnknown("re-arm for a leg that was never reserved - fail closed")
    if not store.write(dict(state, legs=legs), version):
        raise ReservationRefused("re-arm lost the compare-and-swap - refused")
    return True


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
    # Finding 1 (second review): void/refused/dry contribute ZERO exposure, so moving a reserved
    # leg into one of them frees its whole reservation. That is a release and it needs the same
    # proof as any other release: evidence that the order never reached the venue.
    if st in IGNORED:
        if not str(evidence or "").strip():
            raise ExposureUnknown(
                f"release to {st!r} without evidence the order never reached the venue - fail closed")
        if filled_stake is not None and _num(filled_stake, "filled") > 0.011:
            raise ExposureUnknown(f"release to {st!r} with a non-zero fill - fail closed")
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
            verified = l.get("terminal_verified") is True
            if was in TERMINAL_STATES and verified and st in LIVE_STATES:
                raise ReservationRefused(
                    "a verified terminal leg cannot regress to a live state - stale callback refused")
            # Finding 2 (second review): a late callback carrying a SMALLER fill would shrink the
            # recorded exposure and release capacity that is genuinely matched. Once verified, the
            # fill may only hold or grow; a smaller one is stale and is refused.
            if verified and filled_stake is not None and l.get("filled_stake") is not None:
                if _num(filled_stake, "filled") < _num(l.get("filled_stake"), "recorded") - 0.011:
                    raise ReservationRefused(
                        "a verified fill cannot be reduced by a later callback - stale, refused")
            if verified and st in IGNORED:
                raise ReservationRefused(
                    "a verified terminal leg cannot be voided - that would release matched exposure")
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
