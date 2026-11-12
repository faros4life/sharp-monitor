#!/usr/bin/env python3
"""Write-ahead intents must not latch when the order was never transmitted (Peter/Muse, Nov 12).

READ-ONLY and offline: no network, no Gmail, no venue, NO ORDERS. registry.put_rows and
executor.send are replaced in-process; everything else under test is the real code - the real
_account_rows() routing, the real _bot_orders_finish() latch loop, the real refuse_untransmitted(),
and the real book_live place functions' refusal ordering.

The defect: journal_intent() runs before the book dispatch, so a PRE-SUBMISSION refusal
(EXEC_NOVIG_SUBMIT off, short ladder, unknown market) left an unconfirmed intent that latched every
further live order until Peter cleared it by hand. Two plays were lost to it on Nov 12.

Covers: a refusal voids its intent; a voided intent does not latch; an unvoided intent still does;
status == "error" is NOT voided and still latches; a confirmed order is unaffected; and the
never-transmitted claim is checked against the real source of each place function.
"""
import inspect
import json
import os
import sys

os.environ.setdefault("EXEC_LIVE", "off")

import book_live
import executor as ex
import px_live
import registry

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


# ---------------------------------------------------------------- in-process fakes
SENT, PUT, TG = [], [], []
ex.send = lambda subj, body: SENT.append((subj, body))
ex.tg = lambda *a, **k: TG.append(a[0] if a else "")
ex.push = lambda *a, **k: None
registry.enabled = lambda: True
registry.put_rows = lambda rows: (PUT.extend(rows), True)[1]
# authorized_senders() reads the Gmail credentials, which this offline test deliberately lacks.
# Note it raises SystemExit, not Exception - the same pre-existing shape intent_cleared() has.
ex.authorized_senders = lambda: ("pgoranites@gmail.com",)


def play(book="novig", cid="cid0000000000beef"):
    return {"play": {"sport": "NBA", "game": "Charlotte vs Phoenix: Total Points",
                     "bet": "Under 214.5", "play_key": "board|NBA|Charlotte vs Phoenix: Total Points|total|UNDER",
                     "source": "board"},
            "live": {"book": book, "client_id": cid, "line": 214.5, "risk": 200.0,
                     "px": {"buy": [], "thr": None}, "ids": {}}}


def intent_row(cid, voided=False, status="placed"):
    lo = {"status": status, "order_id": "intent-" + cid, "book": "novig",
          "client_id": cid, "intent": True, "asked_stake": 200.0, "filled_stake": None}
    if voided:
        lo["voided"] = True
    row = {"key": "board|NBA|Charlotte vs Phoenix: Total Points|total|UNDER", "source": "board",
           "intent": True, "client_id": cid, "decided_utc": "2026-11-12T17:35:28Z", "live_order": lo}
    if voided:
        row["voided"] = True
    return row


def confirmed_row(cid):
    return {"key": "k", "source": "board", "client_id": cid, "decided_utc": "2026-11-12T17:35:28Z",
            "live_order": {"status": "placed", "order_id": "nv-real-1", "book": "novig",
                           "client_id": cid, "asked_stake": 200.0, "filled_stake": 200.0}}


def route(rows):
    """Run the REAL _account_rows and report which bucket each client_id landed in."""
    ids, seen, _int, _conf = {}, set(), {}, {}
    ex.BOARD.update({"risk": 0.0, "keys": set(), "known": False})
    try:
        ex._account_rows(rows, {}, ids, seen, _int, _conf)
    except Exception as e:          # accounting side-effects are not under test here
        print(f"  (note: _account_rows raised {type(e).__name__}: {str(e)[:60]})")
    return set(_int), set(_conf)


def latched(rows):
    """Run the REAL _bot_orders_finish and report the client_ids left latching live orders."""
    _int, _conf = route(rows)
    ex.intent_cleared = lambda M, cid: False       # no manual clearance in play
    ex.subject_hits = lambda M, n, p, **k: False   # and no mailbox to read
    ex._bot_orders_finish(None, {}, {k: intent_row(k) if k not in _conf else confirmed_row(k)
                                    for k in _int}, {k: True for k in _conf})
    return set(ex.INTENT["open"])


