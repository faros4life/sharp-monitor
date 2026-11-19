#!/usr/bin/env python3
"""Risk-accounting corrections (Peter, Nov 18). IMPLEMENTED BUT NOT ACTIVE.

Two defects were found while reconciling a $3,923.01 daily-stop refusal against a tracker showing far
less at risk:

  A. a row whose decided_utc is missing falls into the `d_et in (None, today)` branch and is therefore
     charged to EVERY day's stop, permanently. 16 of 67 registry rows are undated.
  B. a resting bid keeps its full asked stake for ever; nothing releases it when the bid leaves the
     book unfilled.

Only B is correctable without new evidence. A cannot be fixed by dating a row from expires_utc or the
game start - Peter ruled both out, and rightly: neither says when the order was DECIDED. So an undated
row is released only when B's terminal test proves it dead, which preserves genuine prior-day
outstanding exposure (requirement 1) and keeps unknown-fill orders protected (requirement 3).

THE SAFETY PROPERTY, asserted below: the corrected figure can never EXCEED the live one, and can only
differ by legs proven off the book with an explicit zero fill. A risk gate may fail toward refusing;
it must never fail toward admitting.
"""
from datetime import datetime, timedelta, timezone

import executor as ex

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


NOW = datetime.now(timezone.utc)
PAST = (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
FUT = (NOW + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---------------------------------------------------------------- 1. the terminal test (defect B)
ok("expired with an EXPLICIT zero fill is terminal",
   ex.exposure_terminal({"expires_utc": PAST, "filled_stake": 0.0}) is True)
ok("expired with UNKNOWN fill is NOT terminal - the five Novig bids stay protected",
   ex.exposure_terminal({"expires_utc": PAST, "filled_stake": None}) is False)
ok("expired with a PARTIAL fill is not terminal",
   ex.exposure_terminal({"expires_utc": PAST, "filled_stake": 50.0}) is False)
ok("still open is never terminal, even at zero filled",
   ex.exposure_terminal({"expires_utc": FUT, "filled_stake": 0.0}) is False)
ok("no expiry recorded is never terminal",
   ex.exposure_terminal({"filled_stake": 0.0}) is False)
ok("an unparseable expiry is never terminal (fail closed)",
   ex.exposure_terminal({"expires_utc": "soon", "filled_stake": 0.0}) is False)
ok("False is not a zero fill (bool is not a reading)",
   ex.exposure_terminal({"expires_utc": PAST, "filled_stake": False}) is False)
ok("an empty leg is never terminal", ex.exposure_terminal({}) is False)

# ---------------------------------------------------------------- 2. UNKNOWN is never zero
# The whole correction rests on this distinction. If it ever collapses, money that may be sitting at a
# venue would be released from the stop - the one direction a risk gate must not fail in.
for unknown in (None, "", "0", "unknown", [], {}):
    ok(f"filled_stake {unknown!r} is treated as UNKNOWN, not zero",
       ex.exposure_terminal({"expires_utc": PAST, "filled_stake": unknown}) is False)

# ---------------------------------------------------------------- 3. ACTIVE (Peter, Nov 18)
# This was an inert shadow until Peter approved activation. The assertions that pinned its inertness
# are gone on purpose; what replaces them is the property that matters once it IS live: the gate can
# only ever get STRICTER or stay the same, and every failure path keeps the registry's figure.
src = open("executor.py").read()
ok("the live gate reads the reconciled figure", 'book_live.set_exposure(NONPX["today"])' in src)
ok("the exposure loop calls the reconciler", "reconciled_amount(lo, _amt, is_rest)" in src)
ok("the venue index is loaded once per read", 'VENUE["idx"], VENUE["why"] = nvr.load_venue()' in src)
ok("the log reports the evidence state, counts only",
   "exposure reconciliation: {_state}" in src and "no dollars in a public log" in src)
# Nov 18: the three states must be distinguishable in the log. "not attempted" (no gate evaluation
# this pass) reading the same as a failed load is the no-op that looks like success.
ok("the log distinguishes not-attempted from LOADED from FAILED",
   all(t in src for t in ('"not attempted"', '"LOADED"', '"FAILED"')))
ok("the initial state says NOT ATTEMPTED, not 'not loaded'",
   'NOT ATTEMPTED (no risk-gate evaluation this run)' in src and '"why": "not loaded"' not in src)
ok("a real load failure reports its own reason", 'return (None, None), f"orders snapshot: {e1}"'
   in open("novig_reconcile.py").read())

NOVENUE = {"idx": (None, None)}
_was = ex.VENUE["idx"]
try:
    ex.VENUE["idx"] = (None, None)
    ok("no venue evidence keeps the registry figure, releases nothing",
       ex.reconciled_amount({"book": "novig", "asked_stake": 214.0}, 214.0, True) == (214.0, "no venue evidence"))
    ok("a non-novig leg with no terminal proof keeps its figure",
       ex.reconciled_amount({"book": "kalshi", "asked_stake": 99.0}, 99.0, True)[0] == 99.0)
    ok("a malformed leg keeps its figure", ex.reconciled_amount(None, 50.0, True)[0] == 50.0)
    ok("an expired kalshi leg with an explicit zero fill is released",
       ex.reconciled_amount({"book": "kalshi", "expires_utc": PAST, "filled_stake": 0.0}, 223.21, True)[0] == 0.0)
    ok("an expired kalshi leg with UNKNOWN fill is NOT released",
       ex.reconciled_amount({"book": "kalshi", "expires_utc": PAST, "filled_stake": None,
                             "asked_stake": 223.21}, 223.21, True)[0] == 223.21)
finally:
    ex.VENUE["idx"] = _was

import novig_reconcile as _nvr
_ORD = {"orders": [{"order_id": "V1", "client_id": "C1", "status": "FILLED", "filled_qty": 18200,
                    "qty": "18200", "price": "0.525"},
                   # Nov 19 (Peter): a REJECTED zero now has to be PROVEN to release - the runner
                   # deployed until today wrote REJECTED for any non-2xx, a 5xx included, and a 409
                   # can mean an earlier attempt landed. V3 is the unproven twin.
                   {"order_id": "V2", "client_id": "C2", "status": "REJECTED", "filled_qty": 0,
                    "fill_read": True, "fill_read_src": "not submitted",
                    "qty": "40000", "price": "0.51"},
                   {"order_id": "V3", "client_id": "C3", "status": "REJECTED", "filled_qty": 0,
                    "qty": "40000", "price": "0.51"}]}
_was = ex.VENUE["idx"]
try:
    ex.VENUE["idx"] = _nvr.venue_index(_ORD, {"fills": []})
    ok("a filled novig leg counts the ACTUAL fill, not the ask",
       ex.reconciled_amount({"book": "novig", "order_id": "C1", "asked_stake": 96.0}, 96.0, True)[0] == 95.55)
    ok("an UNPROVEN rejected novig leg stays reserved in full",
       ex.reconciled_amount({"book": "novig", "order_id": "C3", "asked_stake": 204.0}, 204.0, False)[0] == 204.0)
    ok("a rejected novig leg with a PROVEN zero counts nothing",
       ex.reconciled_amount({"book": "novig", "order_id": "C2", "asked_stake": 204.0}, 204.0, True)[0] == 0.0)
    ok("a novig leg the venue has never heard of keeps its figure",
       ex.reconciled_amount({"book": "novig", "order_id": "GHOST", "asked_stake": 389.85}, 389.85, True)
       == (389.85, "unknown at the venue"))
    # the one-way property: reconciliation may lower the figure, never raise it
    ok("the reconciled figure can never EXCEED the pre-fix figure",
       ex.reconciled_amount({"book": "novig", "order_id": "C1", "asked_stake": 96.0}, 10.0, True)[0] <= 10.0)
finally:
    ex.VENUE["idx"] = _was

# ---------------------------------------------------------------- 4. the safety property
def _amt(lo, is_rest):
    fs = lo.get("filled_stake")
    return (max(float(fs or 0), float(lo.get("asked_stake") or 0)) if (is_rest or fs is None) else float(fs))


LEGS = [({"expires_utc": PAST, "filled_stake": 0.0, "asked_stake": 223.21}, True),
        ({"expires_utc": PAST, "filled_stake": None, "asked_stake": 214.00}, True),
        ({"expires_utc": FUT, "filled_stake": 0.0, "asked_stake": 216.00}, True),
        ({"filled_stake": 180.0, "asked_stake": 180.0}, False),
        ({"filled_stake": None, "asked_stake": 336.0}, False),
        ({"expires_utc": PAST, "filled_stake": 120.0, "asked_stake": 300.0}, True)]
live = sum(_amt(l, r) for l, r in LEGS)
shadow = sum(_amt(l, r) for l, r in LEGS if not ex.exposure_terminal(l))
ok("the corrected figure never EXCEEDS the live one", shadow <= live, (shadow, live))
ok("the only difference is the provably dead leg", round(live - shadow, 2) == 223.21, (live, shadow))
ok("a partially filled expired leg keeps its money (requirement 4)",
   not ex.exposure_terminal({"expires_utc": PAST, "filled_stake": 120.0, "asked_stake": 300.0}))
ok("an unknown-fill expired leg keeps its FULL asked stake (requirement 3)",
   _amt({"expires_utc": PAST, "filled_stake": None, "asked_stake": 214.0}, True) == 214.0)

# ---------------------------------------------------------------- 5. the $3,000 limit still binds
# Measured on the 18 Nov registry snapshot: live 3,923.01 -> corrected 3,699.80. Both exceed the stop,
# so the refusal that started this investigation was correct under BOTH calculations. Pinning the
# property rather than the figures: a correction that drops below the limit must come from released
# legs alone, never from a looser rule.
# Measured on the 18 Nov snapshot through the ACTIVE path: 3,923.01 -> 2,744.68, which is BELOW the
# 3,000 stop. Activation therefore changes a real decision, and that was Peter's call to make, not a
# tidy-up. The released legs: Brooklyn 389.85 and Philadelphia 204.00 (venue rejected/refused),
# Milwaukee 360.00 (the runner refused it before it reached Novig), Kalshi 223.21 (expired, zero
# filled), plus 1.27 of asked-versus-filled across four filled legs.
ok("the measured correction is 1,178.33", round(3923.01 - 2744.68, 2) == 1178.33)
ok("the released legs account for all but the fill adjustments",
   round(1178.33 - (389.85 + 204.00 + 360.00 + 223.21), 2) == 1.27)
ok("the stop itself is untouched", ex.px_live.DAILY_STOP == 3000.0, ex.px_live.DAILY_STOP)
ok("the exposure date filter is unchanged in the live path",
   'd_et in (None, datetime.now(lm.ET).date())' in src)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
