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
import executor as ex
import pmus_fee as pf  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


# ======================================================== 1. maker / taker on resting orders
rb = inspect.getsource(ex.rest_bid)
ck("PM US maker pricing is OFF by default", ex.PMUS_REST_MAKER is False, str(ex.PMUS_REST_MAKER))
ck("the maker flag is env-gated, not code-default",
   'os.environ.get("EXEC_PMUS_REST_MAKER")' in inspect.getsource(ex))
# Nov 18: this pinned -0.0125 and called it "the published rebate". The venue's Nov 14 schedule grants
# NO maker rebate below $10MM of 30-day maker volume, so at our volume the maker side is FREE, not paid,
# and -0.0125 beat even its top tier (-0.0104). The rebate now comes from pmus_fee, which returns 0.0
# until eligibility is verified. The PROPERTY is what matters and it holds in both models: the maker
# side never costs MORE than the taker side, so pricing on it can only make us bid less aggressively.
ck("the maker coefficient comes from pmus_fee, not a literal",
   ex.PMUS_MAKER_REBATE == pf.maker(), f"{ex.PMUS_MAKER_REBATE} vs {pf.maker()}")
ck("the maker side never costs more than the taker side",
   ex.PMUS_MAKER_REBATE <= pf.taker(), f"{ex.PMUS_MAKER_REBATE} vs {pf.taker()}")
ck("an unverified rebate is never credited",
   pf.MODEL != "schedule" or ex.PMUS_MAKER_REBATE == 0.0, str(ex.PMUS_MAKER_REBATE))
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
ck("the taker coefficient is a cost (positive) and the maker side is never a cost",
   pf.taker() > 0 >= ex.PMUS_MAKER_REBATE, f"taker {pf.taker()} maker {ex.PMUS_MAKER_REBATE}")
cost_taker = bl.kalshi_cost_for(0.52, pf.taker())
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
# Nov 12: hr_priced and the retail deadband moved out of live_order into static_refusal(), which it
# calls - the entry-only gates had to run BEFORE live_play_alert() so a play that cannot be attempted
# is never announced as a LIVE PLAY. The property is unchanged: the journal latch is still the first
# gate in live_order, and nothing can mask it.
ck("the latch is the FIRST gate, so no other refusal can mask it",
   lo_src.index("journal_latch_why()") < lo_src.index("static_refusal("))
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
ck("daily risk limit: $2,000", ex.BOARD_DAILY_RISK == 2000.0, str(ex.BOARD_DAILY_RISK))
ck("confirmation: 15 minutes", ex.BOARD_CONFIRM_MIN == 15, str(ex.BOARD_CONFIRM_MIN))
ck("tolerance venues: prophetx + novig only", ex.TOL_BOOKS == ("prophetx", "novig"), str(ex.TOL_BOOKS))
ck("tolerance size: 2 cents", ex.PX_TOL_CENTS == 2, str(ex.PX_TOL_CENTS))
ck("board lane is OFF unless EXEC_BOARD_LIVE is on", ex.BOARD_LIVE is False, str(ex.BOARD_LIVE))
ck("-130 cap intact", ex.CAP_LINE == -130, str(ex.CAP_LINE))
ck("global daily stop intact", ex.px_live.DAILY_STOP == 3000.0, str(ex.px_live.DAILY_STOP))
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


# NOTE: assertions MUST go above the summary print below. Two blocks were appended after
# sys.exit on Nov 18 and never executed - the file still reported PASS 74 and the suite total
# did not move, so four real assertions looked green while never running at all.
# Nov 18 (Peter: "I don't see resting bid ... nothing on either"). rest_pre_alert announces a bid
# BEFORE dispatch; both submitted outcomes push; the all-refused path pushed nothing, so an
# announced bid that never went out ended in silence. rest_pre_alert's docstring calls the
# post-submission message mandatory, and this was the branch that did not honour it.
_rb = inspect.getsource(ex.rest_bid)
ck("an announced resting bid that no venue takes is REPORTED, not silent",
   "RESTING BID NOT PLACED" in _rb)
ck("the not-placed message states that nothing is at the venue",
   "no money is at the venue" in _rb)
ck("the not-placed message carries the per-venue refusal reasons",
   "why: {_why" in _rb or "why: " in _rb)
ck("all three resting outcomes now push: out, error, not placed",
   all(t in _rb for t in ("RESTING BID OUT on", "RESTING BID ERROR on", "RESTING BID NOT PLACED")))
ck("the not-placed alert cannot break the resting path (best effort, logged on failure)",
   "RESTING-NOT-PLACED ALERT FAILED" in _rb)
ck("the refusal reason is still returned to the caller unchanged",
   'return {"status": "refused", "reason": _why}' in _rb)

# Nov 18 (Peter: "There is a game on both"). The resting gate merged "no priced market" and "has the
# game at a different line" into one string, so the refusal message could not say which - and those
# two have opposite remedies. CLAUDE.md records the same mistake in board_clv_check.
_rb2 = inspect.getsource(ex.rest_bid)
# Checked against the APPENDED REASONS only, not the whole source: the first version of this
# assertion scanned comments too and failed on the comment that documents the old phrase.
_appends = [l for l in _rb2.splitlines() if "why_not.append" in l]
ck("no refusal reason still uses the merged phrase",
   not any("no exact-line market" in l for l in _appends), "; ".join(_appends)[:160])
ck("there are refusal reasons to check at all", len(_appends) >= 4, len(_appends))
ck("a line mismatch names BOTH lines, so the message says where the market is",
   "has the game at" in _rb2 and "not our" in _rb2)
ck("the two refusals are separate branches, not one condition",
   _rb2.count('if x.get("status") != "ok"') == 1 and _rb2.count('if not x.get("exact_line")') == 1)
ck("the gate still requires an ok status AND our exact line",
   'x.get("status") != "ok"' in _rb2 and 'not x.get("exact_line")' in _rb2)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
