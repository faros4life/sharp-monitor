#!/usr/bin/env python3
import nba_novig_forward as n
p = f = 0
def check(name, cond):
    global p, f
    if cond: p += 1
    else: f += 1; print("  [FAIL]", name)
close = {"line": 220.5, "over": -110, "under": -110, "mins_before": 10}
s = {"side": "Over", "line": 220.5, "novig": {"prob": 0.50, "dec": 2.0}}
n.grade(s, close); check("fair close, 50c price -> 0% CLV", abs(s["clv_v"]) < 1e-6)
s = {"side": "Under", "line": 220.5, "novig": {"prob": 0.48, "dec": 2.0833}}
n.grade(s, close); check("50% fair vs 48c price -> +4.17%", abs(s["clv_v"] - 4.1667) < 0.01)
s = {"side": "Over", "line": 220.5, "novig": {"prob": 0.5}}
n.grade(s, dict(close, line=221.0)); check("different close line refused, not modelled", "clv_v" not in s and "differs" in s["clv_v_excl"])
s = {"side": "Over", "line": 220.5, "novig": {"prob": 0.5}}
n.grade(s, dict(close, mins_before=300)); check("stale close refused", "clv_v" not in s and "min before" in s["clv_v_excl"])
s = {"side": "Over", "line": 220.5}
n.grade(s, close); check("no novig field = not in sample", "clv_v" not in s and "clv_v_excl" not in s)
s = {"side": "Over", "line": 220.5, "novig": {"excluded": "no open Novig total at 220.5"}}
n.grade(s, None); check("no quote excluded with reason", s["clv_v_excl"].startswith("no open"))
g = [(f"2026-11-{i % 28 + 1:02d}", {"clv_v": 1.0 if i % 2 else 2.0}) for i in range(100)]
e = n.evaluate(g); check("100 unique qualifying, both halves positive -> met", e["met"] and e["n"] == 100)
e = n.evaluate(g[:99]); check("99 qualifying -> not met", not e["met"])
g2 = [(f"2026-11-{i % 28 + 1:02d}", {"clv_v": -1.0 if i >= 50 else 1.0}) for i in range(100)]
check("CHECK half negative -> not met", not n.evaluate(g2)["met"])
print(f"{p} passed, {f} failed")
raise SystemExit(1 if f else 0)
