#!/usr/bin/env python3
"""
CAN THE FREE KEY SEE CIRCA? (Peter, Nov 8: "Let find out cost")

HARD CAPPED at 4 calls on the FREE key (250/month, never billable on the paid meter).

WHY. The paid key answers 403 "Restricted bookmaker(s)" for circasports, betcris, matchbook and
smarkets. OddsPapi's own pricing page says the FREE tier carries all 300+ books. hist_cache.py
already relies on exactly this asymmetry - it keeps ODDSPAPI_FREE_KEY because "a paid plan may
stop returning history for books it did not buy". So the restriction may be a property of the
paid plan, not of the account, and the answer may cost nothing.

Read-only. Changes nothing. CONFIRM_BOOK is Peter's flip.
"""
import json, os, sys, urllib.parse, urllib.request

BASE = "https://api.oddspapi.io/v4"
FREE = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()
CAP, n = 4, {"c": 0}
L = []

def say(t):
    L.append(t); print(t)

def get(path, **p):
    if n["c"] >= CAP:
        raise RuntimeError(f"cap {CAP} reached")
    n["c"] += 1
    p["apiKey"] = FREE
    q = urllib.parse.urlencode({k: v for k, v in p.items() if v is not None})
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"{BASE}{path}?{q}", headers={"Accept": "application/json"}), timeout=40) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:160]}

def main():
    if not FREE:
        say("ODDSPAPI_FREE_KEY not set - nothing run"); return 1
    say(f"FREE-KEY BOOK CHECK - hard cap {CAP} calls, free meter only\n")
    s = get("/sports")
    rows = s if isinstance(s, list) else ((s or {}).get("data") or [])
    sid = {r.get("slug"): r.get("sportId") for r in rows if isinstance(r, dict)}
    if not sid.get("basketball"):
        say(f"  /sports on the free key: {str(s)[:160]}"); return 1
    ts = get("/tournaments", sportId=sid["basketball"])
    tid = None
    for t in ts if isinstance(ts, list) else []:
        if (t.get("tournamentName") or "").lower() == "nba":
            tid = str(t.get("tournamentId")); break
    say(f"  NBA tournamentId: {tid}")
    if not tid:
        return 1
    for bk in ("circasports", "betcris"):
        d = get("/odds-by-tournaments", tournamentIds=tid, bookmaker=bk, verbosity=2)
        if isinstance(d, dict) and d.get("_error"):
            say(f"  {bk:14s} HTTP {d['_error']}  {d.get('_body','')[:90]}")
        else:
            fx = d if isinstance(d, list) else (d.get("data") or [])
            say(f"  {bk:14s} {len(fx) if isinstance(fx,list) else 0} fixtures   <-- AVAILABLE ON THE FREE KEY")
    say(f"\ncalls used: {n['c']} of {CAP}, free meter (250/month). Paid credits spent: 0.")
    try:
        import executor as ex; ex.send("Bets FREE-KEY book check", "\n".join(L))
    except Exception: pass
    return 0

sys.exit(main())
