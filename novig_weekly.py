#!/usr/bin/env python3
"""
Monday Novig reconciliation, emailed (never written to the repo, never printed in logs).

Week = last Monday 00:00 ET .. Sunday 24:00 ET (or WEEK_OFFSET weeks earlier).
Contents: balance now and at week start/end (rebuilt from the ledger), the week's ledger by kind,
filled orders and fills (with fees), settled bets (result, cost, payout, pnl), open positions.
Read-only: uses novig_signed (GET-only, fails closed unless the key is read-only).
Secrets: NOVIG_READ_KEY_ID, NOVIG_READ_KEY_PEM, GMAIL_ADDRESS, GMAIL_APP_PASSWORD (EMAIL_TO optional).
"""
import os
import smtplib
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import novig_signed as nv

ET = ZoneInfo("America/New_York")


def ms(dt):
    return int(dt.timestamp() * 1000)


def money(x):
    return f"${x:,.2f}" if x >= 0 else f"-${-x:,.2f}"


def paged(path, params, stop=None, max_pages=40):
    """All items of a {items, next} page set (per-wallet nested pages flattened). stop(item) -> True ends early."""
    out, after = [], None
    for _ in range(max_pages):
        p = dict(params, **({"after": after} if after else {}))
        d = nv.get(path, p)
        if isinstance(d, dict) and "items" in d:
            items, after = d["items"], d.get("next")
        elif isinstance(d, dict):   # management key: {walletKeyId: {items, next}}
            items, after = [], None
            for v in d.values():
                if isinstance(v, dict):
                    items += v.get("items") or []
                    after = after or v.get("next")
                elif isinstance(v, list):
                    items += v
        else:
            items, after = (d or []), None
        out += items
        if not after or (stop and items and stop(items[-1])):
            break
        time.sleep(0.15)
    return out


_MK, _EV = {}, {}


def market(mid):
    if mid not in _MK:
        try:
            _MK[mid] = nv.get(f"/v3/history/markets/{mid}")
        except Exception:
            _MK[mid] = {}
    return _MK[mid]


def event(eid):
    if eid and eid not in _EV:
        try:
            _EV[eid] = nv.get(f"/v3/history/events/{eid}")
        except Exception:
            _EV[eid] = {}
    return _EV.get(eid) or {}


