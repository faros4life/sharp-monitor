#!/usr/bin/env python3
"""
Open positions on every book the executor can bet, for duplicate / conflict checks (Oct 25, 2026).

READ-ONLY: every call here is a GET (ProphetX: its login POST, then GETs). No orders, no transfers.
Each book returns a list of held sides, or None when it couldn't be read (the executor treats None as "unknown").
Public-log rule: nothing in here prints amounts; the report only says which books were checked.

A held side is normalized to: {book, game (title text), date (YYYY-MM-DD or None), mtype, label, flip}
  mtype: moneyline / spread / total;  label: text naming the team or Over/Under of the side bought
  flip: True when the position is the NO / short side of `label` (so the held side is the OTHER team / total side)
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import liquidity_monitor as lm

STATS = {}        # book -> counts / field names for the manual check (no amounts)
WHY = {}          # book -> reason it was unavailable (shown in the private email, never in the Actions log)
MONTHS = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


def _date(text):
    s = text or ""
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d\d)(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d\d)", s.upper())
    if m:
        return f"20{m.group(1)}-{MONTHS[m.group(2)]:02d}-{int(m.group(3)):02d}"
    return None


def _mtype_from_text(label, title=""):
    t = f"{label} {title}".lower()
    if re.search(r"\b(over|under)\b", t) and ("total" in t or re.search(r"\b(over|under)\s*\d", t)):
        return "total"
    if re.search(r"[+-]\d+(\.\d+)?", label or "") or "spread" in t or "wins by" in t:
        return "spread"
    return "moneyline"


# ---------------------------------------------------------------- Kalshi (signed GET)
K_API = os.environ.get("KALSHI_API", "") or "https://api.elections.kalshi.com/trade-api/v2"


def _kalshi_get(path, params=None):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding
    key = serialization.load_pem_private_key(os.environ["KALSHI_PRIVATE_KEY"].strip().encode(), password=None)
    ts = str(int(time.time() * 1000))
    msg = (ts + "GET" + urllib.parse.urlparse(K_API).path.rstrip("/") + path).encode()
    sig = key.sign(msg) if isinstance(key, ed25519.Ed25519PrivateKey) else key.sign(
        msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    req = urllib.request.Request(K_API + path + ("?" + urllib.parse.urlencode(params) if params else ""), headers={
        "KALSHI-ACCESS-KEY": os.environ["KALSHI_KEY_ID"].strip(), "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(), "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def kalshi_positions():
    if not os.environ.get("KALSHI_KEY_ID") or not os.environ.get("KALSHI_PRIVATE_KEY"):
        WHY["kalshi"] = "no key"
        return None
    try:
        out, cursor = [], None
        for _ in range(5):
            d = _kalshi_get("/portfolio/positions", {"limit": 200, "count_filter": "position", **({"cursor": cursor} if cursor else {})})
            for p in d.get("market_positions") or []:
                q = lm.num(p.get("position_fp")) if p.get("position_fp") is not None else lm.num(p.get("position"))
                if not q:
                    continue
                tk = p.get("ticker") or p.get("market_ticker") or ""
                et = tk.split("-")[0].upper()
                mtype = "moneyline" if et.endswith("GAME") else "spread" if "SPREAD" in et else "total" if "TOTAL" in et else None
                if not mtype:
                    continue
                mk = (lm.get(f"{K_API}/markets/{tk}") or {}).get("market") or {}
                out.append({"book": "kalshi", "game": mk.get("title") or "", "date": _date(tk), "mtype": mtype,
                            "label": mk.get("yes_sub_title") or mk.get("subtitle") or mk.get("title") or "", "flip": q < 0})
            cursor = d.get("cursor")
            if not cursor:
                break
        return out
    except Exception as ex:
        WHY["kalshi"] = str(ex)[:100]
        return None


# ---------------------------------------------------------------- Polymarket US (signed GET)
PM_API = "https://api.polymarket.us"


def pmus_positions():
    if not os.environ.get("PMUS_KEY_ID") or not os.environ.get("PMUS_SECRET_KEY"):
        WHY["polymarket_us"] = "no key"
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["PMUS_SECRET_KEY"].strip())[:32])
        path = "/v1/portfolio/positions"
        ts = str(int(time.time() * 1000))
        req = urllib.request.Request(PM_API + path, headers={
            "X-PM-Access-Key": os.environ["PMUS_KEY_ID"].strip(), "X-PM-Timestamp": ts,
            "X-PM-Signature": base64.b64encode(key.sign(f"{ts}GET{path}".encode())).decode(), "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        items = []

        def walk(x, slug=None):
            if isinstance(x, dict):
                if isinstance(x.get("marketMetadata"), dict):
                    items.append((x, slug))
                    return
                for k, v in x.items():
                    walk(v, k if isinstance(v, dict) else slug)
            elif isinstance(x, list):
                for v in x:
                    walk(v, slug)
        walk(d)
        out = []
        for p, slug in items:
            md = p["marketMetadata"]
            q = None
            for k in ("netPosition", "netPositionDecimal", "position", "qtyDecimal", "qty", "quantity"):
                v = p.get(k)
                v = v.get("value") if isinstance(v, dict) else v
                if lm.num(v) is not None:
                    q = lm.num(v)
                    break
            if not q:
                continue
            label = md.get("outcome") or ""
            title = md.get("title") or ""
            out.append({"book": "polymarket_us", "game": title, "date": _date(md.get("eventSlug") or md.get("slug") or slug),
                        "mtype": _mtype_from_text(label, title), "label": label, "flip": q < 0})
        return out
    except Exception as ex:
        WHY["polymarket_us"] = str(ex)[:100]
        return None


# ---------------------------------------------------------------- ProphetX (login + GET)
def px_positions():
    """ProphetX trades carry only strike_id (no event/selection name), so each open trade's strike_id is looked up in
    the selections of current games' markets (games from 8 h ago to 3 days ahead)."""
    import book_check as bc
    if not bc.PX_ACCESS or not bc.PX_SECRET:
        WHY["prophetx"] = "no key"
        return None
    try:
        if not bc.px_login():
            WHY["prophetx"] = "login failed"
            return None
        trades = ((bc.px_call("/v4/mm/get_trades").get("data") or {}).get("trades")) or []
        DONE = ("profit", "loss", "win", "won", "lose", "lost", "push", "void", "refund", "cancel")
        open_ = [t for t in trades if not any(w in str(t.get("winning_status") or "").lower() for w in DONE)
                 and not any(w in str(t.get("status") or "").lower() for w in ("settled", "cancel", "void"))]
        want = {str(t.get("strike_id")) for t in open_ if t.get("strike_id")}
        found, now = {}, datetime.now().astimezone()
        for lg in bc.PX_TOURNAMENTS:
            if not want - set(found):
                break
            for e in bc.px_events(lg):
                if not want - set(found):
                    break
                try:
                    st = datetime.fromisoformat((e.get("scheduled") or "").replace("Z", "+00:00"))
                except Exception:
                    continue
                if not (now - timedelta(hours=8) <= st <= now + timedelta(days=3)):
                    continue
                for mk in bc.px_markets(e["event_id"]):
                    ty = (mk.get("type") or "").lower()
                    mtype = "moneyline" if "money" in ty else "spread" if ("spread" in ty or "handicap" in ty) else \
                        "total" if "total" in ty else None
                    if not mtype:
                        continue
                    for lv, _ln in bc.px_lines(mk):
                        for x in (lv if isinstance(lv, list) else [lv]):
                            sid = str(x.get("strike_id"))
                            if sid in want and sid not in found:
                                found[sid] = {"book": "prophetx", "game": e.get("name") or "", "date": (e.get("scheduled") or "")[:10],
                                              "mtype": mtype, "label": x.get("name") or "", "flip": False}
        STATS["prophetx"] = {"trades": len(trades), "open_fills": len(open_), "open_strikes": len(want),
                             "matched_strikes": len(found)}
        if want - set(found):
            WHY["prophetx_partial"] = f"{len(want - set(found))} of {len(want)} open bets not matched to a game"
        return list(found.values())
    except Exception as ex:
        WHY["prophetx"] = str(ex)[:100]
        return None


