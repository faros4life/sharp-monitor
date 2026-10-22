#!/usr/bin/env python3
"""
ProphetX read-only probe (manual run only). Logs in with the two key halves from GitHub secrets, then reads:
tournaments -> one upcoming game in NFL/NCAAF/NBA/NHL -> its markets, and prints the structure so the
book check and liquidity monitor can be wired to the right fields. Never places, changes or cancels orders.
Tokens and keys are never printed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ACCESS = os.environ.get("PROPHETX_ACCESS_KEY", "")
SECRET = os.environ.get("PROPHETX_SECRET_KEY", "")
BASES = [b for b in [os.environ.get("PX_BASE", "")] if b] or [
    "https://cash.api.prophetx.co/partner", "https://api.prophetx.co/partner", "https://api.sandbox.prophetx.dev/partner"]
MAIN = {"nfl", "nba", "nhl", "ncaaf", "ncaa football", "college football", "ncaa fb", "ncaafb", "cfb"}


def call(base, path, token=None, body=None):
    for i in range(4):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                out = json.loads(r.read().decode())
            time.sleep(1.2)   # stay well under ProphetX's rate limit
            return out
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and i < 3:
                wait = int(ex.headers.get("Retry-After") or 0) or 5 * (i + 1)
                print(f"  rate limited on {path.split('?')[0]}, waiting {wait}s")
                time.sleep(wait)
                continue
            raise


def shape(x, depth=0, maxd=5):
    """Field names and types, with short sample values (no secrets in market data)."""
    pad = "  " * depth
    if depth > maxd:
        return pad + "..."
    if isinstance(x, dict):
        out = []
        for k, v in list(x.items())[:40]:
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out.append(shape(v, depth + 1, maxd))
            else:
                out.append(f"{pad}{k}: {repr(v)[:60]}")
        return "\n".join(out)
    if isinstance(x, list):
        return f"{pad}[list of {len(x)}]" + ("\n" + shape(x[0], depth + 1, maxd) if x else "")
    return pad + repr(x)[:60]


def main():
    if not ACCESS or not SECRET:
        print("Missing PROPHETX_ACCESS_KEY / PROPHETX_SECRET_KEY secrets.")
        sys.exit(1)
    token, base = None, None
    for b in BASES:
        try:
            d = call(b, "/auth/login", body={"access_key": ACCESS, "secret_key": SECRET})
            token = (d.get("data") or {}).get("access_token") or d.get("access_token")
            if token:
                base = b
                print(f"Login OK at {b} (token received, not shown)")
                break
            print(f"Login at {b}: no access_token in response; keys present: {list((d.get('data') or d).keys())}")
        except urllib.error.HTTPError as ex:
            print(f"Login at {b}: HTTP {ex.code} {ex.read().decode()[:200]}")
        except Exception as ex:
            print(f"Login at {b}: {ex}")
    if not token:
        print("No login succeeded.")
        sys.exit(1)
    try:
        t = call(base, "/mm/get_tournaments", token)
    except urllib.error.HTTPError as ex:
        print(f"get_tournaments HTTP {ex.code} {ex.read().decode()[:200]}")
        sys.exit(1)
    tours = ((t.get("data") or {}).get("tournaments")) or []
    print(f"Tournaments: {len(tours)}")
    picks = [x for x in tours if (x.get("name") or "").strip().lower() in MAIN]
    print("Main tournaments: " + ", ".join(f"{x.get('name')} ({x.get('id')})" for x in picks))
    others = sorted({x.get("name") for x in tours if any(w in (x.get("name") or "").lower()
                     for w in ("football", "ncaa", "college", "cfb"))})
    print("Other football/college tournament names: " + "; ".join(others[:30]))
    for tour in picks[:4]:
        try:
            ev = call(base, f"/mm/get_sport_events?tournament_id={tour['id']}", token)
        except urllib.error.HTTPError as ex:
            print(f"get_sport_events {tour['id']} HTTP {ex.code}")
            continue
        events = ((ev.get("data") or {}).get("sport_events")) or []
        if not events:
            continue
        print(f"\nTournament {tour.get('name')}: {len(events)} events. First event fields:")
        print(shape(events[0], 1, 3))
        e = events[0]
        print(f"Event used: {e.get('name')} ({e.get('event_id')}), start {e.get('scheduled') or e.get('start_time') or ''}")
        try:
            m = call(base, f"/v4/mm/get_markets?event_id={e.get('event_id')}", token)
        except urllib.error.HTTPError as ex:
            print(f"get_markets HTTP {ex.code} {ex.read().decode()[:200]}")
            continue
        mk = (m.get("data") or {})
        mlist = mk if isinstance(mk, list) else (mk.get("markets") or mk.get(str(e.get("event_id"))) or [])
        print(f"\nMarkets for {e.get('name')}: {len(mlist) if isinstance(mlist, list) else type(mlist)}")
        print("Response 'data' structure (first market):")
        print(shape(mlist[0] if isinstance(mlist, list) and mlist else mk, 1, 6))
        types = sorted({x.get("type") for x in mlist if isinstance(x, dict)}) if isinstance(mlist, list) else []
        print(f"Market types: {types}")
        sel_path = None
        for mkt in (mlist if isinstance(mlist, list) else []):
            if isinstance(mkt, dict) and mkt.get("selections"):
                print(f"\nFull JSON of one market ('{mkt.get('type')}'), first 2500 chars:")
                print(json.dumps(mkt)[:2500])
                break
        break
    try:
        pl = call(base, "/v4/mm/get_price_ladder", token)
        print("\nPrice ladder structure:")
        print(shape(pl, 1, 2))
    except Exception as ex:
        print(f"price ladder: {ex}")


if __name__ == "__main__":
    main()
