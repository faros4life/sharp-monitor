#!/usr/bin/env python3
"""The Oct 27 retail deadband is PHASE 1 ONLY, and a static refusal never announces a LIVE PLAY.

Peter, Nov 12, after the Toronto/Philadelphia Under 224.5: a Board V3 play that had cleared the
board rule, the liquidity gate, pin_check and the line-value REPLACEMENT maximum (Under 225.5 at
-117 against a -113 alert) was refused by the retail deadband - a filter from the phase-1 lane. It
had also already been announced as a LIVE PLAY with a proposed stake, because the band was checked
inside live_order(), which runs AFTER live_play_alert().

Three scopes have to come out differently, and that is the point of these tests:
  - Hard Rock                -> GLOBAL, every lane (Peter is limited there)
  - unknown after-fee price  -> GLOBAL and fail-closed, every lane (not knowing != acceptable)
  - the -119..-110 band      -> PHASE 1 ONLY

Nothing here places, replays or modifies any order. No historical order is re-sent.
"""
import os
import re
import sys

os.environ["REGISTRY_TOKEN"] = ""
import agree_rules as ar
import executor as ex
import px_live

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


def play(lane, book="novig", paf=-113, source=None):
    """A WOULD PLACE result in `lane`, priced `paf` after fees on `book`."""
    return {"entry": {"book_key": book, "price_after_fee": paf},
            "play": {"bet": "Under 224.5 (-113)", "sport": "NBA",
                     "game": "Toronto @ Philadelphia", "play_key": "k1",
                     **({"source": source} if source else {})},
            "verdict": "WOULD PLACE",
            "live": {"go": True, "lane": lane, "book": "novig", "risk": 234.0,
                     "shown": -117, "line": 225.5, "limit": "-117"}}


print("The band is PHASE 1 only")
r = play("rules")
check("phase 1 at -113 on Novig is refused",
      "retail deadband" in (ex.static_refusal(r) or ""))
check("BOARD V3 at the same price is NOT refused", ex.static_refusal(play("board")) is None)
check("R1 at the same price is NOT refused", ex.static_refusal(play("r1")) is None)
check("LANE 2 at the same price is NOT refused", ex.static_refusal(play("lane2")) is None)

print("\nAn unlabelled play is treated as phase 1, so the band is never dropped by accident")
r = play(None)
r["live"].pop("lane")
check("no lane marker -> still refused", "retail deadband" in (ex.static_refusal(r) or ""))
check("lane_of() agrees it is phase 1", ex.lane_of(r) == "rules")

print("\nThe whole band, not just -113 (inclusive at both ends, phase 1)")
for p in (ar.DEADBAND[0], -115, ar.DEADBAND[1]):
    check(f"phase 1 refused at {p}", "retail deadband" in (ex.static_refusal(play("rules", paf=p)) or ""))
for p in (ar.DEADBAND[0] - 1, ar.DEADBAND[1] + 1):
    check(f"phase 1 NOT refused at {p} (outside the band)", ex.static_refusal(play("rules", paf=p)) is None)

print("\nProphetX stays exempt, on phase 1 too")
check("ProphetX at -113 on phase 1 is not refused",
      ex.static_refusal(play("rules", book="prophetx")) is None)

print("\nHard Rock is GLOBAL - it is not scoped to phase 1")
for lane in ("rules", "board", "r1", "lane2"):
    hrbook = sorted(ar.HARD_ROCK)[0]
    check(f"{lane}: Hard Rock-priced refused",
          "Hard Rock" in (ex.static_refusal(play(lane, book=hrbook)) or ""))

print("\nAn UNKNOWN after-fee price is GLOBAL and fail-closed - it is not scoped either")
for lane in ("rules", "board", "r1", "lane2"):
    check(f"{lane}: unknown price refused (fail closed)",
          "unknown" in (ex.static_refusal(play(lane, paf=None)) or ""))

print("\nThe Toronto/Philadelphia example passes Board V3's STATIC checks...")
tor = play("board", book="novig", paf=-113)
check("no static refusal", ex.static_refusal(tor) is None)

print("...WITHOUT bypassing any later safety gate")
_lv = px_live.LIVE
px_live.LIVE = False
try:
    out = ex.live_order(tor)
    check("live_order still stops at the EXEC_LIVE gate, so nothing is placed",
          (out or {}).get("status") == "dry")
    check("and its reason is the live switch, not the deadband",
          "live is off" in str((out or {}).get("reason", "")))
finally:
    px_live.LIVE = _lv

print("\nlive_order() RE-CHECKS the same function, so the earlier call cannot bypass the gate")
_notes = []
_orig = (ex.refuse, px_live.LIVE)
ex.refuse = lambda r, reason, **k: _notes.append(reason) or {"status": "refused", "reason": reason}
px_live.LIVE = False
try:
    out = ex.live_order(play("rules"))
    check("a phase-1 band play is refused INSIDE live_order too",
          (out or {}).get("status") == "refused" and "retail deadband" in str(out.get("reason")))
    check("the refusal notification still fires (order outcome is never silent)", len(_notes) == 1)
finally:
    ex.refuse, px_live.LIVE = _orig

print("\nNotification sequence: the static check runs BEFORE live_play_alert at the order site")
src = open("executor.py").read()
blk = src[src.index('if r["verdict"] == "WOULD PLACE" and (r.get("live") or {}).get("go"):'):]
blk = blk[:blk.index("if rest_wanted(r):")]
i_static, i_alert = blk.find("static_refusal(r)"), blk.find("live_play_alert(r)")
check("static_refusal appears first in the block", 0 <= i_static < i_alert)
check("live_play_alert is inside the else branch",
      re.search(r"else:\s*\n(?:\s*#[^\n]*\n)*\s*try:[^\n]*\n\s*live_play_alert\(r\)", blk) is not None)
check("the refusal path does NOT call live_play_alert",
      "refuse(r, _sr)" in blk and blk.index("refuse(r, _sr)") < i_alert)

print()
if fails:
    print(f"FAIL  test_deadband_lane_scope.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
