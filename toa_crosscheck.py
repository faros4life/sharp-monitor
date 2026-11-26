#!/usr/bin/env python3
"""CROSS-CHECK: The Odds API close vs the OddsPapi close on the SAME row (Peter, Nov 26: "identical games, markets,
lines and comparable snapshot times. Report agreement rates, discrepancies and their causes").

Population: every graded row that OddsPapi certifies today (VERIFIED_PINNACLE, own line / moneyline, no 'src').
For each, The Odds API close is computed for the same row through toa.close() - same side, same exact line.
Missing snapshots are fetched up to CROSS_MAX_CREDITS (default 10,000), oldest games last.

Reported (counts and probability points only):
  agreement of the no-vig win probability: |diff| <= 0.5 / 1 / 2 points, median and 90th percentile
  causes for |diff| > 1 point: LATE MOVE (OddsPapi's closing tick is after The Odds API snapshot, i.e. the line
  moved in the last minutes - a timing gap, not a data error), STALE TOA QUOTE (the Odds API quote is older than the
  OddsPapi one), OTHER (unexplained - the number that matters).
"""
import collections
import json
import os
import sys
from datetime import timedelta

import clv_ledger as cl
import clv_obs_audit as oa
import fixture_match as fxm
import paper_clv_certify as pc
import toa
import toa_recover as tr
import tracker_build as tb

CAP = int(os.environ.get("CROSS_MAX_CREDITS", "") or "10000")


def main():
    st = tb.dec(json.load(open(cl.STATE)))
    mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    fxs = st.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **fxs)
    import board_build as bb
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    try:
        lanes = json.load(open(pc.LANES))
    except (OSError, ValueError):
        lanes = {}
    items = pc.gather(oa.load(oa.SHARP), oa.load(oa.LIQ), lanes, feed)
    pin = []
    for i, x, s, pre in items:
        if pre:
            continue
        cls, d = oa.classify(x, s, fxs, alt, allfx, mkmap)
        if cls == "VERIFIED_PINNACLE" and not d.get("src") and str(d.get("how")) in pc.CERT_HOW:
            pin.append((i, x, s, d))
    print(f"OddsPapi-certified rows: {len(pin)}")

    def toa_for(x, s):
        snap = oa.snap_for(x, s)
        lg = snap.get("league") or x.get("sport") or x.get("league")
        if lg not in toa.SPORT:
            return None, "league", None
        fx = toa.fixtures(lg)
        fid, _n = fxm.ordered_match(snap, fx, cl.tp)
        if not fid:
            return None, "no event", (toa.SPORT[lg], cl.tp(snap.get("game_start")))
        c, why = toa.close(snap, fx[fid], fid, lg, cl.parsed, fxm.resolve_side, cl.which_team, cl.novig_p,
                           cl.FRESH_MIN)
        return c, why, (toa.SPORT[lg], cl.tp(fx[fid]["start"]), fid.split(":", 1)[1])

    # fetch what is missing, newest games first, within the cap
    need_f, need_a = set(), set()
    for _i, x, s, _d in pin:
        c, why, k = toa_for(x, s)
        if c or not k:
            continue
        if why == "no event" or "not at the close" in str(why) or "no stored" in str(why):
            if k[1]:
                need_f.add((k[0], k[1].replace(second=0, microsecond=0)))
        elif "exact line" in str(why) and len(k) == 3:
            need_a.add(k)
    for k in sorted(need_f, key=lambda k: k[1], reverse=True):
        if toa.METER["credits"] + tr.FEAT_COST > CAP:
            break
        try:
            toa.fetch_snapshot(*k)
        except Exception:
            pass
    toa.reset_cache()
    for k in sorted(need_a, key=lambda k: k[1], reverse=True):
        if toa.METER["credits"] + tr.ALT_COST > CAP:
            break
        try:
            toa.fetch_alts(*k)
        except Exception:
            pass
    toa.reset_cache()

    diffs, causes, miss = [], collections.Counter(), collections.Counter()
    by_mkt = collections.defaultdict(list)
    games = set()
    for i, x, s, d in pin:
        c, why, k = toa_for(x, s)
        if not c:
            miss[str(why)[:60]] += 1
            continue
        diff = 100 * (c["p"] - d["p"])
        diffs.append(abs(diff))
        pz = cl.parsed(oa.snap_for(x, s)) or ("?",)
        by_mkt[pz[0]].append(abs(diff))
        games.add(k[2] if k and len(k) == 3 else i)
        if abs(diff) > 1:
            op_tick = d.get("age_min")
            snap_age = None
            if k and k[1] and c.get("snap_ts"):
                snap_age = (k[1] - cl.tp(c["snap_ts"])).total_seconds() / 60
            if op_tick is not None and snap_age is not None and op_tick < snap_age:
                causes["LATE MOVE (OddsPapi tick after the Odds API snapshot)"] += 1
            elif op_tick is not None and c.get("age_min") is not None and c["age_min"] > op_tick + 5:
                causes["STALE TOA QUOTE"] += 1
            else:
                causes["OTHER (unexplained)"] += 1
    n = len(diffs)
    if not n:
        print("no comparable pairs")
        return 0
    s_ = sorted(diffs)
    w = lambda t: sum(1 for v in diffs if v <= t)
    print(f"comparable pairs {n} | distinct games {len(games)} | not comparable {sum(miss.values())}")
    print(f"agreement |diff| <= 0.5 pt {w(0.5)} ({100 * w(0.5) / n:.1f}%) | <= 1 pt {w(1)} ({100 * w(1) / n:.1f}%) | "
          f"<= 2 pt {w(2)} ({100 * w(2) / n:.1f}%)")
    print(f"median |diff| {s_[n // 2]:.2f} pt | 90th pct {s_[int(n * 0.9)]:.2f} pt | max {s_[-1]:.2f} pt")
    for m, v in sorted(by_mkt.items()):
        v = sorted(v)
        print(f"  {m:<7} pairs {len(v):>5} | <=1 pt {100 * sum(1 for a in v if a <= 1) / len(v):.1f}% | "
              f"median {v[len(v) // 2]:.2f} pt")
    print("causes of |diff| > 1 pt:", dict(causes))
    print("not comparable, by reason:", dict(miss.most_common(8)))
    print(toa.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
