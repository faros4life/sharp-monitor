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


def order_state_snapshot():
    """({order_id: row}, note, complete). The home runner's per-order venue read.

    WHY THIS EXISTS. GET /v3/portfolio/orders answers HTTP 401 with the read key AND the trading
    key, from the cloud AND from the home PC - that list route is not available to us at all, so
    venue_reads()["orders"] is permanently empty and a RESTING order could never be ruled out.
    novig_open_orders.py on the runner asks the per-order route instead (GET /v3/orders/{id}),
    which this repo has used in production since Oct 28.

    ITS LIMIT IS THE POINT. It can only ask about order ids somebody already knows. It can rule a
    known order OUT (terminal status) and it can confirm one, but it can NEVER rule out an order
    whose id was never recorded - there is no enumeration. So its completeness flag means "every
    id we asked about answered", never "we have seen everything Novig holds", and nothing here may
    read a row's absence from it as evidence.
    """
    try:
        import book_live as b
        url = NV_ORDER_STATE if "NV_ORDER_STATE" in globals() else (
            f"https://api.github.com/repos/{b.NV_REPO}/contents/snapshot/novig_open_orders.json?ref=main")
        st, doc = b._gh("GET", url)
    except Exception as ex:
        return {}, f"unreadable ({type(ex).__name__}: {str(ex)[:60]})", False
    try:
        import base64
        d = json.loads(base64.b64decode((doc or {}).get("content") or "").decode() or "{}")
    except Exception as ex:
        return {}, f"unparseable ({type(ex).__name__})", False
    by = {str(o.get("order_id")): o for o in (d.get("orders") or []) if o.get("order_id")}
    note = (f"{d.get('snapshot_utc', '?')}: asked {d.get('asked', '?')}, answered "
            f"{d.get('answered', '?')}, complete={d.get('complete')}")
    if d.get("errors"):
        note += f" | errors: {str(d['errors'])[:80]}"
    return by, note, bool(d.get("complete"))


def evidence():
    """(entries, do_not_touch, note). Facts proved once from sources that expire.

    Read-only and advisory: an entry LABELS a row. Nothing here releases a claim, clears a latch
    or writes to any store - that stays Peter's manual INTENT CLEARED email.
    """
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "novig_recon_evidence.json")) as f:
            d = json.load(f)
    except FileNotFoundError:
        return [], [], "no evidence file (novig_recon_evidence.json absent)"
    except Exception as ex:
        return [], [], f"evidence file unreadable ({type(ex).__name__})"
    e = d.get("entries") or []
    return e, (d.get("do_not_touch") or []), f"{len(e)} entry(ies), recorded {d.get('recorded_utc', '?')}"


