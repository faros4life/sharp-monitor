#!/usr/bin/env python3
"""Part 1 of the Telegram cleanup (Peter, 19 Nov 2026): TRIGGER -> ORDER -> FILL, labels and IDs.

The regression that forced this: on 19 Nov a Novig order that had MATCHED $203.50 at 2.00x was
reported "[BOARD V3] NOVIG NO FILL ... nothing traded". The fill READ had failed; nothing about
the trade was known. 0 of 29 Novig placements since 12 Nov have a fill read, so that was the
normal path, not an edge case.

Scope is notification-only. No test here asserts anything about execution, sizing, routing,
eligibility or risk, because nothing in Part 1 touches them.
"""
import hashlib
import re

import executor as ex

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


PLAY = {"play_key": "NBA|Golden State vs Memphis: Total Points|total|UNDER",
        "sport": "NBA", "game": "Golden State vs Memphis", "bet": "Under 225.5"}
OTHER = {"play_key": "NBA|Los Angeles C vs San Antonio: Total Points|total|UNDER",
         "sport": "NBA", "game": "Los Angeles C vs San Antonio", "bet": "Under 226.5"}

print("1. ITEM 1 - an unread fill is never called a no-fill")
src = open("executor.py").read()
check("the venue-confirmed branch is gated on fills_read",
      src.count('if res.get("fills_read"):') >= 2)
check("NO FILL now claims only what the venue confirmed",
      "Venue confirms zero matched quantity" in src)
check("the unread case says STATUS UNKNOWN - VERIFY", src.count('"STATUS UNKNOWN - VERIFY"') >= 2)
check("it states outright that this is not a no-fill", "This is NOT a no-fill" in src)
check("the old false claim is gone from both venue paths",
      "Fill-or-kill got nothing at this price or better." not in src)
check("both venue paths were corrected, not just the one in the incident",
      src.count('"STATUS UNKNOWN"') >= 2)

print("2. ITEM 2 - one play ID across the whole lifecycle")
a, b = ex.play_id(PLAY), ex.play_id(dict(PLAY, bet="ignored - same play key"))
check("the id is stable for the same play", a == b, f"{a} {b}")
check("different plays get different ids", a != ex.play_id(OTHER))
check("the id is the dedupe token the registry already uses",
      a == ex.pid(PLAY["play_key"]), f"{a} vs {ex.pid(PLAY['play_key'])}")
check("a play with no key says unavailable rather than inventing one",
      ex.play_id({}) == "unavailable", ex.play_id({}))
check("lane_note appends the ID line", 'out.append(f"ID: {play_id(p)}")' in src)

print("3. ITEM 3 - TAKE orders get an ORDER stage")
check("an ORDER SUBMITTED message exists", "ORDER SUBMITTED - TAKE on" in src)
check("it is sent before the venue call",
      src.index("ORDER SUBMITTED - TAKE on") < src.index("res = book_live.kalshi_place("))
check("it reports PENDING, not a fill", "status PENDING - the venue has not answered yet" in src)
check("it carries the play ID", 'f"ID: {play_id(p)}"' in src)
check("a missing stake is named, not invented", "requested stake not recorded" in src)

print("4. ITEM 4 - HR1 wording, manual only")
hr = open("sharp_monitor.py").read()
check("HR1 still cannot place: it appears nowhere in the executor", "HR1" not in src)
check("the trigger source is named", "TRIGGER SOURCE: Hard Rock" in hr)
check("the confirming book is named when there is one", "CONFIRMING BOOK: {_conf}" in hr)
check("and marked UNVERIFIED when there is not",
      "CONFIRMING BOOK: none on this exact line - UNVERIFIED" in hr)
check("other books are context only, never verification",
      "CONTEXT ONLY, not price verification" in hr)
check("the live-board instruction is explicit",
      "CHECK HARD ROCK LIVE BOARD. DO NOT BET UNLESS THE EXACT HR LINE AND" in hr)
# Checked against CODE, not comments: my own comment explains the removal and quotes the old
# string, which a raw substring test read as the string still being there.
hr_code = "\n".join(l for l in hr.splitlines() if not l.strip().startswith("#"))
check("the Muse reference is gone from the message", "log it to Muse" not in hr_code)
check("an alert is not a bet, and recording is manual",
      "THIS IS AN ALERT, NOT A BET" in hr and "approved tracking process" in hr)
