#!/usr/bin/env python3
"""Part 1 of the Telegram cleanup (Peter, 19 Nov 2026): TRIGGER -> ORDER -> FILL, labels and IDs.

The regression that forced this: on 19 Nov a Novig order that had MATCHED $203.50 at 2.00x was
reported "[BOARD V4] NOVIG NO FILL ... nothing traded". The fill READ had failed; nothing about
the trade was known. 0 of 29 Novig placements since 12 Nov have a fill read, so that was the
normal path, not an edge case.

Scope is notification-only. No test here asserts anything about execution, sizing, routing,
eligibility or risk, because nothing in Part 1 touches them.
"""
import ast
import hashlib
import io
import re
import tokenize

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
check("the venue-confirmed branch is gated on fills_read AND a readable quantity",
      src.count('if res.get("fills_read") and res.get("filled_stake") is not None:') >= 2)
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
check("an ORDER ATTEMPT message exists", "ORDER ATTEMPT - PENDING - TAKE on" in src)
check("it is sent before the venue call",
      src.index("ORDER ATTEMPT - PENDING - TAKE on") < src.index("res = book_live.kalshi_place("))
check("it reports PENDING, not a fill", "status PENDING - this is an ATTEMPT" in src)
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


_en = ex.registry.enabled
try:
    # enabled() is False in this container, so claim_token was never reached and this test
    # passed without exercising the failure at all. Force it on.
    ex.registry.claim_token, ex.registry.enabled = boom, (lambda: True)
    check("an unreachable store still sends", ex.notify_once(PLAY, "FILLED", {"filled_stake": 1.0}))
finally:
    ex.registry.claim_token, ex.registry.enabled = real, _en
check("the test exercised the failure rather than the disabled path",
      ex.registry.enabled() is False and ex.notify_once(PLAY, "x") is True)
check("the claim is a notification write only - no fill, exposure or grading call",
      "claim_token" in src and "put_fills" not in src.split("def notify_once")[1].split("def ")[0])

print("7. a notifier failure cannot change an order outcome (rule 8)")
check("the ORDER ATTEMPT send is wrapped", "except Exception" in
      src.split("ORDER ATTEMPT - PENDING - TAKE on")[1][:1400])
check("its failure is logged, not raised", "order-attempt notice failed" in src)
check("the acceptance send is wrapped too and logged, not raised",
      "order-acceptance notice failed" in src)

