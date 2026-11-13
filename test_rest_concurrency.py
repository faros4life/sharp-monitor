#!/usr/bin/env python3
"""CONCURRENT executor runs cannot both post the same resting bid (Peter, Nov 13).

Real threads against one shared store with the real optimistic sha lock - not sequential calls.

THE PROVEN RACE this closes: two overlapping runs on the same resting-only play both reached
rest_bid(). Neither had written a registry order, so LIVEKEYS was empty in both, rest_wanted()
returned True in both, and rest_bid() made NO registry call across its 117 lines. Both posted.

No venue is contacted, no order placed, no real network call made.
"""
import base64
import json
import sys
import threading

import registry as rg

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


STORE = {"blob": None, "sha": None}
LOCK = threading.Lock()
PUTS = {"n": 0}


def fake_call(method, url, body=None, timeout=20):
    with LOCK:                       # the contents API serialises writes to one file
        if method == "GET":
            if STORE["blob"] is None:
                return 404, {}
            return 200, {"content": base64.b64encode(STORE["blob"]).decode(), "sha": STORE["sha"]}
        if method == "PUT":
            if STORE["sha"] and body.get("sha") != STORE["sha"]:
                return 409, {}       # the real sha lock: a stale writer is rejected and retries
            STORE["blob"] = base64.b64decode(body["content"])
            PUTS["n"] += 1
            STORE["sha"] = f"sha{PUTS['n']}"
            return 200, {}
    return 0, {}


rg._call, rg.enabled = fake_call, lambda: True
KEY = "NBA|Utah vs Houston: Total Points|total|OVER"


def reset():
    STORE["blob"], STORE["sha"] = None, None


def race(fn, n=2):
    """Run fn(name) in n threads released simultaneously; return {name: result}."""
    out, barrier = {}, threading.Barrier(n)

    def wrap(nm):
        barrier.wait()
        try:
            out[nm] = fn(nm)
        except Exception as ex:
            out[nm] = f"RAISED {type(ex).__name__}"
    ts = [threading.Thread(target=wrap, args=(f"run{i}",)) for i in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return out


print("1. Two concurrent runs, resting-only, neither has written an order")
reset()
out = race(lambda nm: rg.claim_submission(KEY + "|rest", "rest-" + nm))
for k, v in sorted(out.items()):
    print(f"    {k}: claim -> {v}")
check("exactly one run wins the resting claim", sum(1 for v in out.values() if v is True) == 1)
check("the other is refused, not raised", sum(1 for v in out.values() if v is False) == 1)

print("\n2. Five concurrent runs - still exactly one")
reset()
out = race(lambda nm: rg.claim_submission(KEY + "|rest", "rest-" + nm), n=5)
check("exactly one of five wins", sum(1 for v in out.values() if v is True) == 1)
check("four are cleanly refused", sum(1 for v in out.values() if v is False) == 4)

print("\n3. The TAKE + POST sequence is NOT blocked by its own immediate claim")
reset()
check("the run wins its immediate claim", rg.claim_submission(KEY, "cid-A") is True)
check("...and still wins its own resting claim (separate |rest key)",
      rg.claim_submission(KEY + "|rest", "rest-A") is True)

print("\n4. Requirement 4: a separate key alone must NOT allow exceeding the stake")
# run A holds the IMMEDIATE claim (it is taking part of the stake). Run B is resting-only.
held = rg.submission_held(KEY)
check("the immediate claim is readable without taking it", held is not None and held.get("cid") == "cid-A")
check("a resting-only run sees a cid that is not its own", held.get("cid") != "")
check("so rest_bid refuses while another run's fill is unknown",
      held.get("cid") not in ("", "rest-B"))
check("reading a claim never creates one", rg.submission_held("never|seen|key") is None)

print("\n5. Fail closed when the store cannot be read")
_real = rg.load
rg.load = lambda: None
raised = False
try:
    rg.submission_held(KEY)
except Exception:
    raised = True
check("submission_held RAISES on an unreadable store", raised)
rg.load = _real

print("\n6. A claim is released ONLY on proof nothing was sent")
reset()
check("claim taken", rg.claim_submission(KEY + "|rest", "rest-A") is True)
rg.release_submission(KEY + "|rest", "rest-A")
check("after a release the key is free again", rg.submission_held(KEY + "|rest") is None)
check("and the next run may claim it", rg.claim_submission(KEY + "|rest", "rest-B") is True)
check("a held claim blocks a different run", rg.claim_submission(KEY + "|rest", "rest-C") is False)

print("\n7. The production path wires all of this in, before any dispatch")
src = open("executor.py").read()
i_claim = src.find('registry.claim_submission(_rkey, REST_CID)')
i_held = src.find("registry.submission_held(_pkey)")
i_loop = src.find("    for b in REST_BOOKS:")
check("rest_bid reads the immediate claim first", 0 < i_held < i_claim)
check("then takes the resting claim", 0 < i_claim < i_loop)
check("both happen BEFORE the venue loop", i_claim < i_loop)
check("a disabled registry refuses rather than posting unprotected",
      "no durable store for the resting submission claim" in src)
check("the release sits on the all-refused exit only",
      src.find("registry.release_submission(_rkey, REST_CID)") > i_loop)
check("every enabled resting venue shares that one path", 'for b in REST_BOOKS:' in src)
check("and all three lanes reach it through the same branch", "if rest_wanted(r):" in src)

print()
if fails:
    print(f"FAIL  test_rest_concurrency.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")
