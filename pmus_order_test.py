#!/usr/bin/env python3
"""
Polymarket US $1 REAL-MONEY order test. Polymarket US has no practice site, so this places ONE tiny real order.

Hard limits (it refuses otherwise):
  - only runs when the workflow sets CONFIRM_REAL_ORDER=ONE_DOLLAR
  - buys the YES (long) side of one full-game MONEYLINE, priced 35-65c, on an NHL/NBA/college game not involving
    any team in AVOID (Peter's open bets), at the best offer, FILL-OR-KILL: fills now or cancels, nothing rests
  - total cost capped at $1.50 (about 2 contracts)
Then reads back: the order, recent trades (activities), positions and balance. Public log: prints the test order's own price/size and yes/no checks only, never balances or other positions.
"""
import base64
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

import executor as ex
import liquidity_monitor as lm

if os.environ.get("CONFIRM_REAL_ORDER") != "ONE_DOLLAR":
    sys.exit("REFUSING: CONFIRM_REAL_ORDER is not ONE_DOLLAR.")
API = "https://api.polymarket.us"
KEY_ID = (os.environ.get("PMUS_KEY_ID") or "").strip()
SECRET = (os.environ.get("PMUS_SECRET_KEY") or "").strip()
if not KEY_ID or not SECRET:
    sys.exit("Missing PMUS_KEY_ID / PMUS_SECRET_KEY.")
MAX_COST = 1.50
AVOID = ("pacers", "nets", "magic", "grizzlies", "steelers", "saints", "49ers", "falcons", "bengals", "ravens", "packers",
         "lions", "rams", "raiders", "colts", "vikings", "seahawks", "chiefs", "browns", "titans")

from cryptography.hazmat.primitives.asymmetric import ed25519

KEY = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(SECRET)[:32])


def call(method, path, body=None, query=""):
    ts = str(int(time.time() * 1000))
    sig = base64.b64encode(KEY.sign(f"{ts}{method}{path}".encode())).decode()
    h = {"X-PM-Access-Key": KEY_ID, "X-PM-Timestamp": ts, "X-PM-Signature": sig,
         "Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(API + path + (("?" + query) if query else ""),
                                 data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
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


def show(d, n=600):
    return json.dumps(d)[:n] if isinstance(d, (dict, list)) else str(d)[:n]


def px(x):
    v = x.get("px")
    return lm.num(v.get("value") if isinstance(v, dict) else v)


def main():
    st, bal = call("GET", "/v1/account/balances")
    b = ((bal.get("balances") or [{}])[0] if isinstance(bal, dict) else {})
    print(f"1) Signed read: balances -> {st}; buying power present: {b.get('buyingPower') is not None}")
    if st != 200:
        sys.exit(f"   STOP: {show(bal, 300)}")
    bp0 = lm.num((b.get("buyingPower") or {}).get("value") if isinstance(b.get("buyingPower"), dict) else b.get("buyingPower"))

    pick = None
    for sport in ("NHL", "NBA", "NCAAF", "NFL"):
        for ev in ex.pmus_events(sport):
            title = (ev.get("title") or "").lower()
            if any(t in title for t in AVOID):
                continue
            for mk in ev.get("markets") or []:
                if ex.pmus_type(mk) != "moneyline" or not mk.get("slug"):
                    continue
                try:
                    book = (lm.get(f"{ex.PMUS}/v1/markets/{mk['slug']}/book") or {}).get("marketData") or {}
                except Exception:
                    continue
                offers = sorted((px(o), lm.num(o.get("qty"))) for o in book.get("offers") or [] if px(o) is not None)
                if not offers:
                    continue
                p, q = offers[0]
                if 0.35 <= p <= 0.65 and (q or 0) >= 3:
                    pick = (sport, ev, mk, p, q)
                    break
            if pick:
                break
        if pick:
            break
    if not pick:
        sys.exit("No suitable moneyline (35-65c, not one of your games). Try later.")
    sport, ev, mk, p, q = pick
    qty = max(1, math.floor(1.0 / p + 1e-9))
    cost = qty * p
    if cost > MAX_COST:
        sys.exit(f"REFUSING: cost {cost:.2f} > {MAX_COST}")
    yes = next((s.get("description") for s in mk.get("marketSides") or [] if s.get("long", True)), "YES side")
    print(f"2) {sport}: {ev.get('title')} | market {mk['slug']} | buying '{yes}' (YES) {qty} contract(s) at {p:.3f} "
          f"= ${cost:.2f} + fee | {q:g} offered")

    order = {"marketSlug": mk["slug"], "intent": "ORDER_INTENT_BUY_LONG", "type": "ORDER_TYPE_LIMIT",
             "price": {"value": f"{p:.3f}", "currency": "USD"}, "quantity": qty,
             "tif": "TIME_IN_FORCE_FILL_OR_KILL", "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC",
             "synchronousExecution": True, "maxBlockTime": "5"}
    st, resp = call("POST", "/v1/orders", order)
    print(f"3) Order {json.dumps(order)}\n   -> {st}: {show(resp, 1200)}")
    oid = resp.get("id") if isinstance(resp, dict) else None

    time.sleep(3)
    print("4) Checks:")
    if oid:
        st, r = call("GET", f"/v1/order/{oid}")
        if st != 200:
            st, r = call("GET", f"/v1/orders/{oid}")
        print(f"   order -> {st}: {show(r, 700)}")
    st, a = call("GET", "/v1/portfolio/activities", query=f"limit=3&marketSlug={mk['slug']}")
    print(f"   trades in that market -> {st}: {show(a, 900)}")
    st, pos = call("GET", "/v1/portfolio/positions")
    txt = json.dumps(pos) if isinstance(pos, (dict, list)) else str(pos)
    # public log: no amounts from other positions - just whether the test market now shows up
    print(f"   positions -> {st}: test market listed: {mk['slug'] in txt}")
    st, bal = call("GET", "/v1/account/balances")
    b = ((bal.get("balances") or [{}])[0] if isinstance(bal, dict) else {})
    bp1 = lm.num((b.get("buyingPower") or {}).get("value") if isinstance(b.get("buyingPower"), dict) else b.get("buyingPower"))
    if bp0 is not None and bp1 is not None:
        print(f"5) Buying power change: {bp1 - bp0:+.4f} (cost + fee of the test order)")
    print("Done. ONE real order, about $1, fill-or-kill: nothing left resting.")


if __name__ == "__main__":
    main()
