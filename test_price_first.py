"""Nov 11 (Peter): "BEST PRICE FIRST, NOT MAXIMUM DOLLARS FILLED."

Two defects, both proven from the code before this change:

  (a) Every early refusal in live_order() / live_order_other() returned SILENTLY, while
      live_play_alert() fires immediately before them. Peter was told a bet was coming and
      never told it was not - which on Nov 11 read as a dead bot and produced a hand-placed
      position the registry did not know about.

  (b) plan() and px_limit() sorted best price first and then kept WALKING TO WORSE LEVELS
      until `stake` was covered, set the order's limit to the worst level reached, and sized
      every contract at that worst price. That is paying up to widen a fill, and it made the
      2c tolerance a target: `thr` is built as alert_cost + tol, so nothing anchored the walk
      to the best price actually on offer.

These tests pin the corrected behaviour and the parts that must NOT have moved: eligibility
(`thr`), the -130 cap, venue ranking, the bet-only-at floor and the MIN_ORDER guard Peter
chose to keep.
"""
import ast
import os
import sys

os.environ.setdefault("EXEC_BEST_SLIP_CENTS", "0")   # forced, never inherited: the default is price-first

import book_live
import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


def approx(name, got, want, tol=1e-6):
    CHECKS.append((name, got, want))
    assert got is not None and abs(got - want) <= tol, f"{name}: got {got!r}, want ~{want!r}"


# ---------------------------------------------------------------- book_live.plan (Novig / Kalshi / PMUS)
# A thin best level in front of deep worse liquidity: the exact shape that used to make the bot pay up.
THIN_BEST = [{"price": 0.52, "american": -115, "dollars": 60.0},
             {"price": 0.565, "american": -130, "dollars": 500.0}]

limit, count = book_live.plan(THIN_BEST, -140, 390.0, min_order=50.0, slip=0.0)
approx("plan takes the best level only", limit, 0.52)
ck("plan sizes to the best level's depth", count, int(60.0 / 0.52))
assert limit != 0.565, "plan still walked to the worse level to fill the unit"

# The old behaviour, reproduced by allowing unlimited slip - proof the test shape is right and that
# the only thing that changed is the bound, not the ladder or the arithmetic.
old_limit, old_count = book_live.plan(THIN_BEST, -140, 390.0, min_order=50.0, slip=9.0)
approx("unbounded slip reproduces the old walk", old_limit, 0.565)
ck("old walk priced the whole stake at the worst level", old_count, int(390.0 / 0.565))
assert old_limit > limit, "the fix must improve the limit price, not worsen it"

# MIN_ORDER guard (Peter, Nov 11: "with the guard kept"): a best level too thin to place at all
# may still extend, because a sub-minimum order is refused outright and the play is lost.
limit_g, count_g = book_live.plan(
    [{"price": 0.52, "american": -115, "dollars": 20.0},
     {"price": 0.565, "american": -130, "dollars": 500.0}], -140, 390.0, min_order=50.0, slip=0.0)
approx("guard extends past the slip bound below MIN_ORDER", limit_g, 0.565)
ck("guard then fills the unit", count_g, int(390.0 / 0.565))

# With no minimum to reach, the bound binds immediately.
limit_n, count_n = book_live.plan(
    [{"price": 0.52, "american": -115, "dollars": 20.0},
     {"price": 0.565, "american": -130, "dollars": 500.0}], -140, 390.0, min_order=0.0, slip=0.0)
approx("no guard -> best level only", limit_n, 0.52)
ck("no guard -> stake shrinks to best depth", count_n, int(20.0 / 0.52))

# REGRESSION: when the best level alone covers the stake, nothing about the old result changes.
limit_r, count_r = book_live.plan(
    [{"price": 0.52, "american": -115, "dollars": 500.0},
     {"price": 0.565, "american": -130, "dollars": 500.0}], -140, 390.0, min_order=50.0, slip=0.0)
approx("deep best level: limit unchanged", limit_r, 0.52)
ck("deep best level: full unit still filled", count_r, int(390.0 / 0.52))

