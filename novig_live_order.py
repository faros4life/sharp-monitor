#!/usr/bin/env python3
"""
Novig LIVE order on Peter's home PC (Oct 28, 2026). Novig blocks cloud servers, so the cloud executor (public repo
sharp-monitor, which already checked EXEC_LIVE, the ntfy STOP switch, the $100 cap and the daily stop) sends each
phase-1 Novig order here through workflow_dispatch. This script:
  place  : re-checks the inputs, places ONE order with the trading key, reads it back, records the result
  refresh: (every 5 min) re-reads the bot's still-open Novig orders and records any fill/close changes
Results go to snapshot/novig_orders.json in THIS private repo; the executor reads that file and texts Peter.
Hard limits here too (fail closed): price 2c-98c, cost <= $100, tif FOK or GTT, GTT ttl <= 24 h.
Log: counts and statuses only; never balances.
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
from datetime import datetime, timezone

HOST = "https://api.novig.com"
PATH = "snapshot/novig_orders.json"
MAX_COST = 100.0
KEY_ID = (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()
PEM = (os.environ.get("NOVIG_TRADE_KEY_PEM") or "").strip()
UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


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


def call(method, path, params=None, body=None):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519
    key = serialization.load_pem_private_key(PEM.replace("\\n", "\n").encode(), password=None)
    q = urllib.parse.urlencode(params) if params else ""
    raw = json.dumps(body).encode() if body is not None else b""
    ts = str(int(time.time() * 1000))
    msg = "\n".join(["NOVIG-V3", ts, method, path, canonical_query(q), hashlib.sha256(raw).hexdigest()]).encode()
    sig = key.sign(msg) if isinstance(key, ed25519.Ed25519PrivateKey) else key.sign(msg, ec.ECDSA(hashes.SHA256()))
    h = {"Content-Type": "application/json", "Accept": "application/json", "Novig-Key-Id": KEY_ID, "Novig-Timestamp": ts,
         "Novig-Signature": base64.b64encode(sig).decode()}
    req = urllib.request.Request(HOST + path + ("?" + q if q else ""), data=raw if body is not None else None, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as ex:
        try:
            return ex.code, ex.read().decode()[:300]
        except Exception:
            return ex.code, str(ex)
    except Exception as ex:
        return "?", str(ex)[:200]


def gh(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "novig-live-order"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode() or "{}")


def load():
    api = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/contents/{PATH}"
    try:
        d = gh("GET", api + "?ref=main")
        return json.loads(base64.b64decode(d["content"]).decode()), d.get("sha"), api
    except Exception:
        return {"orders": []}, None, api


def save(doc, sha, api, note):
    doc["orders"] = doc.get("orders", [])[-200:]
    body = {"message": note, "branch": "main", "content": base64.b64encode(json.dumps(doc, indent=1).encode()).decode()}
    if sha:
        body["sha"] = sha
    for i in range(3):
        try:
            gh("PUT", api, body)
            return
        except urllib.error.HTTPError as ex:   # file changed under us: reload sha and retry
            if ex.code != 409 or i == 2:
                raise
            _, body["sha"], _ = load()


def order_state(oid):
    """(status, filled_qty) for one order, or (None, None)."""
    st, d = call("GET", f"/v3/orders/{oid}")
    if st != 200 or not isinstance(d, dict):
        return None, None
    o = d.get("order") or d
    filled = o.get("filledQty", o.get("filled_qty", o.get("executedQty")))
    if filled is None and o.get("qty") is not None and o.get("remainingQty") is not None:
        filled = int(o["qty"]) - int(o["remainingQty"])
    return (o.get("status") or o.get("state")), (int(float(filled)) if filled is not None else None)


def place():
    e = os.environ
    oc, price, qty, tif = e.get("IN_OUTCOME", ""), e.get("IN_PRICE", ""), e.get("IN_QTY", ""), e.get("IN_TIF", "")
    rec = {"client_id": e.get("IN_CLIENT", ""), "play_key": e.get("IN_KEY", ""), "label": e.get("IN_LABEL", ""),
           "outcome_id": oc, "price": price, "qty": qty, "tif": tif, "ttl_ms": e.get("IN_TTL", "0"),
           "placed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": "refused",
           "filled_qty": 0, "order_id": None, "error": None}
    try:
        c, q, ttl = float(price), int(qty), int(e.get("IN_TTL") or 0)
    except ValueError:
        c, q, ttl = 0, 0, 0
    if not KEY_ID or not PEM:
        rec["error"] = "missing Novig trading key on the runner"
    elif not (0.02 <= c <= 0.98) or q < 1 or q * c / 100 > MAX_COST + 1e-9 or tif not in ("FOK", "GTT") \
            or (tif == "GTT" and not (300000 <= ttl <= 86400000)) or not oc:
        rec["error"] = f"inputs outside the hard limits (price {price}, qty {qty}, tif {tif}, ttl {ttl})"
    else:
        order = {"outcomeId": oc, "price": f"{c:.3f}", "qty": q, "tif": tif, "clientId": rec["client_id"]}
        if tif == "GTT":
            order["ttl"] = ttl
        st, resp = call("POST", "/v3/orders", body=order)
        if st not in (200, 201):
            rec.update(status="rejected", error=f"HTTP {st}: {str(resp)[:200]}")
        else:
            rec["order_id"] = resp.get("orderId") if isinstance(resp, dict) else None
            time.sleep(4)
            s2, f2 = order_state(rec["order_id"]) if rec["order_id"] else (None, None)
            rec["status"] = str(s2 or ("sent" if tif == "GTT" else "unknown")).lower()
            rec["filled_qty"] = f2 if f2 is not None else 0
    doc, sha, api = load()
    doc.setdefault("orders", []).append(rec)
    save(doc, sha, api, f"Novig order {rec['status']}")
    print(f"Novig order: status {rec['status']}; tif {tif}; filled {'yes' if rec['filled_qty'] else 'no'}")
    if rec["status"] in ("refused", "rejected"):
        print(f"   reason: {rec['error']}")


def refresh():
    """Re-read still-open GTT orders (and unknown ones) and record changes."""
    if not KEY_ID or not PEM:
        sys.exit("missing Novig trading key")
    doc, sha, api = load()
    changed = 0
    for rec in doc.get("orders", [])[-50:]:
        if not rec.get("order_id") or rec.get("status") in ("filled", "cancelled", "canceled", "expired", "rejected", "refused", "closed"):
            continue
        s2, f2 = order_state(rec["order_id"])
        if s2 is None:
            continue
        s2 = str(s2).lower()
        if s2 != rec.get("status") or (f2 is not None and f2 != rec.get("filled_qty")):
            rec["status"], rec["filled_qty"] = s2, (f2 if f2 is not None else rec.get("filled_qty"))
            rec["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            changed += 1
    if changed:
        save(doc, sha, api, f"Novig order status ({changed} changed)")
    print(f"Novig order refresh: {changed} changed")


if __name__ == "__main__":
    refresh() if (sys.argv[1:] == ["refresh"]) else place()
