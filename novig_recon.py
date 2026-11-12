#!/usr/bin/env python3
"""NOVIG RECONCILIATION (Nov 12, 2026). READ ONLY: GETs only, no order is created, cancelled or amended.

For each Novig order id given (NOVIG_ORDER_IDS, comma separated), reports the venue's own status, the filled
contracts from the Order object and the filled contracts/cost from the fills list, so the two can be compared. Then
reports every OPEN/resting order on the account and the open positions, and the exposure in UNITS.

Counts, contracts, statuses and UNITS go to the log; dollars are sent to the private inbox only when EMAIL=1.
Resting orders matter because an open order is exposure that no position read can see yet.

Env: NOVIG_TRADE_KEY_ID / NOVIG_TRADE_KEY_PEM (read-only use here), NOVIG_ORDER_IDS, UNIT (default 300), EMAIL.
"""
import json
import os
import sys

import novig_live_order as nv

UNIT = float(os.environ.get("UNIT") or 300)


def get(path, params=None):
    try:
        st, d = nv.call("GET", path, params)
        return st, d
    except Exception as ex:
        return None, {"error": f"{type(ex).__name__}: {str(ex)[:80]}"}


def order_detail(oid):
    st, d = get(f"/v3/orders/{oid}")
    out = {"order_id": oid, "http": st, "status": None, "qty": None, "remaining": None, "filled_from_order": None,
           "client_id": None, "outcome_id": None, "price_cents": None, "tif": None, "good_till": None, "error": None}
    if st != 200 or not isinstance(d, dict):
        out["error"] = str((d or {}).get("error") or d)[:120]
        return out
    o = d.get("order") or d
    out.update(status=str(o.get("status") or "").upper() or None, qty=o.get("qty"), remaining=o.get("remaining"),
               client_id=o.get("clientId"), outcome_id=o.get("outcomeId"), price_cents=o.get("price"),
               tif=o.get("tif"), good_till=o.get("goodTillTime"))
    try:
        out["filled_from_order"] = int(o["qty"]) - int(o["remaining"])
    except Exception:
        pass
    return out


def fills_index():
    """{orderId: (contracts, cost)} from the account's fills list - one call, used for every id."""
    st, d = get("/v3/portfolio/fills", {"limit": 200})
    if st != 200:
        return None, str((d or {}).get("error") or d)[:120]
    items = d if isinstance(d, list) else (d.get("items") or d.get("fills") or d.get("data") or [])
    idx = {}
    for f in items:
        k = str(f.get("orderId"))
        q, c = idx.get(k, (0, 0.0))
        idx[k] = (q + int(f.get("qty") or 0), round(c + float(f.get("cost") or 0), 2))
    return idx, None


def open_orders():
    for path, params in (("/v3/orders", {"status": "OPEN", "limit": 100}), ("/v3/orders", {"limit": 100})):
        st, d = get(path, params)
        if st == 200:
            items = d if isinstance(d, list) else (d.get("items") or d.get("orders") or d.get("data") or [])
            rest = [o for o in items if str(o.get("status") or "").upper() in ("OPEN", "PENDING")]
            return rest, None
    return None, "orders list unreadable"


def positions():
    for path in ("/v3/portfolio/positions", "/v3/positions"):
        st, d = get(path)
        if st == 200:
            items = d if isinstance(d, list) else (d.get("items") or d.get("positions") or d.get("data") or [])
            return [p for p in items if int(p.get("qty") or 0) > 0], None
    return None, "positions unreadable"


def main():
    ids = [x.strip() for x in (os.environ.get("NOVIG_ORDER_IDS") or "").split(",") if x.strip()]
    if not nv.KEY_ID or not nv.PEM:
        print("novig_recon: no Novig key in the environment; nothing read.")
        return 1
    fidx, ferr = fills_index()
    print(f"novig_recon: {len(ids)} order id(s); fills list {'read' if fidx is not None else 'UNREADABLE: ' + str(ferr)}")
    rows, mismatch = [], 0
    for oid in ids:
        o = order_detail(oid)
        fq, fc = (fidx or {}).get(str(oid), (None, None))
        o["filled_from_fills"], o["cost_from_fills"] = fq, fc
        agree = (o["filled_from_order"] is not None and fq is not None and o["filled_from_order"] == fq)
        o["agrees"] = agree
        mismatch += 0 if agree else 1
        rows.append(o)
        print(f"  {oid}  http={o['http']}  status={o['status']}  qty={o['qty']} remaining={o['remaining']}"
              f"  filled(order)={o['filled_from_order']}  filled(fills)={fq}  agree={agree}"
              f"  tif={o['tif']} good_till={o['good_till']}  clientId={'yes' if o['client_id'] else 'NONE'}"
              + (f"  error={o['error']}" if o.get("error") else ""))
    rest, rerr = open_orders()
    pos, perr = positions()
    print(f"  resting/open orders: {('UNREADABLE: ' + rerr) if rest is None else len(rest)}")
    for o in rest or []:
        print(f"    OPEN {o.get('id') or o.get('orderId')} outcome={o.get('outcomeId')} qty={o.get('qty')}"
              f" remaining={o.get('remaining')} price={o.get('price')} tif={o.get('tif')}")
    print(f"  open positions: {('UNREADABLE: ' + perr) if pos is None else len(pos)}")
    exp_contracts = sum(int(p.get("qty") or 0) for p in pos or [])
    print(f"  position exposure: {exp_contracts} contracts = {exp_contracts / 100:.2f} dollars-at-risk-equivalent"
          f" = {exp_contracts / 100 / UNIT:.2f} unit(s) at a {UNIT:.0f} unit")
    print(f"  order/fills disagreements: {mismatch} of {len(ids)}")
    os.makedirs("summary", exist_ok=True)
    json.dump({"orders": rows, "resting": rest, "positions_count": None if pos is None else len(pos),
               "exposure_contracts": exp_contracts, "fills_error": ferr, "orders_error": rerr, "positions_error": perr},
              open("summary/novig_recon.json", "w"), indent=1)
    if os.environ.get("EMAIL") == "1":
        try:
            import smtplib
            from email.mime.text import MIMEText
            user, pw = os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"]
            to = os.environ.get("EMAIL_TO") or user
            body = json.dumps({"orders": rows, "resting": rest, "exposure_contracts": exp_contracts}, indent=1)
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = f"NOVIG RECON: {len(ids)} order(s), {0 if rest is None else len(rest)} resting, {mismatch} disagreement(s)"
            msg["From"], msg["To"] = user, to
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
                s.login(user, pw)
                s.sendmail(user, [to], msg.as_string())
            print("  detail emailed (private).")
        except Exception as ex:
            print(f"  email failed: {type(ex).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
