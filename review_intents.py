"""REVIEW ONLY. Keep the unit ledger a superset of every order ATTEMPT, without a pause or a cutoff.

THE GAP THIS CLOSES. The ledger learns about an order in one of three ways: the seed (orders that
existed before it), a reservation (enforcing), or a record-only write (transition). Each leaves a
hole, and a time cutoff does not close them:

  - an OLDER RUN still in flight - started before the flag changed, or a zombie past its timeout -
    can submit after any cutoff, and it writes nothing to the ledger;
  - a record-only write can FAIL, and the order proceeds;
  - an order can be placed between the last check and the moment enforcement is switched on.

In every one of those cases one thing has still happened, because the executor refuses to submit
without it: journal_intent() wrote a write-ahead INTENT to the registry BEFORE the order was sent,
with the play key, the venue, the lane and the asked stake. So the rule is simply

        every intent is represented in the ledger

and sweep() enforces it. The executor runs it immediately before it reserves or records anything,
so by the time an order is judged, every earlier attempt - from any run, in any mode, recorded or
not, filled or not - is already counted against its play.

HOW AN INTENT IS "REPRESENTED":
  1. a ledger leg carries its client id (the reservation or record made for that same attempt);
  2. it was refused by the ledger and never sent (recorded in the ledger's own refused list);
  3. a SEEDED leg for the same play, venue and stake absorbs it, one for one - the order existed
     before the seed and is already counted under its venue id.
Anything else is ADDED, as an open commitment at its full asked stake.

VALUATION IS AN UPPER BOUND, because an intent carries no price: the stake is counted as risk
against the lane unit, which is never less than the to-win measure used for minus money. A lane
that cannot be read is valued at the SMALLEST unit, the larger fraction. An intent whose play key
is not an identity cannot be placed in any budget; it is counted and reported, never guessed.
"""
import review_integration as ri
import review_unit_reservation as R

REFUSED = "intent_refused"
SMALLEST_UNIT = 200.0


def read_intents(registry_module):
    """The registry's write-ahead intents, or None if the file cannot be read. Never []."""
    try:
        data, sha = registry_module._fetch()
    except Exception:
        return None
    if data is None:
        return None
    return list(data.get("intents") or [])


def _lane_unit(row):
    try:
        import review_replay as RR
        lane, unit, _why = RR.lane_unit(row)
        if unit:
            return float(unit), True
        return float(min(RR.LANE_UNIT.values())), False
    except Exception:
        return SMALLEST_UNIT, False


def parse(intents):
    """([{cid, key, book, stake, unit, lane_known, when}], unkeyable_count)."""
    out, bad = [], 0
    for i in intents or []:
        lo = (i or {}).get("live_order") or {}
        cid = str(i.get("client_id") or lo.get("client_id") or "")
        book = str(lo.get("book") or "").strip().lower()
        try:
            stake = float(lo.get("asked_stake"))
            key = ri.key_from_registry(i.get("key"))
            if not cid or not book or not (stake > 0):
                raise ValueError("incomplete intent")
        except Exception:
            bad += 1
            continue
        unit, known = _lane_unit(i)
        out.append({"cid": cid, "key": key, "book": book, "stake": round(stake, 2), "unit": unit,
                    "lane_known": known, "when": str(i.get("decided_utc") or "")})
    out.sort(key=lambda x: x["when"])
    return out, bad


def sweep(store, intents, exclude_cid=None, write=True, attempts=3):
    """Add every unrepresented intent to a SEEDED ledger. Returns counts. Idempotent.

    `exclude_cid` is the attempt being judged right now: its own reservation is about to be made,
    so it is not swept in ahead of itself."""
    items, bad = parse(intents)
    counts = {}
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise R.ExposureUnknown("reservation store unreadable - fail closed")
        state, version = got
        if state.get(R.SEEDED) is not True:
            raise R.ExposureUnknown("the ledger is not seeded - nothing to sweep into")
        legs = list(state.get("legs") or [])
        by_cid = {str(l.get("intent_cid")) for l in legs if l.get("intent_cid")}
        refused = set(state.get(REFUSED) or [])
        # seeded / backfilled legs that can each absorb ONE intent for the same play, venue, stake
        pool = {}
        for l in legs:
            if l.get("backfilled") and not l.get("intent_cid"):
                b = str(l.get("actor") or "").rsplit(":", 1)[-1]
                k = (l.get("key"), b, round(float(l.get("asked_stake") or 0), 2))
                pool[k] = pool.get(k, 0) + 1
        counts = {"intents": len(items), "unkeyable": bad, "represented": 0, "refused_unsent": 0,
                  "absorbed_by_seed": 0, "added": 0, "added_lane_unknown": 0}
        add = []
        for it in items:
            if exclude_cid and it["cid"] == str(exclude_cid):
                continue
            if it["cid"] in by_cid:
                counts["represented"] += 1
                continue
            if it["cid"] in refused:
                counts["refused_unsent"] += 1
                continue
            k = (it["key"], it["book"], it["stake"])
            if pool.get(k):
                pool[k] -= 1
                counts["absorbed_by_seed"] += 1
                continue
            leg = {"key": it["key"], "leg_id": f"intent|{it['cid']}",
                   "order_id": f"intent|{it['cid']}", "status": "open",
                   "asked_stake": it["stake"], "american": 100, "unit": it["unit"],
                   "actor": ri.actor_for("intent", "sweep", it["book"]),
                   # an order attempt that already happened: never claimable by a new order
                   "dispatched": True, "claimed_by": "intent-sweep",
                   "intent_cid": it["cid"], "swept": True}
            R.leg_fraction(leg)
            add.append(leg)
            counts["added"] += 1
            counts["added_lane_unknown"] += 0 if it["lane_known"] else 1
        if not write or not add:
            return counts
        if store.write(dict(state, legs=legs + add), version):
            return counts
    raise R.ReservationRefused("intent sweep could not win the write - the store kept moving")


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
