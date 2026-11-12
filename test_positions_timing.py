#!/usr/bin/env python3
"""The position-read timing wrapper must measure without changing anything (Peter, Nov 12).

`positions read (first attempt)` reported 378.6s as ONE number while every per-call venue counter
came back under a second, so the bracket could not name the venue holding the run open. _timed_pos()
times each of the four reads end to end instead.

It sits directly in front of the live position reads, and those reads are what block a new order
when exposure cannot be verified. So the properties that matter are not the timings - they are that
the wrapper returns the value untouched and lets an exception through, because a swallowed
exception would turn an unreadable venue into an apparently-readable one. That is fail-OPEN on
duplicate protection, and it is the only way this measurement could do harm.
"""
import sys
import time

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


print("It returns exactly what the read returned")
sentinel = {"novig": ["a", "b"]}
check("the value passes through unchanged", ex._timed_pos("v1", lambda: sentinel)() is sentinel)
check("None passes through as None, not as empty",
      ex._timed_pos("v2", lambda: None)() is None)

print("\nIt records the WHOLE function, including waits")
ex.POSW.clear()
ex._timed_pos("slow", lambda: time.sleep(0.25))()
check("a sleep inside the read is counted", ex.POSW.get("slow", 0) >= 0.24)

print("\nAn exception PROPAGATES - a swallowed one would fake a readable venue")
ex.POSW.clear()


def boom():
    raise RuntimeError("venue unreachable")


raised = False
try:
    ex._timed_pos("broken", boom)()
except RuntimeError:
    raised = True
check("the exception reaches the caller", raised)
check("and the attempt was still timed", "broken" in ex.POSW)

print("\nEach venue is recorded separately, so the slowest one is identifiable")
ex.POSW.clear()
for n, d in (("kalshi", 0.05), ("prophetx", 0.20), ("polymarket_us", 0.02)):
    ex._timed_pos(n, lambda d=d: time.sleep(d))()
check("three separate entries", len(ex.POSW) == 3)
check("the slowest is the slowest", max(ex.POSW, key=ex.POSW.get) == "prophetx")

print("\nThe ProphetX sub-timings exist and carry only seconds")
import positions
src = open("positions.py").read()
for step in ("px_login", "get_trades", "strike_map", "_walk", "put_strikes"):
    check(f"{step} is timed", f'_t["{step}"]' in src)
check("they are published as a seconds-only string",
      'WHY["prophetx_timing"]' in src and "{v:.1f}s" in src)
check("the executor prints only the count/second keys, not the exception text",
      '("prophetx_walk_s", "prophetx_timing")' in open("executor.py").read())

print()
if fails:
    print(f"FAIL  test_positions_timing.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
