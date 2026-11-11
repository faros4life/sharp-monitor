"""Nov 11 (Peter): the 4-minute in-run positions polling loop is replaced.

It slept 60s up to four times hoping a venue recovered and pushed the escalation only at the
~3-minute mark - up to 240s PER PASS (measured 138s/175s in run 43070374073), and Peter was told
last. Now: one parallel attempt, one parallel retry after 5s, then stop; escalate immediately.

The safety requirements this file pins, in Peter's words:
  "Block ALL new live orders if any venue's exposure is unverifiable."
  "Never assume missing exposure is zero."
  "Send an immediate ntfy alert identifying the affected venue."
"""
import ast
import os
import re

CHECKS = []
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
tree = ast.parse(src)
fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
main = fns["main"]


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


# ---------------------------------------------------------------- the loop is gone
sleeps = [int(n.args[0].value) for n in ast.walk(main)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
          and n.func.attr == "sleep" and n.args and isinstance(n.args[0], ast.Constant)
          and isinstance(n.args[0].value, (int, float))]
ck("no 60-second sleep remains in main", [x for x in sleeps if x >= 60], [])
ck("only the 5s retry settle remains", sorted(sleeps), [5])

# No loop may re-read positions after the retry: the retry functions must be called in exactly
# the two places (first attempt, retry), never inside a range() loop.
for fname in ("novig_positions",):
    in_loop = []
    for node in ast.walk(main):
        if not isinstance(node, (ast.For, ast.While)):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == fname):
                in_loop.append(inner.lineno)
    ck(f"{fname} is never called inside a loop", in_loop, [])

# ---------------------------------------------------------------- ALL live orders blocked
m = re.search(r'if r\["verdict"\] == "WOULD PLACE" and blind and \(r\.get\("live"\) or \{\}\)\.get\("go"\):'
              r'(?:.|\n){0,400}?verdict="HELD"', src)
assert m, "the per-play gate that HOLDS every live-eligible play when blind is missing"
CHECKS.append(("every live-eligible play is HELD when any venue is blind", True, True))
# and it is not narrowed to one lane or source
gate = m.group(0)
for narrowing in ('source") == "rules"', 'phase1(', 'lane ==', '"board"', '"r1"'):
    assert narrowing not in gate, f"the blind hold must not be narrowed by {narrowing!r}"
CHECKS.append(("the hold is not narrowed to a lane or source", True, True))

# ---------------------------------------------------------------- venue-named alert
# Nov 11 (Peter: "if it happens 5 times in a row then telegram me"): the summary is no longer
# unconditional. A one-run blip is silent - the run placed nothing, which is the safe outcome -
# and the push fires at BLIND_STREAK_AT consecutive runs. What must NOT change: a HELD play still
# pushes immediately, and the alert still names the venue and states the global block.
i = src.index("if blind:")
blk = src[i:src.index("px_live.LIVE", i)]
assert "POSITIONS UNREADABLE" in blk, "a venue-named alert must still be sent"
assert "', '.join(blind)" in blk, "the alert must name the affected venue(s)"
assert "NO new live orders this run on ANY venue" in blk, \
    "the alert must say orders are blocked on every venue, not just the blind one"
CHECKS.append(("alert names the venue and states the global block", True, True))
assert "if p1 or streak is None or streak % BLIND_STREAK_AT == 0:" in blk, \
    "the summary must push on a held play, an uncountable streak, or the streak threshold"
CHECKS.append(("a held play and an uncountable streak both still push immediately", True, True))

# exactly one push from the blind block itself: the per-play HELD path sends its own, deduped
ck("one push from the blind block (no per-play duplicate)", blk.count("push("), 1)
assert "held_tok" in src, "the per-play HELD push must stay deduped on held_tok"
CHECKS.append(("the per-play HELD push is still deduped", True, True))

# ---------------------------------------------------------------- missing exposure is never zero
# `blind` is derived from None results, and None must never be coerced to an empty container
# before that derivation.
d = src[src.index("blind = ("):src.index("blind = (") + 220]
assert "pos is None" in d and "v is None" in d, f"blind must be derived from None results: {d}"
assert "or {}" not in d and "or []" not in d, \
    f"an unreadable venue must not be defaulted to empty before the blind check: {d}"
CHECKS.append(("an unreadable venue is None, never empty", True, True))

print(f"PASS  test_blind_positions.py  {len(CHECKS)} checks")