# ---------------------------------------------------------------- matching
def all_positions():
    """{book: [held sides] or None}"""
    return {"kalshi": kalshi_positions(), "prophetx": px_positions(), "polymarket_us": pmus_positions()}


def _same_game(h, teams, sport, start_utc):
    g = h.get("game") or ""
    if not g or not all(lm.toks(g, sport) & lm.toks(t, sport) for t in teams):
        return False
    if h.get("date") and start_utc:
        try:
            d = datetime.fromisoformat(start_utc.replace("Z", "+00:00")).astimezone(lm.ET).date()
            hd = datetime.fromisoformat(h["date"]).date()
            if abs((hd - d).days) > 1:
                return False
        except Exception:
            pass
    return True


def conflict(al, mtype, side, teams, held_by_book):
    """('duplicate'|'conflict', book) from open positions on Kalshi/ProphetX/Polymarket US, else None.
    Spread and moneyline on the same team count as the same play; opposite team = conflict. Totals only vs totals."""
    for book, held in held_by_book.items():
        for h in held or []:
            if not _same_game(h, teams, al["sport"], al.get("start_utc")):
                continue
            hm = h["mtype"]
            if mtype == "total" and hm == "total":
                lab = h["label"].lower()
                s = "OVER" if "over" in lab else "UNDER" if "under" in lab else None
                if s is None:
                    continue
                if h["flip"]:
                    s = "UNDER" if s == "OVER" else "OVER"
                return ("duplicate" if s == side else "conflict"), book
            if mtype in ("moneyline", "spread") and hm in ("moneyline", "spread"):
                t = lm.team_side(h["label"], list(teams), al["sport"])
                if t is None:
                    continue
                if h["flip"]:
                    t = 1 - t
                return ("duplicate" if t == side else "conflict"), book
    return None


def status_line(held_by_book):
    names = {"kalshi": "Kalshi", "prophetx": "ProphetX", "polymarket_us": "Polymarket US"}
    return ", ".join(f"{names[b]} " + (("checked" + (f" ({WHY[b + '_partial']})" if WHY.get(b + "_partial") else ""))
                                        if v is not None else f"unavailable ({WHY.get(b, '?')})")
                     for b, v in held_by_book.items())
