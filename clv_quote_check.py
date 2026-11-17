#!/usr/bin/env python3
"""READ-ONLY Pinnacle ACTIVE-FLAG audit of certified live bot closes (Peter, Nov 17). FREE history path only.

For every bot row from Nov 12 ET with a CERTIFIED close (report_sections.clv_method == 'certified'), the close is
recomputed twice with the ledger's own close_for: as stored (every last pregame tick), and with a withdrawn line
treated as absent (a line whose last pregame tick is active=False). Same result -> the close did not depend on a
withdrawn line. Different -> AFFECTED. Also flags closes older than 60 min (stale-feed warning).
Counts only in the log; no prices, ids or amounts. Writes nothing; the ledger is never changed.
"""
import collections
import json
import sys

import clv_ledger as cl
import fixture_match as fxm
import hist_cache as hc
import report_sections as rs
import tracker_build as tb

START = "2026-11-12"
STALE_MIN = 60


_LAST_TICK = cl.last_tick   # the ledger's own reader, captured before any substitution


def active_only(ticks, before):
    lt = _LAST_TICK(ticks, before)
    return None if (lt and lt[1].get("active") is False) else lt


def main():
    st = tb.dec(json.load(open(cl.STATE)))
    mk = (json.load(open(cl.MKFILE)) or {}).get("m") or {}
    fxs = dict({k: f for k, (f, _s) in fxm.alt_fixtures().items()}, **(st.get("fixtures") or {}))
    rows = []
    for k, r in (st.get("bets") or {}).items():
        s = r.get("snap") or {}
        gs = cl.tp(s.get("game_start"))
        if (gs and gs.astimezone(cl.ET).strftime("%Y-%m-%d") >= START
                and r.get("clv") is not None and not r.get("fixture_doubt") and rs.clv_method(r) == "certified"):
            rows.append((k, r))
    print(f"certified closes from {START} ET (rows, every source - a superset of the bot positions, which include "
          f"registry-proven rows the tracker labels otherwise): {len(rows)}; tracker-labelled bot {sum(1 for _k, r in rows if (r.get('snap') or {}).get('source') == 'bot')}")
    C = collections.Counter()
    orig_lt = cl.last_tick
    for k, r in rows:
        s, fid = r["snap"], r.get("fixture")
        f = fxs.get(fid)
        if not f:
            C["unverifiable: fixture not in any store"] += 1
            continue
        start = cl.tp(f.get("start")) or cl.tp(s.get("game_start"))
        h = hc.get_hist(fid, ["pinnacle"], start)
        if isinstance(h, dict) and h.get("_error"):
            h = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
        if isinstance(h, dict) and h.get("_error"):
            C["unverifiable: history unavailable"] += 1
            continue
        pm = cl.book_markets(h, "pinnacle")
        lg = s.get("league")
        a, _ = cl.close_for(s, f, pm, mk, start, lg)
        cl.last_tick = active_only
        try:
            b, why_b = cl.close_for(s, f, pm, mk, start, lg)
        finally:
            cl.last_tick = orig_lt
        if not a:
            C["unverifiable: stored close not reproduced"] += 1
            continue
        if b and abs(b["p"] - a["p"]) < 1e-12 and b["how"] == a["how"]:
            C["OK: same close using active lines only"] += 1
        elif b:
            C[f"AFFECTED: close changes without withdrawn lines ({b['how'][:4]})"] += 1
        else:
            C["AFFECTED: no close without withdrawn lines"] += 1
        if (a.get("age_min") or 0) > STALE_MIN:
            C[f"stale-feed warning: close older than {STALE_MIN} min"] += 1
        C[f"league {lg}"] += 1
    for kk in sorted(C):
        print(f"  {kk}: {C[kk]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
