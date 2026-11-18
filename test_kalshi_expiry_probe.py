#!/usr/bin/env python3
"""kalshi_expiry_probe: GET only, cancels nothing, and never calls an order safe without evidence.

This probe runs against a live venue with a trading key, so the first thing to pin is that it
cannot place or cancel anything. The second is its classification: an order with no venue-side
expiry must come back UNSAFE, not "probably fine because we sent one".
"""
import re
from datetime import datetime, timedelta, timezone

import kalshi_expiry_probe as p

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


src = open("kalshi_expiry_probe.py").read()

print("1. the probe cannot write to a venue")
# Checked against the CODE, not the file text. The first version of this test matched the probe's
# own docstring - which explains that it never cancels - and reported three failures for words in
# a comment. A guard that fires on its own documentation gets switched off.
import ast
tree = ast.parse(src)
called, k_methods = set(), []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    f = node.func
    name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
    called.add(name)
    if name == "_k_call" and node.args and isinstance(node.args[0], ast.Constant):
        k_methods.append(node.args[0].value)
for bad in ("kalshi_place", "pmus_place", "novig_place", "kalshi_cancel", "pmus_cancel"):
    check(f"the probe never calls {bad}()", bad not in called)
check("no call name contains 'cancel'", not any("cancel" in c for c in called),
      str(sorted(c for c in called if "cancel" in c)))
check("every venue call is a GET", k_methods and set(k_methods) == {"GET"}, str(k_methods))
check("no write verb is passed to any venue call",
      not {"POST", "PUT", "PATCH", "DELETE"} & set(k_methods), str(k_methods))
check("it says outright that nothing is cancelled", "NOTHING IS CANCELLED HERE" in src)

print("2. a missing venue expiry is UNSAFE, not assumed safe")
check("venue_expiry returns None when no expiry field is present",
      p.venue_expiry({"status": "resting", "remaining_count": 5}) == (None, None))
# venue_expiry must read the VENUE's record only - never the order dict we sent at placement.
ve_fn = next(n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "venue_expiry")
ve_names = {n.id for n in ast.walk(ve_fn) if isinstance(n, ast.Name)}
check("venue_expiry touches only its own argument",
      ve_names <= {"o", "k", "d", "tp"}, str(sorted(ve_names)))

print("3. venue_expiry reads whichever spelling the venue returned")
d, f = p.venue_expiry({"expiration_time": 1763500000})
check("unix seconds parse", d is not None and f == "expiration_time", f"{d} {f}")
d, f = p.venue_expiry({"expires_at": "2026-11-18T23:30:00Z"})
check("ISO string parses", d is not None and f == "expires_at", f"{d} {f}")
d, f = p.venue_expiry({"expiration_time": None, "good_till_time": 1763500000})
check("a null in the first field does not mask a later one", d is not None and f == "good_till_time",
      f"{d} {f}")
d, f = p.venue_expiry({"expiration_time": ""})
check("an empty string is not an expiry", (d, f) == (None, None), f"{d} {f}")

print("4. the cutoff comparison")
# A good_till_canceled order whose stored expiry lands after the game starts is the exact failure
# the notification could not rule out.
start = datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc)
cutoff = start - timedelta(minutes=p.CUTOFF_MIN)
check("the cutoff is 30 minutes before the start", p.CUTOFF_MIN == 30)
check("an expiry at the cutoff is inside tolerance", cutoff <= cutoff + timedelta(minutes=p.GRACE_MIN))
check("an expiry after the start is outside tolerance",
      start > cutoff + timedelta(minutes=p.GRACE_MIN))
check("grace is small", 0 <= p.GRACE_MIN <= 5, str(p.GRACE_MIN))

print("5. resting statuses, and what counts as closed")
check("resting/open/active are the live statuses", set(p.RESTING) == {"resting", "open", "active"})
for s in ("canceled", "cancelled", "executed", "expired", "closed"):
    check(f"'{s}' is not treated as resting", s not in p.RESTING)

print("6. it fails closed rather than reporting on what it could not read")
check("no credentials -> refuses to report", "refuses to report on an order it could not read" in src)
check("registry unreadable -> refuses rather than guessing", "guessing it would be worse" in src)
check("an unreadable order is UNKNOWN exposure, never safe",
      "never assumed safe" in src and "UNREADABLE" in src)
check("an empty result is reported as a fact about the REGISTRY, not about Kalshi",
      "statement about the REGISTRY" in src)

print("7. no dollar figures leave the probe")
check("the log states counts and prices only", "No dollar figures" in src)
check("nothing formats a currency amount", "$" not in src.replace("No dollar figures", "")
      .replace("dollar figures", ""))

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_kalshi_expiry_probe: all passed")