print("1. a PRE-SUBMISSION refusal voids its own intent")
print("=" * 78)
SENT.clear(); PUT.clear()
out = ex.refuse_untransmitted(play(), "Novig submissions are paused (EXEC_NOVIG_SUBMIT is not on)", book="novig")
ck("refusal still returned", out.get("status"), "refused")
ck("void row written to the store", len(PUT), 1)
ck("void row carries voided=True", bool(PUT and PUT[0]["live_order"].get("voided")), True)
ck("void row keeps the client_id", PUT and PUT[0]["live_order"].get("client_id"), "cid0000000000beef")
ck("void row is not counted as money", PUT and PUT[0]["live_order"].get("asked_stake"), 0.0)
# Nov 12 (Peter, "remove routine execution emails"): the VOID email is sent ONLY when the store
# write failed, because then the mailbox copy is the only record of the resolution. With the store
# confirming - the case above - there is nothing for an email to add.
ck("NO void email when the store confirmed the write",
   sum(1 for s, _ in SENT if s.startswith(ex.INTENT_VOID_PREFIX)), 0)
_put_ok, PUT2 = registry.put_rows, []
registry.put_rows = lambda rows: False          # store write fails
SENT.clear()
ex.void_intent("cid00000000store1", "novig", "EXEC_NOVIG_SUBMIT is not on")
_vs = [s for s, _ in SENT if s.startswith(ex.INTENT_VOID_PREFIX)]
ck("void email IS sent when the store failed", len(_vs), 1)
ck("VOID subject names the client_id", bool(_vs and "cid00000000store1" in _vs[0]), True)
registry.put_rows = _put_ok
ck("VOID is not the manual clearance subject",
   any(s.startswith(ex.INTENT_CLEAR_PREFIX) for s, _ in SENT), False)

print()
print("2. a voided intent does NOT latch; an unvoided one still does")
print("=" * 78)
ck("unvoided intent latches (unchanged)", latched([intent_row("aaa1")]), {"aaa1"})
ck("voided intent does not latch", latched([intent_row("bbb2", voided=True)]), set())
ck("confirmed order does not latch", latched([confirmed_row("ccc3")]), set())
ck("voided alongside unvoided: only the unvoided latches",
   latched([intent_row("ddd4", voided=True), intent_row("eee5")]), {"eee5"})
_i, _c = route([intent_row("fff6", voided=True)])
ck("voided intent is routed to _confirmed, not _intents", (_i, _c), (set(), {"fff6"}))

print()
print("3. status == 'error' must NOT be voided - the request may have reached the venue")
print("=" * 78)
src = inspect.getsource(ex.live_order_other)
_refused_block = src.split('if res.get("status") == "refused"')[1].split("\n    if ")[0]
ck("live_order_other voids inside its 'refused' branch", "void_intent(" in _refused_block, True)
_after_error = src.split('"status"] == "error"')[-1]
ck("live_order_other does NOT void on 'error'", "void_intent" in _after_error, False)
ck("the refusal notification stays deduped by refusal_first", "refusal_first(" in src, True)
SENT.clear(); PUT.clear()
ex.void_intent("", "novig", "no client id")
ck("void with no client_id writes nothing", (len(PUT), len(SENT)), (0, 0))

print()
print("4. the never-transmitted claim, checked against each place function's real source")
print("=" * 78)
for name, fn, post in (("novig_place", book_live.novig_place, "_gh("),
                       ("kalshi_place", book_live.kalshi_place, "_k_call("),
                       ("pmus_place", book_live.pmus_place, "_pm_call("),
                       ("px_live.place", px_live.place, "_call(")):
    body = inspect.getsource(fn)
    first_post = body.find(post)
    refusals = [i for i in range(len(body)) if body.startswith('"status": "refused"', i)]
    ck(f"{name}: every 'refused' precedes its first {post}",
       bool(refusals) and first_post > 0 and max(refusals) < first_post, True)

print()
print("5. the voiding refusal is used at every pre-submission site, and nowhere else")
print("=" * 78)
whole = open("executor.py").read()
for site in ("ladder can't cover", "Kalshi market ambiguous", "Polymarket US market unknown",
             "Novig outcome unknown", "no live order code"):
    seg = [ln for ln in whole.splitlines() if site in ln and "return refuse" in ln]
    ck(f"voided at: {site}", bool(seg) and all("refuse_untransmitted" in ln for ln in seg), True)
ck("refuse() itself never voids", "void_intent" not in inspect.getsource(ex.refuse), True)

print()
print("=" * 78)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAILED: " + b)
sys.exit(1 if BAD else 0)
