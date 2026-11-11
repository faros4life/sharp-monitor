"""Nov 11: the Novig snapshot refresh wait runs ONCE per run, and fill-report dedupe moves to the
registry.

Run 43083072268: positions first attempt 80.0s, retry 239.4s, and Novig ended blind anyway.
novig_positions() is called twice per run - the parallel read, then the parallel retry - and each
call that found a stale snapshot asked the home PC for a fresh one and slept up to 90s. Waiting
twice cannot help: nothing between the attempts makes a home PC that ignored 90 seconds answer in
the next 90.

What must not change: a stale snapshot still returns None, Novig is still blind, and no live order
goes out on any venue. Only the time to reach that answer changes.
"""
import ast
import os

import executor as ex

CHECKS = []
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


# ---------------------------------------------------------------- the wait happens once
os.environ["NOVIG_SNAPSHOT_TOKEN"] = "t"
ex._NVERR.clear(); ex._NVERR["why"] = ""
ex._NVERR["waited"] = True          # a previous caller in this run already waited
slept = {"n": 0}
_sleep = ex.time.sleep
try:
    ex.time.sleep = lambda s: slept.__setitem__("n", slept["n"] + 1)
    ck("a second caller returns immediately", ex.novig_snapshot(), None)
    ck("and does not sleep at all", slept["n"], 0)
    assert "already awaited" in ex._NVERR["why"], ex._NVERR["why"]
    CHECKS.append(("the reason says the wait was already spent", True, True))
finally:
    ex.time.sleep = _sleep
    ex._NVERR.clear(); ex._NVERR["why"] = ""
    os.environ.pop("NOVIG_SNAPSHOT_TOKEN", None)

# no token is still an immediate None, unchanged
ex._NVERR["why"] = ""
ck("no snapshot token -> None, unchanged", ex.novig_snapshot(), None)

# the latch is set at the moment the wait begins, not after it
i = src.index('_NVERR["waited"] = True')
j = src.index("for _ in range(9):", i - 400)
ck("the latch is set before the sleep loop", i < j, True)

# ---------------------------------------------------------------- fail-closed is untouched
fns = {n.name: n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
np = fns["novig_positions"]
nones = [n.lineno for n in ast.walk(np)
         if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value is None]
ck("novig_positions still returns None on failure", len(nones) >= 2, True)
assert "positions blind" in src, "the blind path must still exist"
CHECKS.append(("a stale snapshot still blinds the venue", True, True))

# ---------------------------------------------------------------- report dedupe: store, then Gmail
ar = fns["already_reported"]
names = {n.func.id for n in ast.walk(ar) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
ck("it still falls back to the strict Gmail lookup", "sent_tokens" in names, True)
body = src[src.index("def already_reported("):src.index("def novig_reports(")]
assert "rest = [t for t in toks if t not in hit]" in body, \
    "tokens the store does not know must still be checked in Gmail"
CHECKS.append(("an unknown token is checked, never assumed unsent", True, True))
assert 'put_tokens(found, outcome="reported")' in body, \
    "what Gmail confirms must be written back so the store converges"
CHECKS.append(("Gmail's answer converges into the store", True, True))
# Nov 11 (Peter: "fix duplicate Novig fill notifications"): the Novig reporter no longer decides
# from a Gmail search at all. It takes an atomic registry claim BEFORE sending, because Gmail does
# not index a just-sent token email before the next catch-up pass looks - which is what sent 27
# fills 70+ times. Kalshi is unchanged and still uses the batched lookup directly.
ck("kalshi still uses the batched lookup", src.count("= already_reported(M"), 1)
ck("kalshi still stores its token on send",
   src.count('registry.put_tokens([tok], outcome="reported")'), 1)
ck("novig claims through the registry instead", "if not claimer.claim(tok):" in src, True)
ck("the claim is still Gmail-backed when the store cannot answer",
   "return tok not in self._gmail_set()" in src, True)

nb = src[src.index("def novig_reports("):src.index("def kalshi_rest_reports(")]
# ORDER IS THE FIX: the send is recorded as soon as Telegram delivers, BEFORE the backup email.
# The old code wrote the record only if send() succeeded, so one mail failure re-sent that fill
# on every later pass. Compare positions in the Novig body only.
ck("the claim is promoted before the backup email",
   nb.index("claimer.sent(tok)") < nb.index('send(f"Bets Novig order:'), True)
ck("a send that never went out releases its claim", "claimer.failed(tok)" in nb, True)
ck("no per-item Gmail search crept back into the novig loop",
   "already_reported(" in nb, False)

print(f"PASS  test_novig_wait.py  {len(CHECKS)} checks")