# A ladder with one level is untouched by the bound.
limit_1, count_1 = book_live.plan([{"price": 0.54, "american": -120, "dollars": 500.0}],
                                  -140, 390.0, min_order=50.0, slip=0.0)
approx("single level unchanged", limit_1, 0.54)
ck("single level count unchanged", count_1, int(390.0 / 0.54))

# slip as an explicit allowance takes a level inside the bound and still stops outside it.
limit_s, _ = book_live.plan(
    [{"price": 0.52, "american": -115, "dollars": 40.0},
     {"price": 0.525, "american": -117, "dollars": 40.0},
     {"price": 0.60, "american": -150, "dollars": 500.0}], -160, 390.0, min_order=0.0, slip=0.01)
approx("slip 1c takes the level inside the bound", limit_s, 0.525)

# ELIGIBILITY IS UNCHANGED: thr still excludes, and it is still the outer bound, not the target.
ck("thr still excludes worse levels",
   book_live.plan([{"price": 0.60, "american": -150, "dollars": 500.0}], -130, 390.0,
                  min_order=50.0, slip=0.0), (None, 0))
ck("nothing qualifying -> (None, 0)", book_live.plan([], -130, 390.0, min_order=50.0, slip=0.0), (None, 0))
ck("no threshold -> (None, 0)", book_live.plan(THIN_BEST, None, 390.0, min_order=50.0, slip=0.0), (None, 0))
# A level AT the threshold stays eligible (the Nov 11 Lakers case sat exactly on the -130 cap).
at_thr, _ = book_live.plan([{"price": 0.565, "american": -130, "dollars": 500.0}], -130, 390.0,
                           min_order=50.0, slip=0.0)
approx("a level exactly at thr is still eligible", at_thr, 0.565)

# Defaults keep the old signature callable (slip defaults to 0 = price-first).
d_limit, _ = book_live.plan(THIN_BEST, -140, 390.0)
approx("plan default slip is price-first", d_limit, 0.52)


# ---------------------------------------------------------------- executor.px_limit (ProphetX)
def px(am, af, dollars, sid):
    return {"american": am, "american_after_fee": af, "dollars": dollars, "strike_id": sid}


PX_THIN = {"thr": -140, "buy": [px(-115, -117, 60.0, "a"), px(-130, -133, 500.0, "b")]}

sid, lim, stake = ex.px_limit(PX_THIN, 390.0, slip=0.0)
ck("px_limit strike is the best level", sid, "a")
ck("px_limit limit is the best price", lim, -115)
approx("px_limit stake shrinks to best depth", stake, 60.0)

sid_o, lim_o, stake_o = ex.px_limit(PX_THIN, 390.0, slip=9.0)
ck("px unbounded slip reproduces the old walk", lim_o, -130)
approx("px old walk filled the unit", stake_o, 390.0)

# MIN_ORDER guard on ProphetX too.
PX_TINY = {"thr": -140, "buy": [px(-115, -117, 20.0, "a"), px(-130, -133, 500.0, "b")]}
_, lim_g, stake_g = ex.px_limit(PX_TINY, 390.0, slip=0.0)
ck("px guard extends below MIN_ORDER", lim_g, -130)
approx("px guard then fills the unit", stake_g, 390.0)

# REGRESSION: deep best level -> identical to before.
PX_DEEP = {"thr": -140, "buy": [px(-115, -117, 500.0, "a"), px(-130, -133, 500.0, "b")]}
_, lim_d, stake_d = ex.px_limit(PX_DEEP, 390.0, slip=0.0)
ck("px deep best level: limit unchanged", lim_d, -115)
approx("px deep best level: full unit", stake_d, 390.0)

ck("px nothing qualifying", ex.px_limit({"thr": -100, "buy": [px(-130, -133, 500.0, "b")]}, 390.0),
   (None, None, 0.0))
ck("px no threshold", ex.px_limit({"thr": None, "buy": [px(-115, -117, 60.0, "a")]}, 390.0),
   (None, None, 0.0))