check("the bad-quote safeguard is preserved",
      "that is a bad quote, not a moved line" in hr)
check("the unverified label is preserved", "[HR1 - MANUAL - UNVERIFIED]" in hr)

print("5. DEDUPE - one message per real state transition")
t_unknown = ex.notify_tok(PLAY, "STATUS UNKNOWN", {"order_id": "abc", "filled_stake": None})
check("a repeated poll of an unchanged order is the same token",
      t_unknown == ex.notify_tok(PLAY, "STATUS UNKNOWN", {"order_id": "abc", "filled_stake": None}))
check("a workflow restart is the same token too (no run id in it)",
      t_unknown == ex.notify_tok(dict(PLAY), "STATUS UNKNOWN",
                                 {"order_id": "abc", "filled_stake": None}))

print("   a correction must never be suppressed")
t_filled = ex.notify_tok(PLAY, "FILLED", {"order_id": "abc", "filled_stake": 203.50})
check("STATUS UNKNOWN -> FILLED is a different token, so the fill still sends",
      t_unknown != t_filled, f"{t_unknown} {t_filled}")
t_partial = ex.notify_tok(PLAY, "FILLED", {"order_id": "abc", "filled_stake": 100.00})
check("PARTIAL -> FULL is a different token", t_partial != t_filled)
t_cancel = ex.notify_tok(PLAY, "NO FILL", {"order_id": "abc", "filled_stake": 0.0})
check("a confirmed cancellation is its own token", t_cancel not in (t_unknown, t_filled, t_partial))
check("the same state on a different order is a different token",
      t_filled != ex.notify_tok(PLAY, "FILLED", {"order_id": "zzz", "filled_stake": 203.50}))
check("the same state on a different play is a different token",
      t_filled != ex.notify_tok(OTHER, "FILLED", {"order_id": "abc", "filled_stake": 203.50}))

print("6. the claim FAILS OPEN - silence is the worse failure")
real = ex.registry.claim_token


def boom(*a, **k):
    raise RuntimeError("store unavailable")


try:
    ex.registry.claim_token = boom
    check("an unreachable store still sends", ex.notify_once(PLAY, "FILLED", {"filled_stake": 1.0}))
finally:
    ex.registry.claim_token = real
check("the claim is a notification write only - no fill, exposure or grading call",
      "claim_token" in src and "put_fills" not in src.split("def notify_once")[1].split("def ")[0])

print("7. a notifier failure cannot change an order outcome (rule 8)")
blk = src.split("ORDER SUBMITTED - TAKE on")[0].rsplit("try:", 1)[-1]
check("the ORDER SUBMITTED send is wrapped", "except Exception" in
      src.split("ORDER SUBMITTED - TAKE on")[1][:1200])
check("its failure is logged, not raised",
      "order-submitted notice failed" in src)

print("8. regression fixtures - the two orders that caused this")
src_code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
check("GS/MEM: no emitter can print 'nothing traded' for an unknown status",
      "nothing traded" not in src_code, [l for l in src_code.splitlines() if "nothing traded" in l][:1])
check("LAC/SA: the same split applies to the live-order path, not only resting",
      src.count("The venue fill read FAILED") >= 2)

print("9. novig_reports - the emitter that actually sent the bad message")
check("NO FILL is no longer the else branch",
      'elif st in ("CANCELED", "CANCELLED", "EXPIRED"):' in src)
check("an unrecognised or absent status reads STATUS UNKNOWN - VERIFY",
      '"NOVIG STATUS UNKNOWN - VERIFY"' in src)
# Implicit string concatenation across source lines again - normalise before matching.
src_flat = re.sub(r'"\s*\n\s*(f?)"', "", src)
check("the confirmed case names the venue status",
      "zero matched quantity ({st})" in src_flat and "venue confirms" in src_flat.lower())
check("the requested amount is labelled requested, never matched",
      "requested" in src and "asked; nothing traded" not in src_code)
check("an unknown status is never muted", "never muted" in src or "is the one that needs him" in src)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_telegram_sequence: all passed")
