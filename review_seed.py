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
SWEEP = "SWEEP"
RELEASE = "RELEASE"


def stuck_never_submitted(store, rows):
    """Legs still holding a unit whose ROWS prove their order was never submitted.

    One-off repair for legs recorded before void_intent learned to release them. It uses the same
    proof and the same release as the live path - no second rule - so a leg this frees is one the
    executor would have freed itself today."""
    import review_unit_reservation as R
    got = store.read()
    if not got or got[0] is None:
        return None, "ledger unreadable"
    legs = (got[0] or {}).get("legs") or []
    out = []
    for l in legs:
        cid = str(l.get("intent_cid") or "")
        if not cid or str(l.get("status") or "").lower() not in R.LIVE_STATES:
            continue
        if l.get("claimed_by") and str(l.get("claimed_by")) not in ("record", "sweep"):
            continue
        if l.get("filled_stake") not in (None, 0, 0.0):
            continue
        if R.never_submitted_proof(rows, cid):
            out.append(cid)
    return out, ""


class _Mem:
    """An in-memory ledger, for showing what a sweep WOULD add without writing anything."""

    def __init__(self, state):
        self.state = state

    def read(self):
        return ({**self.state, "legs": [dict(l) for l in self.state.get("legs") or []]}, "mem")

    def write(self, state, version):
        self.state = dict(state)
        return True


def build(legs, unreadable):
    """(seed_legs, summary, refusal). refusal is None when the seed is safe to write.

    EVERY INPUT LEG GETS EXACTLY ONE DISPOSITION, written onto the leg itself:
        retained         seeded at its full asked stake
        proven_zero      a venue has PROVEN a terminal zero fill
        never_submitted  the executor voided its own pre-order record: nothing reached a venue
        duplicate        the SAME ORDER as a retained leg, proven by identity - the same venue and
                         the same order id, or the same venue and the same client id (a pre-order
                         row and the confirmed row it became). A shared play, venue and stake is
                         NOT identity and never makes a duplicate.
    The first seed dry run reported 50 read and 39 seeded with 3 skipped, and could not say what
    the other 8 were. They were collapsed here without a word. The counts now have to add up, and
    the reason for each collapse is recorded.
    """
    import novig_reconcile as nr
    import review_integration as ri
    import review_unit_reservation as R
    summary = {"input": len(legs), "retained": 0, "proven_zero": 0, "never_submitted": 0,
               "duplicate": 0, "unproven_retained_in_full": 0, "pending_valued_as_risk": 0,
               "plays": 0, "plays_at_or_over_one_unit": 0, "by_lane": {}, "dup_reasons": {}}
    if unreadable:
        return [], summary, f"{len(unreadable)} row(s) could not be keyed or classified"
    kept, bad, where = [], {}, {}
    for l in legs:
        if l.get("voided"):
            l["disposition"] = "never_submitted"
            summary["never_submitted"] += 1
            continue
        if l.get("venue_class") == nr.TERMINAL and l.get("evidence_class") == RR.PROVEN:
            l["disposition"] = "proven_zero"
            summary["proven_zero"] += 1
            continue
        oid = str(l.get("order_id") or l.get("client_id") or "")
        book = str(l.get("book") or "")
        cid = str(l.get("cid") or "")
        am = l.get("american")
        pending = am is None and bool(l.get("intent_only"))
        try:
            # The id is NAMESPACED BY VENUE. The ledger counts one order id once per play (max),
            # so two venues that happened to issue the same id on one play would otherwise
            # collapse into a single order and the smaller one would vanish from the budget.
            leg = {"key": l.get("key"), "leg_id": f"backfill|{book}|{oid}",
                   "order_id": f"{book}|{oid}", "venue_order_id": oid,
                   "status": "open", "asked_stake": l.get("asked_stake"),
                   # A pending send has no price yet. Counting its stake as risk (+100) is never
                   # less than the to-win measure, so it can only over-count.
                   "american": 100 if pending else am, "unit": l.get("unit"),
                   "actor": ri.actor_for("backfill", l.get("field") or "order", book),
                   # already at the venue: a new Novig order must never be able to claim it
                   "dispatched": True, "claimed_by": "backfill",
                   "placed_utc": l.get("decided_utc"),
                   **({"intent_cid": cid} if cid else {})}
            if not oid or not leg["key"]:
                raise ValueError("no identity")
            frac = R.leg_fraction(leg)
        except Exception as ex:
            why = l.get("unit_why") or type(ex).__name__
            bad[why] = bad.get(why, 0) + 1
            l["disposition"] = "unresolved"
            continue
        # identity: the venue's order id, and separately the executor's client id
        ids = [("order id", (book, oid))] + ([("client id", (book, "cid:" + cid))] if cid else [])
        hit = next(((name, where[i]) for name, i in ids if i in where), None)
        if hit and hit[0] == "client id" and not (l.get("intent_only")
                                                  or hit[1]["src"].get("intent_only")):
            # Two CONFIRMED orders with different venue order ids are two orders, whatever client
            # id they carry. A client id proves identity only between a pre-order row and the
            # confirmed order it became.
            hit = None
            ids = ids[:1]
        if hit is None:
            entry = {"leg": leg, "frac": frac, "src": l, "pending": pending}
            kept.append(entry)
            for _name, i in ids:
                where[i] = entry
            l["disposition"] = "retained"
            continue
        name, entry = hit
        if entry["leg"]["key"] != leg["key"]:
            # one order under two different plays cannot be resolved by this tool
            bad["same venue order under two play keys"] = bad.get(
                "same venue order under two play keys", 0) + 1
            l["disposition"] = "unresolved"
            continue
        same_row = entry["src"].get("row_index") == l.get("row_index")
        # A pending pre-order record and the confirmed order it became are one attempt. The
        # CONFIRMED record is kept: it has the venue's id and the real price, where the pending
        # one could only be valued as an upper bound.
        pend_pair = bool(l.get("intent_only")) != bool(entry["src"].get("intent_only"))
        take_new = (not l.get("intent_only")) if pend_pair else frac > entry["frac"]
        reason = (f"same {name}, " + ("same row in two fields" if same_row else "two rows")
                  + (": pending record and its confirmed order" if pend_pair else
                     ("" if abs(frac - entry["frac"]) < 1e-9 else ", stakes differ: larger kept")))
        summary["dup_reasons"][reason] = summary["dup_reasons"].get(reason, 0) + 1
        summary["duplicate"] += 1
        l["disposition"], l["dup_of_proven"] = "duplicate", entry["src"].get("evidence_class")
        if take_new:
            # keep the larger commitment, and the retained identity moves with it
            entry["src"]["disposition"], l["disposition"] = "duplicate", "retained"
            entry["src"]["dup_of_proven"] = l.get("evidence_class")
            entry.update(leg=leg, frac=frac, src=l, pending=pending)
        for _name, i in ids:
            where[i] = entry
    if bad:
        return [], summary, ("order(s) that cannot be resolved or valued: "
                             + "; ".join(f"{v} x {k}" for k, v in sorted(bad.items())))
    per_play = {}
    for e in kept:
        leg, l = e["leg"], e["src"]
        per_play[leg["key"]] = per_play.get(leg["key"], 0.0) + e["frac"]
        ln = l.get("lane") or "unknown"
        summary["by_lane"][ln] = summary["by_lane"].get(ln, 0) + 1
        summary["unproven_retained_in_full"] += 1 if l.get("evidence_class") != RR.PROVEN else 0
        summary["pending_valued_as_risk"] += 1 if e["pending"] else 0
        l["held_in_full"] = (leg["status"] == "open"
                             and abs(float(leg["asked_stake"]) - float(l.get("asked_stake"))) < 0.005)
    summary["retained"] = len(kept)
    summary["plays"] = len(per_play)
    summary["plays_at_or_over_one_unit"] = sum(1 for v in per_play.values() if v >= 1.0 - 1e-9)
    total = sum(summary[k] for k in ("retained", "proven_zero", "never_submitted", "duplicate"))
    if total != summary["input"]:
        return [], summary, f"accounting does not close: {total} dispositions for {summary['input']} legs"
    return [e["leg"] for e in kept], summary, None


