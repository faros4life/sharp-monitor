"""PERF brackets must not nest or share a label, or the report lies about itself.

Nov 11: live_guards() wrapped bot_orders() in perf("registry read (Gmail IMAP)"), and the
migration added a bracket with that IDENTICAL label inside bot_orders(). PERF sums per label, so
the same seconds were counted twice and n showed x2 - which read as "bot_orders runs twice per
run". It does not: GUARD caches it, once per run. The inflated label also inflated the denominator
every other percentage in the report was computed against, so one duplicated label corrupted the
whole table and sent a performance investigation after a defect that did not exist.
"""
import ast
import os
import re
from collections import Counter

CHECKS = []
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()

labels = re.findall(r'perf\("([^"]+)"', src)
dups = sorted(l for l, c in Counter(labels).items() if c > 1)
assert not dups, f"duplicate perf labels double-count their own seconds: {dups}"
CHECKS.append(("no perf label is used twice", len(labels), len(set(labels))))

# No perf bracket may enclose a call to a function that has brackets of its own.
tree = ast.parse(src)
fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
bracketed = {name for name, fn in fns.items()
             if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "perf"
                    for n in ast.walk(fn))}
CHECKS.append(("functions carrying their own brackets", len(bracketed) > 0, True))

nested = []
for name, fn in fns.items():
    for node in ast.walk(fn):
        if not isinstance(node, ast.With):
            continue
        if not any(isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Name)
                   and i.context_expr.func.id == "perf" for i in node.items):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id in bracketed and inner.func.id != name):
                nested.append((name, inner.func.id, inner.lineno))
# A bracket MAY enclose a self-bracketing call, but only if it is declared rollup=True, which
# keeps its superset seconds out of the percentage denominator.
undeclared = []
for name, callee, lineno in nested:
    line = src.split("\n")[lineno - 1]
    block = src.split("\n")[max(0, lineno - 12):lineno]
    if not any("rollup=True" in b for b in block):
        undeclared.append((name, callee, lineno))
assert not undeclared, ("a perf bracket encloses a self-bracketing call without rollup=True, so "
                        f"those seconds are counted twice: {undeclared}")
CHECKS.append(("every enclosing bracket is declared a rollup", undeclared, []))

# rollups must be excluded from the denominator, and reported as such.
import importlib
ex = importlib.import_module("executor")
ex.PERF["t"].clear(); ex.PERF["n"].clear(); ex.PERF["roll"] = set()
import time as _t
with ex.perf("outer", rollup=True):
    with ex.perf("inner"):
        _t.sleep(0.02)
_r = ex.perf_report()
rep = _r if isinstance(_r, str) else "\n".join(_r)
assert "(rollup)" in rep, rep
assert "MEASURED TOTAL" in rep, rep
# the denominator is the inner only, so inner must read 100%
assert "100.0%" in rep, rep
CHECKS.append(("a rollup is shown but not counted", True, True))

print(f"PASS  test_perf_labels.py  {len(CHECKS)} checks")
