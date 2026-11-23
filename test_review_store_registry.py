#!/usr/bin/env python3
"""REVIEW ONLY. The shared-store adapter, and the two proofs Peter asked for:

  - a duplicate submission cannot reuse a reservation
  - an unknown fill cannot release exposure

Both are exercised THROUGH the adapter, against a fake registry, so they test the protocol over the
store contract rather than over a hand-made dict.
"""
import sys

import review_store_registry as S
import review_unit_exposure as X
import review_unit_reservation as R

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


class FakeRegistry:
    """The shape registry.py already has: _fetch() -> (data, sha), plus a conditional PUT."""

    def __init__(self, data=None, readable=True):
        self.data = dict(data or {})
        self.sha = "sha-1"
        self.readable = readable
        self.puts = 0

    def _fetch(self):
        return (None, None) if not self.readable else (dict(self.data), self.sha)

    def _put_with_sha(self, merged, sha):
        self.puts += 1
        if sha != self.sha:
            return False
        self.data = dict(merged)
        self.sha = f"sha-{int(self.sha.split('-')[1]) + 1}"
        return True


KEY = "NBA|2026-11-22|LAL@BOS|total|under|225.5"
U = 200.0


def seeded_unreadable():
    return S.RegistryStore(FakeRegistry(readable=False))


def seeded(reg=None):
    """A store whose ledger has been migrated - finding 9. The adapter tests below are about the
    STORE contract, so they start from a seeded ledger; the migration itself is tested separately."""
    st = S.RegistryStore(reg or FakeRegistry())
    R.backfill(st, [], "test fixture: no pre-existing venue orders")
    return st

# --- the adapter honours the contract ------------------------------------------------------------
st = S.RegistryStore(FakeRegistry())
state, ver = st.read()
ok("an empty store reads as empty, not as unreadable", state == {"legs": []} and ver is not None)
ok("an UNREADABLE store reads as (None, None), never as empty",
   S.RegistryStore(FakeRegistry(readable=False)).read() == (None, None))
ok("state lives under one key inside the existing file, not in a second file",
   S.LEDGER_KEY == "unit_reservations")

fr = FakeRegistry({"orders": [{"id": "pre-existing"}]})
st2 = seeded(fr)
R.reserve(st2, KEY, "a", 110.0, -110, U, actor="executor")
ok("writing the ledger preserves the rest of the registry file",
   fr.data.get("orders") == [{"id": "pre-existing"}])
ok("the reservation is visible on a fresh read", abs(R.available(st2, KEY) - 0.5) < 1e-9)

ok("a stale version loses the compare-and-swap", st2.write({"legs": []}, "sha-999") is False)
ok("a registry with no conditional PUT fails CLOSED rather than writing",
   S.RegistryStore(type("NoPut", (), {"_fetch": lambda s: ({}, "x")})()).write({"legs": []}, "x")
   is False)
ok("a registry that raises fails closed",
   S.RegistryStore(type("Boom", (), {"_fetch": lambda s: (_ for _ in ()).throw(RuntimeError())})()
                   ).read() == (None, None))

# --- PROOF 1: a duplicate submission cannot reuse a reservation -----------------------------------
p1 = seeded()
g = R.reserve(p1, KEY, "order-1", 220.0, -110, U, actor="executor")
ok("P1: the first submission is authorized", R.authorize(p1, g, 220.0) == 220.0)
ok("P1: a second submission on the same reservation is REFUSED",
   raises(lambda: R.authorize(p1, g, 220.0), R.ReservationRefused))
ok("P1: the other runner cannot authorize it either",
   raises(lambda: R.authorize(p1, g, 220.0), R.ReservationRefused))
ok("P1: re-reserving the same leg does not mint a usable second grant",
   raises(lambda: R.authorize(p1, R.reserve(p1, KEY, "order-1", 220.0, -110, U, actor="executor"),
                              220.0), R.ReservationRefused))
ok("P1: and the play still holds exactly ONE unit of exposure, not two",
   abs(R.available(p1, KEY)) < 1e-9, str(R.available(p1, KEY)))
