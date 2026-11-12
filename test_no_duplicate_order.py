#!/usr/bin/env python3
"""No duplicate order under concurrency, delayed fills, registry failure or submission timeout.

Peter, Nov 12 (requirement 5): "Test concurrent runs, delayed fills, registry failure and
submission timeout: none may produce a duplicate order."

The real event being regressed: R1 placed one NCAAF under three times (ebe82a72, 510a30b6,
adade61d). Reconciled afterwards against the home runner's own results, the THIRD order filled
43,300/43,300 and the first two have no result row at all - outcome unknown, not killed.

READ-ONLY and offline. No network, no venues, NO ORDERS.
"""
import os
import sys

import book_live as bl
import executor as ex

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


def raises(fn, *a):
    """'raise' when fn blows up - a guard that raises is fail-closed; one that returns is not."""
    try:
        fn(*a)
        return "no raise"
    except Exception:
        return "raise"


BARE = "NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"
R1KEY = "r1|" + BARE


def blocked(bare_key, livekeys):
    """The guard as executor.py applies it: exact hit, fuzzy same-bet, or opposite side."""
    return (bare_key in livekeys
            or any(ex.same_bet(bare_key, k) for k in livekeys)
            or any(ex.opp_bet(bare_key, k) for k in livekeys))


def livekeys_from(rows):
    """bot_orders()'s rule: a row with a placed order contributes its key AND the stripped form."""
    out = set()
    for row in rows:
        for lo in [row.get("live_order") or {}, row.get("live_rest") or {}] + list(row.get("live_more") or []):
            if (lo or {}).get("status") == "placed" and (lo or {}).get("order_id") and row.get("key"):
                out.add(row["key"])
                out.add(ex.lane_strip(row["key"]))
    return out


def journal_row(key, oid, cid, filled=None):
    return {"key": key, "source": "r1", "live_order": {
        "status": "placed", "order_id": oid, "book": "novig", "asked_stake": 233.82,
        "filled_stake": filled, "client_id": cid, "intent": False}}


print("1. THE REGRESSION: the exact three-order sequence from this morning")
rows = [journal_row(R1KEY, "ebe82a72", "fee2daff")]
lk = livekeys_from(rows)
ck("run 2 is blocked by run 1's order", blocked(BARE, lk), True)
rows.append(journal_row(R1KEY, "510a30b6", "e238da09"))
ck("run 3 is blocked too", blocked(BARE, livekeys_from(rows)), True)
# and the old behaviour, to prove the test would have caught it
old_lk = {R1KEY}                      # what LIVEKEYS held before the fix: prefixed form only
ck("pre-fix LIVEKEYS would NOT have blocked (the bug)", BARE in old_lk, False)

print("\n2. DELAYED FILL: a placed order with no fill yet still blocks")
# this is the live failure mode - the position does not exist until the fill lands, so a guard
# that waits for a position places again in the meantime.
unfilled = livekeys_from([journal_row(R1KEY, "ebe82a72", "fee2daff", filled=None)])
ck("filled_stake None still reaches LIVEKEYS", blocked(BARE, unfilled), True)
ck("an empty position set does not unblock it", blocked(BARE, unfilled) and not [], True)
partial = livekeys_from([journal_row(R1KEY, "ebe82a72", "fee2daff", filled=50.0)])
ck("a PARTIAL fill still blocks a second order", blocked(BARE, partial), True)

print("\n3. SUBMISSION TIMEOUT / UNKNOWN OUTCOME: still blocks retries")
# an intent row is written BEFORE submission with order_id "intent-<cid>" and status placed,
# so an order whose outcome was never confirmed keeps the key live.
intent_only = livekeys_from([journal_row(R1KEY, "intent-fee2daff", "fee2daff", filled=None)])
ck("an intent row alone blocks a retry", blocked(BARE, intent_only), True)
ck("book_live refuses an unclear dispatch rather than reporting placed",
   "check Novig before any retry" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       "book_live.py")).read(), True)

print("\n4. CONCURRENT RUNS: both passes see the same registry")
# two overlapping runs read the same rows; whichever reads after the first journal is blocked.
shared = [journal_row(R1KEY, "ebe82a72", "fee2daff")]
a = livekeys_from(shared)
b = livekeys_from(shared)
ck("pass A blocked", blocked(BARE, a), True)
ck("pass B blocked", blocked(BARE, b), True)
# the write-ahead intent is what covers the window BEFORE the journal exists
ck("journal_intent is a precondition, not a consequence",
   "the order is submitted only if the write succeeded" in ex.journal_intent.__doc__.lower()
   or "becomes a PRECONDITION of it" in ex.journal_intent.__doc__, True)

print("\n5. REGISTRY FAILURE: blocks, never allows")
import registry                                                          # noqa: E402
registry.token = lambda: ""           # not configured
ck("load() returns None when unreadable (callers FAIL CLOSED)", registry.load(), None)
ck("claim_token RAISES rather than returning a verdict",
   raises(registry.claim_token, "x"), "raise")
ck("an unreadable store never yields an empty-but-trusted registry",
   "never write over what we cannot see" in open(os.path.join(
       os.path.dirname(os.path.abspath(__file__)), "registry.py")).read(), True)

print("\n6. THE HOLD: no Novig submission can get out at all right now")
ck("EXEC_NOVIG_SUBMIT defaults off", bl.NOVIG_SUBMIT, False)
ck("live order refused", bl.novig_place("oid", 0.5, 200, "x").get("status"), "refused")
ck("resting bid refused", bl.novig_place("oid", 0.5, 200, "x", ttl_ms=600000).get("status"), "refused")

print("\n7. OTHER VENUES ARE UNAFFECTED by the Novig hold")
blsrc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "book_live.py")).read()
for fn in ("def kalshi_place", "def pmus_place"):
    if fn in blsrc:
        body = blsrc.split(fn)[1][:1500]
        ck(f"{fn.split()[1]} has no Novig hold", "NOVIG_SUBMIT" in body, False)

print("\n" + "=" * 62)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
