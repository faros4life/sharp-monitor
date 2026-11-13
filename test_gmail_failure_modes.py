#!/usr/bin/env python3
"""Gmail failure modes must refuse, never place (Peter, Nov 12).

MEASURED on run 43311690235: live_guards took 832.2s of a 1012-second pass, while bot_orders' own
brackets INSIDE it read 2.6s and 0.2s. The registry work was never the cost - the connection was.
IMAP4_SSL had no timeout, so a stalled socket waited on the TCP stack. Pass 2 of that same run died
with imaplib.IMAP4.abort: socket error: EOF.

The fix bounds the hang. These tests check the thing that actually matters about it: for every way
Gmail can fail - timeout, socket EOF, slow response, unreadable registry - the answer must be
REFUSE, and it must never be an empty result standing in for data that was not read.

No order is placed. Nothing is submitted. No historical order is replayed.
"""
import imaplib
import socket
import sys

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


print("The socket now has a bound, so a stall cannot run for fourteen minutes")
import inspect
src = inspect.getsource(ex.imap_open)
check("IMAP4_SSL is constructed with a timeout", "timeout=" in src)
check("the bound is configurable but defaulted", ex.IMAP_TIMEOUT_S > 0)
check("and it is well clear of measured work (<= 120s)", ex.IMAP_TIMEOUT_S <= 120)

print("\nEvery Gmail failure mode makes live_guards REFUSE")
_orig_open, _orig_bo, _orig_guard = ex.imap_open, ex.bot_orders, dict(ex.GUARD)

FAILURES = {
    "timeout":    socket.timeout("timed out"),
    "socket EOF": imaplib.IMAP4.abort("socket error: EOF"),
    "connection reset": ConnectionResetError("reset by peer"),
    "auth failure": imaplib.IMAP4.error("AUTHENTICATIONFAILED"),
}
for label, exc in FAILURES.items():
    ex.GUARD.update(ok=None, why="")

    def boom(_e=exc):
        raise _e
    ex.imap_open = boom
    ok, why = ex.live_guards()
    check(f"{label}: refuses", ok is False)
    check(f"{label}: and says so, rather than failing silently", bool(why))

print("\nAn unreadable registry refuses too - None is never read as 'no orders'")
ex.GUARD.update(ok=None, why="")
ex.imap_open = lambda: object()
ex.bot_orders = lambda M: None          # the documented fail-closed answer
ex.imap_close = lambda M: None
ok, why = ex.live_guards()
check("unreadable registry refuses", ok is False)
check("the reason names the registry", "registry" in why.lower())

print("\nA SLOW but successful read still succeeds - the bound must not break normal work")
ex.GUARD.update(ok=None, why="")
ex.bot_orders = lambda M: {}            # readable, no bot orders: a legitimate empty answer
ex.INTENT["open"] = {}
# Nov 12: live_guards now ALSO requires a complete manual-hold window, because an empty
# MANUAL_HELD used to be indistinguishable from "Peter has no manual bets". A readable order
# registry alone is no longer sufficient, so this case states the manual side explicitly.
ex.MANUAL.update(ok=True, src="store")
ok, why = ex.live_guards()
check("a readable registry with no bot orders is allowed", ok is True)
check("and no refusal reason is set", not why)

print("\nAnd manual holds are a REQUIREMENT, not an optional extra")
ex.GUARD.update(ok=None, why="")
ex.MANUAL.update(ok=False, src="none")
ok, why = ex.live_guards()
check("an unreadable manual-hold window refuses", ok is False)
check("even with a perfectly readable order registry", "manual bet notes" in why)
ex.MANUAL.update(ok=True, src="store")

print("\nAn UNRECONCILED intent still blocks, bound or not")
ex.GUARD.update(ok=None, why="")
ex.bot_orders = lambda M: {}
ex.INTENT["open"] = {"NBA|A @ B|total|UNDER": {"live_order": {"book": "novig", "asked_stake": 200.0},
                                               "decided_utc": "2026-11-12T20:00:00Z"}}
ok, why = ex.live_guards()
check("an open intent refuses", ok is False)
check("the reason names the unreconciled intent", "intent" in why.lower())
check("and tells Peter how to clear it", ex.INTENT_CLEAR_PREFIX in why)
ex.INTENT["open"] = {}

print("\nThe guard is computed ONCE per run and cached, so a failure cannot be retried into a pass")
ex.GUARD.update(ok=False, why="already refused this run")
calls = {"n": 0}


def counted():
    calls["n"] += 1
    raise AssertionError("must not reconnect once the guard has answered")


ex.imap_open = counted
ok, why = ex.live_guards()
check("the cached refusal is returned", ok is False)
check("and Gmail was not touched again", calls["n"] == 0)

ex.imap_open, ex.bot_orders = _orig_open, _orig_bo
ex.GUARD.update(**_orig_guard)


# ---------------------------------------------------------------------------- lazy connection
print("\nThe guard does not DIAL Gmail when the private store answers")
_dials = {"n": 0}
_real_open = ex.imap_open


class _FakeM:
    def uid(self, *a, **k):
        return "OK", [b""]


ex.imap_open = lambda: (_dials.__setitem__("n", _dials["n"] + 1), _FakeM())[1]
L = ex._LazyIMAP()
L.close()
check("an unused connection never dials", _dials["n"] == 0)
L2 = ex._LazyIMAP()
L2.uid("SEARCH")
check("the first caller that needs Gmail still gets it", _dials["n"] == 1)
check("and the proxy reports it opened", L2.opened is True)
L2.close()


def _boom():
    raise RuntimeError("gmail down")


ex.imap_open = _boom
raised = False
try:
    ex._LazyIMAP().uid("SEARCH")
except RuntimeError:
    raised = True
check("a failed open propagates on first use (fail-closed intact)", raised)
ex.imap_open = _real_open

print()
if fails:
    print(f"FAIL  test_gmail_failure_modes.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
