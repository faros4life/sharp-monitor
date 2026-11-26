#!/usr/bin/env python3
"""QUOTE-AGE STATISTICS (Peter, Nov 26). Reads the fields the alert feed records since Nov 26 (quote_pin_utc,
quote_book_utc, pin_quote_age_s, book_quote_age_s, quote_recv_utc) and prints, per venue and for Pinnacle:
count, median / p90 / max age in seconds, and how many were older than 60 s and 5 min at the alert.
Also the receipt-to-alert processing delay. Read-only; counts and seconds only."""
import collections
import json
from datetime import datetime


def tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def stats(v):
    v = sorted(v)
    if not v:
        return "none yet"
    n = len(v)
    return (f"n {n} | median {v[n // 2]}s | p90 {v[int(n * 0.9)]}s | max {v[-1]}s | "
            f">60s {sum(x > 60 for x in v)} | >5min {sum(x > 300 for x in v)}")


rows = json.load(open("alerts.json"))["alerts"]
rows = [r for r in rows if r.get("quote_recv_utc")]
pin, book, proc = [], collections.defaultdict(list), []
for r in rows:
    if isinstance(r.get("pin_quote_age_s"), (int, float)):
        pin.append(r["pin_quote_age_s"])
    if isinstance(r.get("book_quote_age_s"), (int, float)):
        book[r.get("book_key")].append(r["book_quote_age_s"])
    a, rc = tp(r.get("alert_utc")), tp(r.get("quote_recv_utc"))
    if a and rc:
        proc.append(round((a - rc).total_seconds()))
print(f"alerts with quote timing: {len(rows)}")
print(f"  Pinnacle          {stats(pin)}")
for b, v in sorted(book.items()):
    print(f"  {str(b):<17} {stats(v)}")
print(f"  receipt -> alert  {stats(proc)}")
