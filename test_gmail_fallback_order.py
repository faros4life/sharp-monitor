#!/usr/bin/env python3
"""The private store is tried before Gmail on every ledger read path (Peter, Nov 12). OFFLINE.

MEASURED on run 43277872370, the executor's own perf table:

    kalshi resting-fill reports (Gmail)   611.3s  (rollup)  x1
    read manual notes (Gmail)              66.9s   77.2%    x1
    novig fill reports (Gmail)             22.5s  (rollup)  x1
    registry read (private store)           0.46s

The 611s found ZERO resting orders - "kalshi resting check: 0 order(s), rows rescanned". The Nov 11
fix reused bot_orders()'s parsed rows, but when that cache is empty the fallback was still the
original full IMAP scan: a SEARCH plus one RFC822 fetch per email, ~200 serial round trips.

This asserts the ORDER of sources, which is the whole fix: cache, then store, then Gmail. It also
pins the guarantee the Nov 11 comment makes - "this can only be faster, never blinder" - by
proving Gmail is still reachable as the last resort rather than removed.

No network, no IMAP, no orders. The IMAP object is a tripwire that records every call, so an
accidental Gmail read shows up as a failure instead of as latency nobody notices.
"""
import inspect
import os
import sys

os.environ.setdefault("EXEC_LIVE", "off")

import executor as ex
import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


class TripwireIMAP:
    """Records every IMAP call. A ledger read that reaches here has bypassed the store."""

    def __init__(self):
        self.calls = []

    def uid(self, *a):
        self.calls.append(a[0] if a else "?")
        return ("NO", [None])

    def __getattr__(self, n):
        def f(*a, **k):
            self.calls.append(n)
            return ("NO", [None])
        return f


STORE = []
registry.enabled = lambda: True
registry.rows = lambda: list(STORE)


def run_kalshi(ledger_cache, store):
    """Call the real kalshi_rest_reports with a tripwire IMAP and report which source it used."""
    ex.LEDGER_ROWS[:] = list(ledger_cache)
    STORE[:] = list(store)
    tw = TripwireIMAP()
    ex.imap_open = lambda: tw
    ex.imap_close = lambda M: None
    ex.already_reported = lambda M, toks, days=None: set()
    ex.tg = lambda *a, **k: None
    ex.push = lambda *a, **k: None
    try:
        ex.kalshi_rest_reports()
    except Exception as e:
        print(f"    (kalshi_rest_reports raised {type(e).__name__}: {str(e)[:60]})")
    return tw.calls


def row(oid="k1", book="kalshi", when="2026-11-12T12:00:00Z"):
    return {"key": f"NCAAB|X @ Y|side|X", "decided_utc": when,
            "live_rest": {"status": "placed", "order_id": oid, "book": book, "asked_stake": 100.0}}


print("1. SOURCE ORDER: cache, then store, then Gmail")
print("=" * 86)
src = inspect.getsource(ex.kalshi_rest_reports)
i_cache = src.find("list(LEDGER_ROWS)")
i_store = src.find("registry.rows()")
# Nov 12: Muse made the IMAP connection lazy, so the call is M_().uid(...) now.
# Match the method, not the receiver, or this silently stops testing anything.
i_imap = max(src.find('uid("SEARCH"'), src.find("uid('SEARCH'"))
ck("the cache is consulted first", 0 <= i_cache < i_store, True)
ck("the store is consulted before Gmail", 0 <= i_store < i_imap, True)
ck("Gmail is still reachable as the last resort", i_imap > 0, True)

print()
print("2. BEHAVIOUR: an empty cache uses the store and never touches Gmail for the ledger")
print("=" * 86)
calls = run_kalshi([], [row()])
ck("no IMAP SEARCH for the ledger", [c for c in calls if c == "SEARCH"], [])
ck("no RFC822 fetch for the ledger", [c for c in calls if c == "FETCH"], [])

print()
print("3. BEHAVIOUR: cache present -> store not needed either")
print("=" * 86)
_hits = []
registry.rows = lambda: (_hits.append(1), list(STORE))[1]
calls = run_kalshi([row()], [row()])
ck("the store was not read when the cache had rows", _hits, [])
ck("and still no Gmail ledger scan", [c for c in calls if c in ("SEARCH", "FETCH")], [])
registry.rows = lambda: list(STORE)

print()
print("4. BEHAVIOUR: both empty -> Gmail IS used, so the path is never blinder than before")
print("=" * 86)
calls = run_kalshi([], [])
ck("Gmail searched when neither cache nor store has rows",
   "SEARCH" in calls, True)

print()
print("5. a store failure must not break the report")
print("=" * 86)
def boom():
    raise RuntimeError("store unreachable")
registry.rows = boom
calls = run_kalshi([], [])
ck("falls through to Gmail when the store raises", "SEARCH" in calls, True)
registry.rows = lambda: list(STORE)

print()
print("=" * 86)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