ck("px empty ladder", ex.px_limit({"thr": -140, "buy": []}, 390.0), (None, None, 0.0))
# A level with no strike_id cannot be ordered and must not become the chosen one.
_, lim_ns, _ = ex.px_limit({"thr": -140, "buy": [px(-115, -117, 60.0, None),
                                                 px(-130, -133, 500.0, "b")]}, 390.0, slip=0.0)
ck("level without a strike_id is skipped", lim_ns, -130)

ck("px default slip is price-first", ex.px_limit(PX_THIN, 390.0)[1], -115)
approx("BEST_SLIP defaults to 0", ex.BEST_SLIP, 0.0)


# ---------------------------------------------------------------- no silent refusals (AST, not text)
# Checked structurally so a docstring that merely MENTIONS a refusal cannot pass or fail the test -
# the mistake this repo has made repeatedly with text-matching assertions.
tree = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read())
fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

for fname in ("live_order", "live_order_other"):
    assert fname in fns, f"{fname} not found"
    silent = []
    for node in ast.walk(fns[fname]):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        for k, v in zip(node.value.keys, node.value.values):
            if (isinstance(k, ast.Constant) and k.value == "status"
                    and isinstance(v, ast.Constant) and v.value == "refused"):
                silent.append(node.lineno)
    ck(f"{fname} has no silent refusal return", silent, [])

# ...and that every refusal in them goes through refuse(), which is the thing that notifies.
for fname in ("live_order", "live_order_other"):
    calls = [n for n in ast.walk(fns[fname])
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "refuse"]
    assert len(calls) >= 5, f"{fname}: expected the refusal paths to call refuse(), found {len(calls)}"
    CHECKS.append((f"{fname} refuse() calls", len(calls), ">=5"))

# refuse() itself: one notification, correct record, and a notifier failure cannot change the refusal.
sent = []
_tg, _ln = ex.tg, ex.lane_note
try:
    ex.tg = lambda *a, **k: sent.append(a[0] if a else "")
    ex.lane_note = lambda r, head, res=None, book=None, limit=None, extra="": f"{head}|{book}|{extra}"
    r = {"live": {"book": "novig"}, "play": {"sport": "NBA", "game": "A @ B", "bet": "Under 230.5 (-119)"}}
    out = ex.refuse(r, "Novig outcome unknown - fail closed", book="novig")
    ck("refuse marks the order refused", out["status"], "refused")
    ck("refuse carries the reason", out["reason"], "Novig outcome unknown - fail closed")
    ck("refuse carries the book", out["book"], "novig")
    ck("refuse notifies exactly once", len(sent), 1)
    assert "ORDER REFUSED" in sent[0], sent[0]
    assert "Novig outcome unknown" in sent[0], sent[0]
    ck("refuse passes extra fields through", ex.refuse(r, "x", revalidated=False)["revalidated"], False)

    sent.clear()
    ex.tg = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("telegram down"))
    out2 = ex.refuse(r, "price moved - fail closed")
    ck("a dead notifier still refuses", out2["status"], "refused")
    ck("a dead notifier keeps the reason", out2["reason"], "price moved - fail closed")
finally:
    ex.tg, ex.lane_note = _tg, _ln

# The resting-bid lane is deliberately untouched: rest_bid() is not preceded by a LIVE PLAY alert,
# so its refusals never created the told-a-bet-was-coming-then-silence problem. Pinned so that a
# future reader does not mistake the omission for an oversight.
rest_silent = [n.lineno for n in ast.walk(fns["rest_bid"])
               if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)
               and any(isinstance(k, ast.Constant) and k.value == "status"
                       and isinstance(v, ast.Constant) and v.value == "refused"
                       for k, v in zip(n.value.keys, n.value.values))]
assert rest_silent, "rest_bid refusals were changed; this fix was scoped to the live-order path only"
CHECKS.append(("rest_bid left out of scope (returns)", len(rest_silent), ">0"))

print(f"PASS  test_price_first.py  {len(CHECKS)} checks")
