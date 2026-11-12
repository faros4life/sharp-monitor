#!/usr/bin/env python3
"""
Kalshi + Polymarket US LIVE order placement for the executor (Oct 28, 2026; Peter: "same phase-1 plays, best price on
any book"). Real-money order code for these two books lives ONLY here; ProphetX stays in px_live.py.

Every order goes through place(), which refuses unless ALL of these hold (fail closed):
  1. px_live.preflight() passes: EXEC_LIVE "on", no ntfy STOP newer than GO, bot-order registry readable, today's
     ProphetX bot result above the daily stop
  2. today's ProphetX result MINUS every Kalshi/Polymarket US dollar the bot has risked today (counted as lost until a
     settled read exists: conservative, can stop early, never late) is above -DAILY_STOP
  3. dollars risked <= MAX_ORDER (same $ cap as ProphetX)
  4. fill-or-kill at a limit price: fills now at that price or better, or nothing happens; nothing rests
After the order: reads the fills back and reports what actually filled. A fill bigger than MAX_ORDER pauses live
(ntfy STOP) until Peter sends GO.
Keys (GitHub Secrets only): KALSHI_KEY_ID / KALSHI_PRIVATE_KEY (the Read/Trade "auto-place" key), PMUS_KEY_ID /
PMUS_SECRET_KEY. Public log: nothing financial is printed here.
"""
import base64
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import px_live

# Nov 12 (Peter): Novig submissions are HELD while duplicate prevention is being repaired. R1
# placed one NCAAF under three times (only one filled, and only because the liquidity was gone).
# Monitoring, fill reporting, position reads and cancellation are all unaffected by this switch.
NOVIG_SUBMIT = (os.environ.get("EXEC_NOVIG_SUBMIT") or "off").strip().lower() == "on"
NOVIG_PAUSE_WHY = ("Novig submissions are paused (EXEC_NOVIG_SUBMIT is not on) while duplicate "
                   "prevention is repaired - Nov 12. Monitoring and cancellation still run; "
                   "place by hand if you want this bet now.")

K_BASE = os.environ.get("KALSHI_API", "") or "https://api.elections.kalshi.com/trade-api/v2"
K_PREFIX = urllib.parse.urlparse(K_BASE).path.rstrip("/")
PM_API = "https://api.polymarket.us"
# Bound to px_live.OTHER so there is ONE at-risk number, not two. Every "EXPO[\"today\"] += ..."
# below therefore updates the same store px_live.preflight() reads - which is what makes the
# daily stop apply equally to a ProphetX order and to every other book. Do not rebind this to a
# fresh dict: that would silently restore the split accounting it exists to prevent.
EXPO = px_live.OTHER


def set_exposure(dollars):
    EXPO["today"] = float(dollars or 0)