def label(mid, oid):
    m = market(mid)
    e = event(m.get("eventId"))
    side = next((o.get("name") for o in m.get("outcomes") or [] if o.get("outcomeId") == oid), "?")
    return f"{e.get('league') or ''} {e.get('description') or m.get('description') or mid[:8]} | {side}".strip()


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def build(now):
    off = int(os.environ.get("WEEK_OFFSET", "") or "0")
    today = now.astimezone(ET).date()
    this_monday = today - timedelta(days=today.weekday())
    ws = datetime.combine(this_monday - timedelta(days=7 * (off + 1)), datetime.min.time(), ET)
    we = ws + timedelta(days=7)
    me = nv._S["id"]

    bal_now = f(nv.get("/v3/account/balance").get("balance"))
    tx = paged("/v3/account/transactions", {"startsAfter": ms(ws) - 1, "limit": 5000})
    after_ws = sum(f(t["amount"]) for t in tx if t["ts"] >= ms(ws))
    after_we = sum(f(t["amount"]) for t in tx if t["ts"] >= ms(we))
    bal_start, bal_end = bal_now - after_ws, bal_now - after_we
    week_tx = [t for t in tx if ms(ws) <= t["ts"] < ms(we)]
    kinds = {}
    for t in week_tx:
        kinds[t["kind"]] = kinds.get(t["kind"], 0.0) + f(t["amount"])

    fills = paged("/v3/portfolio/fills", {"keyId": me, "startsAfter": ms(ws) - 1, "startsBefore": ms(we), "limit": 5000})
    fill_cost = sum(f(x.get("cost")) for x in fills)
    fill_fee = sum(f(x.get("fee")) for x in fills)
    orders = [o for o in paged("/v3/orders", {"keyId": me, "status": "FILLED", "limit": 5000})
              if ms(ws) <= o.get("createdTs", 0) < ms(we)]

    settled = [p for p in paged("/v3/history/positions", {"keyId": me, "status": "SETTLED", "limit": 5000})
               if p.get("settledTs") and ms(ws) <= int(p["settledTs"]) < ms(we)]
    settled.sort(key=lambda p: int(p["settledTs"]))
    res = {"W": 0, "L": 0, "P": 0, "other": 0}
    rows = []
    for p in settled:
        r = str(p.get("result") or "").upper()
        k = {"WIN": "W", "LOSS": "L", "PUSH": "P"}.get(r, "other")
        res[k] += 1
        rows.append((datetime.fromtimestamp(int(p["settledTs"]) / 1000, ET).strftime("%a %m/%d"), k if k != "other" else r,
                     label(p["marketId"], p["outcomeId"]), f(p.get("cost")), f(p.get("payout")), f(p.get("pnl")),
                     " (resettled)" if p.get("resettled") else ""))
    staked = sum(r[3] for r in rows)
    pnl = sum(r[5] for r in rows)

    openp = paged("/v3/portfolio/positions", {"keyId": me})
    openp = [p for p in openp if int(p.get("qty") or 0) > 0]
    open_cost = sum(f(p.get("cost")) for p in openp)

    span = f"{ws.strftime('%a %b %d')} - {(we - timedelta(days=1)).strftime('%a %b %d, %Y')}"
    L = [f"NOVIG WEEKLY RECONCILIATION | {span} (ET)", ""]
    L += ["BALANCE",
          f"  Now:                {money(bal_now)}",
          f"  Week start:         {money(bal_start)}",
          f"  Week end:           {money(bal_end)}",
          f"  Change in week:     {money(bal_end - bal_start)}", ""]
    L += ["LEDGER (week, by kind)"] + [f"  {k:<15} {money(v)}" for k, v in sorted(kinds.items())] + \
         [f"  {'TOTAL':<15} {money(sum(kinds.values()))}   (equals change in week)", ""]
    L += ["SETTLED BETS (week)",
          f"  Record: {res['W']}-{res['L']}-{res['P']}" + (f" (+{res['other']} other)" if res["other"] else ""),
          f"  Staked: {money(staked)} | Returned: {money(sum(r[4] for r in rows))} | P&L: {money(pnl)}"
          + (f" | ROI: {100 * pnl / staked:+.1f}%" if staked else ""), ""]
    for d, k, lab, c, pay, pl, rs in rows:
        L.append(f"  {d}  {k:<2} {lab}  | cost {money(c)} payout {money(pay)} pnl {money(pl)}{rs}")
    L += ["", "TRADING (week)",
          f"  Filled orders: {len(orders)} | Fills: {len(fills)} | Cost of fills: {money(fill_cost)} | Fees: {money(fill_fee)}",
          "", f"OPEN POSITIONS (now): {len(openp)} | Cost at risk: {money(open_cost)}"]
    for p in openp:
        L.append(f"  {label(p['marketId'], p['outcomeId'])}  | qty {p.get('qty')} cost {money(f(p.get('cost')))}")
    L += ["", "CSV (settled bets)", "date,result,bet,cost,payout,pnl"]
    L += [f"{d},{k},\"{lab}\",{c:.2f},{pay:.2f},{pl:.2f}" for d, k, lab, c, pay, pl, _ in rows]
    L += ["", "Source: Novig API, read-only key (management::read). Balances rebuilt from the account ledger."]
    subject = f"Novig weekly: {span} | {res['W']}-{res['L']}-{res['P']} | P&L {money(pnl)}"
    return subject, "\n".join(L), {"settled": len(rows), "open": len(openp), "tx": len(week_tx)}


def send(subject, body):
    user = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("EMAIL_TO", "").strip() or user
    if not (user and pw):
        raise SystemExit("Email not configured (GMAIL_ADDRESS / GMAIL_APP_PASSWORD secrets). Nothing sent.")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())


def main():
    if not nv.ready():
        print("STOP: Novig key unavailable or not read-only.")
        sys.exit(1)
    subject, body, counts = build(datetime.now(timezone.utc))
    send(subject, body)
    # Logs are public: counts only, never amounts.
    print(f"Email sent. Settled bets: {counts['settled']}, open positions: {counts['open']}, ledger rows: {counts['tx']}.")


if __name__ == "__main__":
    main()
