#!/usr/bin/env python3
"""
HISTORY KEY PROBE (Nov 3, 2026; Peter 21:49 "is there something the paid key can download?"). Read-only, 0 credits:
/historical-odds is free. For a few finished games from the saved fixture lists, asks each bookmaker separately with the
PAID key and with the FREE key and prints, per book and key, the HTTP result and whether markets came back. Counts and
status codes only in the log (public repo); no prices, no keys.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import tracker_build as tb

BOOKS = ["pinnacle", "hardrockbet", "novig.us", "prophetx", "kalshi", "polymarket.us"]
PAID = (os.environ.get("ODDSPAPI_KEY") or "").strip()
FREE = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()


def main():
    now = datetime.now(timezone.utc)
    fx = {}
    for path in ("exlag/state.enc", "slowhr/state.enc"):
        try:
            fx.update((tb.dec(json.load(open(path))).get("fixtures") or {}))
        except Exception:
            pass
    games = sorted(((cl.tp(f.get("start")), fid, f.get("lg")) for fid, f in fx.items()
                    if f.get("lg") in ("NBA", "NFL", "NCAAF", "NHL") and cl.tp(f.get("start"))
                    and now - timedelta(days=4) <= cl.tp(f.get("start")) <= now - timedelta(hours=6)), reverse=True)
    pick, seen = [], set()
    for s, fid, lg in games:
        if lg not in seen:
            pick.append((s, fid, lg))
            seen.add(lg)
    pick = pick[:2]   # two games keep the probe short (it shares the free key with the running fill)
    print(f"history probe: {len(fx)} fixtures in saved lists, testing {len(pick)} games ({', '.join(lg for _, _, lg in pick)})")
    tally = {}
    for s, fid, lg in pick:
        for b in BOOKS:
            for name, key in (("paid", PAID), ("free", FREE)):
                if not key:
                    continue
                h = cl.api("/historical-odds", False, apikey=key, fixtureId=fid, bookmakers=b)
                if isinstance(h, dict) and h.get("_error"):
                    res = f"error {h['_error']}"
                else:
                    bm = ((h or {}).get("bookmakers") or {}).get(b) or {}
                    res = "markets" if bm.get("markets") else "empty"
                tally.setdefault((b, name), []).append(res)
    for b in BOOKS:
        print(f"history probe: {b:14s} paid {', '.join(tally.get((b, 'paid'), ['-']))} | free {', '.join(tally.get((b, 'free'), ['-']))}")
    print(f"history probe: calls {len(cl.CALLS)}, billable {cl.STATS['billable']}")   # counts only


if __name__ == "__main__":
    main()
