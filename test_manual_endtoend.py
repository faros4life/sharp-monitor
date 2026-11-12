#!/usr/bin/env python3
"""Phase 1 end-to-end: read_manual() still behaves EXACTLY as before, and the mirror catches
divergence (Peter, Nov 12).

test_manual_mirror.py tests the store and the claim. This tests the thing that actually matters on a
live run: that adding the mirror changed nothing about the Gmail answer, and that when the snapshot
does NOT reproduce Gmail the claim is withdrawn rather than left standing.

Gmail is authoritative in Phase 1, so every case here asserts the Gmail-derived MANUAL_HELD first.
"""
import json
import os
from datetime import datetime, timedelta, timezone

os.environ["REGISTRY_TOKEN"] = ""
import executor as ex
import registry as R

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


N1 = {"sport": "NBA", "game": "Away @ Home", "bet": "Under 225.5 (-110)", "book": "Hard Rock"}
N2 = {"sport": "NBA", "game": "A @ B", "bet": "Over 210.5 (-105)", "book": "Hard Rock"}
# A correction: same game and side as N1, different number. Must OVERWRITE, not add a conflict.
N1C = {"sport": "NBA", "game": "Away @ Home", "bet": "Under 224.5 (-110)", "book": "Hard Rock"}


def mail(note, subject="Bets manual: tonight"):
    return (f"Subject: {subject}\r\nFrom: p@x\r\n\r\n"
            f"MANUAL: {json.dumps(note)}\r\n").encode()


class FakeIMAP:
    """SEARCH returns every uid; FETCH returns the mail. fail_fetch forces a mid-window gap."""

    def __init__(self, mails, search_ok=True, fail_fetch=()):
        self.mails = list(mails)
        self.search_ok = search_ok
        self.fail_fetch = set(fail_fetch)
        self.fetches = 0

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            if not self.search_ok:
                return "NO", [b""]
            return "OK", [b" ".join(str(i).encode() for i in range(len(self.mails)))]
        if cmd == "FETCH":
            i = int(a[0])
            self.fetches += 1
            if i in self.fail_fetch:
                return "NO", None
            return "OK", [(b"x", self.mails[i])]
        return "OK", [b""]


class Store:
    def __init__(self, data=None, writable=True, readable=True):
        self.data = data if data is not None else {"manual": [], "meta": {}}
        self.writable = writable
        self.readable = readable

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
            return True
        R._commit = _commit
        R.enabled = lambda: True
        return self


_orig = (R.load, R._commit, R.enabled)


def run(imap, store):
    """One read_manual() pass with a clean MANUAL_HELD and LOG, as a fresh process would have."""
    ex.MANUAL_HELD.clear()
    del ex.LOG[:]
    store.install()
    ex.read_manual(imap)
    return dict(ex.MANUAL_HELD), [l for l in ex.LOG if "manual" in l]


def replay(notes):
    h = {}
    for n in notes:
        ex._apply_manual(n, h)
    return h


print("The Gmail answer is unchanged, and the snapshot reproduces it")
st = Store()
held, log = run(FakeIMAP([mail(N1), mail(N2)]), st)
check("both notes produced their duplicate+conflict keys", held == replay([N1, N2]))
check("four keys, as before the mirror existed", len(held) == 4)
check("the snapshot holds both notes, in order", st.data["manual"] == [N1, N2])
check("the mirror logged AGREE", any("AGREE" in l for l in log))
check("the claim was asserted", st.data["meta"].get("man_complete_through"))

print("\nA correction OVERWRITES rather than stacking a phantom conflict")
st = Store()
held, log = run(FakeIMAP([mail(N1), mail(N1C)]), st)
check("still one duplicate key for that side", held["NBA|Away @ Home|total|UNDER"] == "duplicate")
check("and the opposite side is a conflict, not a duplicate",
      held["NBA|Away @ Home|total|OVER"] == "conflict")
check("snapshot replay matches Gmail exactly", replay(st.data["manual"]) == held)
check("AGREE", any("AGREE" in l for l in log))

print("\nA DELETED note propagates: the snapshot is replaced, never accumulated")
st = Store()
run(FakeIMAP([mail(N1), mail(N2)]), st)
check("two notes after the first pass", len(st.data["manual"]) == 2)
held, log = run(FakeIMAP([mail(N2)]), st)          # Peter deleted N1 from Gmail
check("the snapshot now holds ONE note", st.data["manual"] == [N2])
check("no phantom key survives from the deleted note",
      "NBA|Away @ Home|total|UNDER" not in held)
check("and the store still agrees with Gmail", replay(st.data["manual"]) == held)

print("\nA failed SEARCH invalidates the claim and never asserts one")
st = Store({"manual": [N1], "meta": {"man_complete_through": "2026-11-12",
                                     "man_complete_at": "2026-11-12T18:00:00Z"}})
held, log = run(FakeIMAP([mail(N1)], search_ok=False), st)
check("claim withdrawn", st.data["meta"]["man_complete_through"] == "")
check("the log says the window was partial", any("partial" in l for l in log))

print("\nA failed FETCH mid-window also invalidates: a gap is not a complete window")
st = Store()
held, log = run(FakeIMAP([mail(N1), mail(N2)], fail_fetch=[0]), st)
check("Gmail's own answer is just the readable note (pre-existing behaviour)",
      held == replay([N2]))
check("but the claim is NOT asserted", not st.data["meta"].get("man_complete_through"))
check("logged as partial", any("partial" in l for l in log))

print("\nAn unwritable store leaves Gmail untouched and claims nothing")
st = Store(writable=False)
held, log = run(FakeIMAP([mail(N1)]), st)
check("Gmail result still correct", held == replay([N1]))
check("no claim asserted", not st.data["meta"].get("man_complete_through"))

print("\nAn unreadable store cannot stop the Gmail path")
st = Store(readable=False)
held, log = run(FakeIMAP([mail(N1)]), st)
check("Gmail result still correct", held == replay([N1]))

print("\nWith no token the mirror does nothing at all")
R.load, R._commit, R.enabled = _orig
R.enabled = lambda: False
ex.MANUAL_HELD.clear()
del ex.LOG[:]
ex.read_manual(FakeIMAP([mail(N1)]))
check("Gmail result unchanged", dict(ex.MANUAL_HELD) == replay([N1]))
check("and nothing was logged about a mirror",
      not [l for l in ex.LOG if "manual mirror" in l])

R.load, R._commit, R.enabled = _orig

print()
if fails:
    print(f"FAIL  test_manual_endtoend.py  {len(fails)} failed: {fails}")
    raise SystemExit(1)
print("ALL PASS")
