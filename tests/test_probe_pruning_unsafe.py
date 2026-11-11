"""WHY THE LINE PROBES CANNOT BE PRUNED (Nov 11).

The obvious speed fix is to stop probing lines the floor rule will reject anyway: at ProphetX's
1-call-per-second pace, 5 lines x 4 books per play is the bulk of a run. For Board v3 and R1 the
floor IS the alert line, so every candidate from a worse line is discarded - the probe looks free
to skip.

IT IS NOT. half_point() derives the value of a half point from the price gaps between ADJACENT
probed lines on the same book. Pruning lines removes gaps, which changes the median, which changes
hp, which changes c_eq = prob(am) - hb*hp for every candidate at a converted line - which can
change WHICH LINE IS TAKEN and at what price.

This test pins that, so a future session measuring the same bottleneck does not ship the same
"equivalent" optimisation. If the probes are ever to be pruned, hp must first be made independent
of the probe set (e.g. a separately sourced half-point value), and that is a pricing change
requiring Peter's approval - not an efficiency change.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


BASE = {225.5: -105, 226.0: -110, 226.5: -116, 227.0: -123, 227.5: -131}
FIVE = [225.5, 226.0, 226.5, 227.0, 227.5]
PRUNED = [226.5, 227.0, 227.5]          # floor == alert line 226.5, UNDER keeps the higher numbers


def ladder(lines):
    return {(b, ln): {"best_price_american": BASE[ln] + (0 if b == "novig" else -2)}
            for b in ("novig", "prophetx") for ln in lines}


hp5, src5 = ex.half_point(ladder(FIVE), "total", "UNDER", "NBA")
hp3, src3 = ex.half_point(ladder(PRUNED), "total", "UNDER", "NBA")

ck("both probe sets yield a LIVE half point (not the fallback)",
   "live" in src5 and "live" in src3, f"{src5} / {src3}")
ck("pruning reduces the gap count", "8 gaps" in src5 and "4 gaps" in src3, f"{src5} / {src3}")
ck("PRUNING CHANGES THE HALF-POINT VALUE", abs(hp5 - hp3) > 1e-9,
   f"{hp5:.5f} vs {hp3:.5f}")

# and that difference is big enough to change which line is taken
def pick(hp):
    better = ex.american_to_prob(BASE[227.5] - 2) - 2 * hp   # 227.5: two half-points better
    alertln = ex.american_to_prob(BASE[226.5] - 2) - 0 * hp  # 226.5: the alert line
    return "227.5" if better < alertln else "226.5"


ck("THE PICK FLIPS: full probe set takes 226.5", pick(hp5) == "226.5", pick(hp5))
ck("THE PICK FLIPS: pruned probe set takes 227.5", pick(hp3) == "227.5", pick(hp3))
ck("so pruning is NOT routing-neutral", pick(hp5) != pick(hp3))

# the mechanism, pinned so the reason survives
import inspect  # noqa: E402

hpsrc = inspect.getsource(ex.half_point)
ck("half_point reads the probed ladders", "ladders" in inspect.signature(ex.half_point).parameters
   or "ladders" in hpsrc)
ck("  and only counts ADJACENT pairs exactly 0.5 apart", "- 0.5) < 1e-9" in hpsrc)
ck("  taking the median across books", "gaps[len(gaps) // 2]" in hpsrc)
ck("  so the probe set is an input to the price, not just to eligibility",
   "best_price_american" in hpsrc)

ev = inspect.getsource(ex.evaluate)
ck("evaluate still probes the full nearby set", "(0, -0.5, 0.5, -1.0, 1.0)" in ev)
ck("hp is computed from those ladders", "half_point(ladders" in ev)
ck("and hp feeds the ranking key", "hb * hp" in ev)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
print(f"\nhp(5 lines)={hp5:.5f} {src5}   hp(3 lines)={hp3:.5f} {src3}   "
      f"delta={abs(hp5 - hp3) * 100:.2f}c   pick {pick(hp5)} -> {pick(hp3)}")
sys.exit(1 if BAD else 0)
