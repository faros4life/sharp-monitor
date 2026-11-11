"""registry.py - the private-GitHub store that replaces Gmail as the bot's registry.

The property that matters most: an unreadable store must return None, never {}. An empty registry
reads as "no exposure today", which is fail-OPEN on the one guard that caps a losing day. Gmail's
bot_orders() already returns None for exactly this reason; this store must match it.

Also pinned: absent token changes nothing (so shipping before Peter creates the secret is safe),
the sha is used as an optimistic lock with retry because overlapping runs are routine here, writes
merge rather than replace, and pruning holds the window at four days.
"""
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ["REGISTRY_TOKEN"] = ""          # forced, never inherited
import registry as rg

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


def day(offset):
    return (datetime.now(timezone.utc) + timedelta(days=offset)).strftime("%Y-%m-%d")


def ts(offset):
    return (datetime.now(timezone.utc) + timedelta(days=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeAPI:
    """Stands in for the GitHub contents API. Tracks calls so locking can be asserted."""

    def __init__(self, data=None, get_status=200, put_status=201, conflicts=0, corrupt=False):
        self.data = data
        self.get_status = get_status
        self.put_status = put_status
        self.conflicts = conflicts
        self.corrupt = corrupt
        self.sha = "sha-0"
        self.puts = []
        self.gets = 0

    def __call__(self, method, url, body=None, timeout=20):
        if method == "GET":
            self.gets += 1
            if self.get_status != 200:
                return self.get_status, {}
            if self.corrupt:
                return 200, {"content": base64.b64encode(b"not json").decode(), "sha": self.sha}
            return 200, {"content": base64.b64encode(json.dumps(self.data).encode()).decode(),
                         "sha": self.sha}
        self.puts.append(body)
        if self.conflicts > 0:
            self.conflicts -= 1
            return 409, {}
        if self.put_status in (200, 201):
            self.data = json.loads(base64.b64decode(body["content"]).decode())
            self.sha = f"sha-{len(self.puts)}"
        return self.put_status, {}


def use(api, tok="t"):
    rg._call = api
    os.environ["REGISTRY_TOKEN"] = tok


# ---------------------------------------------------------------- absent token changes nothing
os.environ["REGISTRY_TOKEN"] = ""
ck("no token -> not enabled", rg.enabled(), False)
ck("no token -> load() is None, not {}", rg.load(), None)
ck("no token -> put_order is a no-op returning False", rg.put_order({"client_id": "c"}), False)
ck("no token -> put_intent False", rg.put_intent({"client_id": "c"}), False)
ck("no token -> mark_handled False", rg.mark_handled(["x"], "placed"), False)
assert "nothing changed" in rg.selftest(), rg.selftest()

# ---------------------------------------------------------------- UNREADABLE IS None, NEVER {}
for label, kw in (("a 500 is unreadable", {"get_status": 500}),
                  ("a 401 is unreadable", {"get_status": 401}),
                  ("a 403 is unreadable", {"get_status": 403}),
                  ("corrupt JSON is unreadable", {"corrupt": True})):
    use(FakeAPI(dict(rg.EMPTY), **kw))
    got = rg.load()
    ck(label, got, None)
    assert got != {}, f"{label}: returned an EMPTY registry - that reads as 'no exposure' (FAIL OPEN)"

# A transport failure (status 0) is unreadable too.
use(lambda *a, **k: (0, {}))
ck("a dead transport is unreadable", rg.load(), None)

# 404 is different and must NOT be an error: the file simply has not been created yet.
use(FakeAPI(None, get_status=404))
ck("404 means an empty store, not an unreadable one", rg.load(), dict(rg.EMPTY))

# An unreadable store must never be written over.
api = FakeAPI(dict(rg.EMPTY), get_status=500)
use(api)
ck("no write when the store cannot be read", rg.put_order({"client_id": "c1"}), False)
ck("and no PUT was attempted", len(api.puts), 0)

# ---------------------------------------------------------------- round trip
api = FakeAPI({"orders": [], "intents": [], "handled": {}})
use(api)
ck("put_order succeeds", rg.put_order(
    {"client_id": "c1", "order_id": "o1", "book": "novig", "stake": 222.0,
     "filled_stake": 222.0, "et_day": day(0), "key": "NBA|A vs B|total|UNDER"}), True)
d = rg.load()
ck("the order is stored", len(d["orders"]), 1)
ck("stake survives the round trip", d["orders"][0]["stake"], 222.0)
ck("client_id survives", d["orders"][0]["client_id"], "c1")

# Same client_id is an UPDATE, not a second row - one order's money counted once.
ck("re-recording the same order updates it", rg.put_order(
    {"client_id": "c1", "order_id": "o1", "filled_stake": 100.0, "et_day": day(0)}), True)
d = rg.load()
ck("still exactly one row for that order", len(d["orders"]), 1)
ck("the fill was updated", d["orders"][0]["filled_stake"], 100.0)
ck("and untouched fields were preserved", d["orders"][0]["book"], "novig")

# A different order appends.
rg.put_order({"client_id": "c2", "order_id": "o2", "stake": 390.0, "et_day": day(0)})
ck("a different order appends", len(rg.load()["orders"]), 2)

# Intents and their clearing.
rg.put_intent({"client_id": "c3", "book": "prophetx", "stake": 300.0, "et_day": day(0),
               "ts": ts(0), "cleared": False})
ck("the intent is stored", len(rg.load()["intents"]), 1)
ck("clear_intent succeeds", rg.clear_intent("c3"), True)
ck("the intent is marked cleared", rg.load()["intents"][0]["cleared"], True)

# Handled tokens.
rg.mark_handled(["xpidaaa", "xrtybbb"], "refused")
h = rg.load()["handled"]
ck("both tokens recorded", sorted(h), ["xpidaaa", "xrtybbb"])
ck("the outcome is recorded", h["xpidaaa"]["outcome"], "refused")

# ---------------------------------------------------------------- writes MERGE, never replace
api = FakeAPI({"orders": [{"client_id": "old", "stake": 50.0, "et_day": day(0)}],
               "intents": [], "handled": {"xpidold": {"outcome": "placed", "ts": ts(0)}}})
use(api)
rg.put_order({"client_id": "new", "stake": 60.0, "et_day": day(0)})
d = rg.load()
ck("the pre-existing order survives a write", len(d["orders"]), 2)
ck("the pre-existing handled token survives", "xpidold" in d["handled"], True)

# ---------------------------------------------------------------- optimistic locking
api = FakeAPI({"orders": [], "intents": [], "handled": {}})
use(api)
rg.put_order({"client_id": "c9", "stake": 1.0, "et_day": day(0)})
ck("the write sends the sha as a lock", api.puts[-1].get("sha"), "sha-0")

# A conflict is re-read and retried, not dropped - overlapping runs are normal here.
api = FakeAPI({"orders": [], "intents": [], "handled": {}}, conflicts=2)
use(api)
ck("two conflicts then success", rg.put_order({"client_id": "cc", "stake": 2.0, "et_day": day(0)}), True)
ck("it retried rather than giving up", len(api.puts), 3)
ck("and re-read before each retry", api.gets >= 3, True)

# Endless conflict gives up and reports failure rather than claiming a write.
api = FakeAPI({"orders": [], "intents": [], "handled": {}}, conflicts=99)
use(api)
ck("endless conflict -> False", rg.put_order({"client_id": "cx", "stake": 3.0, "et_day": day(0)}), False)

# A non-conflict PUT error is not retried and must not claim success.
api = FakeAPI({"orders": [], "intents": [], "handled": {}}, put_status=403)
use(api)
ck("a 403 on write -> False", rg.put_order({"client_id": "cy", "stake": 4.0, "et_day": day(0)}), False)
ck("and it did not retry a hard failure", len(api.puts), 1)

# ---------------------------------------------------------------- the 4-day window
ck("the window is four days, matching bot_orders on Gmail", rg.KEEP_DAYS, 4)
api = FakeAPI({"orders": [{"client_id": "fresh", "et_day": day(0)},
                          {"client_id": "edge", "et_day": day(-3)},
                          {"client_id": "stale", "et_day": day(-9)}],
               "intents": [{"client_id": "oldi", "et_day": day(-9)}],
               "handled": {"xkeep": {"outcome": "placed", "ts": ts(0)},
                           "xdrop": {"outcome": "placed", "ts": ts(-9)}}})
use(api)
d = rg.load()
ck("rows inside the window are kept", sorted(o["client_id"] for o in d["orders"]), ["edge", "fresh"])
ck("stale intents are pruned", d["intents"], [])
ck("handled tokens are pruned by ts", sorted(d["handled"]), ["xkeep"])
assert all(o["client_id"] != "stale" for o in d["orders"]), "a row outside the window must be pruned"

# ---------------------------------------------------------------- the store cannot bet
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.py")).read()
for bad in ("place(", "novig_place", "kalshi_place", "pmus_place", "px_live", "order/"):
    assert bad not in src, f"registry.py must be a store, not an order path - found {bad!r}"
CHECKS.append(("registry.py contains no order path", True, True))

# selftest reports rather than raising, whatever the store does.
use(FakeAPI(dict(rg.EMPTY), get_status=500))
assert "UNREADABLE" in rg.selftest()
use(FakeAPI({"orders": [], "intents": [], "handled": {}}))
out = rg.selftest()
assert "read-back ok" in out and "write ok" in out, out
CHECKS.append(("selftest reports a real round trip", "ok", "ok"))

print(f"PASS  test_registry.py  {len(CHECKS)} checks")
