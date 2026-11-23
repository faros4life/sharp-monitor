#!/usr/bin/env python3
"""REVIEW ONLY until dispatched by Peter. Seed the shared unit ledger from orders that already exist.

The guard refuses every order until the ledger is seeded, because a fresh ledger would read every
play as having a full unit free while real orders are already out. This builds that seed from the
same inventory the reconciliation produces - registry rows, nested order records, venue evidence -
and writes it ONCE, through review_unit_reservation.backfill(), which refuses to run twice.

DRY RUN BY DEFAULT. Without SEED_CONFIRM=SEED it reads, counts and writes nothing.

CONSERVATIVE, per Peter (Nov 23): every order is seeded at its FULL ASKED stake unless a venue has
PROVEN it terminal with a zero fill. An order whose fill was never read - the four Novig orders -
is seeded in full; that can only over-count, which blocks a bet and never allows one. What cannot
be over-counted safely is an order that cannot be valued or keyed at all: a row with no canonical
identity, or a standing leg with no lane unit, price or stake. Any one of those REFUSES THE WHOLE
SEED, because seeding around it would leave real exposure outside the ledger.

It places nothing and cancels nothing. Its one write is the ledger key inside the registry file.
Public log: counts only.
"""
import os
import sys

import review_replay as RR

CONFIRM = "SEED"
CATCHUP = "CATCHUP"


def _when(text):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def catch_up(store, legs, cutoff, write=False, attempts=3):
    """Add to a SEEDED ledger the orders placed after the seed and before recording began.

    The cutover has three stages - seed, record-only, enforce - and this closes the one gap the
    first two leave: an order placed after the seed read the inventory and before the executor
    started writing its own orders to the ledger. Such an order is in the registry and at the
    venue but in no ledger. It is added here at its FULL ASKED stake, as an open commitment,
    whatever its fill status is or later turns out to be.

    `cutoff` is when record-only began (UTC). Orders at or after it are NOT added: the executor
    recorded those itself, under its own leg id, and adding them again would count them twice. An
    order with no timestamp cannot be placed on either side of the cutoff, so it is added - the
    direction that can only over-count - and reported separately.

    Idempotent: an order already in the ledger is skipped, so this can be run again safely."""
    import review_unit_reservation as R
    cut = _when(cutoff)
    if cut is None:
        raise ValueError("catch-up needs the UTC time record-only began (e.g. 2026-11-23T11:00:00Z)")
    out = {}
    for _attempt in range(max(1, int(attempts))):
        got = store.read()
        if not got or got[0] is None or got[1] is None:
            raise R.ExposureUnknown("reservation store unreadable - fail closed")
        state, version = got
        if state.get(R.SEEDED) is not True:
            raise R.ReservationRefused("the ledger is not seeded - seed first, then catch up")
        have = {str(l.get("order_id")) for l in state.get("legs") or []}
        out = {"inventory": len(legs), "already_in_ledger": 0, "after_cutoff_skipped": 0,
               "added": 0, "added_undated": 0}
        add = []
        for leg in legs:
            if str(leg.get("order_id")) in have:
                out["already_in_ledger"] += 1
                continue
            t = _when(leg.get("placed_utc")) if leg.get("placed_utc") else None
            if t is not None and t >= cut:
                out["after_cutoff_skipped"] += 1
                continue
            new = dict(leg, backfilled=True, caught_up=True)
            R.leg_fraction(new)
            add.append(new)
            out["added"] += 1
            out["added_undated"] += 1 if t is None else 0
        if not write or not add:
            return out
        if store.write(dict(state, legs=list(state.get("legs") or []) + add), version):
            return out
    raise R.ReservationRefused("catch-up could not win the write - the store kept moving")


