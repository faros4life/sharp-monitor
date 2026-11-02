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
                    out["bookmakers"][b] = json.load(fh)
                STATS["hit"] += 1
                continue
            except Exception:
                pass
        need.append(b)
    for i in range(0, len(need), 3):   # OddsPapi takes up to 3 bookmakers per history call
        grp = need[i:i + 3]
        h = None
        for _ in range(2):
            h = cl.api("/historical-odds", False, fixtureId=fid, bookmakers=",".join(grp))
            if not (isinstance(h, dict) and h.get("_error")):
                break
        if isinstance(h, dict) and h.get("_error"):
            return h
        STATS["miss"] += len(grp)
        for b in grp:
            bm = ((h or {}).get("bookmakers") or {}).get(b) or {}
            out["bookmakers"][b] = bm
            if final:
                try:
                    os.makedirs(DIR, exist_ok=True)
                    with gzip.open(_path(fid, b), "wt") as fh:
                        json.dump(bm, fh, separators=(",", ":"))
                except Exception:
                    pass
    return out
