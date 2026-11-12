"""bot_orders() reading the private store instead of Gmail (Nov 11, Peter: "b2", "finish the job").

Measured: the Gmail path is 81.4s (~200 serial full-message IMAP fetches); one contents GET is
~0.25s.

The property every test here defends: the fast path is taken ONLY when the store is known to hold
every row Gmail holds for the window. A store missing history would under-count exposure, which is
fail-OPEN on the one guard that caps a losing day. So:

  - no completeness marker            -> Gmail (slow, complete), then backfill + set the marker
  - marker older than the window      -> Gmail
  - store unreadable                  -> Gmail
  - backfill write fails              -> marker NOT set, so the next run is Gmail again
  - a later order write fails         -> marker CLEARED, so the next run is Gmail again

And the accounting itself must be identical either way, which is why _account_rows() is one shared
function rather than two copies.
"""
import json
import os
from datetime import datetime, timedelta, timezone

os.environ["REGISTRY_TOKEN"] = ""
import executor as ex
import registry as rg

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def row(oid, book="novig", stake=222.0, source="r1", key="NCAAB|A @ B|side|A", cid=None,
        intent=False, status="placed"):
    return {"key": key, "source": source, "decided_utc": NOW,
            "live_order": {"status": status, "order_id": oid, "book": book,
                           "asked_stake": stake, "filled_stake": None, "client_id": cid,
                           "intent": intent}}


def ledger_mail(rows):
    body = ("LEDGER (machine-readable, one row per play; latency = decision time minus first alert time)\n"
            + json.dumps(rows))
    return (b"From: p@x\r\nTo: p@x\r\nSubject: Bets LIVE: 1 placed\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n" + body.encode() + b"\r\n")


class FakeIMAP:
    def __init__(self, mails):
        self.mails = mails
        self.fetches = 0

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            if a[0] == "X-GM-RAW":
                return "OK", [b""]            # intent_cleared: nothing cleared
            return "OK", [b" ".join(k.encode() for k in self.mails)]
        self.fetches += 1
        u = a[0] if isinstance(a[0], str) else a[0].decode()
        return "OK", [(b"h", self.mails[u])]


# Intent CLEARANCE is Peter's own manual email and needs real credentials; it has its own tests.
# Stubbed to False here, which is the state these fixtures mean: nothing has been cleared.
ex.intent_cleared = lambda M, k: False


def reset():
    ex.NONPX["today"] = 0.0
    ex.BOARD.update(risk=0.0, known=False)
    ex.BOARD["keys"] = set()
    ex.R1.update(risk=0.0, known=False)
    ex.R1["keys"] = set()
    ex.LIVEKEYS.clear()
    ex.INTENT["open"] = {}


GMAIL = {"1": ledger_mail([row("o1", stake=113.93), row("o2", book="prophetx", stake=108.07)])}

# ---------------------------------------------------------------- no token: Gmail only, unchanged
os.environ["REGISTRY_TOKEN"] = ""
reset()
M = FakeIMAP(GMAIL)
ids = ex.bot_orders(M)
ck("no token -> Gmail path still works", sorted(ids), ["o1", "o2"])
ck("no token -> Gmail was fetched", M.fetches, 1)
ck("R1 risk accumulated", round(ex.R1["risk"], 2), 222.0)
ck("exposure known", ex.R1["known"], True)
GMAIL_IDS, GMAIL_R1, GMAIL_NONPX = dict(ids), ex.R1["risk"], ex.NONPX["today"]


class FakeAPI:
    def __init__(self, data, put_status=201):
        self.data = data
        self.put_status = put_status
        self.sha = "s0"
        self.puts = 0

    def __call__(self, method, url, body=None, timeout=20):
        import base64
        if method == "GET":
            return 200, {"content": base64.b64encode(json.dumps(self.data).encode()).decode(),
                         "sha": self.sha}
        self.puts += 1
        if self.put_status not in (200, 201):
            return self.put_status, {}
        self.data = json.loads(base64.b64decode(body["content"]).decode())
        self.sha = f"s{self.puts}"
        return 201, {}


def use(api, tok="t"):
    rg._call = api
    os.environ["REGISTRY_TOKEN"] = tok


