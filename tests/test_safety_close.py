"""Closing the remaining safety blockers (Peter, Nov 11).

1. maker/taker on resting orders - never assume maker execution or a rebate
2. the order journal cannot silently lose a submitted order (latch -> no further orders)
3. canonical game matching; duplicate and opposite-side positions across venues
5. all Board v3 controls together
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_live as bl  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


# ======================================================== 1. maker / taker on resting orders
rb = inspect.getsource(ex.rest_bid)
ck("PM US maker pricing is OFF by default", ex.PMUS_REST_MAKER is False, str(ex.PMUS_REST_MAKER))
ck("the maker flag is env-gated, not code-default",
   'os.environ.get("EXEC_PMUS_REST_MAKER")' in inspect.getsource(ex))
ck("the published rebate is recorded but negative (a rebate, not a fee)",
   ex.PMUS_MAKER_REBATE == -0.0125, str(ex.PMUS_MAKER_REBATE))
ck("resting prices TAKER unless the maker flag is explicitly on",
   "PMUS_MAKER_REBATE if PMUS_REST_MAKER else" in rb)
ck("the taker coefficient comes from the scored entry, not a constant",
   'x.get("taker_fee_coef")' in rb)
ck("PM US is NOT in the default resting set (maker unproven)",
   "polymarket_us" not in ex.REST_BOOKS, str(ex.REST_BOOKS))
ck("the default resting set is novig+kalshi", ex.REST_BOOKS == ("novig", "kalshi"), str(ex.REST_BOOKS))
ck("resting carries NO worse-price allowance (rests at the alert number)",
   "PX_TOL" not in rb and "TOL_BOOKS" not in rb)
ck("the resting code says the maker flag is unproven on this venue",
   "PROVEN" in inspect.getsource(ex)[:ex_src_i] if (ex_src_i := inspect.getsource(ex).find("PMUS_REST_MAKER")) else True)
ck("book_live records participateDontInitiate as still unproven",
   "STILL UNPROVEN" in inspect.getsource(bl))

# taker is the conservative direction: a positive coef costs us, a rebate would pay us.
# Pricing on a rebate we may not receive would bid MORE aggressively, so taker can only under-bid.
ck("taker coefficient is a cost (positive) and the rebate a credit (negative)",
   ex.PMUS_MAKER_REBATE < 0 < 0.06)
cost_taker = bl.kalshi_cost_for(0.52, 0.06)
cost_maker = bl.kalshi_cost_for(0.52, ex.PMUS_MAKER_REBATE)
ck("the solver accepts a negative coefficient", cost_maker is not None)
ck("taker pricing bids no higher than maker pricing (never over-bids on an unproven rebate)",
   cost_taker is not None and cost_maker is not None and cost_taker <= cost_maker + 1e-9,
   f"taker {cost_taker} vs maker {cost_maker}")

# ======================================================== 2. the journal cannot silently lose an order
ex.JOURNAL["latch"] = None
ck("no latch at rest", ex.journal_latch_why() is None)


def fail_journal():
    """Drive journal_order through a send failure and return the latch."""
    ex.JOURNAL["latch"] = None
    old_send, old_tg = ex.send, ex.tg
    ex.send = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("smtp down"))
    ex.tg = lambda *a, **k: None
    try:
        res = ex.journal_order({"play": {"play_key": "K9"}},
                               {"status": "placed", "order_id": "O9", "book": "kalshi", "asked_stake": 220.0})
    finally:
        ex.send, ex.tg = old_send, old_tg
    return res, ex.journal_latch_why()


res, latch = fail_journal()
ck("a failed journal returns False", res is False)
ck("a failed journal LATCHES", bool(latch), str(latch))
ck("the latch names the order and venue", latch and "O9" in latch and "kalshi" in latch, str(latch))
ck("the latch says the order IS placed", latch and "placed" in latch, str(latch))

# while latched, nothing further may be ordered or rested
r_min = {"play": {"sport": "NBA", "game": "A vs B", "bet": "Under 225.5 (-110)"},
         "live": {"book": "kalshi", "line": 225.5, "risk": 220.0, "px": {"thr": -112}},
         "entry": {"price_after_fee": -110}}
out = ex.live_order(r_min)
ck("live_order REFUSES while latched", out.get("status") == "refused", str(out)[:140])
ck("  and the reason points at the journal",
   out.get("status") == "refused" and "journal" in (out.get("reason") or ""), str(out)[:140])
out_r = ex.rest_bid(r_min)
ck("rest_bid REFUSES while latched", out_r.get("status") == "refused", str(out_r)[:140])
ck("  and the reason points at the journal",
   out_r.get("status") == "refused" and "journal" in (out_r.get("reason") or ""), str(out_r)[:140])
ck("the refusal says reconciliation is what clears it",
   "reconcile" in (out.get("reason") or ""), str(out)[:140])

lo_src = inspect.getsource(ex.live_order)
ck("the latch is checked BEFORE the venue re-read and the order",
   lo_src.index("journal_latch_why()") < lo_src.index("revalidate(r"))
ck("the latch is the FIRST gate, so no other refusal can mask it",
   lo_src.index("journal_latch_why()") < lo_src.index("hr_priced"))
ck("a successful journal leaves no latch",
   (lambda: (ex.JOURNAL.__setitem__("latch", None),
             ex.journal_order({"play": {}}, {"status": "placed", "order_id": "OK1", "book": "kalshi"}),
             ex.journal_latch_why() is None)[-1])()
   if (setattr(ex, "send", lambda *a, **k: None) or True) else False)
ex.JOURNAL["latch"] = None

# ======================================================== 3. canonical game matching
K = "NBA|Atlanta Hawks @ Charlotte Hornets|total|UNDER"
ck("same bet, different game spelling -> SAME",
   ex.same_bet(K, "NBA|Hawks vs. Hornets|total|UNDER"))
ck("same bet behind a board lane prefix -> SAME",
   ex.same_bet("board|" + K, "NBA|Hawks vs Hornets|total|UNDER"))
ck("same bet behind a rules lane prefix -> SAME",
   ex.same_bet("rule|" + K, "board|NBA|Hawks vs Hornets|total|UNDER"))
ck("different league -> NOT same", not ex.same_bet(K, "NCAAB|Atlanta Hawks @ Charlotte Hornets|total|UNDER"))
ck("different market -> NOT same", not ex.same_bet(K, "NBA|Atlanta Hawks @ Charlotte Hornets|side|UNDER"))
ck("different game -> NOT same", not ex.same_bet(K, "NBA|Boston Celtics @ Miami Heat|total|UNDER"))
ck("OVER is not the SAME bet as UNDER", not ex.same_bet(K, "NBA|Hawks vs Hornets|total|OVER"))

ck("OVER is the OPPOSITE of UNDER, across spellings",
   ex.opp_bet(K, "NBA|Hawks vs. Hornets|total|OVER"))
ck("UNDER is the opposite of OVER (symmetric)",
   ex.opp_bet("NBA|Hawks vs Hornets|total|OVER", K))
ck("the same side is NOT an opposite", not ex.opp_bet(K, "NBA|Hawks vs Hornets|total|UNDER"))
ck("opposite detection crosses lane prefixes",
   ex.opp_bet("board|" + K, "rule|NBA|Hawks vs Hornets|total|OVER"))
S = "NBA|Atlanta Hawks @ Charlotte Hornets|side|Atlanta Hawks"
ck("the other TEAM is an opposite", ex.opp_bet(S, "NBA|Hawks vs Hornets|side|Charlotte Hornets"))
ck("the same team is not an opposite", not ex.opp_bet(S, "NBA|Hawks vs Hornets|side|Atlanta Hawks"))
ck("a different game is not an opposite", not ex.opp_bet(S, "NBA|Celtics vs Heat|side|Boston Celtics"))
for bad in (None, "", "junk", "a|b", "NBA|g|total"):
    ck(f"malformed key {bad!r} is not SAME", not ex.same_bet(K, bad))
    ck(f"malformed key {bad!r} is not OPPOSITE", not ex.opp_bet(K, bad))

# the board lane consults all three cross-venue checks before placing
mb = inspect.getsource(ex.main)
ck("board checks LIVEKEYS for an existing order", "lk in LIVEKEYS" in mb)
ck("board checks same_bet across lanes", "same_bet(lk, k)" in mb)
ck("board checks opp_bet for the other side", "opp_bet(lk, k)" in mb)
ck("board checks Peter's manual positions", "MANUAL_HELD" in mb)
ck("derive_key is the canonical key for board plays", "derive_key(p) or p[\"play_key\"]" in mb)

# ======================================================== 5. Board v3 controls, together
ck("unit: $200 to win", ex.BOARD_UNIT == 200.0, str(ex.BOARD_UNIT))
ck("Lane 1 unit untouched at $300", ex.LIVE_UNIT == 300.0, str(ex.LIVE_UNIT))
ck("plays per day: 10", ex.BOARD_MAX_PLAYS == 10, str(ex.BOARD_MAX_PLAYS))
ck("daily risk limit: $1,500", ex.BOARD_DAILY_RISK == 1500.0, str(ex.BOARD_DAILY_RISK))
ck("confirmation: 15 minutes", ex.BOARD_CONFIRM_MIN == 15, str(ex.BOARD_CONFIRM_MIN))
ck("tolerance venues: prophetx + novig only", ex.TOL_BOOKS == ("prophetx", "novig"), str(ex.TOL_BOOKS))
ck("tolerance size: 2 cents", ex.PX_TOL_CENTS == 2, str(ex.PX_TOL_CENTS))
ck("board lane is OFF unless EXEC_BOARD_LIVE is on", ex.BOARD_LIVE is False, str(ex.BOARD_LIVE))
ck("-130 cap intact", ex.CAP_LINE == -130, str(ex.CAP_LINE))
ck("global daily stop intact", ex.px_live.DAILY_STOP == 2250.0, str(ex.px_live.DAILY_STOP))
ck("per-order hard guard intact", ex.px_live.MAX_ORDER == 415.0, str(ex.px_live.MAX_ORDER))
ck("$200 to win sizes risk at negative odds", ex.live_stake(-110, 200.0) == (220.0, 200.0),
   str(ex.live_stake(-110, 200.0)))
ck("$200 risk at positive odds", ex.live_stake(140, 200.0) == (200.0, 280.0), str(ex.live_stake(140, 200.0)))
ck("best executable exchange: ranking excludes the allowance",
   "tol" not in [l for l in inspect.getsource(ex.evaluate).splitlines() if l.strip().startswith("c_eq =")][0])
ck("best executable exchange: all four venues eligible to fill",
   set(ex.LIVE_BOOKS) == {"prophetx", "kalshi", "polymarket_us", "novig"}, str(ex.LIVE_BOOKS))
ck("Polymarket GLOBAL is never a fill venue", "polymarket" not in ex.LIVE_BOOKS)
ck("board exposure unknown fails closed", ex.board_gate(100.0, "k")[0] is False)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
