#!/usr/bin/env python3
"""POSITIONS UNREADABLE is held until 5 consecutive blind runs (Peter, Nov 11).

READ-ONLY and offline: no network, no venues, NO ORDERS. What must NOT change is the safety
behaviour - a blind run still places nothing on any venue, and a held live-eligible play still
pushes immediately. Only the cadence of the summary message changes.
"""
import ast
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
        self.writable = True

    def fetch(self):
        return json.loads(json.dumps(self.data)), self.sha

    def call(self, method, url, body=None, timeout=20):
        if method != "PUT":
            return 200, {}
        if not self.writable:
            return 500, {}
        if body.get("sha") != self.sha:
            return 409, {}
        import base64
        self.data = json.loads(base64.b64decode(body["content"]).decode())
        self.n += 1
        self.sha = f"sha{self.n}"
        return 200, {}


S = Store()
registry.token = lambda: "fake"
registry._fetch = S.fetch
registry._call = S.call

print("1. the counter")
ck("counts up", [registry.bump_streak("b") for _ in range(5)], [1, 2, 3, 4, 5])
registry.reset_streak("b")
ck("reset clears it", registry.bump_streak("b"), 1)
ck("streaks are independent", registry.bump_streak("other"), 1)
S.writable = False
try:
    registry.bump_streak("b")
    ck("an unwritable store raises (caller then notifies)", "no raise", "raise")
except RuntimeError:
    ck("an unwritable store raises (caller then notifies)", "raise", "raise")
S.writable = True

print("\n2. the push rule")
AT = 5


def pushes(streak, held):
    """Mirrors the condition in executor.py: p1 or streak is None or streak % AT == 0."""
    return bool(held) or streak is None or streak % AT == 0


S.data = {}
S.sha, S.n = "sha0", 0
registry.reset_streak("positions_blind")
fired = [n for n in (registry.bump_streak("positions_blind") for _ in range(12))
         if pushes(n, held=0)]
ck("12 quiet blind runs push only at 5 and 10", fired, [5, 10])
ck("runs 1-4 stay silent", [n for n in range(1, 5) if pushes(n, 0)], [])
ck("a HELD play pushes on run 1, streak notwithstanding", pushes(1, held=2), True)
ck("an uncountable streak pushes (fail-safe, never silent on a store failure)",
   pushes(None, held=0), True)

print("\n3. the safety behaviour is untouched")
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()
# strip comments/docstrings so the checks cannot match this file's own prose
tree = ast.parse(src)
code = ast.unparse(tree)

ck("blind still means no live orders on ANY venue",
   "exposure cannot be verified" in code.lower() or "NO new live orders this run on ANY venue" in code,
   True)
ck("the per-play HELD push is still there and separate", "held_tok" in code, True)
ck("the threshold is a named constant, not a literal in the branch",
   "BLIND_STREAK_AT" in code, True)
ck("the streak is reset when nothing is blind", 'reset_streak(' in code, True)

blk = code[code.index("blind = "):]
blk = blk[:blk.index("px_live.LIVE")]
ck("the summary push is inside the streak condition",
   blk.index("BLIND_STREAK_AT") < blk.index("POSITIONS UNREADABLE"), True)
ck("no sleep/retry loop crept back into the blind path", "sleep" in blk, False)

print("\n" + "=" * 58)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
