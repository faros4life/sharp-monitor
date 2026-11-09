#!/usr/bin/env python3
"""CIRCA ON THE FREE KEY - read-only probe (Peter, Nov 9: "CIRCA IS ON THE FREE ODDSPAPI").

The Nov 9 book probe tested circasports on the PAID key only and got 403 "Restricted bookmaker(s)".
That says nothing about the free account, which is where this repo already routes history. If Circa
answers on the free key, it becomes a real second closing anchor instead of the 78 cached rows the
root-cause audit had to make do with.

Tests, in order, free key only:
  1. /historical-odds for circasports on fixtures we already hold - the endpoint the CLV path uses.
  2. /odds-by-tournaments live, to see whether the slug resolves at all on this account.
Nothing is written, no rule changes, no bets. Counts and HTTP statuses only.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex

BASE = "https://api.oddspapi.io/v4"
FREE = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()
PAID = (os.environ.get("ODDSPAPI_KEY") or "").strip()
L = []


def say(s):
    L.append(s)
    print(s)


def get(path, key, **params):
    params["apiKey"] = key
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}",
                                 headers={"Accept": "application/json", "User-Agent": "sharp-monitor-probe"})
    time.sleep(1.2)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"_body": e.read().decode()[:200]}
    except Exception as e:
        return type(e).__name__, {}


def books_in(d):
    b = ((d or {}).get("bookmakers") or {})
    return sorted(b.keys()) if isinstance(b, dict) else []


def main():
    say("CIRCA ON THE FREE KEY - read-only probe")
    say(f"free key present: {bool(FREE)} | paid key present: {bool(PAID)}")
    if not FREE:
        say("No free key in this job's env - nothing to test.")
        ex.send("Bets CIRCA FREE-KEY PROBE", "\n".join(L))
        return

    now = datetime.now(timezone.utc)

    say("")
    say("1) does the slug resolve LIVE on the free key (a real tournamentId, not a bare sportId)")
    code, d = get("/sports", FREE)
    say(f"   /sports HTTP {code}")
    tids = []
    for sid in (11, 17):   # basketball, ice hockey
        code, d = get("/tournaments", FREE, sportId=sid)
        got = []
        def walk(o):
            if isinstance(o, dict):
                if o.get("id") and (o.get("name") or o.get("title")):
                    got.append((o["id"], str(o.get("name") or o.get("title"))[:26]))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(d)
        say(f"   /tournaments sportId={sid} HTTP {code}, {len(got)} found: {[g[1] for g in got[:4]]}")
        tids += [g[0] for g in got[:2]]
    for tid in tids[:3]:
        code, d = get("/odds-by-tournaments", FREE, tournamentIds=tid, bookmakers="circasports")
        say(f"   odds-by-tournaments tid={tid} circasports  HTTP {code}  books: {books_in(d) or '-'}"
            + (f"  {str(d.get('_body'))[:110]}" if code != 200 else ""))
        code, d = get("/odds-by-tournaments", FREE, tournamentIds=tid, bookmakers="pinnacle")
        say(f"   ... same tid with pinnacle (control)   HTTP {code}  books: {books_in(d) or '-'}")

    say("")
    say("2) /historical-odds on the free key, on fixtures already in the shared cache")
    try:
        import hist_cache as hc
        import glob
        paths = sorted(glob.glob(os.path.join(hc.DIR if hasattr(hc, "DIR") else "hcache", "**", "*pinnacle*"), recursive=True))[:5]
        say(f"   cached pinnacle files found: {len(paths)}")
        fids = []
        for pth in paths:
            base = os.path.basename(os.path.dirname(pth)) or os.path.basename(pth)
            fids.append(base.split(".")[0])
        for fid in fids[:4]:
            code, d = get("/historical-odds", FREE, fixtureId=fid, bookmakers="circasports")
            say(f"   fixture {fid}  HTTP {code}  books: {books_in(d) or '-'}"
                + (f"  {str(d.get('_body'))[:110]}" if code != 200 else ""))
    except Exception as e:
        say(f"   cache walk failed: {type(e).__name__}: {str(e)[:70]}")

    say("")
    say("3) same two calls on the PAID key, for the contrast the Nov 9 probe already showed")
    if PAID and fx:
        code, d = get("/historical-odds", PAID, fixtureId=fx[0][0], bookmakers="circasports")
        say(f"   /historical-odds HTTP {code} {str(d.get('_body'))[:120] if code != 200 else 'OK'}")
        code, d = get("/odds-by-tournaments", PAID, sportId=11, bookmakers="circasports")
        say(f"   odds-by-tournaments HTTP {code} {str(d.get('_body'))[:120] if code != 200 else 'OK'}")

    say("")
    say("Read-only. Nothing written, no rule changed.")
    ex.send("Bets CIRCA FREE-KEY PROBE", "\n".join(L))


if __name__ == "__main__":
    main()
