#!/usr/bin/env python3
"""
PLIMIT read-path PROBE v2 (Nov 2, 2026; Peter yes; Muse PLIMIT registration: confirm the read before any logger).
OddsPapi v4 free plan (250 billable requests / month, resets on the 1st; /v4/historical-odds is free). Read-only.
About 6 billable calls: sports, tournaments x3, odds-by-tournaments (pinnacle; circasports). Plus free historical
calls for 2 fixtures to see whether the limit is in the history. Private email; the Actions log prints counts only.
"""
import json
import os
import time
import urllib.parse
import urllib.request

import executor as ex

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
CALLS = []


def get(path, **params):
    params["apiKey"] = KEY
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"Accept": "application/json", "User-Agent": "sharp-monitor-probe"})
    time.sleep(8 if path == "/historical-odds" else 1.1)   # history endpoint throttles harder (429 at ~1 s)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            CALLS.append((path, r.status))
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        CALLS.append((path, e.code))
        return {"_error": e.code, "_body": e.read().decode()[:300]}


def walk(book):
    """(outcomes, with_limit, samples) over a bookmakerOdds entry."""
    n = k = 0
    s = []
    for mid, m in (book.get("markets") or {}).items():
        for oid, o in (m.get("outcomes") or {}).items():
            for pid, pl in (o.get("players") or {}).items():
                n += 1
                if pl.get("limit") is not None:
                    k += 1
                    if len(s) < 4:
                        s.append(f"market {mid} {pl.get('bookmakerOutcomeId')}: price {pl.get('price')} limit {pl.get('limit')}")
    return n, k, s


def hr_check(fid):
    """Free-only: Hard Rock + Pinnacle history for one fixture (historical-odds is unmetered)."""
    L = [f"HARD ROCK HISTORY CHECK (free calls only), fixture {fid}"]
    h = get("/historical-odds", fixtureId=fid, bookmakers="hardrockbet,pinnacle")
    for bk in ("hardrockbet", "pinnacle"):
        b = ((h.get("bookmakers") or {}).get(bk) or {}) if isinstance(h, dict) else {}
        mk = b.get("markets") or {}
        ticks = sum(len(v) for m in mk.values() for o in (m.get("outcomes") or {}).values() for v in (o.get("players") or {}).values() if isinstance(v, list))
        first = None
        for m in mk.values():
            for o in (m.get("outcomes") or {}).values():
                for v in (o.get("players") or {}).values():
                    if isinstance(v, list) and v:
                        first = v[0]
                        break
                if first: break
            if first: break
        L.append(f"  {bk}: markets {len(mk)}, ticks {ticks}, sample tick {json.dumps(first)[:300] if first else '-'}")
    if isinstance(h, dict) and h.get("_error"):
        L.append(f"  HTTP {h['_error']} {h['_body']}")
    return L


def books_check(fid, books):
    """Free-only: which books carry a limit (or exchange depth) in history for one fixture. 3 books per call."""
    L = [f"LIMIT COVERAGE BY BOOK (free history calls only), fixture {fid}"]
    for i in range(0, len(books), 3):
        grp = books[i:i + 3]
        h = get("/historical-odds", fixtureId=fid, bookmakers=",".join(grp))
        if isinstance(h, dict) and h.get("_error"):
            L.append(f"  {grp}: HTTP {h['_error']} {h['_body'][:120]}")
            continue
        for bk in grp:
            mk = ((h.get("bookmakers") or {}).get(bk) or {}).get("markets") or {}
            n = lim = ex_ = 0
            samp = None
            for m in mk.values():
                for o in (m.get("outcomes") or {}).values():
                    for v in (o.get("players") or {}).values():
                        for t in (v if isinstance(v, list) else []):
                            n += 1
                            if t.get("limit") is not None:
                                lim += 1
                                samp = samp or t
                            if t.get("exchangeMeta"):
                                ex_ += 1
                                samp = samp or t
            L.append(f"  {bk}: markets {len(mk)}, ticks {n}, with limit {lim}, with exchange depth {ex_}"
                     + (f" | sample {json.dumps(samp)[:220]}" if samp else ""))
    return L


