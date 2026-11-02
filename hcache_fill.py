#!/usr/bin/env python3
"""
HISTORY CACHE FILL (Nov 2, 2026; Peter 15:24: "we should still download the data this way we can run our models").
Downloads every FINISHED NBA / NFL / NCAAF / NHL game since FILL_FROM (Oct 12 = OddsPapi's history depth) into the shared
history cache (hist_cache.py, private Actions cache), for Pinnacle, Novig, ProphetX, Kalshi, Polymarket US and Hard Rock,
so every model and test can run from disk. Games already cached cost nothing. Free history calls only, plus one billable
/fixtures call per league per run (4). Measurement data only; nothing here touches a bet. The log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
BOOKS = ["pinnacle", "novig.us", "prophetx", "kalshi", "polymarket.us", "hardrockbet"]
FILL_FROM = datetime.fromisoformat(os.environ.get("FILL_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)
MAX_GAMES = int(os.environ.get("FILL_MAX", "") or "700")


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("cache fill: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FILL_FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    todo = []
    for fid, f in (st.get("fixtures") or {}).items():
        s = cl.tp(f.get("start"))
        if f.get("lg") in LEAGUES and s and FILL_FROM <= s <= now - hc.FINAL_AFTER:
            if not all(os.path.exists(hc._path(fid, b)) for b in BOOKS):
                todo.append((s, fid))
    todo.sort(reverse=True)   # newest first: the games the models use most
    done = errs = 0
    for i, (s, fid) in enumerate(todo[:MAX_GAMES], 1):
        h = hc.get_hist(fid, BOOKS, s)
        if isinstance(h, dict) and h.get("_error"):
            errs += 1
        else:
            done += 1
        if i % 25 == 0:   # progress (counts only) so a long fill can be read while it runs
            print(f"cache fill progress: {i} of {min(len(todo), MAX_GAMES)} games, errors {errs}, spacing {cl.HIST_GAP[0]:.1f}s", flush=True)
    n_files = len(os.listdir(hc.DIR)) if os.path.isdir(hc.DIR) else 0
    size = sum(os.path.getsize(os.path.join(hc.DIR, x)) for x in os.listdir(hc.DIR)) if n_files else 0
    print(f"cache fill: fixtures {len(st.get('fixtures') or {})}, needing data {len(todo)}, filled {done}, errors {errs}, "
          f"cache files {n_files}, size {size / 1e6:.0f} MB, calls {len(cl.CALLS)} (billable {cl.STATS['billable']})")   # counts only


if __name__ == "__main__":
    main()
