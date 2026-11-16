"""Synthetic tests for pmus_activity.pmus_verdict. No network, no secrets."""
import sys
import pmus_activity as pa
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
V = pa.pmus_verdict
check("filled quantity -> FILLED", V({"order": {"status": "ORDER_STATE_FILLED", "filledQuantity": "5"}}) == "FILLED")
check("an execution with quantity -> FILLED", V({"order": {"status": "X", "executions": [{"quantity": 2}]}}) == "FILLED")
check("cancelled with nothing filled -> CANCELLED", V({"order": {"status": "ORDER_STATE_CANCELED", "filledQuantity": 0}}) == "CANCELLED")
check("expired with nothing filled -> CANCELLED", V({"order": {"status": "EXPIRED"}}) == "CANCELLED")
check("still open -> OPEN, never UNFILLED", V({"order": {"status": "ORDER_STATE_OPEN"}}) == "OPEN")
check("'filled' status with no quantity is contradictory -> UNKNOWN", V({"order": {"status": "FILLED"}}) == "UNKNOWN")
check("empty / missing record -> UNKNOWN", V({}) == "UNKNOWN" and V(None) == "UNKNOWN")
check("a zero-quantity execution is not a fill", V({"order": {"status": "ORDER_STATE_CANCELED", "executions": [{"quantity": 0}]}}) == "CANCELLED")
src = open("pmus_activity.py").read()
body = src[src.index("def registry_unknowns"):src.index("def main")]
check("the new mode only reads: no POST, no cancel path", "POST" not in body and "cancel" not in body.lower().replace("cancelled", ""))
check("the new mode prints no order id", "{oid}" not in body.split("print(")[1] if "print(" in body else True)
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_pmus_verdict: all passed")