def main():
    if os.environ.get("HR_FIXTURE") and os.environ.get("HR_BOOKS"):
        L = books_check(os.environ["HR_FIXTURE"], [b.strip() for b in os.environ["HR_BOOKS"].split(",") if b.strip()])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS) + " (historical-odds is free)"]
        ex.send("Bets LIMIT COVERAGE BY BOOK (OddsPapi)", "\n".join(L))
        print(f"coverage check emailed: {len(CALLS)} calls")
        return
    if os.environ.get("HR_FIXTURE"):
        L = hr_check(os.environ["HR_FIXTURE"])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS) + " (historical-odds is free)"]
        ex.send("Bets HR HISTORY CHECK (OddsPapi)", "\n".join(L))
        print(f"HR check emailed: {len(CALLS)} calls")
        return
    L = ["PLIMIT PROBE v2 (OddsPapi v4, free plan)", ""]
    if not KEY:
        ex.send("Bets PLIMIT PROBE", "ODDSPAPI_KEY not set - nothing read.")
        return
    acct = get("/account")
    L.append("account: " + json.dumps({k: acct.get(k) for k in ("plan", "requestsUsed", "requestsLimit", "used", "limit", "_error")
                                       if isinstance(acct, dict)})[:300])
    sports = get("/sports")
    if isinstance(sports, dict) and sports.get("_error"):
        L.append(f"/sports HTTP {sports['_error']}: {sports['_body']}")
        ex.send("Bets PLIMIT PROBE v2 (OddsPapi)", "\n".join(L))
        print("probe: sports failed")
        return
    sid = {s.get("slug"): s.get("sportId") for s in sports}
    L.append("sport ids: " + json.dumps({k: sid.get(k) for k in ("basketball", "american-football", "ice-hockey")}))
    tids = {}
    for slug, wants in (("basketball", {"NBA": "nba"}), ("american-football", {"NFL": "nfl", "NCAAF": "ncaa"}),
                        ("ice-hockey", {"NHL": "nhl"})):
        if not sid.get(slug):
            continue
        ts = get("/tournaments", sportId=sid[slug])
        for t in ts if isinstance(ts, list) else []:
            nm, cat = (t.get("tournamentName") or "").lower(), (t.get("categorySlug") or "").lower()
            for lg, w in wants.items():
                if lg not in tids and (nm == w or (nm.startswith(w) and "usa" in cat) or (lg == "NCAAF" and "ncaa" in nm and "div" not in nm and "usa" in cat)):
                    tids[lg] = (t.get("tournamentId"), t.get("tournamentName"), t.get("upcomingFixtures"), t.get("futureFixtures"))
    L.append("tournaments: " + json.dumps(tids))
    ids = ",".join(str(tids[l][0]) for l in ("NBA", "NFL", "NHL") if l in tids)
    first = {}
    for bk in ("pinnacle", "circasports"):
        d = get("/odds-by-tournaments", tournamentIds=ids, bookmaker=bk, verbosity=3)
        if isinstance(d, dict) and d.get("_error"):
            L.append(f"{bk}: HTTP {d['_error']} {d['_body']}")
            continue
        fx = d if isinstance(d, list) else []
        L.append(f"{bk}: {len(fx)} fixtures (NBA/NFL/NHL)")
        tot_n = tot_k = 0
        by_t = {}
        for f in fx:
            b = (f.get("bookmakerOdds") or {}).get(bk) or {}
            n, k, s = walk(b)
            tot_n += n
            tot_k += k
            by_t.setdefault(f.get("tournamentId"), [0, 0])
            by_t[f.get("tournamentId")][0] += n
            by_t[f.get("tournamentId")][1] += k
            if s and bk not in first:
                first[bk] = f.get("fixtureId")
                L.append(f"  sample fixture {f.get('fixtureId')} start {f.get('startTime')}:")
                L += ["    " + x for x in s]
        L.append(f"  outcomes {tot_n}, with a limit {tot_k}; by tournament (outcomes, with limit): {json.dumps(by_t)}")
    for bk, fid in first.items():
        h = get("/historical-odds", fixtureId=fid, bookmakers=bk)
        txt = json.dumps(h)
        L.append(f"historical ({bk}, free): {len(txt)} chars; contains 'limit': {'limit' in txt}; head: {txt[:400]}")
    L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS),
          "Billable: every call except /account and /historical-odds."]
    ex.send("Bets PLIMIT PROBE v2 (OddsPapi)", "\n".join(L))
    print(f"PLIMIT probe v2 emailed: {len(CALLS)} calls")   # counts only


if __name__ == "__main__":
    main()
