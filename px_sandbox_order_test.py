#!/usr/bin/env python3
"""
ProphetX SANDBOX order test (practice money only). Refuses to run unless PX_BASE is the sandbox.

1. Log in, read the practice balance.
2. Pick one upcoming game (NBA, else MLB/NFL/college football), its moneyline, and the best price a bettor can take.
3. Submit ONE fillOrKill order: quantity 1.0 at that price (takes what's there, cancels the rest ~2 s later).
4. Print the full response, look the order up (tries the likely routes), read the balance again,
   and cancel anything still open. Answers: does `quantity` mean risk or to-win, and is `price` the taker's price?
"""
import json
import os
import sys
import time
import uuid

import liquidity_monitor as lm

if "sandbox" not in lm.PX_BASE:
    sys.exit(f"REFUSING: PX_BASE is {lm.PX_BASE} - this test only runs against the sandbox.")


def call(path, body=None):
    try:
        return 200, lm.px_call(path, body)
    except Exception as ex:
        code = getattr(ex, "code", "?")
        try:
            msg = ex.read().decode()[:300]
        except Exception:
            msg = str(ex)[:300]
        return code, msg


def balance():
    st, d = call("/v4/mm/get_balance")
    return (d.get("data") or {}).get("balance") if st == 200 and isinstance(d, dict) else f"{st} {d}"


def main():
    st, d = call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
    lm._PXT["token"] = ((d or {}).get("data") or {}).get("access_token") if isinstance(d, dict) else None
    if not lm._PXT["token"]:
        sys.exit(f"Sandbox login failed: {st} {d}")
    b0 = balance()
    print(f"1) Logged in to sandbox. Practice balance: {b0}")

    pick = None
    for tid in (132, 109, 31, 27653):
        st, ev = call(f"/mm/get_sport_events?tournament_id={tid}")
        evs = ((ev or {}).get("data") or {}).get("sport_events") or [] if isinstance(ev, dict) else []
        for e in evs:
            if (e.get("status") or "not_started") != "not_started":
                continue
            st, mk = call(f"/v4/mm/get_markets?event_id={e['event_id']}")
            data = (mk or {}).get("data") if isinstance(mk, dict) else None
            mks = data if isinstance(data, list) else ((data or {}).get("markets") or (data or {}).get(str(e["event_id"])) or [])
            for m in mks:
                if (m.get("type") or "").lower() != "moneyline" or not m.get("selections"):
                    continue
                for levels in m["selections"]:
                    lv = [x for x in levels or [] if x.get("price") is not None and float(x.get("value") or 0) >= 1]
                    if lv:
                        best = max(lv, key=lambda x: int(x["price"]))
                        pick = (e, m, levels, best)
                        break
                if pick:
                    break
            if pick:
                break
        if pick:
            break
    if not pick:
        sys.exit("No sandbox moneyline with at least $1 available to take. Try again later.")
    e, m, levels, best = pick
    print(f"2) Game: {e.get('name')} ({e.get('scheduled')}) | market {m.get('type')} id {m.get('id')}")
    print(f"   Selection level fields: {sorted(best.keys())}")
    print(f"   Taking: {json.dumps({k: best.get(k) for k in ('name', 'price', 'quantity', 'value', 'strike_id', 'line_id', 'outcome_id')})}")
    strike = best.get("strike_id") or levels[0].get("strike_id")
    if not strike:
        sys.exit("No strike_id on the selection - check the field list above.")

    ext = str(uuid.uuid4())
    order = {"external_id": ext, "strike_id": strike, "price": int(best["price"]), "quantity": 1.0,
             "order_strategy": "fillOrKill"}
    st, resp = call("/v4/mm/submit_order", order)
    print(f"3) submit_order {json.dumps(order)}\n   -> {st}: {json.dumps(resp)[:1200] if isinstance(resp, dict) else resp}")
    o = (((resp or {}).get("data") or {}).get("order") or {}) if isinstance(resp, dict) else {}
    oid = o.get("order_id") or o.get("id")

    time.sleep(4)
    print("4) Order lookup (finding which route reports fills):")
    for path in (f"/v4/mm/get_order/{oid}", f"/v4/mm/get_order_id?order_id={oid}", f"/v4/mm/get_order?order_id={oid}",
                 f"/v4/mm/get_order_matched_detail?order_id={oid}", f"/v4/mm/get_order_matched_detail/{oid}",
                 "/v4/mm/get_order_history", "/v4/mm/get_order_history?limit=5", "/v4/mm/get_trades", "/v4/mm/get_trades?limit=5",
                 "/v4/mm/get_transactions?limit=5"):
        st, r = call(path)
        print(f"   GET {path} -> {st}: {json.dumps(r)[:700] if isinstance(r, dict) else str(r)[:160]}")
    b1 = balance()
    print(f"5) Practice balance after: {b1} (before {b0})")
    if oid:
        st, r = call("/v4/mm/cancel_order", {"external_id": ext, "order_id": oid})
        print(f"6) cancel_order (cleanup of any remainder) -> {st}: {json.dumps(r)[:300] if isinstance(r, dict) else str(r)[:200]}")
    print("Done. Sandbox only; no real money involved.")


if __name__ == "__main__":
    main()
