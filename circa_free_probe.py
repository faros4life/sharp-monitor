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
    st = {"billable": {}}
    for lg in ("NBA", "NHL", "NCAAB"):
        try:
            cl.refresh_fixtures(st, now, lg, (now - timedelta(days=5)).astimezone(cl.ET),
                                (now + timedelta(days=1)).astimezone(cl.ET))
        except Exception as e:
            say(f"  fixtures {lg}: {type(e).__name__}")
    fx = list((st.get("fixtures") or {}).items())
    say(f"fixtures on hand: {len(fx)}")

    say("")
    say("1) /historical-odds on the FREE key")
    hits = 0
    for fid, f in fx[:6]:
        code, d = get("/historical-odds", FREE, fixtureId=fid, bookmakers="circasports")
        bk = books_in(d)
        say(f"   {str(f.get('lg','?')):6} {str(f.get('start'))[:16]}  HTTP {code}  books back: {bk or '-'}"
            + (f"   {str(d.get('_body'))[:90]}" if code != 200 else ""))
        if code == 200 and "circasports" in bk:
            hits += 1
    say(f"   -> circasports returned data on {hits} of {min(6, len(fx))} fixtures")

    say("")
    say("2) /odds-by-tournaments live on the FREE key (does the slug resolve at all)")
    code, d = get("/sports", FREE)
    say(f"   /sports HTTP {code}")
    code, d = get("/odds-by-tournaments", FREE, sportId=11, bookmakers="circasports")
    say(f"   odds-by-tournaments circasports HTTP {code} {str(d.get('_body'))[:120] if code != 200 else 'OK'}")

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
