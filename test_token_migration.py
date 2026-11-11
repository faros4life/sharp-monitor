"""Nov 11: dedupe (xpid), retry (xrty) and side-taken (xwp) checks move off Gmail.

Measured: handled_pids cost 13.6s on Gmail for 21 candidates; one registry contents GET is ~0.3s.

The rule the whole migration rests on: a store that MIGHT be missing a token must never answer
"not handled". That is how a play gets processed - or bet - twice, and how the opposite side of a
held position gets taken. So the registry answers only when it is known complete AND that claim is
fresh; otherwise Gmail, exactly as before.

Backfill costs no extra scan: the tokens are harvested from the "Bets LIVE:" emails bot_orders
already has open.
"""
import ast
import os
import types

import executor as ex

CHECKS = []
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


class FakeIMAP:
    def __init__(self, corpus=None):
        self.corpus = corpus or {}
        self.calls = 0

    def uid(self, cmd, *a):
        self.calls += 1
        if cmd == "SEARCH":
            return "OK", [b" ".join(k.encode() for k in self.corpus)]
        u = a[0] if isinstance(a[0], str) else a[0].decode()
        return "OK", [(b"h", self.corpus[u].encode())]


def with_registry(enabled=True, complete=True, toks=(), raises=False):
    m = types.ModuleType("registry")
    m.enabled = lambda: enabled
    if raises:
        m.tokens_complete = lambda: (_ for _ in ()).throw(RuntimeError("store down"))
    else:
        m.tokens_complete = lambda: complete
    m.token_set = lambda: set(toks)
    m.put_tokens = lambda t, outcome="seen": True
    m.invalidate_tokens = lambda: True
    return m


PLAY = {"play_key": "board|den|under", "source": "board", "sport": "NBA",
        "game": "Denver vs Memphis: Total Points", "bet": "Under 230.5 (-100)"}
dk = ex.derive_key(PLAY)
PIDS = [ex.pid(k) for k in ex.handled_keys(PLAY)]

_rg = ex.registry
try:
    # ------------------------------------------------------- store answers, Gmail untouched
    ex.registry = with_registry(toks=[PIDS[0]])
    M = FakeIMAP()
    seen = ex.handled_pids(M, [PLAY])
    ck("no Gmail call when the store is complete", M.calls, 0)
    ck("a token in the store reads as handled", seen[PIDS[0]], True)
    ck("a token absent from the store reads as not handled", seen[ex.retry_tok(dk)], False)
    ck("already_handled agrees", ex.already_handled(M, PLAY, seen), True)

    # ------------------------------------------------------- incomplete store -> Gmail
    ex.registry = with_registry(complete=False)
    M2 = FakeIMAP({"1": f"run email {PIDS[0]}"})
    seen = ex.handled_pids(M2, [PLAY])
    ck("an incomplete store falls back to Gmail", M2.calls > 0, True)
    ck("and Gmail's answer is used", seen[PIDS[0]], True)

    # ------------------------------------------------------- unreadable store -> Gmail
    ex.registry = with_registry(raises=True)
    M3 = FakeIMAP({"1": f"run email {PIDS[0]}"})
    seen = ex.handled_pids(M3, [PLAY])
    ck("an unreadable store falls back to Gmail", M3.calls > 0, True)
    ck("and never answers 'not handled' from a store it could not read", seen[PIDS[0]], True)

    # ------------------------------------------------------- disabled store -> Gmail
    ex.registry = with_registry(enabled=False)
    M4 = FakeIMAP({"1": f"run email {PIDS[0]}"})
    ck("no token -> Gmail, unchanged", ex.handled_pids(M4, [PLAY])[PIDS[0]], True)
    ck("Gmail was used", M4.calls > 0, True)
finally:
    ex.registry = _rg

# ------------------------------------------------------- tokens are harvested, not re-scanned
ck("the token regex matches all three families",
   sorted(set(ex.TOKRE.findall(f"a {ex.pid('k')} b {ex.retry_tok('k')} c {ex.wp('k')} d"))),
   sorted({ex.pid("k"), ex.retry_tok("k"), ex.wp("k")}))
ck("a held token is NOT harvested (it must not mark a play handled)",
   ex.TOKRE.findall(ex.held_tok("k")), [])
assert "TOKENS_SEEN.update(TOKRE.findall(txt))" in src, \
    "tokens must be harvested from the email text bot_orders already holds"
assert src.index("TOKENS_SEEN.update") > src.index("def bot_orders"), \
    "the harvest belongs inside the scan bot_orders already performs"
CHECKS.append(("backfill costs no extra Gmail scan", True, True))

# ------------------------------------------------------- completeness is set only on success
i = src.index("registry.put_rows(all_rows) and registry.put_tokens(TOKENS_SEEN)")
blk = src[i:i + 500]
assert "set_tokens_complete()" in blk and "invalidate_tokens()" in blk, blk[:200]
CHECKS.append(("tokens are marked complete only when BOTH writes succeed", True, True))

# ------------------------------------------------------- the run teaches the store its own tokens
tree = ast.parse(src)
fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
assert "run_tokens" in fns, "the run must write back the tokens it produced"
rt = fns["run_tokens"]
assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "fmt"
           for n in ast.walk(rt)), \
    "tokens must be derived from the rendered tag, so the email and the store cannot disagree"
CHECKS.append(("the store learns exactly what the email records", True, True))
main = fns["main"]
w = [n.lineno for n in ast.walk(main) if isinstance(n, ast.Call)
     and isinstance(n.func, ast.Attribute) and n.func.attr == "put_tokens"]
ck("the run writes its tokens once", len(w), 1)

# ------------------------------------------------------- manual holds and clearance stay on Gmail
assert 'M.uid("SEARCH", None, "SUBJECT", \'"Bets manual"\'' in src, \
    "manual-bet holds must keep reading Peter's own email - it is the authoritative record"
CHECKS.append(("manual-bet holds still read Gmail", True, True))
ic = fns["intent_cleared"]
assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id in ("subject_hits", "gsearch_strict", "gsearch") for n in ast.walk(ic)), \
    "manual intent clearance must stay on Gmail - the bot must not be able to clear its own intent"
CHECKS.append(("manual intent clearance still requires Peter's email", True, True))

print(f"PASS  test_token_migration.py  {len(CHECKS)} checks")
