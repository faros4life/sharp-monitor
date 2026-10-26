#!/usr/bin/env python3
"""
Polymarket US activity export, emailed (Oct 26, 2026). READ-ONLY: signed GETs only, no order code.

Pulls /v1/portfolio/activities (every page) for the last DAYS days (default 30) and emails:
  - counts and dollar totals by activity type,
  - one line per activity (time, type, market, side, price, quantity, amount, fee),
  - a CSV of the same rows, and the raw JSON of the first rows (so a new field name can't be missed).
Public repo: the Actions log prints counts only. Amounts go by email.
Secrets: PMUS_KEY_ID, PMUS_SECRET_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD (EMAIL_TO optional).
"""
import base64
import json
import os
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

API = "https://api.polymarket.us"
ET = ZoneInfo("America/New_York")
DAYS = int(os.environ.get("DAYS", "") or "30")
TOPKEYS = []


def signed_get(path, params=None):
    from cryptography.hazmat.primitives.asymmetric import ed25519
    key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["PMUS_SECRET_KEY"].strip())[:32])
    ts = str(int(time.time() * 1000))
    sig = base64.b64encode(key.sign(f"{ts}GET{path}".encode())).decode()
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"X-PM-Access-Key": os.environ["PMUS_KEY_ID"].strip(), "X-PM-Timestamp": ts,
                                               "X-PM-Signature": sig, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode() or "{}")


def items_of(d):
    if isinstance(d, list):
        return d
    for k in ("activities", "items", "data", "results", "activity"):
        if isinstance(d.get(k), list):
            return d[k]
    return []


def next_cursor(d):
    if not isinstance(d, dict):
        return None
    for k in ("nextCursor", "next_cursor", "cursor", "next", "nextPageToken", "pageToken"):
        v = d.get(k)
        if isinstance(v, str) and v:
            return k, v
    return None


def val(x):
    if isinstance(x, dict):
        for k in ("value", "amount", "decimal"):
            if k in x:
                return x[k]
    return x


def num(x):
    try:
        return float(val(x))
    except Exception:
        return None


def find(a, *names):
    """First matching field anywhere one level deep (field names vary by activity type)."""
    for n in names:
        if n in a and a[n] not in (None, ""):
            return a[n]
    for v in a.values():
        if isinstance(v, dict):
            for n in names:
                if n in v and v[n] not in (None, ""):
                    return v[n]
    return None


def when(a):
    t = find(a, "createTime", "createdAt", "created_at", "timestamp", "time", "updateTime", "transactTime", "executedAt")
    if t is None:
        return None
    try:
        if isinstance(t, (int, float)) or str(t).isdigit():
            t = float(t)
            return datetime.fromtimestamp(t / 1000 if t > 1e11 else t, timezone.utc)
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except Exception:
        return None


def row(a):
    pr = a.get("positionResolution")
    if isinstance(pr, dict):   # settlement: payout = cashValue before, profit = realized after minus fees (Oct 26 format)
        b, af = pr.get("beforePosition") or {}, pr.get("afterPosition") or {}
        md = b.get("marketMetadata") or {}
        fee, real = num(b.get("fees")), num(af.get("realized"))
        t = when(pr)
        return {"time_et": t.astimezone(ET).strftime("%Y-%m-%d %H:%M") if t else "", "type": "SETTLEMENT",
                "market": f"{md.get('title') or pr.get('marketSlug')} [{pr.get('marketSlug')}]", "outcome": str(md.get("outcome") or ""),
                "price": num(b.get("avgPx")), "qty": num(b.get("netPositionDecimal")), "amount": num(b.get("cashValue")),
                "fee": fee, "pnl": round(real - (fee or 0), 2) if real is not None else None, "cost": num(b.get("cost"))}
    t = when(a)
    md = a.get("marketMetadata") if isinstance(a.get("marketMetadata"), dict) else {}
    return {"time_et": t.astimezone(ET).strftime("%Y-%m-%d %H:%M") if t else "",
            "type": str(find(a, "type", "activityType", "kind") or ""),
            "market": str(md.get("title") or find(a, "marketTitle", "title", "marketSlug", "slug") or ""),
            "outcome": str(md.get("outcome") or find(a, "outcome", "side", "intent") or ""),
            "price": num(find(a, "price", "avgPx", "px", "executionPrice")),
            "qty": num(find(a, "quantity", "qty", "size", "filledQuantity", "cumQuantity")),
            "amount": num(find(a, "amount", "cost", "notional", "cashAmount", "value", "payout", "realizedPnl")),
            "fee": num(find(a, "fee", "fees", "commission")), "pnl": None, "cost": None}


