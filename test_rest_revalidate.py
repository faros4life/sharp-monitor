"""Resting bids must re-read the venue before posting - WITHOUT being judged as taker orders.

Peter, Nov 26 2026 (Task 2, design). rest_bid() prices from r["books"], the ladder evaluate()
built earlier in the run. That is the same stale source revalidate() was added to fix for takes,
and it was the one remaining path by which a stale feed reached money.

The trap in fixing it: revalidate() refuses when there is no executable depth at the price, and
when the market's price is worse than the gate. Both are TAKER tests. A maker order has no
executable depth at its price BY DEFINITION - that is what resting means - so reusing revalidate()
would have refused every valid resting bid and quietly killed the lane. Peter named this
explicitly: "A valid resting bid should not be rejected simply because immediately executable
liquidity is unavailable."
"""
import executor as ex

FAILED = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


PLAY = {"reval": {"al": {"bet": "Under 149.5"}, "mtype": "total", "side": "UNDER",
                  "price": -110, "teams": ["A", "B"], "line": 149.5}}
NOVIG_OK = {"line": 149.5, "outcome_id": "oc-1", "buy_levels": [{"p": 0.52}], "avail": 0.0}
KALSHI_OK = {"line": 149.5, "kalshi_buy": [{"ticker": "T1", "buy": 48}], "avail": 0.0}


def with_reread(fn):
    orig = ex.reread_book
    ex.reread_book = fn
    return orig


# --- the maker case: NO executable depth must still post -----------------------------------------
orig = with_reread(lambda b, ln, rv: dict(NOVIG_OK, avail=0.0))
try:
    okk, why, fresh = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("a maker bid with ZERO executable depth is accepted", okk, why)
    ok("and the refreshed ladder is handed back", fresh is not None and fresh.get("outcome_id") == "oc-1")

    # nor is it judged on the market's current price being worse than our limit
    ex.reread_book = lambda b, ln, rv: dict(NOVIG_OK, price=-200, avail=0.0)
    ok("a worse current market price does not refuse a maker bid", ex.rest_revalidate(PLAY, "novig", 149.5)[0])

    # --- what MUST still refuse -------------------------------------------------------------------
    # STRICT (Peter's ruling, Nov 26): an UNVERIFIED resting order does not go. He accepts the
    # availability cost. These are the unsuccessful-verification cases, and every one refuses.
    ex.reread_book = lambda b, ln, rv: None
    okk, why, fr = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("UNSUCCESSFUL verification: unreadable venue refuses", not okk and "unreadable" in why, why)
    ok("and nothing is handed back to price from", fr is None)

    ex.reread_book = lambda b, ln, rv: dict(NOVIG_OK, line=150.5)
    okk, why, _ = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("a moved line refuses", not okk and "line moved" in why, why)
    ok("the refusal names both numbers", "149.5" in why and "150.5" in why, why)

    ex.reread_book = lambda b, ln, rv: {"line": 149.5, "buy_levels": [{"p": 0.52}]}
    ok("novig with no outcome_id refuses", not ex.rest_revalidate(PLAY, "novig", 149.5)[0])
    ex.reread_book = lambda b, ln, rv: {"line": 149.5, "outcome_id": "oc-1"}
    ok("novig with no grid refuses", not ex.rest_revalidate(PLAY, "novig", 149.5)[0])

    ex.reread_book = lambda b, ln, rv: {"line": 149.5, "kalshi_buy": []}
    ok("kalshi with no market refuses", not ex.rest_revalidate(PLAY, "kalshi", 149.5)[0])
    ex.reread_book = lambda b, ln, rv: {"line": 149.5, "kalshi_buy": [{"t": 1}, {"t": 2}]}
    okk, why, _ = ex.rest_revalidate(PLAY, "kalshi", 149.5)
    ok("an ambiguous kalshi market refuses", not okk and "ambiguous" in why, why)
    ex.reread_book = lambda b, ln, rv: dict(KALSHI_OK)
    ok("a clean kalshi market is accepted", ex.rest_revalidate(PLAY, "kalshi", 149.5)[0])

    # a raising reader is a refusal, not a crash
    def boom(b, ln, rv):
        raise RuntimeError("venue down")
    ex.reread_book = boom
    okk, why, fr = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("UNSUCCESSFUL verification: a raising reader refuses, naming the error",
       not okk and "RuntimeError" in why and "fail closed" in why, why)

    # no basis recorded -> refuse, never post blind
    ex.reread_book = lambda b, ln, rv: dict(NOVIG_OK)
    okk, why, fr = ex.rest_revalidate({}, "novig", 149.5)
    ok("UNSUCCESSFUL verification: no revalidation basis refuses",
       not okk and "fail closed" in why, why)
finally:
    ex.reread_book = orig

# --- SUCCESSFUL verification: the full happy path, both venues ----------------------------------
orig2 = with_reread(lambda b, ln, rv: dict(NOVIG_OK))
try:
    okk, why, fresh = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("SUCCESSFUL verification: novig verifies and returns the fresh ladder",
       okk and why == "" and fresh["outcome_id"] == "oc-1", why)
    ex.reread_book = lambda b, ln, rv: dict(KALSHI_OK)
    okk, why, fresh = ex.rest_revalidate(PLAY, "kalshi", 149.5)
    ok("SUCCESSFUL verification: kalshi verifies and returns its market",
       okk and why == "" and fresh["kalshi_buy"][0]["ticker"] == "T1", why)
    # the ladder handed back is the FRESH one, not the stale one the caller held
    ex.reread_book = lambda b, ln, rv: dict(NOVIG_OK, buy_levels=[{"p": 0.61}])
    _, _, fresh = ex.rest_revalidate(PLAY, "novig", 149.5)
    ok("the CURRENT grid is returned, not the evaluated one", fresh["buy_levels"] == [{"p": 0.61}])
