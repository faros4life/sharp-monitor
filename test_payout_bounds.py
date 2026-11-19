#!/usr/bin/env python3
"""Payout-aware P/L bound (Peter, Nov 19): "Plus-money wins can legitimately produce profit greater
than the stake. Replace the incorrect |P/L| <= risked invariant with a valid payout-aware check
using verified individual bet odds and stakes."

What went wrong: clv_dashboard_recon asserted abs(units) <= risked_u. That is true for any loss and
for a minus-money win, and FALSE for a plus-money win - a 1.00u stake at +150 returns 1.50u of
profit. Peter's sizing risks a full unit at plus money ("If + money we bet 300"), so the lane only
had to contain one plus-money winner to fail. It did: R1, 3 confirmed selections, 2 settled, 0
contradictory, and the dashboard's OWN recomputation of P/L and ROI both matched - which is what
showed the figures were right and the bound was wrong. The whole dashboard refused to publish
because of it.

This is the same trap CLAUDE.md already records once: verifying a finding's arithmetic is not
verifying that the behaviour is unintended. The arithmetic was fine both times; the rule was Peter's.
"""
import clv_coverage as cov

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


UNIT = 100.0
old_invariant = lambda u, risked: abs(u) <= risked + 0.011     # what was there before

# ------------------------------------------------------------------ 1. the three price cases
plus = [{"stake": 100.0, "to_pay": 250.0}]            # +150: risk 1.00u to win 1.50u
minus = [{"stake": 110.0, "to_pay": 210.0}]           # -110: risk 1.10u to win 0.91u
w, st, okp = cov.payout_ceiling(plus)
ok("a plus-money bet's ceiling is to_pay minus stake", (w, st, okp) == (150.0, 100.0, True), (w, st, okp))
ok("PLUS-MONEY WIN: profit above the stake is allowed",
   cov.within_payout_bounds(w / UNIT, st / UNIT, w / UNIT))
ok("...and the OLD invariant wrongly rejected exactly this", not old_invariant(w / UNIT, st / UNIT))

w2, st2, _ = cov.payout_ceiling(minus)
ok("MINUS-MONEY WIN: profit below the stake is allowed",
   cov.within_payout_bounds(w2 / UNIT, st2 / UNIT, w2 / UNIT))
ok("...and the old invariant also allowed it, so nothing regressed there",
   old_invariant(w2 / UNIT, st2 / UNIT))

ok("LOSS: losing the whole stake is allowed",
   cov.within_payout_bounds(-st2 / UNIT, st2 / UNIT, w2 / UNIT))
ok("LOSS: losing MORE than the stake is rejected",
   not cov.within_payout_bounds(-(st2 / UNIT) - 0.5, st2 / UNIT, w2 / UNIT))

ok("a win ABOVE what the bet could ever pay is still rejected",
   not cov.within_payout_bounds(2.0, 1.0, 1.5))
ok("a win exactly at the ceiling is allowed", cov.within_payout_bounds(1.5, 1.0, 1.5))

# ------------------------------------------------------------------ 2. the R1 shape that failed
# 2 settled fills, one plus-money winner, one minus-money loser.
r1 = [{"stake": 100.0, "to_pay": 250.0}, {"stake": 110.0, "to_pay": 210.0}]
w3, st3, _ = cov.payout_ceiling(r1)
realised = (150.0 - 110.0) / UNIT          # the plus win lands, the minus one loses
ok("the R1 shape: ceiling is the sum of what each bet could pay", w3 == 250.0, w3)
ok("the R1 shape passes the new bound", cov.within_payout_bounds(realised, st3 / UNIT, w3 / UNIT))
ok("the R1 shape where |P/L| exceeds risked is no longer a failure",
   cov.within_payout_bounds(1.5, 1.0, 1.5) and not old_invariant(1.5, 1.0))

# ------------------------------------------------------------------ 3. unknown inputs are withheld
w4, st4, ok4 = cov.payout_ceiling([{"stake": 100.0, "to_pay": None}])
ok("a fill with no to_pay makes the ceiling unknowable", (w4, ok4) == (None, False), (w4, ok4))
ok("...but its stake still counts toward the risked total", st4 == 100.0, st4)
ok("an unknown ceiling WITHHOLDS the win check rather than passing or failing it",
   cov.within_payout_bounds(99.0, None, None))
ok("an unknown risked still lets the ceiling bind", not cov.within_payout_bounds(9.0, None, 1.5))
ok("units of None is never a failure", cov.within_payout_bounds(None, 1.0, 1.5))
w5, _, ok5 = cov.payout_ceiling([{"stake": 100.0, "to_pay": 250.0}, {"stake": 50.0, "to_pay": None}])
ok("ONE unknown payout in a set makes the whole ceiling unknown", (w5, ok5) == (None, False), (w5, ok5))
ok("a to_pay below the stake never makes a negative ceiling",
   cov.payout_ceiling([{"stake": 100.0, "to_pay": 40.0}])[0] == 0.0)
ok("an empty set has a zero ceiling and zero stake", cov.payout_ceiling([]) == (0.0, 0.0, True))

# ------------------------------------------------------------------ 4. the recon actually uses it
src = open("clv_dashboard_recon.py").read()
ok("the wrong invariant is gone", "|P/L| never exceeds settled risked units" not in src)
ok("the loss bound is kept", "a loss never exceeds the settled risked units" in src)
ok("the payout bound is checked", "P/L within the bets' own payout bounds" in src)
ok("the ceiling comes from the shared helper, not a second implementation",
   "cov.payout_ceiling(ss)" in src and "cov.within_payout_bounds(" in src)
ok("an unknown ceiling is reported, not silently skipped", "payout ceiling NOT CHECKED" in src)
ok("a selection paying more than it could is named", "OVER ITS OWN PAYOUT" in src)
ok("no sizing or P/L calculation was touched",
   "live_stake" not in src and "def stake" not in src)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
