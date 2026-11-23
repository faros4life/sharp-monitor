"""REVIEW ONLY. Keep the unit ledger a superset of every order ATTEMPT, without a pause or a cutoff.

THE GAP THIS CLOSES. The ledger learns about an order in one of three ways: the seed (orders that
existed before it), a reservation (enforcing), or a record-only write (transition). Each leaves a
hole, and a time cutoff does not close them:

  - an OLDER RUN still in flight - started before the flag changed, or a zombie past its timeout -
    can submit after any cutoff, and it writes nothing to the ledger;
  - a record-only write can FAIL, and the order proceeds;
  - an order can be placed between the last check and the moment enforcement is switched on.

In every one of those cases one thing has still happened, because the executor refuses to submit
without it: journal_intent() stored a PRE-ORDER ROW and read it back before the order was sent.

WHERE THAT ROW LIVES - and the mistake the first version of this file made. It read the registry's
`intents` list. Nothing in the order path writes there. journal_intent() calls
registry.put_rows([row]), so the pre-order row is a row in `orders`, keyed by the executor's
CLIENT ID, shaped {key, source, client_id, decided_utc, live_order: {order_id: "intent-<cid>",
book, asked_stake, client_id, intent: True}}. When the order is confirmed, the confirmed row is
upserted over it under the same client id, and the nested order id becomes the venue's. When the
executor proves nothing was sent, it upserts a row with voided: True. The first production dry
run printed "intents 0" - the reader, not the world - and the tests had passed because the
fixtures put rows where the code looked rather than where production writes them. The tests now
obtain their rows from the real journal_intent().

So the rule is: every non-voided order row is represented in the ledger. sweep() enforces it, and
the executor runs it immediately before it reserves or records anything.

HOW A ROW'S ORDER IS "REPRESENTED" - by identity only, never by resemblance:
  1. a ledger leg has the same venue and the same order id (the seed, or an earlier sweep);
  2. a ledger leg for the same venue carries the same client id (the reservation or record made
     for that attempt, or the pre-order row swept before the order was confirmed);
  3. the ledger refused that client id, so the attempt was never sent;
  4. the seed excluded it by identity, as a venue-proven zero fill.
A row the executor VOIDED was never submitted and is skipped. Anything else is ADDED, as an open
commitment at its full asked stake - including a pending pre-order row whose send is unconfirmed.

VALUATION IS AN UPPER BOUND where the price is not yet known: stake at risk over the lane unit,
never less than the to-win measure. A lane that cannot be read is valued at the SMALLEST unit. A
row that cannot be keyed or valued is counted and reported, never guessed.
"""
import review_integration as ri
import review_unit_reservation as R

REFUSED = "intent_refused"
EXCLUDED = "seed_excluded_ids"
SMALLEST_UNIT = 200.0


def read_rows(registry_module):
    """The registry's order rows - where pre-order records are written - or None if the file
    cannot be read. Never []: "could not read" must not look like "nothing there"."""
    try:
        data, sha = registry_module._fetch()
    except Exception:
        return None
    if data is None:
        return None
    return list(data.get("orders") or [])


def _book_of(leg):
    return str(leg.get("actor") or "").rsplit(":", 1)[-1]


def sweep(store, rows, exclude_cid=None, write=True, attempts=3):
    """Add every unrepresented order row to a SEEDED ledger. Returns counts. Idempotent.

    `exclude_cid` is the attempt being judged right now: its own reservation is about to be made,
    so it is not swept in ahead of itself."""
    import review_replay as RR
    cand, unreadable, _ = RR.backfill_candidates(rows or [])
    counts = {}
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise R.ExposureUnknown("reservation store unreadable - fail closed")
        state, version = got
        if state.get(R.SEEDED) is not True:
            raise R.ExposureUnknown("the ledger is not seeded - nothing to sweep into")
        legs = list(state.get("legs") or [])
        have_ids = {str(l.get("order_id")) for l in legs} | set(state.get(EXCLUDED) or [])
        have_cids = {(_book_of(l), str(l.get("intent_cid"))) for l in legs if l.get("intent_cid")}
        refused = set(state.get(REFUSED) or [])
        counts = {"rows": len(rows or []), "legs": len(cand), "unkeyable": len(unreadable),
                  "never_submitted": 0, "represented_by_order_id": 0,
                  "represented_by_client_id": 0, "refused_unsent": 0, "added": 0,
                  "added_pending": 0, "added_lane_unknown": 0}
        add = []
        for l in cand:
            book, oid, cid = str(l.get("book") or ""), str(l.get("order_id") or ""), str(l.get("cid") or "")
            if l.get("voided"):
                counts["never_submitted"] += 1
                continue
            if exclude_cid and cid and cid == str(exclude_cid):
                continue
            ident = f"{book}|{oid}"
            if ident in have_ids:
                counts["represented_by_order_id"] += 1
                continue
            if cid and (book, cid) in have_cids:
                counts["represented_by_client_id"] += 1
                continue
            if cid and cid in refused:
                counts["refused_unsent"] += 1
                continue
            unit, lane_known = l.get("unit"), True
            if not unit:
                unit, lane_known = SMALLEST_UNIT, False
            pending = l.get("american") is None
            try:
                leg = {"key": l.get("key"), "leg_id": f"sweep|{ident}", "order_id": ident,
                       "venue_order_id": oid, "status": "open",
                       "asked_stake": l.get("asked_stake"),
                       "american": 100 if pending else l.get("american"), "unit": unit,
                       "actor": ri.actor_for("sweep", l.get("field") or "order", book),
                       # an order attempt that already happened: never claimable by a new order
                       "dispatched": True, "claimed_by": "sweep", "swept": True,
                       **({"intent_cid": cid} if cid else {})}
                if not oid or not leg["key"]:
                    raise ValueError("no identity")
                R.leg_fraction(leg)
            except Exception:
                counts["unkeyable"] += 1
                continue
            add.append(leg)
            have_ids.add(ident)
            if cid:
                have_cids.add((book, cid))
            counts["added"] += 1
            counts["added_pending"] += 1 if pending else 0
            counts["added_lane_unknown"] += 0 if lane_known else 1
        if not write or not add:
            return counts
        if store.write(dict(state, legs=legs + add), version):
            return counts
    raise R.ReservationRefused("sweep could not win the write - the store kept moving")


