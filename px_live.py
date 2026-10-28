#!/usr/bin/env python3
"""
ProphetX LIVE order placement for the executor (Oct 26, 2026). The ONLY file with real-money order code.

Every order goes through place(), which refuses unless ALL of these hold (fail closed):
  1. EXEC_LIVE == "on" (GitHub repo variable; the permanent off switch)
  2. no "STOP" on Peter's ntfy topic newer than the last "GO" (quick pause from the phone; ntfy keeps ~12 h)
  3. stake <= MAX_ORDER ($100 hard guard against a bad price/unit)
  4. today's ProphetX result for orders placed today is above -DAILY_STOP ($1,500); unreadable = refuse
  5. fillOrKill at a limit price: it fills now at that price or better, or nothing happens; nothing rests
Oct 27: the daily stop counts ONLY the bot's own orders (registry = order ids in the executor's
'Bets LIVE' email ledgers, set by the executor via set_bot_orders); Peter's manual ProphetX bets are ignored. Registry
unreadable = refuse (fail closed).
After the order: reads the fills back (get_trades for the order id) and reports what actually filled. If a fill comes
back bigger than MAX_ORDER, live is paused (ntfy STOP posted) until Peter sends GO.
Keys: PROPHETX_TRADE_ACCESS_KEY / PROPHETX_TRADE_SECRET_KEY (GitHub Secrets only). Public log: no amounts.
PX_QTY_MEANS: "stake" (default) or "to_win" - what submit_order's quantity means; the $1 live test confirms it.
"""
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BASE = os.environ.get("PX_BASE", "") or "https://cash.api.prophetx.co/partner"
ACCESS = (os.environ.get("PROPHETX_TRADE_ACCESS_KEY") or "").strip()
SECRET = (os.environ.get("PROPHETX_TRADE_SECRET_KEY") or "").strip()
LIVE = (os.environ.get("EXEC_LIVE") or "off").strip().lower() == "on"
MAX_ORDER = float(os.environ.get("EXEC_MAX_ORDER", "") or "100")
DAILY_STOP = float(os.environ.get("EXEC_DAILY_STOP", "") or "1500")
QTY_MEANS = (os.environ.get("PX_QTY_MEANS") or "stake").strip().lower()
TOPIC = os.environ.get("NTFY_TOPIC", "")
_T = {"token": None}
BOT = {"ids": None}
LAST = {"res": None}   # today's bot ProphetX result from the last passing preflight (book_live adds other books)   # order ids the bot placed (from the executor's Gmail ledger); None = unknown -> refuse


def set_bot_orders(ids):
    BOT["ids"] = None if ids is None else {str(i) for i in ids}


def add_bot_order(oid):
    if BOT["ids"] is not None and oid:
        BOT["ids"].add(str(oid))


def _mine(tr):
    ids = BOT["ids"] or set()
    return [t for t in tr if str(t.get("order_id")) in ids]


def _call(path, body=None):
    for i in range(4):
        req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                     method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **({"Authorization": f"Bearer {_T['token']}"} if _T["token"] else {})})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                out = json.loads(r.read().decode() or "{}")
            time.sleep(1.05)   # starter limit: 1 request / second / endpoint
            return out
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and i < 3:
                time.sleep(int(ex.headers.get("Retry-After") or 0) or 2 * (i + 1))
                continue
            raise


def login():
    if _T["token"]:
        return True
    if not (ACCESS and SECRET):
        return False
    d = _call("/auth/login", {"access_key": ACCESS, "secret_key": SECRET})
    _T["token"] = (d.get("data") or {}).get("access_token")
    return bool(_T["token"])


def trades():
    d = _call("/v4/mm/get_trades")
    return ((d.get("data") or {}).get("trades")) or []


def stop_state():
    """('STOP'|'GO'|None, when) - the newest STOP/GO message on Peter's ntfy topic (ntfy keeps ~12 h)."""
    if not TOPIC:
        return None, None
    try:
        with urllib.request.urlopen(f"https://ntfy.sh/{TOPIC}/json?poll=1&since=12h", timeout=15) as r:
            lines = r.read().decode().splitlines()
    except Exception:
        return "UNKNOWN", None
    last = (None, None)
    for ln in lines:
        try:
            m = json.loads(ln)
        except Exception:
            continue
        word = (m.get("message") or "").strip().upper()
        if word in ("STOP", "GO"):
            last = (word, m.get("time"))
    return last


