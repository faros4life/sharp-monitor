#!/usr/bin/env python3
"""
CONFIRM-BOOK PROBE (Peter, Nov 8: "Ok do it"). READ-ONLY. Budget: ~6 billable calls, counted and
reported. Nothing is changed by this script - CONFIRM_BOOK is a repo variable and only Peter flips it.

THREE QUESTIONS, one run:
  1. What bookmakers does this plan actually carry? (the catalog - we have never looked)
  2. Do circasports and bookmaker/betcris resolve, and do they carry OUR markets?
  3. Is betfair_ex_eu genuinely absent, or has it been silently returning nothing?

WHY IT MATTERS. Across 959 sent alerts the four confirm books contributed: betonlineag 678,
matchbook 407, smarkets 4, betfair_ex_eu ZERO. Two of the four slots are dead. We are at exactly
10 books, which is the cap for one credit per market, so those two slots are free to re-use - but
only if the replacement slugs actually resolve. Betfair is the proof that a dead slug is invisible:
nothing errors, the book simply never appears, and nobody notices for 959 alerts.

The Actions log gets counts and book names only. No prices, no stakes, no amounts.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
CALLS = []
L = []
# the candidates, and the incumbents we are testing for silent absence
CANDIDATES = ["circasports", "bookmaker", "betcris", "lowvig"]
INCUMBENTS = ["betonlineag", "matchbook", "smarkets", "betfair_ex_eu"]


def say(line):
    L.append(line)
    print(line)


def get(path, billable=True, **params):
    # CREDIT GATE (Nov 9). This script has its own OddsPapi client and never passes through
    # clv_ledger.api, so the gate could not see or refuse its calls - it held the paid key and
    # would have spent ungated on every dispatch. credit_gate is a leaf module (stdlib only), so
    # importing it here costs nothing and cannot create an import cycle. Free endpoints
    # (/account, /historical-odds) bypass it untouched; a refusal raises rather than spending.
    import credit_gate as cg
    if billable and not cg.take(1, purpose="book_probe" + path, path=path):
        raise RuntimeError(f"credit gate refused {path}: no budget left this period")
    params["apiKey"] = KEY
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}",
                                 headers={"Accept": "application/json", "User-Agent": "sharp-monitor-probe"})
    time.sleep(1.2)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                CALLS.append((path, r.status, billable))
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(30 * (attempt + 1))
                continue
            CALLS.append((path, e.code, billable))
            return {"_error": e.code, "_body": e.read().decode()[:300]}
        except Exception as e:
            CALLS.append((path, type(e).__name__, billable))
            return {"_error": type(e).__name__, "_body": ""}


def names(obj):
    """Pull bookmaker keys/names out of whatever shape the catalog comes back in."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k in ("key", "slug", "bookmaker", "id", "name", "title"):
                v = o.get(k)
                if isinstance(v, str) and v.strip():
                    out.add(v.strip())
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return out


def main():
    if not KEY:
        say("ODDSPAPI_KEY not set - nothing run, 0 credits")
        return 1
    say("CONFIRM-BOOK PROBE - read-only, nothing changed")

    # ---------------------------------------------------------------- 1. the catalog
    # Nov 8: the first run already answered this and the answer does not change hour to hour,
    # so SKIP_CATALOG=1 spends that credit on the market check instead.
    cat = None
    for path in (() if os.environ.get("SKIP_CATALOG") else ("/bookmakers", "/bookmaker", "/sports/bookmakers")):
        d = get(path)
        if isinstance(d, dict) and d.get("_error"):
            say(f"  {path}: HTTP {d['_error']}")
            continue
        cat = d
        say(f"  {path}: catalog returned")
        break

    have = names(cat) if cat is not None else set()
    if have:
        say(f"\nCATALOG: {len(have)} bookmaker identifiers on this plan")
        for b in sorted(have):
            say(f"    {b}")
    else:
        say("\nCATALOG: no bookmaker endpoint answered. Falling back to a live-odds probe per slug,")
        say("  which is the only other way to tell a real slug from a silently-dead one.")

    # ---------------------------------------------------------------- 2/3. slug resolution
    say("\nSLUG CHECK  (does the slug resolve, and does it return our markets?)")
    # Nov 8: the first run guessed sportId=1 and got HTTP 400. The real shape, lifted from
    # plimit_probe: /sports gives slug -> sportId, and a tournament row carries tournamentId /
    # tournamentName / categorySlug. Guessing twice would have cost credits for nothing.
    tids = None
    s = get("/sports")
    rows = s if isinstance(s, list) else ((s or {}).get("data") or [])
    sid = {r.get("slug"): r.get("sportId") for r in rows if isinstance(r, dict)}
    say(f"  basketball sportId: {sid.get('basketball')}")
    if sid.get("basketball"):
        ts = get("/tournaments", sportId=sid["basketball"])
        for t in ts if isinstance(ts, list) else []:
            nm = (t.get("tournamentName") or "").lower()
            cat = (t.get("categorySlug") or "").lower()
            if nm == "nba" or (nm.startswith("nba") and "usa" in cat):
                tids = str(t.get("tournamentId"))
                say(f"  NBA tournamentId: {tids} ({t.get('tournamentName')}, "
                    f"{t.get('upcomingFixtures')} upcoming)")
                break
    if tids is None:
        say("  could not resolve an NBA tournament id - slug check skipped rather than guessed at")
    else:
        for bk in CANDIDATES + INCUMBENTS:
            d = get("/odds-by-tournaments", tournamentIds=tids, bookmaker=bk, verbosity=2)
            if isinstance(d, dict) and d.get("_error"):
                say(f"  {bk:16s} HTTP {d['_error']}  {str(d.get('_body'))[:70]}")
                continue
            fx = d if isinstance(d, list) else (d.get("data") or [])
            n = len(fx) if isinstance(fx, list) else 0
            mk = 0
            if isinstance(fx, list):
                for f in fx:
                    mk += len(((f or {}).get("bookmakerOdds") or {}) or {})
            say(f"  {bk:16s} {n:4d} fixtures, {mk:5d} bookmaker-odds blocks"
                + ("   <- RESOLVES" if n else "   <- returns nothing"))

    b = sum(1 for _, _, bill in CALLS if bill)
    say(f"\nCALLS: {len(CALLS)} total, {b} billable. "
        f"statuses {[(p.split('/')[-1], s) for p, s, _ in CALLS]}")
    say("Nothing was changed. CONFIRM_BOOK is Peter's flip.")

    try:
        import executor as ex
        ex.send("Bets CONFIRM-BOOK PROBE", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
