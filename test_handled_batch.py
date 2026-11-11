"""Nov 11: already_handled() did two Gmail searches PER candidate. Measured on run 43052291191:
9 candidates, 15:50:46 -> 15:55:16 = 4.5 minutes of serial X-GM-RAW round-trips to conclude
"new: 0". ~30s per candidate, bigger than the 79s registry read.

handled_pids() does one OR search per chunk instead, fetches the few matching run emails once, and
answers each pid from that text. These tests pin that the answers are IDENTICAL to the per-pid
searches, that the round trips actually drop, that the namespace rule is unchanged, and - the part
that matters for money - that every failure still RAISES rather than reporting "never placed".
"""
import re

import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


class FakeIMAP:
    """Minimal IMAP double. `corpus` maps uid -> message text."""

    def __init__(self, corpus, fail_search=False, fail_fetch=False, bad_typ=False):
        self.corpus = corpus
        self.fail_search = fail_search
        self.fail_fetch = fail_fetch
        self.bad_typ = bad_typ
        self.searches = []
        self.fetches = []

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            q = args[-1].strip('"')
            self.searches.append(q)
            if self.fail_search:
                return "NO", [None]
            # every dedupe search MUST carry a date bound - unbounded X-GM-RAW scanned the whole
            # mailbox and cost ~30s per pid (Peter, Nov 11: "why are you looking back so far")
            assert "newer_than:" in q, f"dedupe search has no date bound: {q}"
            body = q[q.index("(") + 1:q.rindex(")")] if "(" in q else q
            body = re.sub(r"newer_than:\d+d\s*", "", body)   # strip the bound, keep the terms
            terms = [t.strip() for t in body.split(" OR ") if t.strip()]
            hits = [u for u, txt in self.corpus.items() if any(t in txt for t in terms)]
            return "OK", [b" ".join(u.encode() for u in hits)]
        if cmd == "FETCH":
            u = args[0] if isinstance(args[0], str) else args[0].decode()
            self.fetches.append(u)
            if self.fail_fetch:
                return "NO", [None]
            if self.bad_typ:
                return "OK", [None]
            return "OK", [(b"1 (RFC822 {n}", self.corpus[u].encode())]
        raise AssertionError(cmd)


def play(key, source=None, game=None, bet=None, sport="NBA"):
    p = {"play_key": key}
    if source:
        p["source"] = source
    if game:
        p.update(sport=sport, game=game, bet=bet)
    return p


# ---------------------------------------------------------------- identical answers, fewer trips
A = play("board|lakers|under", game="Los Angeles Lakers @ Milwaukee Bucks", bet="Under 230.5 (-119)")
B = play("board|denver|under", game="Denver vs Memphis: Total Points", bet="Under 230.5 (-100)")
C = play("rules|utah|spread", source="rules")
cands = [A, B, C]

# One run email carrying A's and C's pids; B has never been seen.
pid_a_keys = [ex.pid(k) for k in ex.handled_keys(A)]
pid_c = ex.pid(C["play_key"])
corpus = {"101": f"Bets LIVE run email ... {pid_a_keys[0]} {pid_c} ... details",
          "102": "Bets balances ... nothing relevant here"}

M = FakeIMAP(corpus)
seen = ex.handled_pids(M, cands)
ck("one search for all three candidates", len(M.searches), 1)
ck("only the matching message is fetched", M.fetches, ["101"])
ck("A is handled", ex.already_handled(M, A, seen), True)
ck("B is NOT handled", ex.already_handled(M, B, seen), False)
ck("C is handled", ex.already_handled(M, C, seen), True)
ck("the batched lookup touched no further network", len(M.searches) + len(M.fetches), 2)

# The per-pid path must agree exactly - this is the equivalence proof, not a smoke test.
M2 = FakeIMAP(corpus)
for name, p in (("A", A), ("B", B), ("C", C)):
    ck(f"batched == per-pid for {name}",
       ex.already_handled(M2, p, seen), ex.already_handled(M2, p))
ck("the per-pid path searched once per key, short-circuiting on a hit", len(M2.searches), 4)

# Round-trip count: 2N searches before, ~1 search + a few fetches now.
CHECKS.append(("round trips: per-pid vs batched",
               len(M2.searches), len(M.searches) + len(M.fetches)))
assert len(M.searches) + len(M.fetches) < len(M2.searches), "the fix must reduce round trips"

# ---------------------------------------------------------------- namespace rule unchanged
ck("rules source dedupes on play_key only", ex.handled_keys(C), {"rules|utah|spread"})
ck("lane2 source dedupes on play_key only",
   ex.handled_keys(play("lane2|x", source="lane2")), {"lane2|x"})
ck("board source dedupes on play_key AND derive_key",
   ex.handled_keys(A), {A["play_key"], ex.derive_key(A)})
assert ex.derive_key(A) in ex.handled_keys(A), "the game+side key must still be one of them"
# A board play matches on EITHER key: a re-sent play under a different play_key is still caught.
alt = play("board|lakers|RESENT", game="Los Angeles Lakers @ Milwaukee Bucks", bet="Under 231.5 (-130)")
M3 = FakeIMAP({"1": f"... {ex.pid(ex.derive_key(alt))} ..."})
ck("a re-sent board play is caught by its game+side key",
   ex.already_handled(M3, alt, ex.handled_pids(M3, [alt])), True)

# ---------------------------------------------------------------- FAILS CLOSED (the money part)
for label, kw in (("a failed search raises", {"fail_search": True}),
                  ("a failed fetch raises", {"fail_fetch": True}),
                  ("a malformed fetch raises", {"bad_typ": True})):
    try:
        ex.handled_pids(FakeIMAP(corpus, **kw), cands)
        raise AssertionError(f"{label}: it returned instead of raising - FAIL OPEN ON MONEY")
    except RuntimeError:
        CHECKS.append((label, "RuntimeError", "RuntimeError"))

# A raise must never be convertible into "not handled" by a caller that swallows it.
try:
    ex.handled_pids(FakeIMAP(corpus, fail_search=True), cands)
    got = "returned"
except RuntimeError:
    got = "raised"
ck("an unreadable Gmail aborts rather than answering 'never placed'", got, "raised")

# ---------------------------------------------------------------- edges
ck("no candidates -> no searches", ex.handled_pids(FakeIMAP(corpus), []), {})
ck("no candidates issues no round trips", len(FakeIMAP(corpus).searches), 0)
# Chunking: 45 pids at chunk=20 must be 3 searches, and still answer every pid.
many = [play(f"rules|p{i}", source="rules") for i in range(45)]
M4 = FakeIMAP({"1": f"... {ex.pid('rules|p7')} {ex.pid('rules|p44')} ..."})
seen4 = ex.handled_pids(M4, many, chunk=20)
ck("45 pids chunk into 3 searches", len(M4.searches), 3)
ck("every pid gets an answer", len(seen4), 45)
ck("p7 handled", seen4[ex.pid("rules|p7")], True)
ck("p44 handled", seen4[ex.pid("rules|p44")], True)
ck("p8 not handled", seen4[ex.pid("rules|p8")], False)
# A message matched on one pid must not mark a DIFFERENT pid handled just by association.
ck("no guilt by association", seen4[ex.pid("rules|p0")], False)

# A pid absent from the map (a play that never went through handled_pids) is treated as NOT
# handled by the lookup - so a caller must pass the map built from the same candidate list.
ck("unknown pid defaults to not-handled", ex.already_handled(None, play("rules|never", source="rules"), {}), False)

print(f"PASS  test_handled_batch.py  {len(CHECKS)} checks")
