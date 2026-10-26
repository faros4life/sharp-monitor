#!/usr/bin/env python3
"""
ProphetX $1 REAL-MONEY order test with the TRADING key (Oct 26). Runs only when CONFIRM_REAL_ORDER=ONE_DOLLAR.
Places ONE fillOrKill order: quantity 1.0 on a full-game moneyline priced between -185 and +185 (35-65%), not on any
game Peter holds, at the best price on the screen. Then reads the fill back and answers:
  does submit_order's `quantity` mean the STAKE ($1 risked) or the TO-WIN amount? -> sets PX_QTY_MEANS for live.
Public log: the test order's own price/size and yes/no checks only. No balances, no other positions.
"""
import json
import os
import sys
import time
import uuid

import book_check as bc
import px_live as px

if os.environ.get("CONFIRM_REAL_ORDER") != "ONE_DOLLAR":
    sys.exit("REFUSING: CONFIRM_REAL_ORDER is not ONE_DOLLAR.")
if "sandbox" in px.BASE:
    print("Note: running against the SANDBOX base.")
if not (px.ACCESS and px.SECRET):
    sys.exit("Missing PROPHETX_TRADE_ACCESS_KEY / PROPHETX_TRADE_SECRET_KEY.")


def main():
    if not px.login():
        sys.exit("Trading-key login failed.")
    print("1) Logged in with the trading key.")
    held = set()
    try:
        held = {str(t.get("strike_id")) for t in px.trades()}
    except Exception as ex:
        sys.exit(f"Couldn't read trades (fail closed): {str(ex)[:80]}")
    if not bc.px_login():
        sys.exit("Read-key login failed (needed to find a market).")
    pick = None
    for lg in ("NBA", "NHL", "NCAAF", "NFL"):
        for e in bc.px_events(lg):
            if (e.get("status") or "not_started") != "not_started":
                continue
            for m in bc.px_markets(e["event_id"]):
                if (m.get("type") or "").lower() != "moneyline" or (m.get("status") or "active") != "active":
                    continue
                for levels, _ln in bc.px_lines(m):
                    lv = [x for x in levels or [] if x.get("price") is not None and float(x.get("value") or 0) >= 2
                          and -185 <= int(x["price"]) <= 185 and str(x.get("strike_id")) not in held]
                    if lv:
                        pick = (lg, e, max(lv, key=lambda x: int(x["price"])))
                        break
                if pick:
                    break
            if pick:
                break
        if pick:
            break
    if not pick:
        sys.exit("No suitable moneyline right now (-185..+185 with $2+ available). Try again later.")
    lg, e, best = pick
    price = int(best["price"])
    print(f"2) {lg}: {e.get('name')} | taking '{best.get('name')}' at {price:+d} | ${float(best.get('value') or 0):,.0f} offered")
    order = {"external_id": str(uuid.uuid4()), "strike_id": best["strike_id"], "price": price, "quantity": 1.0,
             "order_strategy": "fillOrKill"}
    try:
        resp = px._call("/v4/mm/submit_order", order)
    except Exception as ex:
        try:
            msg = ex.read().decode()[:400]
        except Exception:
            msg = str(ex)[:300]
        sys.exit(f"3) submit_order FAILED: {getattr(ex, 'code', '?')} {msg}")
    o = ((resp.get("data") or {}).get("order") or {})
    oid = o.get("order_id") or o.get("id")
    print(f"3) submit_order {json.dumps(order)}\n   -> order id {oid}; status {o.get('status')}")
    time.sleep(4)
    mine = [t for t in px.trades() if str(t.get("order_id")) == str(oid)]
    print(f"4) Fills for this order: {len(mine)}")
    for t in mine:
        print("   " + json.dumps({k: t.get(k) for k in ("price", "quantity", "profit", "fee", "status", "winning_status", "matched_at")}))
    if mine:
        q = sum(float(t.get("quantity") or 0) for t in mine)
        prof = sum(float(t.get("profit") or 0) for t in mine)
        print(f"5) quantity filled {q:g}; 'profit' field {prof:g} at {price:+d}")
        if prof:
            ratio = prof / q if q else 0
            exp_stake = (100 / abs(price)) if price < 0 else price / 100
            means = "stake" if abs(ratio - exp_stake) < 0.05 else ("to_win" if abs(ratio - 1 / exp_stake) < 0.05 else "unclear")
            print(f"   profit/quantity = {ratio:.3f}; if quantity = stake it would be {exp_stake:.3f} -> quantity means: {means.upper()}")
        print("   Check ProphetX My Trades too: Cost $1.00 means quantity = STAKE; To-gain $1.00 means quantity = TO-WIN.")
    print("Done. ONE real order, about $1, fill-or-kill: nothing left resting.")


if __name__ == "__main__":
    main()
