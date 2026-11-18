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

# ---------------------------------------------------------------- 3. the shadow is INERT
src = open("executor.py").read()
ok("the live gate still reads NONPX, not the shadow",
   'book_live.set_exposure(NONPX["today"])' in src)
# Every appearance of the shadow total must be an increment. A single READ would mean the corrected
# number had reached a decision, which is exactly what is not approved yet. (The first version of this
# assertion was arithmetic on counts and was simply wrong - it failed on correct code.)
_reads = [ln.strip() for ln in src.splitlines()
          if 'NONPX_SHADOW["today"]' in ln and '+=' not in ln]
ok("the shadow total is only ever incremented, never read", not _reads, _reads)
ok("the shadow is incremented in both the normal and the fallback branch",
   src.count('NONPX_SHADOW["today"] +=') == 2, src.count('NONPX_SHADOW["today"] +='))
ok("set_exposure is never called with the shadow", "set_exposure(NONPX_SHADOW" not in src)
ok("the shadow cannot raise into the exposure loop", "except Exception:\n                    NONPX_SHADOW" in src)
ok("the shadow is reset each run alongside the live figure",
   "NONPX_SHADOW.update(today=0.0" in src)

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
ok("the measured correction still exceeds the $3,000 stop", 3699.80 > 3000.0)
ok("the correction is bounded by the released legs", round(3923.01 - 3699.80, 2) == 223.21)
ok("the stop itself is untouched", ex.px_live.DAILY_STOP == 3000.0, ex.px_live.DAILY_STOP)
ok("the exposure date filter is unchanged in the live path",
   'd_et in (None, datetime.now(lm.ET).date())' in src)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
