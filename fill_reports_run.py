#!/usr/bin/env python3
"""Kalshi resting-fill reporting, moved OFF the executor's critical path (Peter, Nov 12).

WHY. Measured on executor run 43283085130: `kalshi resting-fill reports (Gmail)` was 518.8s of a
632-second pass - 82% of it - while gating nothing at all. It only reports fills that ALREADY
happened, and it dedupes on its own token emails, so a missed cycle simply reports next cycle.

Holding the executor open for it is what starved the registry freshness claim. The claim is written
by a COMPLETED executor run and FRESH_MIN is 12 minutes; a 26-minute run leaves it stale well past
that, signal_alerts then loses the private-store fast path for bot_orders, its held-read blows the
240s budget, and AGAINST YOUR BET reports unavailable every cycle. That chain is the whole reason
this file exists.

WHAT STAYS IN THE EXECUTOR. novig_reports() - it is 16.8s, and it carries the put_venue_ids()
venue reconciliation that Peter wants kept on the execution path. Only the Kalshi reporter moves.

NO DUPLICATE NOTIFICATIONS. Three layers, unchanged from how the executor ran it:
  - the workflow's concurrency group (cancel-in-progress: false) means two of these never run at once
  - the fill path skips any order whose token email is already in Gmail (sent_tokens)
  - the expiry path claims its token in the private store first (registry.claim_token)
Dedupe is via token emails in the shared mailbox, so this job and the executor reading the same
mailbox agree; only true concurrency could duplicate, and the concurrency group prevents it.

Counts only in this log. Nothing here places, cancels, sizes or routes an order.
"""
import os
import sys

import executor as ex

if (os.environ.get("EXEC_KALSHI_REPORTS") or "on").strip().lower() != "on":
    print("kalshi fill reports: skipped (EXEC_KALSHI_REPORTS=off)")
    sys.exit(0)

rc = 0
try:
    with ex.perf("kalshi resting-fill reports (Gmail)", rollup=True):
        ex.kalshi_rest_reports()
except Exception as e_:
    # Never fail the workflow on a reporting error: the next firing retries, and a red run here
    # would look like an execution problem when nothing that gates a bet has happened.
    print(f"kalshi resting-fill check failed: {str(e_)[:80]}")
    rc = 0

print(ex.perf_report())
for _l in ex.LOG:
    print(f"  {_l}")
sys.exit(rc)
