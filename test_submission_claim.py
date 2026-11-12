#!/usr/bin/env python3
"""Two simultaneous runs on the same bet produce EXACTLY ONE submission (Peter/Muse, Nov 12).

OFFLINE. NO NETWORK. NO ORDERS. The registry's HTTP layer is replaced by an in-memory store that
enforces the real sha lock, so an overlapping run is a genuine race here and not a mock that
agrees. Everything above that - journal_intent(), void_intent(), _release_claim(),
registry.claim_submission(), registry._commit() and its 409 retry - is production code.

WHY THIS TEST EXISTS. The lane-key fix closed the SEQUENTIAL duplicate: two runs five minutes
apart, which is what placed the same NCAAF under three times (ebe82a72, 510a30b6, adade61d). It
does not close the concurrent one, because LIVEKEYS is a READ - two overlapping runs can both pass
it before either writes an intent, and runs do overlap here. registry.claim_submission() is a
WRITE under the sha lock, so exactly one caller can win a key; it existed and was NEVER CALLED,
and the one release_submission() call passed an undefined `_key` and raised NameError into a bare
except.

ACCEPTANCE BAR, verbatim: "two simultaneous runs on the same play key produce exactly one
submission, and the release path uses the row's real key."
"""
import copy
import json
import sys

import executor as ex
import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


class Store:
    """In-memory registry file with the REAL optimistic lock. A stale sha gets 409, exactly as
    GitHub answers, so _commit()'s retry path is the production one."""

    def __init__(self):
        self.data = {"orders": [], "meta": {}, "submissions": {}}
        self.sha = "sha0"
        self.puts = 0
        self.conflicts = 0
        self.frozen = None          # a pre-fetched (data, sha) handed to the next _fetch

    def fetch(self):
        if self.frozen is not None:
            d, s = self.frozen
            self.frozen = None
            return copy.deepcopy(d), s
        return copy.deepcopy(self.data), self.sha

    def call(self, method, url, body=None, timeout=20):
        if method != "PUT":
            return 200, {}
        if body.get("sha") != self.sha:
            self.conflicts += 1
            return 409, {}
        import base64
        self.data = json.loads(base64.b64decode(body["content"]).decode())
        self.sha = f"sha{int(self.sha[3:]) + 1}"
        self.puts += 1
        return 200, {}

    def claims(self):
        return dict(self.data.get("submissions") or {})


def wire(store):
    registry.enabled = lambda: True
    registry._fetch = store.fetch
    registry._call = store.call
    registry._prune = lambda d: None
    registry.load = lambda: copy.deepcopy(store.data)
    registry.put_rows = lambda rows: True
    registry.set_gmail_incomplete = lambda: True
    ex.intent_verified = lambda cid, row: (True, "private store")
    ex.send = lambda *a, **k: None
    ex.tg_push = lambda *a, **k: None
    ex.tg = lambda *a, **k: None
    ex.push = lambda *a, **k: None


def play(key, source="board"):
    return {"play": {"sport": "NBA", "game": "Charlotte vs Phoenix: Total Points",
                     "bet": "Under 214.5", "play_key": key, "source": source},
            "live": {"book": "novig", "line": 214.5, "risk": 200.0,
                     "px": {"buy": [], "thr": None}, "ids": {}}}


KEY_B = "board|NBA|Charlotte vs Phoenix: Total Points|total|UNDER"
KEY_R1 = "r1|NBA|Charlotte vs Phoenix: Total Points|total|UNDER"
BARE = ex.lane_strip(KEY_B)

print("0. the guard is actually REACHED by the order path")
print("=" * 88)
src = __import__("inspect").getsource(ex.journal_intent)
ck("journal_intent calls claim_submission", "registry.claim_submission(" in src, True)
ck("it claims the LANE-STRIPPED key", "lane_strip(row[\"key\"])" in src, True)
ck("a lost claim returns no client_id", "return False, None" in src, True)
ck("lane_strip collapses board| and r1| to one identity",
   ex.lane_strip(KEY_B) == ex.lane_strip(KEY_R1), True)

print()
print("1. SEQUENTIAL: the second attempt on the same bet is refused")
print("=" * 88)
st = Store(); wire(st)
ok1, cid1 = ex.journal_intent(play(KEY_B), "novig", 200.0)
ok2, cid2 = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("first attempt wins", ok1, True)
ck("second attempt refused", ok2, False)
ck("no client_id for the loser", cid2, None)
ck("exactly one claim stored", len(st.claims()), 1)
ck("the claim is on the bare key", list(st.claims()), [BARE])
ck("the claim records the winner's cid", st.claims()[BARE]["cid"], cid1)

