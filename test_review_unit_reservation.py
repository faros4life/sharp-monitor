#!/usr/bin/env python3
"""REVIEW ONLY. Tests for the two-runner atomic reservation protocol (draft PR #10).

Each of Peter's six requirements has its own named test. The two that matter most are the ones a
pure calculator cannot give you: two runners racing on the same play, and the impossibility of
submitting without a grant.
"""
import sys

import review_unit_exposure as X
import review_unit_reservation as R

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


class Store:
    """A durable store with compare-and-swap, the shape registry.claim_submission already has."""

    def __init__(self, legs=None, readable=True):
        self.state = {"legs": list(legs or [])}
        self.version = 1
        self.readable = readable
        self.writes = 0

    def read(self):
        return (None, None) if not self.readable else (dict(self.state), self.version)

    def write(self, state, version):
        self.writes += 1
        if version != self.version:
            return False
        self.state = dict(state)
        self.version += 1
        return True


KEY = "NBA|2026-11-22|LAL@BOS|total|under|225.5"
U = 200.0


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


# --- 1. ONE budget shared by both runners ------------------------------------------------------
s = Store()
g1 = R.reserve(s, KEY, "px-1", 220.0, -110, U, actor="executor")
ok("runner A reserves most of the unit", round(g1.units, 3) == 1.0, str(g1.units))
ok("runner B is then refused on the SAME play from a different system",
   raises(lambda: R.reserve(s, KEY, "novig-1", 220.0, -110, U, actor="novig-runner"),
          R.ReservationRefused))
ok("the budget is per play, not per venue or per lane",
   round(R.available(s, KEY, U), 6) == 0.0)
ok("a DIFFERENT play is unaffected", R.available(s, KEY + "|other", U) == 1.0)

s2 = Store()
R.reserve(s2, KEY, "a", 110.0, -110, U, actor="executor")
ok("a half-unit leaves half the unit", abs(R.available(s2, KEY, U) - 0.5) < 1e-9,
   str(R.available(s2, KEY, U)))
ok("the second half is grantable to the other runner",
   R.reserve(s2, KEY, "b", 110.0, -110, U, actor="novig-runner").units > 0)
ok("but a third leg is not", raises(lambda: R.reserve(s2, KEY, "c", 1.0, -110, U, actor="x"),
                                    R.ReservationRefused))


# --- 2. atomic: the loser of a race does not proceed on a stale read ---------------------------
class RacyStore(Store):
    """Another runner commits in between this runner's read and write, every time."""

    def __init__(self):
        super().__init__()
        self.sniped = 0

    def write(self, state, version):
        if self.sniped < 99:          # always lose
            self.sniped += 1
            self.state = {"legs": list(self.state.get("legs") or []) + [
                {"key": KEY, "leg_id": f"other-{self.sniped}", "status": "open",
                 "asked_stake": 220.0, "american": -110, "order_id": f"other-{self.sniped}"}]}
            self.version += 1
            return False
        return super().write(state, version)


rs = RacyStore()
ok("losing the compare-and-swap REFUSES, it does not submit on the stale answer",
   raises(lambda: R.reserve(rs, KEY, "mine", 220.0, -110, U, actor="executor"),
          (R.ReservationRefused, X.ExposureUnknown)))

s3 = Store()
R.reserve(s3, KEY, "same-leg", 110.0, -110, U, actor="executor")
before = R.available(s3, KEY, U)
R.reserve(s3, KEY, "same-leg", 110.0, -110, U, actor="executor")
ok("retrying the same leg is idempotent, never double-counted",
   abs(R.available(s3, KEY, U) - before) < 1e-9)


# --- 3. open orders stay reserved until VERIFIED ------------------------------------------------
s4 = Store()
R.reserve(s4, KEY, "o1", 220.0, -110, U, actor="executor")
R.record_outcome(s4, KEY, "o1", "open")
ok("an open order still holds its reservation", R.available(s4, KEY, U) == 0.0)
R.record_outcome(s4, KEY, "o1", "cancelled", filled_stake=0.0)
ok("a cancellation WITHOUT verified terminal evidence releases nothing",
   R.available(s4, KEY, U) == 0.0)
