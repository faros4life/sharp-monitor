#!/usr/bin/env python3
"""ONE-TIME NCAAB FIXTURE TOP-UP (Peter, Nov 17 07:26 "Get it"). Exactly ONE billable /fixtures call for NCAAB
tournament 648 (verified Nov 16), covering only the NCAAB rows from Nov 12 ET still waiting with "NCAAB fixture not in
any cached store". New fixtures are ADDED to oddspapi/fixtures_ncaab.json (existing ids never overwritten); the store
records the top-up so it can never repeat. Then each row is graded READ-ONLY with the ledger's own functions, exactly
as ncaab_fx_recover.py did. The official CLV is written by the scheduled ledger run, which reads this store.
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
TAG = "topup_2026_11_17"
START = "2026-11-12"


def main():
    now = cl.datetime.now(cl.timezone.utc)
    store = json.load(open(OUT)) if os.path.exists(OUT) else {"fixtures": {}}
    if store.get(TAG):
        print("REFUSED: this top-up already ran - no call")
        return 1
    st = tb.dec(json.load(open(cl.STATE)))
    rs = [(k, r) for k, r in sorted((st.get("bets") or {}).items())
          if (r.get("snap") or {}).get("league") == "NCAAB" and r.get("clv") is None and not r.get("done")
          and str(r.get("why") or "").startswith("NCAAB fixture not in any cached store")
          and cl.tp((r.get("snap") or {}).get("game_start"))
          and cl.tp(r["snap"]["game_start"]).astimezone(cl.ET).strftime("%Y-%m-%d") >= START]
    print(f"NCAAB rows waiting for a fixture since {START} ET: {len(rs)}")
    if not rs:
        print("nothing to recover - no call")
        return 0
    if not cl.can_bill(st, now, 1):
        print(f"REFUSED: the ledger's monthly cap would be exceeded - no call")
        return 1
    starts = [cl.tp(r["snap"]["game_start"]) for _, r in rs]
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
    fx, added = store.setdefault("fixtures", {}), 0
    for f in d if isinstance(d, list) else []:
        if f.get("fixtureId") and f["fixtureId"] not in fx:
            fx[f["fixtureId"]] = {"lg": "NCAAB", "start": f.get("startTime"), "status": f.get("statusId"),
                                  "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                                  "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                                  "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}
            added += 1
    store[TAG] = {"at": cl.iso(now), "window": [lo, hi], "returned": len(d) if isinstance(d, list) else 0, "added": added}
    json.dump(store, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"fixtures returned {store[TAG]['returned']}, added {added}, store now {len(fx)}")
    mkmap = (json.load(open(cl.MKFILE)) or {}).get("m") or {}
    found = cert = 0
    for i, (k, r) in enumerate(rs, 1):
        s = r["snap"]
        fid, note = fxm.ordered_match(s, fx, cl.tp)
        fid2 = cl.find_fixture({"fixtures": fx}, s)
        if not fid:
            print(f"row {i}: NO FIXTURE - {str(note)[:90]}")
            continue
        if fid2 and fid2 != fid:
            print(f"row {i}: AMBIGUOUS - the two matchers disagree; not certified")
            continue
        f = fx[fid]
        start = cl.tp(f["start"])
        if not start or abs((start - cl.tp(s["game_start"])).total_seconds()) > 3 * 3600:
            print(f"row {i}: FIXTURE START DISAGREES with the bet's game start; not certified")
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
            print(f"row {i}: fixture matched; Pinnacle history unavailable; not certified")
            continue
        c, why = cl.close_for(s, f, cl.book_markets(h, "pinnacle"), mkmap, start, "NCAAB")
        dd = cl.eff_dec(s)
        if c and dd and c["how"] in ("own line", "moneyline"):
            cert += 1
            print(f"row {i}: CERTIFIED  {cl.parsed(s)[0]}  CLV {100 * (c['p'] * dd - 1):+.2f}%  close {c['how']}, quote age {c['age_min']} min")
        elif c and dd:
            print(f"row {i}: ESTIMATED only ({c['how']}) - line-move adjusted, not certified")
        else:
            print(f"row {i}: fixture matched; NOT certified - {why or 'no after-fee entry price on the bet'}")
    print(f"SUMMARY rows {len(rs)} | fixtures matched {found} | certified {cert} | billable calls {cl.STATS['billable']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
