#!/usr/bin/env python3
"""NOVIG RECONCILIATION (Nov 12, 2026). READ ONLY: reads records, places/cancels/amends nothing.

Novig BLOCKS cloud servers, so the cloud holds no Novig trading key: orders are dispatched to Peter's home runner
(private repo novig-runner), which places them and writes every result to snapshot/novig_orders.json. That file is
therefore the only cloud-readable record of what happened to an order, and it is what this reconciles, joining the
THREE identities a Novig order has:

    client_id   ours, sent as clientId and used as the executor's order_id in the ledger (book_live.novig_place)
    order_id    Novig's own orderId, returned to the home runner on acceptance
    outcome_id  the contract the exposure sits on (marketId/outcomeId is how a position is identified)

For each id given it reports the status, the filled contracts and cost the home runner recorded, whether the order is
still resting, and the exposure in UNITS. An id that appears in the ledger but not in the results file is reported as
UNRECONCILED - that is the state that matters, because it is exposure nobody can see.

Statuses, contracts and UNITS go to the log; dollars go to the private inbox only when EMAIL=1.
Env: NOVIG_SNAPSHOT_TOKEN (read-only, scoped to novig-runner), NOVIG_ORDER_IDS, UNIT (default 300), EMAIL.
"""
import json
import os
import sys

import novig_live_order as nv

UNIT = float(os.environ.get("UNIT") or 300)


def results():
    """The home runner's order results (newest last), or None when unreadable."""
    import book_live as bl
    return bl.novig_results()


def ident(o):
    """The three identities of one result row, whatever shape the runner wrote."""
    return {"client_id": o.get("client_id") or o.get("clientId") or (o.get("order") or {}).get("client_id"),
            "order_id": o.get("order_id") or o.get("orderId") or o.get("id"),
            "outcome_id": o.get("outcome_id") or o.get("outcomeId") or (o.get("order") or {}).get("outcome_id")}


def row_of(o):
    i = ident(o)
    filled = o.get("filled_qty") if o.get("filled_qty") is not None else o.get("filled")
    return dict(i, status=str(o.get("status") or "").upper() or None, qty=o.get("qty") or (o.get("order") or {}).get("qty"),
                filled_qty=filled, filled_cost=o.get("filled_cost"), tif=o.get("tif") or (o.get("order") or {}).get("tif"),
                error=o.get("error"), play_key=o.get("play_key") or (o.get("order") or {}).get("play_key"),
                resting=str(o.get("status") or "").upper() in ("OPEN", "PENDING"))


def main():
    ids = [x.strip() for x in (os.environ.get("NOVIG_ORDER_IDS") or "").split(",") if x.strip()]
    rs = results()
    if rs is None:
        print("novig_recon: the home runner's results file is UNREADABLE (no token, or novig-runner unreachable).")
        return 1
    rows = [row_of(o) for o in rs]
    print(f"novig_recon: {len(rows)} result row(s) in the home runner's file; reconciling {len(ids)} id(s)")
    by = {}
    for r in rows:
        for k in ("client_id", "order_id"):
            if r.get(k):
                by[str(r[k])] = r
    out, unrec = [], 0
    for oid in ids:
        r = by.get(str(oid))
        if not r:
            unrec += 1
            out.append({"id": oid, "reconciled": False})
            print(f"  {oid}  UNRECONCILED: no row in the home runner's results file (it matches neither a client_id nor an order_id)")
            continue
        out.append(dict(r, id=oid, reconciled=True))
        print(f"  {oid}  status={r['status']}  qty={r['qty']} filled={r['filled_qty']}  resting={r['resting']}"
              f"  client_id={'yes' if r['client_id'] else 'NONE'}  order_id={'yes' if r['order_id'] else 'NONE'}"
              f"  outcome={r['outcome_id']}" + (f"  error={str(r['error'])[:60]}" if r.get("error") else ""))
    resting = [r for r in rows if r["resting"]]
    print(f"  resting/open orders in the file: {len(resting)}")
    for r in resting:
        print(f"    RESTING client_id={r['client_id']} order_id={r['order_id']} outcome={r['outcome_id']} qty={r['qty']} filled={r['filled_qty']}")
    filled = [r for r in rows if (r.get("filled_qty") or 0) > 0]
    contracts = sum(int(r.get("filled_qty") or 0) for r in filled)
    print(f"  filled rows: {len(filled)}; filled contracts: {contracts} = {contracts / 100 / UNIT:.2f} unit(s) at a {UNIT:.0f} unit")
    missing_ids = [r for r in rows if not r.get("client_id") or not r.get("order_id")]
    print(f"  rows missing one of the two order identities: {len(missing_ids)}")
    dups = {}
    for r in rows:
        k = str(r.get("client_id") or "")
        if k:
            dups[k] = dups.get(k, 0) + 1
    repeats = {k: v for k, v in dups.items() if v > 1}
    print(f"  client_ids appearing more than once (a repeat submission would show here): {len(repeats)}"
          + (f" -> {list(repeats.items())[:5]}" if repeats else ""))
    print(f"  UNRECONCILED ids: {unrec} of {len(ids)}")
    os.makedirs("summary", exist_ok=True)
    json.dump({"asked": ids, "rows": out, "resting": resting, "filled_contracts": contracts,
               "rows_missing_an_identity": len(missing_ids), "repeat_client_ids": repeats, "unreconciled": unrec},
              open("summary/novig_recon.json", "w"), indent=1)
    if os.environ.get("EMAIL") == "1":
        try:
            import smtplib
            from email.mime.text import MIMEText
            user, pw = os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"]
            to = os.environ.get("EMAIL_TO") or user
            msg = MIMEText(json.dumps({"rows": out, "resting": resting}, indent=1), "plain", "utf-8")
            msg["Subject"] = f"NOVIG RECON: {len(ids)} asked, {unrec} unreconciled, {len(resting)} resting, {contracts} contracts filled"
            msg["From"], msg["To"] = user, to
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as sm:
                sm.login(user, pw)
                sm.sendmail(user, [to], msg.as_string())
            print("  detail emailed (private).")
        except Exception as ex:
            print(f"  email failed: {type(ex).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
