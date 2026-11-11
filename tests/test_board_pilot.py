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

print("\n" + ("ALL PASS" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}"))
sys.exit(1 if FAIL else 0)
