#!/usr/bin/env python3
"""Kalshi open-order watch (Peter, Nov 23). Offline: the venue is stubbed. Proves it is read-only, reads EVERY page,
fails closed on any incomplete read, and flags each unsafe case."""
import ast
import re
import os
import sys
from datetime import datetime, timedelta, timezone

import kalshi_open_orders as k

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "kalshi_open_orders.py")).read()
tree = ast.parse(SRC)
strs = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
calls = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(tree) if isinstance(n, ast.Call)}
ok("READ-ONLY: no POST/PUT/PATCH/DELETE string anywhere", not {"POST", "PUT", "PATCH", "DELETE"} & set(strs))
ok("READ-ONLY: never calls a place or cancel function", not any(re.search(r"(^|_)place|cancel", c) for c in calls), calls)
ok("lists the whole account, not registry ids", '"/portfolio/orders"' in SRC and '"status": "resting"' in SRC)


def pages(*ps):
    it = iter(ps)

    def call(method, path, params=None):
        assert method == "GET"
        return next(it)
    return call


o, why = k.list_resting(pages((200, {"orders": [{"order_id": "a"}], "cursor": "c1"}),
                              (200, {"orders": [{"order_id": "b"}], "cursor": ""})))
ok("every page is read", [x["order_id"] for x in o] == ["a", "b"] and why is None)
ok("an empty account is a complete read of zero", k.list_resting(pages((200, {"orders": [], "cursor": ""}))) == ([], None))
ok("HTTP error: UNKNOWN, not zero", k.list_resting(pages((500, {})))[0] is None)
ok("missing 'orders' field: UNKNOWN, not zero", k.list_resting(pages((200, {"cursor": ""})))[0] is None)


def boom(*a, **kw):
    raise OSError("down")


ok("call failure: UNKNOWN, not zero", k.list_resting(boom)[0] is None)
endless = lambda m, p, params=None: (200, {"orders": [{"order_id": "x"}], "cursor": "again"})  # noqa: E731
ok("paging that never ends: UNKNOWN, not a partial list", k.list_resting(endless)[0] is None)

NOW = datetime(2026, 11, 23, 23, 0, tzinfo=timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
START = NOW + timedelta(hours=2)
ours = {"bot1": START, "bot2": NOW + timedelta(minutes=20), "bot3": START}
orders = [
    {"order_id": "bot1", "status": "resting", "expiration_time": iso(START - timedelta(minutes=30))},   # safe
    {"order_id": "bot2", "status": "resting", "expiration_time": iso(NOW + timedelta(minutes=5))},     # within 30 of start
    {"order_id": "bot3", "status": "resting", "expiration_time": iso(START + timedelta(minutes=10))},  # late expiry
    {"order_id": "x1", "status": "resting", "expiration_time": iso(NOW - timedelta(minutes=10))},      # expiry ignored
    {"order_id": "x2", "status": "resting"},                                                            # no expiry
    {"order_id": "x3", "status": "resting", "expiration_time": iso(NOW + timedelta(hours=5))},        # not ours, has expiry
    {"order_id": "x4", "status": "canceled"},
]
got = {b[1]["order_id"]: b[0] for b in k.classify(orders, ours, NOW)}
ok("a bot bid set to expire at start-30 is safe", "bot1" not in got)
ok("a bot bid still open within 30 min of start is flagged", got.get("bot2") == "NEAR/PAST START", got)
ok("a bot bid whose venue expiry is after start-30 is flagged", got.get("bot3") == "LATE EXPIRY", got)
ok("an order still resting past its own expiry is flagged", got.get("x1") == "EXPIRY IGNORED", got)
ok("an order with no venue expiry is flagged", got.get("x2") == "NO EXPIRY", got)
ok("an unrecorded order with a future expiry is counted, not alerted", "x3" not in got)
ok("a cancelled order is not open", "x4" not in got)
ok("a bot bid past its game start is flagged", k.classify([{"order_id": "bot1", "status": "resting",
   "expiration_time": iso(NOW + timedelta(hours=1))}], {"bot1": NOW - timedelta(minutes=5)}, NOW)[0][0] in
   ("NEAR/PAST START", "LATE EXPIRY"))

M = SRC.split("def main(")[1]
ok("alerts go to Telegram AND ntfy through the shared sender", "ex.tg_push(" in M)
ok("an incomplete read alerts and fails the job", "if problems or send:" in M and "return 1 if problems else 0" in M)
ok("delivery counts are printed", 'notifications (counts only): ' in M)
WF = open(os.path.join(HERE, ".github", "workflows", "kalshi-open-orders.yml")).read()
ok("workflow: read-only, scheduled after every executor run, this test before the key",
   "contents: read" in WF and 'workflows: ["executor-dry-run"]' in WF and "schedule:" in WF
   and WF.index("test_kalshi_open_orders.py") < WF.index("KALSHI_PRIVATE_KEY"))

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
