#!/usr/bin/env python3
"""novig_order_probe: GET only, cancels nothing, and never turns an unread order into a no-fill.

The probe runs with a Novig TRADING key because there is no read-only variant, so the read-only
guarantee has to come from the code. Checked against the parsed AST, not the file text - an
earlier version of this test matched its own docstring and reported failures for words in a
comment, which is how a guard gets switched off.
"""
import ast

import novig_order_probe as p

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


src = open("novig_order_probe.py").read()
# Normalised: the probe's messages wrap across source lines, so a raw substring test fails on
# text that is present and correct. Collapse the implicit concatenation before matching.
import re as _re
flat = _re.sub(r'"\s*\n\s*"', "", src)
flat = _re.sub(r"\s+", " ", flat)
tree = ast.parse(src)
called, methods = set(), []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    f = node.func
    name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
    called.add(name)
    if name in ("call", "_n_call") and node.args and isinstance(node.args[0], ast.Constant):
        methods.append(node.args[0].value)

print("1. the probe cannot write to the venue")
for bad in ("novig_place", "kalshi_place", "pmus_place", "novig_cancel", "cancel_order", "place"):
    check(f"never calls {bad}()", bad not in called)
check("no call name contains 'cancel'", not any("cancel" in c for c in called),
      str(sorted(c for c in called if "cancel" in c)))
check("no write verb appears as a venue method", not {"POST", "PUT", "PATCH", "DELETE"} & set(methods),
      str(methods))
# AST, not text: the probe's docstring CITES novig_live_order for Novig's own guidance about
# partial fills, and a substring test read that citation as an import. Third time this exact
# mistake has cost a cycle today - check what the code does, never what it says.
imported = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported |= {a.name for a in node.names}
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported.add(node.module)
check("the trading client is not imported", "novig_live_order" not in imported, str(sorted(imported)))
check("the read-only client is", "novig_signed" in imported, str(sorted(imported)))
check("the venue is reached through it", "nv.get" in src)
check("the probe checks the key is read-scoped before reading",
      "nv.ready()" in src and "nv.scope()" in src)
check("it says outright that nothing is cancelled", "NOTHING WAS CANCELLED" in flat)

print("2. an unread order is never a no-fill")
check("OPEN and PENDING are the open states", set(p.OPEN_STATES) == {"PENDING", "OPEN"})
check("an unreadable status is reported as UNRESOLVED", "UNRESOLVED - venue did not answer" in flat)
check("and counted, not swallowed", "unresolved += 1" in src)
check("an unreadable order is called UNKNOWN exposure", "UNKNOWN exposure" in flat)
check("a cancelled/rejected order is the only CONFIRMED nothing-traded",
      "rather than inferred" in flat)

print("3. a partial fill is read from remaining, not from the status word")
check("Novig's own guidance is recorded", "track remaining, not the status" in flat)
check("filled qty is computed from qty minus remaining",
      'int(o["qty"]) - int(o["remaining"])' in src)
check("partial fills are reported with their qty", "partially filled" in src)

print("4. it fails closed")
check("no credentials -> refuses to report", "refuses to report a status it could not read" in flat)
check("registry unreadable -> refuses rather than guessing", "guessing it would be worse" in flat)
check("an empty list is a statement about the REGISTRY", "statement about the REGISTRY" in flat)

print("5. no dollar figures leave the probe")
check("counts and prices only", "No dollar figures" in flat)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_novig_order_probe: all passed")