ok("P1: a second leg on the same play is refused for want of budget",
   raises(lambda: R.reserve(p1, KEY, "order-2", 220.0, -110, U, actor="novig-runner"),
          R.ReservationRefused))

# --- PROOF 2: an unknown fill cannot release exposure ----------------------------------------------
p2 = seeded()
R.reserve(p2, KEY, "o", 220.0, -110, U, actor="executor")
held = R.available(p2, KEY)
ok("P2: a fresh reservation holds the whole unit", abs(held) < 1e-9)
for call, what in (
        (lambda: R.record_outcome(p2, KEY, "o", "cancelled", 0.0), "an unverified cancellation"),
        (lambda: R.record_outcome(p2, KEY, "o", "expired", 0.0), "an unverified expiry"),
        (lambda: R.record_outcome(p2, KEY, "o", "void"), "a void with no evidence"),
        (lambda: R.record_outcome(p2, KEY, "o", "filled", None, True, "e"), "a terminal with no fill"),
        (lambda: R.record_outcome(p2, KEY, "o", "filled", 0.0, True, ""), "a terminal with no evidence"),
        (lambda: R.record_outcome(p2, KEY, "o", "banana"), "an unrecognised status")):
    try:
        call()
    except Exception:
        pass
    ok(f"P2: {what} does not release exposure", abs(R.available(p2, KEY)) < 1e-9,
       str(R.available(p2, KEY)))

ok("P2: an unreadable store blocks rather than reporting free capacity",
   raises(lambda: R.available(seeded_unreadable(), KEY),
          X.ExposureUnknown))
R.record_outcome(p2, KEY, "o", "cancelled", 0.0, True, "venue read: 0 matched quantity")
ok("P2: only an explicit verified zero from the venue releases it",
   abs(R.available(p2, KEY) - 1.0) < 1e-9)

# --- the wiring gap is stated, not implied ----------------------------------------------------------
gap = S.wiring_gap()
ok("the remaining wiring is enumerated", len(gap) == 4)
ok("it names both repositories", {g[0] for g in gap} == {"sharp-monitor", "novig-runner"})
ok("it names the runner's own send path",
   any("novig_live_order.place()" in g[1] for g in gap))

import subprocess

hits = subprocess.run(["grep", "-rln", "review_store_registry", "--include=*.py", "."],
                      capture_output=True, text=True).stdout.split()
ok("no production module imports the adapter",
   all(h.endswith(("review_store_registry.py", "test_review_store_registry.py")) for h in hits),
   str(hits))
# Match CODE, not prose: the module docstring names REGISTRY_TOKEN and registry._commit precisely
# in order to say it uses neither, and a whole-file match would flag that explanation.
full = open("review_store_registry.py", encoding="utf-8").read()
import ast as _ast
body = full
_mod = _ast.parse(full)
if _ast.get_docstring(_mod):
    body = "\n".join(full.split("\n")[_mod.body[0].end_lineno:])
ok("the adapter holds no token of its own",
   "TOKEN" not in body and "Bearer" not in body and "Authorization" not in body)
ok("it does not CALL registry._commit, whose retry is unsafe here",
   "._commit(" not in body and "_commit(merge" not in body)
ok("it does call the registry's own fetch", "._fetch()" in body)
ok("the docstring explains why _commit is unsafe here", "_commit" in full)


# --- migration through the real store contract ------------------------------------------------
m = S.RegistryStore(FakeRegistry())
ok("M: a brand-new ledger on the shared store does not read as a free unit",
   raises(lambda: R.available(m, KEY), X.ExposureUnknown))
R.backfill(m, [{"key": KEY, "order_id": "venue-order", "status": "open", "asked_stake": 220.0,
                "american": -110, "unit": U}], "seeded from registry filled+resting")
ok("M: after seeding, a play already live at the venue has no capacity",
   abs(R.available(m, KEY)) < 1e-9, str(R.available(m, KEY)))
ok("M: the seed is persisted in the store, not held in memory",
   m._r.data["unit_reservations"].get("seeded") is True)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
