#!/usr/bin/env python3
"""KALSHI OPEN-ORDER WATCH - READ-ONLY (Peter, Nov 23 2026).

Lists EVERY resting order on the Kalshi account straight from the venue (GET /portfolio/orders?status=resting,
every page) - not just the ids our registry recorded - and alerts Telegram AND ntfy when one is unsafe:

  NEAR/PAST START   a bot order still resting within 30 minutes of its game's start, or after it
  EXPIRY IGNORED    a resting order whose own venue expiry has already passed
  LATE EXPIRY       a bot order whose venue expiry is later than start - 30 min
  NO EXPIRY         a resting order with no venue expiry at all (bot orders always send one)
  READ INCOMPLETE   any failed call, bad response or unfinished paging - unknown is never "nothing open"

Every venue call is a GET. Nothing is cancelled, placed or changed; an unsafe order is escalated to Peter.
Public log: counts only. Order details go to Telegram/ntfy only.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import book_live

CUTOFF_MIN = 30
GRACE_MIN = 2
MAX_PAGES = 20


def tp(x):
    if x in (None, ""):
        return None
    try:
        n = float(x)
        if n > 1_000_000_000:
            return datetime.fromtimestamp(n, timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except ValueError:
        return None


def list_resting(call=None):
    """(orders, None) on a COMPLETE read, or (None, reason). Pages until the cursor is empty."""
    call = call or book_live._k_call
    out, cursor = [], None
    for _ in range(MAX_PAGES):
        params = {"status": "resting", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        try:
            code, resp = call("GET", "/portfolio/orders", params)
        except Exception as ex:
            return None, f"Kalshi order list call failed ({type(ex).__name__})"
        if code != 200 or not isinstance(resp, dict) or not isinstance(resp.get("orders"), list):
            return None, f"Kalshi order list unreadable (HTTP {code})"
        out += resp["orders"]
        cursor = resp.get("cursor") or None
        if not cursor:
            return out, None
    return None, f"Kalshi order list did not finish within {MAX_PAGES} pages"


def our_rests(reg):
    """{venue order id: game start} for every Kalshi bid the bot recorded."""
    m = {}
    for row in (reg or {}).get("orders") or []:
        for lo in [row.get("live_rest"), row.get("live_order")] + list(row.get("live_more") or []):
            if isinstance(lo, dict) and lo.get("book") == "kalshi" and lo.get("order_id"):
                m[str(lo["order_id"])] = tp(row.get("start_utc"))
    return m


def classify(orders, ours, now):
    """[(reason, order, start)] for every unsafe resting order. Pure."""
    bad = []
    for o in orders:
        if str(o.get("status") or "resting").lower() not in ("resting", "open", "active"):
            continue
        oid = str(o.get("order_id") or "")
        exp, _f = book_live.kalshi_order_expiry(o)
        start = ours.get(oid)
        if exp is None:
            bad.append(("NO EXPIRY", o, start))
        elif now > exp + timedelta(minutes=GRACE_MIN):
            bad.append(("EXPIRY IGNORED", o, start))
        elif start is not None and now >= start - timedelta(minutes=CUTOFF_MIN):
            bad.append(("NEAR/PAST START", o, start))
        elif start is not None and exp > start - timedelta(minutes=CUTOFF_MIN) + timedelta(minutes=GRACE_MIN):
            bad.append(("LATE EXPIRY", o, start))
    return bad


def main():
    import executor as ex          # its tg_push sends the SAME text to Telegram and ntfy, and counts delivery
    import registry as rg
    now = datetime.now(timezone.utc)
    print("KALSHI OPEN-ORDER WATCH - read-only, GET only, nothing cancelled", flush=True)
    problems = []
    if not (os.environ.get("KALSHI_KEY_ID") and os.environ.get("KALSHI_PRIVATE_KEY")):
        problems.append("Kalshi credentials missing - open orders could not be read")
        orders = None
    else:
        orders, why = list_resting()
        if orders is None:
            problems.append(why)
    reg = rg.load()
    if reg is None:
        problems.append("private registry unreadable - bot orders cannot be told from others, start times unknown")
    ours = our_rests(reg)
    bad = classify(orders or [], ours, now) if orders is not None else []
    n_ours = sum(1 for o in (orders or []) if str(o.get("order_id")) in ours)
    print(f"resting on Kalshi: {'UNKNOWN' if orders is None else len(orders)} "
          f"(bot-recorded {n_ours}, other {0 if orders is None else len(orders) - n_ours}); "
          f"unsafe {len(bad)}; read problems {len(problems)}", flush=True)
    for reason in sorted({b[0] for b in bad}):
        print(f"  {reason}: {sum(1 for b in bad if b[0] == reason)}", flush=True)
    # A non-bot order with no expiry is most likely one of Peter's own; say so once an hour, not every run.
    hourly = now.minute < 10
    send = [b for b in bad if not (b[0] == "NO EXPIRY" and str(b[1].get("order_id")) not in ours and not hourly)]
    if problems or send:
        lines = [f"- {p}" for p in problems]
        for reason, o, start in send:
            exp, _f = book_live.kalshi_order_expiry(o)
            rem = o.get("remaining_count_fp", o.get("remaining_count"))
            lines.append(f"- {reason}: {o.get('ticker')} {o.get('side') or ''} rem {rem} | "
                         f"{'bot' if str(o.get('order_id')) in ours else 'NOT a recorded bot order'} | "
                         f"expiry {exp:%H:%M}Z" if exp else f"- {reason}: {o.get('ticker')} rem {rem} | no venue expiry")
            if start:
                lines[-1] += f" | game {start:%H:%M}Z"
        ex.tg_push("KALSHI OPEN ORDER - check, cancel in the app if needed",
                   "Kalshi open-order watch (read-only - nothing was cancelled):\n" + "\n".join(lines[:15]))
    print("notifications (counts only): " + ("; ".join(f"{c} {s} {n}" for (c, s), n in sorted(ex.NOTIFY.items()))
                                             if ex.NOTIFY else "none sent this run"), flush=True)
    for line in ex.LOG:
        if "NTFY" in line or "TELEGRAM" in line:
            print(f"  {line}", flush=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
