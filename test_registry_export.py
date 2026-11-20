#!/usr/bin/env python3
"""The registry export must state what it does NOT have, rather than inventing cuts to reach 56."""
import registry_export as re_

FAILED, TOTAL = [], 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


e = re_.entries()
ok("the master list parses to 34 entries", len(e) == 34, len(e))
ok("25 are betting lanes", sum(1 for r in e if r["is_betting_lane"]) == 25)
ok("9 are lenses or research, not strategies", sum(1 for r in e if not r["is_betting_lane"]) == 9)
ok("LENSES are not counted as betting lanes",
   all(not r["is_betting_lane"] for r in e if r["section"].startswith("LENSES")))
ok("RESEARCH is not counted as betting lanes",
   all(not r["is_betting_lane"] for r in e if r["section"].startswith("RESEARCH")))
ok("entry 1 is LANE 1", [r for r in e if r["entry_no"] == 1][0]["name"] == "LANE 1")
ok("dollar figures are redacted on the way out",
   re_.clean("won $1,234.50 today") == "won [redacted] today", re_.clean("won $1,234.50 today"))
ok("bold markers are stripped", re_.clean("**LANE 1**") == "LANE 1")

import json, tempfile, os
f = os.path.join(tempfile.mkdtemp(), "r.json")
re_.main(["x", f])
d = json.load(open(f))
ok("no dollar figure survives into the file", "$" not in json.dumps(d))
ok("the duplicate entry numbers are named", d["duplicate_entry_numbers"] == [7, 29],
   d["duplicate_entry_numbers"])
ok("the export says plainly there is no list of 56", any("no list of 56" in g for g in d["gaps"]))
ok("alert_price is named as the binding gap",
   any("alert_price" in g and "binding gap" in g for g in d["gaps"]))
ok("the missing play_id is named", any("play_id" in g for g in d["gaps"]))
ok("the strategy_key limitation is named", any("strategy_key" in g for g in d["gaps"]))
ok("the lane map is exported", d["lane_map"]["r1"] == "R1" and len(d["lane_map"]) == 4)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
import sys as _s
_s.exit(1 if FAILED else 0)