R.record_outcome(s4, KEY, "o1", "cancelled", filled_stake=0.0, terminal_verified=True)
ok("only verified terminal evidence releases the unfilled remainder",
   abs(R.available(s4, KEY, U) - 1.0) < 1e-9)

s5 = Store()
R.reserve(s5, KEY, "p1", 220.0, -110, U, actor="executor")
R.record_outcome(s5, KEY, "p1", "filled", filled_stake=110.0, terminal_verified=True)
ok("a verified PARTIAL fill keeps the matched portion reserved",
   abs(R.available(s5, KEY, U) - 0.5) < 1e-9, str(R.available(s5, KEY, U)))


# --- 4. unknown exposure BLOCKS ------------------------------------------------------------------
ok("an unreadable store refuses, it does not assume a free unit",
   raises(lambda: R.available(Store(readable=False), KEY, U), X.ExposureUnknown))
ok("an unreadable store refuses a reservation too",
   raises(lambda: R.reserve(Store(readable=False), KEY, "x", 10.0, -110, U, actor="e"),
          X.ExposureUnknown))
unk = Store([{"key": KEY, "leg_id": "weird", "status": "something-new", "asked_stake": 10.0,
              "american": -110, "order_id": "weird"}])
ok("an unrecognised order state blocks rather than being ignored",
   raises(lambda: R.available(unk, KEY, U), X.ExposureUnknown))
noid = Store([{"key": KEY, "leg_id": "n", "status": "open", "asked_stake": 10.0, "american": -110}])
ok("a leg with no order identity blocks", raises(lambda: R.available(noid, KEY, U), X.ExposureUnknown))
ok("an outcome for a leg never reserved blocks",
   raises(lambda: R.record_outcome(Store(), KEY, "ghost", "filled"), X.ExposureUnknown))
ok("a missing canonical key blocks",
   raises(lambda: R.reserve(Store(), "", "x", 10.0, -110, U, actor="e"), X.ExposureUnknown))


# --- 5. a failed reservation cannot be bypassed ---------------------------------------------------
ok("no grant means no authorized stake", raises(lambda: R.authorize(None, 100.0), R.ReservationRefused))
ok("a forged object is not a grant", raises(lambda: R.authorize({"max_stake": 999}, 100.0),
                                            R.ReservationRefused))
g = R.reserve(Store(), KEY, "g1", 110.0, -110, U, actor="executor")
ok("a stake within the grant authorizes", R.authorize(g, 110.0) == 110.0)
ok("a stake ABOVE the grant is refused, not silently trimmed",
   raises(lambda: R.authorize(g, 220.0), R.ReservationRefused))
ok("authorize is the only function that returns permission",
   not any(n for n in dir(R) if n.startswith("force") or n.startswith("override")))


# --- 6. nothing here cancels or shrinks a venue order ---------------------------------------------
src = open(__file__.replace("test_review_unit_reservation.py", "review_unit_reservation.py"),
           encoding="utf-8").read()
# needles are CALLS and DEFINITIONS, not prose: the docstrings discuss cancelling and shrinking
# precisely to say the module does not do them, and a word-match would flag that explanation.
for bad in ("cancel(", "def cancel", "shrink(", "def shrink", "amend(", "place(", "submit(",
            "requests.", "urllib"):
    ok(f"reservation module has no {bad!r}", bad not in src)
ok("it performs no I/O of its own", "open(" not in src and "json.load" not in src)
ok("the store is injected, not constructed", "def reserve(store" in src)

# --- review-only: not wired to anything ------------------------------------------------------------
import subprocess
hits = subprocess.run(["grep", "-rln", "review_unit_reservation", "--include=*.py", "."],
                      capture_output=True, text=True).stdout.split()
ok("no production module imports it",
   all(h.endswith(("review_unit_reservation.py", "test_review_unit_reservation.py")) for h in hits),
   str(hits))

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
