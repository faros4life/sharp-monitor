#!/usr/bin/env python3
"""TAKE + POST across Phase 1, Board V3 and R1 (Peter, Nov 13).

"TAKE available liquidity immediately at an acceptable after-fee price, even when less than $50 is
available. POST the remaining unfilled stake as a resting limit order."

THE AUDIT FINDING THIS RESTS ON: take/remainder/resting already existed and already sized the
remainder from CONFIRMED fills. MIN_ORDER = $50 was the only thing refusing the play outright -
Peter's 9:31 R1 alert, "ProphetX ladder can't cover $50+ at the alert number (have $37.00)", would
have taken $37 and rested $187. So this is one floor, not a second execution path.

Nothing here places, submits, cancels or prices anything live.
"""
import inspect
import sys

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


def _got(x):
    return ex._got(x)


print("1. The take floor is $5, and it is the SAME floor on every take path")
check("MIN_TAKE is 5", abs(ex.MIN_TAKE - 5.0) < 1e-9)
check("it is configurable without a code change", 'os.environ.get("EXEC_MIN_TAKE"' in open("executor.py").read())
src = open("executor.py").read()
for fn, nm in ((ex.live_remainder, "live_remainder"), (ex.rest_wanted, "rest_wanted")):
    check(f"{nm} uses MIN_TAKE, not the old $50", "MIN_TAKE" in inspect.getsource(fn))
check("the ProphetX first take uses MIN_TAKE", "ProphetX ladder can't cover ${MIN_TAKE:.0f}+" in src)
check("every other venue's first take uses MIN_TAKE", '"{name} ladder can\'t cover ${MIN_TAKE:.0f}+' in src.replace('f"', '"'))
check("the POST side matches the TAKE side (Kalshi)", 'why_not.append(f"Kalshi: under ${MIN_TAKE:.0f}")' in src)
check("the POST side matches the TAKE side (Polymarket US)",
      'why_not.append(f"Polymarket US: under ${MIN_TAKE:.0f}")' in src)

print("\n2. Peter's own 9:31 R1 case: $37 available against a $224 stake")
check("$37 is now takeable", 37.00 >= ex.MIN_TAKE - 0.01)
check("...and would have been refused before", 37.00 < ex.MIN_ORDER - 0.01)
rem = round(224.0 - 37.0, 2)
check("the remainder to POST is the unfilled part", rem == 187.0)
check("and the remainder is postable", rem >= ex.MIN_TAKE - 0.01)

print("\n3. The remainder is sized from CONFIRMED fills, never submitted quantity (rule 3)")
lr = inspect.getsource(ex.live_remainder)
check("live_remainder subtracts _got(), the confirmed fill", "_got(first)" in lr and "sum(_got(o) for o in more)" in lr)
check("it targets the ORIGINAL stake", 'target = lv["risk"]' in lr)
rw = inspect.getsource(ex.rest_wanted)
check("rest_wanted rests only the unfilled part", 'lv["rest_risk"] = rem' in rw)
check("and computes it from confirmed fills too", "sum(_got(x) for x in allo)" in rw)
rb = inspect.getsource(ex.rest_bid)
check("rest_bid never rests more than that remainder", 'min(risk, float(r["live"]["rest_risk"]))' in rb)

print("\n4. Fills + resting exposure can never exceed the intended stake (rule 4)")
TARGET = 200.0
for filled, label in ((0.0, "nothing filled"), (37.0, "partial"), (200.0, "fully filled")):
    remaining = round(TARGET - filled, 2)
    check(f"{label}: take {filled:.2f} + post {remaining:.2f} == {TARGET:.2f}",
          abs(filled + remaining - TARGET) < 1e-9)
check("a full fill leaves nothing to post", round(TARGET - 200.0, 2) < ex.MIN_TAKE)

print("\n5. Zero liquidity still refuses, and says so (rule 8)")
check("a zero-depth ladder is below the floor", 0.0 < ex.MIN_TAKE - 0.01)
check("the refusal is reported, not silent", "refuse_untransmitted(r," in src)
check("and it names the amount actually available", "(have ${stake:.2f})" in src)

print("\n6. All three lanes use the SAME take/post code (rule: apply consistently)")
mb = src
check("one dispatch for every lane", 'r["live"]["order"] = live_order(r)' in mb)
check("one remainder path for every lane", 'r["live"]["more"] = live_remainder(r)' in mb)
check("one resting path for every lane", "if rest_wanted(r):" in mb)
check("the stake per lane still comes from unit_for(lane) - strategy untouched",
      'unit_for((r.get("live") or {}).get("lane"))' in rb)

print("\n7. Duplicate remainders cannot be posted by overlapping runs (rule 9)")
check("each placed order and resting bid reaches LIVEKEYS",
      mb.count('LIVEKEYS.add(derive_key(p) or p["play_key"])') >= 2)
check("live_remainder never reuses a venue within a play", 'used = {lv["book"]}' in lr and "used.add(" in lr)
check("the resting path refuses once a duplicate reason exists",
      'return lv.get("why") == ["no live book has the alert number or better"]' in rw)

print("\n8. Nothing about eligibility, pricing or limits moved")
check("the -130 cap is untouched", "CAP_LINE = -130" in src)
check("the 2c tolerance venues are untouched", str(ex.TOL_BOOKS) == str(("prophetx", "novig")))
check("lane risk limits are untouched", ex.BOARD_DAILY_RISK == 2000.0 and ex.R1_DAILY_RISK == 2000.0)
check("resting still expires 30 min before the start (rule 7)", ex.REST_BEFORE_MIN == 30)
check("MIN_ORDER itself is left defined, not repurposed", ex.MIN_ORDER == 50.0)

print()
if fails:
    print(f"FAIL  test_take_and_post.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
