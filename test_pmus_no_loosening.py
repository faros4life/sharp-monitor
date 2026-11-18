#!/usr/bin/env python3
"""ACTIVATION SAFETY: no Polymarket US pricing or eligibility path may become more permissive.

Peter, Nov 18, activation blocker 3: "Confirm no other pricing or eligibility path becomes more
permissive under the new schedule."

The trap this file exists for is that the quantities run in OPPOSITE DIRECTIONS, so "use the bigger
number" is wrong half the time and "use the smaller" is wrong the other half:

  ECONOMICS / GATE   a bigger fee makes the net price WORSE -> harder to clear a threshold -> STRICTER.
                     pmus_fee.gate_coef() takes max().
  EXECUTION FLOOR    a bigger fee makes the venue's own after-fee price worse, which puts the floor
                     LOWER -> admits prices the old floor refused -> LOOSER.
                     pmus_fee.floor_coef() takes min().

One rule, two directions. Every assertion below is written as "schedule is never more permissive than
legacy" for that specific quantity, never as a bare inequality on the coefficient.

Both lanes checked here are LIVE: EXEC_BOARD_FEE_BASIS is ON in production (the executor log prints
`BOARD_FEE_BASIS: on`), whatever executor.py's own default says.
"""
import json
import subprocess
import sys

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


PROBE = r'''
import json
import executor as ex, board_build as bb, clv_std as cs, pmus_fee as pf
COSTS = (0.30, 0.42, 0.51, 0.545, 0.62, 0.74, 0.88)
AMS = (-300, -200, -150, -130, -126, -120, -110, 100, 130, 150, 300)
out = {
  "model": pf.MODEL, "taker": pf.taker(), "gate": pf.gate_coef(), "floor": pf.floor_coef(),
  "cap": ex.CAP_LINE,
  # economics: the net decimal we would actually receive
  "net": {str(c): bb.after_fee_dec("polymarket_us", c) for c in COSTS},
  # gate: the frozen qualification price every eligibility check reads, anchored on RAW COST.
  # Anchoring on the after-fee american instead is a reader error - the same after-fee number is a
  # DIFFERENT raw price in each model, so comparing qual_price(-110) across models compares two
  # different bets. The raw screen cost is the physical invariant, and bc.ladder_result is the path
  # the per-level gate actually uses.
  "qual_from_raw": {}, "econ_from_raw": {},
  # kept for the weaker property that holds in both models: the gate is never looser than economics
  "qual_vs_econ": {str(a): (ex.qual_price(a, "polymarket_us"), a) for a in AMS},
  # board execution floor (LIVE lane)
  "floor_am": {str(c): ex.board_after_fee_floor({"price": c, "book": "polymarket_us",
                                                 "league": "NBA"})[0] for c in COSTS},
  # per-level liquidity actually admitted at a fixed threshold
  "levels": {},
  # price REQUIREMENT: the raw price the venue must show to net a target
  "raw_for": {str(a): cs.net_dec("polymarket_us", 1 + (100/abs(a) if a < 0 else a/100)) for a in AMS},
  # maker side
  "maker": {str(c): cs.net_dec("polymarket_us", 1/c, maker=True) for c in COSTS},
  # the other three trigger venues must not move at all
  "others": {b: {str(c): bb.after_fee_dec(b, c, "NBA") for c in COSTS}
             for b in ("kalshi", "novig", "prophetx")},
  "other_floor": {b: ex.board_after_fee_floor({"price": 0.51, "book": b, "league": "NBA"})[0]
                  for b in ("kalshi", "novig", "prophetx")},
  # GLOBAL book must be priced on its own fee and be untouched by the US model
  "global": {str(c): bb.after_fee_dec("polymarket", c) for c in COSTS},
  "pm_global_fee": bb.PM_GLOBAL_FEE,
}
import book_check as bc
for c in COSTS:
    _r = bc.ladder_result([(c, 500.0)], None, None, None, None, ex.PMUS_FEE, ex.PMUS_QUAL_FEE)
    _lv = _r["buy_levels"][0]
    out["qual_from_raw"][str(c)] = _lv["american_after_fee_qual"]
    out["econ_from_raw"][str(c)] = _lv["american"]
for thr in (-110, -120, -126, -130):
    r = bc.ladder_result([(0.545, 500.0)], None, None, None, None, ex.PMUS_FEE, ex.PMUS_QUAL_FEE)
    out["levels"][str(thr)] = sum(d for a, d in ex.levels("polymarket_us", r, qual=True) if a >= thr)
print("PROBE" + json.dumps(out))
'''


