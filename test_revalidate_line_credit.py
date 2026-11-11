"""Nov 11: revalidate() dropped the half-point credit, so it refused plays routed to a better line.

evaluate()'s gate:    c_eq_q = american_to_prob(am_q) - hb * hp ;  refuse if c_eq_q > alert_cost + tol
revalidate()'s gate:          american_to_prob(am_q)            ;  refuse if that    > alert_cost + tol

A better line always carries a WORSE raw price - that is the reason for taking it - so comparing the
raw price at the ROUTED line against the bar for the ALERT line refused the play at the last gate,
and (before today's refuse() change) refused it silently.

Reproduced from the real ledger row of the Nov 11 Denver vs Memphis board play:
  alert   Under 230.5 at -100 (kalshi)
  routed  novig Under 231.5 at -111, its own thr -118, equivalent +104 at 230.5
  refused "novig moved worse than the alert gate before the order (now -111, allowed -102)"
  -102 is the 230.5 candidate's threshold. The play was judged against another line's bar.
"""
import os
import sys

import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


def cents_tol(alert_af, cents=2):
    return ex.american_to_prob(ex.cents_worse(alert_af, cents)) - ex.american_to_prob(alert_af)


def scenario(alert_af, alert_line, fill_line, fresh_am, thr, hp, book="novig", mtype="total",
             side="UNDER", tol_cents=2):
    """A play that qualified at `alert_af` on `alert_line` and routed to `fill_line`."""
    return {
        "live": {"book": book, "line": fill_line, "px": {"thr": thr}, "risk": 333.0},
        "reval": {"al": "x", "mtype": mtype, "side": side, "price": alert_af, "teams": ("A", "B"),
                  "line": alert_line, "alert_af": alert_af,
                  "alert_cost": ex.american_to_prob(alert_af),
                  "px_tol": cents_tol(alert_af, tol_cents), "hp": hp},
        "play": {"sport": "NBA", "game": "A vs B", "bet": f"Under {alert_line} ({alert_af})"},
    }


def with_book(fresh, fn):
    """Run fn with reread_book stubbed to return `fresh`."""
    orig = ex.reread_book
    try:
        ex.reread_book = lambda book, ln, rv: fresh
        return fn()
    finally:
        ex.reread_book = orig


def ladder(am, line, dollars=3020.0):
    return {"status": "ok", "best_price_american": am, "best_price_american_qual": am,
            "best_price_american_displayed": am, "line": line, "point": line,
            "buy_levels": [{"price": ex.american_to_prob(am), "american": am, "dollars": dollars}],
            "outcome_id": "oid-1"}


# ---------------------------------------------------------------- the real Denver vs Memphis row
DEN = scenario(alert_af=-100, alert_line=230.5, fill_line=231.5, fresh_am=-111, thr=-118, hp=0.018)
ok, why, fresh = with_book(ladder(-111, 231.5), lambda: ex.revalidate(DEN, 333.0))
ck("the real Nov 11 board play now revalidates", ok, True)
assert "re-read novig at order time" in why, why
assert fresh is not None

# The arithmetic the fix restores, stated explicitly so the test documents the bar.
hb = ex.better_halfpoints("total", "UNDER", 230.5, 231.5)
ck("231.5 is two half points better than 230.5 for an under", hb, 2)
c_eq_q = ex.american_to_prob(-111) - hb * 0.018
bar = ex.american_to_prob(-100) + cents_tol(-100, 2)
assert c_eq_q <= bar + 1e-9, f"equivalent {c_eq_q} must clear the bar {bar}"
assert ex.american_to_prob(-111) > bar + 1e-9, "the RAW price must fail it - that was the bug"
CHECKS.append(("raw fails, equivalent clears", round(ex.american_to_prob(-111) - c_eq_q, 4), 0.036))

