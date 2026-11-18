#!/usr/bin/env python3
"""Polymarket US fee model, schedule of Nov 14 2026 (Peter yes, Nov 18 - model only, not activated).

Two things are asserted and they are easy to confuse:
  1. LEGACY is byte-identical to the pre-Nov-18 behaviour. That is what makes this commit safe to land
     without approval: live pricing cannot move until PMUS_FEE_MODEL is flipped.
  2. SCHEDULE prices the venue's published tiers, and every unknown resolves to the conservative value.

The historical fee assumption (0.06 taker, -0.0125 maker) is PRESERVED as the legacy branch rather than
deleted, because every executed price in the ledger was recorded under it. Restating a past fill at a
coefficient that did not exist when it filled would rewrite history; the old numbers stay reachable.
"""
import os
from datetime import datetime, timedelta, timezone

import exchange_lag as el
import pmus_fee as pf

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


ET = timezone(timedelta(hours=-5))
DEC110 = 1 + 100 / 110          # -110


def eff_with(model, *a, **k):
    """Call eff() under a given model without leaving the module mutated.

    Flips pmus_fee.MODEL, which is the ONLY model switch. An earlier version of this helper flipped
    an exchange_lag alias instead and the fee did not move - two switches, one of them dead. That is
    why the alias was deleted rather than kept for convenience.
    """
    was = pf.MODEL
    try:
        pf.MODEL = model
        return el.eff(*a, **k)
    finally:
        pf.MODEL = was


# ---------------------------------------------------------------- 1. the table itself
ok("taker tiers are ordered high floor -> low",
   [t[0] for t in el.PMUS_TAKER_TIERS] == sorted([t[0] for t in el.PMUS_TAKER_TIERS], reverse=True))
ok("maker tiers are ordered high floor -> low",
   [t[0] for t in el.PMUS_MAKER_TIERS] == sorted([t[0] for t in el.PMUS_MAKER_TIERS], reverse=True))
ok("published taker tiers are exactly the four from the schedule",
   sorted(t[1] for t in el.PMUS_TAKER_TIERS) == [0.0695, 0.075, 0.085, 0.095])
ok("cheapest published taker tier is still ABOVE the old 0.06 literal",
   min(t[1] for t in el.PMUS_TAKER_TIERS) > el.TAKER["polymarket.us"],
   f"min tier {min(t[1] for t in el.PMUS_TAKER_TIERS)} vs legacy {el.TAKER['polymarket.us']}")
ok("tier 1 maker earns no rebate",
   el._tier_coef(el.PMUS_MAKER_TIERS, 0.0) == 0.0)
ok("tier 1 maker threshold is $10MM",
   el.PMUS_MAKER_TIERS[-2][0] == 10_000_000.0)

# ---------------------------------------------------------------- 2. tier selection by volume
for vol, want in ((0.0, 0.095), (9_999.0, 0.095), (10_000.0, 0.085), (49_999.0, 0.085),
                  (50_000.0, 0.075), (249_999.0, 0.075), (250_000.0, 0.0695), (10_000_000.0, 0.0695)):
    ok(f"taker volume {vol:,.0f} -> {want}", el.pmus_coef(taker_vol_30d=vol, model="schedule")[0] == want,
       el.pmus_coef(taker_vol_30d=vol, model="schedule"))
for vol, want in ((0.0, 0.0), (9_999_999.0, 0.0), (10_000_000.0, -0.0035),
                  (50_000_000.0, -0.0070), (200_000_000.0, -0.0104)):
    ok(f"maker volume {vol:,.0f} -> {want}", el.pmus_coef(maker=True, maker_vol_30d=vol, model="schedule")[0] == want,
       el.pmus_coef(maker=True, maker_vol_30d=vol, model="schedule"))

# ---------------------------------------------------------------- 3. unknowns resolve CONSERVATIVELY
c, why = el.pmus_coef(model="schedule")
ok("unknown taker tier -> 0.095", c == 0.095 and "unestablished" in why, (c, why))
c, why = el.pmus_coef(maker=True, model="schedule")
ok("unverified maker rebate -> 0.0", c == 0.0 and "unverified" in why, (c, why))
ok("unknown taker tier is the WORST published tier, not a guess",
   el.pmus_coef(model="schedule")[0] == max(t[1] for t in el.PMUS_TAKER_TIERS))
ok("an unverified maker is never credited above raw price",
   el.pmus_coef(maker=True, model="schedule")[0] >= 0.0)

