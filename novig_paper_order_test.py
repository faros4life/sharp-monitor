#!/usr/bin/env python3
"""
Novig PAPER order test (play money only). Refuses to run unless the host is the paper exchange.

1. Signed read: balance of the paper subaccount (proves the trading key + signing work, and that funding applied).
2. Find one open NFL/NBA/college football/NHL market and its order book; pick a side that can be bought
   for 20-80c with enough on the other side's bid to fill (Novig books are bids per outcome: buying X takes
   the best bid on the other outcome at 1 - p).
3. ONE fill-or-kill order: 200 contracts (1 contract pays 1c -> about $1) at that price. Fills fully or not at all.
4. Fills, positions and balance read back.
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HOST = os.environ.get("NOVIG_HOST", "") or "https://api.paper.novig.com"
if "paper" not in HOST:
    sys.exit(f"REFUSING: host is {HOST} - this test only runs against the Novig paper exchange.")
KEY_ID = (os.environ.get("NOVIG_PAPER_TRADE_KEY_ID") or "").strip()
PEM = (os.environ.get("NOVIG_PAPER_TRADE_KEY_PEM") or "").strip()
if not KEY_ID or not PEM:
    sys.exit("Missing NOVIG_PAPER_TRADE_KEY_ID or NOVIG_PAPER_TRADE_KEY_PEM secret.")

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

KEY = serialization.load_pem_private_key(PEM.encode(), password=None)
UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
QTY = 200


def canonical_query(q):
    if not q:
        return ""
    enc = lambda s: "".join(c if c in UNRESERVED else "".join(f"%{b:02X}" for b in c.encode()) for c in s)
    pairs = []
    for part in q.split("&"):
        if part:
            k, _, v = part.partition("=")
            pairs.append((enc(urllib.parse.unquote_plus(k)), enc(urllib.parse.unquote_plus(v))))
    return "&".join(f"{k}={v}" for k, v in sorted(pairs))


def call(method, path, params=None, body=None, signed=True):
    q = urllib.parse.urlencode(params) if params else ""
    raw = json.dumps(body).encode() if body is not None else b""
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if signed:
        ts = str(int(time.time() * 1000))
        msg = "\n".join(["NOVIG-V3", ts, method, path, canonical_query(q), hashlib.sha256(raw).hexdigest()]).encode()
        sig = KEY.sign(msg) if isinstance(KEY, ed25519.Ed25519PrivateKey) else KEY.sign(msg, ec.ECDSA(hashes.SHA256()))
        h.update({"Novig-Key-Id": KEY_ID, "Novig-Timestamp": ts, "Novig-Signature": base64.b64encode(sig).decode()})
    req = urllib.request.Request(HOST + path + ("?" + q if q else ""), data=raw if body is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as ex:
        try:
            return ex.code, ex.read().decode()[:400]
        except Exception:
            return ex.code, str(ex)
    except Exception as ex:
        return "?", str(ex)[:300]


def show(d, n=700):
    return json.dumps(d)[:n] if isinstance(d, (dict, list)) else str(d)[:n]


def main():
    print(f"0) Paper host: {HOST}")
    st, bal = call("GET", "/v3/account/balance")
    print(f"1) Balance (signed read) -> {st}: {show(bal, 400)}")
    if st != 200:
        sys.exit("   STOP: signed read failed - check the two secrets.")

    pick = None
    for lg in ("NFL", "NBA", "NCAAF", "NHL"):
        st, cat = call("GET", "/v3/catalog/markets", {"league": lg, "limit": 100})
        if st != 200 or not isinstance(cat, dict):
            print(f"   catalog {lg} -> {st}: {show(cat, 200)}")
            continue
        for mk in cat.get("items") or []:
            oc = mk.get("outcomes") or []
            if mk.get("status") not in (None, "OPEN") or len(oc) != 2:
                continue
            st, book = call("GET", f"/v3/public/catalog/markets/{mk['marketId']}/book", {"depth": 20}, signed=False)
            if st != 200:
                st, book = call("GET", f"/v3/catalog/markets/{mk['marketId']}/book", {"depth": 20})
            if st != 200 or not isinstance(book, dict):
                continue
            orders = book.get("orders") or {}
            for i, o in enumerate(oc):
                other = oc[1 - i]
                bids = [(float(r["price"]), int(r["qty"])) for r in orders.get(other["outcomeId"], [])]
                if not bids:
                    continue
                bp, bq = max(bids)
                cost = round(1 - bp, 3)
                if 0.20 <= cost <= 0.80 and bq >= QTY:
                    pick = (lg, mk, o, cost, bq)
                    break
            if pick:
                break
        if pick:
            break
    if not pick:
        sys.exit("No paper market with a side at 20-80c and enough size. Try again later.")
    lg, mk, o, cost, bq = pick
    print(f"2) {lg} market {mk.get('marketId')} | {mk.get('description') or mk.get('marketType')} | buying '{o.get('name')}' "
          f"at {cost:.3f} ({bq} contracts on the other side's best bid)")

    cid = str(uuid.uuid4())
    order = {"outcomeId": o["outcomeId"], "price": f"{cost:.3f}", "qty": QTY, "tif": "FOK", "clientId": cid}
    st, resp = call("POST", "/v3/orders", body=order)
    print(f"3) Order {json.dumps(order)}\n   -> {st}: {show(resp)}")
    oid = resp.get("orderId") if isinstance(resp, dict) else None

    time.sleep(4)
    print("4) Checks:")
    st, f = call("GET", "/v3/portfolio/fills", {"limit": 5})
    print(f"   recent fills -> {st}: {show(f)}")
    if oid:
        st, r = call("GET", f"/v3/orders/{oid}")
        print(f"   order {oid} -> {st}: {show(r, 300)}  (404 = not resting, expected for FOK)")
    st, p = call("GET", "/v3/portfolio/positions")
    print(f"   positions -> {st}: {show(p)}")
    st, bal2 = call("GET", "/v3/account/balance")
    print(f"5) Balance after -> {st}: {show(bal2, 400)}")
    print("Done. Paper exchange only; no real money. Fill-or-kill: nothing left resting.")


if __name__ == "__main__":
    main()
