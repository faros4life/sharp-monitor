#!/usr/bin/env python3
"""
ProphetX fee model check on the LIVE account (read-only: login + GET /v4/mm/get_trades only; no orders).
For each recent fill prints fee as a % of profit and as a % of stake - RATIOS ONLY (the Actions log is public).
2% of winnings -> fee/profit ~ 2.0%.  1% of stake -> fee/stake ~ 1.0%.
"""
import sys

import liquidity_monitor as lm


def main():
    d = lm.px_call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
    lm._PXT["token"] = (d.get("data") or {}).get("access_token")
    if not lm._PXT["token"]:
        sys.exit("Login failed.")
    where = "SANDBOX" if "sandbox" in lm.PX_BASE else "LIVE"
    trades = ((lm.px_call("/v4/mm/get_trades").get("data") or {}).get("trades")) or []
    print(f"{where} account: {len(trades)} recent fills (ratios only, no amounts)")
    rp, rs = [], []
    for t in trades[:40]:
        fee, prof, qty = float(t.get("fee") or 0), float(t.get("profit") or 0), float(t.get("quantity") or 0)
        a = fee / prof * 100 if prof else None
        b = fee / qty * 100 if qty else None
        if a is not None:
            rp.append(a)
        if b is not None:
            rs.append(b)
        print(f"  price {t.get('price'):>5} | fee = {a:5.2f}% of profit | {b:5.2f}% of stake | "
              f"status {t.get('status')} / {t.get('winning_status')}" if a is not None and b is not None
              else f"  price {t.get('price')} | fee/profit n/a")
    if rp:
        mid = lambda v: sorted(v)[len(v) // 2]
        print(f"\nMedian: fee = {mid(rp):.2f}% of profit, {mid(rs):.2f}% of stake.")
        print("Reading: ~2% of profit on every price = '2% of winnings'; ~1% of stake on every price = '1% of stake'.")


if __name__ == "__main__":
    main()
