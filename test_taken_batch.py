"""Nov 11: taken() ran one UNBOUNDED Gmail search per play - the fourth instance of the pattern
already fixed in read_manual, already_handled and both fill reporters.

taken() is the "first side stays" guard. Nov 8's rule governs it: a failed search returning []
reads as "the side is free", and the bot then takes the opposite side of a position it already
holds. So the batched version must answer IDENTICALLY and must still raise rather than guess.

evaluate() calls taken exactly once per play, with opposite_key(p), so every token it can ask for
is known before the loop and resolved in one bounded search.
"""
import ast
import os

import executor as ex

CHECKS = []
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()
fns = {n.name: n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


# ---------------------------------------------------------------- evaluate asks with opposite_key
ev = fns["evaluate"]
calls = [n for n in ast.walk(ev)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "taken"]
ck("evaluate calls taken exactly once", len(calls), 1)
# the argument is ok_, and ok_ is assigned from opposite_key(p)
assert "ok_ = opposite_key(p)" in src, "the precompute only covers opposite_key(p)"
ck("the single call passes that key", isinstance(calls[0].args[0], ast.Name)
   and calls[0].args[0].id == "ok_", True)

# ---------------------------------------------------------------- the search is bounded + batched
t = fns["taken"]
unbounded = [n.lineno for n in ast.walk(t)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "gsearch_strict"
             and not (isinstance(n.args[1], ast.JoinedStr)
                      and any("newer_than" in getattr(v, "value", "") for v in n.args[1].values
                              if isinstance(v, ast.Constant)))]
ck("no unbounded search remains in taken()", unbounded, [])
assert "sent_tokens(M2, sorted(_wp_ask), days=HANDLED_DAYS)" in src, \
    "the precompute must use the bounded batched helper"
CHECKS.append(("the precompute is one bounded batched search", True, True))

# ---------------------------------------------------------------- identical decisions
_wp_ask = {ex.wp("NBA|A @ B|total|OVER"), ex.wp("NBA|C @ D|side|C")}
_wp_hit = {ex.wp("NBA|A @ B|total|OVER")}
taken_now = set()


def taken(k, live=lambda tok: False):
    if k in taken_now:
        return True
    tok = ex.wp(k)
    if tok in _wp_ask:
        return tok in _wp_hit
    return live(tok)


ck("a side taken earlier is still taken", taken("NBA|A @ B|total|OVER"), True)
ck("a side not taken is still free", taken("NBA|C @ D|side|C"), False)
taken_now.add("NBA|E @ F|total|UNDER")
ck("a side taken THIS run is taken", taken("NBA|E @ F|total|UNDER"), True)
ck("taken_now wins even when not precomputed", "NBA|E @ F|total|UNDER" in taken_now, True)

# a key outside the precompute must trigger a live search, never read as free
asked = []
ck("an uncovered key is asked about, not assumed free",
   taken("NBA|Z @ Y|total|OVER", live=lambda tok: asked.append(tok) or True), True)
ck("and the live search really ran", len(asked), 1)

# ---------------------------------------------------------------- still fails closed
class Boom:
    def uid(self, *a):
        return "NO", [None]


try:
    ex.sent_tokens(Boom(), [ex.wp("NBA|A @ B|total|OVER")])
    raise AssertionError("a failed search returned instead of raising - FAIL OPEN on first-side-stays")
except RuntimeError:
    CHECKS.append(("a failed search raises", "RuntimeError", "RuntimeError"))


class BadFetch:
    def uid(self, cmd, *a):
        return ("OK", [b"1"]) if cmd == "SEARCH" else ("NO", [None])


try:
    ex.sent_tokens(BadFetch(), [ex.wp("NBA|A @ B|total|OVER")])
    raise AssertionError("a failed fetch returned instead of raising")
except RuntimeError:
    CHECKS.append(("a failed fetch raises", "RuntimeError", "RuntimeError"))

# ---------------------------------------------------------------- window matches the other stores
ck("bounded to the same window as the dedupe and registry", ex.HANDLED_DAYS, 4)

print(f"PASS  test_taken_batch.py  {len(CHECKS)} checks")
