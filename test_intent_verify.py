"""intent_verified(): durable pre-order read-back from the private store, Gmail as fallback.

intent_readable() opened a FRESH IMAP connection per try and slept 5s between up to 3 tries, PER
ORDER, because Gmail's index lags its own SMTP. A contents PUT returns only on a confirmed commit
and a GET reads the row straight back - 0.33s measured, against 114.2s for the Gmail registry read.

THE RULE MUST NOT WEAKEN: no order is submitted until its pre-order record has been read back out of
a durable store. These tests check which store answers, and that NEITHER answering means no order.
"""
import json
import os
from datetime import datetime, timezone

os.environ["REGISTRY_TOKEN"] = ""
import executor as ex
import registry as rg

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def intent_row(cid):
    return {"key": "NCAAB|A @ B|side|A", "source": "r1", "decided_utc": NOW,
            "live_order": {"status": "placed", "order_id": None, "book": "novig",
                           "asked_stake": 222.0, "client_id": cid, "intent": True}}


class FakeAPI:
    def __init__(self, put_status=201, get_status=200):
        self.data = dict(rg.EMPTY)
        self.put_status = put_status
        self.get_status = get_status
        self.sha = "s0"
        self.puts = 0

    def __call__(self, method, url, body=None, timeout=20):
        import base64
        if method == "GET":
            if self.get_status != 200:
                return self.get_status, {}
            return 200, {"content": base64.b64encode(json.dumps(self.data).encode()).decode(),
                         "sha": self.sha}
        self.puts += 1
        if self.put_status not in (200, 201):
            return self.put_status, {}
        self.data = json.loads(base64.b64decode(body["content"]).decode())
        self.sha = f"s{self.puts}"
        return 201, {}


# Gmail fallback instrumented: counts calls and proves no sleeping happened on the store path.
calls = {"gmail": 0}
_readable, _sleep = ex.intent_readable, ex.time.sleep
slept = {"n": 0}


def fake_readable(cid, tries=3, wait=5):
    calls["gmail"] += 1
    return calls.get("answer", False)


try:
    ex.intent_readable = fake_readable
    ex.time.sleep = lambda s: slept.__setitem__("n", slept["n"] + 1)

    # ---------------------------------------------------------------- no token: Gmail, unchanged
    os.environ["REGISTRY_TOKEN"] = ""
    calls["answer"] = True
    ok, where = ex.intent_verified("c1", intent_row("c1"))
    ck("no token -> verified via Gmail", (ok, where), (True, "Gmail"))
    ck("Gmail was consulted", calls["gmail"], 1)

    calls["answer"] = False
    ok, where = ex.intent_verified("c1", intent_row("c1"))
    ck("no token and Gmail cannot read it back -> NOT verified", ok, False)

    # ---------------------------------------------------------------- store path, no Gmail at all
    api = FakeAPI()
    rg._call = api
    os.environ["REGISTRY_TOKEN"] = "t"
    calls["gmail"] = 0
    slept["n"] = 0
    calls["answer"] = False          # Gmail would say NO; the store must answer YES on its own
    ok, where = ex.intent_verified("c2", intent_row("c2"))
    ck("store verifies the intent", (ok, where), (True, "private store"))
    ck("Gmail was NOT consulted", calls["gmail"], 0)
    ck("and nothing slept", slept["n"], 0)
    ck("the row is actually in the store", len(api.data.get("orders") or []), 1)
    ck("stored as an intent", (api.data["orders"][0]["live_order"]).get("intent"), True)

    # ---------------------------------------------------------------- store writes but row absent
    # A PUT that reports success while the row is not readable back must NOT pass on the store.
    api2 = FakeAPI()
    rg._call = api2
    calls["gmail"] = 0
    calls["answer"] = True
    ok, where = ex.intent_verified("c3", intent_row("cOTHER"))   # row carries a different cid
    ck("a row that reads back under another id falls through to Gmail", where, "Gmail")
    ck("Gmail was consulted for it", calls["gmail"], 1)

    # ---------------------------------------------------------------- store broken -> Gmail
    rg._call = FakeAPI(put_status=403)
    calls["gmail"] = 0
    calls["answer"] = True
    ok, where = ex.intent_verified("c4", intent_row("c4"))
    ck("a failed store write falls back to Gmail", (ok, where), (True, "Gmail"))
    ck("Gmail answered", calls["gmail"], 1)

    rg._call = FakeAPI(get_status=500)
    calls["gmail"] = 0
    calls["answer"] = True
    ok, where = ex.intent_verified("c5", intent_row("c5"))
    ck("an unreadable store falls back to Gmail", where, "Gmail")

    rg._call = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    calls["gmail"] = 0
    calls["answer"] = True
    ok, where = ex.intent_verified("c6", intent_row("c6"))
    ck("a throwing store falls back to Gmail", where, "Gmail")

    # ---------------------------------------------------------------- NEITHER store: no order
    rg._call = FakeAPI(put_status=403)
    calls["answer"] = False
    ok, where = ex.intent_verified("c7", intent_row("c7"))
    ck("store broken AND Gmail cannot confirm -> NOT verified", ok, False)
    assert ok is False, "fail-closed: the caller must submit nothing"
finally:
    ex.intent_readable = _readable
    ex.time.sleep = _sleep
    os.environ["REGISTRY_TOKEN"] = ""

# ---------------------------------------------------------------- the rule still exists in code
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
assert "intent_verified(cid, row)" in src, "journal_intent must still verify before returning"
i = src.index("_ok, _where = intent_verified")
tail = src[i:i + 900]
assert "return False, None" in tail, "an unverified intent must still return False and place nothing"
CHECKS.append(("journal_intent still gates the order on verification", True, True))

print(f"PASS  test_intent_verify.py  {len(CHECKS)} checks")
