#!/usr/bin/env python3
"""
NOVIG ORDER STATUS READBACK - READ-ONLY (Peter, 19 Nov 2026).

WHY. A Telegram alert read "[BOARD V4] NOVIG NO FILL ... limit -102, $205.53 asked; nothing
traded". The registry holds exactly ONE row for that play: a journal row whose only order is a
RESTING Novig bid (resting: true, status: placed, filled_stake: null, expires 2026-11-20T00:30Z)
and whose live_order is null. "Nothing traded" is therefore our inference from a fill read, not a
venue answer, and Peter's instruction is that the money stays UNRESOLVED EXPOSURE until Novig
confirms the order: open, partially filled, canceled or filled.

WHAT IT DOES, AND ONLY THIS. For every Novig order in the private registry whose stored state
leaves the outcome open, read the venue:
  * GET /v3/orders/{id}        - status and qty/remaining
  * GET /v3/portfolio/fills    - what actually traded
Novig's own guidance, recorded in novig_live_order.order_state's docstring: "a partly filled order
stays OPEN - track remaining, not the status". So remaining is read, not inferred from the status.

THE CREDENTIAL, NOT JUST THE CODE. This goes through novig_signed, the repo's READ-ONLY client: it
has no POST/PUT/PATCH/DELETE path at all, and it refuses to run unless its key's own scope reads
back as read-only. A dedicated NOVIG_READ_KEY exists, so this probe never touches the trading key -
which is a stronger guarantee than a test asserting my code behaves, because a read-scoped key
cannot place an order even if the code tried.
Nothing is cancelled even if an order is found open past its intended cutoff: that is a
live-betting change and needs Peter's explicit yes. This escalates instead.

Counts and prices only in the log, per the repo rule - no dollar figures.
"""
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import novig_signed as nv
import registry as rg

