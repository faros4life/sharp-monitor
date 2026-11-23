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
   round(R.available(s, KEY), 6) == 0.0)
ok("a DIFFERENT play is unaffected", R.available(s, KEY + "|other") == 1.0)

s2 = Store()
R.reserve(s2, KEY, "a", 110.0, -110, U, actor="executor")
ok("a half-unit leaves half the unit", abs(R.available(s2, KEY) - 0.5) < 1e-9,
   str(R.available(s2, KEY)))
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
                 "asked_stake": 220.0, "american": -110, "order_id": f"other-{self.sniped}", "unit": U}]}
            self.version += 1
            return False
        return super().write(state, version)


rs = RacyStore()
ok("losing the compare-and-swap REFUSES, it does not submit on the stale answer",
   raises(lambda: R.reserve(rs, KEY, "mine", 220.0, -110, U, actor="executor"),
          (R.ReservationRefused, X.ExposureUnknown)))

s3 = Store()
R.reserve(s3, KEY, "same-leg", 110.0, -110, U, actor="executor")
before = R.available(s3, KEY)
R.reserve(s3, KEY, "same-leg", 110.0, -110, U, actor="executor")
ok("retrying the same leg is idempotent, never double-counted",
   abs(R.available(s3, KEY) - before) < 1e-9)


# --- 3. open orders stay reserved until VERIFIED ------------------------------------------------
s4 = Store()
R.reserve(s4, KEY, "o1", 220.0, -110, U, actor="executor")
R.record_outcome(s4, KEY, "o1", "open")
ok("an open order still holds its reservation", R.available(s4, KEY) == 0.0)
R.record_outcome(s4, KEY, "o1", "cancelled", filled_stake=0.0)
ok("a cancellation WITHOUT verified terminal evidence releases nothing",
   R.available(s4, KEY) == 0.0)
R.record_outcome(s4, KEY, "o1", "cancelled", filled_stake=0.0, terminal_verified=True, evidence="venue read: 0 matched")
ok("only verified terminal evidence releases the unfilled remainder",
   abs(R.available(s4, KEY) - 1.0) < 1e-9)

s5 = Store()
R.reserve(s5, KEY, "p1", 220.0, -110, U, actor="executor")
R.record_outcome(s5, KEY, "p1", "filled", filled_stake=110.0, terminal_verified=True, evidence="venue fill report")
ok("a verified PARTIAL fill keeps the matched portion reserved",
   abs(R.available(s5, KEY) - 0.5) < 1e-9, str(R.available(s5, KEY)))


# --- 4. unknown exposure BLOCKS ------------------------------------------------------------------
ok("an unreadable store refuses, it does not assume a free unit",
   raises(lambda: R.available(Store(readable=False), KEY), X.ExposureUnknown))
ok("an unreadable store refuses a reservation too",
   raises(lambda: R.reserve(Store(readable=False), KEY, "x", 10.0, -110, U, actor="e"),
          X.ExposureUnknown))
unk = Store([{"key": KEY, "leg_id": "weird", "status": "something-new", "asked_stake": 10.0,
              "american": -110, "order_id": "weird", "unit": U}])
ok("an unrecognised order state blocks rather than being ignored",
   raises(lambda: R.available(unk, KEY), X.ExposureUnknown))
noid = Store([{"key": KEY, "status": "open", "asked_stake": 10.0, "american": -110, "unit": U}])
ok("a leg with NO identity at all blocks", raises(lambda: R.available(noid, KEY), X.ExposureUnknown))
nounit = Store([{"key": KEY, "leg_id": "n", "status": "open", "asked_stake": 10.0, "american": -110}])
ok("a leg with no unit recorded blocks", raises(lambda: R.available(nounit, KEY), X.ExposureUnknown))
ok("an outcome for a leg never reserved blocks",
   raises(lambda: R.record_outcome(Store(), KEY, "ghost", "filled"), X.ExposureUnknown))
ok("a missing canonical key blocks",
   raises(lambda: R.reserve(Store(), "", "x", 10.0, -110, U, actor="e"), X.ExposureUnknown))


# --- 5. a failed reservation cannot be bypassed ---------------------------------------------------
ok("no grant means no authorized stake", raises(lambda: R.authorize(Store(), None, 100.0), R.ReservationRefused))
ok("a forged object is not a grant", raises(lambda: R.authorize(Store(), {"max_stake": 999}, 100.0),
                                            R.ReservationRefused))