def tg_mirror(text):
    """Oct 27 (Peter): every ntfy push is mirrored to Telegram (@sharp_fills_bot) so all alerts land in one place.
    Secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID; missing or failing = silently skipped. ntfy is unchanged and always
    fires first. Nothing is printed to the public log."""
    tok, chat = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip(), (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not tok or not chat:
        return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=json.dumps({"chat_id": chat, "text": text[:3500]}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        print("telegram mirror failed")


def push(title, body, tags="moneybag"):
    if not TOPIC:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": tags})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass
    if body.strip().upper() not in ("STOP", "GO"):   # the switch word itself stays on ntfy only
        tg_mirror(f"{title}\n{body}")


def today_result(tr):
    """Result of the BOT's ProphetX trades matched today (ET): settled profit/loss after the 2% fee; open = 0.
    None if the bot-order registry is unknown (fail closed)."""
    if BOT["ids"] is None:
        return None
    today = datetime.now(ET).date()
    tot = 0.0
    for t in _mine(tr):
        try:
            when = datetime.fromisoformat(str(t.get("matched_at")).replace("Z", "+00:00")).astimezone(ET).date()
        except Exception:
            continue
        if when != today:
            continue
        ws = str(t.get("winning_status") or "").lower()
        p = float(t.get("profit") or 0)
        if ws in ("profit", "win", "won"):
            tot += abs(p) * 0.98
        elif ws in ("loss", "lose", "lost"):
            tot -= stake_of(t)   # 'profit' is the potential win (the $1 test showed 0.81 on an open $1 at -123), so a loss = the stake
    return round(tot, 2)


def stake_of(t):
    q = float(t.get("quantity") or 0)
    if QTY_MEANS == "stake":
        return q
    pr = int(t.get("price") or 0)
    return q * abs(pr) / 100 if pr < 0 else (q * 100 / pr if pr else q)


def qty_for(stake, price):
    """submit_order quantity for a stake at this American price."""
    if QTY_MEANS == "stake":
        return round(stake, 2)
    return round(stake * 100 / abs(price), 2) if price < 0 else round(stake * price / 100, 2)


def preflight():
    """(ok, reason). Every check here must pass before any order (fail closed)."""
    if not LIVE:
        return False, "live is off (EXEC_LIVE is not 'on')"
    if not (ACCESS and SECRET):
        return False, "no ProphetX trading key"
    s, _ = stop_state()
    if s == "STOP":
        return False, "paused: STOP sent on ntfy (send GO to resume)"
    if s == "UNKNOWN":
        return False, "couldn't read the ntfy STOP switch"
    try:
        if not login():
            return False, "ProphetX trading login failed"
        res = today_result(trades())
    except Exception as ex:
        return False, f"couldn't read today's ProphetX result ({str(ex)[:60]})"
    if res is None:
        return False, "today's result unreadable (bot-order registry unknown)"
    if res <= -DAILY_STOP:
        return False, f"daily stop hit (today {res:+,.2f} <= -{DAILY_STOP:,.0f})"
    LAST["res"] = res
    return True, f"ok (today {res:+,.2f})"


def place(strike_id, limit_price, stake, label=""):
    """One fillOrKill order. Returns {"status": placed|refused|error, ...}. Never retries a placed order."""
    ok, why = preflight()
    if not ok:
        return {"status": "refused", "reason": why}
    if stake <= 0 or stake > MAX_ORDER + 1e-9:
        return {"status": "refused", "reason": f"stake {stake:.2f} outside 0-{MAX_ORDER:.0f}"}
    if not strike_id or not limit_price:
        return {"status": "refused", "reason": "missing strike or price"}
    ext = str(uuid.uuid4())
    order = {"external_id": ext, "strike_id": strike_id, "price": int(limit_price), "quantity": qty_for(stake, int(limit_price)),
             "order_strategy": "fillOrKill"}
    try:
        resp = _call("/v4/mm/submit_order", order)
    except urllib.error.HTTPError as ex:
        try:
            msg = ex.read().decode()[:300]
        except Exception:
            msg = str(ex)
        return {"status": "error", "reason": f"submit_order HTTP {ex.code}: {msg}", "order": order}
    except Exception as ex:   # timeout etc.: the order MAY exist - never resubmit blindly
        return {"status": "error", "reason": f"submit_order unclear ({str(ex)[:80]}); check My Trades before any retry",
                "order": order}
    o = ((resp.get("data") or {}).get("order") or {})
    oid = o.get("order_id") or o.get("id")
    time.sleep(3)
    filled, avg = 0.0, None
    try:
        mine = [t for t in trades() if str(t.get("order_id")) == str(oid)] if oid else []
        filled = round(sum(stake_of(t) for t in mine), 2)
        if mine:
            avg = round(sum(int(t.get("price") or 0) * stake_of(t) for t in mine) / max(filled, 1e-9))
    except Exception:
        mine = None
    add_bot_order(oid)
    out = {"status": "placed", "order_id": oid, "external_id": ext, "order": order, "filled_stake": filled,
           "avg_price": avg, "fills_read": mine is not None, "response": json.dumps(resp)[:400]}
    if filled > MAX_ORDER + 0.5:   # fill bigger than allowed: pause everything
        push("STOP", "STOP")
        push("Live PAUSED: fill too big", f"{label}\nFilled ${filled:,.2f} > ${MAX_ORDER:,.0f} max. Live is paused. Check My Trades, "
             "then send GO to resume.", "rotating_light")
        out["paused"] = True
    return out
