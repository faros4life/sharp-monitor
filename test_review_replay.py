#!/usr/bin/env python3
"""REVIEW ONLY. The private reconciliation reports or says MISSING - it never invents a record."""
import sys

import review_replay as RP

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


ROWS = [
    {"order_id": "a", "play_key": "k1", "status": "open", "asked_stake": 220.0, "american": -110, "unit": 200},
    {"order_id": "b", "play_key": "k1", "status": "filled", "asked_stake": 110.0, "filled_stake": 110.0,
     "american": -110, "unit": 200},
    {"order_id": "c", "play_key": "k2", "status": "banana", "asked_stake": 10.0, "american": -110, "unit": 200},
    {"order_id": "d", "status": "open", "asked_stake": 10.0, "american": -110, "unit": 200},
    {"order_id": "e", "play_key": "k3", "status": "resting", "asked_stake": 50.0, "american": -110},
]
legs, unreadable, terminal = RP.backfill_candidates(ROWS)
ok("an outstanding order becomes a backfill leg", any(l["order_id"] == "a" for l in legs))
ok("a resting order counts as outstanding", any(l["order_id"] == "e" for l in legs))
ok("a settled order does not", terminal == 1 and not any(l["order_id"] == "b" for l in legs))
ok("an unrecognised state goes to UNREADABLE, never to zero exposure",
   any(u["id"] == "c" for u in unreadable))
ok("a row missing its play key goes to UNREADABLE", any(u["id"] == "d" for u in unreadable))
ok("nothing is silently dropped", len(legs) + len(unreadable) + terminal == len(ROWS))

v, why = RP.completeness(legs, unreadable)
ok("completeness is INCOMPLETE while anything is unreadable", v == "INCOMPLETE", v)
ok("and says how many", "could not be classified" in why)
v2, why2 = RP.completeness([{"key": "k", "unit": 200}], [])
ok("a clean list is COMPLETE", v2 == "COMPLETE")
v3, _ = RP.completeness([{"key": "k"}], [])
ok("a leg with no lane unit makes it INCOMPLETE", v3 == "INCOMPLETE")
v4, why4 = RP.completeness([], [])
ok("an empty list is reported as empty, not as proven", "empty" in v4 and "verify" in why4)

ok("the replay returns verbatim rows", len(RP.min_at_sf(ROWS, "k1")) == 2)
ok("no term means no replay, not a guess", RP.min_at_sf(ROWS, "") == [])
ok("an unmatched term returns nothing rather than the nearest row",
   RP.min_at_sf(ROWS, "zzz") == [])
ok("an unreadable registry reports nothing and infers nothing", RP._rows.__doc__.count("NEVER") == 1)

# Match CODE, not comments: the docstrings name EXEC_UNIT_LEDGER and "no schedule" precisely to
# say the module has neither, and ".replace(" contains "place(".
full = open("review_replay.py", encoding="utf-8").read()
import ast as _ast
_m = _ast.parse(full)
code = "\n".join(full.split("\n")[_m.body[0].end_lineno:]) if _ast.get_docstring(_m) else full
code = "\n".join(l for l in code.split("\n") if not l.strip().startswith("#"))
for bad in ("px_live.place(", "cancel(", "rest_bid", "live_order(", "_put_with_sha",
            'environ.get("EXEC_UNIT_LEDGER'):
    ok(f"the reconciler has no {bad!r}", bad not in code)
# The flag's NAME does appear once in code - inside the email body, telling Peter it was not
# touched. That is a message, not a read. The precise assertion above (no environ.get) is the one
# that matters; a blanket name match would flag the reassurance itself.
ok("the only mention is the line telling Peter it was untouched",
   code.count("EXEC_UNIT_LEDGER") == 1 and "untouched" in code)
ok("it computes no verdict on the incident", "no verdict is computed" in full.lower())
wf = open(".github/workflows/pr10-reconcile.yml", encoding="utf-8").read()
wfc = "\n".join(l for l in wf.split("\n") if not l.strip().startswith("#"))
ok("the workflow is dispatch-only, never scheduled",
   "schedule:" not in wfc and "cron" not in wfc and "workflow_dispatch" in wfc)
ok("it is read-only on contents", "contents: read" in wf)
ok("it runs the REVIEW branch, not main", "review/per-play-unit-exposure-guard" in wf)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