OPEN_STATES = ("PENDING", "OPEN")
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def main():
    now = datetime.now(timezone.utc)
    say("NOVIG ORDER STATUS READBACK - READ-ONLY, GET only, nothing cancelled")
    say(f"generated {now.astimezone(cl.ET):%Y-%m-%d %H:%M} ET")
    say("=" * 104)
    if not nv.ready():
        say("FATAL: no read-only Novig key available (novig_signed refuses a write-scoped key), so "
            "the venue cannot be read, and this probe refuses to "
            "report a status it could not read.")
        return 1
    say(f"read-only client ready; key scope {nv.scope()!r}")
    reg = rg.load()
    if reg is None:
        say("FATAL: private registry unreadable - the order list comes from there, and guessing "
            "it would be worse than failing.")
        return 1

    want = {}
    for row in (reg.get("orders") or []):
        for fld in ("live_order", "live_rest"):
            lo = row.get(fld) or {}
            if not isinstance(lo, dict) or lo.get("book") != "novig" or not lo.get("order_id"):
                continue
            oid = str(lo["order_id"])
            # Unresolved by OUR record: placed, and the fill was never read back. These are the
            # ones whose money is neither a confirmed loss nor a confirmed no-fill.
            if lo.get("status") == "placed" and lo.get("filled_stake") is None:
                want[oid] = (row, lo, fld)
    say(f"Novig orders whose outcome our record leaves OPEN: {len(want)}")
    if not want:
        say("None. NOTE: a statement about the REGISTRY, not about Novig - an order whose registry "
            "write failed would not appear here.")
        return 0
    say("")

    # /v3/orders/{id} is NOT readable with a read-only key - novig_live_order.order_state signs
    # with the TRADING key, which this job is deliberately not given, and clv_link_recon already
    # records the same thing. The first version of this probe called it anyway and got
    # NovigReadError on all 28 orders while the fills endpoint answered fine; 28 unreadable orders
    # was never the likely reading - the endpoint was. The portfolio LIST is the read-only route.
    PORTFOLIO, PORT_OK = {}, False
    try:
        od = nv.get("/v3/portfolio/orders", {"limit": 200})
        items = []
        for v in ((od or {}).values() if isinstance(od, dict) else [od]):
            if isinstance(v, list):
                items += v
            elif isinstance(v, dict):
                items.append(v)
        if isinstance(od, list):
            items = od
        for it in items:
            if isinstance(it, dict):
                i = str(it.get("id") or it.get("orderId") or it.get("order_id") or "")
                if i:
                    PORTFOLIO[i] = it
        PORT_OK = True
        say(f"/v3/portfolio/orders returned {len(PORTFOLIO)} order(s) to match against")
    except Exception as ex:
        say(f"/v3/portfolio/orders UNREADABLE ({type(ex).__name__}: {str(ex)[:70]}) - every order "
            f"below is UNRESOLVED for that reason alone, which is a fact about the READ, not "
            f"about the orders")
    say("")

    rows, unresolved = [], 0
    for oid, (row, lo, fld) in sorted(want.items(), key=lambda kv: str(kv[1][0].get("decided_utc") or "")):
        key = str(row.get("key") or "").replace("|", " ")[:50]
        status, filled_qty = None, None
        o = PORTFOLIO.get(oid)
        if o is None:
            why = "not in /v3/portfolio/orders" + ("" if PORT_OK else " (that list could not be read)")
            say(f"  UNREADABLE {oid[:12]} {key:<50} {why}")
        else:
            status = str(o.get("status") or "").upper() or None
            try:    # Novig: a partly filled order stays OPEN, so remaining is what decides
                filled_qty = int(o["qty"]) - int(o["remaining"])
            except (KeyError, TypeError, ValueError):
                filled_qty = None
        c = None
        try:
            fl = nv.get("/v3/portfolio/fills", {"limit": 100}) or {}
            items = fl if isinstance(fl, list) else (fl.get("items") or fl.get("fills")
                                                    or fl.get("data") or [])
            mine = [f for f in items if isinstance(f, dict) and str(f.get("orderId")
                    or f.get("order_id") or "") == oid]
            c = sum(float(f.get("qty") or 0) for f in mine) if mine else 0.0
        except Exception:
            c = None
        verdict = ("UNRESOLVED - venue did not answer" if status is None else
                   ("OPEN" if status in OPEN_STATES else status))
        if status is None:
            unresolved += 1
        rows.append((oid, key, fld, status, filled_qty, c, verdict,
                     str(lo.get("expires_utc") or ""), str(row.get("decided_utc") or "")))
        say(f"  {verdict:<30} {oid[:12]} {key:<50} [{fld}]")
        say(f"      venue status {status or 'UNREADABLE'} | filled qty "
            f"{'unknown' if filled_qty is None else filled_qty} | fill rows "
            f"{'unknown' if c is None else c} contracts"
            + (f" | our expiry {lo.get('expires_utc')}" if lo.get("expires_utc") else ""))

    say("")
    say("WHAT THIS SETTLES")
    say("-" * 104)
    for oid, key, fld, status, fq, c, verdict, exp, dec in rows:
        if status is None:
            say(f"  {key}: STILL UNRESOLVED. The venue did not answer, so the stake stays "
                f"unresolved exposure - not a loss, not a no-fill.")
        elif status in OPEN_STATES:
            say(f"  {key}: OPEN at Novig"
                + (f", partially filled ({fq} qty)" if fq else ", nothing filled yet")
                + f". The stake is LIVE RESTING EXPOSURE until it fills, is cancelled or expires"
                + (f" at {exp}" if exp else "") + ".")
        elif status == "FILLED":
            say(f"  {key}: FILLED at Novig ({fq} qty). Any 'NO FILL' message for it was wrong.")
        elif status in ("CANCELED", "CANCELLED", "REJECTED"):
            say(f"  {key}: {status} at Novig - no exposure, and nothing traded is CONFIRMED "
                f"rather than inferred.")
        else:
            say(f"  {key}: venue says {status} - outside the states this probe knows; treat as "
                f"unresolved and look at it by hand.")
    say("")
    if unresolved:
        say(f"  {unresolved} order(s) could not be read. An unreadable order is UNKNOWN exposure, "
            f"never a no-fill.")
    say("  NOTHING WAS CANCELLED. Cancelling a Novig order is a live-betting change and needs "
        "Peter's explicit yes.")
    say("")
    say("Counts and prices only. No dollar figures. Every venue call here was a GET.")
    os.makedirs("audit", exist_ok=True)
    json.dump({"generated": cl.iso(now), "checked": len(rows), "unresolved": unresolved},
              open("audit/novig_order_probe.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