TERMINAL_ROW = ("filled", "settled", "canceled", "cancelled", "expired")


def reconcile_outcomes(store, rows, write=True, attempts=3):
    """Bring ledger legs down to what the venue ACTUALLY matched, from the registry rows.

    Until now a leg held its FULL ASKED stake for ever. Nothing released it when the order
    cancelled, expired or filled for less than it asked, so a play that had an order on it refused
    every later order even when nothing was matched. That is safe against an overbet and wrong
    about everything else.

    No venue is called: the rows already carry what the venue said. Every change goes through
    record_outcome(), which is the one place that validates a release, so there is no second set
    of rules - a fill cannot exceed the ask, a verified terminal cannot regress or be reduced by a
    late callback, and a release needs evidence.

    WHAT COUNTS AS PROOF, deliberately narrow:
      - a terminal row with a POSITIVE fill: a number that size can only have come from a read, so
        the leg is marked verified at the FILLED amount and the rest of the ask is freed;
      - a terminal row with a ZERO fill ONLY when the record says the fill was READ. CLAUDE.md,
        Nov 19: an initialised zero is how an unread fill became a confident "venue confirms zero",
        and that released real exposure. An unread zero is left holding the full ask.
    OPEN, RESTING and UNKNOWN rows are never touched. A settled row is treated exactly like any
    other terminal row - it releases only the part the venue did not match, never more.
    """
    import review_replay as RR
    import review_unit_reservation as R
    cand, _unreadable, _t = RR.backfill_candidates(rows or [])
    by_oid, by_cid = {}, {}
    for l in cand:
        by_oid[f"{l.get('book')}|{l.get('order_id')}"] = l
        if l.get("cid"):
            by_cid[(str(l.get("book")), str(l.get("cid")))] = l
    counts = {"legs": 0, "matched": 0, "already_settled": 0, "reduced_to_fill": 0,
              "released_zero_fill": 0, "unread_zero_held": 0, "still_live": 0, "refused": 0}
    got = store.read()
    if not got or got[0] is None or got[1] is None:
        raise R.ExposureUnknown("reservation store unreadable - fail closed")
    if (got[0] or {}).get(R.SEEDED) is not True:
        raise R.ExposureUnknown("the ledger is not seeded - nothing to reconcile")
    for leg in list((got[0] or {}).get("legs") or []):
        counts["legs"] += 1
        if leg.get("terminal_verified") is True or str(leg.get("status") or "").lower() not in R.LIVE_STATES:
            counts["already_settled"] += 1
            continue
        book = str(leg.get("actor") or "").rsplit(":", 1)[-1]
        src = by_oid.get(str(leg.get("order_id"))) or by_oid.get(f"{book}|{leg.get('venue_order_id')}")
        if src is None and leg.get("intent_cid"):
            src = by_cid.get((book, str(leg.get("intent_cid"))))
        if src is None:
            continue
        counts["matched"] += 1
        st = str(src.get("status") or "").lower()
        if st not in TERMINAL_ROW:
            counts["still_live"] += 1
            continue
        filled = src.get("filled_stake")
        try:
            f = None if filled is None else float(filled)
        except (TypeError, ValueError):
            f = None
        if f is None or (f == 0.0 and src.get("fill_read") is not True):
            counts["unread_zero_held"] += 1          # an unread fill is never a releasable zero
            continue
        if not write:
            counts["reduced_to_fill" if f > 0 else "released_zero_fill"] += 1
            continue
        try:
            R.record_outcome(store, leg.get("key"), leg.get("leg_id"), st, f, True,
                             f"registry row: {st}, fill read {f}")
            counts["reduced_to_fill" if f > 0 else "released_zero_fill"] += 1
        except Exception:
            counts["refused"] += 1                   # validation said no: the leg keeps its hold
    return counts


def note_excluded(store, ids, attempts=3):
    """Record the order ids the SEED left out as venue-proven zero fills, so the sweep - which has
    no venue evidence of its own - does not add them back at full stake."""
    ids = [str(i) for i in ids or [] if i]
    if not ids:
        return True
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            return False
        state, version = got
        cur = list(state.get(EXCLUDED) or [])
        new = cur + [i for i in ids if i not in cur]
        if new == cur or store.write(dict(state, **{EXCLUDED: new}), version):
            return True
    return False


def mark_refused(store, cid, attempts=3):
    """Record that the ledger REFUSED this attempt, so its intent is not later counted as an order.
    Best effort: if this cannot be written the intent is swept in as exposure, which over-counts."""
    if not cid:
        return False
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            return False
        state, version = got
        cur = list(state.get(REFUSED) or [])
        if str(cid) in cur:
            return True
        if store.write(dict(state, **{REFUSED: (cur + [str(cid)])[-500:]}), version):
            return True
    return False
