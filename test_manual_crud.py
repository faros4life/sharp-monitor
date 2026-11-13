#!/usr/bin/env python3
"""Step 1 (Peter, Nov 12): manual-note ADD, EDIT and DELETE against the registry, using ISOLATED
SYNTHETIC records only. No real hold, note, order or store is touched.

The whole GitHub transport is replaced by an in-memory dict, so put_manual(), _commit(), _prune()
and load() all run for real against a fake file. Nothing leaves this process.

DELETE is the case that matters. put_manual() is a WHOLE-WINDOW SNAPSHOT and deliberately not an
upsert: a manual note carries no id, and Peter can correct or remove one. An upsert would make a
deleted note immortal - the bot would keep refusing a bet he is no longer on, or worse, keep
believing a hold that he cleared. An ADD-only test cannot see that, which is why it is here.
"""
import base64
import json
import sys

import registry as rg

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- in-memory GitHub, no network
STORE = {"blob": None, "sha": None, "puts": 0}


def fake_call(method, url, body=None, timeout=20):
    if method == "GET":
        if STORE["blob"] is None:
            return 404, {}
        return 200, {"content": base64.b64encode(STORE["blob"]).decode(), "sha": STORE["sha"]}
    if method == "PUT":
        if STORE["sha"] and body.get("sha") != STORE["sha"]:
            return 409, {}            # the real optimistic lock, exercised
        STORE["blob"] = base64.b64decode(body["content"])
        STORE["puts"] += 1
        STORE["sha"] = f"sha{STORE['puts']}"
        return 200, {}
    return 0, {}


_orig_call, _orig_enabled = rg._call, rg.enabled
rg._call, rg.enabled = fake_call, lambda: True


def note(game, bet, book="Hard Rock", sport="NBA"):
    return {"sport": sport, "game": game, "bet": bet, "book": book}


def held():
    """Replay the stored window through the executor's own accounting."""
    import executor as ex
    out = {}
    stored = rg.manual_notes()
    if stored is None:
        return None
    for n in stored:
        ex._apply_manual(n, out)
    return out


A = note("Boston @ Miami", "Under 215.5 (-110)")
B = note("Denver @ Phoenix", "Denver +3.5 (-110)")
C = note("Dallas @ Houston", "Houston ML (+130)")

print("ADD")
check("an empty store starts empty, not unreadable", rg.manual_notes() == [])
check("writing two notes succeeds", rg.put_manual([A, B]) is True)
check("both come back", len(rg.manual_notes() or []) == 2)
h1 = held()
check("both produce holds", h1 is not None and len(h1) >= 2)

print("\nADD a third")
check("writing three succeeds", rg.put_manual([A, B, C]) is True)
check("all three stored", len(rg.manual_notes() or []) == 3)
h2 = held()
check("the third adds its own hold", len(h2) > len(h1))

print("\nEDIT the second (same game, corrected side)")
B2 = note("Denver @ Phoenix", "Phoenix -3.5 (-110)")
check("writing the corrected window succeeds", rg.put_manual([A, B2, C]) is True)
stored = rg.manual_notes() or []
check("the stored note is the corrected one", any(n.get("bet") == "Phoenix -3.5 (-110)" for n in stored))
check("and the superseded text is GONE, not kept alongside",
      not any(n.get("bet") == "Denver +3.5 (-110)" for n in stored))

print("\nDELETE the third - the case an upsert would get wrong")
check("writing the shorter window succeeds", rg.put_manual([A, B2]) is True)
stored = rg.manual_notes() or []
check("only two notes remain", len(stored) == 2)
check("the deleted note is absent", not any(n.get("game") == "Dallas @ Houston" for n in stored))
h3 = held()
check("its hold is released too, not immortal",
      all("Dallas" not in k and "Houston" not in k for k in (h3 or {})))

print("\nDELETE everything")
check("an empty window is writable", rg.put_manual([]) is True)
check("no notes remain", rg.manual_notes() == [])
check("and no holds remain", held() == {})

print("\nFAIL CLOSED: an unreadable store is never an empty window")
rg._call = lambda *a, **k: (500, {})
check("manual_notes() is None, not []", rg.manual_notes() is None)
check("held replay refuses rather than returning {}", held() is None)
check("put_manual() refuses to overwrite what it cannot read", rg.put_manual([A]) is False)
check("manual_complete() is False", rg.manual_complete() is False)
rg._call = fake_call

print("\nA PARTIAL window must never be stored as if complete")
check("invalidate_manual() is available to the mirror", callable(rg.invalidate_manual))
rg.put_manual([A, B2])
rg.set_manual_complete()
check("a fresh claim reads complete", rg.manual_complete() is True)
rg.invalidate_manual()
check("after invalidation it does not", rg.manual_complete() is False)

rg._call, rg.enabled = _orig_call, _orig_enabled

print()
if fails:
    print(f"FAIL  test_manual_crud.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