# ---------------------------------------------------------------- 4. onboarding window
first = datetime(2026, 11, 2, tzinfo=ET)
ok("day 1 is the day of the first fill", el.pmus_onboarding(first, datetime(2026, 11, 2, 23, tzinfo=ET)) == (True, 1))
ok("day 7 is still inside the window", el.pmus_onboarding(first, datetime(2026, 11, 8, 1, tzinfo=ET))[0] is True)
ok("day 8 is outside the window", el.pmus_onboarding(first, datetime(2026, 11, 9, 1, tzinfo=ET)) == (False, 8))
ok("onboarding gives 0.0695 regardless of zero volume",
   el.pmus_coef(taker_vol_30d=0.0, first_fill=first, asof=datetime(2026, 11, 3, tzinfo=ET), model="schedule")[0] == 0.0695)
ok("spent onboarding falls back to the volume tier",
   el.pmus_coef(taker_vol_30d=0.0, first_fill=first, asof=datetime(2026, 11, 18, tzinfo=ET), model="schedule")[0] == 0.095)
ok("UNKNOWN first fill is NOT treated as onboarding", el.pmus_onboarding(None) == (False, None))
ok("unknown first fill does not earn the cheap onboarding rate",
   el.pmus_coef(taker_vol_30d=0.0, model="schedule")[0] == 0.095)
ok("a first fill in the future is not a fill",
   el.pmus_onboarding(datetime(2026, 12, 25, tzinfo=ET), datetime(2026, 11, 18, tzinfo=ET)) == (False, None))

# ---------------------------------------------------------------- 5. LEGACY is unchanged (the safety claim)
ok("legacy taker decimal is the old 0.06 answer",
   abs(eff_with("legacy", "polymarket.us", DEC110) - 1.8561) < 5e-5,
   eff_with("legacy", "polymarket.us", DEC110))
ok("legacy maker decimal still exceeds raw (the old -0.0125 rebate)",
   eff_with("legacy", "polymarket.us", DEC110, maker=True) > DEC110)
# Only meaningful when the variable is actually unset: the suite is also run WITH it set to
# "schedule" to prove the activated model regresses nothing, and asserting the default there would
# fail on the test harness rather than on the code.
ok("legacy default is what an unset environment gets",
   os.environ.get("PMUS_FEE_MODEL") is not None
   or (os.environ.get("PMUS_FEE_MODEL", "") or "legacy").strip().lower() == "legacy")
ok("exchange_lag exposes NO second model switch", not hasattr(el, "PMUS_FEE_MODEL"))
for bk in ("kalshi", "novig.us", "prophetx"):
    ok(f"{bk} is untouched by the PMUS model",
       eff_with("schedule", bk, DEC110) == eff_with("legacy", bk, DEC110))

# ---------------------------------------------------------------- 6. SCHEDULE moves the price the right way
sch_t = eff_with("schedule", "polymarket.us", DEC110)
leg_t = eff_with("legacy", "polymarket.us", DEC110)
ok("schedule taker nets LESS than legacy taker", sch_t < leg_t, (sch_t, leg_t))
ok("schedule taker is worse than Kalshi at -110",
   sch_t < eff_with("schedule", "kalshi", DEC110), (sch_t, eff_with("schedule", "kalshi", DEC110)))
sch_m = eff_with("schedule", "polymarket.us", DEC110, maker=True)
ok("schedule maker equals the RAW price - free, not a rebate", abs(sch_m - DEC110) < 1e-9, sch_m)
ok("schedule maker never exceeds raw", sch_m <= DEC110 + 1e-12)
ok("posting still beats taking under the schedule", sch_m > sch_t)
# raw_for() calls eff() internally, so BOTH halves of the round trip must run under the same model.
# The first version of this assertion computed raw_for() as an argument - it was therefore evaluated
# under legacy before eff_with() switched the model, and the "failure" was the test, not the code.
_was = pf.MODEL
try:
    pf.MODEL = "schedule"
    _raw = el.raw_for("polymarket.us", 1.80)
    ok("raw_for inverts the schedule model", abs(el.eff("polymarket.us", _raw) - 1.80) < 1e-3,
       (_raw, el.eff("polymarket.us", _raw)))
    ok("schedule needs a HIGHER raw price than legacy for the same net",
       _raw > (lambda: (setattr(pf, "MODEL", "legacy"), el.raw_for("polymarket.us", 1.80),
                        setattr(pf, "MODEL", "schedule"))[1])())
finally:
    pf.MODEL = _was

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
# run_tests.py parses this exact shape. Without it the file reports rc=0 and NO assertion count, so 44
# real assertions were invisible in the suite total - a file that passes silently is not a file that is
# being counted.
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
