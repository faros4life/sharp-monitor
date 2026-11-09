#!/usr/bin/env python3
"""
WHICH BOOKS DOES THE ODDS API CARRY FOR US? (Peter, Nov 8: "Do it")

ONE REQUEST. HARD CAPPED. This exists because I overspent the last probe - 10 OddsPapi calls
against a ~3 approval - and because that probe asked the WRONG PROVIDER. CONFIRM_BOOK is sent to
api.the-odds-api.com (sharp_monitor.py:28), not to OddsPapi, so a 321-book OddsPapi catalog said
nothing about which confirm books are available.

THE QUESTION: of the sharp candidates - Circa, Bookmaker/BetCRIS, Pinnacle variants - which does
this plan actually return for an NBA market, and what are the real slugs?

COST. The Odds API bills one credit per region per market. This asks for ONE market (totals) over
the two US regions where a sharp US or offshore book would sit, so the ceiling is 2 credits on a
DIFFERENT meter from OddsPapi. x-requests-remaining is printed before and after, so the exact
spend is visible rather than asserted. CALL_CAP makes a second request impossible.

Read-only. Changes nothing. CONFIRM_BOOK is Peter's flip.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.the-odds-api.com/v4"
KEY = (os.environ.get("ODDS_API_KEY") or os.environ.get("API_KEY") or "").strip()
CALL_CAP = 1
_calls = {"n": 0}
L = []

# what we would like to find, by the names a feed is likely to use
SHARP_WANTED = ("circa", "bookmaker", "betcris", "pinnacle", "ps3838", "lowvig", "betonline",
                "matchbook", "smarkets", "betfair")


def say(t):
    L.append(t)
    print(t)


def get(path, **params):
    if _calls["n"] >= CALL_CAP:
        raise RuntimeError(f"call cap {CALL_CAP} reached - refusing to spend another request")
    _calls["n"] += 1
    params["apiKey"] = KEY
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=40) as r:
        return json.loads(r.read().decode()), r.headers.get("x-requests-remaining"), r.headers.get("x-requests-used")


def main():
    if not KEY:
        say("no Odds API key in the environment - nothing run, 0 requests")
        return 1
    say("THE ODDS API - which bookmakers come back for an NBA market")
    say(f"ONE request, hard-capped at {CALL_CAP}. Read-only, nothing changed.")
    try:
        data, rem, used = get("/sports/basketball_nba/odds", regions="us,us2",
                              markets="totals", oddsFormat="american")
    except Exception as e:
        say(f"request failed ({type(e).__name__}: {str(e)[:120]})")
        return 1

    books = {}
    for ev in data if isinstance(data, list) else []:
        for b in (ev.get("bookmakers") or []):
            k = b.get("key")
            if k:
                books[k] = books.get(k, 0) + 1
    say(f"\nevents returned: {len(data) if isinstance(data, list) else 0}; "
        f"distinct bookmakers: {len(books)}")
    say(f"requests used {used}, remaining {rem}  (this is the ODDS API meter, not OddsPapi)")

    say("\nEVERY bookmaker key returned, by how many events carried it:")
    for k, n in sorted(books.items(), key=lambda x: (-x[1], x[0])):
        mark = "  <-- sharp candidate" if any(w in k.lower() for w in SHARP_WANTED) else ""
        say(f"  {k:28s} {n:4d}{mark}")

    say("\nTHE ANSWER, candidate by candidate:")
    for w in ("circa", "bookmaker", "betcris", "ps3838", "lowvig",
              "betonlineag", "matchbook", "smarkets", "betfair"):
        hits = [k for k in books if w in k.lower()]
        say(f"  {w:14s} {'FOUND: ' + ', '.join(hits) if hits else 'not returned on this plan/region'}")

    say("\nNothing was changed. CONFIRM_BOOK is Peter's flip.")
    try:
        import executor as ex
        ex.send("Bets ODDS API book availability", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
