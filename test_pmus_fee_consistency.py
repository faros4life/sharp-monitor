#!/usr/bin/env python3
"""ONE fee model across every module that prices Polymarket US (Peter, Nov 18).

Peter: "Make every module use the same verified fee calculation" and "report whether any remaining
pricing path uses an inconsistent fee assumption." A number that merely looks right in one module is
not evidence; this file asserts that all of them produce the SAME number, under BOTH models, and that
no module keeps a private literal that could drift again.

Each module is re-imported in a SUBPROCESS with PMUS_FEE_MODEL set, because these constants resolve at
import time - checking them in one already-imported process would only ever test the default.

The GLOBAL book is deliberately out of scope. liquidity_monitor.TAKER_COEF and book_check.TAKER_COEF
price `polymarket` / `polymarket.global` at 0.03, a different venue with a different API that is not
bettable from the US. Routing those through pmus_fee would mis-price the global book and break the
resolution of historical rows, so this file asserts they are UNCHANGED - the absence of a change is
the correct behaviour here, not an omission.
"""
import json
import subprocess
import sys

import pmus_fee as pf

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


PROBE = r'''
import json, os
import pmus_fee as pf, exchange_lag as el, executor as ex, board_build as bb
import sharp_monitor as sm, ncaab_grade as ng, clv_std as cs
import liquidity_monitor as lm, book_check as bc
D = 1 + 100/110                     # -110
out = {
  "model": pf.MODEL,
  "pf_taker": pf.taker(), "pf_maker": pf.maker(), "pf_gate": pf.gate_coef(),
  "ex_fee": ex.PMUS_FEE, "ex_qual": ex.PMUS_QUAL_FEE,
  "bb_fee": bb.PMUS_FEE,
  "sm_fee": sm.TAKER_FEE["polymarket_us"],
  "el_taker_tbl": el.TAKER["polymarket.us"],
  # the six independent PRICING paths, all on the same input
  "p_el":   round(el.eff("polymarket.us", D), 9),
  "p_ng":   round(ng.eff("polymarket.us", D), 9),
  "p_cs":   round(cs.net_dec("polymarket_us", D), 9),
  "p_bb":   round(bb.after_fee_dec("polymarket_us", 1/D), 9),
  "p_sm":   round(sm.net(-110, "polymarket_us"), 4),
  "p_elmk": round(el.eff("polymarket.us", D, maker=True), 9),
  "raw": round(D, 9),
  # other venues must not move at all
  "kalshi": round(el.eff("kalshi", D), 9),
  "novig":  round(el.eff("novig.us", D), 9),
  "px":     round(el.eff("prophetx", D), 9),
  # GLOBAL book, must be untouched
  "lm_global": lm.TAKER_COEF.get("polymarket"), "bc_global": bc.TAKER_COEF.get("polymarket"),
  "ex_books": list(ex.BOOKS),
}
print("PROBE" + json.dumps(out))
'''


def probe(model):
    env = {"PMUS_FEE_MODEL": model} if model else {}
    import os
    e = dict(os.environ)
    e.pop("PMUS_FEE_MODEL", None)
    e.pop("PMUS_FEE", None)
    e.update(env)
    r = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, env=e, timeout=300)
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("PROBE"):
            return json.loads(ln[5:])
    raise AssertionError(f"probe failed for {model!r}: {(r.stderr or '')[-600:]}")


LEG = probe("legacy")
SCH = probe("schedule")
DEF = probe(None)

PRICE_PATHS = ("p_el", "p_ng", "p_cs", "p_bb")
CONSTS = ("pf_taker", "ex_fee", "bb_fee", "sm_fee")

# ---------------------------------------------------------------- 1. the models load at all
ok("legacy model loads", LEG["model"] == "legacy", LEG["model"])
ok("schedule model loads", SCH["model"] == "schedule", SCH["model"])
ok("UNSET environment defaults to legacy", DEF["model"] == "legacy", DEF["model"])
ok("unset environment is byte-identical to explicit legacy", DEF == LEG)

# ---------------------------------------------------------------- 2. one coefficient, every module
for tag, P in (("legacy", LEG), ("schedule", SCH)):
    vals = {k: P[k] for k in CONSTS}
    ok(f"[{tag}] every module's PMUS constant is the same number", len(set(vals.values())) == 1, vals)
    prices = {k: P[k] for k in PRICE_PATHS}
    ok(f"[{tag}] every PMUS pricing path returns the same decimal", len(set(prices.values())) == 1, prices)
    ok(f"[{tag}] sharp_monitor.net agrees with the decimal paths",
       abs(P["p_sm"] - (-100 / (P["p_el"] - 1) if P["p_el"] < 2 else (P["p_el"] - 1) * 100)) < 0.15,
       (P["p_sm"], P["p_el"]))

ok("legacy coefficient is still exactly 0.06", LEG["pf_taker"] == 0.06, LEG["pf_taker"])
ok("schedule coefficient is 0.095 with the tier unverified", SCH["pf_taker"] == 0.095, SCH["pf_taker"])
ok("legacy maker rebate is preserved", LEG["pf_maker"] == -0.0125, LEG["pf_maker"])
ok("schedule maker rebate is zero until proven", SCH["pf_maker"] == 0.0, SCH["pf_maker"])
ok("schedule maker price equals the raw price exactly", SCH["p_elmk"] == SCH["raw"], (SCH["p_elmk"], SCH["raw"]))
ok("schedule maker never beats raw", SCH["p_elmk"] <= SCH["raw"])
ok("schedule nets strictly less than legacy", SCH["p_el"] < LEG["p_el"], (SCH["p_el"], LEG["p_el"]))