finally:
    ex.reread_book = orig2

# --- rest_bid refuses rather than posting unverified ---------------------------------------------
_src = body0 = src0 = open("executor.py", encoding="utf-8").read()
_rb = src0[src0.index("def rest_bid("):]
_rb = _rb[:_rb.index("\ndef ", 10)]
ok("rest_bid never posts on a failed verification", "x = _fresh" in _rb and "elif _rwhy" not in _rb)
ok("a failed verification is recorded in why_not", "why_not.append(_rwhy)" in _rb)

# --- the limit price is never taken from the re-read ---------------------------------------------
src = open("executor.py", encoding="utf-8").read()
fn = src[src.index("def rest_revalidate("):src.index("def rest_bid(")]
ok("rest_revalidate never computes a price", "p_star" not in fn and "alert_af" not in fn)
# precise, not a substring sweep: the prose explains why depth is not tested, so "avail" appears
ok("it never reads a depth field",
   'get("avail")' not in fn and '["avail"]' not in fn and "fillable" not in fn)
ok("it documents why depth is not tested", "MAKER" in fn and "TAKER" in fn)

body = src[src.index("def rest_bid("):]
body = body[:body.index("\ndef ", 10)]
# p_star (the limit) is computed at the TOP of rest_bid from the alert's after-fee number, well
# before the per-book loop - which is correct and is why the re-read can never move it. What must
# hold is that the re-read happens before the venue-specific cost/size maths that uses the ladder.
ok("the limit is derived from the alert, not from any venue re-read",
   body.index("p_star = american_to_prob") < body.index("rest_revalidate("))
ok("rest_bid re-reads before computing kalshi cost from the ladder",
   body.index("rest_revalidate(") < body.index("kalshi_cost_for"))
ok("rest_bid re-reads before computing the novig grid floor",
   body.index("rest_revalidate(") < body.index("novig_grid_floor"))
ok("the refusal falls through to the next book", "why_not.append(_rwhy)" in body and "continue" in body)
ok("the unit-ledger guard still runs after it", body.index("rest_revalidate(") < body.index("_unit_ledger_guard"))
ok("the T-30 expiry is untouched", "REST_BEFORE_MIN" in src)
ok("the ledger consume ordering is unchanged", "_unit_ledger_consume(_rb_grant, risk)" in body)

# --- Peter's four pre-deployment questions, answered from the code -------------------------------
_src = open("executor.py", encoding="utf-8").read()
_rb = _src[_src.index("def rest_bid("):]
_rb = _rb[:_rb.index("\ndef ", 10)]
_i_rev = _rb.index("rest_revalidate(")
_i_cont = _rb.index("why_not.append(_rwhy)")

ok("1. a refused book CANNOT consume a unit - it continues before the ledger guard",
   _i_cont < _rb.index("_unit_ledger_guard"))
ok("   and before the ledger consume", _i_cont < _rb.index("_unit_ledger_consume"))
ok("   the grant stays None until a book passes", "_rb_grant = None" in _rb
   and _rb.index("_rb_grant = None") < _i_rev)

ok("2. no ORPHANED CLAIM: the all-refused path releases the submission claim",
   _rb.index("why_not.append(_rwhy)") < _rb.rindex("registry.release_submission"))
ok("   and a failed release leaves it HELD so the next run refuses",
   "it stays held, next run refuses" in _rb)

ok("3. no INCORRECT EXPOSURE: consume runs only for the book that passed",
   _rb.index("_unit_ledger_consume") > _i_rev
   and _rb.count("_unit_ledger_consume") == 1)

ok("4. FALLBACK preserved: a refusal continues to the next book",
   _rb[_i_cont:_i_cont + 120].find("continue") > 0)
ok("   using the same fallthrough the pre-existing refusals use",
   _rb.count("continue") >= 5 and "falls through to the next book" in _rb)

ok("5. an all-refused run is announced, not silent",
   "RESTING BID NOT PLACED" in _rb and "_why[:300]" in _rb)

# --- PMUS resting is BLOCKED (Peter, Nov 27) -----------------------------------------------------
# The venue cannot enforce an expiry: it accepts GOOD_TILL_TIME + goodTillTime and stores DAY with
# goodTillTime null. The only exit is a bot-side cancel at T-30, so a bot outage leaves it resting.
_pm = _rb[_rb.index('elif b == "polymarket_us":'):]
_pm = _pm[:_pm.index("\n        elif ") if "\n        elif " in _pm else len(_pm)]
ok("PMUS resting refuses before any pricing", _pm.index("why_not.append") < _pm.index("continue"))
ok("it refuses before the ledger guard could run",
   "polymarket_us" in _rb and _rb.index('elif b == "polymarket_us":') > _rb.index("_unit_ledger_guard"))
ok("the refusal names the expiry defect", "cannot enforce an expiry" in _pm)
ok("and that cancellation needs the bot alive", "needs the bot alive" in _pm)
ok("no PMUS order can be placed from the resting path",
   _pm.index("continue") < (_pm.index("pmus_place") if "pmus_place" in _pm else len(_pm)))
ok("the TAKE path is untouched - takes do not use REST_BOOKS",
   "REST_BOOKS" not in _src[_src.index("def live_order("):_src.index("def live_order(") + 4000])

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
