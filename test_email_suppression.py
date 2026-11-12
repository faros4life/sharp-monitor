#!/usr/bin/env python3
"""Routine execution emails are suppressed ONLY when the store confirmed the row (Peter, Nov 12).

OFFLINE. NO ORDERS. NO NETWORK. NO EMAIL. registry and send() are replaced in-process; the code
under test is the real journal_intent(), void_intent() and bot_orders() fallback.

Peter: "Verify the registry read-back before removing each email dependency. Do not remove any
email still required for authorization, reconciliation, or duplicate protection."

The invariant being protected, which is NOT obvious: is_complete()'s own docstring rests on "the
next run is back on Gmail, which is always complete." That was true only because every durable row
was also emailed. So the three properties here are inseparable:

  1 store confirms  -> NO email, and Gmail is marked no longer authoritative
  2 store fails     -> email IS sent, and it is the record the read-back then checks
  3 store unreadable AND Gmail not authoritative -> bot_orders() returns None, live refuses

Drop any one and the result is a duplicate bet or an undercounted daily stop, so each is asserted
here rather than argued for in a comment.

INTENT CLEARED is untouched: it is authorization, it stays in email, and no test here sends one.
"""
import json
import os
import re
import sys

os.environ.setdefault("EXEC_LIVE", "off")

import executor as ex
import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


SENT, PUT, MARKED = [], [], []
ex.send = lambda s, b: SENT.append(s)
ex.tg = lambda *a, **k: None
ex.push = lambda *a, **k: None
registry.enabled = lambda: True
registry.set_gmail_incomplete = lambda: (MARKED.append(1), True)[1]
# Nov 12: journal_intent() now takes an ATOMIC SUBMISSION CLAIM before writing the intent, and
# refuses outright if it cannot win one. That precondition is tested on its own in
# test_submission_claim.py; here it is granted so these assertions stay about the EMAIL rule.
CLAIMS = []
registry.claim_submission = lambda key, cid: (CLAIMS.append((key, cid)), True)[1]
registry.release_submission = lambda key, cid: True


def play(cid="cidbeef0000000001", book="novig"):
    return {"play": {"sport": "NBA", "game": "Charlotte vs Phoenix: Total Points",
                     "bet": "Under 214.5", "play_key": "board|NBA|CHA v PHX|total|UNDER",
                     "source": "board"},
            "live": {"book": book, "client_id": cid, "line": 214.5, "risk": 200.0,
                     "px": {"buy": [], "thr": None}, "ids": {}}}


def reset():
    SENT.clear(); PUT.clear(); MARKED.clear()


print("1. STORE CONFIRMS -> no intent email, and Gmail marked no longer authoritative")
print("=" * 82)
reset()
ex.intent_verified = lambda cid, row: (True, "private store")
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("the intent is accepted", ok, True)
ck("a client_id is returned", bool(cid), True)
ck("NO intent email was sent", [s for s in SENT if s.startswith(ex.INTENT_SUBJECT_PREFIX)], [])
ck("Gmail marked no longer authoritative", len(MARKED), 1)

print()
print("2. STORE FAILS -> the intent email IS sent, because it is then the only record")
print("=" * 82)
reset()
ex.intent_verified = lambda cid, row: (False, "Gmail")
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("no order may be submitted", ok, False)
ck("the intent email WAS sent", len([s for s in SENT if s.startswith(ex.INTENT_SUBJECT_PREFIX)]), 1)
ck("Gmail NOT marked incomplete (it holds the row)", len(MARKED), 0)

reset()
ex.intent_verified = lambda cid, row: (True, "Gmail")   # store missed it, mailbox answered
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("store missed but Gmail confirmed: accepted", ok, True)
ck("the email was sent in that case too", len([s for s in SENT if s.startswith(ex.INTENT_SUBJECT_PREFIX)]), 1)
ck("Gmail still authoritative", len(MARKED), 0)

print()
print("3. VOID follows the same rule")
print("=" * 82)
reset()
registry.put_rows = lambda rows: (PUT.extend(rows), True)[1]
ex.void_intent("cid000000000void1", "novig", "EXEC_NOVIG_SUBMIT is not on")
ck("void written to the store", len(PUT), 1)
ck("NO void email when the store confirmed", [s for s in SENT if s.startswith(ex.INTENT_VOID_PREFIX)], [])
ck("Gmail marked no longer authoritative", len(MARKED), 1)

reset()
registry.put_rows = lambda rows: False          # store write failed
ex.void_intent("cid000000000void2", "novig", "ladder short")
ck("void email sent when the store failed", len([s for s in SENT if s.startswith(ex.INTENT_VOID_PREFIX)]), 1)
ck("Gmail NOT marked incomplete", len(MARKED), 0)

print()
print("4. THE GUARD: store unreadable AND Gmail not authoritative -> bot_orders FAILS CLOSED")
print("=" * 82)
src = __import__("inspect").getsource(ex.bot_orders)
ck("the fallback consults gmail_authoritative()", "gmail_authoritative()" in src, True)
ck("and returns None rather than reading an incomplete mailbox",
   "FAILING CLOSED" in src and "return None" in src.split("gmail_authoritative()")[1][:600], True)
ck("an exception in that check also fails closed",
   "_gmail_ok = False" in src, True)
# registry.gmail_authoritative itself must answer False when the store cannot be read at all.
import inspect as _i
gsrc = _i.getsource(registry.gmail_authoritative)
ck("unreadable store -> not authoritative", "if d is None:" in gsrc and "return False" in gsrc, True)
ck("default is True, so nothing changes until a row is registry-only",
   'get("gmail_complete", True)' in gsrc, True)
_assigns = re.findall(r'\["gmail_complete"\]\s*=\s*(\w+)', open(registry.__file__).read())
ck("every assignment to the marker sets it False, never back to True",
   (bool(_assigns), set(_assigns)), (True, {"False"}))

print()
print("5. AUTHORIZATION email is untouched")
print("=" * 82)
ck("INTENT CLEARED is still the manual, subject-only authorization",
   ex.INTENT_CLEAR_PREFIX == "INTENT CLEARED", True)
ck("the bot never sends that subject",
   "INTENT_CLEAR_PREFIX" not in _i.getsource(ex.journal_intent)
   and "INTENT_CLEAR_PREFIX" not in _i.getsource(ex.void_intent), True)
ck("intent_cleared still requires an authorized sender",
   "authorized_senders()" in _i.getsource(ex.intent_cleared), True)

print()
print("=" * 82)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
