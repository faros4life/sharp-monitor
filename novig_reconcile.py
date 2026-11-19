#!/usr/bin/env python3
"""Reconcile registry legs against Novig's own order and fill records. PURE FUNCTIONS, NOT WIRED IN.

Peter approved implementing this and explicitly NOT activating the live risk-gate change, so nothing
here is imported by executor, live_guards or any gate. It exists to be tested and reviewed.

WHY THIS EXISTS - the identifier trap
-------------------------------------
The registry stores the VENUE'S CLIENT ID in its own `order_id` field for Novig legs. Joining
registry.order_id to novig_orders.order_id therefore matches NOTHING: 0 of 31 on the Nov 18 snapshot.
Joining registry.order_id to novig_orders.CLIENT_ID matches 31 of 31.

That near-miss is the dangerous kind. A reconciliation written the obvious way finds no venue record
for any leg and, if it treated absence as evidence, would "confirm" that nothing ever filled - while
eleven of those legs were FILLED at the venue. Absence of a record is never evidence here; only an
explicit venue status is. normalize_ids() exists so the join is written once, correctly, and the true
venue order id is preserved rather than overwritten (Peter, requirement 1).

CLASSES (requirement 3)
    FILLED             venue says FILLED and filled_qty > 0
    PARTIALLY FILLED   venue says terminal/open with 0 < filled_qty < qty
    OPEN               venue says OPEN - a live commitment, counted in full
    TERMINAL ZERO FILL venue says CANCELED / REJECTED / refused, filled_qty == 0, no fill record
    UNKNOWN            anything else, INCLUDING no venue record at all

Only TERMINAL ZERO FILL releases exposure. Age releases nothing (requirement 6): a leg is released by
what the venue says about it, never by how old it is.
"""
from datetime import datetime, timezone

RELEASABLE = ("CANCELED", "REJECTED", "REFUSED", "CANCELLED")
FILLED, PARTIAL, OPEN, TERMINAL, UNKNOWN = ("FILLED", "PARTIALLY FILLED", "OPEN",
                                            "TERMINAL ZERO FILL", "UNKNOWN")


def venue_index(novig_orders, novig_fills):
    """(by_client_id, fills_by_client_id) from the runner's snapshots.

    Keyed on CLIENT ID because that is what the registry's order_id actually holds. Keying on the
    venue order id is the mistake this module exists to prevent.
    """
    by_cid, fills = {}, {}
    for row in (novig_orders or {}).get("orders") or []:
        c = row.get("client_id")
        if c:
            by_cid[str(c)] = row
    for f in (novig_fills or {}).get("fills") or []:
        c = f.get("clientId")
        if c:
            fills.setdefault(str(c), []).append(f)
    return by_cid, fills


def normalize_ids(leg):
    """{'client_id': ..., 'venue_order_id': ...} for a registry leg.

    The registry's order_id is the venue's CLIENT id. The true venue order id is carried separately in
    venue_order_id when reconciliation has supplied it, so the original value is never overwritten and
    the audit trail survives (requirement 5).
    """
    return {"client_id": str(leg.get("order_id") or "") or None,
            "venue_order_id": str(leg.get("venue_order_id") or "") or None}


def usd(qty, price):
    """Novig dollars: one contract pays 1c, so dollars = qty x price / 100."""
    try:
        return round(float(qty or 0) * float(price or 0) / 100.0, 2)
    except Exception:
        return None


