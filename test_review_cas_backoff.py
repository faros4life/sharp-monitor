"""Lost compare-and-swap must be RETRIED, not read as "the unit is taken". Nov 24, 2026.

A real Novig order (BOARD V4, NBA Dallas/Denver Under 233.5) was refused and never placed with
"lost the compare-and-swap claiming this reservation". The registry is shared with ordinary
bookkeeping writes, so a lost CAS is usually somebody else's unrelated commit - but all three
attempts fired back-to-back with no pause, so they landed in the same burst and the order died.

Two states with opposite remedies were reading as one: "another runner holds this reservation"
(refuse) and "an unrelated commit beat us to the file" (re-read and try again).

The danger in fixing it is loosening the budget by accident, so most of this file is about what
must STILL refuse."""
import time
import review_unit_reservation as R

FAILED = []
SLEPT = []
R._cas_pause = lambda attempt, sleep=None: SLEPT.append(attempt)   # no real waiting in tests


def ok(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


class Store:
    """A registry that loses the CAS `lose` times, then accepts - like unrelated commits landing."""

    def __init__(self, state, lose=0):
        self.state, self.lose, self.version, self.writes = state, lose, 1, 0

    def read(self):
        return (self.state, self.version)

    def write(self, new, version):
        self.writes += 1
        if self.lose > 0:                 # somebody else committed first
            self.lose -= 1
            self.version += 1             # and the version moved, so a stale write cannot win
            return False
        if version != self.version:
            return False
        self.state, self.version = new, self.version + 1
        return True


def seeded(legs=None):
    return {"seeded": True, "legs": list(legs or [])}


KEY = "NBA|DAL@DEN|side|UNDER"


def fresh(lose=0, legs=None):
    SLEPT.clear()
    return Store(seeded(legs), lose=lose)


# --- the bug: a transient loss must not kill the order ---------------------------------------
s = fresh(lose=2)
try:
    g = R.reserve(s, KEY, "leg-1", 200.0, 104, 200.0, "cloud")
    ok("reserve survives 2 unrelated commits", g is not None)
except Exception as e:
    ok(f"reserve survives 2 unrelated commits (raised {type(e).__name__})", False)
ok("reserve paused between attempts, did not spin", len(SLEPT) == 2)
ok("reserve paused with rising attempt numbers", SLEPT == [0, 1])

# --- what must STILL refuse: the budget is not loosened ---------------------------------------
full = [{"key": KEY, "leg_id": "other", "status": "open", "asked_stake": 200.0,
         "american": 104, "unit": 200.0, "order_id": "other", "actor": "cloud"}]
try:
    R.reserve(fresh(lose=0, legs=full), KEY, "leg-2", 200.0, 104, 200.0, "cloud")
    ok("a full play still refuses on the budget", False)
except R.ReservationRefused as e:
    ok("a full play still refuses on the budget", "unit budget" in str(e))
except Exception:
    ok("a full play still refuses on the budget", False)

# and it refuses on the FIRST read - retrying must not be used to wait out a full budget
s = fresh(lose=0, legs=full)
try:
    R.reserve(s, KEY, "leg-3", 200.0, 104, 200.0, "cloud")
except Exception:
    pass
ok("a full play refuses immediately, with no retries", SLEPT == [] and s.writes == 0)

# --- a genuinely exhausted store still refuses, it does not loop forever ----------------------
s = fresh(lose=99)
try:
    R.reserve(s, KEY, "leg-4", 200.0, 104, 200.0, "cloud")
    ok("a store that keeps moving still refuses", False)
except R.ReservationRefused:
    ok("a store that keeps moving still refuses", True)
except Exception:
    ok("a store that keeps moving still refuses", False)
ok("refusal is bounded by attempts", s.writes == R._CAS_ATTEMPTS)
ok("no pause after the final attempt", len(SLEPT) == R._CAS_ATTEMPTS - 1)

# --- an unreadable store still fails closed, with no retrying ---------------------------------
class Dead:
    def read(self):
        return None

    def write(self, *a):
        raise AssertionError("must not write to an unreadable store")


SLEPT.clear()
try:
    R.reserve(Dead(), KEY, "leg-5", 200.0, 104, 200.0, "cloud")
    ok("unreadable store fails closed", False)
except R.ExposureUnknown:
    ok("unreadable store fails closed", True)
except Exception:
    ok("unreadable store fails closed", False)
ok("unreadable store is not retried", SLEPT == [])

# --- the pause itself: bounded, jittered, and it actually sleeps -------------------------------
real = R.__dict__["_cas_pause"]
import importlib
importlib.reload(R)
R._cas_pause = R.__dict__["_cas_pause"]
waits = []
for attempt in range(6):
    seen = []
    R._cas_pause(attempt, sleep=seen.append)
    waits.append(seen[0])
ok("every pause is positive", all(w > 0 for w in waits))
ok("every pause is capped", all(w <= R._CAS_CAP * 1.5 + 1e-9 for w in waits))
ok("pauses grow then flatten", waits[0] < R._CAS_CAP * 1.5 and waits[-1] <= R._CAS_CAP * 1.5)
seen_a, seen_b = [], []
R._cas_pause(3, sleep=seen_a.append)
R._cas_pause(3, sleep=seen_b.append)
ok("pauses are jittered, not identical", seen_a[0] != seen_b[0])
ok("a real pause actually waits", (lambda t0: (R._cas_pause(0), time.monotonic() - t0 > 0)[1])(time.monotonic()))

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
