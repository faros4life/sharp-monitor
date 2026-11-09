#!/usr/bin/env python3
"""WHICH SHARP BOOKS DOES THE FREE KEY CARRY, AND WHAT IS THE REAL BUDGET?
(Peter, Nov 9: "Are you going to use circa and other sharp books free api")

TWO QUESTIONS, and the second one decides whether the first matters.

1. WHICH BOOKS. The paid plan answers 403 "Restricted bookmaker(s)" for circasports, betcris,
   matchbook and smarkets. The free key returned circasports fine (5 fixtures) on 8 Nov, so the
   restriction is a property of the PAID PLAN, not the account. This asks the same question of
   every sharp book worth having, not just the two that fitted in the last probe's cap.

2. WHAT IS THE BUDGET. freekey_books.py says the free tier is "250/month" - that number is MINE,
   written into a docstring, never verified against the provider. A feed's cadence cannot be
   planned on a figure I made up, so this prints every rate-limit and quota header the API
   returns and reports the limit as MEASURED or as UNKNOWN. It does not restate the 250.

   Why it decides everything: the live scanner runs every 5 minutes, about 8,640 runs a month. If
   the free budget is in the hundreds, no free-key book can ever be a live confirmation book -
   the arithmetic is off by more than an order of magnitude. It could still serve a once-or-
   twice-daily CLOSING-LINE capture, which is a different and much cheaper job.

Hard capped. FREE meter only - zero paid credits, and the paid key is never sent.
Read-only: changes nothing, sets no variable, writes no file.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.oddspapi.io/v4"
FREE = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()
CAP = int(os.environ.get("FK_CAP", "") or "12")
n = {"c": 0}
L = []
HDRS = {}

# The sharp books worth having, by the names a feed is likely to use. betonlineag and matchbook are
# incumbents, included so the free key's answer can be compared against what we already measure.
SHARPS = ["circasports", "betcris", "bookmaker", "pinnacle", "ps3838", "lowvig",
          "matchbook", "smarkets", "betonlineag"]


def say(t=""):
    L.append(t)
    print(t)


def get(path, **p):
    if n["c"] >= CAP:
        raise RuntimeError(f"call cap {CAP} reached - refusing another call")
    n["c"] += 1
    p["apiKey"] = FREE
    q = urllib.parse.urlencode({k: v for k, v in p.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}",
                                 headers={"Accept": "application/json"})
    time.sleep(1.5)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            if not HDRS:
                HDRS.update({k: v for k, v in r.headers.items()})
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if not HDRS:
            HDRS.update({k: v for k, v in (e.headers or {}).items()})
        return {"_error": e.code, "_body": e.read().decode()[:160]}
    except Exception as e:
        return {"_error": type(e).__name__, "_body": ""}


def main():
    if not FREE:
        say("ODDSPAPI_FREE_KEY not set - nothing run, 0 calls")
        return 1
    say("FREE-KEY SHARP BOOK CHECK - free meter only, zero paid credits")
    say(f"hard cap {CAP} calls. Read-only; the paid key is never sent.")
    say()

    s = get("/sports")
    rows = s if isinstance(s, list) else ((s or {}).get("data") or [])
    sid = {r.get("slug"): r.get("sportId") for r in rows if isinstance(r, dict)}

    # ------------------------------------------------------------- 2. the budget, MEASURED
    say("=" * 70)
    say("THE BUDGET - measured from the response headers, not from a docstring")
    say("=" * 70)
    quota = [(k, v) for k, v in HDRS.items()
             if any(w in k.lower() for w in ("limit", "remain", "quota", "ratelimit", "retry", "usage"))]
    if quota:
        for k, v in quota:
            say(f"  {k}: {v}")
        say()
        say("  ^ MEASURED. Plan the cadence from these numbers.")
    else:
        say("  The API returns NO rate-limit or quota header on this endpoint.")
        say("  So the free budget is UNKNOWN from here, and the '250/month' in freekey_books.py")
        say("  is an unverified figure I wrote - it must not be used to plan a cadence. The")
        say("  number has to come from the provider's own account page before anything is wired.")
    say()
    say(f"  all headers returned: {sorted(HDRS.keys())}")

    if not sid.get("basketball"):
        say(f"\n  /sports did not resolve on the free key: {str(s)[:140]}")
        say(f"\ncalls used {n['c']} of {CAP}, free meter. Paid credits: 0.")
        try:
            import executor as ex
            ex.send("Bets FREE-KEY sharp books", "\n".join(L))
        except Exception:
            pass
        return 1

    ts = get("/tournaments", sportId=sid["basketball"])
    tid = None
    for t in ts if isinstance(ts, list) else []:
        if (t.get("tournamentName") or "").lower() == "nba":
            tid = str(t.get("tournamentId"))
            break
    say(f"\n  NBA tournamentId: {tid}")
    if not tid:
        say("  could not resolve an NBA tournament - book check skipped rather than guessed at")
        return 1

    # ------------------------------------------------------------- 1. which books
    say()
    say("=" * 70)
    say("WHICH SHARP BOOKS THE FREE KEY ACTUALLY RETURNS")
    say("=" * 70)
    found, denied, other = [], [], []
    for bk in SHARPS:
        if n["c"] >= CAP - 1:
            say(f"  {bk:14s} not tested - call cap reached (raise FK_CAP to continue)")
            continue
        d = get("/odds-by-tournaments", tournamentIds=tid, bookmaker=bk, verbosity=2)
        if isinstance(d, dict) and d.get("_error"):
            code = d["_error"]
            body = str(d.get("_body") or "")[:70]
            say(f"  {bk:14s} HTTP {code}  {body}")
            (denied if code in (403, 400) else other).append(f"{bk} ({code})")
            continue
        fx = d if isinstance(d, list) else (d.get("data") or [])
        cnt = len(fx) if isinstance(fx, list) else 0
        mk = sum(len(((f or {}).get("bookmakerOdds") or {}) or {}) for f in fx) if isinstance(fx, list) else 0
        say(f"  {bk:14s} {cnt:4d} fixtures, {mk:5d} odds blocks"
            + ("   <-- AVAILABLE FREE" if cnt else "   <-- resolves but returns nothing"))
        (found if cnt else other).append(bk)

    say()
    say("=" * 70)
    say("WHAT THIS DOES AND DOES NOT MAKE POSSIBLE")
    say("=" * 70)
    say(f"  available on the free key : {found or 'none'}")
    say(f"  refused (403/400)         : {denied or 'none'}")
    say(f"  resolved but empty / other: {other or 'none'}")
    say()
    say("  A free-key book CANNOT be a CONFIRM_BOOK entry whatever the budget: CONFIRM_BOOK is")
    say("  sent to api.the-odds-api.com (sharp_monitor.py line 28) and this is OddsPapi. They are")
    say("  different providers. Circa is absent from The Odds API in us/us2 (probe 42561779308),")
    say("  so no CONFIRM_BOOK value can ever include it.")
    say()
    say("  What a free-key sharp book CAN do, if the measured budget allows it:")
    say("    * a once- or twice-daily CLOSING-LINE capture, which is what CLV grading needs")
    say("    * a pre-game sanity check against Pinnacle on a handful of games")
    say("  What it cannot do on a few-hundred-calls budget: feed the 5-minute live scanner, which")
    say("  is about 8,640 runs a month.")
    say()
    say(f"calls used {n['c']} of {CAP}, FREE meter. Paid credits spent: 0.")
    say("Nothing was changed. CONFIRM_BOOK is Peter's flip.")

    try:
        import executor as ex
        ex.send("Bets FREE-KEY sharp books", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
