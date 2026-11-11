#!/usr/bin/env python3
"""Novig fill-notification dedupe (Peter, Nov 11: "fix duplicate Novig fill notifications").

READ-ONLY and offline: no network, no Gmail, no Novig, NO ORDERS. The registry is replaced with
an in-memory store that enforces the same sha lock the real one does, so a concurrent pass is a
real race here and not a mock that always agrees.

Covers: duplicate suppression, two overlapping passes, crash recovery, PARTIAL -> FULL, registry
failure falling back to Gmail, fail-closed on a Gmail failure, and the exact defect that caused
the dupes - a mail failure must never re-send a fill that already went out.
"""
import hashlib
import json
import sys

import registry

OK = []
BAD = []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


# ---------------------------------------------------------------- fake store
class Store:
    """In-memory stand-in for the registry file, with the real optimistic lock."""

    def __init__(self):
        self.data = {}
        self.sha = "sha0"
        self.n = 0
        self.readable = True
        self.writable = True
        self.freeze = None      # sha to hand out, to stage a lost-update race

    def fetch(self):
        if not self.readable:
            return None, None
        return json.loads(json.dumps(self.data)), (self.freeze or self.sha)

    def call(self, method, url, body=None, timeout=20):
        if method != "PUT":
            return 200, {}
        if not self.writable:
            return 500, {}
        if body.get("sha") != self.sha:
            return 409, {}       # someone else wrote first
        import base64
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
    S.readable = S.writable = True
    S.freeze = None


# ---------------------------------------------------------------- 1. claim_token
print("1. claim_token")
reset()
ck("first claim wins", registry.claim_token("xnvrAAA"), True)
ck("second claim on a fresh pending loses", registry.claim_token("xnvrAAA"), False)
registry.mark_handled(["xnvrAAA"], "reported")
ck("claim after it was sent loses", registry.claim_token("xnvrAAA"), False)
ck("a different token still wins", registry.claim_token("xnvrBBB"), True)
ck("outcome recorded as pending", S.data["handled"]["xnvrBBB"]["outcome"], "pending")
ck("sent token recorded as reported", S.data["handled"]["xnvrAAA"]["outcome"], "reported")

print("\n2. crash recovery (interrupted send)")
reset()
registry.claim_token("xnvrC")
S.data["handled"]["xnvrC"]["ts"] = "2020-01-01T00:00:00Z"      # a pass that died long ago
ck("a stale pending is re-claimed", registry.claim_token("xnvrC"), True)
reset()
registry.claim_token("xnvrD")
S.data["handled"]["xnvrD"]["ts"] = "not-a-date"
ck("an unreadable stamp is treated as stale, never pinned shut",
   registry.claim_token("xnvrD"), True)
reset()
registry.claim_token("xnvrE")
ck("a stale pending that was already REPORTED stays shut",
   (registry.mark_handled(["xnvrE"], "reported"), registry.claim_token("xnvrE", stale_min=0))[1],
   False)

print("\n3. release_token")
reset()
registry.claim_token("xnvrF")
registry.release_token("xnvrF")
ck("released claim can be taken again", registry.claim_token("xnvrF"), True)
reset()
registry.claim_token("xnvrG")
registry.mark_handled(["xnvrG"], "reported")
registry.release_token("xnvrG")
ck("release never clears a completed send", S.data["handled"]["xnvrG"]["outcome"], "reported")

print("\n4. registry failure RAISES (so the caller falls back, never sends blind)")
reset()
S.readable = False
try:
    registry.claim_token("xnvrH")
    ck("unreadable store raises", "no raise", "raise")
except RuntimeError:
    ck("unreadable store raises", "raise", "raise")
reset()
S.writable = False
try:
    registry.claim_token("xnvrI")
    ck("unwritable store raises", "no raise", "raise")
except RuntimeError:
    ck("unwritable store raises", "raise", "raise")

print("\n5. two overlapping passes race for one token")
reset()
S.freeze = "sha0"          # both passes read the same sha
first = registry.claim_token("xnvrRACE")
S.freeze = None            # the loser now re-reads and re-applies under the real sha
second = registry.claim_token("xnvrRACE")
ck("exactly one pass wins the race", (first, second), (True, False))

