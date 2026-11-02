#!/usr/bin/env python3
"""
PLIMIT read-path PROBE (Nov 2, 2026; Peter yes; Muse PLIMIT registration says: confirm the read before any logger).
One-off, read-only, about 8 OddsPapi calls on the free plan (250 total). Reports whether Pinnacle (and Circa) carry a
per-market limit on NFL / NCAAF / NBA / NHL main markets. Private email; the Actions log prints counts only.
"""
import json
import os
import urllib.parse
import urllib.request

import executor as ex

BASE = "https://v5.oddspapi.io/en"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
CALLS = []


def get(path, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"X-API-Key": KEY, "Accept": "application/json",
                                                              "User-Agent": "sharp-monitor-probe"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            CALLS.append((path, r.status, r.headers.get("X-RateLimit-Remaining")))
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        CALLS.append((path, e.code, None))
        return {"_error": e.code, "_body": e.read().decode()[:300]}


def items(d):
    if isinstance(d, list):
        return d
    for k in ("data", "items", "results", "sports", "tournaments", "fixtures"):
        if isinstance(d, dict) and isinstance(d.get(k), list):
            return d[k]
    return []


def main():
    L = ["PLIMIT PROBE (OddsPapi free plan): does Pinnacle / Circa carry a per-market limit on our leagues?", ""]
    if not KEY:
        ex.send("Bets PLIMIT PROBE", "ODDSPAPI_KEY not set - nothing read.")
        return
    sports = items(get("/sports"))
    sid = {}
    for s in sports:
        nm = str(s.get("sportName") or s.get("name") or s.get("slug") or "").lower()
        for want in ("basketball", "american football", "ice hockey"):
            if nm == want:
                sid[want] = s.get("sportId") or s.get("id")
    L.append(f"sports found: {sid} (of {len(sports)})")
    want_t = {"NBA": ("basketball", ["nba"]), "NFL": ("american football", ["nfl"]),
              "NCAAF": ("american football", ["ncaa", "college"]), "NHL": ("ice hockey", ["nhl"])}
    tids = {}
    for sp in set(v[0] for v in want_t.values()):
        if sp not in sid:
            continue
        ts = items(get("/tournaments", sportId=sid[sp]))
        for lg, (s2, words) in want_t.items():
            if s2 != sp or lg in tids:
                continue
            for t in ts:
                nm = str(t.get("tournamentName") or t.get("name") or "").lower()
                cat = str(t.get("categoryName") or t.get("category") or "").lower()
                if any(w == nm or nm.startswith(w) or (w in nm and "usa" in cat) for w in words):
                    tids[lg] = (t.get("tournamentId") or t.get("id"), t.get("tournamentName") or t.get("name"))
                    break
    L.append(f"tournaments: {tids}")
    for lg in ("NBA", "NFL"):
        if lg not in tids:
            L.append(f"{lg}: tournament not found")
            continue
        d = get("/fixtures/odds/main", tournamentId=tids[lg][0], bookmakers="pinnacle,circasports")
        fx = items(d) or (d if isinstance(d, list) else [])
        if isinstance(d, dict) and d.get("_error"):
            L.append(f"{lg}: HTTP {d['_error']} {d['_body']}")
            continue
        L.append(f"{lg}: {len(fx)} fixtures returned")
        shown = 0
        for f in fx[:3]:
            L.append(f"  fixture keys: {sorted(f.keys())[:15]}")
            bo = f.get("bookmakerOdds") or {}
            for bk in ("pinnacle", "circasports"):
                b = bo.get(bk)
                if not b:
                    L.append(f"   {bk}: not present")
                    continue
                n_lim = n_out = 0
                samples = []
                for mid, m in (b.get("markets") or {}).items():
                    for oid, o in (m.get("outcomes") or {}).items():
                        for pid, pl in (o.get("players") or {}).items():
                            n_out += 1
                            if pl.get("limit") is not None:
                                n_lim += 1
                                if len(samples) < 6:
                                    samples.append(f"market {mid} outcome {oid}: price {pl.get('price')} limit {pl.get('limit')}")
                L.append(f"   {bk}: outcomes {n_out}, with limit {n_lim}")
                L += ["     " + s for s in samples]
            shown += 1
        if not fx:
            L.append("  raw (first 600 chars): " + json.dumps(d)[:600])
    L += ["", "Calls used this probe: " + "; ".join(f"{p} {c} (remaining {r})" for p, c, r in CALLS)]
    ex.send("Bets PLIMIT PROBE (OddsPapi)", "\n".join(L))
    print(f"PLIMIT probe emailed: {len(CALLS)} calls")   # counts only


if __name__ == "__main__":
    main()
