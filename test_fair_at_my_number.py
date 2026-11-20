#!/usr/bin/env python3
"""CLV is scored at MY number (Peter's ruling, Nov 19).

"The line moved my way, it should get CLV credit. The CLV is not at my number."

What was wrong: the `own line` branch read the no-vig fair straight off whatever quote sat at our
number. Once the line moves, our number survives only as a deep ALT. Pinnacle prices alts with
heavier and UNEVEN juice, and novig_p strips vig assuming it sits evenly - so the alt's fair
understates the side holding the better number, biasing exactly the plays that moved our way.

The evidence that this was a defect and not a market verdict: on Nov 19, seven plays all beat the
closing number (+0.5 to +3.0 pts, +11.5 total) and ALL scored negative CLV, averaging -6.8%, with
the size tracking how far the line moved. Toledo -6.5 closed -7.5 and scored -9.63%, which implies
a fair of ~47% at -6.5 - below even the closing number's own probability. You cannot be a 47% shot
at -6.5 when the market closed you at -7.5.

The fair at our number now comes from the MAIN line - the liquid, properly priced quote - moved
across the intervening numbers by the same half-point model already used when Pinnacle has no quote
at our number at all. The alt's own fair is kept on the row as alt_p so the bias stays measurable
and the change is reversible.
"""
import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


F = cl.fair_from_main


def val(*a):
    """the probability only, asserting the conversion was SUPPORTED"""
    p, why, src = F(*a)
    assert why is None, why
    assert isinstance(src, list), "provenance is always a list"
    return p


# ------------------------------------------------------------------ 1. supported moves, measured masses
tol = val(0.50, -7.5, -6.5, True, "NFL", "spr")
ok("NFL -6.5 against a -7.5 close is a favourite at our number", tol > 0.50, tol)
ok("...the gain is the MEASURED mass on 7, not a default", abs(tol - (0.50 + 0.06903765690376569)) < 1e-6, tol)
ok("...so the CLV at -110 is positive, not -9.63%", tol * 1.909 - 1 > 0, round(tol * 1.909 - 1, 4))

worse = val(0.50, -6.5, -7.5, False, "NFL", "spr")
ok("a WORSE number is penalised by the same mass", abs((0.50 - worse) - (tol - 0.50)) < 1e-9, worse)
ok("a favourable move never reduces our fair chance", val(0.50, -7.5, -6.5, True, "NFL", "spr") >= 0.50)
ok("our number BEING the main line changes nothing", abs(val(0.50, -7.5, -7.5, True, "NFL", "spr") - 0.50) < 1e-9)
ok("a main line that already favours us keeps that edge and adds to it",
   val(0.62, -7.5, -6.5, True, "NFL", "spr") > 0.62)
ok("probabilities stay inside [0.01, 0.99]", 0.01 <= val(0.985, -7.5, -6.5, True, "NFL", "spr") <= 0.99)

# ------------------------------------------------------------------ 2. UNSUPPORTED is never substituted
for lab, a, b, kind, why in (("NFL", 5.5, 2.0, "spr", "no_mass_row"),
                             ("NBA", -7.5, -6.5, "spr", "no_mass_row")):
    p_, w_, _s = F(0.50, a, b, False, lab, kind)
    ok(f"{lab} {kind} {a}->{b} is UNSUPPORTED, not a generic value", p_ is None and why in str(w_), (p_, w_))

import line_value as _lv
_row = _lv.mass_row("NCAAB", "spread", 7)
ok("NCAAB spreads ARE registered, as a PUBLISHED estimate rather than measured here",
   _row is not None and "not measured here" in str(_row.calc), _row)
ok("...so the conversion is supported and uses that row's mass",
   abs(val(0.50, -7.5, -6.5, True, "NCAAB", "spr") - (0.50 + _row.m)) < 1e-9)
ok("a registered row always carries its sample size, so measured and estimated stay distinguishable",
   _row.n and _row.n >= _lv.MIN_N, _row.n)

p_, w_, _s = F(0.50, -7.5, -3.5, True, "NFL", "spr")
ok("a move more than 1 point from the line is refused, not extrapolated",
   p_ is None and "far_from_line" in str(w_), (p_, w_))
ok("the reason is always named", F(0.50, 5.5, 2.0, False, "NFL", "spr")[1])
ok("a supported conversion names the registered rows it crossed",
   F(0.50, -7.5, -6.5, True, "NFL", "spr")[2] == ["NFL spread 7"],
   F(0.50, -7.5, -6.5, True, "NFL", "spr")[2])

# ------------------------------------------------------------------ 3. only landing mass is used
src = open("clv_ledger.py").read()
fn = src[src.index("def fair_from_main("):src.index("def close_for(")]
code = fn.split('"""')[2]
ok("the mass comes from line_value's registered table", "lv._mass(" in code)
ok("no legacy half_point_value call survives", "half_point_value" not in code)
ok("cents are never mixed in", not any(t in code for t in ("cents", "cents_of", "am_of_cents")))
ok("Unsupported is caught and returned as a reason, never swallowed", "lv.Unsupported" in code)
ok("no silent default anywhere in the walk", ".get(" not in code)

# ------------------------------------------------------------------ 4. wired in, V1 untouched
cf = src[src.index("def close_for("):src.index("MAX_NEW_MAIL")]
ok("V1 stays OFFICIAL: both branches return the quote read at our number as 'p'",
   cf.count('"p": _p1v') == 2)
ok("...and both still label it 'own line'", cf.count('"how": "own line"') == 2)
ok("V2 is carried in its own fields, never over V1", cf.count('"v2_p"') == 2)
ok("V2 equals V1 whenever our number WAS the main line",
   cf.count('_p2v, _v2why, _v2src = (_p1v, None, ["observed at our number"]) if _at_main') == 2)
ok("an unsupported conversion is recorded as unsupported, not skipped silently",
   '"v2_unsupported"' in src and "UNSUPPORTED: " in src)
ok("CLV is still written at exactly one place in the ledger", src.count('rec["clv"] = ') == 1)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
import sys as _sys
_sys.exit(1 if FAILED else 0)   # a soft assertion failure MUST fail the build, not print and pass
raise SystemExit(1 if FAILED else 0)
