#!/usr/bin/env python3
"""Priority 1 (Peter, Nov 12): reconcile the registry's handled map against the AUTHORITATIVE Gmail
history, both directions, before the duplicate guard is allowed to leave Gmail.

handled_pids() is the duplicate-bet guard. Its own docstring states the rule this script exists to
respect: "a guard that answers 'no' when it cannot see is fail-open on money". So the only
acceptable evidence for switching it is that the store contains EVERY token Gmail contains, inside
the window the guard actually searches (HANDLED_DAYS).

The two directions are NOT symmetric and are reported separately:

  GMAIL-ONLY (missing from the store)  THE DANGEROUS ONE. The guard would answer "never placed
                                       before" for a play that was placed -> a duplicate order.
  STORE-ONLY (extra in the store)      Safe direction but still wrong: the bot would refuse a play
                                       it never actually made. Expected in bulk for tokens OLDER
                                       than the window, which is why age is reported separately
                                       from identity.

Gmail is read ONCE, here. Nothing is placed, cancelled, cleared or retried. The only writes are the
ones bot_orders() already performs on its normal Gmail path (row backfill and its completeness
claim), because this script drives PRODUCTION's own scan rather than re-implementing it - a second
scanner would reconcile itself rather than the thing that runs.

Counts and 8-char hashes only: no play key, bet text, stake or balance.
"""
import sys
from datetime import datetime, timedelta, timezone

import executor as ex
import registry as rg

print("HANDLED-TOKEN RECONCILIATION (Gmail vs private registry)")
print(f"  window (HANDLED_DAYS)     : {ex.HANDLED_DAYS}d   registry KEEP_DAYS: {rg.KEEP_DAYS}d")

if not rg.enabled():
    print("  FAIL  no REGISTRY_TOKEN")
    print("RECONCILIATION: FAIL")
    sys.exit(0)

# ---- Force production's GMAIL path -----------------------------------------------------------
# bot_orders() prefers the store when it can prove completeness. For THIS one-time comparison the
# store is exactly what is on trial, so its fast path is disabled for the duration and the real
# Gmail scan runs. Nothing else is stubbed: same search, same fetch, same parser, same TOKENS_SEEN.
_real_is_complete = rg.is_complete
rg.is_complete = lambda *a, **k: False

ex.TOKENS_SEEN.clear()
try:
    M = ex.imap_open()
except Exception as e:
    print(f"  FAIL  Gmail unreachable: {str(e)[:70]}")
    print("RECONCILIATION: FAIL")
    sys.exit(0)
try:
    ids = ex.bot_orders(M, days=max(ex.HANDLED_DAYS, rg.KEEP_DAYS))
finally:
    try:
        ex.imap_close(M)
    except Exception:
        pass
    rg.is_complete = _real_is_complete

if ids is None:
    print("  FAIL  the Gmail scan did not complete - it returned None (fail closed). No comparison")
    print("        is possible against a window that was not fully read.")
    print("RECONCILIATION: FAIL")
    sys.exit(0)

gmail_tok = {t for t in ex.TOKENS_SEEN if t.startswith(("xpid", "xrty"))}

# ---- Store side ------------------------------------------------------------------------------
data = rg.load()
if data is None:
    print("  FAIL  the store is UNREADABLE - never to be read as 'nothing handled'")
    print("RECONCILIATION: FAIL")
    sys.exit(0)
handled = data.get("handled") or {}
store_tok = {k for k in handled if str(k).startswith(("xpid", "xrty"))}
other = len(handled) - len(store_tok)

cut = (datetime.now(timezone.utc) - timedelta(days=ex.HANDLED_DAYS)).strftime("%Y-%m-%d")


def in_window(t):
    return str((handled.get(t) or {}).get("ts") or "")[:10] >= cut


print(f"  gmail tokens in window    : {len(gmail_tok)}")
print(f"  store handled entries     : {len(handled)}  ({len(store_tok)} dedupe tokens, {other} other)")
print(f"  store tokens in window    : {sum(1 for t in store_tok if in_window(t))}")

missing = sorted(gmail_tok - store_tok)                       # DANGEROUS: guard would fail open
extra_in = sorted(t for t in store_tok - gmail_tok if in_window(t))
extra_old = sum(1 for t in store_tok - gmail_tok if not in_window(t))

print(f"  GMAIL-ONLY (missing)      : {len(missing)}  {[t[:8] for t in missing[:10]]}")
print(f"  STORE-ONLY, in window     : {len(extra_in)}  {[t[:8] for t in extra_in[:10]]}")
print(f"  STORE-ONLY, older (stale) : {extra_old}  (expected: pruning windows differ)")

# Duplicates cannot exist in a dict; what CAN exist is the same play under two token families.
# Reported so "duplicate entries" is answered with a number rather than an assumption.
fams = {}
for t in store_tok:
    fams[t[:4]] = fams.get(t[:4], 0) + 1
print(f"  token families in store   : {fams}")

ok = not missing
print()
print("RECONCILIATION:", "PASS" if ok else "FAIL")
if missing:
    print("  DO NOT SWITCH. Every hash above is a play Gmail knows was handled and the store does")
    print("  not. The guard would answer 'never placed before' for each one, which is a duplicate")
    print("  order on live money - the exact failure handled_pids exists to prevent.")
else:
    print("  The store contains every dedupe token Gmail contains inside the guard's own window.")
    print("  STORE-ONLY entries are the safe direction and do not block the switch.")
sys.exit(0)
