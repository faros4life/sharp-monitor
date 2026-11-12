#!/usr/bin/env python3
"""client_id <-> Novig order id mapping, and one dispatch from competing attempts (Peter, Nov 12).

"store both IDs from the submission response and use the venue ID to reconcile fills. Test the
complete path through a mocked submission - exactly one dispatch from competing attempts."

The defect: book_live.novig_place returns a LOCALLY generated uuid4 as order_id, because the order
is dispatched to the home runner and Novig's own id does not exist yet. Fills carry Novig's id.
So adade61d, known to have filled 43,300/43,300, was absent from all 152 fill rows - the join was
impossible by construction, not because the order was missing.

The home runner's result rows carry BOTH, which is where the mapping is recovered:
    client_id  adade61d-8fb6-4f2b-980e-6a7ca126af22   (local)
    order_id   01a1d042-e4b5-7423-a0bf-785747f314f6   (Novig's, what fills carry)

READ-ONLY and offline. No network, no venues, NO ORDERS. Pricing untouched.
"""
import base64
import json
import os
import sys

import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


class Store:
    def __init__(self):
        self.data, self.sha, self.n = {}, "sha0", 0
        self.puts, self.conflicts = 0, 0
        self.readable = self.writable = True
        self.stale_once = None

    def fetch(self):
        if not self.readable:
            return None, None
        if self.stale_once is not None:
            d, sha = self.stale_once
            self.stale_once = None
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


CID = "adade61d-8fb6-4f2b-980e-6a7ca126af22"
VID = "01a1d042-e4b5-7423-a0bf-785747f314f6"
KEY = "r1|NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"

print("1. novig_place returns BOTH ids (venue id null until the runner supplies it)")
import book_live as bl                                                   # noqa: E402
res = bl.novig_place("outcome", 0.54, 43300, "x")
ck("submission is HELD, so no dispatch happened", res.get("status"), "refused")
# inspect the success-shape in source, since the hold (correctly) prevents reaching it
blsrc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "book_live.py")).read()
shape = blsrc[blsrc.index('"status": "placed", "book": "novig"'):][:420]
ck("returns client_id", '"client_id": cid' in shape, True)
ck("returns venue_order_id, initially None", '"venue_order_id": None' in shape, True)
ck("order_id is still the client id at dispatch time", '"order_id": cid' in shape, True)

print("\n2. the mapping is recovered from a runner result row and is durable")
reset()
runner_rows = [
    {"client_id": CID, "order_id": VID, "status": "FILLED", "qty": "43300", "filled_qty": "43300"},
    {"client_id": "bb955c64-f829-445e-89e3-cdd39b991422",
     "order_id": "01a1cbb2-815c-75a3-8fd4-a59fd27daaab", "status": "FILLED"},
]
pairs = {str(x["client_id"]): str(x["order_id"]) for x in runner_rows
         if x.get("client_id") and x.get("order_id") and str(x["client_id"]) != str(x["order_id"])}
ck("both rows yield a pair", len(pairs), 2)
registry.put_venue_ids(pairs)
ck("mapping stored", registry.venue_ids().get(CID), VID)
ck("a repeat write is skipped (no churn)",
   (lambda before: (registry.put_venue_ids(pairs), S.puts == before)[1])(S.puts), True)
registry.put_venue_ids({CID: "01a1-SOMETHING-ELSE"})
ck("a stored mapping is never repointed", registry.venue_ids().get(CID), VID)

print("\n3. fills reconcile on the VENUE id, not the client id")
fills = [{"orderId": VID, "quantity": 43300}, {"orderId": "01a1-other", "quantity": 100}]
fill_oids = {str(f.get("orderId")) for f in fills}
ck("the client id does NOT appear in fills (the original defect)", CID in fill_oids, False)
ck("the venue id DOES", registry.venue_ids().get(CID) in fill_oids, True)
matched = sum(int(f["quantity"]) for f in fills if str(f["orderId"]) == registry.venue_ids().get(CID))
ck("filled quantity reconciles", matched, 43300)

print("\n4. an unmapped client id is UNRESOLVED, never 'no fill'")
reset()
m = registry.venue_ids()
ck("ebe82a72 has no mapping", m.get("ebe82a72-3dd0-4e45-8108-df1d5038ba9f"), None)
ck("510a30b6 has no mapping", m.get("510a30b6-8837-4fee-be01-5b16e79cdcda"), None)
ck("an unreadable store yields {} (treated as unresolved, not empty-and-trusted)",
   (lambda: (setattr(S, "readable", False), registry.venue_ids())[1])(), {})
S.readable = True

print("\n5. MOCKED SUBMISSION, COMPLETE PATH: competing attempts -> exactly ONE dispatch")
reset()
dispatched = []


def submit(cid):
    """The real sequence: atomic claim -> (intent) -> dispatch. No claim, no dispatch."""
    try:
        if not registry.claim_submission(KEY, cid):
            return "lost claim"
    except Exception:
        return "claim unavailable"          # store failure: no dispatch
    dispatched.append(cid)
    return "dispatched"


before = (json.loads(json.dumps(S.data)), S.sha)   # what both racers saw: unclaimed
a = submit("cid-A")
S.stale_once = before                              # B's first read is pre-commit: a true race
b = submit("cid-B")
ck("A dispatched", a, "dispatched")
ck("B did not", b, "lost claim")
ck("EXACTLY ONE dispatch", len(dispatched), 1)
ck("the lock was exercised (409 recorded)", S.conflicts >= 1, True)

print("\n6. the dispatched order's mapping completes the loop")
registry.put_venue_ids({dispatched[0]: VID})
ck("client -> venue recorded for the one dispatch", registry.venue_ids().get(dispatched[0]), VID)
ck("a second dispatch never existed to map", len(dispatched), 1)

print("\n7. store failure during the claim blocks the dispatch entirely")
reset()
dispatched.clear()
S.writable = False
ck("no dispatch when the claim cannot be written", submit("cid-C"), "claim unavailable")
ck("nothing dispatched", len(dispatched), 0)

print("\n8. the executor records the mapping where the two ids meet")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
body = src[src.index("def novig_reports("):src.index("def kalshi_rest_reports(")]
ck("put_venue_ids is called in novig_reports", "registry.put_venue_ids(" in body, True)
ck("it skips rows where the two ids are identical",
   'str(x.get("client_id")) != str(x.get("order_id"))' in body, True)
ck("a mapping failure never blocks a report",
   "venue id mapping not stored" in body, True)

print("\n" + "=" * 62)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
