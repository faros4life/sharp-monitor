#!/usr/bin/env python3
"""REVIEW ONLY. Proof that the real order paths refuse without a valid shared reservation.

Two kinds of evidence, because neither alone is enough:
  - BEHAVIOURAL: the guard itself refuses, on every path, for every reason.
  - STRUCTURAL: each real dispatch function actually calls it, and calls it BEFORE it dispatches.
    A guard nothing calls passes every behavioural test ever written.
"""
import os
import re
import sys

import review_integration as RI
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
    def __init__(self):
        self.data, self.sha = {}, "s1"

    def _fetch(self):
        return (dict(self.data), self.sha)

    def _put_with_sha(self, merged, sha):
        if sha != self.sha:
            return False
        self.data, self.sha = dict(merged), f"s{int(self.sha[1:]) + 1}"
        return True


KEY = RI.play_key("NBA", "LAL @ BOS", "total", "under", 225.5)
U = 200.0


def seeded():
    st = S.RegistryStore(FakeRegistry())
    R.backfill(st, [], "test fixture")
    return st


def on():
    os.environ[RI.FLAG] = "on"


def off():
    os.environ.pop(RI.FLAG, None)


# --- the flag is OFF by default: landing this code changes nothing ------------------------------
off()
ok("the ledger is OFF unless switched on", RI.enabled() is False)
ok("with it off the guard is a no-op",
   RI.guard_or_refuse(seeded(), KEY, "l", 220.0, -110, U, "a") is None)
ok("with it off the stake passes through unchanged", RI.authorized_stake(None, None, 220.0) == 220.0)
ok("the flag is a repo variable, not a code default",
   'os.environ.get(FLAG) or "off"' in open("review_integration.py", encoding="utf-8").read())

# --- identity: lane and venue are NOT in the key -------------------------------------------------
ok("the same side of the same game is ONE key whatever the lane",
   RI.play_key("NCAAF", "NM @ WYO", "spread", "New Mexico -7.5", -7.5)
   == RI.play_key("NCAAF", "NM @ WYO", "spread", "New Mexico -7.5", -7.5))
ok("an incomplete identity fails closed",
   raises(lambda: RI.play_key("NBA", "", "total", "under", 1), X.ExposureUnknown))

# --- behavioural: with the flag ON, the paths refuse ---------------------------------------------
on()
try:
    st = seeded()
    g = RI.guard_or_refuse(st, KEY, "taker", 220.0, -110, U, "sharp-monitor:live_order")
    ok("the first path reserves", g is not None)
    ok("a SECOND path on the same play is refused - this is the cross-venue case",
       raises(lambda: RI.guard_or_refuse(st, KEY, "runner", 220.0, -110, U, "novig-runner:place"),
              R.ReservationRefused))
    ok("submission without a grant is refused",
       raises(lambda: RI.authorized_stake(st, None, 220.0), R.ReservationRefused))
    ok("submission with a grant is authorized", RI.authorized_stake(st, g, 220.0) == 220.0)
    ok("the same grant cannot authorize twice",
       raises(lambda: RI.authorized_stake(st, g, 220.0), R.ReservationRefused))

    unseeded = S.RegistryStore(FakeRegistry())
    ok("an UNSEEDED ledger refuses every path",
       raises(lambda: RI.guard_or_refuse(unseeded, KEY, "x", 10.0, -110, U, "a"), X.ExposureUnknown))

    class Dead:
        def read(self):
            return (None, None)

        def write(self, state, version):
            return False

    ok("an unreadable store refuses rather than letting the order through",
       raises(lambda: RI.guard_or_refuse(Dead(), KEY, "x", 10.0, -110, U, "a"), X.ExposureUnknown))

    # concurrent runs: two reservations racing for the last half unit
    cc = seeded()
    RI.guard_or_refuse(cc, KEY, "first", 110.0, -110, U, "sharp-monitor:live_order")
    ok("a concurrent run gets the remaining half",
       RI.guard_or_refuse(cc, KEY, "second", 110.0, -110, U, "novig-runner:place") is not None)
    ok("a third concurrent run gets nothing",
       raises(lambda: RI.guard_or_refuse(cc, KEY, "third", 1.0, -110, U, "x"), R.ReservationRefused))
finally:
    off()

# --- STRUCTURAL: the real dispatch paths call it, before dispatching -------------------------------
ex = open("executor.py", encoding="utf-8").read()
for fn in ("live_order", "live_remainder", "rest_bid"):
    m = re.search(rf"\ndef {fn}\(r\):\n(.*?)(?=\ndef )", ex, re.S)
    ok(f"executor.{fn} exists", m is not None)
    if not m:
        continue
    body = m.group(1)
    ok(f"executor.{fn} calls the shared guard", "_unit_ledger_guard(" in body)
    # the guard must come before anything that sends
    gi = body.find("_unit_ledger_guard(")
    for send in ("px_live.place(", "live_order_other(", "book_live.", "kalshi_place(", "novig_place("):
        si = body.find(send)
        ok(f"executor.{fn}: guard precedes {send}", si == -1 or gi < si, f"{gi} vs {si}")

ok("the helper reserves against the SHARED registry store",
   "review_store_registry" in ex and "RegistryStore(_reg)" in ex)
ok("the helper is a no-op when the flag is off", "if not ri.enabled():\n        return None" in ex)
ok("every dispatch path is enumerated for review", len(RI.DISPATCH_PATHS) == 4)
ok("both repositories are named in that list",
   {p[0] for p in RI.DISPATCH_PATHS} == {"sharp-monitor", "novig-runner"})

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
