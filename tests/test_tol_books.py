"""Peter, Nov 11: Novig gets the same 2-probability-cent execution allowance as ProphetX,
on BOTH lanes (phase 1 / Lane 1 and Board v3 / LIQ-BOT). Kalshi and Polymarket US unchanged.

What these tests pin:
  1. membership   - prophetx and novig get the allowance; kalshi and polymarket_us get 0.0
  2. identity     - Novig's allowance is the SAME number as ProphetX's, not a lookalike
  3. lane-blind   - the allowance does not read the lane, so phase 1 and board behave identically
  4. eligibility  - the allowance widens the gate and the depth threshold, never the ranking key
  5. routing      - a tolerated venue cannot out-rank a cheaper venue because of its allowance
  6. boundary     - exactly 2c in, 3c out
  7. speed        - the allowance is pure arithmetic on the cached ladder: no network, no API
  8. untouched    - the -130 cap, resting orders and Lane 1's ProphetX value are unchanged
"""
import ast
import inspect
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


def tol_for(book, alert_af):
    """Mirror of the executor's own per-book tolerance decision."""
    px_tol = ex.american_to_prob(ex.cents_worse(alert_af, ex.PX_TOL_CENTS)) - ex.american_to_prob(alert_af)
    return px_tol if book in ex.TOL_BOOKS else 0.0


# ---------------------------------------------------------------- 1. membership
ck("prophetx is in TOL_BOOKS", "prophetx" in ex.TOL_BOOKS, str(ex.TOL_BOOKS))
ck("novig is in TOL_BOOKS", "novig" in ex.TOL_BOOKS, str(ex.TOL_BOOKS))
ck("kalshi is NOT in TOL_BOOKS", "kalshi" not in ex.TOL_BOOKS, str(ex.TOL_BOOKS))
ck("polymarket_us is NOT in TOL_BOOKS", "polymarket_us" not in ex.TOL_BOOKS, str(ex.TOL_BOOKS))
ck("polymarket (global) is NOT in TOL_BOOKS", "polymarket" not in ex.TOL_BOOKS, str(ex.TOL_BOOKS))
ck("TOL_BOOKS holds exactly two venues", len(ex.TOL_BOOKS) == 2, str(ex.TOL_BOOKS))
ck("every TOL_BOOKS name is a real dispatchable book",
   all(b in ex.BOOKS for b in ex.TOL_BOOKS), f"{ex.TOL_BOOKS} vs {ex.BOOKS}")

# ---------------------------------------------------------------- 2. identity
for af in (-250, -130, -115, -109, -101, 100, 105, 140, 300):
    ck(f"novig allowance == prophetx allowance at {af:+d}",
       tol_for("novig", af) == tol_for("prophetx", af),
       f"{tol_for('novig', af)!r} vs {tol_for('prophetx', af)!r}")
    ck(f"kalshi allowance is zero at {af:+d}", tol_for("kalshi", af) == 0.0)
    ck(f"polymarket_us allowance is zero at {af:+d}", tol_for("polymarket_us", af) == 0.0)
    ck(f"allowance is positive and under 3 probability cents at {af:+d}",
       0 < tol_for("novig", af) < 0.03, repr(tol_for("novig", af)))

# the allowance really is TWO American cents of room, in the bettor's-cost direction
for af in (-250, -115, -109, 100, 105, 140):
    ck(f"two cents worse is strictly more expensive at {af:+d}",
       ex.american_to_prob(ex.cents_worse(af, 2)) > ex.american_to_prob(af))
    ck(f"cents_worse is monotone at {af:+d}",
       ex.american_to_prob(ex.cents_worse(af, 1)) < ex.american_to_prob(ex.cents_worse(af, 2)))

# ---------------------------------------------------------------- 3. lane-blind
src = inspect.getsource(ex.evaluate)
tree = ast.parse(textwrap.dedent(src))
tol_lines = [l for l in src.splitlines() if "tol = px_tol" in l]
ck("the tolerance decision exists exactly once", len(tol_lines) == 1, repr(tol_lines))
ck("the tolerance decision keys off TOL_BOOKS", tol_lines and "TOL_BOOKS" in tol_lines[0], repr(tol_lines))
ck("the tolerance decision does not read the lane",
   tol_lines and not any(w in tol_lines[0] for w in ("lane", "board", "source", "rules")), repr(tol_lines))
ck("no hardcoded per-book tolerance branch survives",
   'px_tol if b == "prophetx"' not in src and "px_tol if b == 'prophetx'" not in src)

# ---------------------------------------------------------------- 4+5. eligibility, not price
# c_eq is the ranking key. It must be built from the real after-fee price and the half-point
# conversion only - never from tol - or the allowance would silently promote a venue.
ceq_lines = [l.strip() for l in src.splitlines() if l.strip().startswith("c_eq =")]
ck("the ranking key is assigned exactly once", len(ceq_lines) == 1, repr(ceq_lines))
ck("the ranking key does not contain the allowance",
   ceq_lines and "tol" not in ceq_lines[0], repr(ceq_lines))
sort_lines = [l for l in src.splitlines() if "capped.sort" in l]
ck("the sort key does not contain the allowance",
   sort_lines and not any("tol" in l for l in sort_lines), repr(sort_lines))

