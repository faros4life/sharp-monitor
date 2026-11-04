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
    free = [b for b in need if FREE_KEY]   # Nov 3 21:30: with the free key, ALL books' history uses it (paid key: 403 on pinnacle)
    paid = [b for b in need if b not in free]
    groups = [(paid[i:i + 3], None) for i in range(0, len(paid), 3)] + [(free[i:i + 3], FREE_KEY) for i in range(0, len(free), 3)]
    for grp, key in groups:   # OddsPapi takes up to 3 bookmakers per history call
        h = None
        for _ in range(2):
            h = cl.api("/historical-odds", False, apikey=key, fixtureId=fid, bookmakers=",".join(grp))
            if not (isinstance(h, dict) and h.get("_error")):
                break
        if isinstance(h, dict) and h.get("_error"):
            return h
        STATS["miss"] += len(grp)
        for b in grp:
            bm = ((h or {}).get("bookmakers") or {}).get(b) or {}
            s_ = BOOK_STATS.setdefault(b, {"markets": 0, "empty": 0})
            s_["markets" if (bm.get("markets") if isinstance(bm, dict) else None) else "empty"] += 1
            if not bm and b in EXCH_BOOKS and key is None:
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