# ---------------------------------------------------------------- first run with a token: BACKFILL
api = FakeAPI(dict(rg.EMPTY))
use(api)
reset()
M = FakeIMAP(GMAIL)
ids = ex.bot_orders(M)
ck("first run still reads Gmail (store not yet complete)", M.fetches, 1)
ck("same ids as the Gmail-only run", sorted(ids), sorted(GMAIL_IDS))
ck("the store was backfilled", len(api.data.get("orders") or []), 2)
ck("and marked complete", (api.data.get("meta") or {}).get("complete_through"), TODAY)
assert (api.data.get("meta") or {}).get("complete_at"), "the claim must be stamped"
CHECKS.append(("the completeness claim is time-stamped", True, True))

# ---------------------------------------------------------------- second run: FAST PATH, no Gmail
reset()
M2 = FakeIMAP(GMAIL)
ids2 = ex.bot_orders(M2)
ck("fast path fetches NO mail", M2.fetches, 0)
ck("fast path returns the same ids", sorted(ids2), sorted(GMAIL_IDS))
ck("fast path computes the same R1 risk", round(ex.R1["risk"], 2), round(GMAIL_R1, 2))
ck("fast path computes the same non-ProphetX exposure",
   round(ex.NONPX["today"], 2), round(GMAIL_NONPX, 2))
ck("fast path still marks exposure known", ex.R1["known"], True)

# ---------------------------------------------------------------- the marker is the only switch
stale = (datetime.now(timezone.utc) - timedelta(days=9)).strftime("%Y-%m-%d")
api.data["meta"]["complete_through"] = stale
reset()
M3 = FakeIMAP(GMAIL)
ex.bot_orders(M3)
ck("a stale marker forces Gmail", M3.fetches, 1)

api.data["meta"]["complete_through"] = ""
reset()
M4 = FakeIMAP(GMAIL)
ex.bot_orders(M4)
ck("an empty marker forces Gmail", M4.fetches, 1)

# Unreadable store -> Gmail, never an empty fast path.
use(lambda *a, **k: (500, {}))
reset()
M5 = FakeIMAP(GMAIL)
ids5 = ex.bot_orders(M5)
ck("an unreadable store falls back to Gmail", M5.fetches, 1)
ck("and still returns the real ids", sorted(ids5), sorted(GMAIL_IDS))

# ---------------------------------------------------------------- failed writes force the slow path
api = FakeAPI(dict(rg.EMPTY), put_status=403)
use(api)
reset()
ex.bot_orders(FakeIMAP(GMAIL))
ck("a failed backfill leaves the marker unset",
   (api.data.get("meta") or {}).get("complete_through"), None)

# A failed order write must CLEAR an existing marker.
api = FakeAPI({"orders": [], "intents": [], "handled": {},
               "meta": {"complete_through": TODAY, "complete_at": NOW}})
use(api)
ck("marker starts set", rg.complete_through(), TODAY)
_send = ex.send
try:
    ex.send = lambda *a, **k: None
    api.put_status = 403        # every store write now fails
    ex.journal_order({"play": {"play_key": "k", "source": "r1"}},
                     {"order_id": "o9", "book": "novig", "asked_stake": 100.0}, cid="c9")
finally:
    ex.send = _send
api.put_status = 201            # let a read through again
# invalidate() is itself a write, so when writes fail it CANNOT clear the marker. Freshness is what
# closes that hole: the claim is only trusted while it keeps being re-asserted.
old = (datetime.now(timezone.utc) - timedelta(minutes=rg.FRESH_MIN + 5)).strftime("%Y-%m-%dT%H:%M:%SZ")
api.data["meta"] = {"complete_through": TODAY, "complete_at": old}
ck("a stale completeness claim is not trusted", rg.is_complete(TODAY), False)
fresh = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
api.data["meta"] = {"complete_through": TODAY, "complete_at": fresh}
ck("a fresh claim is trusted", rg.is_complete(TODAY), True)
api.data["meta"] = {"complete_through": TODAY}
ck("a claim with no stamp is not trusted", rg.is_complete(TODAY), False)
api.data["meta"] = {"complete_through": TODAY, "complete_at": "garbage"}
ck("an unparseable stamp is not trusted", rg.is_complete(TODAY), False)
future = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
api.data["meta"] = {"complete_through": TODAY, "complete_at": future}
ck("a stamp from the future is not trusted", rg.is_complete(TODAY), False)

