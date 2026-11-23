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
            leg = {"key": l.get("key"), "leg_id": f"backfill|{book}|{oid}", "order_id": oid,
                   "status": "open", "asked_stake": l.get("asked_stake"),
                   "american": l.get("american"), "unit": l.get("unit"),
                   "actor": ri.actor_for("backfill", l.get("field") or "order", book),
                   # already at the venue: a new Novig order must never be able to claim it
                   "dispatched": True, "claimed_by": "backfill"}
            if not oid or not leg["key"]:
                raise ValueError("no identity")
            frac = R.leg_fraction(leg)
        except Exception as ex:
            why = l.get("unit_why") or type(ex).__name__
            bad[why] = bad.get(why, 0) + 1
            continue
        prev = by_id.get((leg["key"], oid))
        if prev is None or frac > prev[1]:
            by_id[(leg["key"], oid)] = (leg, frac, l)
    if bad:
        return [], summary, ("standing order(s) that cannot be valued: "
                             + "; ".join(f"{v} x {k}" for k, v in sorted(bad.items())))
    per_play = {}
    for (key, _oid), (leg, frac, l) in by_id.items():
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
    if (os.environ.get("SEED_CONFIRM") or "").strip() != CONFIRM:
        print("SEED: DRY RUN - nothing written. Dispatch with confirm=SEED to write.", flush=True)
        return 0
    import registry
    import review_store_registry as rs
    import review_unit_reservation as R
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
