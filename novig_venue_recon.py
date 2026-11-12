#!/usr/bin/env python3
"""NOVIG VENUE RECONCILIATION + OUTSTANDING INTENTS (Peter, Nov 12). READ-ONLY. WRITES NOTHING.

Peter: "add a read-only venue reconciliation path through the home runner. Match clientId,
orderId, fills, and open orders against the registry. If an order cannot be confirmed, leave it
unresolved and block any duplicate submission. Never assume an order does not exist merely because
the snapshot is missing it."

WHY THE OLD RECON COULD NOT ANSWER. novig_recon.main() takes ids from a hand-supplied
NOVIG_ORDER_IDS and looks each one up in the home runner's snapshot/novig_orders.json:

    r = by.get(str(oid))
    if not r:
        out.append({"id": oid, "reconciled": False})

The runner's results file is its ONLY source. If the runner never wrote a row, the recon reports
"not found" - which is indistinguishable from "no such order ever existed". That is how the 11:57
run reported 2 unreconciled as bare {"id": ..., "reconciled": false} rows with no status, qty or
error. Absence of a record is not evidence of absence of an order.

This adds the venue itself as an independent second source, and keeps the two separable:

    REGISTRY   what the bot believes it did        (REGISTRY_TOKEN, contents read)
    RUNNER     what the home PC recorded doing     (NOVIG_READ_TOKEN / NOVIG_SNAPSHOT_TOKEN)
    VENUE      what Novig actually holds           (NOVIG_READ_KEY_ID / _PEM, GET only)

A fill carries clientId, orderId and fillId (measured Nov 12: 28 of 35 tracker rows matched on
fill.clientId), so the venue can confirm an order the runner lost. Ruling one OUT is the harder
direction and is only ever claimed when a venue read actually SUCCEEDED and covered the window -
never from an empty or failed read. Everything else stays UNRESOLVED, which is the state that
keeps duplicate submission blocked.

Writes nothing: no order placed, amended or cancelled, no registry write, no live setting touched.
"""
import json
import os
import sys
from datetime import datetime, timezone

VERDICT = {}


def say(t=""):
    print(t)


def ident(rec):
    """Every id a row can be matched on, as strings."""
    out = set()
    for k in ("client_id", "clientId", "order_id", "orderId", "id", "fillId"):
        v = rec.get(k) if isinstance(rec, dict) else None
        if v:
            out.add(str(v))
    for k in ("live_order", "live_rest"):
        lo = (rec.get(k) or {}) if isinstance(rec, dict) else {}
        for kk in ("client_id", "order_id"):
            if lo.get(kk):
                out.add(str(lo[kk]))
    return out


# ------------------------------------------------------------------ 1. the registry (bot belief)
def registry_unresolved():
    """(rows, note). Orders/intents the bot cannot show a confirmed venue result for."""
    try:
        import registry
    except Exception as ex:
        return None, f"registry module unavailable ({type(ex).__name__})"
    if not registry.enabled():
        return None, "REGISTRY_TOKEN not set - the bot's own belief cannot be read"
    try:
        d = registry.load()
    except Exception as ex:
        return None, f"registry unreadable ({type(ex).__name__}: {str(ex)[:60]})"
    if d is None:
        return None, "registry unreadable (load returned None)"
    out = []
    for r in (d.get("orders") or []):
        for k in ("live_order", "live_rest"):
            lo = r.get(k) or {}
            if not lo:
                continue
            if lo.get("book") and str(lo["book"]) != "novig":
                continue
            # An intent with no fill reading, or a voided row, or anything still marked intent.
            if lo.get("voided"):
                continue          # refused before submission - never transmitted, nothing to reconcile
            if lo.get("intent") or lo.get("filled_stake") is None:
                out.append({"cid": str(lo.get("client_id") or ""), "oid": str(lo.get("order_id") or ""),
                            "key": str(r.get("key") or ""), "when": str(r.get("decided_utc") or ""),
                            "asked": lo.get("asked_stake"), "intent": bool(lo.get("intent")),
                            "status": str(lo.get("status") or "")})
    return out, f"{len(d.get('orders') or [])} order row(s), {len(d.get('intents') or [])} intent row(s)"


# ------------------------------------------------------------------ 2. the runner (home PC record)
def runner_rows():
    try:
        import book_live as b
        st, doc = b._gh("GET", b.NV_RESULTS)
    except Exception as ex:
        return None, f"runner results unreadable ({type(ex).__name__}: {str(ex)[:60]})"
    try:
        import base64
        raw = base64.b64decode((doc or {}).get("content") or "")
        return (json.loads(raw.decode() or "{}").get("orders") or []), None
    except Exception as ex:
        return None, f"runner results unparseable ({type(ex).__name__})"


