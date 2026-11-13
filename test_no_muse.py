#!/usr/bin/env python3
"""Muse cannot be reactivated by any configuration (Peter, Nov 13: permanently retired).

"Make sure no configuration setting can accidentally reactivate Muse or its veto. Keep Phase 1,
Board V3, and R1 operating exactly as they do today. Lane 2 stays paper-only."

Two vectors existed:
  1. EXEC_SOURCE=muse|both -> read_verdicts() and the Muse watchdog came back. Worse, EXEC_SOURCE=muse
     would also have made `SOURCE in ("rules", "both")` False and SILENTLY switched off the coded
     rules lane - Phase 1 with no plays at all.
  2. agree_rules.phase1(a, muse_agree) with muse_agree False -> the "no Muse AGREE" veto.

READ-ONLY and offline. No network, no venues, NO ORDERS.
"""
import ast
import importlib
import os
import re
import sys

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()

print("1. SOURCE is a constant - no environment variable can move it")
for val in ("muse", "both", "MUSE", "Both", "rules", "", "anything"):
    os.environ["EXEC_SOURCE"] = val
    import executor as ex
    importlib.reload(ex)
    ck(f"EXEC_SOURCE={val!r} -> SOURCE", ex.SOURCE, "rules")
os.environ.pop("EXEC_SOURCE", None)
import executor as ex                                                    # noqa: E402
importlib.reload(ex)
ck("unset -> SOURCE", ex.SOURCE, "rules")

print("\n2. executor.py no longer READS EXEC_SOURCE at all")
tree = ast.parse(src)
reads = [n for n in ast.walk(tree)
         if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value == "EXEC_SOURCE"]
ck("no EXEC_SOURCE string literal in the code", len(reads), 0)
ck("no other module reads it", [f for f in os.listdir(HERE)
                                if f.endswith(".py") and not f.startswith("test_")
                                and "EXEC_SOURCE" in open(os.path.join(HERE, f)).read()
                                and f != "executor.py"], [])

print("\n3. the Muse paths are unreachable with SOURCE pinned")
ck("verdict reads skipped", ex.SOURCE in ("muse", "both"), False)
ck("watchdog returns early", ex.SOURCE not in ("both",), True)
ck("the '[Muse] ' tag never applies", ex.SOURCE == "both", False)

print("\n4. ...and the coded RULES lane still runs (the silent-off door)")
ck("rule_plays still runs", ex.SOURCE in ("rules", "both"), True)

print("\n5. no ORDER path can pass the Muse veto: every phase1() call there passes True")
# Scope is the modules that can decide or place a live bet. Research scripts are excluded on
# purpose and checked separately below - novig_only_clv.py passes ar.decide(...)=="AGREE", which
# is the CODED RULES verdict replayed over history, not Muse, and it places nothing.
ORDER_PATHS = ("executor.py", "sharp_monitor.py", "book_live.py", "px_live.py", "agree_rules.py")
calls, bad = 0, []
for f in ORDER_PATHS:
    t = ast.parse(open(os.path.join(HERE, f)).read())
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "phase1" and len(n.args) >= 2:
            calls += 1
            a = n.args[1]
            if not (isinstance(a, ast.Constant) and a.value is True):
                bad.append(f"{f}: {ast.unparse(a)[:40]}")
ck("found phase1 call sites on the order path", calls >= 5, True)
ck("every one passes a literal True for muse_agree", bad, [])

# any OTHER caller must be unable to place an order at all
PLACERS = ("novig_place", "kalshi_place", "pmus_place", "rest_bid(", "live_order(", "px_live.place")
others = []
for f in sorted(os.listdir(HERE)):
    if not f.endswith(".py") or f.startswith("test_") or f in ORDER_PATHS:
        continue
    body = open(os.path.join(HERE, f)).read()
    if ".phase1(" not in body:
        continue
    t = ast.parse(body)
    code = ast.unparse(t)
    if any(pl in code for pl in PLACERS):
        others.append(f)
ck("no non-order-path phase1 caller can place a bet", others, [])

print("\n6. the other lanes are untouched by this change")
ck("Phase 1 unit", ex.LIVE_UNIT, 300.0)
ck("Board v3 unit", ex.BOARD_UNIT, 200.0)
ck("R1 unit", ex.R1_UNIT, 200.0)
ck("Lane 2 is still dry-run only",
   bool(re.search(r"Lane 2 is dry-run only", src)), True)
ck("lane prefixes unchanged", ex.LANE_PREFIXES, ("rule|", "board|", "r1|", "lane2|"))

print("\n7. nothing about execution, pricing, staking or resting moved")
ck("price cap", ex.CAP_LINE, -130)
ck("tolerance cents", ex.PX_TOL_CENTS, 2)
ck("tolerance books", ex.TOL_BOOKS, ("prophetx", "novig"))
ck("resting expiry minutes", ex.REST_BEFORE_MIN, 30)
ck("min order", ex.MIN_ORDER, 50.0)

print("\n" + "=" * 60)
print(f"PASSED {len(OK)}   FAILED {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
