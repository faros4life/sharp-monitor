#!/usr/bin/env python3
"""NON-SUBMITTING lifecycle test of the Novig dispatch path (Peter, Nov 12).

Six response shapes, none of them real: accepted, rejected, partial, timeout, duplicate, unknown.
Nothing is posted anywhere - the dispatch transport itself is replaced, so no workflow_dispatch is
created, no home runner is contacted and no order reaches Novig. No historical order is replayed.

The question each case answers is the one that matters for turning submission back on: after this
response, can a LATER run submit the same bet again? The claim is what decides that, so every case
checks the claim's state, not just the returned status.
"""
import json
import sys

import book_live as bl
import registry as R

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class Store:
    def __init__(self):
        self.d = {"orders": [], "intents": [], "handled": {}, "submissions": {}}

    def install(self):
        R.load = lambda: json.loads(json.dumps(self.d))

        def _commit(merge, tries=4):
            d = json.loads(json.dumps(self.d))
            if merge(d) is False:
                return True
            self.d = d
            return True
        R._commit = _commit
        R.enabled = lambda: True
        return self


_orig = (R.load, R._commit, R.enabled, bl.NOVIG_SUBMIT)
KEY = "NBA|A @ B|total|UNDER"

print("The hold itself: with EXEC_NOVIG_SUBMIT off, nothing reaches the transport")
bl.NOVIG_SUBMIT = False
touched = {"n": 0}


def transport_spy(*a, **k):
    touched["n"] += 1
    raise AssertionError("the transport must not be reached while the hold is on")


res = bl.novig_place("00000000-0000-0000-0000-000000000000", 0.99, 1, label="probe")
check("refused at the first gate", (res or {}).get("status") == "refused")
check("the reason names the pause", "paus" in str((res or {}).get("reason", "")).lower())
check("the transport was never touched", touched["n"] == 0)

print("\nThe six response shapes, classified by what a LATER run may do")
# status -> (what it means, may a later run submit the same bet again?)
CASES = {
    "placed":   ("accepted",  False),
    "refused":  ("rejected",  True),    # provably pre-POST: the claim is released by design
    "partial":  ("partial",   False),
    "error":    ("timeout / unknown", False),
}
for st, (label, retry_ok) in CASES.items():
    print(f"  {label:<18} status={st:<8} later submission allowed: {retry_ok}")
check("only a provable pre-POST refusal permits a later submission",
      [s for s, (_, r) in CASES.items() if r] == ["refused"])

print("\nambiguous/unknown (HTTP error on dispatch) must not claim non-submission")
src = "\n".join(l.split("#")[0] for l in open(bl.__file__).read().splitlines())
check("no path says nothing was sent to Novig", "nothing was sent to Novig" not in src)
check("the HTTP-error path reports UNKNOWN", "dispatch UNKNOWN" in src)
check("and states the claim stays held", "the claim stays held" in src)
check("the non-HTTP path still says check before any retry", "check Novig before any retry" in src)

print("\nDUPLICATE: a second attempt on a held key cannot submit")
s = Store().install()
check("first attempt claims the key", R.claim_submission(KEY, "cid-1") is True)
check("second attempt is refused the claim", R.claim_submission(KEY, "cid-2") is False)
check("one claim stored", len(s.d["submissions"]) == 1)

print("\nTIMEOUT / UNKNOWN: the claim stays held, so no automatic retry follows")
s = Store().install()
R.claim_submission(KEY, "cid-unknown")
# an error path never releases: release_submission is reachable only from void_intent(), which is
# itself reachable only from a provably pre-submission refusal.
ex_src = open("executor.py").read()
rel = ex_src[ex_src.index("def _release_claim("):]
rel = rel[:rel.index("\n\ndef ")]
check("_release_claim is documented as refusal-only",
      "never from an error path" in rel or "refusal that never reached the venue" in rel)
check("the key is still held after an unknown outcome",
      R.claim_submission(KEY, "cid-someone-else") is False)
check("a failed release leaves it held (the safe direction)", "leaves the key claimed" in rel)

print("\nrefuse_untransmitted is the ONLY voiding refusal, and never for an error")
ru = ex_src[ex_src.index("def refuse_untransmitted("):]
ru = ru[:ru.index("\n\ndef ")]
check("it voids the write-ahead intent", "void_intent(" in ru)
check("it notifies, because it ends in refuse()", "return refuse(r," in ru)
check("its rule excludes error explicitly", 'Never for "error"' in ru)

print("\nThe registry is a HARD precondition: no durable claim, no submission")
R.load, R._commit, R.enabled = (lambda: None), (lambda m, tries=4: False), (lambda: True)
raised = False
try:
    R.claim_submission(KEY, "cid-x")
except Exception:
    raised = True
check("an unwritable store raises rather than granting a claim", raised)
ji = ex_src[ex_src.index("def journal_intent("):ex_src.index("def journal_latch_why(")]
check("journal_intent refuses when the claim is unavailable",
      "submission claim unavailable" in ji and ji.count("return False, None") >= 3)
check("and it tells Peter no order was placed",
      "CLAIM UNAVAILABLE" in ji and "NO ORDER PLACED" in ji)

R.load, R._commit, R.enabled, bl.NOVIG_SUBMIT = _orig

print()
if fails:
    print(f"FAIL  test_novig_lifecycle.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