# ---------------------------------------------------------------- the gate still bites when it should
# Same play, but the venue has genuinely moved past the allowance at its own line.
ok_w, why_w, _ = with_book(ladder(-150, 231.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 231.5, -150, -118, 0.018), 333.0))
ck("a genuine adverse move is still refused", ok_w, False)
assert "moved worse than the alert gate" in why_w, why_w
# The message must now name BOTH lines, so it can never again quote one line's bar against
# another line's price - the thing that made the Nov 11 refusal unreadable.
assert "231.5" in why_w and "230.5" in why_w, why_w
assert "-118" in why_w, f"the refusal must quote the routed line's own threshold: {why_w}"

# No line improvement: the equivalent price IS the raw price, so behaviour is unchanged.
ok_s, _, _ = with_book(ladder(-101, 230.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 230.5, -101, -102, 0.018), 333.0))
ck("same line, inside the allowance: unchanged pass", ok_s, True)
ok_s2, why_s2, _ = with_book(ladder(-140, 230.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 230.5, -140, -102, 0.018), 333.0))
ck("same line, outside the allowance: unchanged refusal", ok_s2, False)

# A WORSE line is still rejected outright by the line check, before any price arithmetic -
# "original alert line or strictly better" (Peter) is untouched by this fix.
ok_bad, why_bad, _ = with_book(ladder(-100, 229.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 231.5, -100, -118, 0.018), 333.0))
ck("a venue that moved off the chosen line is refused", ok_bad, False)
assert "moved off" in why_bad, why_bad

# hp = 0 (no live ladder basis) gives NO credit, so the fix cannot invent one.
ok_h, _, _ = with_book(ladder(-111, 231.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 231.5, -111, -118, 0.0), 333.0))
ck("hp 0 grants no credit (fails closed, as before)", ok_h, False)

# A non-tolerance book gets no 2c allowance, same as evaluate().
ok_k, _, _ = with_book(ladder(-111, 231.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 231.5, -111, -118, 0.0005, book="kalshi"), 333.0))
ck("kalshi gets no tolerance, unchanged", ok_k, False)
assert "novig" in str(ex.TOL_BOOKS) and "prophetx" in str(ex.TOL_BOOKS)
assert "kalshi" not in ex.TOL_BOOKS, "the tolerance must stay ProphetX + Novig only"

# The -130 cap on the RAW taken price is deliberately unchanged (Peter, Oct 28: "never fill below
# the -130 cap, whatever the line conversion says"). A big line credit must not buy past it.
ok_c, why_c, _ = with_book(ladder(-135, 231.5), lambda: ex.revalidate(
    scenario(-100, 230.5, 231.5, -135, -140, 0.060), 333.0))
ck("the -130 cap still binds despite a large line credit", ok_c, False)
assert str(ex.CAP_LINE) in why_c, why_c

# Depth is still required at the routed line's own threshold.
thin = ladder(-111, 231.5, dollars=0.0)
ok_d, why_d, _ = with_book(thin, lambda: ex.revalidate(DEN, 333.0))
ck("no depth at the threshold is still refused", ok_d, False)
assert "depth" in why_d, why_d

# Depth short of the stake is NOT a refusal - it flows to the partial shrink.
ok_p, why_p, _ = with_book(ladder(-111, 231.5, dollars=120.0), lambda: ex.revalidate(DEN, 333.0))
ck("short depth passes and flags a partial", ok_p, True)
assert "short of" in why_p and "partial" in why_p, why_p

# Unreadable / closed venue: unchanged fail-closed.
ck("unreadable venue", with_book(None, lambda: ex.revalidate(DEN, 333.0))[0], False)
ck("closed market", with_book({"status": "closed"}, lambda: ex.revalidate(DEN, 333.0))[0], False)
ck("no reval basis", ex.revalidate({"live": {"book": "novig", "line": 231.5}}, 333.0)[0], False)


def thrower(*a, **k):
    raise RuntimeError("venue down")


_o = ex.reread_book
try:
    ex.reread_book = thrower
    ck("a throwing venue read fails closed", ex.revalidate(DEN, 333.0)[0], False)
finally:
    ex.reread_book = _o

print(f"PASS  test_revalidate_line_credit.py  {len(CHECKS)} checks")
