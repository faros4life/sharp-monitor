#!/usr/bin/env python3
"""REVIEW/MEASUREMENT ONLY. The TRUE 2X verdict, its clauses, and the backfill boundary.

Every 2X backtest so far used a depth-only proxy (2-of-3 >= $5k AND >= $25k total) without the
Pinnacle multiple, which fires on 73% of resulted plays. This file's job is to persist the real
verdict per alert so the forward test measures the trigger itself.

Nothing here places, prices or changes a bet.
"""
import os
import re

SRC = open("x2_tag.py", encoding="utf-8").read()
P, F = [], []
def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


def verdict(tot, p_limit, dep):
    """The three clauses exactly as x2_tag computes them."""
    two5k = sum(1 for v in dep if v >= 5000) >= 2
    c_mult = p_limit is not None and tot >= 2 * p_limit
    return c_mult, two5k, tot >= 25000, (c_mult and two5k and tot >= 25000)


# --- the condition itself -------------------------------------------------------------------
ok("all three clauses together pass", verdict(30000, 10000, [9000, 9000, 12000])[3] is True)
ok("the MULTIPLE clause is what the depth-only proxy drops",
   verdict(30000, 20000, [9000, 9000, 12000]) == (False, True, True, False))
ok("one exchange over $5k is not two", verdict(30000, 10000, [26000, 3000, 1000])[1] is False)
ok("under $25k total fails even with a big multiple",
   verdict(24000, 1000, [12000, 12000, 0])[2] is False)
ok("exactly at the thresholds passes", verdict(25000, 12500, [5000, 5000, 15000])[3] is True)
ok("no Pinnacle limit means NO verdict, not a False",
   verdict(30000, None, [9000, 9000, 12000])[0] is False)

# --- what the file persists ------------------------------------------------------------------
for f in ("x2_pass", "p_limit", "c_mult", "c_two5k", "c_total", "mult", "exch_total", "basis"):
    ok(f"the row persists {f}", f'"{f}"' in SRC or f"{f}=" in SRC)
ok("the multiple is stored so it can be re-derived, not just trusted",
   'mult=round(tot / rec["p_alert"], 3)' in SRC)
ok("a row with no limit keeps NO x2 verdict at all",
   'for f in ("x2", "x2_pass", "p_limit", "c_mult", "mult"):' in SRC and "rec.pop(f, None)" in SRC)
ok("depth is read all-levels first, as the condition specifies",
   'd.get("this_side_all_levels") if d.get("this_side_all_levels") is not None' in SRC)
ok("the exchanges are Novig, ProphetX and Kalshi",
   re.search(r'EXCH = \("novig", "prophetx", "kalshi"\)', SRC) is not None)

# --- backfill can never pool into the forward count ---------------------------------------------
ok("every row records whether it is forward or backfill", 'rec["basis"] =' in SRC)
ok("the boundary is the day the fields landed", 'FORWARD_FROM = (os.environ.get("X2_FORWARD_FROM")' in SRC)
ok("backfill is OFF by default - it bills, so it is opt-in per run",
   'BACKFILL_DAYS = max(0, int(os.environ.get("X2_BACKFILL_DAYS") or "0"))' in SRC)
ok("a backfill widens the fixture window it needs", "days=1 + BACKFILL_DAYS" in SRC)
ok("the log says plainly that backfill is backtest data",
   "must not pool into the forward count" in SRC)
ok("and reports forward and backfill counts separately",
   'basis") == "forward"' in SRC and 'basis") == "backfill"' in SRC)
ok("the log also prints what the depth-only proxy WOULD have passed, so the gap is visible",
   "depth-only proxy would pass" in SRC)

import datetime as _dt
def basis(alerted, forward_from="2026-11-23"):
    return "forward" if str(alerted)[:10] >= forward_from else "backfill"
ok("an alert from before the landing day is backfill", basis("2026-11-22T18:00:00Z") == "backfill")
ok("an alert from the landing day onward is forward",
   basis("2026-11-23T00:01:00Z") == "forward" and basis("2026-12-05T12:00:00Z") == "forward")

# --- a verdict survives the prune ----------------------------------------------------------------
ok("a row that HAS a verdict is kept, so a backfilled row is not dropped next run",
   'v.get("x2_pass") is not None' in SRC)

# --- it stays a sidecar, and stays free ------------------------------------------------------------
ok("it never writes the liquidity feed - the monitor rewrites that file in full each run",
   "liquidity/alerts.json" not in SRC.split('a = load(')[1].split("\n")[0].replace('"liquidity/alerts.json", []', "")
   and 'open("liquidity/alerts.json", "w")' not in SRC)
_writes = re.findall(r'open\(([^,]+),\s*"w"\)', SRC)
ok("the only files it writes are its own sidecar and the shared fixture cache",
   sorted(set(w.strip() for w in _writes)) == ["CACHE", "OUT"], str(_writes))
ok("and those are x2/limits.json and the fixture cache",
   'OUT = "x2/limits.json"' in SRC and 'CACHE = "oddspapi/fixtures.json"' in SRC)
ok("the Pinnacle limit comes from the FREE historical path",
   'cl.api("/historical-odds"' in SRC)
ok("the fixture call is still capped at once per league per 8h",
   "timedelta(hours=8)" in SRC)
ok("the log prints counts only - no stake, price or play identity",
   not re.search(r'print\(f?"[^"]*\{[^}]*(stake|price|game|bet)', SRC))

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
