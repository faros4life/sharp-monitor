#!/usr/bin/env python3
"""Every write-ahead record reaches BOTH stores (Peter, Nov 12 - GO on the revert). OFFLINE.

This file previously tested the opposite rule. On Nov 12 journal_intent() and void_intent() were
changed to email the record ONLY when the private store could not confirm it, and that suppression
was paid for with registry.gmail_authoritative(): a guard that answered False when the store was
merely UNREADABLE, so any registry outage stopped live betting outright. Muse's
test_registry_migration caught it - "an unreadable store falls back to Gmail".

The trade was wrong. Intent and void emails are about five a day; the volume is the end-of-run
ledger email. A fail-closed landmine was spent on a rounding error. Peter gave GO on the revert,
so the rule under test is now the original one:

    BOTH stores receive the row, always. The store makes the read-back fast; Gmail keeps the
    fallback complete, which is what is_complete()'s invariant already assumes in writing -
    "the next run is back on Gmail, which is always complete."

What this file now guards against is the suppression coming back by accident: if the email becomes
conditional again, or the fail-closed guard reappears in bot_orders()'s fallback, these fail.

The atomic submission claim is NOT under test here - that is test_submission_claim.py - so it is
granted, because without it journal_intent() correctly refuses before reaching any email at all.
"""
import inspect
import re
import sys

import executor as ex
import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


SENT, PUT, CLAIMS = [], [], []
ex.send = lambda s, b: SENT.append(s)
ex.tg = lambda *a, **k: None
ex.tg_push = lambda *a, **k: None
ex.push = lambda *a, **k: None
registry.enabled = lambda: True
registry.put_rows = lambda rows: (PUT.extend(rows), True)[1]
registry.claim_submission = lambda key, cid: (CLAIMS.append((key, cid)), True)[1]
registry.release_submission = lambda key, cid: True


def play(cid="cidbeef0000000001"):
    return {"play": {"sport": "NBA", "game": "Charlotte vs Phoenix: Total Points",
                     "bet": "Under 214.5", "play_key": "board|NBA|CHA v PHX|total|UNDER",
                     "source": "board"},
            "live": {"book": "novig", "client_id": cid, "line": 214.5, "risk": 200.0,
                     "px": {"buy": [], "thr": None}, "ids": {}}}


def reset():
    SENT.clear(); PUT.clear(); CLAIMS.clear()


def intents():
    return [s for s in SENT if s.startswith(ex.INTENT_SUBJECT_PREFIX)
            and not s.startswith(ex.INTENT_VOID_PREFIX)]


def voids():
    return [s for s in SENT if s.startswith(ex.INTENT_VOID_PREFIX)]


print("1. the intent email is sent whether or not the store confirms")
print("=" * 86)
reset()
ex.intent_verified = lambda cid, row: (True, "private store")
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("store confirmed: accepted", ok, True)
ck("store confirmed: the email STILL went", len(intents()), 1)
ck("the claim was taken first", len(CLAIMS), 1)

reset()
ex.intent_verified = lambda cid, row: (True, "Gmail")
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("store missed, Gmail answered: accepted", ok, True)
ck("the email went", len(intents()), 1)

reset()
ex.intent_verified = lambda cid, row: (False, "Gmail")
ok, cid = ex.journal_intent(play(), "novig", 200.0)
ck("neither store confirmed: NO submission", (ok, cid), (False, None))
ck("the email still went, so the record is not lost", len(intents()), 1)

print()
print("2. the void email is sent whether or not the store write succeeds")
print("=" * 86)
reset()
registry.put_rows = lambda rows: (PUT.extend(rows), True)[1]
ex.void_intent("cid00000000void01", "novig", "EXEC_NOVIG_SUBMIT is not on", key="board|NBA|X|total|UNDER")
ck("store write ok: the void email STILL went", len(voids()), 1)
ck("and the void row was stored too", len(PUT), 1)

reset()
registry.put_rows = lambda rows: False
ex.void_intent("cid00000000void02", "novig", "ladder short", key="board|NBA|X|total|UNDER")
ck("store write failed: the void email went", len(voids()), 1)
registry.put_rows = lambda rows: (PUT.extend(rows), True)[1]

print()
print("3. the suppression cannot come back by accident")
print("=" * 86)
jsrc = inspect.getsource(ex.journal_intent)
vsrc = inspect.getsource(ex.void_intent)
ck("journal_intent does not mark Gmail incomplete", "set_gmail_incomplete" in jsrc, False)
ck("void_intent does not mark Gmail incomplete", "set_gmail_incomplete" in vsrc, False)
ck("the registry no longer offers that marker at all",
   hasattr(registry, "set_gmail_incomplete") or hasattr(registry, "gmail_authoritative"), False)
# The email send must not sit behind a conditional on the store's answer. intent_verified() is
# called AFTER the send, so a send that appears before it cannot be gated on its result.
_i_send = jsrc.find("send(f\"{INTENT_SUBJECT_PREFIX}")
_i_ver = jsrc.find("intent_verified(cid, row)")
ck("the intent email precedes the read-back, so it cannot be gated on it",
   0 <= _i_send < _i_ver, True)

print()
print("4. bot_orders falls back to Gmail again, with no fail-closed guard")
print("=" * 86)
bsrc = inspect.getsource(ex.bot_orders)
ck("no gmail_authoritative() call in the fallback",
   bool(re.search(r"registry\.gmail_authoritative\(\)", bsrc)), False)
ck("no FAILING CLOSED branch there", "FAILING CLOSED" in bsrc, False)
ck("the Gmail IMAP read is still reachable", 'SUBJECT", \'"Bets LIVE:"\'' in bsrc, True)

print()
print("5. the authorization email is untouched, as always")
print("=" * 86)
ck("INTENT CLEARED is still the manual, subject-only authorization",
   ex.INTENT_CLEAR_PREFIX, "INTENT CLEARED")
ck("the bot never emits that subject",
   "INTENT_CLEAR_PREFIX" in jsrc or "INTENT_CLEAR_PREFIX" in vsrc, False)
ck("intent_cleared still requires an authorized sender",
   "authorized_senders()" in inspect.getsource(ex.intent_cleared), True)

print()
print("=" * 86)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
