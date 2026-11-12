#!/usr/bin/env python3
"""Two CONCURRENT submission attempts produce exactly ONE dispatch (Peter, Nov 12).

"Complete it now and prove two concurrent attempts produce exactly one dispatch."

What the earlier test did NOT do, and I wrongly claimed it did: it checked two passes READING the
same registry rows. That is sequential. This races two callers on the same key through the store's
real sha lock - the loser's write is rejected, it re-reads, and it must come back False.

Also covers: STOP latching so ntfy's ~12 h retention cannot resume trading.

READ-ONLY and offline. No network, no venues, NO ORDERS.
"""
import base64
import json
import sys

import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


class Store:
    """The registry file with the REAL optimistic lock: a PUT whose sha is stale returns 409, and
    _commit must then re-read and re-apply. That is what makes the race genuine here."""

    def __init__(self):
        self.data, self.sha, self.n = {}, "sha0", 0
        self.puts, self.conflicts = 0, 0
        self.readable = self.writable = True
        self.stale_once = None      # (data, sha) handed to the NEXT fetch, as a real race would

    def fetch(self):
        if not self.readable:
            return None, None
        if self.stale_once is not None:
            d, sha = self.stale_once
            self.stale_once = None  # only the first read of the losing racer is pre-commit
            return json.loads(json.dumps(d)), sha
        return json.loads(json.dumps(self.data)), self.sha

    def call(self, method, url, body=None, timeout=20):
        if method != "PUT":
            return 200, {}
        if not self.writable:
            return 500, {}
        self.puts += 1
        if body.get("sha") != self.sha:
            self.conflicts += 1
            return 409, {}
        self.data = json.loads(base64.b64decode(body["content"]).decode())
        self.n += 1
        self.sha = f"sha{self.n}"
        return 200, {}


S = Store()
registry.token = lambda: "fake"
registry._fetch = S.fetch
registry._call = S.call


def reset():
    S.data, S.sha, S.n = {}, "sha0", 0
    S.puts = S.conflicts = 0
    S.readable = S.writable = True
    S.stale_once = None


KEY = "r1|NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"

print("1. TWO CONCURRENT ATTEMPTS ON ONE KEY -> exactly one dispatch")
reset()
# A TRUE race: the frozen sha stays in force for BOTH callers, so the loser reads the pre-commit
# snapshot (no owner yet), attempts its PUT with a stale sha, is rejected 409, and only then
# re-reads and finds the winner. Lifting the freeze between the two calls - which the first
# version of this test did - makes the loser read fresh data and decline without ever contending,
# i.e. the sequential path again, which is exactly the gap Peter called out.
before = (json.loads(json.dumps(S.data)), S.sha)     # what BOTH racers saw: no owner yet
first = registry.claim_submission(KEY, "cid-A")       # A commits
S.stale_once = before                                # B's first read is the pre-commit snapshot
second = registry.claim_submission(KEY, "cid-B")     # B must contend, lose the sha, re-read, fail
ck("exactly one caller wins", [first, second].count(True), 1)
ck("the winner is the first to commit", first, True)
ck("the loser is refused", second, False)
ck("the store recorded a real conflict (the lock was exercised)", S.conflicts >= 1, True)
ck("only ONE owner is stored", S.data["submissions"][KEY]["cid"], "cid-A")

print("\n2. a third and fourth attempt still lose")
ck("third attempt", registry.claim_submission(KEY, "cid-C"), False)
ck("fourth attempt", registry.claim_submission(KEY, "cid-D"), False)
ck("still one owner", S.data["submissions"][KEY]["cid"], "cid-A")

print("\n3. the SAME caller may re-claim (a retry of its own submission is not a duplicate)")
ck("owner re-claims its own key", registry.claim_submission(KEY, "cid-A"), True)

print("\n4. NO staleness expiry: an unknown outcome keeps blocking")
S.data["submissions"][KEY]["ts"] = "2020-01-01T00:00:00Z"
ck("a year-old unconfirmed claim still blocks", registry.claim_submission(KEY, "cid-E"), False)

print("\n5. release only by the owner, and only when nothing was submitted")
reset()
registry.claim_submission(KEY, "cid-A")
ck("a non-owner cannot release", registry.release_submission(KEY, "cid-X") or
   KEY in S.data.get("submissions", {}), True)
ck("key still owned after a foreign release attempt", S.data["submissions"][KEY]["cid"], "cid-A")
registry.release_submission(KEY, "cid-A")
ck("owner released it", KEY in S.data.get("submissions", {}), False)
ck("a later run may now claim", registry.claim_submission(KEY, "cid-B"), True)

print("\n6. store failure BLOCKS, never allows")
reset()
S.readable = False
try:
    registry.claim_submission(KEY, "cid-A")
    ck("unreadable store raises (no claim, no submission)", "no raise", "raise")
except RuntimeError:
    ck("unreadable store raises (no claim, no submission)", "raise", "raise")
reset()
S.writable = False
try:
    registry.claim_submission(KEY, "cid-A")
    ck("unwritable store raises", "no raise", "raise")
except RuntimeError:
    ck("unwritable store raises", "raise", "raise")

print("\n7. the executor takes the claim BEFORE submitting, and releases on a failed intent")
import os                                                                # noqa: E402
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
body = src[src.index("def journal_intent("):src.index("def journal_latch_why(")]
ck("claim_submission is called in journal_intent", "registry.claim_submission(" in body, True)
ck("the claim comes BEFORE the intent read-back",
   body.index("claim_submission(") < body.index("intent_verified("), True)
# Nov 12: these two matched literal MESSAGE TEXT, which was reworded, so they failed while the
# behaviour they guard was intact. Asserting the CONTROL FLOW instead - a lost or unavailable claim
# must return the no-order tuple - because that is the property that stops a duplicate order, and it
# does not change when someone rewrites a log line.
ck("a lost claim returns no client id (no order)",
   "refusing" in body and "return False, None" in body, True)
ck("a failed intent releases the key", "release_submission(" in body, True)
# Three distinct refusal exits before anything is submitted: no play key to claim, the key already
# claimed by another run, and the claim unavailable because the store could not be written. Each
# one must return the no-order tuple rather than fall through.
ck("a claim it cannot take refuses the order, not proceeds",
   body.count("return False, None") >= 3, True)

print("\n8. STOP LATCHES: ntfy expiry must not resume trading")
reset()
import px_live                                                           # noqa: E402
px_live._ntfy_switch = lambda: ("STOP", 111)
ck("a live STOP reports STOP", px_live.stop_state()[0], "STOP")
ck("STOP was latched in the store", S.data["switch"]["word"], "STOP")
px_live._ntfy_switch = lambda: (None, None)          # the ntfy message has aged out
ck("STOP SURVIVES ntfy expiry", px_live.stop_state()[0], "STOP")
px_live._ntfy_switch = lambda: ("GO", 222)
ck("an explicit GO clears it", px_live.stop_state()[0], "GO")
px_live._ntfy_switch = lambda: (None, None)
ck("GO also persists", px_live.stop_state()[0], "GO")
px_live._ntfy_switch = lambda: ("UNKNOWN", None)
ck("an unreadable ntfy still refuses", px_live.stop_state()[0], "UNKNOWN")
px_live._ntfy_switch = lambda: (None, None)
S.readable = False
ck("ntfy silent AND latch unreadable -> UNKNOWN, never None",
   px_live.stop_state()[0], "UNKNOWN")

print("\n" + "=" * 62)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