# ------------------------------------------------------------------ 3. the venue (ground truth)
def venue_reads():
    """{'fills': [...], 'orders': [...], 'errors': {...}} - each read reported separately, because
    a read that FAILED must never be mistaken for a read that returned nothing."""
    out = {"fills": [], "orders": [], "errors": {}, "ok": {}}
    try:
        import novig_signed as nv
    except Exception as ex:
        out["errors"]["import"] = f"{type(ex).__name__}"
        return out
    if not nv.ready():
        out["errors"]["key"] = "NOVIG_READ_KEY_ID / NOVIG_READ_KEY_PEM not usable"
        return out

    def unwrap(d):
        """Novig returns a dict KEYED BY WALLET; read_positions() unwraps with d.values(). Parsing
        it as items/fills/data read 0 rows on the first attempt - that was a reader bug, not an
        empty account."""
        got = []
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    got += v
                elif isinstance(v, dict):
                    got += v.get("items") or v.get("fills") or v.get("orders") or v.get("data") or []
        elif isinstance(d, list):
            got = d
        return got

    for name, path in (("fills", "/v3/portfolio/fills"), ("orders", "/v3/portfolio/orders")):
        rows, after, pages = [], None, 0
        try:
            while pages < 40:          # 100 rows a page; 2 wallets gave 130 fills, so paginate
                pages += 1
                prm = {"limit": 100}
                if after:
                    prm["after"] = after
                got = unwrap(nv.get(path, prm))
                if not got:
                    break
                rows += got
                nxt = got[-1].get("fillId") or got[-1].get("orderId") or got[-1].get("id")
                if not nxt or nxt == after:
                    break
                after = nxt
            out[name] = rows
            out["ok"][name] = True
        except Exception as ex:
            out["errors"][name] = f"{type(ex).__name__}: {str(ex)[:70]}"
            out["ok"][name] = False
    return out


def main():
    say("NOVIG VENUE RECONCILIATION + OUTSTANDING INTENTS")
    say(f"generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z | READ-ONLY (GET only) | writes nothing")
    say("=" * 100)

    reg, rnote = registry_unresolved()
    say()
    say("1. REGISTRY - what the bot believes it did")
    say("-" * 100)
    say(f"  {rnote}")
    if reg is None:
        say("  CANNOT VERIFY from the registry; falling back to the ids given in NOVIG_ORDER_IDS only")
        reg = []
    extra = [x.strip() for x in (os.environ.get("NOVIG_ORDER_IDS") or "").split(",") if x.strip()]
    for x in extra:
        if not any(r["cid"] == x or r["oid"] == x for r in reg):
            reg.append({"cid": x, "oid": "", "key": "(supplied by hand)", "when": "",
                        "asked": None, "intent": False, "status": ""})
    say(f"  {len(reg)} Novig row(s) with no confirmed result (including {len(extra)} supplied by hand)")
    for r in reg:
        say(f"    {r['cid'][:38]:<38} {'INTENT' if r['intent'] else r['status'] or 'order':<8} {r['key'][:40]}")

    rows, rerr = runner_rows()
    say()
    say("2. RUNNER - what the home PC recorded doing")
    say("-" * 100)
    if rows is None:
        say(f"  UNREADABLE: {rerr}")
        say("  -> every id below stays UNRESOLVED. An unreadable record is not an absent order.")
        rows = []
        runner_ok = False
    else:
        say(f"  {len(rows)} result row(s) in snapshot/novig_orders.json")
        runner_ok = True

    v = venue_reads()
    say()
    say("3. VENUE - what Novig actually holds (independent second source)")
    say("-" * 100)
    for name in ("fills", "orders"):
        if v["errors"].get(name):
            say(f"  {name:<7} READ FAILED: {v['errors'][name]}")
        else:
            say(f"  {name:<7} {len(v[name])} row(s) read")
    for k, e in v["errors"].items():
        if k in ("import", "key"):
            say(f"  venue unreachable ({k}): {e}")
    venue_fills_ok = bool(v["ok"].get("fills"))
    venue_orders_ok = bool(v["ok"].get("orders"))
    if not venue_orders_ok:
        say("  NOTE: open orders could not be read, so a RESTING order cannot be ruled out here.")
        say("        That limits every RULED OUT verdict below to orders that would have FILLED.")

    # ------------------------------------------------------------------ the join
    say()
    say("4. VERDICTS - clientId / orderId matched across all three sources")
    say("-" * 100)
    runner_ids, venue_ids = set(), set()
    for r in rows:
        runner_ids |= ident(r)
    for r in v["fills"] + v["orders"]:
        venue_ids |= ident(r)
    counts = {}
    for r in reg:
        ids = {x for x in (r["cid"], r["oid"]) if x}
        at_venue = bool(ids & venue_ids)
        at_runner = bool(ids & runner_ids)
        if at_venue:
            verdict = "CONFIRMED AT VENUE"
        elif not venue_fills_ok:
            verdict = "UNRESOLVED - venue unreadable"
        elif not venue_orders_ok:
            verdict = "UNRESOLVED - no fill, open orders unreadable"
        elif at_runner:
            verdict = "UNRESOLVED - runner recorded it, venue shows nothing"
        else:
            verdict = "RULED OUT - never reached the venue"
        counts[verdict] = counts.get(verdict, 0) + 1
        say(f"    {r['cid'][:38]:<38} runner={'Y' if at_runner else 'n'} venue={'Y' if at_venue else 'n'}  {verdict}")
        if r["key"]:
            say(f"        {r['key'][:88]}")
    say()
    for k, n in sorted(counts.items()):
        say(f"  {n:>3}  {k}")
    unresolved = sum(n for k, n in counts.items() if k.startswith("UNRESOLVED"))
    say()
    say(f"  {unresolved} id(s) UNRESOLVED -> duplicate submission stays blocked for those plays.")
    say("  Nothing here clears a latch, resolves an intent, or writes to any store. Clearing an")
    say("  intent remains Peter's manual, subject-only INTENT CLEARED email.")
    say()
    say("=" * 100)
    say("READ-ONLY: no order placed, amended or cancelled; no registry write; no live setting changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
