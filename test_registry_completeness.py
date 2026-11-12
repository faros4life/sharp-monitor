#!/usr/bin/env python3
"""A completeness refresh must never resurrect an EXPIRED claim (Peter, Nov 12). OFFLINE. NO NETWORK.

touch_complete() and touch_tokens_complete() exist to keep a VALID claim alive, because the only
code that can create one lives in the Gmail backfill - the very thing being skipped when runs are
slow. Both had two fail-OPEN defects:

  1 They checked only the WINDOW half (complete_through / tok_complete_through) and never the
    FRESHNESS half (complete_at / tok_complete_at), so a claim whose stamp expired hours ago was
    re-stamped to now. is_complete()'s own docstring names why that matters: when writes are
    failing, a newly placed order is missing from the store AND invalidate() fails too, so the
    window marker survives while the stamp goes stale. is_complete() then correctly answers "not
    complete" - and re-stamping undoes exactly that protection. The $2,000 per-lane daily risk and
    the global stop read through this claim, so a falsely complete store UNDERCOUNTS exposure.

  2 _commit() treats a merge returning False as "nothing to change" and returns True, so the
    concurrent-invalidation branch reported SUCCESS. An aborted refresh must not look like a
    completed one.

These tests drive the REAL _commit() with _fetch/_call stubbed, so the optimistic-lock path and its
"merge returned False" semantics are the production ones, not a reimplementation. The concurrency
cases make _fetch return a document that differs from what load() returned - a real race, not a
mock that always agrees.
"""
import sys
from datetime import datetime, timedelta, timezone

import registry as R

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


