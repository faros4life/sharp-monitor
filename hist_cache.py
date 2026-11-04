#!/usr/bin/env python3
"""
SHARED ODDSPAPI HISTORY CACHE (Nov 2, 2026; Peter yes 15:11 ET). Each FINISHED game's /historical-odds data is downloaded
once per bookmaker, gzip-compressed, and kept in hcache/ - restored and saved by each workflow through GitHub's Actions
cache (private to this repo's workflows; never committed, so OddsPapi data is not republished). Every test reads from it,
so re-runs and new variants take minutes instead of re-downloading at ~8 s per call.

A game counts as finished 4 h after its listed start; before that, history is fetched fresh and not stored (prices are
still moving). A bookmaker with no data for a finished game is stored as empty, so it is not asked again.
"""
import gzip
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl

DIR = os.environ.get("HCACHE_DIR", "") or "hcache"
FINAL_AFTER = timedelta(hours=4)
STATS = {"hit": 0, "miss": 0}
# Nov 3 21:00 (Peter: "if needed build tonight and run so we have the data in the morning"). OddsPapi staff: a paid plan
# may stop returning history for books it did not buy (our exchanges). Two guards:
# 1) An EMPTY exchange answer under the paid key is stored as {"_empty_by": "paid"} - never as a final "no data" - so it is
#    asked again once a free-account key exists (secret ODDSPAPI_FREE_KEY, never in a file or log).
# 2) With ODDSPAPI_FREE_KEY set, exchange books are fetched with that key (its own rate limit), Pinnacle / Hard Rock with
#    the paid key. BOOK_STATS counts, per book, answers with markets vs empty (counts only), so coverage is visible.
FREE_KEY = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()
EXCH_BOOKS = {"novig.us", "prophetx", "kalshi", "polymarket.us"}
BOOK_STATS = {}
# Nov 4 9:37 (Wenzel, OddsPapi): on v4 the paid plan's Pinnacle is "Pinnacle +30 sec", slug "pinnacle+30" - asking for
# "pinnacle" is what gave the 403. Probe (run 41852138523): the paid key returns Pinnacle (as pinnacle+30) and Hard Rock
# history. Peter 10:02 "let the run save then change": Pinnacle + Hard Rock go on the PAID key, the exchanges on the FREE
# key, and the two keys' calls run side by side (each key keeps its own OddsPapi cooldown). Stored under the plain book
# name. History stays free on both keys. HIST_PAID=off returns to all-on-the-free-key.
PAID_SLUG = {"pinnacle": "pinnacle+30"}
PAID_BOOKS = ("pinnacle", "hardrockbet")
PAID_HIST = (os.environ.get("HIST_PAID") or "on").strip().lower() == "on" and bool(cl.KEY)


def _paid_empty(d):
    return isinstance(d, dict) and d.get("_empty_by") == "paid"


def have(fid, book):
    """True when the cache holds a final answer for this game x book (a paid-key empty exchange answer is not final
    once a free key is available)."""
    p = _path(fid, book)
    if not os.path.exists(p):
        return False
    if FREE_KEY and book in EXCH_BOOKS:
        try:
            with gzip.open(p, "rt") as fh:
                return not _paid_empty(json.load(fh))
        except Exception:
            return False
    return True


def _path(fid, book):
    return os.path.join(DIR, f"{fid}__{book}.json.gz")


def get_hist(fid, books, start=None):
    """{'bookmakers': {book: {...}}} for the requested books, or the API's error dict ({'_error': ...})."""
    now = datetime.now(timezone.utc)
    final = bool(start) and now - start >= FINAL_AFTER
    out, need = {"bookmakers": {}}, []
    for b in books:
        p = _path(fid, b)
        if final and os.path.exists(p):
            try:
                with gzip.open(p, "rt") as fh:
                    d = json.load(fh)
                if not (FREE_KEY and b in EXCH_BOOKS and _paid_empty(d)):
                    out["bookmakers"][b] = d
                    STATS["hit"] += 1
                    continue
            except Exception:
                pass
        need.append(b)
    if FREE_KEY:
        paid = [b for b in need if PAID_HIST and b in PAID_BOOKS]
        free = [b for b in need if b not in paid]
    else:
        paid, free = list(need), []
    pkey = cl.KEY if FREE_KEY else None   # explicit, or cl.api would route history to the free key
    groups = ([(paid[i:i + 3], pkey, True) for i in range(0, len(paid), 3)]
              + [(free[i:i + 3], FREE_KEY, False) for i in range(0, len(free), 3)])

    def _fetch(grp, key, is_paid):
        names = [PAID_SLUG.get(b, b) if is_paid else b for b in grp]
        h = None
        for _ in range(2):
            h = cl.api("/historical-odds", False, apikey=key, fixtureId=fid, bookmakers=",".join(names))
            if not (isinstance(h, dict) and h.get("_error")) or h.get("_error") == 404:
                break   # Nov 4 11:10: a 404 is a final "no data" answer - never ask twice (halves calls on empty games)
        if isinstance(h, dict) and isinstance(h.get("bookmakers"), dict) and is_paid:
            h["bookmakers"] = {b: h["bookmakers"].get(PAID_SLUG.get(b, b)) for b in grp}   # back to the plain names
        return h

    # Nov 4: the paid-key groups and the free-key groups run in parallel (one thread per key; each key stays serial)
    from concurrent.futures import ThreadPoolExecutor
    by_key = {}
    for g in groups:
        by_key.setdefault(g[2], []).append(g)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {k: pool.submit(lambda gs: [(g, _fetch(*g)) for g in gs], gs) for k, gs in by_key.items()}
        results = [x for k in (True, False) if k in futs for x in futs[k].result()]
    for (grp, key, is_paid), h in results:   # OddsPapi takes up to 3 bookmakers per history call
        if isinstance(h, dict) and h.get("_error") == 404:
            # Nov 3 22:35 (probe run 41766896409): OddsPapi answers 404 when NONE of the requested books has history for the
            # game (e.g. Kalshi alone on a game it never listed); a group where some books have data answers 200 with the
            # rest empty. So a 404 is a final "no data" for these books - store it empty instead of re-asking every run.
            STATS["no_data_404"] = STATS.get("no_data_404", 0) + 1
            h = {"bookmakers": {}}
        if isinstance(h, dict) and h.get("_error"):
            return h
        STATS["miss"] += len(grp)
        for b in grp:
            bm = ((h or {}).get("bookmakers") or {}).get(b) or {}
            s_ = BOOK_STATS.setdefault(b, {"markets": 0, "empty": 0})
            s_["markets" if (bm.get("markets") if isinstance(bm, dict) else None) else "empty"] += 1
            if not bm and b in EXCH_BOOKS and is_paid:
                bm = {"_empty_by": "paid"}   # not a final "no data": re-asked once a free key exists
            out["bookmakers"][b] = bm
            if final:
                try:
                    os.makedirs(DIR, exist_ok=True)
                    with gzip.open(_path(fid, b), "wt") as fh:
                        json.dump(bm, fh, separators=(",", ":"))
                except Exception:
                    pass
    return out
