#!/usr/bin/env python3
"""
Brake check (Oct 27): proves the ntfy STOP/GO switch is read live, WITHOUT placing anything.
Runs the exact pre-order checks the live executor runs (executor.live_guards + px_live.preflight) and prints the verdict.
There is NO order code path here: place() / submit_order are never called.
The workflow sets EXEC_LIVE=on for THIS job only (so preflight gets past the first check); the real switch for the
executor is untouched. Public log: verdict text only (it carries no amounts beyond 'today +0.00' style bot-only P&L).
"""
import executor as X
import px_live as P

ok_g, why_g = X.live_guards()                       # bot-order registry from Gmail (fail closed)
print(f"1) Registry: {'OK' if ok_g else 'REFUSED'}" + (f" - {why_g}" if why_g else "") + f"; bot orders known: {len(P.BOT['ids'] or [])}")
s, t = P.stop_state()
print(f"2) ntfy switch now: {s or 'no STOP/GO in the last 12 h'}" + (f" (sent {t})" if t else ""))
ok, why = P.preflight()
print(f"3) Pre-order verdict: {'WOULD PLACE (all checks pass)' if ok else 'REFUSED'} - {why}")
print("Nothing was placed: this check has no order code.")
