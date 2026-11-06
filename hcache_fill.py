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
import ncaab_top100 as t100
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL", "NCAAB")   # Nov 6 (Peter): NCAAB, Top 100 games only (ncaab_top100.py)
SHRINK_MIN = int(os.environ.get("FILL_SHRINK_MIN", "") or "40")   # Nov 6: time for trimming older untrimmed files per run
BOOKS = ["pinnacle", "novig.us", "prophetx", "kalshi", "polymarket.us", "hardrockbet"]
FILL_FROM = datetime.fromisoformat(os.environ.get("FILL_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)
MAX_GAMES = int(os.environ.get("FILL_MAX", "") or "700")
BUDGET_MIN = int(os.environ.get("FILL_BUDGET_MIN", "") or "150")   # Nov 4 (Peter): 2.5 h batches - stop in time for the save, lose less on a failure
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
    # Nov 6 (Peter): NCAAB is not in the other jobs' lists, so it always takes its own fixtures call (paid key, at most every
    # 6 h). Only games with a Top 100 team are kept; no ratings file -> no NCAAB at all.
    top = t100.load()
    if top:
        cl.refresh_fixtures(st, now, "NCAAB", (FILL_FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    fx_all = st.get("fixtures") or {}
    n_cbb = sum(1 for f in fx_all.values() if f.get("lg") == "NCAAB")
    for fid in [k for k, f in fx_all.items() if f.get("lg") == "NCAAB" and not t100.game_in([f.get("p1"), f.get("p2")], top)]:
        del fx_all[fid]
    kept = sum(1 for f in fx_all.values() if f.get("lg") == "NCAAB")
    print(f"cache fill: NCAAB {kept} of {n_cbb} games have a Top 100 team" if top else "cache fill: NCAAB skipped (Top 100 ratings missing)", flush=True)
    print(f"cache fill: game list from {src}", flush=True)   # counts only
    # Nov 6: trim older (untrimmed) cache files to the tested markets, within SHRINK_MIN; the rest continue next run.
    if os.path.isdir(hc.DIR) and hc.KEEP:
        t0, saved, n_sh, left_sh = datetime.now(timezone.utc), 0, 0, 0
        for x in sorted(os.listdir(hc.DIR)):
            if datetime.now(timezone.utc) - t0 > timedelta(minutes=SHRINK_MIN):
                left_sh += 1
                continue
            b_ = hc.shrink_file(os.path.join(hc.DIR, x))
            if b_ is not None:
                saved += b_
                n_sh += 1
        print(f"cache fill: trimmed {n_sh} older files, saved {saved / 1e6:.0f} MB" + (f", about {left_sh} files not checked yet" if left_sh else ""), flush=True)
    todo = []
    for fid, f in (st.get("fixtures") or {}).items():
        s = cl.tp(f.get("start"))
        if f.get("lg") in LEAGUES and s and FILL_FROM <= s <= now - hc.FINAL_AFTER:
            if not all(hc.have(fid, b) for b in BOOKS):   # Nov 3: a paid-key empty exchange answer is re-asked once a free key exists
                todo.append((s, fid))
    todo.sort(reverse=(ORDER != "oldest"))   # newest first: the games the models use most (oldest first for a 2nd fill)
    done = errs = 0
    codes, first_err = {}, ""   # Nov 3 19:50: error codes + first error text in the log (no amounts) so a failing fill is diagnosable
    t_start = datetime.now(timezone.utc)
    stopped = False
    for i, (s, fid) in enumerate(todo[:MAX_GAMES], 1):
        # Nov 4 4:45 AM: run 41768012373 hit GitHub's 6 h job limit mid-download, so the save step was killed and about 350
        # games were lost. Stop downloading after FILL_BUDGET_MIN (default 300) so the cache save always has time to finish.
        if datetime.now(timezone.utc) - t_start > timedelta(minutes=BUDGET_MIN):
            stopped = True
            print(f"cache fill: time budget {BUDGET_MIN} min reached at game {i - 1}; stopping so the cache can save", flush=True)
            break
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
    # Nov 4 (Peter: "before we get to full memory leave room - delete the oldest games and keep the newest"): GitHub keeps at
    # most 10 GB of caches, so cap this one at CAP_GB (default 8). Over the cap, whole OLDEST games (by listed start, then
    # file age for games not in the list) are deleted until it fits. Counts only in the log.
    cap = float(os.environ.get("CAP_GB", "") or "8") * 1e9
    if os.path.isdir(hc.DIR):
        files = [os.path.join(hc.DIR, x) for x in os.listdir(hc.DIR)]
        total = sum(os.path.getsize(p) for p in files)
        if total > cap:
            starts = {fid: cl.tp(f.get("start")) for fid, f in (st.get("fixtures") or {}).items()}
            games = {}
            for p in files:
                games.setdefault(os.path.basename(p).split("__")[0], []).append(p)
            def age(fid):
                t = starts.get(fid)
                return t.timestamp() if t else min(os.path.getmtime(p) for p in games[fid])
            cut = 0
            for fid in sorted(games, key=age):
                if total <= cap:
                    break
                for p in games[fid]:
                    total -= os.path.getsize(p)
                    os.remove(p)
                cut += 1
            print(f"cache fill: over the {cap / 1e9:.0f} GB cap - removed the {cut} oldest games to make room", flush=True)
    n_files = len(os.listdir(hc.DIR)) if os.path.isdir(hc.DIR) else 0
    size = sum(os.path.getsize(os.path.join(hc.DIR, x)) for x in os.listdir(hc.DIR)) if n_files else 0
    print(f"cache fill: fixtures {len(st.get('fixtures') or {})}, needing data {len(todo)}, filled {done}, errors {errs}, "
          f"cache files {n_files}, size {size / 1e6:.0f} MB, calls {len(cl.CALLS)} (billable {cl.STATS['billable']}), "
          f"rate-limit waits {cl.STATS.get('rate_waits', 0)}, free key {'on' if hc.FREE_KEY else 'off'}")   # counts only
    left = max(0, len(todo) - done - errs)
    print(f"cache fill: {'stopped at the time budget' if stopped else 'finished the list'}; games still needing data about {left}", flush=True)
    if os.environ.get("GITHUB_OUTPUT"):   # Nov 4: the workflow starts the next batch after a SUCCESSFUL save when more remain
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"more={'1' if (stopped and left > 0) else '0'}\n")
    print("cache fill per book (answers with markets / empty): " +
          ", ".join(f"{b} {v['markets']}/{v['empty']}" for b, v in sorted(hc.BOOK_STATS.items())), flush=True)   # counts only


if __name__ == "__main__":
    main()