def probe(model):
    import os
    e = dict(os.environ)
    e.pop("PMUS_FEE", None)
    e["PMUS_FEE_MODEL"] = model
    r = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, env=e, timeout=300)
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("PROBE"):
            return json.loads(ln[5:])
    raise AssertionError(f"probe failed for {model!r}: {(r.stderr or '')[-700:]}")


L, S = probe("legacy"), probe("schedule")

ok("the two models really are different", L["taker"] != S["taker"], (L["taker"], S["taker"]))
ok("legacy is 0.06 and schedule is 0.095", (L["taker"], S["taker"]) == (0.06, 0.095))

# ---------------------------------------------------------------- 1. ECONOMICS: net price only worsens
for c, v in L["net"].items():
    ok(f"net price at cost {c} is no better under schedule", S["net"][c] <= v + 1e-12, (v, S["net"][c]))

# ---------------------------------------------------------------- 2. GATE: qualification only tightens
# Anchored on RAW COST: for the same screen price the venue shows, the gate price may only get worse.
for c, v in L["qual_from_raw"].items():
    ok(f"gate price for raw cost {c} is no more lenient under schedule", S["qual_from_raw"][c] <= v,
       (v, S["qual_from_raw"][c]))
for c, v in L["econ_from_raw"].items():
    ok(f"economic price for raw cost {c} is no better under schedule", S["econ_from_raw"][c] <= v,
       (v, S["econ_from_raw"][c]))
# The weaker property, true in both models: the gate never prices BETTER than the economics. Under
# legacy it is strictly worse (0.0695 > 0.06); under schedule the two coincide, so qual_price becomes
# an identity. Equality is not a loosening - the economics it matches have themselves moved to the
# conservative rate, which is why section 2 above is the test that matters.
for tag, P in (("legacy", L), ("schedule", S)):
    for a, (q, econ) in P["qual_vs_econ"].items():
        if q is None:
            ok(f"[{tag}] qual price at {a} is computable", False, "returned None")
            continue
        ok(f"[{tag}] gate at {a} is never better than economics", q <= econ, (q, econ))

# ---------------------------------------------------------------- 3. FLOOR: pinned, never lower
for c, v in L["floor_am"].items():
    ok(f"board execution floor at cost {c} is UNCHANGED", S["floor_am"][c] == v, (v, S["floor_am"][c]))
ok("the floor basis is pinned below the active rate under schedule", S["floor"] <= S["taker"],
   (S["floor"], S["taker"]))
ok("the floor basis equals the legacy basis under schedule", S["floor"] == L["taker"],
   (S["floor"], L["taker"]))
ok("the floor and the gate move in OPPOSITE directions, by design",
   S["floor"] <= L["floor"] and S["gate"] >= L["gate"], (S["floor"], L["floor"], S["gate"], L["gate"]))

# ---------------------------------------------------------------- 4. LIQUIDITY admitted never grows
for thr, v in L["levels"].items():
    ok(f"dollars admitted at threshold {thr} never increase", S["levels"][thr] <= v, (v, S["levels"][thr]))

# ---------------------------------------------------------------- 5. price requirement only rises
for a, v in L["raw_for"].items():
    ok(f"net decimal at {a} is no better under schedule", S["raw_for"][a] <= v + 1e-12,
       (v, S["raw_for"][a]))

# ---------------------------------------------------------------- 6. maker side never improves
for c, v in L["maker"].items():
    ok(f"maker net at cost {c} is no better under schedule", S["maker"][c] <= v + 1e-12,
       (v, S["maker"][c]))

# ---------------------------------------------------------------- 7. the cap is untouched
ok("the -130 after-fee cap is unchanged", L["cap"] == S["cap"] == -130, (L["cap"], S["cap"]))

# ---------------------------------------------------------------- 8. other venues bit-identical
for b in ("kalshi", "novig", "prophetx"):
    ok(f"{b} net prices are bit-identical", L["others"][b] == S["others"][b])
    ok(f"{b} board floor is bit-identical", L["other_floor"][b] == S["other_floor"][b],
       (L["other_floor"][b], S["other_floor"][b]))

# ---------------------------------------------------------------- 9. GLOBAL is separate and untouched
ok("global Polymarket is priced on its own 0.03", L["pm_global_fee"] == S["pm_global_fee"] == 0.03,
   (L["pm_global_fee"], S["pm_global_fee"]))
ok("global Polymarket prices are bit-identical across the US models", L["global"] == S["global"])
ok("global is NOT priced at the US rate", L["global"] != L["net"], "global and US must differ")

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
