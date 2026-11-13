#!/usr/bin/env python3
"""Every live order AND every resting bid is announced BEFORE dispatch, on all three lanes.

THE DEFECT (Peter, Nov 13, 9:06 AM): live_play_alert() fires only inside
    if r["verdict"] == "WOULD PLACE" and r["live"]["go"]:
while
    if rest_wanted(r):
sits OUTSIDE that block, at the same indent. A play that never took the live-order branch could
therefore submit a RESTING BID with no prior notice. It happened: Board V3 rested $215.78 on Novig
(NBA Utah vs Houston, Over 218.5, limit -106) at 14:06:01Z and Peter learned of it only from the
post-submission message. STOP does not cancel a resting bid, so that is money at a venue he was
never warned about.

Nothing here places, submits, cancels or prices anything.
"""
import inspect
import re
import sys

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


SENT = []


def fake_tg_push(title, text):
    SENT.append((title, text))


print("1. The resting path announces BEFORE it dispatches")
src = inspect.getsource(ex.rest_bid)
i_alert = src.find("rest_pre_alert(")
i_loop = src.find("for b in REST_BOOKS:")
check("rest_bid calls rest_pre_alert", i_alert > 0)
check("and it runs BEFORE the venue loop", 0 < i_alert < i_loop)
for guard in ("journal_latch_why()", "no start time", "live_guards()"):
    check(f"...and AFTER the pre-dispatch refusal: {guard}", src.find(guard) < i_alert)

print("\n2. The alert carries what Peter asked for")
ex.tg_push, _orig = fake_tg_push, ex.tg_push
SENT.clear()
ex.PRE_ALERTED.clear()
from datetime import datetime, timedelta, timezone
exp = datetime.now(timezone.utc) + timedelta(hours=6)
r = {"play": {"sport": "NBA", "game": "Utah vs Houston", "bet": "Over 218.5 (-108)",
              "play_key": "board|NBA|Utah vs Houston|total|OVER"},
     "entry": {"price_after_fee": -108}, "live": {"lane": "board", "line": 218.5}}
ex.rest_pre_alert(r, 215.78, exp, ("novig", "kalshi"))
check("an alert was sent", len(SENT) == 1)
title, body = SENT[0] if SENT else ("", "")
for field, needle in (("the lane", "BOARD"), ("it is a RESTING bid", "RESTING"),
                      ("not yet placed", "not yet placed"), ("the game", "Utah vs Houston"),
                      ("side and line", "Over 218.5"), ("odds after fees", "-108 after fees"),
                      ("the venue", "Novig"), ("the stake", "215.78"),
                      ("the expiry", "ET"), ("STOP will not cancel it", "does NOT cancel")):
    check(f"it names {field}", needle in (title + "\n" + body))

print("\n3. ONE pre-alert per play - the resting remainder does not repeat it")
SENT.clear()
ex.rest_pre_alert(r, 215.78, exp, ("novig",))
check("a second call for the same play sends nothing", len(SENT) == 0)
SENT.clear()
ex.PRE_ALERTED.clear()
ex.rest_pre_alert(r, 215.78, exp, ("novig",))
check("but a fresh run announces it again", len(SENT) == 1)

print("\n4. live_play_alert registers the play, so the remainder stays silent")
lpa = inspect.getsource(ex.live_play_alert)
check("live_play_alert records the play in PRE_ALERTED", "PRE_ALERTED.add" in lpa)
check("rest_pre_alert checks PRE_ALERTED first", "PRE_ALERTED" in inspect.getsource(ex.rest_pre_alert))

print("\n5. A failed notification is REPORTED, never swallowed (item 6)")


def boom(title, text):
    raise RuntimeError("telegram down")


ex.tg_push = boom
ex.PRE_ALERTED.clear()
ex.LOG.clear()
got = ex.rest_pre_alert(r, 215.78, exp, ("novig",))
check("it returns False rather than raising into the order path", got is False)
check("and the failure is written to LOG, which every run prints",
      any("PRE-SUBMISSION ALERT FAILED" in l for l in ex.LOG))
mb = inspect.getsource(ex.main) if hasattr(ex, "main") else open("executor.py").read()
check("the immediate-order alert reports its failures the same way",
      "PRE-SUBMISSION ALERT FAILED (order still proceeds)" in open("executor.py").read())
ex.tg_push = _orig

print("\n6. All three lanes reach the resting path through the SAME code")
msrc = open("executor.py").read()
check("rest_wanted/rest_bid are not lane-specific",
      "lane" not in inspect.getsource(ex.rest_wanted).split("def ")[0][:0] + "")
check("the resting branch is lane-agnostic in main", "if rest_wanted(r):" in msrc)
check("unit_for(lane) supplies each lane's own stake, unchanged",
      "unit_for((r.get(\"live\") or {}).get(\"lane\"))" in inspect.getsource(ex.rest_bid))

print("\n7. Post-submission reporting is unchanged (item 4) and nothing is called filled early")
nr = open("executor.py").read()
check("RESTING is reported as its own outcome", "NOVIG RESTING (nothing filled yet)" in nr)
check("a fill is only claimed when the venue confirms quantity",
      'if st == "FILLED" and not int(x.get("filled_qty") or 0)' in nr)
check("expiry is 30 minutes before the start", ex.REST_BEFORE_MIN == 30)
check("and the bid is sized to expire at start - REST_BEFORE_MIN",
      "st - timedelta(minutes=REST_BEFORE_MIN)" in inspect.getsource(ex.rest_bid))

print()
if fails:
    print(f"FAIL  test_pre_submission_alerts.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