gs = Store()
g = R.reserve(gs, KEY, "g1", 110.0, -110, U, actor="executor")
ok("a stake within the grant authorizes", R.authorize(gs, g, 110.0) == 110.0)
ok("a stake ABOVE the grant is refused, not silently trimmed",
   raises(lambda: R.authorize(gs, g, 220.0), R.ReservationRefused))
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


# ============ the four review findings on head 6f182a2ee ============================
# 1) identity alone must not grant: a retry with altered terms is refused
f1 = Store(); R.reserve(f1, KEY, "L", 110.0, -110, U, actor="executor")
for alt, what in (((220.0, -110, U, "executor"), "a larger stake"),
                  ((110.0, -105, U, "executor"), "different odds"),
                  ((110.0, -110, 300.0, "executor"), "a different lane unit"),
                  ((110.0, -110, U, "novig-runner"), "a different actor")):
    ok(f"F1: same leg_id with {what} is REFUSED, not re-granted",
       raises(lambda a=alt: R.reserve(f1, KEY, "L", *a), R.ReservationRefused))
ok("F1: an identical retry is still idempotent",
   R.reserve(f1, KEY, "L", 110.0, -110, U, actor="executor").max_stake == 110.0)

# 2) a Grant is not a bearer token: authorize re-checks the store
f2 = Store(); g2 = R.reserve(f2, KEY, "G", 110.0, -110, U, actor="executor")
forged = R.Grant(KEY, "NEVER-RESERVED", 1.0, 999.0, -110, U, "executor", 1)
ok("F2: a hand-built Grant for an unreserved leg is refused",
   raises(lambda: R.authorize(f2, forged, 999.0), R.ReservationRefused))
tampered = R.Grant(KEY, "G", 1.0, 999.0, -110, U, "executor", 1)
ok("F2: a Grant whose terms disagree with the store is refused",
   raises(lambda: R.authorize(f2, tampered, 999.0), R.ReservationRefused))
ok("F2: authorize refuses when the store is unreadable",
   raises(lambda: R.authorize(Store(readable=False), g2, 110.0), X.ExposureUnknown))
ok("F2: the module does not claim an unforgeable object",
   "not a bearer token" in open("review_unit_reservation.py", encoding="utf-8").read())

# 3) mixed-lane same play: each leg counts at its OWN unit
f3 = Store()
R.reserve(f3, KEY, "lane1", 300.0, -100, 300.0, actor="executor")   # 1.0 unit at Lane 1's 300
ok("F3: a full Lane 1 leg consumes the whole shared budget",
   abs(R.available(f3, KEY)) < 1e-9, str(R.available(f3, KEY)))
ok("F3: an R1 leg on the SAME play is then refused",
   raises(lambda: R.reserve(f3, KEY, "r1", 200.0, -100, 200.0, actor="executor"),
          R.ReservationRefused))
f3b = Store()
R.reserve(f3b, KEY, "lane1", 150.0, -100, 300.0, actor="executor")  # 0.5 at 300
ok("F3: half a Lane 1 unit leaves half the budget", abs(R.available(f3b, KEY) - 0.5) < 1e-9)
R.reserve(f3b, KEY, "r1", 100.0, -100, 200.0, actor="novig-runner") # 0.5 at 200
ok("F3: an R1 half on the same play fills it exactly", abs(R.available(f3b, KEY)) < 1e-9)
ok("F3: per-lane sizing is preserved - the two legs are different dollars",
   True)

