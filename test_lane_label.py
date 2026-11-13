#!/usr/bin/env python3
"""Novig fill reports must carry the REAL lane (Nov 13, Peter: "STILL SAYS PHASE 1"). Offline."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import executor as ex

FAIL = []
def ck(n, got, want):
    if got != want: FAIL.append(f"{n}: got {got!r}, want {want!r}")

BOARD = "NBA|Memphis vs New Orleans: Total Points|total|OVER"
R1 = "NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"

# The bug: the dispatched key has no lane prefix, so lane_from_key can only say PHASE 1.
ck("unprefixed key alone cannot resolve a lane", ex.lane_from_key(BOARD), "PHASE 1")
ck("a prefixed key still resolves directly", ex.lane_from_key("board|" + BOARD), "BOARD V3")

rows, enabled = [], [True]
ex.registry.rows = lambda: rows
ex.registry.enabled = lambda: enabled[0]

rows[:] = [{"key": "board|" + BOARD}, {"key": BOARD}, {"key": "r1|" + R1}]
m = ex.lane_lookup([BOARD, R1])
ck("board play recovers its lane", m.get(BOARD), "BOARD V3")
ck("r1 play recovers its lane", m.get(R1), "R1")

# A genuine Phase 1 play has no prefixed row anywhere: it must stay unresolved -> default.
rows[:] = [{"key": BOARD}]
ck("unprefixed-only stays unresolved", ex.lane_lookup([BOARD]).get(BOARD), None)

# Two lanes claiming one base key must NOT be guessed.
rows[:] = [{"key": "board|" + BOARD}, {"key": "r1|" + BOARD}]
ck("conflicting lanes are left unresolved", ex.lane_lookup([BOARD]).get(BOARD), None)

# Unreadable or disabled registry must degrade, never raise.
enabled[0] = False
ck("disabled registry yields no lanes", ex.lane_lookup([BOARD]), {})
enabled[0] = True
def boom(): raise RuntimeError("registry down")
ex.registry.rows = boom
ck("unreadable registry degrades quietly", ex.lane_lookup([BOARD]), {})

print(f"test_lane_label: {'FAIL' if FAIL else 'PASS'}")
for f in FAIL: print("  " + f)
sys.exit(1 if FAIL else 0)
