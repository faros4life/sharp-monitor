#!/usr/bin/env python3
"""Nov 17: ledger rows write decided_utc (it sat inside a comment); journal rows carry start, alert price, latency."""
import ast
import sys

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


src = open("executor.py").read()
t = ast.parse(src)
fns = {n.name: n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)}


def keys(fn):
    return {k.value for d in ast.walk(fns[fn]) if isinstance(d, ast.Dict) for k in d.keys if isinstance(k, ast.Constant)}


check("ledger_row really writes decided_utc (not inside a comment)", "decided_utc" in keys("ledger_row"))
check("ledger_row still writes start_utc and latency_s", {"start_utc", "latency_s"} <= keys("ledger_row"))
check("journal_order writes start_utc, alert_price_after_fee, latency_s",
      {"start_utc", "alert_price_after_fee", "latency_s"} <= keys("journal_order"))
body = src[src.index("def journal_order"):src.index("def journal_order") + 6000]
check("the journal row is still built inside the never-raising try block", body.index("try:") < body.index('"alert_price_after_fee"'))
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
