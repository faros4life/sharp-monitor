#!/usr/bin/env python3
"""Carry the runner's REFUSAL back to the cloud registry, and release exposure only on proof.

Peter, 27 Nov: "For refusal writeback, require exact order identity, fill_read=True, zero filled
quantity and authoritative confirmation of no submission before releasing exposure. Make the release
idempotent. Unknown or contradictory records must remain reserved."

THE DEFECT THIS CLOSES, measured. The Dogs order decided 2026-11-27T14:16:09Z shows in the registry as
`status=placed, filled_stake=None, reason=None`, while the runner's own log for run 46014376990 at
14:16:06Z reads "Novig order: status refused; tif FOK; filled no". The runner was right and it said so
durably: on a pre-submission refusal it records filled_qty=0, fill_read=True, fill_read_src="not
submitted" and appends that row to snapshot/novig_orders.json. The cloud reads that snapshot in
executor.novig_reports() - and that function only ANNOUNCES to Telegram. Nothing wrote the result back
to the registry leg and nothing released the reservation the cloud took before dispatch. The evidence
was produced, delivered, read, announced, and then dropped.

WHY THE TEST IS "not submitted" AND NOT THE WORD "refused". A venue-side rejection AFTER submission is
not proof of zero exposure - the order reached Novig and its fate depends on the venue. Only the
runner's own pre-submission refusal proves nothing was sent, and the runner marks exactly that case
with fill_read_src="not submitted". Collapsing the two would release money that may be live at the
venue, which is the one direction a risk gate must never fail in (Peter, 23 Nov: "an unknown fill is
never turned into zero exposure").

This module is PURE: it decides, it does not write. The caller performs the registry write and the
release, so every rule here is unit-testable without a store, a token or a venue.
"""

# The runner's marker for "this never reached the venue". Set in novig_live_order._not_submitted().
NOT_SUBMITTED = "not submitted"

# Stamped on a leg we have written back, so a second pass is a no-op rather than a second release.
DONE_MARK = "novig_writeback"

RELEASE = "RELEASE"        # proven zero exposure: write back and release
HOLD = "HOLD"              # unknown or contradictory: stays reserved, reported
DONE = "DONE"              # already written back AND released; idempotent no-op
RELEASE_AGAIN = "RELEASE_AGAIN"   # written back on an earlier pass, claim may still be held
NO_MATCH = "NO_MATCH"      # no registry leg carries this identity