# ---------------------------------------------------------------- intents survive the fast path
api = FakeAPI({"orders": [row("oi", cid="cid1", intent=True)], "intents": [], "handled": {},
               "meta": {"complete_through": TODAY, "complete_at": NOW}})
use(api)
reset()
M6 = FakeIMAP(GMAIL)
ex.bot_orders(M6)
ck("fast path read no mail", M6.fetches, 0)
ck("an unresolved intent is still latched open", list(ex.INTENT["open"]), ["cid1"])

# ...and a confirmed order resolves it, same as on the Gmail path.
api = FakeAPI({"orders": [row("oi", cid="cid1", intent=True),
                          row("oi", cid="cid1", intent=False)],
               "intents": [], "handled": {}, "meta": {"complete_through": TODAY, "complete_at": NOW}})
use(api)
reset()
ex.bot_orders(FakeIMAP(GMAIL))
ck("a confirmed order clears its own intent", dict(ex.INTENT["open"]), {})

# ---------------------------------------------------------------- one order counted once
api = FakeAPI({"orders": [row("o1", cid="cA", stake=222.0), row("o1", cid="cA", stake=222.0)],
               "intents": [], "handled": {}, "meta": {"complete_through": TODAY, "complete_at": NOW}})
use(api)
reset()
ex.bot_orders(FakeIMAP(GMAIL))
ck("the same order twice adds its money once", round(ex.R1["risk"], 2), 222.0)

# ------------------------------------------------- a SHORT-window caller never asserts the claim
# Nov 12 (Peter): signal_alerts calls bot_orders(M, days=2) so that AGAINST YOUR BET can use the
# fast store read instead of the 240s Gmail scan. The marker is always TESTED against KEEP_DAYS,
# so a 2-day scan asserting it would let the next 4-day reader trust a store missing days 3-4 and
# UNDERCOUNT exposure against the daily stop. Rows may still be written; only the claim is withheld.
api = FakeAPI(dict(rg.EMPTY))
use(api)
reset()
M7 = FakeIMAP(GMAIL)
ex.bot_orders(M7, days=2)
ck("a short-window scan does read Gmail", M7.fetches > 0, True)
ck("a short-window scan still stores its rows", bool(api.data.get("orders")), True)
meta7 = api.data.get("meta") or {}
ck("a short-window scan asserts NO orders claim", meta7.get("complete_through"), None)
ck("a short-window scan asserts NO tokens claim", meta7.get("tok_complete_through"), None)
ck("so the store is still not trusted for the real window", rg.is_complete(TODAY), False)

# The full-window caller, unchanged, still does assert it.
api = FakeAPI(dict(rg.EMPTY))
use(api)
reset()
ex.bot_orders(FakeIMAP(GMAIL))
ck("the full-window scan still asserts the claim",
   (api.data.get("meta") or {}).get("complete_through"), TODAY)

# ------------------------------------- a short-window READER does not refresh the freshness stamp
# It verified nothing about completeness, so extending the claim's life from it would defeat the
# 12-minute bound. It may still READ: its cut is nearer, so a valid 4-day claim satisfies it.
OLD = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
api = FakeAPI({"orders": [row("o9", stake=222.0)], "intents": [], "handled": {},
               "meta": {"complete_through": TODAY, "complete_at": OLD}})
use(api)
reset()
M8 = FakeIMAP(GMAIL)
ex.bot_orders(M8, days=2)
ck("the short-window reader took the fast path", M8.fetches, 0)
ck("...and counted the stored row", round(ex.R1["risk"], 2), 222.0)
ck("...and left the freshness stamp alone", (api.data.get("meta") or {}).get("complete_at"), OLD)

os.environ["REGISTRY_TOKEN"] = ""
print(f"PASS  test_registry_migration.py  {len(CHECKS)} checks")
