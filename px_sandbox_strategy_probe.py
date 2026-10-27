#!/usr/bin/env python3
"""
ProphetX SANDBOX order-type probe (Oct 27, practice money only). Refuses to run unless PX_BASE is the sandbox.
Answers two questions for the partial-fill switch:
  A. Does ProphetX accept an immediate-or-cancel strategy? Tries several spellings at a NON-crossing price (nothing can
     fill), prints accept/reject + the API's error text (which often lists the allowed values), cancels anything that rests.
  B. What does fillOrKill do when you ask for MORE than is offered at the price: all-or-nothing, or a partial?

(Original sandbox test notes below.)

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


def levels_for(m):
    for levels in m.get("selections") or []:
        lv = [x for x in levels or [] if x.get("price") is not None and float(x.get("value") or 0) >= 1]
        if lv:
            return levels, max(lv, key=lambda x: int(x["price"]))
    return None, None


def nofill(price):
    """A price far BETTER for the taker than anything offered (e.g. +300 when the best is -120), so it cannot fill."""
    return 300 if int(price) < 200 else int(price) + 200


def main():
    st, d = call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
    lm._PXT["token"] = ((d or {}).get("data") or {}).get("access_token") if isinstance(d, dict) else None
    if not lm._PXT["token"]:
        sys.exit(f"Sandbox login failed: {st} {d}")
    print("1) Logged in to the sandbox.")
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
                if (m.get("type") or "").lower() != "moneyline":
                    continue
                levels, best = levels_for(m)
                if best and best.get("strike_id"):
                    pick = (e, m, levels, best)
                    break
            if pick:
                break
        if pick:
            break
    if not pick:
        sys.exit("No sandbox moneyline with liquidity right now. Try again later.")
    e, m, levels, best = pick
    price, avail = int(best["price"]), float(best.get("value") or 0)
    print(f"2) {e.get('name')} | taking '{best.get('name')}' best {price:+d} with ${avail:,.2f} at that price")

    print("A) Strategy names at a NON-crossing price (cannot fill):")
    for strat in ("immediateOrCancel", "ImmediateOrCancel", "ioc", "IOC", "immediate_or_cancel", "fillAndKill", "limit", "bogusStrategyXYZ"):
        ext = str(uuid.uuid4())
        order = {"external_id": ext, "strike_id": best["strike_id"], "price": nofill(price), "quantity": 1.0, "order_strategy": strat}
        st, resp = call("/v4/mm/submit_order", order)
        o = (((resp or {}).get("data") or {}).get("order") or {}) if isinstance(resp, dict) else {}
        oid = o.get("order_id") or o.get("id")
        time.sleep(2)
        rest = None
        if oid:
            st2, r2 = call("/v4/mm/cancel_order", {"external_id": ext, "order_id": oid})
            rest = f"cancel -> {st2}: {json.dumps(r2)[:160] if isinstance(r2, dict) else str(r2)[:160]}"
        print(f"   {strat:20s} -> {st}: status={o.get('status')} strategy={o.get('order_strategy')} "
              f"{'' if isinstance(resp, dict) else str(resp)[:300]}" + (f" | {rest}" if rest else ""))

    print("B) fillOrKill asking MORE than is offered at the best price:")
    ext = str(uuid.uuid4())
    want = round(avail + 5.0, 2)
    order = {"external_id": ext, "strike_id": best["strike_id"], "price": price, "quantity": want, "order_strategy": "fillOrKill"}
    st, resp = call("/v4/mm/submit_order", order)
    o = (((resp or {}).get("data") or {}).get("order") or {}) if isinstance(resp, dict) else {}
    oid = o.get("order_id") or o.get("id")
    print(f"   submit {json.dumps(order)} -> {st}: {json.dumps(resp)[:600] if isinstance(resp, dict) else resp}")
    time.sleep(4)
    st, tr = call("/v4/mm/get_trades")
    mine = [t for t in (((tr or {}).get("data") or {}).get("trades") or [] if isinstance(tr, dict) else []) if str(t.get("order_id")) == str(oid)]
    got = sum(float(t.get("quantity") or 0) for t in mine)
    print(f"   filled {got:g} of {want:g} asked (${avail:,.2f} was offered at {price:+d}) -> "
          + ("ALL-OR-NOTHING (nothing filled)" if got == 0 else "PARTIAL FILL (behaves like IOC)" if got < want - 1e-6 else "FULL fill (more liquidity arrived?)"))
    if oid:
        st, r = call("/v4/mm/cancel_order", {"external_id": ext, "order_id": oid})
        print(f"   cleanup cancel -> {st}: {json.dumps(r)[:200] if isinstance(r, dict) else str(r)[:200]}")
    print("Done. Sandbox only; no real money.")


if __name__ == "__main__":
    main()
