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

# ------------------------------------------------------------------ 1. the seven plays' shape
tol = F(0.50, -7.5, -6.5, True, "NCAAB", "spr")
ok("Toledo -6.5 against a -7.5 close is now a FAVOURITE at our number", tol > 0.50, tol)
ok("...and the CLV at -110 is positive, not -9.63%", tol * 1.909 - 1 > 0, round(tol * 1.909 - 1, 4))
ok("...and it is not absurdly large - a 1-point move is worth a few points of win chance",
   0.50 < tol < 0.58, tol)

ore = F(0.50, 159.5, 160.5, True, "NCAAB", "tot")
ok("Under 160.5 against a 159.5 close gains, because the under is easier", ore > 0.50, ore)
hou = F(0.50, -13.0, -10.5, True, "NCAAF", "spr")
ok("Houston -10.5 against a -13 close gains more than a 1-point move did", hou > tol, (hou, tol))

# ------------------------------------------------------------------ 2. direction and symmetry
worse = F(0.50, 159.5, 158.5, False, "NCAAB", "tot")
ok("a WORSE number is still penalised", worse < 0.50, worse)
ok("ahead and behind by the same distance move equally and oppositely",
   abs((ore - 0.50) - (0.50 - worse)) < 1e-9, (ore, worse))
ok("a favourable move can never reduce our fair chance",
   all(F(0.50, -7.5, -7.5 + d, True, "NBA", "spr") >= 0.50 for d in (0.5, 1.0, 2.0, 3.0)))
ok("further ahead is worth more than less far ahead",
   F(0.50, -7.5, -5.5, True, "NBA", "spr") > F(0.50, -7.5, -6.5, True, "NBA", "spr") >
   F(0.50, -7.5, -7.0, True, "NBA", "spr"))
ok("our number BEING the main line changes nothing",
   abs(F(0.50, -7.5, -7.5, True, "NBA", "spr") - 0.50) < 1e-9)

# ------------------------------------------------------------------ 3. it carries the main's own read
ok("a main line that already favours us keeps that edge and adds to it",
   F(0.62, -7.5, -6.5, True, "NCAAB", "spr") > 0.62)
ok("a main line that is against us is not rescued by a tiny move",
   F(0.38, -7.5, -7.0, True, "NCAAB", "spr") < 0.50)
ok("probabilities stay inside [0.01, 0.99]",
   0.01 <= F(0.985, -20.5, 0.5, True, "NFL", "spr") <= 0.99 and
   0.01 <= F(0.015, 0.5, -20.5, False, "NFL", "spr") <= 0.99)

# ------------------------------------------------------------------ 4. wired in, and reversible
src = open("clv_ledger.py").read()
cf = src[src.index("def close_for("):src.index("MAX_NEW_MAIL")]
ok("V1 stays OFFICIAL: both branches return the quote read at our number as 'p'",
   cf.count('"p": _p1v') == 2, cf.count('"p": _p1v'))
ok("...and both still label it 'own line', unchanged from before",
   cf.count('"how": "own line"') == 2)
ok("V2 is computed alongside, from the main line", cf.count("fair_from_main(") == 2)
ok("V2 is carried in its own fields, never over V1",
   cf.count('"v2_p"') == 2 and cf.count('"v2_how"') == 2)
ok("V2 equals V1 whenever our number WAS the main line",
   cf.count("_p2v = _p1v if _at_main") == 2)
ok("a derived V2 is labelled distinctly from an observed close",
   cf.count('own line (from main') == 2)
ok("whether our number was the main line is recorded, so the two can be separated",
   cf.count('"at_main"') == 2)
ok("the shadow is stored by record_v2, which never writes clv or close_p",
   '"clv_v2"' in src and 'rec["clv"] =' not in src[src.index("def record_v2("):src.index("def fair_from_main(")])
ok("a model-derived fair is flagged so it is never called a certified same-line close",
   '"v2_derived"' in src)
ok("the no-quote path still exists for numbers Pinnacle never priced",
   'moved to' in cf and 'far from Pinnacle' in cf)
ok("CLV is still written at exactly one place in the ledger", src.count('rec["clv"] = ') == 1)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
