#!/usr/bin/env python3
"""
Kalshi DEMO order test (practice money only). Refuses to run unless the base URL is the demo exchange.

1. Signed read of the practice balance (proves the key + signing work).
2. Pick one open sports game market (NFL/NBA/college football/NHL/MLB, else any open market) whose YES side
   can be bought for 5-95c with at least 1 contract available.
3. Submit ONE fill-or-kill order: buy 1 YES contract at the best offer (takes what's there, never rests).
4. Print the response, then fills and position for that market, and the balance again.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("KALSHI_DEMO_API", "") or "https://external-api.demo.kalshi.co/trade-api/v2"
if "demo" not in BASE:
    sys.exit(f"REFUSING: base is {BASE} - this test only runs against the Kalshi demo exchange.")

KEY_ID = (os.environ.get("KALSHI_DEMO_KEY_ID") or "").strip()
PEM = (os.environ.get("KALSHI_DEMO_PRIVATE_KEY") or "").strip()
if not KEY_ID or not PEM:
    sys.exit("Missing KALSHI_DEMO_KEY_ID or KALSHI_DEMO_PRIVATE_KEY secret.")
PREFIX = urllib.parse.urlparse(BASE).path.rstrip("/")   # /trade-api/v2

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding

_KEY = serialization.load_pem_private_key(PEM.encode(), password=None)


def _sig(msg):
    if isinstance(_KEY, ed25519.Ed25519PrivateKey):
        return _KEY.sign(msg)
    return _KEY.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                     hashes.SHA256())


def call(method, path, params=None, body=None, signed=True):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    h = {"Accept": "application/json", "User-Agent": "kalshi-demo-test/1.0"}
    if signed:
        ts = str(int(time.time() * 1000))
        h.update({"KALSHI-ACCESS-KEY": KEY_ID, "KALSHI-ACCESS-TIMESTAMP": ts,
                  "KALSHI-ACCESS-SIGNATURE": base64.b64encode(_sig((ts + method + PREFIX + path).encode())).decode()})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as ex:
        try:
            return ex.code, ex.read().decode()[:400]
        except Exception:
            return ex.code, str(ex)
    except Exception as ex:
        return "?", str(ex)[:300]


def balance():
    st, d = call("GET", "/portfolio/balance")
    if st == 200 and isinstance(d, dict):
        b = d.get("balance")
        return f"${b / 100:,.2f}" if isinstance(b, (int, float)) else json.dumps(d)[:200]
    return f"{st} {d}"


def levels(book, side):
    ob = book.get("orderbook_fp") or book.get("orderbook") or {}
    raw = ob.get(f"{side}_dollars")
    if raw is not None:
        return [(float(p), float(q)) for p, q in raw]
    return [(float(p) / 100.0, float(q)) for p, q in (ob.get(side) or [])]


def candidates():
    for series in ("KXNFLGAME", "KXNBAGAME", "KXNCAAFGAME", "KXNHLGAME", "KXMLBGAME", None):
        p = {"status": "open", "limit": 100}
        if series:
            p["series_ticker"] = series
        st, d = call("GET", "/markets", p, signed=False)
        if st != 200 or not isinstance(d, dict):
            print(f"   markets {series or 'any'} -> {st}")
            continue
        for mk in d.get("markets") or []:
            yield mk


def main():
    print(f"0) Demo base: {BASE}")
    b0 = balance()
    print(f"1) Signed read OK? Practice balance: {b0}")
    if not b0.startswith("$"):
        sys.exit("   STOP: signed read failed - check the two secrets (key id + full private key text).")

    pick = None
    for mk in candidates():
        st, book = call("GET", f"/markets/{mk['ticker']}/orderbook", signed=False)
        if st != 200 or not isinstance(book, dict):
            continue
        no_bids = levels(book, "no")
        if not no_bids:
            continue
        best_no, qty = max(no_bids, key=lambda x: x[0])
        ask = round(1 - best_no, 4)          # buying YES takes the best NO bid
        if 0.05 <= ask <= 0.95 and qty >= 1:
            pick = (mk, ask, qty)
            break
    if not pick:
        sys.exit("No demo market with a YES offer between 5c and 95c. Try again later.")
    mk, ask, qty = pick
    print(f"2) Market: {mk['ticker']} | {mk.get('title')} | {mk.get('yes_sub_title') or ''}")
    print(f"   Best YES offer: {ask:.2f} ({qty:g} contracts there)")

    coid = str(uuid.uuid4())
    order = {"ticker": mk["ticker"], "side": "bid", "count": "1", "price": f"{ask:.2f}",
             "time_in_force": "fill_or_kill", "self_trade_prevention_type": "taker_at_cross", "client_order_id": coid}
    st, resp = call("POST", "/portfolio/events/orders", body=order)
    print(f"3) Order (new route) {json.dumps(order)}\n   -> {st}: {json.dumps(resp)[:800] if isinstance(resp, dict) else resp}")
    if st not in (200, 201):
        legacy = {"ticker": mk["ticker"], "action": "buy", "side": "yes", "type": "limit", "count": 1,
                  "yes_price": int(round(ask * 100)), "time_in_force": "fill_or_kill", "client_order_id": str(uuid.uuid4())}
        st, resp = call("POST", "/portfolio/orders", body=legacy)
        print(f"   Fallback (older route) {json.dumps(legacy)}\n   -> {st}: {json.dumps(resp)[:800] if isinstance(resp, dict) else resp}")
    oid = (resp.get("order_id") or (resp.get("order") or {}).get("order_id")) if isinstance(resp, dict) else None

    time.sleep(3)
    print("4) Checks:")
    if oid:
        st, r = call("GET", "/portfolio/fills", {"order_id": oid})
        print(f"   fills for order -> {st}: {json.dumps(r)[:700] if isinstance(r, dict) else r}")
        st, r = call("GET", f"/portfolio/orders/{oid}")
        print(f"   order status -> {st}: {json.dumps(r)[:700] if isinstance(r, dict) else r}")
    st, r = call("GET", "/portfolio/positions", {"ticker": mk["ticker"]})
    print(f"   position in that market -> {st}: {json.dumps(r)[:700] if isinstance(r, dict) else r}")
    print(f"5) Practice balance after: {balance()} (before {b0})")
    print("Done. Demo exchange only; no real money involved. Fill-or-kill: nothing left resting.")


if __name__ == "__main__":
    main()
