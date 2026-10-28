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

K_BASE = os.environ.get("KALSHI_API", "") or "https://api.elections.kalshi.com/trade-api/v2"
K_PREFIX = urllib.parse.urlparse(K_BASE).path.rstrip("/")
PM_API = "https://api.polymarket.us"
EXPO = {"today": 0.0}   # dollars risked today on Kalshi/PM US by the bot (registry + this run's fills)


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
def pmus_place(slug, long_side, limit_cost, qty, label=""):
    """Buy `qty` contracts on market `slug`: long_side True = BUY_LONG at `limit_cost`; False = BUY_SHORT, whose order
    price is the LONG-side price (1 - short cost; proven by the Oct 27 short test). Fill-or-kill, synchronous."""
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
    oid = resp.get("id") if isinstance(resp, dict) else None
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


def plan(levels, thr_american, stake):
    """From a book's ladder [{price (pre-fee cost), american (after-fee), dollars}], keep the levels at or better than
    the after-fee threshold, cheapest first, until `stake` dollars are covered. Returns (limit_cost, contracts) where
    limit_cost is the worst pre-fee cost used (the order's limit) and contracts = floor(dollars / limit_cost);
    (None, 0) if nothing qualifies."""
    lv = sorted((x for x in levels or [] if x.get("american") is not None and thr_american is not None
                 and x["american"] >= thr_american and x.get("price") and x.get("dollars")), key=lambda x: x["price"])
    got, limit = 0.0, None
    for x in lv:
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
    return {"status": "placed", "book": "novig", "order_id": cid, "order": inputs, "filled_stake": None, "asked": risk,
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
