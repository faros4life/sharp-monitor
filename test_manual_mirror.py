#!/usr/bin/env python3
"""Phase 1 safety tests: the manual-notes mirror and its own completeness claim (Peter, Nov 12).

Manual notes are Peter's Hard Rock bets, which the bot has no read path for. They are the only thing
standing between a manual position and a duplicate or opposite bot bet, so getting this wrong is
fail-OPEN on money in two different directions:

  - a note MISSING from the store  -> "no conflict" -> the bot bets a side Peter already holds
  - a note LINGERING in the store  -> a phantom conflict -> a real, qualifying bet is blocked

The second is why the mirror is a whole-window SNAPSHOT and not an upsert: a note carries no id and
Peter can correct or delete one. Both directions are tested below.

Gmail remains authoritative in Phase 1. Nothing here gates a bet yet; these tests defend the claim
that would allow the switch later.
"""
import json
from datetime import datetime, timedelta, timezone

import registry as R

UTC = timezone.utc
NOW = datetime(2026, 11, 12, 18, 0, 0, tzinfo=UTC)
TODAY = NOW.strftime("%Y-%m-%d")
FRESH = (NOW - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
STALE = (NOW - timedelta(minutes=R.FRESH_MIN + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
AGED = (NOW - timedelta(days=R.MANUAL_DAYS + 1)).strftime("%Y-%m-%d")

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class Store:
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
                return True
            if not self.writable:
                return False
            self.data = d
            self.writes += 1
            return True
        R._commit = _commit
        R.enabled = lambda: True
        return self


_orig = (R.load, R._commit, R.enabled)

N1 = {"sport": "NBA", "game": "Away @ Home", "bet": "Under 225.5 (-110)", "book": "Hard Rock"}
N2 = {"sport": "NBA", "game": "A @ B", "bet": "Over 210.5 (-105)", "book": "Hard Rock"}

print("The claim follows the same two-part rule as orders and tokens")
s = Store({"manual": [N1], "meta": {"man_complete_through": TODAY, "man_complete_at": FRESH}}).install()
check("a fresh, in-window claim is trusted", R.manual_complete(now=NOW))
s.data["meta"]["man_complete_at"] = STALE
check("a claim older than FRESH_MIN is not trusted", not R.manual_complete(now=NOW))
s.data["meta"] = {"man_complete_through": AGED, "man_complete_at": FRESH}
check("a window claim aged past MANUAL_DAYS is not trusted", not R.manual_complete(now=NOW))
s.data["meta"] = {"man_complete_through": TODAY}
check("a window claim with no stamp is not trusted", not R.manual_complete(now=NOW))
s.data["meta"] = {"man_complete_through": TODAY, "man_complete_at": "garbage"}
check("an unparseable stamp is not trusted", not R.manual_complete(now=NOW))
s.data["meta"] = {"man_complete_through": TODAY,
                  "man_complete_at": (NOW + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")}
check("a stamp from the future is not trusted", not R.manual_complete(now=NOW))
s.data["meta"] = {}
check("no claim at all is not trusted", not R.manual_complete(now=NOW))

print("\nIt is tested against MANUAL_DAYS, not KEEP_DAYS")
# The claims compare DATE STRINGS, so the discriminating value has to be a whole day apart: one day
# past the manual window is still inside the 4-day order window. The same stored value must be
# trusted by one claim and refused by the other, which is the whole point of a separate domain.
check("the two windows really differ, so the distinction is live", R.MANUAL_DAYS != R.KEEP_DAYS)
between = (NOW - timedelta(days=R.MANUAL_DAYS + 1)).strftime("%Y-%m-%d")
s.data["meta"] = {"man_complete_through": between, "man_complete_at": FRESH,
                  "complete_through": between, "complete_at": FRESH}
check("a claim inside KEEP_DAYS but outside MANUAL_DAYS is NOT trusted by manual_complete",
      not R.manual_complete(now=NOW))
check("...while the SAME value is still inside the orders window", R.is_complete(between, now=NOW))

print("\nAn unreadable store asserts nothing, and never reads as 'no manual positions'")
s = Store({"manual": [N1], "meta": {"man_complete_through": TODAY, "man_complete_at": FRESH}},
          readable=False).install()
check("manual_notes() returns None, not []", R.manual_notes() is None)
check("the claim is not trusted", not R.manual_complete(now=NOW))

print("\nAn unwritable store reports False so the caller can invalidate")
s = Store({"manual": [], "meta": {}}, writable=False).install()
check("put_manual reports False", R.put_manual([N1]) is False)
check("nothing was written", s.writes == 0)

print("\nThe mirror is a SNAPSHOT: corrections and deletions propagate")
s = Store({"manual": [], "meta": {}}).install()
R.put_manual([N1, N2])
check("both notes stored, in order", R.manual_notes() == [N1, N2])
R.put_manual([N2])                      # Peter deleted the first note from Gmail
check("the deleted note is GONE, not lingering", R.manual_notes() == [N2])
R.put_manual([])
check("an empty window empties the snapshot", R.manual_notes() == [])
check("a non-dict note is refused entry", R.put_manual(["junk", N1]) and R.manual_notes() == [N1])

print("\nReplay order is preserved, because the accounting depends on it")
R.put_manual([N1, N2])
check("order round-trips exactly", [n["bet"] for n in R.manual_notes()] == [N1["bet"], N2["bet"]])

print("\ninvalidate_manual() leaves the claim untrusted and the notes intact")
s = Store({"manual": [N1], "meta": {"man_complete_through": TODAY, "man_complete_at": FRESH}}).install()
R.invalidate_manual()
check("claim no longer trusted", not R.manual_complete(now=NOW))
check("the notes themselves are NOT destroyed", R.manual_notes() == [N1])

print("\nset_manual_complete() makes exactly the claim it is entitled to")
# It stamps from the REAL clock, not the frozen NOW above, so trust is checked against real time.
s = Store({"manual": [N1], "meta": {}}).install()
R.set_manual_complete()
REAL = datetime.now(UTC)
check("through is today", s.data["meta"]["man_complete_through"] == REAL.strftime("%Y-%m-%d"))
check("and it is immediately trusted", R.manual_complete(now=REAL))
check("the orders claim was NOT touched", "complete_through" not in s.data["meta"])
check("the tokens claim was NOT touched", "tok_complete_through" not in s.data["meta"])

R.load, R._commit, R.enabled = _orig

print()
if fails:
    print(f"FAIL  test_manual_mirror.py  {len(fails)} failed: {fails}")
    raise SystemExit(1)
print("ALL PASS")
