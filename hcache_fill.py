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
import re
import shutil
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
BOOKS = ["pinnacle", "novig.us", "prophetx", "kalshi", "polymarket.us", "hardrockbet"]
FILL_FROM = datetime.fromisoformat(os.environ.get("FILL_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)
MAX_GAMES = int(os.environ.get("FILL_MAX", "") or "700")
ORDER = (os.environ.get("FILL_ORDER", "") or "newest").lower()   # Nov 2 18:01 (Peter: faster now): a 2nd fill runs oldest-first
MERGE = [d for d in (os.environ.get("FILL_MERGE", "") or "").split(",") if d]   # extra restored cache dirs folded in first


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("cache fill: ODDSPAPI_KEY not set")
        return
    os.makedirs(hc.DIR, exist_ok=True)
    merged = 0
    for d in MERGE:   # fold other fills' caches into this one (files are per game x book, so a plain copy is a merge)
        if os.path.isdir(d):
            for x in os.listdir(d):
                if not os.path.exists(os.path.join(hc.DIR, x)):
                    shutil.copy2(os.path.join(d, x), os.path.join(hc.DIR, x))
                    merged += 1
    if MERGE:
        print(f"cache fill: merged {merged} files from {len(MERGE)} other caches", flush=True)
    st = {"billable": {}}
    # Nov 3 21:10 (Peter: "dont use credits for this"): by default the game list comes from the fixture lists other jobs
    # already hold (exchange-lag, SLOW-HR logger; encrypted state) - zero credits. FILL_FIXTURES=api uses 4 billable calls.
    src = "OddsPapi /fixtures (billable)"
    if (os.environ.get("FILL_FIXTURES", "") or "cached").lower() != "api":
        n_ = 0
        for path in ("exlag/state.enc", "slowhr/state.enc"):
            try:
                other = tb.dec(json.load(open(path)))
            except Exception:
                continue
            for fid, f in (other.get("fixtures") or {}).items():
                if f.get("lg") in LEAGUES and fid not in st.setdefault("fixtures", {}):
                    st["fixtures"][fid] = f
                    n_ += 1
        src = f"cached lists ({n_} fixtures, 0 credits)"
    else:
        for lg in LEAGUES:
            cl.refresh_fixtures(st, now, lg, (FILL_FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    print(f"cache fill: game list from {src}", flush=True)   # counts only
    todo = []
    for fid, f in (st.get("fixtures") or {}).items():
        s = cl.tp(f.get("start"))
        if f.get("lg") in LEAGUES and s and FILL_FROM <= s <= now - hc.FINAL_AFTER:
            if not all(hc.have(fid, b) for b in BOOKS):   # Nov 3: a paid-key empty exchange answer is re-asked once a free key exists
                todo.append((s, fid))
    todo.sort(reverse=(ORDER != "oldest"))   # newest first: the games the models use most (oldest first for a 2nd fill)
    done = errs = 0
    codes, first_err = {}, ""   # Nov 3 19:50: error codes + first error text in the log (no amounts) so a failing fill is diagnosable
    for i, (s, fid) in enumerate(todo[:MAX_GAMES], 1):
        h = hc.get_hist(fid, BOOKS, s)
        if isinstance(h, dict) and h.get("_error"):
            errs += 1
            codes[h["_error"]] = codes.get(h["_error"], 0) + 1
            if not first_err:
                first_err = re.sub(r"[A-Za-z0-9_-]{20,}", "***", str(h.get("_body", "")))[:150].replace("\n", " ")   # never echo a key
                print(f"cache fill first error: code {h['_error']} - {first_err}", flush=True)
        else:
            done += 1
        if i % 25 == 0:   # progress (counts only) so a long fill can be read while it runs
            print(f"cache fill progress: {i} of {min(len(todo), MAX_GAMES)} games, errors {errs} {codes}, spacing {cl.HIST_GAP[0]:.1f}s", flush=True)
    n_files = len(os.listdir(hc.DIR)) if os.path.isdir(hc.DIR) else 0
    size = sum(os.path.getsize(os.path.join(hc.DIR, x)) for x in os.listdir(hc.DIR)) if n_files else 0
    print(f"cache fill: fixtures {len(st.get('fixtures') or {})}, needing data {len(todo)}, filled {done}, errors {errs}, "
          f"cache files {n_files}, size {size / 1e6:.0f} MB, calls {len(cl.CALLS)} (billable {cl.STATS['billable']}), "
          f"rate-limit waits {cl.STATS.get('rate_waits', 0)}, free key {'on' if hc.FREE_KEY else 'off'}")   # counts only
    print("cache fill per book (answers with markets / empty): " +
          ", ".join(f"{b} {v['markets']}/{v['empty']}" for b, v in sorted(hc.BOOK_STATS.items())), flush=True)   # counts only


if __name__ == "__main__":
    main()
