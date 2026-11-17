#!/usr/bin/env python3
"""ONE-TIME basketball-wide fixture search (Peter, Nov 17 08:45 "OK DO IT"). Exactly ONE billable /fixtures call by
sportId=11 (all basketball competitions) over Nov 16-17 (under 48 h), for the NCAAB bot rows still waiting whose game
day IS listed under tournament 648 but the game itself is not (filed under another competition). Matching NCAAB-looking
fixtures are ADDED to oddspapi/fixtures_ncaab.json (never overwritten), with their competition id/name logged as counts;
then each waiting row is graded READ-ONLY with the ledger's own functions. Records itself so it cannot repeat.
"""
import collections
import json
import sys

import clv_ledger as cl
import fixture_match as fxm
import tracker_build as tb

OUT = "oddspapi/fixtures_ncaab.json"
TAG = "sportsearch_2026_11_17"
FROM, TO = "2026-11-16", "2026-11-17"


def main():
    now = cl.datetime.now(cl.timezone.utc)
    store = json.load(open(OUT))
    if store.get(TAG):
        print("REFUSED: this search already ran - no call")
        return 1
    st = tb.dec(json.load(open(cl.STATE)))
    rs = [(k, r) for k, r in sorted((st.get("bets") or {}).items())
          if (r.get("snap") or {}).get("league") == "NCAAB" and r.get("clv") is None and not r.get("done")
          and cl.tp((r.get("snap") or {}).get("game_start"))
          and FROM <= cl.tp(r["snap"]["game_start"]).astimezone(cl.ET).strftime("%Y-%m-%d") <= TO]
    print(f"NCAAB rows waiting with a game on {FROM}..{TO} ET: {len(rs)}")
    if not rs:
        print("nothing to search for - no call")
        return 0
    if not cl.can_bill(st, now, 1):
        print("REFUSED: monthly cap - no call")
        return 1
    try:
        d = cl.api("/fixtures", True, sportId=11, **{"from": FROM, "to": TO})
    except cl.GateRefused as e:
        print(f"REFUSED by the credit gate, no call made: {e}")
        return 1
    print(f"billable calls made: {cl.STATS['billable']} (sportId 11, {FROM}..{TO})")
    if isinstance(d, dict) and d.get("_error"):
        print(f"OddsPapi error {d['_error']} - nothing written")
        return 1
    allfx = {}
    for f in d if isinstance(d, list) else []:
        if f.get("fixtureId"):
            allfx[f["fixtureId"]] = ({"lg": "NCAAB", "start": f.get("startTime"), "status": f.get("statusId"),
                                      "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                                      "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                                      "n1": f.get("participant1Name"), "n2": f.get("participant2Name")},
                                     f.get("tournamentId"), str(f.get("tournamentName") or ""))
    print(f"basketball fixtures returned: {len(allfx)}")
    fx = store.setdefault("fixtures", {})
    found = cert = added = 0
    comps = collections.Counter()
    mkmap = (json.load(open(cl.MKFILE)) or {}).get("m") or {}
    for i, (k, r) in enumerate(rs, 1):
        s = r["snap"]
        cand = {fid: v[0] for fid, v in allfx.items()}
        fid, note = fxm.ordered_match(s, cand, cl.tp)
        if not fid:
            print(f"row {i}: NO FIXTURE in any basketball competition - {str(note)[:80]}")
            continue
        f, tid, tname = allfx[fid]
        start = cl.tp(f["start"])
        if not start or abs((start - cl.tp(s["game_start"])).total_seconds()) > 3 * 3600:
            print(f"row {i}: FIXTURE START DISAGREES with the bet's game start; not certified")
            continue
        comps[f"{tid} {tname}"[:60]] += 1
        found += 1
        if fid not in fx:
            fx[fid] = f
            added += 1
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
            print(f"row {i}: fixture matched; NOT certified - {why or 'no after-fee entry price'}")
    store[TAG] = {"at": cl.iso(now), "window": [FROM, TO], "returned": len(allfx), "added": added}
    json.dump(store, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"competition of the matched games (id name): {dict(comps)}")
    print(f"SUMMARY rows {len(rs)} | matched {found} | certified {cert} | added {added} | billable calls {cl.STATS['billable']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
