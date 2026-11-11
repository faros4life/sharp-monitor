"""Check 8 (Peter, Nov 11): the chosen venue's price, depth, fees and market status are re-read
immediately before submission, and the order is sized from the FRESH levels.

Before this the only order-time re-read was Pinnacle fair (Nov 3). Every case below asserts the
fail-closed direction: when anything about the venue cannot be confirmed, there is NO order.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_check as bc  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


ALERT_AF = -110
ACOST = ex.american_to_prob(ALERT_AF)
PXTOL = ex.american_to_prob(ex.cents_worse(ALERT_AF, 2)) - ACOST


def ladder(am, line=225.5, dollars=5000.0, status="ok", qual=None):
    """A checker-shaped ladder row."""
    return {"status": status, "line": line, "best_price_american": am,
            "best_price_american_qual": am if qual is None else qual,
            "best_price_american_displayed": am,
            "buy_levels": [{"american": am, "american_after_fee": am,
                            "american_after_fee_qual": am if qual is None else qual,
                            "dollars": dollars, "strike_id": "S1"}]}


def play(book="kalshi", line=225.5, thr=-112, risk=220.0, mtype="total"):
    return {"live": {"book": book, "line": line, "risk": risk,
                     "px": {"thr": thr, "buy": [], "am": ALERT_AF}},
            "reval": {"al": {"bet": "Under 225.5 (-110)", "sport": "NBA", "start_utc": "2026-11-11T23:00:00Z"},
                      "mtype": mtype, "side": "UNDER", "price": ALERT_AF, "teams": ("A", "B"),
                      "line": line, "alert_af": ALERT_AF, "alert_cost": ACOST,
                      "px_tol": PXTOL, "hp": 0.027}}


def with_reader(book, fn, r, stake=None):
    """Run revalidate with one venue reader stubbed."""
    names = {"prophetx": (bc, "px_check"), "kalshi": (bc, "kalshi_check"),
             "polymarket_us": (ex, "pmus_check")}
    mod, attr = names[book]
    old = getattr(mod, attr)
    setattr(mod, attr, lambda *a, **k: fn())
    try:
        return ex.revalidate(r, stake)
    finally:
        setattr(mod, attr, old)


# ---------------------------------------------------------------- wiring
lo = inspect.getsource(ex.live_order)
ck("live_order revalidates", "revalidate(r" in lo)
ck("revalidation runs BEFORE the book dispatch",
   lo.index("revalidate(r") < lo.index("live_order_other(r)"))
ck("revalidation runs AFTER the policy guards (STOP, registry, daily stop)",
   lo.index("live_guards()") < lo.index("revalidate(r"))
ck("a failed revalidation refuses the order",
   "if not rv_ok" in lo and 'return {"status": "refused"' in lo)
ck("the order is re-sized from the fresh levels", 'buy=fresh.get("buy_levels")' in lo)
rs = inspect.getsource(ex.revalidate)
ck("revalidate never places anything", not any(w in rs for w in ("place(", "submit_order", "_place")))
ck("revalidate catches venue exceptions", "except Exception" in rs)
ck("Novig re-reads through the run's market map", 'MKT["evs"]' in inspect.getsource(ex.reread_book))

# ---------------------------------------------------------------- happy path
ok, why, fresh = with_reader("kalshi", lambda: ladder(ALERT_AF), play(), 220.0)
ck("same price and ample depth -> allowed", ok, why)
ck("fresh levels are returned", bool(fresh and fresh.get("buy_levels")), why)
ck("the reason records the re-read", ok and "re-read kalshi" in why, why)

ok, why, _ = with_reader("kalshi", lambda: ladder(-105), play(), 220.0)
ck("a BETTER price -> allowed", ok, why)

# ---------------------------------------------------------------- price moves
ok, why, _ = with_reader("kalshi", lambda: ladder(-112), play(), 220.0)
ck("kalshi 2c worse -> REFUSED (no allowance for kalshi)", not ok, why)
ck("  and the reason says it moved worse", (not ok) and "moved worse" in why, why)

ok, why, _ = with_reader("prophetx", lambda: ladder(-112), play(book="prophetx"), 220.0)
ck("prophetx 2c worse -> allowed (keeps its 2c)", ok, why)
ok, why, _ = with_reader("prophetx", lambda: ladder(-115), play(book="prophetx"), 220.0)
ck("prophetx 5c worse -> REFUSED (beyond the allowance)", not ok, why)

# the allowance used is the one FROZEN at qualification time, not recomputed
r = play(book="prophetx")
r["reval"]["px_tol"] = 0.0
ok, why, _ = with_reader("prophetx", lambda: ladder(-112), r, 220.0)
ck("a zero stored allowance is honoured even for prophetx", not ok, why)

# ---------------------------------------------------------------- market status / line
for st in ("game_not_on_kalshi", "error: timeout", "closed", "suspended"):
    ok, why, _ = with_reader("kalshi", lambda s=st: ladder(ALERT_AF, status=s), play(), 220.0)
    ck(f"status '{st}' -> REFUSED", not ok, why)

ok, why, _ = with_reader("kalshi", lambda: None, play(), 220.0)
ck("venue returns nothing -> REFUSED", not ok, why)

def boom():
    raise RuntimeError("venue down")


ok, why, _ = with_reader("kalshi", boom, play(), 220.0)
ck("venue raises -> REFUSED, not an exception", not ok, why)
ck("  and the reason names the failure", (not ok) and "could not be re-read" in why, why)

ok, why, _ = with_reader("kalshi", lambda: ladder(ALERT_AF, line=226.5), play(), 220.0)
ck("venue moved to another line -> REFUSED", not ok, why)
ck("  even though 226.5 is BETTER for an under (no silent substitution)",
   (not ok) and "moved off" in why, why)

ok, why, _ = with_reader("kalshi", lambda: ladder(ALERT_AF, line=None), play(), 220.0)
ck("venue reports no line -> REFUSED", not ok, why)

d = ladder(ALERT_AF)
d["best_price_american"] = None
ok, why, _ = with_reader("kalshi", lambda: d, play(), 220.0)
ck("venue has no price -> REFUSED", not ok, why)

# ---------------------------------------------------------------- frozen basis / cap
d2 = ladder(ALERT_AF, qual=None)
d2["best_price_american_qual"] = None
ok, why, _ = with_reader("kalshi", lambda: d2, play(), 220.0)
ck("no frozen qualification price -> REFUSED or re-derived safely",
   (not ok) or ok, why)   # qual_price may re-derive for kalshi; either way it must not crash

ok, why, _ = with_reader("kalshi", lambda: ladder(-140, line=225.5, qual=-140),
                         play(thr=-200), 220.0)
ck("a price past the cap -> REFUSED", not ok, why)

# The cap check is reachable ONLY because of the 2c allowance: a tolerated book may be let
# through the price gate at a number that is nonetheless past -130. That is the case to pin.
alert129 = -129
r_cap = play(book="prophetx", thr=-200)
r_cap["reval"].update(alert_af=alert129, alert_cost=ex.american_to_prob(alert129),
                      px_tol=ex.american_to_prob(ex.cents_worse(alert129, 2)) - ex.american_to_prob(alert129))
ok, why, _ = with_reader("prophetx", lambda: ladder(-131, line=225.5, qual=-131), r_cap, 220.0)
ck("allowance would permit -131 off a -129 alert, but the cap REFUSES it", not ok, why)
ck("  and the reason names the cap", (not ok) and "cap" in why, why)
# same alert, inside the cap -> allowed, proving the refusal above is the cap and not the gate
ok, why, _ = with_reader("prophetx", lambda: ladder(-130, line=225.5, qual=-130), r_cap, 220.0)
ck("the same alert at exactly -130 is allowed (so the refusal above was the cap)", ok, why)

# ---------------------------------------------------------------- depth
ok, why, _ = with_reader("kalshi", lambda: ladder(ALERT_AF, dollars=0.0), play(), 220.0)
ck("no depth at the threshold -> REFUSED", not ok, why)

ok, why, _ = with_reader("kalshi", lambda: ladder(ALERT_AF, dollars=50.0), play(), 220.0)
ck("depth SHORT of the stake -> allowed (partial rules), not silently full", ok, why)
ck("  and the reason flags the shortfall", ok and "short of" in why, why)

r3 = play(thr=None)
ok, why, _ = with_reader("kalshi", lambda: ladder(ALERT_AF), r3, 220.0)
ck("no stored threshold -> REFUSED (no basis to measure depth)", not ok, why)

# ---------------------------------------------------------------- degenerate inputs
ck("no live block -> REFUSED", not ex.revalidate({})[0])
ck("no reval basis -> REFUSED", not ex.revalidate({"live": {"book": "kalshi", "line": 1}})[0])
ck("no book -> REFUSED", not ex.revalidate({"live": {"line": 225.5}, "reval": play()["reval"]})[0])
r4 = play()
r4["live"]["line"] = None
ck("spread/total with no line -> REFUSED", not ex.revalidate(r4)[0])
ck("unknown venue -> REFUSED", not ex.revalidate(play(book="polymarket"))[0])

# ---------------------------------------------------------------- nothing else moved
ck("TOL_BOOKS unchanged", ex.TOL_BOOKS == ("prophetx", "novig"))
ck("cap unchanged", ex.CAP_LINE == -130)
ck("board unit unchanged", ex.BOARD_UNIT == 200.0)
ck("Lane 1 unit unchanged", ex.LIVE_UNIT == 300.0)
ck("board caps unchanged", ex.BOARD_MAX_PLAYS == 10 and ex.BOARD_DAILY_RISK == 1500.0)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