NOW = datetime(2026, 11, 12, 19, 0, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def day(dt):
    return dt.strftime("%Y-%m-%d")


def meta(through_days_ago=0, stamp_min_ago=1, tok=False):
    """A registry doc whose claim is `stamp_min_ago` minutes old."""
    k = ("tok_complete_through", "tok_complete_at") if tok else ("complete_through", "complete_at")
    return {"orders": [], "meta": {k[0]: day(NOW - timedelta(days=through_days_ago)),
                                   k[1]: iso(NOW - timedelta(minutes=stamp_min_ago))}}


WROTE = []


def wire(doc_for_load, doc_for_commit=None):
    """Stub the IO around the REAL _commit: load() sees one document, _fetch() may see another."""
    WROTE.clear()
    R.enabled = lambda: True
    R.load = lambda: doc_for_load
    state = {"d": doc_for_commit if doc_for_commit is not None else doc_for_load}
    R._fetch = lambda: (state["d"], "sha-1")

    def call(method, url, body=None, timeout=20):
        if method == "PUT":
            WROTE.append(body)
            return 200, {}
        return 200, {}
    R._call = call
    R._prune = lambda d: None
    return state


print("1. touch_complete: the WINDOW half (unchanged behaviour)")
print("=" * 88)
wire(meta(through_days_ago=0, stamp_min_ago=1))
ck("fresh claim inside the window refreshes", R.touch_complete(NOW), True)
ck("and it wrote exactly once", len(WROTE), 1)
wire({"orders": [], "meta": {"complete_through": "", "complete_at": iso(NOW)}})
ck("no claim at all is never created", R.touch_complete(NOW), False)
ck("and nothing was written", len(WROTE), 0)
wire(meta(through_days_ago=R.KEEP_DAYS + 2, stamp_min_ago=1))
ck("a claim older than the window is not refreshed", R.touch_complete(NOW), False)

print()
print("2. touch_complete: the FRESHNESS half - THE DEFECT")
print("=" * 88)
wire(meta(through_days_ago=0, stamp_min_ago=R.FRESH_MIN + 1))
ck("an EXPIRED stamp is NOT resurrected", R.touch_complete(NOW), False)
ck("and nothing was written", len(WROTE), 0)
wire(meta(through_days_ago=0, stamp_min_ago=180))
ck("a three-hour-old stamp is not resurrected", R.touch_complete(NOW), False)
wire({"orders": [], "meta": {"complete_through": day(NOW)}})
ck("a missing stamp is not treated as fresh", R.touch_complete(NOW), False)
wire({"orders": [], "meta": {"complete_through": day(NOW), "complete_at": "not-a-date"}})
ck("an unparseable stamp is not treated as fresh", R.touch_complete(NOW), False)
wire(meta(through_days_ago=0, stamp_min_ago=-30))
ck("a FUTURE stamp is rejected (clock skew cannot extend a claim)", R.touch_complete(NOW), False)
wire(meta(through_days_ago=0, stamp_min_ago=R.FRESH_MIN - 1))
ck("just inside FRESH_MIN still refreshes", R.touch_complete(NOW), True)

print()
print("3. touch_complete: CONCURRENT change between the pre-check and the write")
print("=" * 88)
good = meta(through_days_ago=0, stamp_min_ago=1)
st = wire(good, {"orders": [], "meta": {"complete_through": "", "complete_at": iso(NOW)}})
ck("invalidated under the lock -> False, not True", R.touch_complete(NOW), False)
ck("and no write happened", len(WROTE), 0)
st = wire(good, meta(through_days_ago=0, stamp_min_ago=R.FRESH_MIN + 5))
ck("expired under the lock -> False", R.touch_complete(NOW), False)
ck("and no write happened", len(WROTE), 0)

print()
print("4. touch_complete never widens the window it claims")
print("=" * 88)
wire(meta(through_days_ago=2, stamp_min_ago=1))
R.touch_complete(NOW)
_wrote = WROTE[0] if WROTE else None
ck("a write occurred", bool(_wrote), True)
if _wrote:
    import base64
    import json
    d = json.loads(base64.b64decode(_wrote["content"]).decode())
    ck("complete_through untouched", d["meta"]["complete_through"], day(NOW - timedelta(days=2)))
    ck("only complete_at advanced", d["meta"]["complete_at"], iso(NOW))

print()
print("5. touch_tokens_complete: the same rules, on its own keys")
print("=" * 88)
wire(meta(through_days_ago=0, stamp_min_ago=1, tok=True))
ck("fresh token claim refreshes", R.touch_tokens_complete(NOW), True)
wire(meta(through_days_ago=0, stamp_min_ago=R.FRESH_MIN + 1, tok=True))
ck("an EXPIRED token stamp is NOT resurrected", R.touch_tokens_complete(NOW), False)
ck("and nothing was written", len(WROTE), 0)
wire({"orders": [], "meta": {"tok_complete_through": day(NOW)}})
ck("a missing token stamp is not fresh", R.touch_tokens_complete(NOW), False)
wire(meta(through_days_ago=0, stamp_min_ago=-30, tok=True))
ck("a future token stamp is rejected", R.touch_tokens_complete(NOW), False)
goodt = meta(through_days_ago=0, stamp_min_ago=1, tok=True)
wire(goodt, {"orders": [], "meta": {"tok_complete_through": "", "tok_complete_at": iso(NOW)}})
ck("token claim invalidated under the lock -> False", R.touch_tokens_complete(NOW), False)
wire(goodt, meta(through_days_ago=0, stamp_min_ago=R.FRESH_MIN + 5, tok=True))
ck("token claim expired under the lock -> False", R.touch_tokens_complete(NOW), False)

print()
print("6. an unreadable store asserts nothing")
print("=" * 88)
wire(None)
ck("touch_complete on an unreadable store", R.touch_complete(NOW), False)
ck("touch_tokens_complete on an unreadable store", R.touch_tokens_complete(NOW), False)

print()
print("7. the refresh and the reader agree on what 'valid' means")
print("=" * 88)
for mins, label in ((1, "fresh"), (R.FRESH_MIN + 1, "expired")):
    d = meta(through_days_ago=0, stamp_min_ago=mins)
    wire(d)
    want = R.is_complete(day(NOW - timedelta(days=R.KEEP_DAYS)), NOW)
    got = R.touch_complete(NOW)
    ck(f"is_complete and touch_complete agree when {label}", got, want)
for mins, label in ((1, "fresh"), (R.FRESH_MIN + 1, "expired")):
    d = meta(through_days_ago=0, stamp_min_ago=mins, tok=True)
    wire(d)
    want = R.tokens_complete(NOW)
    got = R.touch_tokens_complete(NOW)
    ck(f"tokens_complete and touch_tokens_complete agree when {label}", got, want)

print()
print("=" * 88)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
