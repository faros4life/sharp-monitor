"""Nov 11: the two fill reporters cost 136s combined (novig 67.4s, kalshi 68.6s) and both did it
the same way - one UNBOUNDED Gmail search PER RECORD, plus, in kalshi's case, a second full
"Bets LIVE:" scan repeating work bot_orders() had just done in the same run.

Fixed by one shared sent_tokens() doing a bounded OR search per 20 tokens, and by kalshi reusing
LEDGER_ROWS.

What these tests defend: reporting decisions are IDENTICAL, an already-reported fill is still
suppressed exactly once, the 2-day window is preserved even though bot_orders reads 4 days, the
fallback scan still works when the row cache is empty, and the whole thing FAILS CLOSED - a
reporter that answers "not yet reported" when it cannot see Gmail would message twice.
"""
import json
from datetime import datetime, timedelta, timezone

import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


NOW = datetime.now(timezone.utc)


def iso(d):
    return (NOW + timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeIMAP:
    def __init__(self, corpus, fail_search=False, fail_fetch=False):
        self.corpus = corpus
        self.fail_search = fail_search
        self.fail_fetch = fail_fetch
        self.searches = []
        self.fetches = []

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            self.searches.append(a)
            if self.fail_search:
                return "NO", [None]
            if a[0] == "X-GM-RAW":
                q = a[-1].strip('"')
                assert "newer_than:" in q, f"token search must be bounded: {q}"
                body = q[q.index("(") + 1:q.rindex(")")]
                terms = [t.strip() for t in body.split(" OR ") if t.strip()]
                return "OK", [b" ".join(u.encode() for u, t in self.corpus.items()
                                        if any(x in t for x in terms))]
            return "OK", [b" ".join(u.encode() for u in self.corpus)]
        if self.fail_fetch:
            return "NO", [None]
        u = a[0] if isinstance(a[0], str) else a[0].decode()
        self.fetches.append(u)
        return "OK", [(b"h", self.corpus[u].encode())]


# ---------------------------------------------------------------- sent_tokens
M = FakeIMAP({"1": "report ... xnvrAAA ... end", "2": "unrelated"})
got = ex.sent_tokens(M, ["xnvrAAA", "xnvrBBB"])
ck("an already-reported token is found", "xnvrAAA" in got, True)
ck("an unreported token is not", "xnvrBBB" in got, False)
ck("one search for both tokens", len([s for s in M.searches if s[0] == "X-GM-RAW"]), 1)
ck("no tokens -> no search", ex.sent_tokens(FakeIMAP({}), []), set())
ck("blank tokens are ignored", ex.sent_tokens(FakeIMAP({}), [None, ""]), set())

# 45 tokens -> 3 bounded searches, not 45
M2 = FakeIMAP({"1": "xT7 and xT44"})
got2 = ex.sent_tokens(M2, [f"xT{i}" for i in range(45)])
ck("45 tokens chunk into 3 searches", len(M2.searches), 3)
ck("and the right ones are found", sorted(got2), ["xT44", "xT7"])
ck("a short token does not match inside a longer one",
   sorted(ex.sent_tokens(FakeIMAP({"1": "xT44"}), ["xT4", "xT44"])), ["xT44"])

# FAILS CLOSED both ways.
for label, kw in (("a failed search raises", {"fail_search": True}),
                  ("a failed fetch raises", {"fail_fetch": True})):
    try:
        ex.sent_tokens(FakeIMAP({"1": "xnvrAAA"}, **kw), ["xnvrAAA"])
        raise AssertionError(f"{label}: returned instead of raising - would re-report a fill")
    except RuntimeError:
        CHECKS.append((label, "RuntimeError", "RuntimeError"))

# A message is fetched once even when several tokens match it.
M3 = FakeIMAP({"1": "xA xB xC"})
ex.sent_tokens(M3, ["xA", "xB", "xC"])
ck("one matching message is fetched once", M3.fetches, ["1"])

# ---------------------------------------------------------------- kalshi reuses parsed rows
def rest_row(oid, day=0):
    return {"key": "NBA|A @ B|total|UNDER", "decided_utc": iso(day),
            "live_rest": {"status": "placed", "order_id": oid, "book": "kalshi", "limit": -118}}


calls = {"k": 0}


def fake_k(method, path):
    calls["k"] += 1
    oid = path.rsplit("/", 1)[-1]
    return 200, {"order": {"fill_count": 5 if oid == "ok1" else 0, "remaining_count": 0}}


_k, _push, _tg, _rows = ex.book_live._k_call, ex.push, ex.tg, list(ex.LEDGER_ROWS)
_send, _imap = ex.send, ex.imap_open
msgs = []
try:
    ex.book_live._k_call = fake_k
    ex.push = lambda *a, **k: None
    ex.tg = lambda m: msgs.append(m)
    ex.send = lambda *a, **k: None   # the token email IS the record; not what this file tests

    # rows already parsed this run -> NO second "Bets LIVE:" scan
    ex.LEDGER_ROWS[:] = [rest_row("ok1"), rest_row("ok2")]
    M4 = FakeIMAP({})
    ex.imap_open = lambda: M4
    ex.kalshi_rest_reports()
    plain = [s for s in M4.searches if s[0] is None]
    ck("no second Bets LIVE: scan when rows are cached", plain, [])
    ck("the venue was still checked for each resting order", calls["k"], 2)
    ck("the fill was reported", len(msgs), 1)
    assert "KALSHI RESTING BID FILLED" in msgs[0], msgs[0]

    # already reported -> suppressed, and the venue is still checked (state may have changed)
    msgs.clear(); calls["k"] = 0
    # derived exactly as the code does: fc goes through lm.num, so "5" and 5.0 differ
    _fc = ex.lm.num(5)
    tok = "xkrf" + __import__("hashlib").sha1(f"ok1|{_fc}".encode()).hexdigest()[:12]
    M5 = FakeIMAP({"1": f"earlier report {tok}"})
    ex.imap_open = lambda: M5
    ex.kalshi_rest_reports()
    ck("an already-reported fill is not reported twice", len(msgs), 0)

    # the 2-day window is preserved even though bot_orders reads 4 days
    msgs.clear(); calls["k"] = 0
    ex.LEDGER_ROWS[:] = [rest_row("ok1", day=-9)]
    ex.imap_open = lambda: FakeIMAP({})
    ex.kalshi_rest_reports()
    ck("a row older than 2 days is not checked", calls["k"], 0)

    # empty cache -> the original scan still runs (never blinder than before)
    msgs.clear(); calls["k"] = 0
    ex.LEDGER_ROWS[:] = []
    body = ("LEDGER (machine-readable)\n" + json.dumps([rest_row("ok1")]))
    M6 = FakeIMAP({"1": "Subject: Bets LIVE: x\n\n" + body})
    ex.imap_open = lambda: M6
    ex.kalshi_rest_reports()
    ck("with no cache it falls back to scanning", calls["k"], 1)
    ck("and still reports the fill", len(msgs), 1)
finally:
    ex.book_live._k_call, ex.push, ex.tg = _k, _push, _tg
    ex.send, ex.imap_open = _send, _imap
    ex.LEDGER_ROWS[:] = _rows

print(f"PASS  test_fill_reports.py  {len(CHECKS)} checks")
