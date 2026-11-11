"""Nov 11 (Peter: "retry"): a REFUSED order was recorded as handled and never retried.

Run 43052291191 proved the cost: "coded-rule alerts: 9; new: 0". All nine candidates - including
that evening's live board play - were permanently skipped, because the run that REFUSED each order
still wrote a real xpid, which already_handled() reads as a completed decision. The revalidate fix
shipped the same morning could not reach a single one of them.

Now a refusal with nothing placed writes xrty instead of xpid+xwp: the play stays new so the next
run re-evaluates it from scratch, the opposite side stays free, and the LIVE PLAY alert does not
repeat on every retry.

The asymmetry these tests exist to protect: wrongly retrying a PLACED order risks a double bet,
wrongly not retrying a refused one costs an opportunity. So order_retryable() must demand positive
proof that nothing went out, and every uncertain case must come back False.
"""
import ast
import os

import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


PLAY = {"play_key": "board|den|under", "sport": "NBA", "source": "board",
        "game": "Denver vs Memphis: Total Points", "bet": "Under 230.5 (-100)"}


def res(order, verdict="WOULD PLACE", rest=None, more=None):
    """A WOULD PLACE row shaped as fmt() renders it, with the real Nov 11 Denver vs Memphis
    numbers: alert Under 230.5 at -100, routed to novig 231.5 at -111 (= +104 at the alert line)."""
    return {"play": PLAY, "verdict": verdict, "pid": ex.pid(PLAY["play_key"]),
            "mtype": "total", "side": "UNDER", "line": 230.5, "take_line": 231.5,
            "book": "novig", "american": -111, "shown": -111, "equiv": 104,
            "hp": 0.018, "hp_src": "(live, 4 gaps)", "risk": 222.0, "to_win": 200.0,
            "nets": 200.0, "partial": False, "others": [],
            "live": {"order": order, "rest": rest, "more": more or [], "book": "novig",
                     "line": 231.5, "am": -111, "shown": -111, "risk": 222.0},
            "entry": {"price_after_fee": -100}}


# ---------------------------------------------------------------- retryable: the real case
REFUSED = {"status": "refused", "reason": "novig moved worse than the alert gate before the order"}
ck("refused with nothing placed is retryable", ex.order_retryable(res(REFUSED)), True)

# ---------------------------------------------------------------- NOT retryable (money side)
ck("a placed order is never retryable",
   ex.order_retryable(res({"status": "placed", "order_id": "o1"})), False)
ck("refused but carrying an order id is not retryable",
   ex.order_retryable(res(dict(REFUSED, order_id="o9"))), False)
ck("refused but with a filled stake is not retryable",
   ex.order_retryable(res(dict(REFUSED, filled_stake=120.0))), False)
ck("refused but a resting bid was placed is not retryable",
   ex.order_retryable(res(REFUSED, rest={"status": "placed"})), False)
ck("refused but a remainder was placed elsewhere is not retryable",
   ex.order_retryable(res(REFUSED, more=[{"status": "refused"}, {"status": "placed"}])), False)
ck("a dry run is not retryable",
   ex.order_retryable(res({"status": "dry", "reason": "live is off"})), False)
ck("an order error is not retryable (state at the venue unknown)",
   ex.order_retryable(res({"status": "error", "reason": "timeout"})), False)
ck("a SKIP verdict is not retryable", ex.order_retryable(res(REFUSED, verdict="SKIP")), False)
ck("no live block at all is not retryable", ex.order_retryable({"play": PLAY, "verdict": "WOULD PLACE"}), False)
ck("no order record is not retryable", ex.order_retryable(res(None)), False)
ck("empty result is not retryable", ex.order_retryable({}), False)