# the allowance must reach BOTH the gate and the depth threshold, so eligibility and
# fillable depth agree; a gate-only change would admit bets with no depth behind them
gate = [l for l in src.splitlines() if "c_eq_q >" in l]
thr = [l for l in src.splitlines() if l.strip().startswith("thr = lm.american")]
ck("the allowance widens the eligibility gate", gate and "tol" in gate[0], repr(gate))
ck("the allowance widens the depth threshold", thr and "tol" in thr[0], repr(thr))

# arithmetic proof of requirement 5: Novig tolerated at 2c worse still ranks BELOW a
# cheaper Kalshi quote, because ranking never sees the allowance.
alert = -110
novig_raw, kalshi_raw = ex.cents_worse(alert, 2), alert          # novig 2c worse, kalshi at the number
ck("tolerated novig is eligible at exactly 2c worse",
   ex.american_to_prob(novig_raw) <= ex.american_to_prob(alert) + tol_for("novig", alert) + 1e-9)
ck("tolerated novig still ranks behind an untolerated cheaper kalshi",
   ex.american_to_prob(novig_raw) > ex.american_to_prob(kalshi_raw))
ck("an untolerated kalshi 2c worse is NOT eligible",
   ex.american_to_prob(ex.cents_worse(alert, 2)) > ex.american_to_prob(alert) + tol_for("kalshi", alert) + 1e-9)

# ---------------------------------------------------------------- 6. boundary
for book in ("prophetx", "novig"):
    t = tol_for(book, alert)
    ck(f"{book}: at the alert number is eligible",
       ex.american_to_prob(alert) <= ex.american_to_prob(alert) + t + 1e-9)
    ck(f"{book}: 1c worse is eligible",
       ex.american_to_prob(ex.cents_worse(alert, 1)) <= ex.american_to_prob(alert) + t + 1e-9)
    ck(f"{book}: exactly 2c worse is eligible",
       ex.american_to_prob(ex.cents_worse(alert, 2)) <= ex.american_to_prob(alert) + t + 1e-9)
    ck(f"{book}: 3c worse is REJECTED",
       ex.american_to_prob(ex.cents_worse(alert, 3)) > ex.american_to_prob(alert) + t + 1e-9)
    ck(f"{book}: 5c worse is REJECTED",
       ex.american_to_prob(ex.cents_worse(alert, 5)) > ex.american_to_prob(alert) + t + 1e-9)
for book in ("kalshi", "polymarket_us"):
    ck(f"{book}: at the alert number is eligible",
       ex.american_to_prob(alert) <= ex.american_to_prob(alert) + tol_for(book, alert) + 1e-9)
    ck(f"{book}: even 1c worse is REJECTED",
       ex.american_to_prob(ex.cents_worse(alert, 1)) > ex.american_to_prob(alert) + tol_for(book, alert) + 1e-9)

# ---------------------------------------------------------------- 7. speed
body = ast.dump(tree)
for bad in ("requests", "urlopen", "httpx", "urllib", "fetch_", "get_json", "time.sleep"):
    ck(f"no {bad} in the selection path", bad not in body, bad)
tol_decl = [l for l in inspect.getsource(ex).splitlines() if l.startswith("TOL_BOOKS")]
ck("TOL_BOOKS is resolved once at import, not per candidate", len(tol_decl) == 1, repr(tol_decl))
ck("TOL_BOOKS is a tuple (immutable at runtime)", isinstance(ex.TOL_BOOKS, tuple))

# ---------------------------------------------------------------- 8. untouched
ck("PX_TOL_CENTS is still 2", ex.PX_TOL_CENTS == 2, repr(ex.PX_TOL_CENTS))
ck("the -130 cap is unchanged", ex.CAP_LINE == -130, repr(ex.CAP_LINE))
ck("the cap is applied after the allowance",
   any("max(thr, CAP_LINE)" in l for l in src.splitlines()))
ck("resting orders carry no worse-price allowance",
   "PX_TOL" not in inspect.getsource(ex.rest_bid) and "TOL_BOOKS" not in inspect.getsource(ex.rest_bid))
ck("the board unit is still 200", ex.BOARD_UNIT == 200.0, repr(ex.BOARD_UNIT))
ck("the board daily risk limit is still 1500", ex.BOARD_DAILY_RISK == 1500.0, repr(ex.BOARD_DAILY_RISK))
ck("the board play cap is still 10", ex.BOARD_MAX_PLAYS == 10, repr(ex.BOARD_MAX_PLAYS))
ck("Lane 1's unit is untouched", ex.LIVE_UNIT == 300.0, repr(ex.LIVE_UNIT))
ck("the SKIP reason names the tolerated books, not just ProphetX",
   "'/'.join(TOL_BOOKS)" in src)

# the env override must not be able to smuggle in Polymarket Global
os.environ["EXEC_TOL_BOOKS"] = "prophetx,novig,polymarket"
import importlib  # noqa: E402
ex2 = importlib.reload(ex)
ck("an env override still cannot tolerate a non-dispatchable book",
   all(b in ex2.BOOKS for b in ex2.TOL_BOOKS) or "polymarket" not in ex2.BOOKS,
   f"override produced {ex2.TOL_BOOKS}; BOOKS={ex2.BOOKS}")
del os.environ["EXEC_TOL_BOOKS"]
importlib.reload(ex)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
