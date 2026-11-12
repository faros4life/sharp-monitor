#!/usr/bin/env python3
"""Lane play-key prefixes cannot leave a duplicate guard blind (Peter, Nov 12 - money).

R1 placed the SAME NCAAF under three times this morning: ebe82a72, 510a30b6, adade61d, one key,
one stake each. Only one filled, and only because order 1 had taken the liquidity at -117. Two
independent guards were blind, for two different reasons:

  1. LIVEKEYS stored row["key"] = play_key ("r1|NCAAF|..."); the guard tests derive_key(p), which
     carries NO lane prefix. The exact check could never match.
  2. same_bet / opp_bet stripped only ("board|", "rule|"), so an "r1|" key split into 5 fields,
     failed `len(a) != 4` and returned False on every comparison. lane2 was missing too.

opp_bet being blind is worse than the duplicate: a lane could take the OTHER side of a game it
already held - two vigs for a guaranteed loss.

READ-ONLY and offline. No network, no venues, NO ORDERS.
"""
import ast
import os
import re
import sys

import executor as ex

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()

print("1. EVERY lane that stamps a play_key is registered in LANE_PREFIXES")
# this is the check that makes the defect un-repeatable: a new lane with an unregistered prefix
# fails here instead of duplicating a live bet.
used = sorted(set(re.findall(r'play_key\s*=\s*"([a-z0-9_]+)\|"', src)))
print(f"     lanes found in the source: {used}")
ck("at least the four known lanes are present", len(used) >= 4, True)
for pre in used:
    ck(f"{pre}| is in LANE_PREFIXES", pre + "|" in ex.LANE_PREFIXES, True)
ck("no registered prefix is unused (stale entry)",
   sorted(p.rstrip("|") for p in ex.LANE_PREFIXES) == used, True)

print("\n2. lane_strip removes every registered prefix and nothing else")
BARE = "NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"
for pre in ex.LANE_PREFIXES:
    ck(f"strips {pre!r}", ex.lane_strip(pre + BARE), BARE)
ck("leaves an unprefixed key alone", ex.lane_strip(BARE), BARE)
ck("does not strip a league that looks like a prefix", ex.lane_strip("NBA|x|total|UNDER"),
   "NBA|x|total|UNDER")
ck("handles None", ex.lane_strip(None), "")

print("\n3. the exact LIVEKEYS check now matches across the prefix boundary")
# the guard holds derive_key(p) (bare); the registry row holds play_key (prefixed)
for pre in ex.LANE_PREFIXES:
    live = {pre + BARE, ex.lane_strip(pre + BARE)}      # what bot_orders() now stores
    ck(f"bare key hits LIVEKEYS stored from {pre!r}", BARE in live, True)

print("\n4. same_bet and opp_bet see through the prefix")
for pre in ex.LANE_PREFIXES:
    ck(f"same_bet({pre!r} vs bare)", ex.same_bet(BARE, pre + BARE), True)
ck("same_bet still rejects a different bet",
   ex.same_bet(BARE, "r1|NCAAF|Other A @ Other B|total|UNDER"), False)
OPP = "NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|OVER"
for pre in ex.LANE_PREFIXES:
    ck(f"opp_bet sees the other side through {pre!r}", ex.opp_bet(OPP, pre + BARE), True)
ck("opp_bet does not flag the SAME side", ex.opp_bet(BARE, "r1|" + BARE), False)

print("\n5. the source itself no longer hard-codes a prefix list in a comparison")
tree = ast.parse(src)
# ast.unparse strips COMMENTS but keeps DOCSTRINGS, and the first version of this check matched
# lane_strip's own docstring describing the bug. Drop docstrings as well, so the assertion can
# only see executable code.
for node in ast.walk(tree):
    body = getattr(node, "body", None)
    if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
            and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
code = ast.unparse(tree)
ck("no prefix tuple left in any startswith comparison",
   any("board|" in ast.unparse(n) for n in ast.walk(tree)
       if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "startswith"), False)
ck("LIVEKEYS stores the stripped form too", "LIVEKEYS.add(lane_strip(" in code, True)

print("\n6. the Novig submission hold is in force and is a single chokepoint")
import book_live as bl                                                   # noqa: E402
ck("EXEC_NOVIG_SUBMIT defaults to paused", bl.NOVIG_SUBMIT, False)
res = bl.novig_place("some-outcome-id", 0.50, 200, "test")
ck("a live submission is refused while paused", res.get("status"), "refused")
ck("the refusal says why", "paused" in (res.get("reason") or ""), True)
res_rest = bl.novig_place("some-outcome-id", 0.50, 200, "test", ttl_ms=600000)
ck("a RESTING bid is refused too (same chokepoint)", res_rest.get("status"), "refused")
blsrc = open(os.path.join(HERE, "book_live.py")).read()
bl_code = ast.unparse(ast.parse(blsrc))
ck("reads are NOT gated - novig_results has no submit check",
   "NOVIG_SUBMIT" in bl_code.split("def novig_results")[1][:600], False)
ck("the hold is checked before any order inputs are built",
   bl_code.index("NOVIG_PAUSE_WHY") < bl_code.index("bad Novig order inputs"), True)

print("\n" + "=" * 60)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
