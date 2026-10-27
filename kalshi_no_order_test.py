#!/usr/bin/env python3
"""
Kalshi $1 REAL-MONEY **NO-side** order test (Oct 27, 2026): proves buying NO (an under) before NO buys can route live. Runs only when CONFIRM_REAL_ORDER=ONE_DOLLAR, against the real exchange,
with the TRADING key (GitHub Secrets KALSHI_TRADE_KEY_ID / KALSHI_TRADE_PRIVATE_KEY only).

1. Signed read of the balance: prints only whether it worked (never the amount; the repo is public).
2. Pick one open TOTAL market (NBA/NFL/college football/NHL) whose NO side (= the under) costs 35-65c, 2+ contracts
   offered, not already held.
3. ONE fill-or-kill order: buy 1 NO contract at the best NO offer (= 1 - best YES bid). Older order route first
   (action buy / side no / no_price); only if that route is gone (404/405), the V2 route as a YES ask. Cost about 50c + fee.
4. Reads back fills, order status and the position; prints only this order's price/size and the balance CHANGE.
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

if os.environ.get("CONFIRM_REAL_ORDER") != "ONE_DOLLAR":
    sys.exit("REFUSING: CONFIRM_REAL_ORDER is not ONE_DOLLAR.")
BASE = os.environ.get("KALSHI_API", "") or "https://api.elections.kalshi.com/trade-api/v2"
KEY_ID = (os.environ.get("KALSHI_TRADE_KEY_ID") or "").strip()
PEM = (os.environ.get("KALSHI_TRADE_PRIVATE_KEY") or "").strip()
if not KEY_ID or not PEM:
    sys.exit("Missing KALSHI_TRADE_KEY_ID or KALSHI_TRADE_PRIVATE_KEY secret.")
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
    h = {"Accept": "application/json", "User-Agent": "kalshi-live-test/1.0"}
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
    """Balance in cents, or None. Never printed (public log): only the change for the test order is shown."""
    st, d = call("GET", "/portfolio/balance")
    if st == 200 and isinstance(d, dict) and isinstance(d.get("balance"), (int, float)):
        return d["balance"]
    return None


def levels(book, side):
    ob = book.get("orderbook_fp") or book.get("orderbook") or {}
    raw = ob.get(f"{side}_dollars")
    if raw is not None:
        return [(float(p), float(q)) for p, q in raw]
    return [(float(p) / 100.0, float(q)) for p, q in (ob.get(side) or [])]


def held_tickers():
    st, d = call("GET", "/portfolio/positions", {"limit": 1000})
    if st != 200 or not isinstance(d, dict):
        return None
    return {p.get("ticker") for p in (d.get("market_positions") or []) if float(p.get("position_fp") or p.get("position") or 0) != 0}


def candidates():
    for series in ("KXNBATOTAL", "KXNFLTOTAL", "KXNCAAFTOTAL", "KXNHLTOTAL"):
        st, d = call("GET", "/markets", {"status": "open", "limit": 200, "series_ticker": series}, signed=False)
        if st != 200 or not isinstance(d, dict):
            print(f"   markets {series} -> {st}")
            continue
        for mk in d.get("markets") or []:
            yield mk


def main():
    print(f"0) Base: {BASE}")
    b0 = balance()
    print(f"1) Signed read with the trading key: {'OK' if b0 is not None else 'FAILED'}")
    if b0 is None:
        sys.exit("   STOP: signed read failed.")
    held = held_tickers()
    if held is None:
        sys.exit("   STOP: couldn't read positions (fail closed).")
    pick = None
    for mk in candidates():
        if mk["ticker"] in held:
            continue
        st, book = call("GET", f"/markets/{mk['ticker']}/orderbook", signed=False)
        if st != 200 or not isinstance(book, dict):
            continue
        yes_bids = levels(book, "yes")
        if not yes_bids:
            continue
        best_yes, qty = max(yes_bids, key=lambda x: x[0])
        no_cost = round(1 - best_yes, 4)          # buying NO takes the best YES bid
        if 0.35 <= no_cost <= 0.65 and qty >= 2:
            pick = (mk, no_cost, qty)
            break
    if not pick:
        sys.exit("No total market with a NO (under) offer between 35c and 65c right now. Try again later.")
    mk, no_cost, qty = pick
    exp_fee = 0.07 * no_cost * (1 - no_cost)
    print(f"2) Market: {mk['ticker']} | {mk.get('title')} | YES = {mk.get('yes_sub_title') or ''} -> buying NO (the under)")
    print(f"   Quoted NO cost {no_cost:.2f} ({qty:g} on the best YES bid); expected taker fee 0.07*P*(1-P) = {exp_fee:.4f}")
    order = {"ticker": mk["ticker"], "action": "buy", "side": "no", "type": "limit", "count": 1,
             "no_price": int(round(no_cost * 100)), "time_in_force": "fill_or_kill", "client_order_id": str(uuid.uuid4())}
    st, resp = call("POST", "/portfolio/orders", body=order)
    route = "older route (action buy, side no)"
    print(f"3) Order [{route}] {json.dumps(order)}\n   -> {st}: {json.dumps(resp)[:700] if isinstance(resp, dict) else resp}")
    if st in (404, 405):
        order = {"ticker": mk["ticker"], "side": "ask", "count": "1", "price": f"{1 - no_cost:.2f}",
                 "time_in_force": "fill_or_kill", "self_trade_prevention_type": "taker_at_cross", "client_order_id": str(uuid.uuid4())}
        st, resp = call("POST", "/portfolio/events/orders", body=order)
        route = "V2 route (YES ask)"
        print(f"   Order [{route}] {json.dumps(order)}\n   -> {st}: {json.dumps(resp)[:700] if isinstance(resp, dict) else resp}")
    if st not in (200, 201):
        sys.exit("   Order not accepted (nothing placed). Paste this log to Claude.")
    o = resp.get("order") or resp
    oid = o.get("order_id")
    time.sleep(3)
    print("4) Checks:")
    st, r = call("GET", "/portfolio/fills", {"order_id": oid})
    fills = (r.get("fills") or []) if isinstance(r, dict) else []
    print(f"   fills for this order -> {st}: {len(fills)} fill(s) " + json.dumps(
        [{k: f.get(k) for k in ("count_fp", "side", "action", "yes_price_dollars", "no_price_dollars", "is_taker")} for f in fills]))
    st, r = call("GET", f"/portfolio/orders/{oid}")
    od = (r.get("order") or {}) if isinstance(r, dict) else {}
    print(f"   order status -> {st}: status={od.get('status')} side={od.get('side')} tif={od.get('time_in_force')} "
          f"filled={od.get('fill_count', od.get('fill_count_fp'))} remaining={od.get('remaining_count', od.get('remaining_count_fp'))} "
          f"taker_fees={od.get('taker_fees', od.get('taker_fees_dollars'))}")
    st, r = call("GET", "/portfolio/positions", {"ticker": mk["ticker"]})
    pos = [p for p in ((r.get("market_positions") or []) if isinstance(r, dict) else []) if p.get("ticker") == mk["ticker"]]
    print(f"   position in that market: {[{k: p.get(k) for k in ('position', 'position_fp')} for p in pos]} (negative = NO)")
    b1 = balance()
    print(f"5) Balance change: {('-$%.4f' % ((b0 - b1) / 100)) if b1 is not None else 'unreadable'} "
          f"(expected about {no_cost + exp_fee:.4f} = NO cost + fee)")
    print(f"Done. ONE real NO order via the {route}, about $1, fill-or-kill: nothing left resting.")


if __name__ == "__main__":
    main()