# ---------------------------------------------------------------- 3. THE GATE (Peter's directive 5)
for tag, P in (("legacy", LEG), ("schedule", SCH)):
    ok(f"[{tag}] gate coefficient is never BELOW the applicable rate", P["ex_qual"] >= P["pf_taker"],
       (P["ex_qual"], P["pf_taker"]))
    ok(f"[{tag}] gate coefficient is never below the Nov 6 freeze", P["ex_qual"] >= pf.QUAL_FLOOR,
       (P["ex_qual"], pf.QUAL_FLOOR))
    ok(f"[{tag}] executor gate matches pmus_fee.gate_coef", P["ex_qual"] == P["pf_gate"],
       (P["ex_qual"], P["pf_gate"]))
ok("legacy gate is unchanged at the Nov 6 freeze", LEG["ex_qual"] == 0.0695, LEG["ex_qual"])
ok("schedule gate TIGHTENS to the conservative rate", SCH["ex_qual"] == 0.095, SCH["ex_qual"])
ok("the gate can never be the lenient side of the economics",
   LEG["ex_qual"] >= LEG["ex_fee"] and SCH["ex_qual"] >= SCH["ex_fee"])
# a fee correction must never CREATE a bet: the gate's net price may only get worse, never better
ok("activation cannot make a gated price BETTER than it was", SCH["ex_qual"] >= LEG["ex_qual"],
   (SCH["ex_qual"], LEG["ex_qual"]))

# ---------------------------------------------------------------- 4. the other three trigger venues
for v in ("kalshi", "novig", "px"):
    ok(f"{v} is bit-identical under both models", LEG[v] == SCH[v], (LEG[v], SCH[v]))
ok("all four trigger venues are present in executor.BOOKS",
   set(LEG["ex_books"]) == {"novig", "prophetx", "kalshi", "polymarket_us"}, LEG["ex_books"])
ok("executor trades the US venue, never the global book", "polymarket" not in LEG["ex_books"])

# ---------------------------------------------------------------- 5. the global book stays alone
for tag, P in (("legacy", LEG), ("schedule", SCH)):
    ok(f"[{tag}] global Polymarket is still 0.03, not routed through pmus_fee", P["lm_global"] == 0.03,
       P["lm_global"])
    ok(f"[{tag}] book_check global Polymarket is still 0.03", P["bc_global"] == 0.03, P["bc_global"])

# ---------------------------------------------------------------- 6. no module keeps a private literal
src = {}
for f in ("executor.py", "board_build.py", "sharp_monitor.py", "ncaab_grade.py", "exchange_lag.py"):
    src[f] = open(f).read()
ok("executor has no bare 0.06 PMUS literal", "PMUS_FEE = 0.06" not in src["executor.py"])
ok("board_build has no bare 0.06 PMUS literal", "PMUS_FEE = 0.06" not in src["board_build.py"])
ok("sharp_monitor has no bare 0.06 PMUS literal", 'or "0.06"' not in src["sharp_monitor.py"])
ok("ncaab_grade has no bare 0.06 PMUS literal", 'or "0.06"' not in src["ncaab_grade.py"])
ok("executor gate is not a frozen literal", "PMUS_QUAL_FEE = 0.0695" not in src["executor.py"])
for f in ("executor.py", "board_build.py", "sharp_monitor.py", "ncaab_grade.py", "exchange_lag.py"):
    ok(f"{f} imports pmus_fee", "import pmus_fee as pf" in src[f])

# ---------------------------------------------------------------- 7. the paper study is PINNED, not floated
# ev_sightings is measurement-only and every sighting it has recorded was measured at 0.06. It must have
# no literal of its own (so it cannot drift) AND must not follow the active model (so activation cannot
# silently restate its history). Those two requirements look contradictory and are not: pinning to
# pmus_fee.LEGACY_TAKER satisfies both.
ev = open("ev_sightings.py").read()
ok("ev_sightings keeps no PMUS literal of its own", '"polymarket_us": 0.06' not in ev)
ok("ev_sightings is pinned to the legacy basis", '"polymarket_us": pf.LEGACY_TAKER' in ev)
EVP = r'''
import json, pmus_fee as pf, ev_sightings as ev
print("PROBE" + json.dumps({"ev": ev.TAKER["polymarket_us"], "model": pf.MODEL}))
'''


def ev_probe(model):
    import os
    e = dict(os.environ)
    e.pop("PMUS_FEE", None)
    e["PMUS_FEE_MODEL"] = model
    r = subprocess.run([sys.executable, "-c", EVP], capture_output=True, text=True, env=e, timeout=300)
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("PROBE"):
            return json.loads(ln[5:])
    raise AssertionError(f"ev probe failed for {model!r}: {(r.stderr or '')[-400:]}")


ok("ev_sightings reports on 0.06 under legacy", ev_probe("legacy")["ev"] == 0.06)
ok("ev_sightings STILL reports on 0.06 under schedule - history is not restated",
   ev_probe("schedule")["ev"] == 0.06, ev_probe("schedule"))

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
