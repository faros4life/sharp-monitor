#!/usr/bin/env python3
"""Settled stake/payout correction (Peter, Nov 19, approved after proof).

The ledger froze each bet's FIRST-SEEN stake and to_pay - taken from the OPEN row, which can be a
partial fill - while refreshing profit from the SETTLED row's pnl. One row, two bases.

Proved against Novig's own settlement record for two R1 selections (units at the R1 registered unit):

  Xavier @ Mississippi St, Under 163.5, WIN : cost 1.079u, payout 2.075u, pnl 0.996u
  Delaware St @ East Carolina, Under 147.5  : cost 1.038u, payout 2.035u, pnl 0.997u

payout - cost equals pnl to the cent on both, so Novig's record is internally consistent. The ledger
held 0.616u / 1.185u / 0.996u: PROFIT was right and the ROI DENOMINATOR was understated, so R1's ROI
read high and the payout ceiling read low - which is what the dashboard diagnostic caught.

The trap this guards: a settlement row DROPS the stake for losses. Overwriting unconditionally would
blank the stake on every loss, which is precisely why first-seen is kept as the fallback. The
original is preserved under <field>_first_seen rather than discarded.
"""
import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


def run(snap, row):
    snap = dict(snap)
    return cl.apply_settled_amounts(snap, row), snap


# ------------------------------------------------------------------ 1. the proved win cases
xav_snap = {"stake": 123.2, "to_pay": 237.0, "profit": 199.2}
xav_row = {"result": "W", "settled": "2026-11-14T02:00Z", "stake": 215.80, "to_pay": 415.0, "profit": 199.2}
ch, out = run(xav_snap, xav_row)
ok("WIN: the settled stake replaces the partial first-seen stake", out["stake"] == 215.80, out["stake"])
ok("WIN: the settled payout replaces the first-seen payout", out["to_pay"] == 415.0, out["to_pay"])
ok("WIN: profit is left exactly as it was", out["profit"] == 199.2)
ok("WIN: payout minus stake now equals the venue's pnl",
   abs((out["to_pay"] - out["stake"]) - out["profit"]) < 0.01,
   out["to_pay"] - out["stake"])
ok("WIN: the original first-seen stake is preserved, not discarded",
   out["stake_first_seen"] == 123.2 and out["to_pay_first_seen"] == 237.0)
ok("WIN: the substitution is auditable", out["stake_src"] == "settled row")
ok("WIN: both fields are reported as replaced", ch == ["stake", "to_pay"], ch)

del_snap = {"stake": 104.0, "to_pay": 204.0, "profit": 199.43}
_, out2 = run(del_snap, {"result": "W", "settled": "x", "stake": 207.57, "to_pay": 407.0})
ok("the second proved selection reconciles the same way",
   abs((out2["to_pay"] - out2["stake"]) - 199.43) < 0.01, out2["to_pay"] - out2["stake"])

# ------------------------------------------------------------------ 2. LOSSES: the trap
ch, out = run({"stake": 200.0, "to_pay": 390.0}, {"result": "L", "settled": "x", "stake": None, "to_pay": None})
ok("LOSS with the stake dropped: first-seen survives untouched",
   out["stake"] == 200.0 and out["to_pay"] == 390.0 and ch == [], (ch, out))
ok("LOSS: no first_seen shadow is written when nothing was replaced", "stake_first_seen" not in out)
ch, out = run({"stake": 200.0, "to_pay": 390.0}, {"result": "L", "settled": "x", "stake": "", "to_pay": ""})
ok("LOSS with empty-string fields is treated as missing, not as zero",
   out["stake"] == 200.0 and ch == [], (ch, out))
ch, out = run({"stake": 150.0}, {"result": "L", "settled": "x", "stake": 200.0})
ok("LOSS that DOES carry its stake still corrects it", out["stake"] == 200.0 and ch == ["stake"])

# ------------------------------------------------------------------ 3. partial fills / unsettled
ch, out = run({"stake": 50.0, "to_pay": 95.0}, {"stake": 200.0, "to_pay": 390.0})
ok("an UNSETTLED row never overwrites the first-seen pair",
   out["stake"] == 50.0 and ch == [], (ch, out))
ch, out = run({"stake": 50.0}, {"result": "W", "stake": 200.0})
ok("a result with no settled timestamp is not treated as settled", ch == [], ch)
ch, out = run({"stake": 50.0}, {"settled": "x", "stake": 200.0})
ok("a settled timestamp with no result is not treated as settled", ch == [], ch)

# ------------------------------------------------------------------ 4. missing / idempotent
ch, out = run({}, {"result": "W", "settled": "x", "stake": 200.0, "to_pay": 390.0})
ok("a snap with no prior values takes the settled pair",
   out["stake"] == 200.0 and out["to_pay"] == 390.0)
ok("...and records the absent original as None rather than inventing one",
   out["stake_first_seen"] is None)
ch, out = run({"stake": 200.0, "to_pay": 390.0}, {"result": "W", "settled": "x", "stake": 200.0, "to_pay": 390.0})
ok("identical values are not rewritten", ch == [], ch)
ok("...and leave no first_seen shadow", "stake_first_seen" not in out)
first = {"stake": 50.0}
cl.apply_settled_amounts(first, {"result": "W", "settled": "x", "stake": 200.0})
cl.apply_settled_amounts(first, {"result": "W", "settled": "x", "stake": 210.0})
ok("a later correction keeps the ORIGINAL first-seen, not the previous correction",
   first["stake_first_seen"] == 50.0 and first["stake"] == 210.0, first)

# ------------------------------------------------------------------ 5. scope
src = open("clv_ledger.py").read()
fn = src[src.index("def apply_settled_amounts("):src.index("def espn_fill(")]
ok("profit is never touched by this function", '"profit"' not in fn)
ok("nothing is deleted", ".pop(" not in fn and "del " not in fn)
ok("it is wired into the capture stage", "apply_settled_amounts(snap, b)" in src)
# Checked on the CODE, not the prose: the first version scanned the whole function and failed on
# its own docstring, which necessarily says what it does not touch. CLAUDE.md records this same
# over-blunt grep twice already.
_code = fn.split('"""')[2] if fn.count('"""') >= 2 else fn
ok("no sizing, pricing or risk control appears in the code",
   not any(t in _code for t in ("live_stake", "DAILY_STOP", "gate", "place")))
_lits = sorted(set(__import__("re").findall(r'"(\w+)"', _code)))
ok("the code touches only result, settled, stake, to_pay and its own audit suffixes",
   _lits == ["_first_seen", "_src", "result", "settled", "stake", "to_pay"], _lits)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