def detail_lines(legs, prior_utc):
    """Per-order lines for the orders that need individual attention - WITHOUT any identifier,
    key, price or amount. The identity comparison happens above, in memory; what is printed is the
    venue, a fixed-vocabulary reason, the disposition and yes/no facts."""
    out = []
    unproven = [l for l in legs if l.get("evidence_class") != RR.PROVEN]
    for n, l in enumerate(unproven, 1):
        new = bool(prior_utc and (l.get("decided_utc") or "") > prior_utc)
        out.append(f"unproven {n}/{len(unproven)}: {l.get('book')} | {RR.reason_code(l)} | "
                   f"{'pending pre-order record' if l.get('intent_only') else 'confirmed order row'} | "
                   f"disposition {l.get('disposition')} | held at full asked stake "
                   f"{'YES' if l.get('held_in_full') else ('n/a' if l.get('disposition') != 'retained' else 'NO')}"
                   + (f" | duplicate of a retained order that is {l.get('dup_of_proven')}"
                      if l.get("disposition") == "duplicate" else "")
                   + f" | new since prior snapshot {'YES' if new else 'no'}")
    fresh = [l for l in legs if prior_utc and (l.get("decided_utc") or "") > prior_utc]
    for n, l in enumerate(fresh, 1):
        out.append(f"new row {n}/{len(fresh)}: {l.get('book')} | lane {l.get('lane') or 'unknown'} | "
                   f"{l.get('evidence_class')} | "
                   f"{'pending pre-order record' if l.get('intent_only') else 'confirmed order row'} | "
                   f"has client id {'YES' if l.get('cid') else 'no'} | "
                   f"disposition {l.get('disposition')}")
    return out, len(fresh)


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
    print("SEED: " + " | ".join(f"{k} {v}" for k, v in summary.items()
                                if k not in ("by_lane", "dup_reasons")), flush=True)
    print("SEED: accounting " + ("CLOSES" if sum(summary[k] for k in (
        "retained", "proven_zero", "never_submitted", "duplicate")) == summary["input"]
        else "DOES NOT CLOSE") + " - every input leg has exactly one disposition", flush=True)
    print("SEED: duplicates by proof " + ("; ".join(
        f"{v} x {k}" for k, v in sorted(summary["dup_reasons"].items())) or "none"), flush=True)
    prior = (os.environ.get("SEED_PRIOR_SNAPSHOT_UTC") or "").strip()
    lines, n_new = detail_lines(legs, prior)
    print(f"SEED: rows new since the prior snapshot ({prior or 'not given'}): {n_new}", flush=True)
    for ln in lines:
        print("SEED: " + ln, flush=True)
    print("SEED: by lane " + ("; ".join(f"{v} x {k}" for k, v in sorted(summary["by_lane"].items()))
                              or "none"), flush=True)
    if refusal:
        print(f"SEED: REFUSED - {refusal}. Nothing written.", flush=True)
        return 1
    import registry
    import review_store_registry as rs
    import review_unit_reservation as R
    import review_intents as RI
    confirm = (os.environ.get("SEED_CONFIRM") or "").strip()
    store = rs.RegistryStore(registry)
    intents = rows                                   # pre-order rows live in `orders`
    zero_ids = [f"{l.get('book')}|{l.get('order_id')}" for l in legs
                if l.get("disposition") == "proven_zero"]
    got = store.read()
    if not got or got[0] is None:
        print("SEED: ledger unreadable - nothing written", flush=True)
        return 1
    already = got[0].get(R.SEEDED) is True
    print(f"SEED: ledger currently {'SEEDED' if already else 'not seeded'} | "
          f"legs in ledger {len(got[0].get('legs') or [])}", flush=True)

    def _show(c, label):
        print(f"SWEEP ({label}): " + " | ".join(f"{k} {v}" for k, v in c.items()), flush=True)

    if confirm == RELEASE or (not confirm and already):
        import review_unit_reservation as _R
        cids, why = stuck_never_submitted(store, rows)
        if cids is None:
            print(f"RELEASE: {why} - nothing done", flush=True)
            return 1
        print(f"RELEASE: legs holding a unit for a never-submitted order: {len(cids)}", flush=True)
        if confirm == RELEASE:
            freed = 0
            for c in cids:
                try:
                    freed += _R.release_never_submitted(
                        store, c, "one-off repair: registry rows prove never submitted", rows=rows)
                except Exception as ex:
                    print(f"RELEASE: refused for one leg ({type(ex).__name__})", flush=True)
            back = store.read()
            bl = (back[0] or {}).get("legs") or []
            print(f"RELEASE: freed {freed} | ledger legs {len(bl)} | "
                  f"still held {sum(1 for l in bl if str(l.get('status') or '').lower() in _R.LIVE_STATES)}",
                  flush=True)
            return 0
        print("RELEASE: dry run - dispatch with confirm=RELEASE to apply.", flush=True)
    if already:
        # The seed is a one-time act. On a seeded ledger the only thing left to do is the sweep.
        try:
            _show(RI.sweep(store, intents, write=(confirm == SWEEP)),
                  "WRITTEN" if confirm == SWEEP else "dry run - confirm=SWEEP to write")
        except Exception as ex:
            print(f"SWEEP: REFUSED - {type(ex).__name__}: {str(ex)[:120]}", flush=True)
            return 1
        return 0
    # What the sweep would add on top of this seed - shown BEFORE anything is written.
    try:
        sim = [dict(l, backfilled=True) for l in seed]
        _show(RI.sweep(_Mem({"legs": sim, R.SEEDED: True, RI.EXCLUDED: zero_ids}), intents,
                       write=True),
              "what the seed's sweep would add - nothing written")
    except Exception as ex:
        print(f"SWEEP: preview failed - {type(ex).__name__}. Nothing written.", flush=True)
        return 1
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
    back = store.read()
    ok = bool(back and back[0] and back[0].get(R.SEEDED) is True
              and len(back[0].get("legs") or []) >= n)
    print(f"SEED: read-back {'CONFIRMED' if ok else 'FAILED'} - "
          f"{len((back[0] or {}).get('legs') or []) if back and back[0] else 0} leg(s) in the ledger",
          flush=True)
    if not ok:
        return 1
    if not RI.note_excluded(store, zero_ids):
        print("SEED: could not record the proven-zero exclusions - the sweep would re-add them. "
              "Re-run with confirm=SWEEP after checking.", flush=True)
        return 1
    try:
        _show(RI.sweep(store, intents, write=True), "WRITTEN with the seed")
    except Exception as ex:
        print(f"SWEEP: FAILED after the seed - {type(ex).__name__}. Re-run with confirm=SWEEP.",
              flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
