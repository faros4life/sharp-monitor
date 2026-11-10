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

import book_live as bl

MAX_COST = 1.50
BELOW = 0.15        # how far under the best offer to sit, so it cannot cross
EXPIRE_S = 180      # the ONLY guaranteed exit - there is no known cancel endpoint


def say(line):
    print(line, flush=True)


def best_offer(slug):
    """Best offer, read the way executor.py actually reads it.

    TWO DIFFERENT HOSTS, and getting this wrong is why the first version of this file was broken.
    Market and book reads go through the GATEWAY (executor.PMUS = gateway.polymarket.us) via
    liquidity_monitor.get; ORDERS go through book_live.PM_API = api.polymarket.us via _pm_call.
    My first draft read the book with _pm_call, i.e. asked the order host for market data."""
    import executor as _ex
    import liquidity_monitor as _lm
    md = (_lm.get(f"{_ex.PMUS}/v1/markets/{slug}/book") or {}).get("marketData") or {}
    for k in ("bestAsk", "best_ask", "ask", "bestOffer"):
        v = md.get(k)
        if isinstance(v, (int, float)) and 0 < float(v) < 1:
            return float(v)
        if isinstance(v, dict):
            for kk in ("value", "price"):
                try:
                    f = float(v.get(kk))
                    if 0 < f < 1:
                        return f
                except (TypeError, ValueError):
                    pass
    return None


def read_back(oid):
    """Order read-back on the paths book_live already uses."""
    for path in (f"/v1/order/{oid}", f"/v1/orders/{oid}"):
        try:
            _, r = bl._pm_call("GET", path)
            if r:
                return r
        except Exception:
            continue
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

    r = bl.pmus_place(slug, True, price, 1, label="rest-test", expire_ts=expire_ts)
    say(f"1) place -> {json.dumps(r)[:400]}")
    st = (r or {}).get("status")
    if st == "refused":
        say(f"\nREFUSED BEFORE SENDING: {(r or {}).get('reason')}")
        say("Nothing was placed - this is our own guard, not the venue.")
        return
    if st == "error":
        say(f"\nVENUE REJECTED IT: {(r or {}).get('reason')}")
        say("Q1 ANSWER: the tif/postOnly names are WRONG or unsupported on this API version.")
        say("Nothing rests. Do NOT add Polymarket US to REST_BOOKS.")
        return

    resp = (r or {}).get("resp") or r or {}
    oid = resp.get("orderId") or resp.get("id") or (r or {}).get("order_id")
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
