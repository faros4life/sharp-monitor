#!/usr/bin/env python3
"""Safety tests for registry.touch_tokens_complete() (Peter, Nov 12).

The claim this function makes is "the store still holds everything Gmail holds for the window".
Getting that wrong is fail-OPEN on money: a falsely complete store answers "not handled" for a bet
that WAS handled, and the play is eligible to be placed a second time. So every test below asks the
same question - can this function ever leave a claim standing that is not earned?

Interruption points covered, per Peter's list: before the token write, during it, after it, before
the ledger email, after the ledger email.
"""
import json
from datetime import datetime, timedelta, timezone

import registry as R

UTC = timezone.utc
NOW = datetime(2026, 11, 12, 18, 0, 0, tzinfo=UTC)
TODAY = NOW.strftime("%Y-%m-%d")
OLD = (NOW - timedelta(days=R.KEEP_DAYS + 1)).strftime("%Y-%m-%d")

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class Store:
    """Stands in for the private repo file. Records every write so 'did it change anything' is testable."""

    def __init__(self, data, writable=True, readable=True):
        self.data = data
        self.writable = writable
        self.readable = readable
        self.writes = 0

    def install(self):
        R.load = lambda: (json.loads(json.dumps(self.data)) if self.readable else None)

        def _commit(merge, tries=4):
            if not self.readable:
                return False
            d = json.loads(json.dumps(self.data))
            if merge(d) is False:
                return True                      # nothing to change still counts as success
            if not self.writable:
                return False
            self.data = d
            self.writes += 1
            return True
        R._commit = _commit
        R.enabled = lambda: True
        return self


_orig = (R.load, R._commit, R.enabled)

print("A valid, fresh-enough claim is re-stamped")
s = Store({"meta": {"tok_complete_through": TODAY,
                    "tok_complete_at": (NOW - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")}}).install()
ok = R.touch_tokens_complete(now=NOW)
check("returns True", ok)
check("stamp moved forward", s.data["meta"]["tok_complete_at"] == NOW.strftime("%Y-%m-%dT%H:%M:%SZ"))
check("window claim untouched", s.data["meta"]["tok_complete_through"] == TODAY)
check("tokens_complete() now true", R.tokens_complete(now=NOW))

print("\nAn INVALIDATED claim is never recreated (this is the fail-open case)")
s = Store({"meta": {"tok_complete_through": "", "tok_complete_at": "whenever"}}).install()
check("returns False", R.touch_tokens_complete(now=NOW) is False)
check("nothing was written", s.writes == 0)
check("still incomplete", not R.tokens_complete(now=NOW))

print("\nA claim that has aged out of the window is not revived")
s = Store({"meta": {"tok_complete_through": OLD, "tok_complete_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}}).install()
check("returns False", R.touch_tokens_complete(now=NOW) is False)
check("nothing was written", s.writes == 0)

print("\nA store with no meta at all is not promoted to complete")
s = Store({}).install()
check("returns False", R.touch_tokens_complete(now=NOW) is False)
check("nothing was written", s.writes == 0)

print("\nAn UNREADABLE store asserts nothing")
s = Store({"meta": {"tok_complete_through": TODAY}}, readable=False).install()
check("returns False", R.touch_tokens_complete(now=NOW) is False)
check("nothing was written", s.writes == 0)

print("\nA store that reads but cannot be WRITTEN reports failure (interrupted mid-write)")
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}, writable=False).install()
check("returns False", R.touch_tokens_complete(now=NOW) is False)
check("stamp unchanged", s.data["meta"]["tok_complete_at"] == "old")

print("\nInvalidated UNDER the lock, between the pre-check and the merge: the merge re-checks")
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}).install()
_real = R._commit


def racing(merge, tries=4):
    s.data["meta"]["tok_complete_through"] = ""      # another run invalidates right now
    return _real(merge, tries)


R._commit = racing
R.touch_tokens_complete(now=NOW)
check("stamp NOT moved after the race", s.data["meta"]["tok_complete_at"] == "old")
check("claim stays invalid", not R.tokens_complete(now=NOW))

print("\nFreshness itself is unchanged: a stamp older than FRESH_MIN is still stale")
s = Store({"meta": {"tok_complete_through": TODAY,
                    "tok_complete_at": (NOW - timedelta(minutes=R.FRESH_MIN + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")}}).install()
check(f"FRESH_MIN is still {R.FRESH_MIN}", R.FRESH_MIN == 12)
check("stale claim is not trusted", not R.tokens_complete(now=NOW))

print("\nRun-order cases Peter listed")
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}).install()
check("killed BEFORE the token write: claim ages out on its own, nothing asserted", s.writes == 0)
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}, writable=False).install()
check("killed DURING the write: put_tokens False -> executor invalidates; touch also False",
      R.touch_tokens_complete(now=NOW) is False)
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}).install()
check("killed AFTER the write but before the touch: claim simply stale, next run reads Gmail",
      not R.tokens_complete(now=NOW))
s = Store({"meta": {"tok_complete_through": TODAY, "tok_complete_at": "old"}}).install()
R.touch_tokens_complete(now=NOW)
check("killed AFTER the touch, before the ledger email: tokens were a CONFIRMED put, so the store "
      "that answers dedupe has them", R.tokens_complete(now=NOW))

R.load, R._commit, R.enabled = _orig
print("\n" + ("ALL PASS" if not fails else f"FAILURES: {fails}"))
raise SystemExit(1 if fails else 0)