print()
print("2. CROSS-LANE: a different lane cannot claim the same underlying bet")
print("=" * 88)
st = Store(); wire(st)
okb, cidb = ex.journal_intent(play(KEY_B, "board"), "novig", 200.0)
okr, cidr = ex.journal_intent(play(KEY_R1, "r1"), "novig", 200.0)
ck("board wins", okb, True)
ck("R1 refused on the same bet", okr, False)
ck("still exactly one claim", len(st.claims()), 1)

print()
print("3. CONCURRENT: two runs that both read before either writes")
print("=" * 88)
# The race, made real: run A and run B both fetch at sha0. A commits (sha -> sha1). B then PUTs
# with the stale sha0, gets 409, and _commit() re-fetches and re-applies its merge against A's
# write - where claim_submission() now sees another cid owns the key and declines.
st = Store(); wire(st)
pre = st.fetch()                       # what BOTH runs see before either writes
ok_a, cid_a = ex.journal_intent(play(KEY_B), "novig", 200.0)          # A writes first
st.frozen = pre                        # B's next fetch returns the PRE-A snapshot: stale sha
ok_b, cid_b = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("exactly one of the two simultaneous runs submits", sorted([ok_a, ok_b]), [False, True])
ck("the loser got no client_id", cid_b, None)
ck("the lock actually conflicted (a real race, not a mock)", st.conflicts >= 1, True)
ck("exactly one claim survives", len(st.claims()), 1)
ck("the surviving claim belongs to the winner", st.claims()[BARE]["cid"], cid_a)

print()
print("4. RELEASE uses the row's real key, and only for a never-transmitted refusal")
print("=" * 88)
st = Store(); wire(st)
ok1, cid1 = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("claimed", list(st.claims()), [BARE])
ex.void_intent(cid1, "novig", "EXEC_NOVIG_SUBMIT is not on", key=KEY_B)
ck("the claim is released after a pre-submission refusal", st.claims(), {})
ok3, cid3 = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("the bet can be attempted again once released", ok3, True)
ck("and it is claimed again", list(st.claims()), [BARE])
rsrc = __import__("inspect").getsource(ex._release_claim)
ck("_release_claim lane-strips the key it was given", "lane_strip(" in rsrc, True)
# Checked on CODE only and on a word boundary: "_ckey" contains "_key" as a substring, and the
# commit comment names the old bug by name, so a naive substring search reports a false positive.
import re as _re
_code = "\n".join(l for l in __import__("inspect").getsource(ex.journal_intent).splitlines()
                  if not l.strip().startswith("#"))
ck("no bare _key survives in journal_intent's CODE",
   _re.findall(r"(?<![A-Za-z0-9_])_key(?![A-Za-z0-9_])", _code), [])

print()
print("5. FAIL CLOSED: an unusable store submits nothing")
print("=" * 88)
st = Store(); wire(st)
registry._fetch = lambda: (None, None)      # store unreadable -> _commit returns False -> raises
ok, cid = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("unreadable store -> no submission", (ok, cid), (False, None))
st2 = Store(); wire(st2)
registry._call = lambda m, u, body=None, timeout=20: (500, {})   # every write fails
ok, cid = ex.journal_intent(play(KEY_B), "novig", 200.0)
ck("unwritable store -> no submission", (ok, cid), (False, None))
ck("and nothing was claimed", st2.claims(), {})
# A blank play_key is NOT keyless: derive_key() builds one from sport/game/bet, which is correct
# and is what the guards compare on. The real keyless case is a play derive_key() cannot key at
# all - that must be refused rather than claimed under "".
st3 = Store(); wire(st3)
_blank = {"play": {"source": "board"}, "live": {"book": "novig", "risk": 200.0,
                                                "px": {"buy": [], "thr": None}, "ids": {}}}
ck("derive_key really yields nothing for it", ex.derive_key(_blank["play"]), None)
ok, cid = ex.journal_intent(_blank, "novig", 200.0)
ck("a truly keyless play is refused, not claimed under ''", (ok, cid), (False, None))
ck("and nothing was claimed", st3.claims(), {})
st4 = Store(); wire(st4)
ok, cid = ex.journal_intent(play("", "board"), "novig", 200.0)
ck("a blank play_key is keyed by derive_key and claimed there", ok, True)
ck("claimed under the derived key", list(st4.claims()), [BARE])

print()
print("6. the claim has NO staleness expiry - an unknown outcome keeps blocking")
print("=" * 88)
csrc = __import__("inspect").getsource(registry.claim_submission)
ck("claim_submission states it has no expiry", "NO staleness expiry" in csrc, True)
ck("it raises rather than returning False when it cannot write",
   "raise RuntimeError" in csrc, True)

print()
print("=" * 88)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
