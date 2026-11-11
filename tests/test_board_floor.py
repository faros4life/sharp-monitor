"""Board v3 floor-line protection (Peter, Nov 11: "original alert line or strictly better").

Board plays carry no floor_line - the board producer writes none (0 of 1045 rows in
board/calls.json) - so the Oct 31 bet-only-at floor never bound on Lane 3 and
better_halfpoints could convert to a WORSE line on an estimated half-point value.
evaluate() now defaults a board play's floor to its own alert line. Lane 1 unchanged.
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


src = inspect.getsource(ex.evaluate)

# ---------------------------------------------------------------- the defect is real
calls = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "board/calls.json")))["calls"]
rows = list(calls.values())
ck("board producer writes no floor_line (the defect this fixes)",
   sum(1 for r in rows if r.get("floor_line") is not None) == 0, f"of {len(rows)} rows")

# ---------------------------------------------------------------- the fix is wired
ck("evaluate defaults a board floor", "p.get(\"source\") == \"board\"" in src and "floor = line" in src)
floor_blk = [l.strip() for l in src.splitlines() if "floor = line" in l]
ck("the default is applied exactly once", len(floor_blk) == 1, repr(floor_blk))
guard = [l for l in src.splitlines() if "floor is None" in l and "board" in l]
ck("the default only fires when no floor was supplied", guard and "floor is None" in guard[0], repr(guard))
ck("the default is limited to spread/total",
   guard and "spread" in guard[0] and "total" in guard[0], repr(guard))
ck("Lane 1's own floor still takes precedence (p.get first)",
   src.index('floor = p.get("floor_line")') < src.index("floor = line"))
ck("the Oct 31 ledger backfill is untouched",
   'ent.get("floor_line") is not None' in inspect.getsource(ex.main))

# ------------------------------------------------- floor semantics: worse lines are blocked
# evaluate blocks a candidate when better_halfpoints(mtype, side, floor, bl) < 0.
# With floor == the alert line, that means: strictly-better or equal only.
def blocked(mtype, side, floor, bl):
    return ex.better_halfpoints(mtype, side, floor, bl) < -1e-9


for mtype, side, alert in (("total", "UNDER", 225.5), ("total", "OVER", 225.5),
                           ("spread", "HOME", -6.5), ("spread", "AWAY", 3.5)):
    ck(f"{mtype}/{side}: the alert line itself is allowed", not blocked(mtype, side, alert, alert))

# totals: UNDER wants a HIGHER number, OVER wants a LOWER one
ck("total/UNDER: higher line allowed (better)", not blocked("total", "UNDER", 225.5, 226.5))
ck("total/UNDER: lower line BLOCKED (worse)", blocked("total", "UNDER", 225.5, 224.5))
ck("total/UNDER: much lower line BLOCKED", blocked("total", "UNDER", 225.5, 205.5))
ck("total/OVER: lower line allowed (better)", not blocked("total", "OVER", 225.5, 224.5))
ck("total/OVER: higher line BLOCKED (worse)", blocked("total", "OVER", 225.5, 226.5))

# the two real rows from the replay that the missing floor would have admitted
ck("replay row 'Utah vs Dallas' 227.5 -> 205.5 is now BLOCKED",
   blocked("total", "UNDER", 227.5, 205.5))
ck("replay row 'Detroit vs New York' 218.5 -> 215.5 is now BLOCKED",
   blocked("total", "UNDER", 218.5, 215.5))

# a worse line must stay blocked NO MATTER how cheap it is: the floor is checked before price
floor_first = src.index("better_halfpoints(mtype, side, floor, bl)") < src.index("c_eq_q >")
ck("the floor is checked BEFORE the price gate (price cannot buy a worse line)", floor_first)
ck("the floor check continues (skips the candidate) rather than adjusting it",
   "floor_blocked += 1" in src)

# ---------------------------------------------------------------- nothing else moved
ck("TOL_BOOKS still prophetx+novig", ex.TOL_BOOKS == ("prophetx", "novig"), str(ex.TOL_BOOKS))
ck("PX_TOL_CENTS still 2", ex.PX_TOL_CENTS == 2)
ck("-130 cap unchanged", ex.CAP_LINE == -130)
ck("board unit still 200", ex.BOARD_UNIT == 200.0)
ck("board play cap still 10", ex.BOARD_MAX_PLAYS == 10)
ck("board daily risk still 1500", ex.BOARD_DAILY_RISK == 1500.0)
ck("Lane 1 unit still 300", ex.LIVE_UNIT == 300.0)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