# ---------------------------------------------------------------- the tokens actually written
line = ex.fmt(res(REFUSED))
dk = ex.derive_key(PLAY)
assert ex.retry_tok(dk) in line, f"a retryable refusal must write its xrty token: {line[:160]}"
assert ex.pid(PLAY["play_key"]) not in line, "a retryable refusal must NOT write an xpid"
assert ex.pid(dk) not in line, "a retryable refusal must NOT write the game+side xpid"
assert ex.wp(dk) not in line, "a refusal took no side, so it must NOT write xwp"
CHECKS.append(("refused row writes xrty only", "xrty", "xrty"))

placed_line = ex.fmt(res({"status": "placed", "order_id": "o1", "filled_stake": 222.0}))
assert ex.pid(PLAY["play_key"]) in placed_line, "a placed row must still write its xpid"
assert ex.wp(dk) in placed_line, "a placed row must still mark the side taken"
assert ex.retry_tok(dk) not in placed_line, "a placed row must never write xrty"
CHECKS.append(("placed row unchanged", "xpid+xwp", "xpid+xwp"))

# ---------------------------------------------------------------- dedupe treats them differently
class FakeIMAP:
    def __init__(self, corpus):
        self.corpus = corpus

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            q = a[-1].strip('"')
            body = q[q.index("(") + 1:q.rindex(")")] if "(" in q else q
            terms = [t.strip() for t in body.replace("newer_than:4d", "").split(" OR ") if t.strip()]
            return "OK", [b" ".join(u.encode() for u, t in self.corpus.items()
                                    if any(x in t for x in terms))]
        u = a[0] if isinstance(a[0], str) else a[0].decode()
        return "OK", [(b"h", self.corpus[u].encode())]


# A run email that REFUSED the play carries only xrty.
M = FakeIMAP({"1": f"Bets LIVE ... {ex.retry_tok(dk)} ... [REFUSED: ...]"})
seen = ex.handled_pids(M, [PLAY])
ck("a refused play is NOT handled -> it is retried", ex.already_handled(M, PLAY, seen), False)
ck("but its retry token IS seen -> no re-alert", seen[ex.retry_tok(dk)], True)

# A run email that PLACED the play carries xpid.
M2 = FakeIMAP({"1": f"Bets LIVE ... {ex.pid(dk)} {ex.wp(dk)} ..."})
seen2 = ex.handled_pids(M2, [PLAY])
ck("a placed play IS handled -> never retried", ex.already_handled(M2, PLAY, seen2), True)

# Neither token present: brand new play.
M3 = FakeIMAP({"1": "Bets balances ... nothing"})
seen3 = ex.handled_pids(M3, [PLAY])
ck("an unseen play is not handled", ex.already_handled(M3, PLAY, seen3), False)
ck("an unseen play has no retry token", seen3[ex.retry_tok(dk)], False)
ck("both token families are asked for in one search", len(seen3), 4)   # 2 keys x 2 families

# ---------------------------------------------------------------- the alert does not repeat
sent = []
_push, _seen_save = ex.push, ex.SEEN["tok"]
try:
    ex.push = lambda title, body, **k: sent.append(title)

    ex.SEEN["tok"] = {}
    ex.live_play_alert(res(REFUSED))
    ck("first time: the alert goes out", len(sent), 1)
    assert "LIVE PLAY" in sent[0], sent[0]

    ex.SEEN["tok"] = {ex.retry_tok(dk): True}
    ex.live_play_alert(res(REFUSED))
    ck("retry: the alert is suppressed", len(sent), 1)

    # An unavailable map must still alert - being told twice beats being told nothing.
    ex.SEEN["tok"] = {}
    ex.live_play_alert(res(REFUSED))
    ck("no map: the alert still goes out", len(sent), 2)
finally:
    ex.push, ex.SEEN["tok"] = _push, _seen_save

# ---------------------------------------------------------------- HELD is untouched
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
fns = {n.name: n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
assert "held_tok" in fns, "the HELD retry mechanism must still exist - xrty mirrors it, not replaces it"
CHECKS.append(("held_tok still present", True, True))

print(f"PASS  test_retry_refused.py  {len(CHECKS)} checks")