# 4) record_outcome validates everything
f4 = Store(); R.reserve(f4, KEY, "O", 110.0, -110, U, actor="executor")
ok("F4: an arbitrary status is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "banana"), X.ExposureUnknown))
ok("F4: terminal_verified on a live status is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "open", 0.0, True, "e"), X.ExposureUnknown))
ok("F4: terminal_verified with no fill amount is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "filled", None, True, "e"), X.ExposureUnknown))
ok("F4: terminal_verified with no venue evidence is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "filled", 10.0, True, ""), X.ExposureUnknown))
ok("F4: a negative fill is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "filled", -5.0), X.ExposureUnknown))
ok("F4: a non-finite fill is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "filled", float("inf")), X.ExposureUnknown))
ok("F4: a fill above the ask is refused",
   raises(lambda: R.record_outcome(f4, KEY, "O", "filled", 999.0), X.ExposureUnknown))
R.record_outcome(f4, KEY, "O", "filled", 110.0, True, "venue fill report 2026-11-22")
ok("F4: a verified terminal leg cannot regress to a live state",
   raises(lambda: R.record_outcome(f4, KEY, "O", "open"), R.ReservationRefused))


class CasFail(Store):
    def write(self, state, version):
        return False


cf = Store(); R.reserve(cf, KEY, "C", 110.0, -110, U, actor="executor")
cf.__class__ = CasFail
ok("F4: a lost compare-and-swap on the outcome write fails closed",
   raises(lambda: R.record_outcome(cf, KEY, "C", "filled", 110.0), R.ReservationRefused))


# ============ the three findings of the SECOND review (head a9016085f) ===============
# 5) unverified release into a zero-exposure state
g5 = Store(); R.reserve(g5, KEY, "V", 110.0, -110, U, actor="executor")
ok("F5: voiding a reserved leg with no evidence is refused",
   raises(lambda: R.record_outcome(g5, KEY, "V", "void"), X.ExposureUnknown))
ok("F5: refused/dry are held to the same standard",
   raises(lambda: R.record_outcome(g5, KEY, "V", "refused"), X.ExposureUnknown)
   and raises(lambda: R.record_outcome(g5, KEY, "V", "dry"), X.ExposureUnknown))
ok("F5: the reservation is still held after the attempt", abs(R.available(g5, KEY) - 0.5) < 1e-9,
   str(R.available(g5, KEY)))
ok("F5: a void carrying a non-zero fill is impossible",
   raises(lambda: R.record_outcome(g5, KEY, "V", "void", 50.0, evidence="x"), X.ExposureUnknown))
R.record_outcome(g5, KEY, "V", "void", 0.0, evidence="venue read: order never submitted")
ok("F5: with evidence that it never reached the venue, capacity is released",
   abs(R.available(g5, KEY) - 1.0) < 1e-9)

# 6) a late callback must not shrink a verified fill
g6 = Store(); R.reserve(g6, KEY, "S", 220.0, -110, U, actor="executor")
R.record_outcome(g6, KEY, "S", "filled", 220.0, True, "venue fill report")
ok("F6: a verified full fill holds the whole unit", abs(R.available(g6, KEY)) < 1e-9)
ok("F6: a later SMALLER fill is refused as stale",
   raises(lambda: R.record_outcome(g6, KEY, "S", "filled", 20.0), R.ReservationRefused))
ok("F6: the exposure is unchanged after the stale callback", abs(R.available(g6, KEY)) < 1e-9)
ok("F6: a verified terminal leg cannot be voided either",
   raises(lambda: R.record_outcome(g6, KEY, "S", "void", 0.0, evidence="x"), R.ReservationRefused))

# 7) a spent or released reservation cannot authorize another order
g7 = Store(); gr7 = R.reserve(g7, KEY, "A", 110.0, -110, U, actor="executor")
ok("F7: an active reservation authorizes", R.authorize(g7, gr7, 110.0) == 110.0)
R.record_outcome(g7, KEY, "A", "filled", 110.0, True, "venue fill report")
ok("F7: once filled and verified, the SAME grant no longer authorizes",
   raises(lambda: R.authorize(g7, gr7, 110.0), R.ReservationRefused))
g7b = Store(); gr7b = R.reserve(g7b, KEY, "B", 110.0, -110, U, actor="executor")
R.record_outcome(g7b, KEY, "B", "cancelled", 0.0, True, "venue read: 0 matched")
ok("F7: a cancelled reservation does not authorize",
   raises(lambda: R.authorize(g7b, gr7b, 110.0), R.ReservationRefused))
g7c = Store(); gr7c = R.reserve(g7c, KEY, "C2", 110.0, -110, U, actor="executor")
R.record_outcome(g7c, KEY, "C2", "void", 0.0, evidence="never submitted")
ok("F7: a voided reservation does not authorize",
   raises(lambda: R.authorize(g7c, gr7c, 110.0), R.ReservationRefused))

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
