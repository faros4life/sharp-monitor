#!/usr/bin/env python3
"""One-time / on-demand: email Novig wallet balances (main + subaccounts) and recent transfers. Read-only key.
Nothing financial is printed in the (public) Actions log."""
import json
import sys
from datetime import datetime, timezone

import novig_signed as nv
import novig_weekly as nw


def main():
    if not nv.ready():
        print("STOP: Novig key unavailable or not read-only.")
        sys.exit(1)
    L = [f"NOVIG WALLETS | {datetime.now(nw.ET).strftime('%a %b %d %I:%M %p ET')}", ""]
    try:
        L.append(f"Main wallet balance: {nw.money(nw.f(nv.get('/v3/account/balance').get('balance')))}")
    except Exception as ex:
        L.append(f"Main wallet balance: error {str(ex)[:80]}")
    try:
        subs = nv.get("/v3/account/subaccounts")
        items = subs.get("items") if isinstance(subs, dict) else subs
        L.append("")
        L.append("Subaccounts:")
        for s in items or []:
            L.append(f"  {s.get('label')}  key {s.get('keyId')}  balance {nw.money(nw.f(s.get('balance')))}")
        if not items:
            L.append(f"  none listed (raw: {json.dumps(subs)[:200]})")
    except Exception as ex:
        L.append(f"Subaccounts: error {str(ex)[:120]}")
    try:
        tr = nv.get("/v3/account/transfers", {"limit": 20})
        items = tr.get("items") if isinstance(tr, dict) else tr
        L.append("")
        L.append("Recent transfers:")
        for t in items or []:
            L.append(f"  {t.get('createdAt')}  {t.get('direction')}  {t.get('amount')}  status {t.get('status')}"
                     + (f"  (balance at rejection {t.get('actualBalance')})" if t.get("actualBalance") else ""))
        if not items:
            L.append(f"  none listed (raw: {json.dumps(tr)[:200]})")
    except Exception as ex:
        L.append(f"Recent transfers: error {str(ex)[:120]}")
    nw.send("Novig wallets check", "\n".join(L))
    print("Wallet check emailed.")


if __name__ == "__main__":
    main()