# ---------------------------------------------------------------- ReportClaim
print("\n6. ReportClaim: registry path, Gmail fallback, fail-closed")
import executor as ex                                                   # noqa: E402

GMAIL = {"calls": 0, "ret": set(), "raise": False}


def fake_already_reported(M, toks, days=None):
    GMAIL["calls"] += 1
    if GMAIL["raise"]:
        raise RuntimeError("Gmail search failed")
    return set(GMAIL["ret"])


ex.already_reported = fake_already_reported
ex.LOG = []

reset()
c = ex.ReportClaim(None, ["t1", "t2"])
ck("registry path claims", (c.claim("t1"), c.claim("t1")), (True, False))
ck("registry path never touches Gmail", GMAIL["calls"], 0)

reset()
S.readable = False
GMAIL["ret"] = {"t2"}
c = ex.ReportClaim(None, ["t1", "t2"])
ck("store down -> Gmail says t2 already sent", c.claim("t2"), False)
ck("store down -> Gmail says t1 not sent", c.claim("t1"), True)
ck("Gmail searched ONCE for the whole pass, not per item", GMAIL["calls"], 1)

reset()
S.readable = False
GMAIL["raise"] = True
c = ex.ReportClaim(None, ["t9"])
try:
    c.claim("t9")
    ck("store down AND Gmail down -> fails closed (raises)", "no raise", "raise")
except RuntimeError:
    ck("store down AND Gmail down -> fails closed (raises)", "raise", "raise")
GMAIL["raise"] = False

print("\n7. PARTIAL -> FULL still reports; identical repeat does not")
reset()


def tok_for(cid, status, fq, cost):
    return "xnvr" + hashlib.sha1(f"{cid}|{status}|{fq}|{cost}".encode()).hexdigest()[:12]


part = tok_for("ord1", "PARTIAL", 13186, 71.86)
full = tok_for("ord1", "FILLED", 44000, 239.80)
same = tok_for("ord1", "PARTIAL", 13186, 71.86)
c = ex.ReportClaim(None, [part, full])
ck("partial reports", c.claim(part), True)
c.sent(part)
ck("the FULL that follows is a different token and reports", c.claim(full), True)
c.sent(full)
ck("a byte-identical repeat of the partial is suppressed", c.claim(same), False)
ck("partial and full are genuinely different tokens", part != full, True)

print("\n8. THE DEFECT: an email failure must not re-send a delivered fill")
reset()
c = ex.ReportClaim(None, ["tX"])
ck("claim taken", c.claim("tX"), True)
c.sent("tX")                      # Telegram delivered -> marked BEFORE the email
# the email now fails; the old code skipped the record write here and re-sent every pass
c2 = ex.ReportClaim(None, ["tX"])
ck("next pass does NOT re-send after a mail failure", c2.claim("tX"), False)

print("\n9. a send that never went out IS retried")
reset()
c = ex.ReportClaim(None, ["tY"])
c.claim("tY")
c.failed("tY")                    # tg() raised: nothing reached him
c2 = ex.ReportClaim(None, ["tY"])
ck("next pass retries a failed send immediately", c2.claim("tY"), True)

print("\n10. the dupe scenario end to end: 3 catch-up passes, 27 fills")
reset()
base_calls = GMAIL["calls"]        # whatever the fallback tests above spent; this step adds none
toks = [tok_for(f"ord{i}", "FILLED", 40000 + i, 200.0 + i) for i in range(27)]
sends = 0
for _ in range(3):                      # three passes inside one workflow run
    c = ex.ReportClaim(None, toks)
    for t in toks:
        if c.claim(t):
            c.sent(t)
            sends += 1
ck("27 fills across 3 passes send exactly 27 messages", sends, 27)
ck("Gmail never consulted while the registry answers", GMAIL["calls"] - base_calls, 0)

print("\n" + "=" * 60)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
if BAD:
    for b in BAD:
        print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
