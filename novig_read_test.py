#!/usr/bin/env python3
"""
Novig read-only test (manual run). Shows that signed reads work and are read-only, before anything is wired in:
  1. key check (scope must be read-only, or everything stops)
  2. catalog (events + markets)
  3. one market's order book: signed vs public route, same moment, compared level by level
  4. account: balance / orders / fills / positions -> COUNTS AND FIELD NAMES ONLY (the repo and its logs are public;
     no amounts, prices or IDs of your bets are printed)
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import novig_signed as nv

PUBLIC = "https://api.novig.com"


def pub(path, params):
    req = urllib.request.Request(PUBLIC + path + "?" + urllib.parse.urlencode(params),
                                 headers={"Accept": "application/json", "User-Agent": "novig-read-test"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fields(x):
    if isinstance(x, dict):
        return sorted(x.keys())
    if isinstance(x, list) and x and isinstance(x[0], dict):
        return sorted(x[0].keys())
    return type(x).__name__


def items_count(d):
    """Pages come as {items, next}; a management key's pages may be nested per wallet key id."""
    if isinstance(d, dict) and "items" in d:
        return len(d["items"]), fields(d["items"])
    if isinstance(d, dict):
        tot, f = 0, None
        for v in d.values():
            if isinstance(v, dict) and "items" in v:
                tot += len(v["items"])
                f = f or fields(v["items"])
            elif isinstance(v, list):   # per-wallet arrays (positions)
                tot += len(v)
                f = f or fields(v)
        return tot, f
    if isinstance(d, list):
        return len(d), fields(d)
    return None, fields(d)


def main():
    print("1) KEY CHECK")
    if not nv.ready():
        print("   STOP: signed reads not available or key is not read-only.")
        print("   " + nv.diagnose())
        sys.exit(1)
    print(f"   OK: scope = {nv.scope()} (read-only). Client is GET-only.")

    print("\n2) CATALOG (signed)")
    now = datetime.now(timezone.utc)
    lo, hi = int(now.timestamp() * 1000), int((now + timedelta(days=2)).timestamp() * 1000)
    evs = nv.get("/v3/catalog/events", {"startsAfter": lo, "startsBefore": hi, "limit": 500})
    mks = nv.get("/v3/catalog/markets", {"startsAfter": lo, "startsBefore": hi, "limit": 1000})
    ev_items, mk_items = evs.get("items", []), mks.get("items", [])
    print(f"   events next 48h: {len(ev_items)} | markets: {len(mk_items)} | event fields: {fields(ev_items)}")
    leagues = {}
    for e in ev_items:
        leagues[e.get("league")] = leagues.get(e.get("league"), 0) + 1
    print(f"   by league: {dict(sorted(leagues.items(), key=lambda kv: -kv[1])[:12])}")

    print("\n3) ORDER BOOK: signed vs public, same market, back to back")
    by_ev = {e["eventId"]: e for e in ev_items}
    pick = next((m for m in mk_items if m.get("marketType") in ("MONEY", "SPREAD", "TOTAL") and m.get("status") == "OPEN"
                 and (by_ev.get(m.get("eventId")) or {}).get("league") in ("NBA", "NHL", "NFL", "NCAAF", "MLB")), None)
    if not pick:
        print("   no open main market found to compare")
    else:
        e = by_ev[pick["eventId"]]
        s = nv.get(f"/v3/catalog/markets/{pick['marketId']}/book", {"depth": 20})
        p = pub(f"/v3/public/catalog/markets/{pick['marketId']}/book", {"depth": 20})
        print(f"   market: {e.get('league')} {e.get('description')} {pick.get('marketType')} {pick.get('strike') or ''}")
        for o in pick.get("outcomes") or []:
            so = s.get("orders", {}).get(o["outcomeId"], [])
            po = p.get("orders", {}).get(o["outcomeId"], [])
            sd = sum(float(x["price"]) * int(x["qty"]) / 100 for x in so)
            pd = sum(float(x["price"]) * int(x["qty"]) / 100 for x in po)
            same = [(x["price"], x["qty"]) for x in so] == [(x["price"], x["qty"]) for x in po]
            print(f"   {o.get('name')}: signed {len(so)} orders ${sd:,.0f} | public {len(po)} orders ${pd:,.0f} | "
                  f"identical: {same}")
        print(f"   seq signed {s.get('seq')} vs public {p.get('seq')} | signed fields {fields(s)}")

    print("\n4) ACCOUNT (counts and field names only)")
    me = nv._S["id"]   # a management::read key's OWN id addresses the primary wallet
    for label, path, params in [
            ("balance", "/v3/account/balance", {}),
            ("open orders", "/v3/orders", {"keyId": me, "status": "OPEN", "limit": 500}),
            ("filled orders", "/v3/orders", {"keyId": me, "status": "FILLED", "limit": 500}),
            ("open orders (no keyId)", "/v3/orders", {"status": "OPEN", "limit": 500}),
            ("fills", "/v3/portfolio/fills", {"keyId": me, "limit": 500}),
            ("positions", "/v3/portfolio/positions", {"keyId": me}),
            ("settled bets (history)", "/v3/history/positions", {"keyId": me, "status": "SETTLED", "limit": 500})]:
        try:
            d = nv.get(path, params)
            if label == "balance":
                print(f"   {label}: read OK (amount not printed) | fields {fields(d)}")
            else:
                n, f = items_count(d)
                print(f"   {label}: {n} items | fields {f}")
        except Exception as ex:
            print(f"   {label}: {str(ex)[:150]}")
        time.sleep(0.3)
    print("\nDone. Nothing was placed, changed or cancelled (GET requests only).")


if __name__ == "__main__":
    main()