def legs_by_cid(rows):
    """{client_id: [(row, leg_field, leg), ...]} across every stored order row.

    A list, not a single leg, deliberately: two legs sharing one client_id is an AMBIGUOUS identity and
    must be held, not resolved by arrival order. Collapsing it to the first match would let the order
    the rows happen to be stored in decide which exposure gets released.
    """
    out = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        fields = [("live_order", row.get("live_order")), ("live_rest", row.get("live_rest"))]
        fields += [("live_more", x) for x in (row.get("live_more") or [])]
        for name, leg in fields:
            if not isinstance(leg, dict):
                continue
            cid = leg.get("client_id")
            cid = str(cid).strip() if cid is not None else ""
            if not cid:
                continue
            out.setdefault(cid, []).append((row, name, leg))
    return out


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def classify(rec, index):
    """(decision, reason) for ONE snapshot record against the registry index from legs_by_cid().

    Every gate below is a REQUIREMENT Peter named, checked independently, and any failure HOLDs rather
    than guessing. The order is deliberate: identity first, because without it the rest is about the
    wrong order.
    """
    rec = rec or {}

    # ---- exact order identity -------------------------------------------------------------
    cid = rec.get("client_id")
    cid = str(cid).strip() if cid is not None else ""
    if not cid:
        return HOLD, "snapshot record carries no client_id - identity cannot be established"
    hits = index.get(cid) or []
    if not hits:
        return NO_MATCH, f"no registry leg carries client_id {cid}"
    if len(hits) > 1:
        return HOLD, (f"client_id {cid} matches {len(hits)} registry legs - ambiguous identity, "
                      "nothing released")
    _row, _field, leg = hits[0]

    # ---- idempotent, and crash-safe ---------------------------------------------------------
    # Nov 27 (Peter, fix 2): "A persisted, proven zero must allow the next pass to retry the claim
    # release safely." The caller persists the zero BEFORE releasing the claim, so a crash between
    # the two leaves the mark written and the claim held. This used to return DONE, which never
    # retried - and registry.claim_submission has deliberately NO staleness expiry, so that play was
    # blocked for takes AND rests until Peter cleared it by hand. The in-code comment claiming the
    # claim "ages out" was simply wrong.
    #
    # Retrying is safe only because the PERSISTED PROOF is re-checked here rather than trusted from
    # the mark: the mark alone is a record that someone wrote something. If the mark is present but
    # the proof is not intact, that is a contradiction and it HOLDS. release_submission is itself
    # idempotent (it pops only on an exact key+cid match), so a retry after a successful release is
    # a harmless no-op.
    if leg.get("writeback") == DONE_MARK:
        if (_num(leg.get("filled_stake")) == 0.0 and leg.get("filled_stake") is not None
                and leg.get("fill_read") is True
                and str(leg.get("fill_read_src") or "") == NOT_SUBMITTED
                and str(leg.get("status") or "") == "refused"):
            return RELEASE_AGAIN, (f"client_id {cid} was written back on an earlier pass; "
                                   f"retrying the claim release in case it did not complete")
        return HOLD, (f"client_id {cid} carries the writeback mark but not the proven zero "
                      f"(filled {leg.get('filled_stake')!r}, read {leg.get('fill_read')!r}, "
                      f"src {leg.get('fill_read_src')!r}, status {leg.get('status')!r}) - "
                      f"contradictory, nothing released")

    # ---- fill_read is True, by identity and not by truthiness ------------------------------
    if leg.get("filled_stake") is not None and _num(leg.get("filled_stake")) == 0.0 \
            and leg.get("fill_read") is True:
        return DONE, f"client_id {cid} already carries a proven zero"
    if rec.get("fill_read") is not True:
        return HOLD, (f"client_id {cid}: fill_read is {rec.get('fill_read')!r}, not True - the fill was "
                      "not read, so exposure is UNKNOWN and stays reserved")

    # ---- zero filled quantity --------------------------------------------------------------
    q = rec.get("filled_qty")
    qn = _num(q)
    if qn is None:
        return HOLD, (f"client_id {cid}: filled_qty is {q!r} - missing or unreadable is UNKNOWN, "
                      "never zero")
    if qn != 0.0:
        return HOLD, f"client_id {cid}: filled_qty is {qn} - something filled, exposure is real"
    fc = rec.get("filled_cost")
    if fc is not None and (_num(fc) is None or _num(fc) != 0.0):
        return HOLD, (f"client_id {cid}: filled_qty is 0 but filled_cost is {fc!r} - contradictory, "
                      "stays reserved")

    # ---- authoritative confirmation of NO SUBMISSION ---------------------------------------
    src = str(rec.get("fill_read_src") or "").strip().lower()
    if src != NOT_SUBMITTED:
        return HOLD, (f"client_id {cid}: fill_read_src is {rec.get('fill_read_src')!r}, not "
                      f"{NOT_SUBMITTED!r} - a zero read AFTER submission is not proof the order never "
                      "reached the venue, so exposure stays reserved")
    if rec.get("order_id"):
        return HOLD, (f"client_id {cid}: marked not submitted but carries order_id "
                      f"{rec.get('order_id')!r} - contradictory, stays reserved")

    # ---- the registry must not already disagree --------------------------------------------
    have = _num(leg.get("filled_stake"))
    if leg.get("filled_stake") is not None and have is None:
        return HOLD, f"client_id {cid}: registry filled_stake is {leg.get('filled_stake')!r} - unreadable"
    if have is not None and have > 0:
        return HOLD, (f"client_id {cid}: registry already records ${have} filled but the snapshot says "
                      "nothing was submitted - contradictory, stays reserved")

    return RELEASE, (f"client_id {cid}: proven not submitted ({rec.get('fill_read_why') or 'no reason '
                     'recorded'}), fill_read True, zero filled - releasing")


def plan(recs, rows):
    """([(cid, row, leg_field, reason)], {decision: [reason]}) - what to write back, and why not.

    Returns the RELEASE list for the caller to act on and every other decision for the log, so a HOLD
    is visible rather than silent. Nothing here mutates `rows`.
    """
    index = legs_by_cid(rows)
    releases, other = [], {}
    seen = set()
    for rec in recs or []:
        d, why = classify(rec, index)
        if d in (RELEASE, RELEASE_AGAIN):
            cid = str((rec or {}).get("client_id")).strip()
            if cid in seen:          # the same refusal twice in one snapshot: act once
                other.setdefault(DONE, []).append(f"client_id {cid}: duplicate record in this snapshot")
                continue
            seen.add(cid)
            row, field, _leg = index[cid][0]
            # The 5th element says whether the row still needs WRITING. A RELEASE_AGAIN is already
            # persisted, so re-writing it would burn a registry write and a sha race for nothing;
            # only the claim release is retried.
            releases.append((cid, row, field, why, d == RELEASE))
        else:
            other.setdefault(d, []).append(why)
    return releases, other


def apply_to_leg(leg, rec):
    """Stamp the proven zero onto a registry leg, in place. Caller persists the row.

    Records WHY, not just what: a later reader must be able to tell this zero came from the runner's
    pre-submission refusal and not from a venue read or a guess.
    """
    leg["filled_stake"] = 0.0
    leg["fill_read"] = True
    leg["fill_read_src"] = NOT_SUBMITTED
    leg["fill_read_why"] = rec.get("fill_read_why") or "refused before submission"
    leg["status"] = "refused"
    leg["reason"] = str(rec.get("error") or "refused before submission by the runner")[:300]
    leg["writeback"] = DONE_MARK
    return leg
