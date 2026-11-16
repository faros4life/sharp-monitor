#!/usr/bin/env python3
"""ONE-TIME NCAAB FIXTURE RECOVERY + READ-ONLY CERTIFICATION (Peter, Nov 16 16:25).

Exactly ONE billable /fixtures call (tournament 648, Peter's pick), through the shared credit gate
and after the ledger's own monthly-cap check, covering the four reopened NCAAB bot rows. The
fixtures (public OddsPapi ids and team names only) are written to oddspapi/fixtures_ncaab.json,
which the ledger reads as an alternate store, and whose presence makes the ledger's own one-time
lookup a permanent no-op - so no repeat call is possible.

Then each of the four rows is graded INDEPENDENTLY with the ledger's own functions (ordered_match,
close_for, eff_dec, Pinnacle history via hist_cache on the FREE history path). The ledger state is
READ ONLY here; the official CLV is written by the scheduled ledger run, with the same code.
A row is certified only if the fixture match is unique AND agrees with find_fixture, the fixture
start is within 3 h of the row's game start, and close_for returns a same-line or standard-move
pregame close within FRESH_MIN. No stakes, ids or dollars are printed.
"""
import json
import os
import sys
from datetime import timedelta

import clv_ledger as cl
import fixture_match as fxm
import tracker_build as tb

OUT = "oddspapi/fixtures_ncaab.json"
TID = 648


def rows(st):
    return [(k, r) for k, r in sorted((st.get("bets") or {}).items())
            if r.get("ncaab_reopened") and (r.get("snap") or {}).get("league") == "NCAAB"
            and (r.get("snap") or {}).get("source") == "bot"]


def main():
    now = cl.datetime.now(cl.timezone.utc)
    if os.path.exists(OUT):
        print("REFUSED: the one-time NCAAB fixture recovery has already run (file present) - no call")
        return 1
    st = tb.dec(json.load(open(cl.STATE)))
    if st.get("ncaab_fx_once"):
        print("REFUSED: the ledger already used its one-time NCAAB lookup - no call")
        return 1
    rs = rows(st)
    print(f"reopened NCAAB bot rows: {len(rs)}")
    if len(rs) != 4:
        print("REFUSED: expected exactly 4 rows - no call")
        return 1
    starts = [cl.tp(r["snap"].get("game_start")) for _, r in rs]
    if not all(starts):
        print("REFUSED: a row has no game start - no call")
        return 1
    if not cl.can_bill(st, now, 1):
        print(f"REFUSED: the ledger's monthly cap would be exceeded ({cl.used_this_period(st, now)} of {cl.CAP}) - no call")
        return 1
    lo = (min(starts) - timedelta(days=1)).astimezone(cl.ET).strftime("%Y-%m-%d")
    hi = (max(starts) + timedelta(days=1)).astimezone(cl.ET).strftime("%Y-%m-%d")
    try:
        d = cl.api("/fixtures", True, tournamentId=TID, **{"from": lo, "to": hi})
    except cl.GateRefused as e:
        print(f"REFUSED by the credit gate, no call made: {e}")
        return 1
    print(f"billable calls made: {cl.STATS['billable']} (window {lo}..{hi}, tournament {TID})")
    if isinstance(d, dict) and d.get("_error"):
        print(f"OddsPapi error {d['_error']} - nothing written")
        return 1
    fx = {}
    for f in d if isinstance(d, list) else []:
        if f.get("fixtureId"):
            fx[f["fixtureId"]] = {"lg": "NCAAB", "start": f.get("startTime"), "status": f.get("statusId"),
                                  "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                                  "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                                  "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}
    json.dump({"note": "OddsPapi fixture ids (public). One-time NCAAB recovery, tournament 648, Nov 16 2026.",
               "fixtures": fx}, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"fixtures returned and saved: {len(fx)}")
    mkmap = (json.load(open(cl.MKFILE)) or {}).get("m") or {}
    stx = {"fixtures": fx}
    found, cert = 0, 0
    for i, (k, r) in enumerate(rs, 1):
        s = r["snap"]
        fid, note = fxm.ordered_match(s, fx, cl.tp)
        fid2 = cl.find_fixture(stx, s)
        if not fid:
            print(f"bet {i}: NO FIXTURE - {str(note)[:90]}")
            continue
        if fid2 and fid2 != fid:
            print(f"bet {i}: AMBIGUOUS - the two matchers disagree; not certified")
            continue
        f = fx[fid]
        start = cl.tp(f["start"])
        if not start or abs((start - cl.tp(s["game_start"])).total_seconds()) > 3 * 3600:
            print(f"bet {i}: FIXTURE START DISAGREES with the bet's game start; not certified")
            continue
        found += 1
        try:
            import hist_cache as hc
            h = hc.get_hist(fid, ["pinnacle"], start)
        except Exception as e:
            h = {"_error": str(e)[:40]}
        if isinstance(h, dict) and h.get("_error"):
            h = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
        if isinstance(h, dict) and h.get("_error"):
            print(f"bet {i}: fixture matched; Pinnacle history unavailable ({h['_error']}); not certified")
            continue
        pl = cl.tp(s.get("placed"))
        if pl and pl > start:
            print(f"bet {i}: fixture matched; placed after start - never scored")
            continue
        c, why = cl.close_for(s, f, cl.book_markets(h, "pinnacle"), mkmap, start, "NCAAB")
        dd = cl.eff_dec(s)
        if c and dd:
            cert += 1
            print(f"bet {i}: CERTIFIED  {cl.parsed(s)[0]}  CLV {100 * (c['p'] * dd - 1):+.2f}%  close {c['how']}, "
                  f"quote age {c['age_min']} min")
        else:
            print(f"bet {i}: fixture matched; NOT certified - {why or 'no after-fee entry price on the bet'}")
    print(f"SUMMARY fixtures recovered {found}/4 | certified {cert}/4 | billable calls {cl.STATS['billable']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
