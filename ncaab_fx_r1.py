#!/usr/bin/env python3
"""ONE-TIME PAID FIXTURE LOOKUP FOR R1's UNCOVERED COLLEGE-BASKETBALL GAMES (Peter, 17 Nov 2026: "Do paid calls").

R1 has 47 graded plays and a certified Pinnacle close on 26. Of the 21 without one, 17 fail for a single reason the
certifier's own counters report: "no fixture in any cache matches this league and date". The games were played; we
never fetched the fixture list for those dates. This makes exactly ONE billable /fixtures call (sportId=11, all
basketball, over the whole date range at once - /fixtures bills per league per [from,to] range, not per day), adds the
NCAAB fixtures that match a waiting row to oddspapi/fixtures_ncaab.json, then fills their Pinnacle history through the
FREE /historical-odds path. paper_clv_certify then re-certifies from the cache.

Hard limits: BILL_CAP billable calls, refused by the credit gate before that. Records itself under TAG so a second run
makes no call. Writes the public fixture store and hcache only; clv/ is never touched, and no live rule reads any of it.
"""
import collections
import json
import os
import sys

import clv_ledger as cl
import clv_obs_audit as oa
import fixture_match as fxm
import hist_cache as hc

OUT = "oddspapi/fixtures_ncaab.json"
TAG = "r1_fixture_recovery_2026_11_17"
BILL_CAP = int(os.environ.get("R1FX_BILL_CAP", "") or "2")
NEED = "no fixture in any cache"


def targets(alerts, rejected):
    """[(alert, snapshot)] for R1-eligible graded plays the certifier rejected for a missing fixture list."""
    import agree_rules as ar
    out = []
    for a in alerts:
        if not isinstance(a, dict) or a.get("result") not in ("W", "L", "P") or not ar.r1(a)[0]:
            continue
        why = str(rejected.get(f"sharp|{a.get('alert_utc')}|{a.get('game')}|{a.get('bet')}|{a.get('book_key')}") or "")
        if NEED in why:
            out.append((a, oa.snap_for(a, "sharp")))
    return out


def window(rows):
    days = sorted(str(a.get("start_utc"))[:10] for a, _s in rows if a.get("start_utc"))
    return (days[0], days[-1]) if days else (None, None)


def fixtures_from(d):
    out = {}
    for f in d if isinstance(d, list) else []:
        if not f.get("fixtureId"):
            continue
        out[f["fixtureId"]] = ({"lg": "NCAAB", "start": f.get("startTime"), "status": f.get("statusId"),
                                "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                                "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                                "n1": f.get("participant1Name"), "n2": f.get("participant2Name")},
                               f.get("tournamentId"), str(f.get("tournamentName") or ""))
    return out


def main():
    now = cl.datetime.now(cl.timezone.utc)
    store = json.load(open(OUT))
    if store.get(TAG):
        print("REFUSED: this recovery already ran - no call made")
        return 1
    A = (json.load(open("alerts.json")) or {}).get("alerts") or []
    rej = (json.load(open("paper/clv_certified.json")) or {}).get("rejected") or {}
    rows = targets(A, rej)
    lo, hi = window(rows)
    print(f"R1 plays waiting on a fixture list: {len(rows)} | dates {lo}..{hi}")
    if not rows or not lo:
        print("nothing to recover - no call made")
        return 0
    st = tb_state()
    if not cl.can_bill(st, now, 1):
        print("REFUSED: monthly cap - no call made")
        return 1
    try:
        d = cl.api("/fixtures", True, sportId=11, **{"from": lo, "to": hi})
    except cl.GateRefused as e:
        print(f"REFUSED by the credit gate, no call made: {e}")
        return 1
    if isinstance(d, dict) and d.get("_error"):
        print(f"OddsPapi error {d['_error']} after {cl.STATS['billable']} billable call(s) - nothing written")
        return 1
    if cl.STATS["billable"] > BILL_CAP:
        print(f"STOP: {cl.STATS['billable']} billable calls exceeds the cap {BILL_CAP}")
        return 1
    allfx = fixtures_from(d)
    print(f"basketball fixtures returned: {len(allfx)} | billable calls: {cl.STATS['billable']}")
    fx = store.setdefault("fixtures", {})
    comps, matched, added, hist = collections.Counter(), 0, 0, 0
    for i, (a, s) in enumerate(rows, 1):
        fid, note = fxm.ordered_match(s, {k: v[0] for k, v in allfx.items()}, cl.tp)
        if not fid:
            print(f"row {i}: still NO FIXTURE - {str(note)[:70]}")
            continue
        f, tid, tname = allfx[fid]
        start, want = cl.tp(f["start"]), cl.tp(s.get("game_start"))
        if not start or not want or abs((start - want).total_seconds()) > 3 * 3600:
            print(f"row {i}: fixture start disagrees with the bet's game start - not added")
            continue
        matched += 1
        comps[f"{tid} {tname}"[:50]] += 1
        if fid not in fx:
            fx[fid] = f
            added += 1
        h = hc.get_hist(fid, ["pinnacle"], start)   # FREE path (/historical-odds)
        bm = ((h or {}).get("bookmakers") or {}).get("pinnacle") or {}
        if isinstance(bm, dict) and bm.get("markets"):
            hist += 1
    store[TAG] = {"at": cl.iso(now), "window": [lo, hi], "returned": len(allfx), "added": added}
    json.dump(store, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"competitions matched: {dict(comps)}")
    print(f"SUMMARY rows {len(rows)} | matched {matched} | fixtures added {added} | with Pinnacle history {hist} | "
          f"billable calls {cl.STATS['billable']}")
    return 0


def tb_state():
    import tracker_build as tb
    return tb.dec(json.load(open(cl.STATE)))


if __name__ == "__main__":
    sys.exit(main())
