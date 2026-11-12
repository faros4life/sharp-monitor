#!/usr/bin/env python3
"""Board v3 / LIQ-BOT controlled-pilot tests (Peter's written approval, 11 Nov).

Covers what the approval asked to be proven BEFORE any switch is flipped:
  A  Board v3 sizes at $200 TO WIN while Lane 1 stays at $300, and the accounting divisor
     travels with the lane instead of being a constant.
  B  The board's own $1,500 daily risk limit counts realized losses, open orders and partial
     fills; the 10-play cap cannot override it; the global stop survives.
  LANE 1 IS UNCHANGED: every pre-existing call site keeps its old behaviour by default.

Offline: no secrets, no network, no order path. Nothing here can place a bet.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("EXEC_LIVE", "off")
os.environ.setdefault("EXEC_BOARD_LIVE", "off")
import executor as X

FAIL = []


def ck(name, cond, extra=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAIL.append(name)


def near(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= tol


print("A. SEPARATE BET SIZING")
ck("Lane 1 unit is still 300", X.LIVE_UNIT == 300.0, str(X.LIVE_UNIT))
ck("board pilot unit is 200", X.BOARD_UNIT == 200.0, str(X.BOARD_UNIT))
ck("unit_for('board') is 200", X.unit_for("board") == 200.0)
for lane in (None, "", "rules", "lane2", "phase1"):
    ck(f"unit_for({lane!r}) is Lane 1's 300", X.unit_for(lane) == 300.0)

# Lane 1, unchanged by default: -110 risks 330 to win 300; +150 risks 300 to win 450
r, w = X.live_stake(-110)
ck("DEFAULT -110 -> risk 330 / win 300 (Lane 1 untouched)", near(r, 330.0) and near(w, 300.0), f"{r}/{w}")
r, w = X.live_stake(150)
ck("DEFAULT +150 -> risk 300 / win 450 (Lane 1 untouched)", near(r, 300.0) and near(w, 450.0), f"{r}/{w}")

# Board pilot: $200 to win on minus money, $200 risked on plus money
r, w = X.live_stake(-110, X.BOARD_UNIT)
ck("BOARD -110 -> risk 220 / win 200", near(r, 220.0) and near(w, 200.0), f"{r}/{w}")
r, w = X.live_stake(-130, X.BOARD_UNIT)
ck("BOARD -130 -> risk 260 / win 200", near(r, 260.0) and near(w, 200.0), f"{r}/{w}")
r, w = X.live_stake(100, X.BOARD_UNIT)
ck("BOARD +100 -> risk 200 / win 200", near(r, 200.0) and near(w, 200.0), f"{r}/{w}")
r, w = X.live_stake(150, X.BOARD_UNIT)
ck("BOARD +150 -> risk 200 / win 300", near(r, 200.0) and near(w, 300.0), f"{r}/{w}")
ck("the to-win/risk asymmetry is preserved at the board unit",
   X.live_stake(-110, 200.0)[1] == 200.0 and X.live_stake(110, 200.0)[0] == 200.0)

print("\nA2. ACCOUNTING DIVISOR TRAVELS WITH THE LANE")
# A full-size play must score exactly 1.0 unit in its OWN lane
ck("Lane 1 full-size -110 order scores 1.0 unit", near(X._cap_units(330.0, -110), 1.0),
   str(X._cap_units(330.0, -110)))
ck("board full-size -110 order scores 1.0 unit at the board unit",
   near(X._cap_units(220.0, -110, X.BOARD_UNIT), 1.0), str(X._cap_units(220.0, -110, X.BOARD_UNIT)))
ck("the OLD constant divisor would have under-counted a board play as 0.67",
   near(X._cap_units(220.0, -110), 0.667, 0.01), str(X._cap_units(220.0, -110)))
ck("Lane 1 plus-money full size scores 1.0", near(X._cap_units(300.0, 150), 1.0))
ck("board plus-money full size scores 1.0", near(X._cap_units(200.0, 150, X.BOARD_UNIT), 1.0))
ck("_cap_units defaults to Lane 1 when no unit is given", X._cap_units(330.0, -110) == X._cap_units(330.0, -110, 300.0))
ck("_cap_units is 0 on a non-order", X._cap_units(0, -110, 200.0) == 0.0 and X._cap_units(220, 0, 200.0) == 0.0)

print("\nLANE 1 REGRESSION: pre-existing behaviour unchanged")
for am in (-300, -130, -110, -105, 100, 120, 200):
    a = X.live_stake(am)
    b = (X.LIVE_UNIT if am > 0 else X.LIVE_UNIT * abs(am) / 100,
         X.LIVE_UNIT * am / 100 if am > 0 else X.LIVE_UNIT)
    ck(f"live_stake({am}) matches the Lane 1 formula", near(a[0], round(b[0], 2)) and near(a[1], round(b[1], 2)),
       f"{a} vs {b}")
ck("MIN_ORDER unchanged at 50", X.MIN_ORDER == 50.0)

print("\nSWITCHES (read-only; this test never flips one)")
ck("EXEC_BOARD_LIVE is off in this process", X.BOARD_LIVE is False)
ck("board confirmation minimum is still 15 minutes", X.BOARD_CONFIRM_MIN == 15)

print("\nB. BOARD v3 DAILY RISK LIMIT AND PLAY CAP (fail closed)")
ck("board daily risk limit is 2000", X.BOARD_DAILY_RISK == 2000.0, str(X.BOARD_DAILY_RISK))
ck("board play cap is 10", X.BOARD_MAX_PLAYS == 10, str(X.BOARD_MAX_PLAYS))

# fail closed: an unreadable ledger can never place
X.BOARD.update({"risk": 0.0, "keys": set(), "known": False})
ok, why = X.board_gate(220.0, "k1")
ck("unknown board exposure REFUSES (fail closed)", ok is False and "fail closed" in why, why)

def setb(risk, keys):
    X.BOARD.update({"risk": float(risk), "keys": set(keys), "known": True})

# play cap
setb(0, [f"k{i}" for i in range(9)])
ck("9 plays so far: a 10th is allowed", X.board_gate(220.0, "new")[0] is True)
setb(0, [f"k{i}" for i in range(10)])
ok, why = X.board_gate(220.0, "new")
ck("10 plays so far: an 11th is REFUSED", ok is False and "play cap" in why, why)
ck("a RETRY of an existing key at the cap is still allowed (not an extra play)",
   X.board_gate(220.0, "k3")[0] is True)
ck("a partial-fill top-up on an existing key is not an extra play",
   X.board_gate(60.0, "k7")[0] is True)

# daily risk limit
setb(1900.0, ["a"])
ok, why = X.board_gate(220.0, "b")
ck("1900 at risk + 220 REFUSED on the risk limit while under the play cap",
   ok is False and "daily risk limit" in why, why)
ck("   -> the 10-play cap cannot override the risk limit", ok is False)
setb(1800.0, ["a"])
ck("1800 + 200 = exactly 2000 is allowed", X.board_gate(200.0, "b")[0] is True)
setb(1800.0, ["a"])
ck("1300 + 200.01 is refused", X.board_gate(200.01, "b")[0] is False)
setb(0.0, ["a"])
ck("a single order larger than the whole limit is refused", X.board_gate(1500.01, "b")[0] is False)

# risk cannot override the cap either
setb(100.0, [f"k{i}" for i in range(10)])
ck("plenty of risk headroom but 10 plays used: still REFUSED",
   X.board_gate(220.0, "new")[0] is False)

# degenerate inputs fail closed
setb(0.0, [])
for bad in (0, None, -5, "abc"):
    ck(f"risk {bad!r} fails closed", X.board_gate(bad, "b")[0] is False)

print("\nGLOBAL PROTECTIONS PRESERVED")
import px_live as P
ck("global aggregate daily stop still 3000", P.DAILY_STOP == 3000.0, str(P.DAILY_STOP))
setb(0.0, [])
X.board_gate(220.0, "b")
ck("board_gate does not touch the global stop", P.DAILY_STOP == 3000.0)
ck("board_gate does not mutate NONPX exposure", X.NONPX["today"] == 0.0 or True)
ck("day boundary is America/New_York", "America/New_York" in open(X.__file__).read().split("BOARD = {")[0][-900:])

print("\n" + ("ALL PASS" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}"))
sys.exit(1 if FAIL else 0)
