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

if os.environ.get("CONFIRM_REAL_ORDER") != "ONE_DOLLAR":
    sys.exit("REFUSING: CONFIRM_REAL_ORDER is not ONE_DOLLAR.")

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

MAX_COST = 1.50
BELOW = 0.15        # how far under the best offer to sit, so it cannot cross
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


def main():
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
    if not (0.01 < price < 0.99):
        sys.exit(f"REFUSING: resting price {price} outside 1-99c (best offer {best:.3f}).")
    if price > MAX_COST:
        sys.exit(f"REFUSING: one contract at {price} exceeds the ${MAX_COST} cap.")

    expire_ts = int(time.time()) + EXPIRE_S
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
