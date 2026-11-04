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
    pick = pick[:0]   # Nov 3 22:25: per-league check already answered; this pass only tests the newest games   # two games keep the probe short (it shares the free key with the running fill)
    print(f"history probe: {len(fx)} fixtures in saved lists, testing {len(pick)} games ({', '.join(lg for _, _, lg in pick)})")
    bk = cl.api("/bookmakers", False, apikey=PAID)   # Nov 4: which Pinnacle slugs does the paid plan list?
    try:
        slugs = [b.get("slug") or b.get("bookmakerSlug") or str(b) for b in (bk if isinstance(bk, list) else bk.get("data") or bk.get("bookmakers") or [])]
        print("history probe: paid-key bookmaker slugs with 'pinn': " + ", ".join(x for x in slugs if "pinn" in str(x).lower())[:300])
    except Exception as x:
        print(f"history probe: bookmakers list unreadable: {str(bk)[:160]}")
    tally = {}
    for s, fid, lg in pick:
        for b in BOOKS:
            for name, key in ((("free", FREE),) if os.environ.get("PROBE_FREE_ONLY") else (("paid", PAID), ("free", FREE))):
                if not key:
                    continue
                h = cl.api("/historical-odds", False, apikey=key, fixtureId=fid, bookmakers=b)
                if isinstance(h, dict) and h.get("_error"):
                    res = f"error {h['_error']}"
                else:
                    bm = ((h or {}).get("bookmakers") or {}).get(b) or {}
                    res = "markets" if bm.get("markets") else "empty"
                tally.setdefault((b, name), []).append(res)
    # Nov 3 22:25: the fill gets 404 on most games. Test the fill's exact grouped calls (3 books per call) on the NEWEST
    # finished games, plus each book alone, free key only, and print the 404 text (counts / codes only).
    newest = [g for g in games if g[0] <= now - timedelta(hours=4)][:4]
    for s, fid, lg in newest:
        for grp in (["pinnacle", "novig.us", "prophetx"], ["kalshi", "polymarket.us", "hardrockbet"]):
            h = cl.api("/historical-odds", False, apikey=FREE, fixtureId=fid, bookmakers=",".join(grp))
            if isinstance(h, dict) and h.get("_error"):
                body = str(h.get("_body", ""))[:120].replace(FREE, "***") if FREE else ""
                print(f"history probe: {lg} game {s:%m-%d %H:%M}Z group {'+'.join(grp)}: error {h['_error']} {body}")
            else:
                got = [b for b in grp if (((h or {}).get("bookmakers") or {}).get(b) or {}).get("markets")]
                print(f"history probe: {lg} game {s:%m-%d %H:%M}Z group {'+'.join(grp)}: ok, markets for {len(got)} of 3")
        # Nov 4 9:37 (Wenzel, OddsPapi): on v4 the paid plan's Pinnacle slug is "pinnacle+30s", not "pinnacle"
        for grp in (["pinnacle+30"], ["pinnacle+30", "hardrockbet"]):   # the slug list says "pinnacle+30" (no s)
            h = cl.api("/historical-odds", False, apikey=PAID, fixtureId=fid, bookmakers=",".join(grp))
            if isinstance(h, dict) and h.get("_error"):
                body = str(h.get("_body", ""))[:160].replace(PAID, "***") if PAID else ""
                print(f"history probe: {lg} game {s:%m-%d %H:%M}Z PAID {'+'.join(grp)}: error {h['_error']} {body}")
            else:
                bms = (h or {}).get("bookmakers") or {}
                print(f"history probe: {lg} game {s:%m-%d %H:%M}Z PAID {','.join(grp)}: ok, books returned "
                      f"{sorted(bms)}, with markets {[b for b in bms if (bms[b] or {}).get('markets')]}")
        for b in BOOKS:
            h = cl.api("/historical-odds", False, apikey=FREE, fixtureId=fid, bookmakers=b)
            r = f"error {h['_error']}" if isinstance(h, dict) and h.get("_error") else (
                "markets" if (((h or {}).get("bookmakers") or {}).get(b) or {}).get("markets") else "empty")
            print(f"history probe: {lg} game {s:%m-%d %H:%M}Z {b}: {r}")
    for b in BOOKS:
        print(f"history probe: {b:14s} paid {', '.join(tally.get((b, 'paid'), ['-']))} | free {', '.join(tally.get((b, 'free'), ['-']))}")
    print(f"history probe: calls {len(cl.CALLS)}, billable {cl.STATS['billable']}")   # counts only


if __name__ == "__main__":
    main()