# ---------------------------------------------------------------- signed calls
def _k_call(method, path, params=None, body=None):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding
    key = serialization.load_pem_private_key((os.environ.get("KALSHI_PRIVATE_KEY") or "").strip().encode(), password=None)
    ts = str(int(time.time() * 1000))
    msg = (ts + method + K_PREFIX + path).encode()
    sig = key.sign(msg) if isinstance(key, ed25519.Ed25519PrivateKey) else key.sign(
        msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    h = {"KALSHI-ACCESS-KEY": (os.environ.get("KALSHI_KEY_ID") or "").strip(), "KALSHI-ACCESS-TIMESTAMP": ts,
         "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(), "Accept": "application/json",
         "User-Agent": "sharp-monitor-live/1.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    url = K_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=20) as r:
        return r.status, json.loads(r.read().decode() or "{}")


def _pm_call(method, path, body=None, query=""):
    from cryptography.hazmat.primitives.asymmetric import ed25519
    key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode((os.environ.get("PMUS_SECRET_KEY") or "").strip())[:32])
    ts = str(int(time.time() * 1000))
    h = {"X-PM-Access-Key": (os.environ.get("PMUS_KEY_ID") or "").strip(), "X-PM-Timestamp": ts,
         "X-PM-Signature": base64.b64encode(key.sign(f"{ts}{method}{path}".encode())).decode(),
         "Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(PM_API + path + (("?" + query) if query else ""),
                                 data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        t = r.read().decode()
        return r.status, (json.loads(t) if t else {})


def _num(x):
    if isinstance(x, dict):
        x = x.get("value")
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- guards
def preflight(book, risk):
    """(ok, reason). Same fail-closed rules as ProphetX plus the non-ProphetX exposure in the daily stop."""
    if book == "kalshi" and not (os.environ.get("KALSHI_KEY_ID") and os.environ.get("KALSHI_PRIVATE_KEY")):
        return False, "no Kalshi trading key"
    if book == "novig" and not (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip():
        return False, "no token to reach the home runner"
    if book == "polymarket_us" and not (os.environ.get("PMUS_KEY_ID") and os.environ.get("PMUS_SECRET_KEY")):
        return False, "no Polymarket US trading key"
    ok, why = px_live.preflight()
    if not ok:
        return False, why
    res = px_live.LAST.get("res")
    if res is None:
        return False, "today's result unreadable (fail closed)"
    worst = res - EXPO["today"] - risk   # this order counted as lost too
    if worst <= -px_live.DAILY_STOP:
        return False, (f"daily stop: ProphetX {res:+,.2f}, other books risked ${EXPO['today']:,.2f} today, this order "
                       f"${risk:,.2f} -> worst case {worst:+,.2f} <= -{px_live.DAILY_STOP:,.0f}")
    if risk <= 0 or risk > px_live.MAX_ORDER + 1e-9:
        return False, f"stake {risk:.2f} outside 0-{px_live.MAX_ORDER:.0f}"
    return True, "ok"


def _too_big(filled, label, book):
    if filled > px_live.MAX_ORDER + 0.5:
        px_live.push("STOP", "STOP")
        px_live.push("Live PAUSED: fill too big", f"{label}\nFilled ${filled:,.2f} > ${px_live.MAX_ORDER:,.0f} max on {book}. "
                     "Live is paused. Check the book, then send GO to resume.", "rotating_light")
        return True
    return False


# ---------------------------------------------------------------- Kalshi
def kalshi_place(ticker, buy, limit_cost, count, label="", expire_ts=None):
    """Buy `count` contracts of `buy` ('yes'|'no') on `ticker`, paying at most `limit_cost` per contract (0-1, pre-fee).
    V2 route (the legacy route returns 410): buy YES = side 'bid' at the YES price; buy NO = side 'ask' at 1 - NO cost.
    expire_ts (Oct 28, Peter: rest a bid if not filled): good_till_canceled with expiration_time = a RESTING bid that
    fills what's there now and rests the rest until expire_ts (unix seconds); None = fill-or-kill."""
    risk = round(count * limit_cost, 2)
    ok, why = preflight("kalshi", risk)
    if not ok:
        return {"status": "refused", "reason": why}
    if buy not in ("yes", "no") or not ticker or count < 1 or not (0 < limit_cost < 1):
        return {"status": "refused", "reason": "bad Kalshi order inputs"}
    price = limit_cost if buy == "yes" else round(1 - limit_cost, 2)
    order = {"ticker": ticker, "side": "bid" if buy == "yes" else "ask", "count": str(int(count)), "price": f"{price:.2f}",
             "time_in_force": "fill_or_kill", "self_trade_prevention_type": "taker_at_cross",
             "client_order_id": str(uuid.uuid4())}
    if expire_ts:
        if int(expire_ts) <= int(time.time()) + 300:
            return {"status": "refused", "reason": "too close to the start to rest a bid"}
        order.update(time_in_force="good_till_canceled", expiration_time=int(expire_ts))
    try:
        st, resp = _k_call("POST", "/portfolio/events/orders", body=order)
    except urllib.error.HTTPError as ex:
        try:
            msg = ex.read().decode()[:300]
        except Exception:
            msg = str(ex)
        return {"status": "error", "reason": f"Kalshi order HTTP {ex.code}: {msg}", "order": order}
    except Exception as ex:   # the order MAY exist: never resubmit blindly
        return {"status": "error", "reason": f"Kalshi order unclear ({str(ex)[:80]}); check Kalshi before any retry", "order": order}
    o = resp.get("order") or resp
    oid = o.get("order_id")
    time.sleep(3)
    filled, cost_sum, n, read = 0.0, 0.0, 0.0, True
    try:
        _, r = _k_call("GET", "/portfolio/fills", {"order_id": oid}) if oid else (0, {})
        for _ in range(2):   # Oct 28: fills can lag the match - read twice more before calling it "no fill"
            if (r.get("fills") or []) or not oid or expire_ts:
                break
            time.sleep(5)
            _, r = _k_call("GET", "/portfolio/fills", {"order_id": oid})
        for f in (r.get("fills") or []):
            c = _num(f.get("count_fp")) or _num(f.get("count")) or 0
            yp = _num(f.get("yes_price_dollars"))
            if yp is None and f.get("yes_price") is not None:
                yp = _num(f.get("yes_price")) / 100
            np_ = _num(f.get("no_price_dollars"))
            if np_ is None and f.get("no_price") is not None:
                np_ = _num(f.get("no_price")) / 100
            pc = (yp if buy == "yes" else (np_ if np_ is not None else (1 - yp if yp is not None else None)))
            if pc is None:
                continue
            n += c
            cost_sum += c * pc
        filled = round(cost_sum, 2)
    except Exception:
        read = False
    px_live.add_bot_order(oid)
    EXPO["today"] += filled if read else risk
    avg_cost = round(cost_sum / n, 4) if n else None
    if expire_ts:   # a resting bid: everything asked counts as risked until it expires or settles
        EXPO["today"] += max(0.0, risk - (filled if read else risk))
    out = {"status": "placed", "book": "kalshi", "order_id": oid, "order": order, "filled_stake": filled,
           "resting": bool(expire_ts), "rest_contracts": max(0.0, count - n) if expire_ts else 0.0,
           "contracts": n, "avg_cost": avg_cost, "fills_read": read, "response": json.dumps(resp)[:400]}
    if _too_big(filled, label, "Kalshi"):
        out["paused"] = True
    return out


# ---------------------------------------------------------------- Polymarket US
def pmus_place(slug, long_side, limit_cost, qty, label="", expire_ts=None):
    """Buy `qty` contracts on market `slug`: long_side True = BUY_LONG at `limit_cost`; False = BUY_SHORT, whose order
    price is the LONG-side price (1 - short cost; proven by the Oct 27 short test). Fill-or-kill, synchronous.

    expire_ts (Nov 9, Peter: "build it for test") = a RESTING, MAKER-ONLY bid until that unix second, mirroring
    kalshi_place's expire_ts. None keeps the fill-or-kill behaviour this venue has always had, so every existing
    caller is unchanged.

    WHY THIS DID NOT EXIST. Peter asked twice before to rank Polymarket US ahead of Kalshi for resting bids. It was
    refused both times because this function hardcoded FILL_OR_KILL: putting the venue in REST_BOOKS would have sent
    a FOK order that crosses at the TAKER price or dies - about 5c worse than Kalshi's maker - while consuming a
    resting slot. The venue was never the problem; our integration was.

    PROVEN AGAINST THE VENUE, Nov 9. This docstring previously said Polymarket's docs were access-gated and the
    field names came from a third-party library. The first claim was my error - I checked
    apidocs.polymarketexchange.com and never tried docs.polymarket.us - and it made "Polymarket cannot rest" look
    settled when it had never been tested. The second was true, and the names were wrong: see the expire_ts block.
    A resting order is now sent with the one variant the venue accepted, and the enum it rejects is refused outright
    rather than silently falling back to a taker fill.

    STILL UNPROVEN: participateDontInitiate. It is sent because it is what makes us maker, but this venue accepted
    goodTillTime and then dropped it, so acceptance proves nothing and the flag may not survive the read-back
    either. Until pmus_rest_order_test's pdi_test shows it holding, maker pricing here is an assumption - and the
    maker rebate is the whole reason for ranking this venue above Kalshi. Do not reorder REST_BOOKS on it.

    participateDontInitiate is the point. It refuses to cross rather than paying the taker fee, which is what makes a
    resting bid actually earn the maker price instead of quietly becoming a taker. Kalshi and Novig have no
    equivalent.

    THE FEE IS NOT IN DOUBT - only whether we can REACH it. clv_std.FEE_NOTES carries Polymarket's own published
    schedule: TAKER 0.06 x C x p x (1-p), MAKER -0.0125, a REBATE - the venue pays us to post, and their worked
    example checks exactly. That makes this venue's maker the best of the three at every price (at a -110 screen:
    -108.6 here, -110.0 Novig, -111.9 Kalshi), while the fill-or-kill we have always sent gets its TAKER price of
    -116.8, the worst of the three. An 8.2c swing on the venue with the best posting economics.
    Fees are charged only on execution, so an order that rests and expires unfilled costs nothing."""
    risk = round(qty * limit_cost, 2)
    ok, why = preflight("polymarket_us", risk)
    if not ok:
        return {"status": "refused", "reason": why}
    if not slug or qty < 1 or not (0 < limit_cost < 1):
        return {"status": "refused", "reason": "bad Polymarket US order inputs"}
    price = limit_cost if long_side else round(1 - limit_cost, 3)
    order = {"marketSlug": slug, "intent": "ORDER_INTENT_BUY_LONG" if long_side else "ORDER_INTENT_BUY_SHORT",
             "type": "ORDER_TYPE_LIMIT", "price": {"value": f"{price:.3f}", "currency": "USD"}, "quantity": int(qty),
             "tif": "TIME_IN_FORCE_FILL_OR_KILL", "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC",
             "synchronousExecution": True, "maxBlockTime": "5"}
    if expire_ts:
        # Same floor as Kalshi: a bid resting into the last 5 minutes before the start is refused.
        if int(expire_ts) <= int(time.time()) + 300:
            return {"status": "refused", "reason": "too close to the start to rest a bid"}
        # FIELD NAMES PROVEN AGAINST THE VENUE, Nov 9 (run 42746257288). The three names that were
        # here before - GOOD_TILL_DATE, expiresAt, postOnly - are all wrong; none is in the enum
        # or the schema, and they came from a third-party client library rather than the API. The
        # probe sent five variants one field at a time and the venue accepted exactly this one:
        #   tif TIME_IN_FORCE_GOOD_TILL_TIME + goodTillTime as an ISO-8601 STRING, not an int.
        # Order DMGX8V5G13ZD rested unfilled on it: executions [], cumQuantity 0, leaves 1.
        #
        # THE EXPIRY IS NOT AN EXIT. The same read-back showed the venue SILENTLY rewriting what
        # it had just accepted: stored tif TIME_IN_FORCE_DAY, goodTillTime null. A 3-minute order
        # became a day order, and it does the same to FILL_OR_KILL (stored IMMEDIATE_OR_CANCEL),
        # so this is consistent normalisation. goodTillTime is therefore sent as a best effort and
        # NOTHING may depend on it: the caller must cancel explicitly at T-30 via pmus_cancel.
        # Both probe orders had to be killed by hand before that route was found.
        order.update(tif="TIME_IN_FORCE_GOOD_TILL_TIME",
                     goodTillTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(expire_ts))),
                     participateDontInitiate=True)
        # synchronousExecution waits for a fill; a resting bid has nothing to wait for.
        order.pop("synchronousExecution", None)
        order.pop("maxBlockTime", None)
    try:
        st, resp = _pm_call("POST", "/v1/orders", order)
    except urllib.error.HTTPError as ex:
        try:
            msg = ex.read().decode()[:300]
        except Exception:
            msg = str(ex)
        return {"status": "error", "reason": f"Polymarket US order HTTP {ex.code}: {msg}", "order": order}
    except Exception as ex:
        return {"status": "error", "reason": f"Polymarket US order unclear ({str(ex)[:80]}); check the app before any retry",
                "order": order}
    # resp.get("id") FIRST, so wherever this already works the value is byte-for-byte what it was.
    # The two fallbacks only run when that returns nothing. Nov 9: the resting probes could not
    # find the order id under "id" alone and had to try all three shapes, and an oid of None here
    # is not harmless - the read-back below GETs /v1/order/None, fails, sets fills_read False, and
    # reports contracts 0 for an order that may genuinely have filled. Exposure stays conservative
    # (it adds full risk, not the filled amount), but the fill would be mis-recorded. Strictly
    # additive: it can only find an id where there was none.
    oid = None
    if isinstance(resp, dict):
        oid = resp.get("id") or resp.get("orderId") or (resp.get("order") or {}).get("id")
    time.sleep(3)
    n, avg_cost, read = 0.0, None, True
    try:
        o = {}
        for path in (f"/v1/order/{oid}", f"/v1/orders/{oid}"):
            try:
                _, r = _pm_call("GET", path)
                o = (r.get("order") or {}) if isinstance(r, dict) else {}
                if o:
                    break
            except urllib.error.HTTPError:
                continue
        n = _num(o.get("cumQuantity")) or 0
        ap = _num(o.get("avgPx"))
        if n and ap is not None:
            avg_cost = round(ap if long_side else 1 - ap, 4)
        if not o:
            read = False
    except Exception:
        read = False
    filled = round(n * avg_cost, 2) if (n and avg_cost is not None) else 0.0
    px_live.add_bot_order(oid)
    EXPO["today"] += filled if read else risk
    out = {"status": "placed", "book": "polymarket_us", "order_id": oid, "order": order, "filled_stake": filled,
           "contracts": n, "avg_cost": avg_cost, "fills_read": read, "response": json.dumps(resp)[:400]}
    if _too_big(filled, label, "Polymarket US"):
        out["paused"] = True
    return out


def pmus_cancel(order_id, slug=None, label=""):
    """Cancel ONE resting Polymarket US order by id. Returns {"status": "cancelled"|"refused"|"error", ...}.

    THIS IS WHAT MAKES RESTING ON THIS VENUE LEGITIMATE AT ALL. pmus_place sends goodTillTime, the venue accepts it
    and then stores the order as TIME_IN_FORCE_DAY with goodTillTime null - so the expiry is not an exit and a bid
    left alone rests until end of day. Peter's rule is that a resting bid comes off at T-30 and whenever the signal
    dies, is pulled or flips. Without this function that rule cannot be honoured, which is why Polymarket stayed out
    of REST_BOOKS even after resting was proven to work.

    THE ROUTE IS THE DOCUMENTED ONE, and the namespace is SINGULAR: GET /v1/order/{id} returns 200 where
    GET /v1/orders/{id} 404s. Every plural shape and the whole gRPC-style colon family (/v1/orders/{id}:cancel and
    relatives) returned 404 across two probe runs; one 501 that looked like a near miss was the gateway's generic
    code-12 UNIMPLEMENTED stub, not a route. Discovery found this one answering a dead order id with a real
    handler's 400.

    marketSlug is the documented optional field, tried on the second attempt: the dead-id rejection carried the
    generic code-3 body, so if a live cancel fails identically that field is the first suspect. Third attempt is the
    batched route with a single id.

    NEVER /v1/orders/open/cancel. It is cancel-ALL. It answered 200 with canceledOrderIds [] during discovery only
    because nothing was open at that moment; fired while any other order rests - Peter's own included - it kills
    those too. Cancellation here is always by explicit order id, and this function has no cancel-all fallback by
    design. A cancel that cannot be targeted is reported as a failure, because the caller must then alert rather
    than quietly cancel something else.

    VERIFIED, NOT ASSUMED. The cancel call succeeding is not enough on this venue - it accepted goodTillTime and
    discarded it. So the order is read back and the status must actually say cancelled."""
    if not order_id:
        return {"status": "refused", "reason": "no order id to cancel"}
    # marketSlug IS REQUIRED, not optional - proven on a live order, run 42750863769:
    #   POST /v1/order/{id}/cancel              -> 400 {"code":3, "The server was unable..."}
    #   POST /v1/order/{id}/cancel + marketSlug -> 200, reads back ORDER_STATE_CANCELED
    # The bare route fails on a LIVE order with the same generic code-3 body it gave the dead one,
    # so the docs' "optional" is wrong in practice. Muse flagged code 3 as the suspect and it was.
    #
    # THE ORDER OF THESE TWO WAS A BUG I SHIPPED AN HOUR BEFORE THIS WAS PROVEN. The slug form was
    # second, and worse, it was skipped entirely when slug was None - so a caller that cancels by
    # id alone would have fallen through to the batched route with no working primary. The T-30
    # caller must therefore carry the slug alongside the order id, and this refuses up front if it
    # does not, rather than half-trying and reporting a confusing failure.
    if not slug:
        return {"status": "refused", "reason": f"cannot cancel {order_id} without its marketSlug "
                                               f"(the venue rejects the id-only route with code 3)"}
    tries = [("POST", f"/v1/order/{order_id}/cancel", {"marketSlug": slug}),
             ("POST", f"/v1/order/{order_id}/cancel", {}),
             ("POST", "/v1/orders/batched/cancel", {"orderIds": [order_id]})]
    last = None
    for method, path, body in tries:
        if body is None:
            continue
        try:
            st, resp = _pm_call(method, path, body)
        except urllib.error.HTTPError as ex:
            try:
                last = f"HTTP {ex.code}: {ex.read().decode()[:200]}"
            except Exception:
                last = f"HTTP {ex.code}"
            continue
        except Exception as ex:
            last = str(ex)[:120]
            continue
        if isinstance(st, int) and 200 <= st < 300:
            # Read it back: this venue has already been caught accepting a field and discarding it.
            state = ""
            time.sleep(2)
            try:
                for p in (f"/v1/order/{order_id}", f"/v1/orders/{order_id}"):
                    try:
                        _, r = _pm_call("GET", p)
                    except urllib.error.HTTPError:
                        continue
                    o = (r.get("order") or r or {}) if isinstance(r, dict) else {}
                    state = str(o.get("status") or o.get("state") or "").upper()
                    if state:
                        break
            except Exception:
                state = ""
            if "CANCEL" in state:
                # The id stays in px_live's bot-order registry. That registry exists to tell the bot's fills
                # apart from Peter's manual bets, and a cancelled order has no fill to match, so it simply
                # never matches - no new teardown API needed for it.
                return {"status": "cancelled", "order_id": order_id, "state": state, "via": path}
            # Succeeded but unverified: say so rather than reporting a cancel we cannot see.
            return {"status": "error", "order_id": order_id, "state": state or "unknown",
                    "reason": f"cancel call returned {st} but the order reads {state or 'unreadable'}; "
                              f"check the app for {order_id}", "via": path}
    return {"status": "error", "order_id": order_id,
            "reason": f"no targeted cancel route worked for {order_id} ({last}); check the app. "
                      f"Cancel-all was deliberately not attempted - it would hit every open order."}


def plan(levels, thr_american, stake, min_order=0.0, slip=0.0):
    """From a book's ladder [{price (pre-fee cost), american (after-fee), dollars}], keep the levels at or better than
    the after-fee threshold, cheapest first, until `stake` dollars are covered. Returns (limit_cost, contracts) where
    limit_cost is the worst pre-fee cost used (the order's limit) and contracts = floor(dollars / limit_cost);
    (None, 0) if nothing qualifies.

    Nov 11 (Peter, "BEST PRICE FIRST, NOT MAXIMUM DOLLARS FILLED"): the walk stops at the BEST
    AVAILABLE price. Levels worse than the best qualifying one by more than `slip` (probability) are
    not taken merely to reach `stake` - the stake shrinks to the best-priced depth instead, and the
    caller's live_remainder() takes what is left to the next VENUE at its own threshold. Before this
    the walk descended to worse levels to widen the fill and then priced EVERY contract at the worst
    level reached, so `thr_american` (built as alert_cost + tolerance) acted as a target rather than
    the ceiling it is meant to be. It remains the outer eligibility bound, unchanged.

    `min_order` is the one exception: a sub-minimum order is refused outright and the play is lost, so
    while the walk has not yet gathered `min_order` it may still extend past the slip bound."""
    lv = sorted((x for x in levels or [] if x.get("american") is not None and thr_american is not None
                 and x["american"] >= thr_american and x.get("price") and x.get("dollars")), key=lambda x: x["price"])
    got, limit = 0.0, None
    best = lv[0]["price"] if lv else None
    for x in lv:
        # price-first: a worse level is taken only while the fill is still short of min_order
        if best is not None and x["price"] > best + slip + 1e-9 and got >= min_order - 0.01:
            break
        got += x["dollars"]
        limit = x["price"]
        if got >= stake:
            break
    if limit is None:
        return None, 0
    return round(limit, 4), int(math.floor(min(stake, got) / limit + 1e-9))


def kalshi_cost_for(after_fee_prob, coef):
    """Pre-fee Kalshi cost c whose after-fee cost c + coef*c*(1-c) is <= after_fee_prob, rounded DOWN to the cent."""
    a, b = coef, -(1 + coef)
    disc = b * b - 4 * a * after_fee_prob
    if disc < 0:
        return None
    c = (-b - math.sqrt(disc)) / (2 * a)
    c = math.floor(c * 100 + 1e-9) / 100
    return c if 0.01 <= c <= 0.99 else None


# ---------------------------------------------------------------- Novig (orders run on Peter's home PC)
NV_REPO = "faros4life/novig-runner"
NV_WORKFLOW = "novig-live-order.yml"
NV_RESULTS = f"https://api.github.com/repos/{NV_REPO}/contents/snapshot/novig_orders.json?ref=main"


def _gh(method, url, body=None):
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sharp-monitor", **({"Content-Type": "application/json"} if body is not None else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        t = r.read().decode()
        return r.status, (json.loads(t) if t else {})


def novig_place(outcome_id, limit_cost, qty, label="", ttl_ms=None, key=""):
    """Novig blocks cloud servers, so the order is SENT to Peter's home PC (private repo novig-runner, workflow
    novig-live-order) which places it with the trading key and writes the result to snapshot/novig_orders.json.
    ttl_ms None = FOK; else GTT (fills what's there, rests the remainder until ttl_ms). Novig: 1 contract pays 1c, so
    dollars = qty x cost / 100. The full amount counts as risked today until a settled read exists."""
    # Nov 12 (Peter: "Hold new Novig submissions while the duplicate guard is unreliable"). This is
    # the ONE chokepoint for both Novig submission paths - the live order and the resting bid - so
    # the hold cannot be bypassed by a caller. Reads are untouched: novig_results() still reports
    # fills, the snapshot still answers positions, and cancellation still works. Default OFF: Peter
    # sets the repo VARIABLE EXEC_NOVIG_SUBMIT to "on" when he is satisfied the guard holds.
    if not NOVIG_SUBMIT:
        return {"status": "refused", "reason": NOVIG_PAUSE_WHY}
    risk = round(qty * limit_cost / 100, 2)
    ok, why = preflight("novig", risk)
    if not ok:
        return {"status": "refused", "reason": why}
    if not (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip():
        return {"status": "refused", "reason": "no token to reach the home runner (NOVIG_SNAPSHOT_TOKEN)"}
    if not outcome_id or qty < 1 or not (0.02 <= limit_cost <= 0.98):
        return {"status": "refused", "reason": "bad Novig order inputs"}
    if ttl_ms is not None and ttl_ms < 300000:
        return {"status": "refused", "reason": "too close to the start to rest a bid"}
    cid = str(uuid.uuid4())
    inputs = {"outcome_id": str(outcome_id), "price": f"{limit_cost:.3f}", "qty": str(int(qty)),
              "tif": "GTT" if ttl_ms else "FOK", "ttl_ms": str(int(min(ttl_ms or 0, 86400000))), "client_id": cid,
              "label": label[:120], "play_key": key[:120]}
    try:
        st, _ = _gh("POST", f"https://api.github.com/repos/{NV_REPO}/actions/workflows/{NV_WORKFLOW}/dispatches",
                    {"ref": "main", "inputs": inputs})
    except urllib.error.HTTPError as ex:
        return {"status": "error", "reason": f"couldn't reach the home runner (HTTP {ex.code}); nothing was sent to Novig"}
    except Exception as ex:
        return {"status": "error", "reason": f"home runner dispatch unclear ({str(ex)[:60]}); check Novig before any retry"}
    EXPO["today"] += risk
    # Nov 12 (Peter): BOTH ids. order_id here is the locally generated client id - Novig's own id
    # does not exist yet, because the order is dispatched to the home runner and placed there. It
    # is returned as client_id too, and venue_order_id is None until a runner result row supplies
    # it (executor.novig_reports records the mapping). Fills carry Novig's id, so without that
    # mapping the bot cannot reconcile its own orders against its own fills.
    return {"status": "placed", "book": "novig", "order_id": cid, "client_id": cid,
            "venue_order_id": None, "order": inputs, "filled_stake": None, "asked": risk,
            "contracts": 0, "avg_cost": None, "fills_read": False, "sent_to_runner": True, "resting": bool(ttl_ms)}


def novig_results():
    """The home runner's order results (list of dicts, newest last); None if unreadable."""
    try:
        req = urllib.request.Request(NV_RESULTS, headers={
            "Authorization": f"Bearer {(os.environ.get('NOVIG_SNAPSHOT_TOKEN') or '').strip()}",
            "Accept": "application/vnd.github.raw+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return (json.loads(r.read().decode()) or {}).get("orders") or []
    except urllib.error.HTTPError as ex:
        return [] if ex.code == 404 else None
    except Exception:
        return None