def build(legs, unreadable):
    """(seed_legs, summary, refusal). refusal is None when the seed is safe to write."""
    import novig_reconcile as nr
    import review_integration as ri
    import review_unit_reservation as R
    summary = {"read": len(legs), "skipped_proven_zero": 0, "seeded": 0, "unproven_seeded_in_full": 0,
               "plays": 0, "plays_at_or_over_one_unit": 0, "by_lane": {}}
    if unreadable:
        return [], summary, f"{len(unreadable)} row(s) could not be keyed or classified"
    by_id, bad = {}, {}
    for l in legs:
        if l.get("venue_class") == nr.TERMINAL and l.get("evidence_class") == RR.PROVEN:
            summary["skipped_proven_zero"] += 1
            continue
        oid = str(l.get("order_id") or l.get("client_id") or "")
        book = str(l.get("book") or "")
        try:
            # The id is NAMESPACED BY VENUE. The ledger counts one order id once per play (max),
            # so two venues that happened to issue the same id on one play would otherwise
            # collapse into a single order and the smaller one would vanish from the budget.
            leg = {"key": l.get("key"), "leg_id": f"backfill|{book}|{oid}",
                   "order_id": f"{book}|{oid}", "venue_order_id": oid,
                   "status": "open", "asked_stake": l.get("asked_stake"),
                   "american": l.get("american"), "unit": l.get("unit"),
                   "actor": ri.actor_for("backfill", l.get("field") or "order", book),
                   # already at the venue: a new Novig order must never be able to claim it
                   "dispatched": True, "claimed_by": "backfill",
                   "placed_utc": l.get("decided_utc")}
            if not oid or not leg["key"]:
                raise ValueError("no identity")
            frac = R.leg_fraction(leg)
        except Exception as ex:
            why = l.get("unit_why") or type(ex).__name__
            bad[why] = bad.get(why, 0) + 1
            continue
        prev = by_id.get((leg["key"], book, oid))
        if prev is None or frac > prev[1]:
            by_id[(leg["key"], book, oid)] = (leg, frac, l)
    if bad:
        return [], summary, ("standing order(s) that cannot be valued: "
                             + "; ".join(f"{v} x {k}" for k, v in sorted(bad.items())))
    per_play = {}
    for (key, _book, _oid), (leg, frac, l) in by_id.items():
        per_play[key] = per_play.get(key, 0.0) + frac
        ln = l.get("lane") or "unknown"
        summary["by_lane"][ln] = summary["by_lane"].get(ln, 0) + 1
        if l.get("evidence_class") != RR.PROVEN:
            summary["unproven_seeded_in_full"] += 1
    summary["seeded"] = len(by_id)
    summary["plays"] = len(per_play)
    summary["plays_at_or_over_one_unit"] = sum(1 for v in per_play.values() if v >= 1.0 - 1e-9)
    return [v[0] for v in by_id.values()], summary, None


def main():
    rows = RR._rows()
    if rows is None:
        print("SEED: registry unreadable - nothing read, nothing written", flush=True)
        return 1
    legs, unreadable, _ = RR.backfill_candidates(rows)
    legs, counts = RR.venue_evidence(legs)
    seed, summary, refusal = build(legs, unreadable)
    print("SEED: venue evidence " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
          flush=True)
    print("SEED: " + " | ".join(f"{k} {v}" for k, v in summary.items() if k != "by_lane"), flush=True)
    print("SEED: by lane " + ("; ".join(f"{v} x {k}" for k, v in sorted(summary["by_lane"].items()))
                              or "none"), flush=True)
    if refusal:
        print(f"SEED: REFUSED - {refusal}. Nothing written.", flush=True)
        return 1
    import registry
    import review_store_registry as rs
    import review_unit_reservation as R
    confirm = (os.environ.get("SEED_CONFIRM") or "").strip()
    cutoff = (os.environ.get("SEED_CUTOFF") or "").strip()
    if cutoff:
        # CATCH-UP path: the ledger is already seeded; add what was placed before recording began.
        try:
            c = catch_up(rs.RegistryStore(registry), seed, cutoff, write=(confirm == CATCHUP))
        except Exception as ex:
            print(f"CATCHUP: REFUSED - {type(ex).__name__}: {str(ex)[:120]}. Nothing written.",
                  flush=True)
            return 1
        print("CATCHUP: " + " | ".join(f"{k} {v}" for k, v in c.items()), flush=True)
        print("CATCHUP: WRITTEN" if confirm == CATCHUP else
              "CATCHUP: DRY RUN - nothing written. Dispatch with confirm=CATCHUP to write.",
              flush=True)
        return 0
    if confirm != CONFIRM:
        print("SEED: DRY RUN - nothing written. Dispatch with confirm=SEED to write.", flush=True)
        return 0
    try:
        n = R.backfill(rs.RegistryStore(registry), seed,
                       f"seed from registry+venue inventory, {len(seed)} legs, conservative full ask")
    except Exception as ex:
        print(f"SEED: REFUSED at write - {type(ex).__name__}: {str(ex)[:120]}. Nothing written.",
              flush=True)
        return 1
    print(f"SEED: WRITTEN - {n} leg(s). The ledger is seeded; the flag is still off.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