def main():
    if not os.environ.get("PMUS_KEY_ID") or not os.environ.get("PMUS_SECRET_KEY"):
        sys.exit("Missing PMUS_KEY_ID / PMUS_SECRET_KEY.")
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    acts, params, pages = [], {"limit": 100}, 0
    for _ in range(50):
        try:
            d = signed_get("/v1/portfolio/activities", params)
        except urllib.error.HTTPError as e:
            sys.exit(f"activities read failed: HTTP {e.code}")
        pages += 1
        if pages == 1:
            TOPKEYS.extend(list(d.keys()) if isinstance(d, dict) else ["(list)"])
        got = items_of(d)
        acts += got
        nc = next_cursor(d)
        oldest = min((when(a) for a in got if when(a)), default=None)
        if not got or not nc or (oldest and oldest < since):
            break
        params = {"limit": 100, nc[0] if nc[0] != "next" else "cursor": nc[1]}
    rows = [row(a) for a in acts if (when(a) is None or when(a) >= since)]
    by = {}
    for r in rows:
        b = by.setdefault(r["type"] or "?", [0, 0.0, 0.0])
        b[0] += 1
        b[1] += r["amount"] or 0
        b[2] += r["fee"] or 0
    L = [f"POLYMARKET US ACTIVITY | last {DAYS} days (to {datetime.now(ET).strftime('%b %d %I:%M %p ET')})", "",
         f"Activities: {len(rows)} (pages read: {pages})", "", "BY TYPE (count | sum of amount | sum of fee)"]
    L += [f"  {k}: {v[0]} | {v[1]:,.2f} | {v[2]:,.2f}" for k, v in sorted(by.items())]
    st = [r for r in rows if r["type"] == "SETTLEMENT" and r["pnl"] is not None]
    L += ["", f"SETTLED: {len(st)} | payout {sum(r['amount'] or 0 for r in st):,.2f} | cost {sum(r['cost'] or 0 for r in st):,.2f} | "
              f"fees {sum(r['fee'] or 0 for r in st):,.2f} | P&L after fees {sum(r['pnl'] for r in st):,.2f}"]
    L += ["", "ACTIVITIES (newest first)"]
    L += [f"  {r['time_et']} | {r['type']} | {r['market'][:60]} | {r['outcome'][:30]} | px {r['price']} | qty {r['qty']} | "
          f"amt {r['amount']} | fee {r['fee']}" + (f" | P&L {r['pnl']:+.2f}" if r.get("pnl") is not None else "") for r in rows]
    L += ["", "CSV", "time_et,type,market,outcome,price,qty,amount,fee"]
    L += [",".join(json.dumps(r[k]) if isinstance(r[k], str) else ("" if r[k] is None else str(r[k]))
                   for k in ("time_et", "type", "market", "outcome", "price", "qty", "amount", "fee")) for r in rows]
    L += ["", f"Response keys (page 1): {TOPKEYS}", "RAW (first 2 activities, for field names)", json.dumps(acts[:2], indent=1)[:4000],
          "", "Source: Polymarket US API, signed GET /v1/portfolio/activities (read-only)."]
    user = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("EMAIL_TO", "").strip() or user
    msg = MIMEText("\n".join(L), "plain", "utf-8")
    msg["Subject"] = f"Polymarket US activity: last {DAYS} days | {len(rows)} activities"
    msg["From"], msg["To"] = user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"Email sent. Activities: {len(rows)}, pages: {pages}, types: {len(by)}.")   # counts only


if __name__ == "__main__":
    main()