def evidence_for(entries, row, at_runner):
    """The entry that covers this registry row, or None. Matches on client id first (exact), then
    on play key - and a play-key entry may demand that the runner recorded nothing, so it cannot
    reach a sibling attempt on the same play that DID produce a record."""
    cid, key = row.get("cid") or "", row.get("key") or ""
    for e in entries:
        m = e.get("match") or {}
        if cid and cid in (m.get("client_ids") or []):
            return e
        if m.get("order_ids") and row.get("oid") and row["oid"] in m["order_ids"]:
            return e
    for e in entries:
        m = e.get("match") or {}
        pk = m.get("play_key")
        if not pk or pk not in key:
            continue
        if m.get("only_when_no_runner_record") and at_runner:
            continue
        return e
    return None


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

    # Pagination, as the working reader in clv_link_recon does it and as the venue requires:
    #   - keyId is MANDATORY per wallet. Without it the API answers HTTP 400 AFTER_NEEDS_KEY_ID,
    #     which is what my first version got. Both wallets are read, as the executor does: the main
    #     one and the auto-place sub-wallet.
    #   - the cursor is the RESPONSE's own "next", not the last row's id.
    #   - partial pages are KEPT when a later page fails. Discarding them would turn a partial read
    #     into "venue shows nothing", which is the exact mistake this whole job exists to prevent.
    wallets = [w for w in dict.fromkeys([nv._S.get("id"),
                                         (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()]) if w]
    if not wallets:
        out["errors"]["wallets"] = "no key id available to scope a portfolio read"
        return out
    out["wallets"] = len(wallets)
    for name, path in (("fills", "/v3/portfolio/fills"), ("orders", "/v3/portfolio/orders")):
        rows, failed = [], None
        for kid in wallets:
            after, pages = None, 0
            while pages < 40:
                pages += 1
                prm = {"limit": 100, "keyId": kid}
                if after:
                    prm["after"] = after
                try:
                    d = nv.get(path, prm)
                except Exception as ex:
                    failed = f"{type(ex).__name__}: {str(ex)[:70]}"
                    break
                got, nxt = [], None
                for v in (d.values() if isinstance(d, dict) else [d]):
                    if isinstance(v, list):
                        got += v
                    elif isinstance(v, dict):
                        got += v.get("items") or v.get(name) or v.get("data") or []
                        nxt = nxt or v.get("next")
                if isinstance(d, dict):
                    nxt = nxt or d.get("next")
                rows += got
                if not got or not nxt:
                    break
                after = nxt
        out[name] = rows
        # A read is only "ok" - good enough to rule an order OUT - if NOTHING failed. A partial
        # read can CONFIRM (a match is a match) but can never rule out.
        out["ok"][name] = failed is None
        if failed:
            out["errors"][name] = failed + (f" (kept {len(rows)} row(s) read before the failure)" if rows else "")
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
    say(f"  wallets read: {v.get('wallets', 0)}")
    for name in ("fills", "orders"):
        if v["errors"].get(name):
            say(f"  {name:<7} INCOMPLETE: {v['errors'][name]}")
            say(f"          -> can still CONFIRM a match, can NEVER rule one out")
        else:
            say(f"  {name:<7} {len(v[name])} row(s) read, complete")
    for k, e in v["errors"].items():
        if k in ("import", "key"):
            say(f"  venue unreachable ({k}): {e}")
    venue_fills_ok = bool(v["ok"].get("fills"))
    venue_orders_ok = bool(v["ok"].get("orders"))
    if not venue_orders_ok:
        say("  NOTE: the portfolio ORDERS list is unavailable to us on every key tried, from the")
        say("        cloud and from the home PC. Per-order state comes from the runner instead:")

    states, snote, states_ok = order_state_snapshot()
    say()
    say("3b. ORDER STATE - the home runner's per-order venue read (GET /v3/orders/{id})")
    say("-" * 100)
    say(f"  {snote}")
    say(f"  {len(states)} order id(s) with a venue status")
    say("  Asks only about ids already known. Can rule a KNOWN order out; can never rule out an")
    say("  order whose id was never recorded, so absence from this list proves nothing.")
    live = [o for o in states.values() if o.get("resting")]
    if live:
        say(f"  {len(live)} order(s) currently RESTING at the venue - reported only, never touched:")
        for o in live:
            say(f"    {o['order_id']}  {o.get('status')}  qty {o.get('qty')} remaining {o.get('remaining')}")

    ev, dnt, enote = evidence()
    say()
    say("3c. DURABLE EVIDENCE - facts proved once from sources that expire")
    say("-" * 100)
    say(f"  {enote}")
    for e in ev:
        say(f"    {e.get('kind','?'):<22} {e.get('verdict','?')}")
    say("  Advisory only: labels a row, releases nothing. Clearing a claim or an intent latch stays")
    say("  Peter's manual, subject-only INTENT CLEARED email.")
    for o in dnt:
        say(f"  DO NOT TOUCH: {o.get('order_id')} {o.get('status')} qty {o.get('qty')} - {str(o.get('note'))[:70]}")

    # ------------------------------------------------------------------ the join
    say()
    say("4. VERDICTS - clientId / orderId matched across all three sources")
    say("-" * 100)
    runner_ids, venue_ids = set(), set()
    for r in rows:
        runner_ids |= ident(r)
    for r in v["fills"] + v["orders"]:
        venue_ids |= ident(r)
    counts, why = {}, {}
    for r in reg:
        ids = {x for x in (r["cid"], r["oid"]) if x}
        at_venue = bool(ids & venue_ids)
        at_runner = bool(ids & runner_ids)
        # Per-order state for an id we actually hold. Terminal (FILLED/CANCELED/REJECTED/EXPIRED)
        # means the order can neither rest nor fill, which is what rules a RESTING order out.
        st = next((states[i] for i in ids if i in states), None)
        ev_hit = None
        src = ""
        if at_venue:
            verdict = "CONFIRMED AT VENUE"          # a live match always wins over recorded evidence
        elif st and st.get("terminal"):
            verdict = ("RULED OUT - terminal at venue, nothing filled" if not st.get("filled_qty")
                       else "CONFIRMED AT VENUE")
            src = f"venue status {st.get('status')}, remaining {st.get('remaining')} of {st.get('qty')}"
        elif st and st.get("resting"):
            verdict = "LIVE - resting at venue right now (untouched)"
            src = f"venue status {st.get('status')}, remaining {st.get('remaining')}"
        else:
            ev_hit = evidence_for(ev, r, at_runner)
            if ev_hit:
                verdict = ev_hit.get("verdict") or "UNRESOLVED - evidence entry has no verdict"
                src = f"evidence[{ev_hit.get('id')}] {ev_hit.get('source', '')[:60]}"
            elif not venue_fills_ok:
                verdict = "UNRESOLVED - venue unreadable"
            elif at_runner:
                verdict = "UNRESOLVED - runner recorded it, no fill and no order state"
            else:
                # DELIBERATELY NOT "ruled out". This branch used to read a missing runner record
                # plus a complete venue read as proof the order never existed. It is not proof:
                # novig_live_order.place() appends its record AFTER the POST returns, so a crash
                # in that window leaves a venue order with no runner record and no id anywhere -
                # and with no list endpoint, an id we never knew cannot be looked up. Absence of a
                # record is not absence of an order.
                verdict = "UNRESOLVED - no runner record (absence is not proof; see POST-window note)"
        counts[verdict] = counts.get(verdict, 0) + 1
        why[verdict] = src or why.get(verdict, "")
        say(f"    {r['cid'][:38]:<38} runner={'Y' if at_runner else 'n'} venue={'Y' if at_venue else 'n'}"
            f" state={'Y' if st else 'n'} ev={'Y' if ev_hit else 'n'}  {verdict}")
        if r["key"]:
            say(f"        {r['key'][:88]}")
        if src:
            say(f"        via {src[:88]}")
    say()
    for k, n in sorted(counts.items()):
        say(f"  {n:>3}  {k}")
    unresolved = sum(n for k, n in counts.items() if k.startswith("UNRESOLVED"))
    say()
    say(f"  {unresolved} id(s) UNRESOLVED -> duplicate submission stays blocked for those plays.")
    say("  A RULED OUT verdict does NOT release anything either: every submission claim and every")
    say("  intent latch stays exactly as it is until Peter sends the manual, subject-only")
    say("  INTENT CLEARED email. Nothing here clears a latch, resolves an intent, or writes to any")
    say("  store, and no resting order is ever cancelled or amended.")
    say()
    say("  The three ruled-out kinds are not interchangeable:")
    say("    terminal at venue     - the venue itself reported a terminal status for a known id")
    say("    pre-execution failure - positive proof the order code never ran; no venue read needed")
    say("    no dispatch evidence  - NOT proof, only absence of one. Those rows stay UNRESOLVED.")
    say()
    say("=" * 100)
    say("READ-ONLY: no order placed, amended or cancelled; no registry write; no live setting changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
