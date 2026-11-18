#!/usr/bin/env python3
"""
KALSHI RESTING-ORDER EXPIRY READBACK — READ-ONLY (Peter, 18 Nov 2026).

WHY. A resting-bid notification printed "383.7 still resting until None". kalshi_place() DOES send
time_in_force=good_till_canceled with expiration_time=start-30min, but it stores only what it SENT
(order) plus a 400-char slice of the response, and nothing anywhere reads the order back to see
what Kalshi actually STORED. The repo's own rule for the other transcoded venue is that acceptance
is never proof - Polymarket US took a 3-minute order and stored a day order with goodTillTime null.
Until the venue's own record is read, "we sent an expiry" is not "the order expires".

THE RISK BEING TESTED. If an expiry did not take, a resting bid stays fillable past the intended
30-minutes-before-start cutoff and can fill AFTER the game has started, at a pregame-priced number.
That is live exposure on a bet that was never meant to be live.

WHAT THIS DOES, AND ONLY THIS. GET /portfolio/orders/{id} for every Kalshi resting order in the
private registry, and report each one's venue-side status, expiration and remaining size against
the cutoff its game implies. Peter, 18 Nov: "If the venue can't confirm the pregame cutoff, the
order should be treated as potentially unsafe and escalated for cancellation - not assumed safe
because an expiry was included in the original request." So:

  * Every call is a GET. There is no POST, no DELETE, no cancel, no place. A test asserts that.
  * Nothing is cancelled here even when found unsafe. Cancelling a resting order is a live-betting
    change and needs Peter's explicit yes; this escalates instead.
  * Counts and prices only in the log, per the repo rule. No dollar figures.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import book_live
import clv_ledger as cl
import registry as rg

CUTOFF_MIN = 30          # executor.REST_BEFORE_MIN: resting bids are meant to expire this early
GRACE_MIN = 2            # tolerance when comparing the venue's stamp to our intended cutoff
RESTING = ("resting", "open", "active")
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def tp(x):
    """Kalshi returns expiration either as unix seconds or an ISO string, depending on the field."""
    if x is None or x == "":
        return None
    n = num(x)
    if n is not None and n > 1_000_000_000:
        return datetime.fromtimestamp(n, timezone.utc)
    return cl.tp(str(x))


def venue_expiry(o):
    """(datetime, which field) for whatever Kalshi stored, or (None, None).

    Several spellings are tried because the field that matters is the one the VENUE chose to
    return, not the one we sent. A missing expiry on a good_till_canceled order is the finding,
    so it must not be confused with 'we looked in the wrong key'.
    """
    for k in ("expiration_time", "expiration_ts", "expires_at", "expiration",
              "good_till_time", "expiration_time_unix"):
        if k in (o or {}):
            d = tp(o.get(k))
            if d:
                return d, k
    return None, None


def main():
    now = datetime.now(timezone.utc)
    say("KALSHI RESTING-ORDER EXPIRY READBACK - READ-ONLY, GET only, nothing cancelled")
    say(f"generated {now.astimezone(cl.ET):%Y-%m-%d %H:%M} ET   cutoff rule: start - {CUTOFF_MIN} min")
    say("=" * 100)
    if not (os.environ.get("KALSHI_KEY_ID") and os.environ.get("KALSHI_PRIVATE_KEY")):
        say("FATAL: Kalshi read credentials not present - cannot read the venue back, and this "
            "probe refuses to report on an order it could not read.")
        return 1
    reg = rg.load()
    if reg is None:
        say("FATAL: private registry unreadable - the resting-order list comes from there, and "
            "guessing it would be worse than failing.")
        return 1

    rests = {}
    for row in (reg.get("orders") or []):
        lo = row.get("live_rest") or {}
        if not isinstance(lo, dict):
            continue
        if lo.get("book") == "kalshi" and lo.get("order_id"):
            rests[str(lo["order_id"])] = (row, lo)
    say(f"Kalshi resting records in the registry: {len(rests)}")
    if not rests:
        say("No Kalshi resting order on record. Nothing to read back.")
        say("NOTE: this is a statement about the REGISTRY, not about Kalshi. An order placed by a "
            "run whose registry write failed would not appear here.")
        return 0

    buckets = {"CONFIRMED_SAFE": [], "UNSAFE_NO_EXPIRY": [], "UNSAFE_LATE_EXPIRY": [],
               "NOT_RESTING": [], "UNREADABLE": []}
    for oid, (row, lo) in sorted(rests.items()):
        key = str(row.get("key") or "").replace("|", " ")[:54]
        try:
            st_code, resp = book_live._k_call("GET", f"/portfolio/orders/{oid}")
            o = (resp or {}).get("order") or resp or {}
        except Exception as ex:
            buckets["UNREADABLE"].append((oid, key, f"{type(ex).__name__}: {str(ex)[:60]}"))
            continue
        status = str(o.get("status") or "").lower()
        rem = num(o.get("remaining_count_fp"))
        if rem is None:
            rem = num(o.get("remaining_count")) or 0.0
        exp, field = venue_expiry(o)
        # The cutoff this order SHOULD have: from the game's own start when we know it, else from
        # the expiry we recorded at placement. Our own record is the weaker source and is labelled.
        start = cl.tp(str(row.get("start_utc") or row.get("start") or "")) or None
        want = (start - timedelta(minutes=CUTOFF_MIN)) if start else cl.tp(str(lo.get("expires_utc") or ""))
        want_src = "game start" if start else "our placement record"

        if status and status not in RESTING:
            buckets["NOT_RESTING"].append((oid, key, status, rem))
            continue
        if exp is None:
            buckets["UNSAFE_NO_EXPIRY"].append((oid, key, status or "unknown", rem,
                                                sorted(k for k in (o or {}) if "exp" in k.lower())))
            continue
        if want and exp > want + timedelta(minutes=GRACE_MIN):
            buckets["UNSAFE_LATE_EXPIRY"].append((oid, key, status or "unknown", rem, exp, want,
                                                  want_src, field))
            continue
        buckets["CONFIRMED_SAFE"].append((oid, key, status or "unknown", rem, exp, field, want_src))

    say("")
    say("RESULT")
    say("-" * 100)
    for b, rows in buckets.items():
        say(f"  {len(rows):4d}  {b}")
    say("")

    for oid, key, status, rem, exp, field, wsrc in buckets["CONFIRMED_SAFE"]:
        say(f"  SAFE      {oid[:12]} {key:<54} {status:<8} rem {rem:g} contracts | venue "
            f"{field}={exp:%Y-%m-%d %H:%M}Z, at or before the cutoff ({wsrc})")
    for oid, key, status, rem, keys in buckets["UNSAFE_NO_EXPIRY"]:
        say(f"  UNSAFE    {oid[:12]} {key:<54} {status:<8} rem {rem:g} contracts | NO expiry in "
            f"Kalshi's own record (expiry-like fields present: {keys or 'none'})")
    for oid, key, status, rem, exp, want, wsrc, field in buckets["UNSAFE_LATE_EXPIRY"]:
        say(f"  UNSAFE    {oid[:12]} {key:<54} {status:<8} rem {rem:g} contracts | venue "
            f"{field}={exp:%Y-%m-%d %H:%M}Z is AFTER the cutoff {want:%Y-%m-%d %H:%M}Z ({wsrc})")
    for oid, key, status, rem in buckets["NOT_RESTING"]:
        say(f"  closed    {oid[:12]} {key:<54} {status:<8} rem {rem:g} - no live exposure")
    for oid, key, why in buckets["UNREADABLE"]:
        say(f"  UNKNOWN   {oid[:12]} {key:<54} readback failed: {why}")

    unsafe = buckets["UNSAFE_NO_EXPIRY"] + buckets["UNSAFE_LATE_EXPIRY"]
    at_risk = [r for r in unsafe if (r[3] or 0) > 0]
    say("")
    say("ESCALATION")
    say("-" * 100)
    if not unsafe and not buckets["UNREADABLE"]:
        say("  Every resting order on record carries a venue-side expiry at or before its cutoff.")
        say("  The 'until None' in the notification is therefore OUR record missing the field, not")
        say("  a missing expiry at Kalshi. The reporting gap is real; the exposure risk is not.")
    else:
        say(f"  {len(unsafe)} order(s) cannot be confirmed to expire before their cutoff, "
            f"{len(at_risk)} of them with contracts still resting.")
        say("  Treated as POTENTIALLY UNSAFE, per Peter's instruction. NOTHING IS CANCELLED HERE:")
        say("  cancelling a resting order is a live-betting change and needs Peter's explicit yes.")
        if buckets["UNREADABLE"]:
            say(f"  {len(buckets['UNREADABLE'])} order(s) could not be read at all. An unreadable "
                f"order is UNKNOWN exposure, never assumed safe.")
    say("")
    say("Counts and prices only. No dollar figures. Every venue call in this probe was a GET.")
    os.makedirs("audit", exist_ok=True)
    json.dump({"generated": cl.iso(now),
               "counts": {k: len(v) for k, v in buckets.items()}},
              open("audit/kalshi_expiry_probe.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
