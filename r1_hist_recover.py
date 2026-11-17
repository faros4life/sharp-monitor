#!/usr/bin/env python3
"""FREE PINNACLE HISTORY FOR R1's LISTED-BUT-UNCACHED GAMES (Peter, 17 Nov 2026: "Option 1: Free only").

Targets ONLY the R1-eligible graded alerts that paper_clv_certify rejected as MISSING_HISTORY (a fixture IS matched,
no Pinnacle history was ever cached). Fetches each fixture's Pinnacle history once through hist_cache.get_hist on
/historical-odds - a FREE path (credit_gate.FREE_PATHS). The workflow passes ONLY the free-account key: there is no
paid key in the environment, so no billable call is possible. No fixture lookups (those bill). Hard cap R1H_MAX
fixtures. Writes hcache only; paper_clv_certify then re-certifies from the cache. Log: counts only.
"""
import json
import os
import sys
from datetime import datetime

import agree_rules as ar
import clv_ledger as cl
import hist_cache as hc

MAX = int(os.environ.get("R1H_MAX", "") or "20")


def targets(alerts, rejected):
    """{fid: start datetime} for R1-eligible graded alerts rejected only for missing cached history."""
    out = {}
    for a in alerts:
        if not isinstance(a, dict) or a.get("result") not in ("W", "L", "P") or not ar.r1(a)[0]:
            continue
        why = str(rejected.get(f"sharp|{a.get('alert_utc')}|{a.get('game')}|{a.get('bet')}|{a.get('book_key')}") or "")
        if not why.startswith("MISSING_HISTORY"):
            continue
        parts = why.split()
        fid = parts[parts.index("fixture") + 1] if "fixture" in parts else None
        try:
            st = datetime.fromisoformat(str(a.get("start_utc")).replace("Z", "+00:00"))
        except ValueError:
            st = None
        if fid and st:
            out.setdefault(fid, st)
    return out


def main():
    if cl.KEY:
        print("FAIL: a paid key is present; this job runs on the free key only")
        return 1
    if not cl.FREE_KEY:
        print("FAIL: no free key")
        return 1
    A = (json.load(open("alerts.json")) or {}).get("alerts") or []
    rej = (json.load(open("paper/clv_certified.json")) or {}).get("rejected") or {}
    T = targets(A, rej)
    got = empty = err = 0
    for fid, st in list(T.items())[:MAX]:
        h = hc.get_hist(fid, ["pinnacle"], start=st)
        if isinstance(h, dict) and h.get("_error"):
            err += 1
            continue
        bm = ((h or {}).get("bookmakers") or {}).get("pinnacle") or {}
        if bm.get("markets") if isinstance(bm, dict) else None:
            got += 1
        else:
            empty += 1
    print(f"r1 history: targets {len(T)} | tried {min(len(T), MAX)} | with Pinnacle markets {got} | "
          f"no data {empty} | errors {err} | cache files written {hc.STATS.get('miss', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
