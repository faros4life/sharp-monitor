#!/usr/bin/env python3
"""ACCEPTANCE BAR: two simultaneous attempts on the same play key produce exactly ONE submission.

Peter, Nov 12. This is the defect that placed the same NCAAF under three times. The sequential case
(two runs five minutes apart) was closed by the lane-key fix. This file is about the case that was
still open: two OVERLAPPING attempts, which LIVEKEYS cannot stop because it is a read - both runs
pass it before either writes anything.

registry.claim_submission() is a WRITE under the store's sha lock, so it does not care whether the
two attempts are two executor runs, a zombie run past its timeout, or two different workflows. That
is why it closes the cross-workflow case too, independently of any concurrency group: the group
stops overlap within one workflow, the claim stops it everywhere.

The simulation below is the real race, not a stand-in for it: both callers read the SAME version of
the store, then both write. The second write is rejected on the stale version exactly as the GitHub
contents API rejects it, the caller re-reads, and its merge then sees the first caller's claim.

No order is placed. Nothing is submitted. No historical order is replayed.
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import registry as R

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class RacingStore:
    """A store with real optimistic locking: a write against a stale version is rejected.

    `hold_at_version` makes one caller read, then pause while another caller commits - the exact
    interleaving two overlapping runs produce.
    """

    def __init__(self, data=None):
        self.data = data or {"submissions": {}}
        self.version = 0
        self.rejected = 0
        self.commits = 0

    def install(self):
        store = self

        def load():
            return json.loads(json.dumps(store.data))

        def _commit(merge, tries=4):
            for _ in range(tries):
                seen_version = store.version          # read
                d = json.loads(json.dumps(store.data))
                if merge(d) is False:
                    return True                       # nothing to write still counts as success
                if seen_version != store.version:     # someone committed while we were deciding
                    store.rejected += 1
                    continue                          # re-read and re-run merge, as the real one does
                store.data = d
                store.version += 1
                store.commits += 1
                return True
            return False

        R.load, R._commit, R.enabled = load, _commit, lambda: True
        return self


_orig = (R.load, R._commit, R.enabled)
KEY = "NCAAF|A @ B|total|UNDER"

print("Two simultaneous attempts on one play key")
s = RacingStore().install()
a = R.claim_submission(KEY, "cid-run-A")
b = R.claim_submission(KEY, "cid-run-B")
check("the first attempt wins the key", a is True)
check("the second attempt LOSES it (no second submission)", b is False)
check("exactly one claim is stored", list((s.data.get("submissions") or {}).keys()) == [KEY])
check("and it belongs to the first caller", s.data["submissions"][KEY]["cid"] == "cid-run-A")

print("\nThe SAME caller may re-claim its own key (a retry of its own attempt is not a duplicate)")
check("same cid re-claims", R.claim_submission(KEY, "cid-run-A") is True)
check("still one key", len(s.data["submissions"]) == 1)

print("\nInterleaved: both read the same version, then both write (the real race)")
s = RacingStore().install()
captured = {}


def racing_merge_probe(key, cid, other):
    """Claim `key` for `cid`, but let `other` commit in the middle of our decision."""
    first = {"done": False}
    real_commit = R._commit

    def commit_with_interleave(merge, tries=4):
        def wrapped(d):
            if not first["done"]:
                first["done"] = True
                captured["other"] = R.claim_submission(key, other)   # the other run commits HERE
            return merge(d)
        return real_commit(wrapped, tries)

    R._commit = commit_with_interleave
    try:
        return R.claim_submission(key, cid)
    finally:
        R._commit = real_commit


mine = racing_merge_probe(KEY, "cid-run-C", "cid-run-D")
check("the interleaved write was rejected on a stale version at least once", s.rejected >= 1)
check("exactly one of the two interleaved callers won",
      (mine is True) != (captured.get("other") is True))
check("and only one claim exists for the key", len(s.data.get("submissions") or {}) == 1)

print("\nNo staleness expiry: an unconfirmed submission keeps blocking retries")
s = RacingStore({"submissions": {KEY: {"cid": "cid-old",
                                       "ts": (datetime.now(timezone.utc) - timedelta(days=3))
                                       .strftime("%Y-%m-%dT%H:%M:%SZ")}}}).install()
check("a three-day-old unconfirmed claim still blocks a new attempt",
      R.claim_submission(KEY, "cid-new") is False)
check("the old claim is untouched", s.data["submissions"][KEY]["cid"] == "cid-old")

print("\nAn unreadable or unwritable store RAISES - no durable claim, no submission")
R.load, R._commit, R.enabled = (lambda: None), (lambda m, tries=4: False), (lambda: True)
raised = False
try:
    R.claim_submission(KEY, "cid-x")
except Exception:
    raised = True
check("it raises rather than returning a claim it does not hold", raised)

print("\nrelease_submission is NOT reachable from an error path (an unknown outcome holds the key)")
src = open("executor.py").read()
rel = src[src.index("def _release_claim("):]
rel = rel[:rel.index("\n\ndef ")]
check("_release_claim documents the refusal-only rule",
      "never from an error path" in rel or "refusal that never reached the venue" in rel)
check("a failed release leaves the key claimed (the safe direction)",
      "leaves the key claimed" in rel)
nv = open("book_live.py").read()
# Comments stripped: the commit that fixed this QUOTES the old wording to explain what changed, and
# matching raw source made the fix look unapplied. The same trap tripped two other guards today.
nv_code = "\n".join(l.split("#")[0] for l in nv.splitlines())
check("the Novig HTTPError path no longer claims nothing was sent",
      "nothing was sent to Novig" not in nv_code)
check("it reports the outcome as UNKNOWN instead",
      "dispatch UNKNOWN" in nv and "the claim stays held" in nv)

R.load, R._commit, R.enabled = _orig

print()
if fails:
    print(f"FAIL  test_one_submission.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