def classify(leg, by_cid, fills_by_cid):
    """(class, evidence) for one registry leg. Never releases on a missing record."""
    cid = normalize_ids(leg)["client_id"]
    if not cid:
        return UNKNOWN, {"why": "registry leg carries no identifier"}
    v = by_cid.get(cid)
    if not v:
        # REQUIREMENT 6: a missing API result is NOT proof of zero fills.
        return UNKNOWN, {"why": "no venue record for this client id", "client_id": cid}
    st = str(v.get("status") or "").upper()
    fq = float(v.get("filled_qty") or 0)
    qty = float(v.get("qty") or 0)
    ev = {"client_id": cid, "venue_order_id": v.get("order_id"), "venue_status": v.get("status"),
          "filled_qty": fq, "qty": qty, "filled_usd": usd(fq, v.get("price")),
          "asked_usd": usd(qty, v.get("price")), "fill_records": len(fills_by_cid.get(cid) or []),
          "placed_utc": v.get("placed_utc")}
    if st == "OPEN":
        return (PARTIAL if 0 < fq < qty else OPEN), ev
    if fq > 0:
        return (FILLED if (st == "FILLED" and fq >= qty) else PARTIAL), ev
    if st in RELEASABLE and fq == 0 and not (fills_by_cid.get(cid) or []):
        return TERMINAL, ev
    return UNKNOWN, ev


def exposure_for(leg, cls, ev):
    """Dollars this leg should count toward the daily stop, under the reconciled view.

    FILLED / PARTIAL count the ACTUAL filled amount (requirement 4). OPEN counts the whole commitment.
    TERMINAL counts nothing. UNKNOWN keeps whatever the registry already counted - unresolved never
    means released.
    """
    asked = float(leg.get("asked_stake") or 0)
    fs = leg.get("filled_stake")
    registry_amt = (max(float(fs or 0), asked) if (leg.get("resting") or fs is None) else float(fs))
    if cls == TERMINAL:
        return 0.0
    if cls in (FILLED, PARTIAL) and ev.get("filled_usd") is not None:
        return float(ev["filled_usd"])
    if cls == OPEN:
        return asked or registry_amt
    return registry_amt


def reconciliation_patch(leg, cls, ev, asof=None):
    """The fields to merge into the registry leg. IDEMPOTENT: same inputs -> same patch, and applying
    it twice leaves the row identical. Nothing in the original row is overwritten except by a value
    that reconciliation has actually established.
    """
    if cls == UNKNOWN:
        return {}
    p = {"venue_order_id": ev.get("venue_order_id"), "venue_status": ev.get("venue_status"),
         "venue_filled_usd": ev.get("filled_usd"), "reconciled_class": cls}
    p = {k: v for k, v in p.items() if v is not None}
    if p:
        p["reconciled_utc"] = (asof or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return p


def apply_patch(leg, patch):
    """Merge a patch, preserving audit history: the registry's original order_id and filled_stake are
    never altered, so the pre-reconciliation record remains readable (requirement 5).
    """
    out = dict(leg)
    for k, v in (patch or {}).items():
        if k in ("order_id", "filled_stake", "asked_stake", "book", "status"):
            continue                       # original audit fields are immutable here
        out[k] = v
    return out

# ---------------------------------------------------------------- live loading (Peter, Nov 18: activate)
SNAP_ORDERS = "snapshot/novig_orders.json"
SNAP_FILLS = "snapshot/novig_fills.json"


def load_venue(reg=None):
    """((by_client_id, fills_by_client_id), why) from the runner's snapshots, or ((None, None), why).

    FAILS CLOSED BY CONTRACT. Every caller must treat a None index as "no evidence" and count the
    registry's own figure unchanged - never as "nothing filled". A read failure must not be able to
    release a single dollar, which is the whole reason this returns a reason string instead of an
    empty pair of dicts.
    """
    try:
        if reg is None:
            import registry as reg
        if not reg.enabled():
            return (None, None), "registry disabled"
        o, e1 = reg.read_json(SNAP_ORDERS)
        if o is None:
            return (None, None), f"orders snapshot: {e1}"
        f, e2 = reg.read_json(SNAP_FILLS)
        if f is None:
            return (None, None), f"fills snapshot: {e2}"
        if not (f or {}).get("complete"):
            return (None, None), "fills snapshot not marked complete"
        by, fb = venue_index(o, f)
        if not by:
            return (None, None), "orders snapshot held no client ids"
        return (by, fb), f"ok ({len(by)} orders, {sum(len(v) for v in fb.values())} fills)"
    except Exception as ex:
        return (None, None), f"load failed: {str(ex)[:60]}"