print("8. regression fixtures - the two orders that caused this")
src_code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
# Nov 19: src_code strips "#" lines but not docstrings, and novig_head's docstring quotes the old
# false message while explaining its removal. The requirement is that no EMITTED string says it, so
# this now walks the AST and checks every string literal that is not a docstring.
_tree = ast.parse(src)
# every docstring in the file, collected FIRST. Walking from each scope and comparing against that
# scope's own docstring does not work: the Module walk re-visits every nested function's docstring,
# where the comparison value is the MODULE docstring, so none of them get excluded.
_docs = {d for _n in ast.walk(_tree)
         if isinstance(_n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
         for d in [ast.get_docstring(_n, clean=False)] if d}
_emit = [_c.value for _c in ast.walk(_tree)
         if isinstance(_c, ast.Constant) and isinstance(_c.value, str) and _c.value not in _docs]
check("GS/MEM: no emitter can print 'nothing traded' for an unknown status",
      not [t for t in _emit if "nothing traded" in t], [t for t in _emit if "nothing traded" in t][:1])
check("and the head for an unknown status asks for a check instead",
      ex.novig_head({"status": "", "qty": 100, "filled_qty": None, "fill_read": False})
      == "NOVIG STATUS UNKNOWN - VERIFY")
check("LAC/SA: the same split applies to the live-order path, not only resting",
      src.count("The venue fill read FAILED") >= 2)

print("9. novig_reports - the emitter that actually sent the bad message")
# Nov 19: the head chain moved into novig_head(), so this is asserted on behaviour.
check("NO FILL is no longer the else branch",
      'if st in ("CANCELED", "CANCELLED", "EXPIRED") and fq_zero_proven(x):' in src
      and ex.novig_head({"status": "WEIRD", "qty": 100, "filled_qty": 0, "fill_read": True})
      == "NOVIG STATUS UNKNOWN - VERIFY")
check("an unrecognised or absent status reads STATUS UNKNOWN - VERIFY",
      '"NOVIG STATUS UNKNOWN - VERIFY"' in src)
# Implicit string concatenation across source lines again - normalise before matching.
src_flat = re.sub(r'"\s*\n\s*(f?)"', "", src)
check("the confirmed case names the venue status",
      "zero matched quantity ({st})" in src_flat and "venue confirms" in src_flat.lower())
check("the requested amount is labelled requested, never matched",
      "requested" in src and "asked; nothing traded" not in src_code)
check("an unknown status is never muted", "never muted" in src or "is the one that needs him" in src)

print("10. SAFEGUARD 1 - an attempt is never reported as acceptance")
check("the pre-call message calls itself an ATTEMPT, not a submission",
      "ORDER ATTEMPT - PENDING - TAKE on" in src and "ORDER SUBMITTED" not in src_code)
check("it says outright the venue may never have received it",
      "may never \nhave received it" in src or "may never" in src_flat)
check("acceptance is reported separately", "acceptance is reported separately below" in src_flat)
check("acceptance is gated on status placed, nothing weaker",
      'if res.get("status") == "placed":\n        try:\n            # Novig' in src)
check("and it is emitted AFTER the venue call, not before",
      src.index('_acc = "ORDER DISPATCHED') > src.index("res = book_live.novig_place("))
check("the venue id is the evidence it cites", "venue answered the order with id" in src_flat)

print("   placed does not mean the same thing at every venue")
check("the Novig runner case is split out by sent_to_runner and a missing venue id",
      '_runner = bool(res.get("sent_to_runner")) and not res.get("venue_order_id")' in src)
check("that case does NOT claim acceptance",
      "ORDER DISPATCHED - ACCEPTANCE NOT YET KNOWN" in src and "This is NOT acceptance" in src_flat)
check("Polymarket US acceptance is receipt only - that venue rewrites terms silently",
      "Acceptance is receipt only" in src_flat)

print("   FAILED is said only where non-submission is proven")
check("the refused head carries it in both venue paths",
      src.count('"ORDER FAILED - REFUSED BEFORE SUBMISSION"') >= 2)
check("FAILED is never used for any other state",
      all("REFUSED BEFORE SUBMISSION" in l for l in src.splitlines() if "ORDER FAILED" in l
          and not l.strip().startswith("#")),
      [l.strip() for l in src.splitlines() if "ORDER FAILED" in l and "REFUSED BEFORE" not in l
       and not l.strip().startswith("#")][:2])
check("an error keeps RESULT UNKNOWN - it may or may not exist at the venue",
      src.count("the order may or may not exist at the venue") >= 2
      and "ORDER ERROR" in src)

print("11. SAFEGUARD 2 - a missing fill quantity is UNKNOWN, never zero")
check("the raw quantity is tested for readability before use",
      "fq = fq_read(x)[1]" in src and "def fq_zero_proven(x)" in src)
check("and a ZERO additionally needs proof that it was read",
      ex.fq_zero_proven({"filled_qty": 0, "fill_read": True}) is True
      and ex.fq_zero_proven({"filled_qty": 0}) is False
      and ex.fq_zero_proven({"filled_qty": None, "fill_read": False}) is False)
# src_code only strips "#" lines, and the pattern also appears inside fq_read's own docstring
# explaining what it replaced - which a line test read as the pattern still being live. Strip
# comments AND string literals, so only real callers can match.
src_bare = "".join(
    ("" if tk.type in (tokenize.COMMENT, tokenize.STRING) else tk.string) + " "
    for tk in tokenize.generate_tokens(io.StringIO(src).readline))
check("the old coercion of a missing quantity to zero is gone from every CALLER",
      'int ( x . get ( "filled_qty" ) or 0 )'.replace(" ", "") not in src_bare.replace(" ", ""),
      src_bare.count("filled_qty"))
check("one shared reader, so a new caller cannot reintroduce it", "def fq_read(x)" in src)
check("it answers unknown for a missing quantity", ex.fq_read({}) == (False, 0))
check("and unknown for an unreadable one, instead of raising",
      ex.fq_read({"filled_qty": "not a number"}) == (False, 0))
check("a read zero is known-zero, which is a different thing",
      ex.fq_read({"filled_qty": 0}) == (True, 0))
check("a read quantity comes back as itself", ex.fq_read({"filled_qty": "250"}) == (True, 250))

print("   the two sites that CLAIMED a no-fill from an unreadable quantity")
# Nov 19 (PRIORITY 1): the first version of this returned the row UNCHANGED when the quantity was
# unreadable, which reported a bid whose expiry had passed as still RESTING, or dropped it in
# silence. It now produces its own unresolved state.
check("the expiry synthesiser marks an unreadable quantity unresolved rather than claiming",
      '_unresolved=True' in src and "could NOT " in src)
check("its note is the claim being guarded",
      "nothing filled as of the last read" in src_flat)
check("the report token canonicalises to NOFILL only on a READ zero",
      "if _k and not _q and st not in" in src)
check("and an unknown quantity no longer shares a token with a confirmed zero",
      "'unread'" in src and "str(q) if k else" in src)
check("NO FILL needs an authoritative cancel/expire AND a read zero",
      src.count("fq_zero_proven(x)") >= 2
      and ex.novig_head({"status": "CANCELED", "qty": 100, "filled_qty": 0, "fill_read": True})
      == "NOVIG NO FILL"
      and ex.novig_head({"status": "CANCELED", "qty": 100, "filled_qty": 0})
      == "NOVIG STATUS UNKNOWN - VERIFY")
check("the no-fill body cites the venue's own confirmation",
      "venue confirms \nzero matched quantity" in src or "venue confirms" in src_flat.lower())
check("both live-order paths require a readable filled_stake",
      src.count('if res.get("fills_read") and res.get("filled_stake") is not None:') >= 2)

print("12. SAFEGUARD 3 - the claim fails open, loudly, and never blocks a correction")
real2, log_len, en2 = ex.registry.claim_token, len(ex.LOG), ex.registry.enabled
try:
    ex.registry.claim_token, ex.registry.enabled = boom, (lambda: True)
    sent = ex.notify_once(PLAY, "FILLED", {"filled_stake": 203.50})
finally:
    ex.registry.claim_token, ex.registry.enabled = real2, en2
logged = [l for l in ex.LOG[log_len:] if "notify claim unavailable" in l]
check("an unreachable store sends rather than risking silence", sent)
check("and the failure is LOGGED as a notification-state failure", bool(logged), ex.LOG[log_len:])
check("the log names it as a notify-claim problem, not an order problem",
      bool(logged) and "notify" in logged[0] and "silence" in logged[0])

body = src.split("def notify_once")[1].split("\ndef ")[0]
for forbidden in ("put_fills", "add_bot_order", "_place(", "void_intent", "mark_handled",
                  "EXPO", "journal_order", "tg(", "push("):
    check(f"notify_once cannot touch execution or send: no {forbidden}", forbidden not in body)

print("   a seen UNKNOWN must not swallow the later FILLED")
seen = set()


def one_shot(tok):
    if tok in seen:
        return False
    seen.add(tok)
    return True


real3, real_en = ex.registry.claim_token, ex.registry.enabled
try:
    ex.registry.claim_token, ex.registry.enabled = one_shot, (lambda: True)
    u1 = ex.notify_once(PLAY, "STATUS UNKNOWN", {"order_id": "abc", "filled_stake": None})
    u2 = ex.notify_once(PLAY, "STATUS UNKNOWN", {"order_id": "abc", "filled_stake": None})
    f1 = ex.notify_once(PLAY, "FILLED", {"order_id": "abc", "filled_stake": 203.50})
    f2 = ex.notify_once(PLAY, "FILLED", {"order_id": "abc", "filled_stake": 203.50})
    p1 = ex.notify_once(PLAY, "FILLED", {"order_id": "abc", "filled_stake": 100.00})
finally:
    ex.registry.claim_token, ex.registry.enabled = real3, real_en
check("the first UNKNOWN sends", u1)
check("the repeat is suppressed", not u2)
check("the later FILLED still sends - the correction is not blocked", f1)
check("the repeated FILLED is suppressed", not f2)
check("a partial at a different amount is its own message", p1)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_telegram_sequence: all passed")
