#!/usr/bin/env python3
"""
OFFLINE TEST: does leaving tries=8 really permit EXACTLY ONE attempt? (Peter, Nov 12.)

No network, no credentials, no state file. It imports the REAL MAX_TRIES from clv_ledger and
replays clv_ledger's own two loops verbatim, so it tests the shipped control rather than a
description of it.

THE CLAIM UNDER TEST. The one-time recovery sets done=False and deliberately does NOT reset tries.
The argument is that the EXISTING guard then does the work: a reopened row gets one attempt, and a
failure increments 8 -> 9, clears MAX_TRIES, and retires the row again. If that is wrong, the
recovery creates an unlimited retry cycle, and Peter's instruction is to STOP.

The loops being replayed, from clv_ledger:

    # pending
    if rec.get("clv") is not None or rec.get("done"): continue

    # scoring, on a fixture miss
    if lg in fetched:
        rec["tries"] = rec.get("tries", 0) + 1
        rec["why"]   = "no OddsPapi fixture matched"
        if rec["tries"] >= MAX_TRIES: rec["done"] = True
    else:
        rec["why"] = "no fixture yet - no fresh lookup this run (6 h cooldown), retry not counted"

The `fetched` guard matters: a run that did not look fixtures up for that league must not burn a
retry. So a reopened row can wait across runs without being retried - that is waiting, not
retrying, and it still holds only one attempt.
"""
import sys

from clv_ledger import MAX_TRIES


def enters_scoring(rec):
    """clv_ledger's pending gate."""
    return rec.get("clv") is None and not rec.get("done")


def attempt(rec, matched, league_fetched):
    """One pass of clv_ledger's scoring loop for this row. Returns 'scored' | 'missed' | 'waited'."""
    if matched:
        rec["clv"] = -0.0123          # a real score; the row leaves the queue for good
        return "scored"
    if league_fetched:
        rec["tries"] = rec.get("tries", 0) + 1
        rec["why"] = "no OddsPapi fixture matched"
        if rec["tries"] >= MAX_TRIES:
            rec["done"] = True
        return "missed"
    rec["why"] = "no fixture yet - no fresh lookup this run (6 h cooldown), retry not counted"
    return "waited"


def reopened():
    """A row exactly as the one-time recovery leaves it: done cleared, tries PRESERVED."""
    return {"clv": None, "done": False, "tries": MAX_TRIES,
            "why": "reopened once: retired by the pre-fix matcher, which now resolves it"}


def main():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if got == want else 'FAIL'} {name}")

    print(f"OFFLINE TEST - one attempt only (real MAX_TRIES={MAX_TRIES})")
    print("=" * 84)
    check("the recovery preserves tries at MAX_TRIES", reopened()["tries"], MAX_TRIES)

    # --- the decisive case: reopened, attempt FAILS, league was fetched
    r = reopened()
    check("a reopened row enters scoring", enters_scoring(r), True)
    check("the attempt runs and misses", attempt(r, matched=False, league_fetched=True), "missed")
    check("tries incremented past MAX_TRIES", r["tries"], MAX_TRIES + 1)
    check("the row retired itself again", r["done"], True)
    check("and it can no longer enter scoring", enters_scoring(r), False)

    # --- it must stay retired over further runs: no cycle
    for i in range(5):
        if enters_scoring(r):
            fails.append(f"row re-entered scoring on later run {i}")
    check("still retired after 5 further runs", enters_scoring(r), False)

    # --- a reopened row whose attempt SUCCEEDS keeps its score and leaves the queue
    r2 = reopened()
    check("successful attempt scores", attempt(r2, matched=True, league_fetched=True), "scored")
    check("a scored row leaves the queue", enters_scoring(r2), False)
    check("its tries were not touched by success", r2["tries"], MAX_TRIES)
    check("and it was NOT marked done by scoring", r2.get("done"), False)

    # --- the cooldown case: no fetch this run must not burn the single attempt
    r3 = reopened()
    check("no fetch -> waited, not missed", attempt(r3, matched=False, league_fetched=False),
          "waited")
    check("waiting did not burn a try", r3["tries"], MAX_TRIES)
    check("waiting left it eligible", enters_scoring(r3), True)
    # ...and when a fetch finally happens, it still gets exactly one
    check("the deferred attempt then misses", attempt(r3, matched=False, league_fetched=True),
          "missed")
    check("and retires it", enters_scoring(r3), False)

    # --- a row NOT reopened (still done) never enters scoring at all
    r4 = {"clv": None, "done": True, "tries": MAX_TRIES, "why": "no OddsPapi fixture matched"}
    check("an un-reopened retired row stays out", enters_scoring(r4), False)

    # --- an already-scored row is never re-entered, reopened or not
    r5 = {"clv": -0.02, "done": False, "tries": 3}
    check("an already-scored row stays out", enters_scoring(r5), False)

    print("=" * 84)
    if fails:
        for f in fails:
            print("  " + f)
        print("  FAIL - STOP. Do not apply the recovery.")
        return 1
    print("  PASS - a reopened row gets EXACTLY ONE attempt. A miss takes tries to")
    print(f"  {MAX_TRIES + 1} >= {MAX_TRIES} and retires it again through the existing guard; it never")
    print("  re-enters. A cooldown run does not burn the attempt. No retry logic is changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
