#!/usr/bin/env python3
"""Step 3 (Peter, Nov 12): manual holds served by the private registry, with Gmail as the fallback
and a refusal when NEITHER can prove a complete window.

The defect this closes predates the switch. read_manual() computed `partial` - a failed SEARCH, a
failed FETCH, an unparseable note - and discarded it, and main() caught any exception with
LOG.append("manual-bet notes unreadable"). Both left MANUAL_HELD EMPTY, and an empty MANUAL_HELD
reads exactly like "Peter has no manual bets". A single failed Gmail search therefore permitted a
duplicate of a bet already placed on a book the bot cannot read.

No order is placed, nothing is submitted, no historical order is replayed.
"""
import sys

import executor as ex
import registry as rg

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


NOTE = {"sport": "NBA", "game": "Boston @ Miami", "bet": "Under 215.5 (-110)", "book": "Hard Rock"}

_o = (rg.enabled, rg.manual_complete, rg.manual_notes, ex.read_manual, ex.imap_open)


def reset():
    ex.MANUAL.update(ok=None, src="")
    ex.MANUAL_HELD.clear()
    ex.LOG.clear()
    ex.GUARD.update(ok=None, why="")


class NoDial:
    """Any use at all is a failure: the store path must not touch Gmail."""

    def __getattr__(self, _n):
        raise AssertionError("Gmail was dialled when the store could answer")


print("1. STORE answers: holds come from the registry and Gmail is never touched")
reset()
rg.enabled = lambda: True
rg.manual_complete = lambda: True
rg.manual_notes = lambda: [NOTE]
ok = ex.manual_holds(NoDial())
check("resolved ok", ok is True)
check("the source is the store", ex.MANUAL["src"] == "store")
check("the hold is applied", len(ex.MANUAL_HELD) >= 1)
check("and it says so in the log", any("manual holds: store" in l for l in ex.LOG))

print("\n2. STORE cannot prove completeness -> Gmail fallback (Gmail is always complete)")
reset()
rg.manual_complete = lambda: False
called = {"n": 0}


def fake_read(M):
    called["n"] += 1
    ex._apply_manual(NOTE, ex.MANUAL_HELD)
    return True


ex.read_manual = fake_read
check("resolved ok via Gmail", ex.manual_holds(object()) is True)
check("Gmail was used", called["n"] == 1)
check("the source is gmail", ex.MANUAL["src"] == "gmail")

print("\n3. STORE UNREADABLE is not an empty window - it falls back, it does not proceed empty")
reset()
rg.manual_complete = lambda: True
rg.manual_notes = lambda: None          # unreadable
called["n"] = 0
check("resolved via Gmail, not via an empty store", ex.manual_holds(object()) is True)
check("Gmail was used", called["n"] == 1)
check("holds are present", len(ex.MANUAL_HELD) >= 1)

print("\n4. Gmail window PARTIAL -> refuse. A gap is not an absence of holds.")
reset()
rg.manual_complete = lambda: False
ex.read_manual = lambda M: False        # a failed SEARCH/FETCH: window not fully read
check("resolution fails", ex.manual_holds(object()) is False)
check("MANUAL ok is False", ex.MANUAL["ok"] is False)
check("the log says it is refusing", any("PARTIAL" in l for l in ex.LOG))

print("\n5. BOTH unreadable -> refuse, and MANUAL_HELD is left empty rather than half-applied")
reset()
rg.manual_complete = lambda: (_ for _ in ()).throw(RuntimeError("store down"))


def boom(M):
    raise RuntimeError("gmail down")


ex.read_manual = boom
check("resolution fails", ex.manual_holds(object()) is False)
check("no stale holds survive", ex.MANUAL_HELD == {})
check("the log records both failures", any("UNREADABLE both ways" in l for l in ex.LOG))

print("\n6. live_guards REFUSES while manual holds are unavailable")
reset()
ex.MANUAL.update(ok=False, src="none")
_bo, _io = ex.bot_orders, ex.imap_open
ex.bot_orders = lambda M: {}            # a perfectly good order registry
ex.imap_open = lambda: object()
ex.INTENT["open"] = {}
ok, why = ex.live_guards()
check("it refuses even though the order registry is fine", ok is False)
check("and the reason names the manual notes", "manual bet notes" in why)
check("and explains the assumption it refuses to make", "no manual" in why)

print("\n   and ALLOWS when they resolved")
reset()
ex.MANUAL.update(ok=True, src="store")
ok, why = ex.live_guards()
check("a resolved window does not block", ok is True)
check("no refusal reason", not why)

ex.bot_orders, ex.imap_open = _bo, _io
rg.enabled, rg.manual_complete, rg.manual_notes, ex.read_manual, ex.imap_open = _o
reset()

print()
if fails:
    print(f"FAIL  test_manual_authoritative.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
