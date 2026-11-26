"""toa_alert_baseline.py - Pinnacle prices AT THE ALERT from The Odds API, for the zero-movement baseline of the plays whose
certified close came from that provider (Peter, Nov 26: approved, HARD CAP 100,000 credits, pilot first).

One historical call returns Pinnacle h2h/spreads/totals for EVERY game of a sport at one 5-minute snapshot (~30 credits),
so requests are deduplicated by (sport, 5-minute bucket of the alert) and the buckets covering the most plays go first.
Every response is cached in toa_hist and never fetched twice. The budget is checked BEFORE each call.

Pilot (TOA_PILOT=n): n buckets of these plays, plus up to n/2 buckets of plays that ALSO have OddsPapi history, so the
alert-time price can be checked against a second provider before the full run.

Certified CLV is not touched. Log: counts, credits and percentages only. Env: TOA_BUDGET, TOA_DRY, TOA_PILOT.
"""
import json
import os
import statistics as st
import sys
from collections import Counter
from datetime import timedelta

import clv_baseline as bl
import clv_ledger as cl
import clv_obs_audit as oa
import fixture_match as fxm
import toa

BUDGET = int(os.environ.get("TOA_BUDGET", "") or "0")
DRY = (os.environ.get("TOA_DRY", "") or "1") != "0"
PILOT = int(os.environ.get("TOA_PILOT", "") or "0")
COST = 30          # h2h + spreads + totals, one region-equivalent bookmaker; replaced by the real header after call 1


def bucket(t):
    return t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0)


def targets(certp, certl, items):
    """[(id, x, src, rec, lg, alert time)] for certified rows whose alert precedes the start."""
    out = []
    for i, x, src, pre in items:
        rec = certp.get(i) or (certl.get(i[4:]) if i.startswith("liq|") else None)
        if pre or not rec or rec.get("how") not in bl.CERT_HOW:
            continue
        snap = oa.snap_for(x, src)
        lg, ta, s0 = snap.get("league"), bl.alert_time(x, src), cl.tp(snap.get("game_start"))
        if lg not in toa.SPORT or not ta or (s0 and ta >= s0):
            continue
        out.append((i, x, src, rec, lg, ta))
    return out


def plan(rows, limit):
    """Buckets ordered by plays covered (desc), skipping any already in the store. Pure apart from have_snap."""
    c = Counter((toa.SPORT[lg], bucket(ta)) for _i, _x, _s, _r, lg, ta in rows)
    todo = [(k, n) for k, n in c.most_common() if not toa.have_snap(k[0], k[1])]
    return todo[:limit] if limit else todo, len(c)


def toa_fair(x, src, rec, lg, ta):
    """Alert-time Pinnacle no-vig from the store; for an OddsPapi row the event is matched by the ledger's own matcher."""
    snap = oa.snap_for(x, src)
    fx = toa.fixtures(lg)
    fid = rec.get("fid") if str(rec.get("fid") or "").startswith("toa:") else fxm.ordered_match(snap, fx, cl.tp)[0]
    f = fx.get(fid) if fid else None
    if not f:
        return None
    c, _w = toa.close(snap, dict(f, start=cl.iso(ta)), fid, lg, cl.parsed, fxm.resolve_side, cl.which_team,
                      cl.novig_p, cl.FRESH_MIN)
    return c["p"] if c and c.get("how") == rec.get("how") else None


def main():
    import paper_clv_certify as pc
    import board_build as bb
    certp = (json.load(open("paper/clv_certified.json")) or {}).get("certified") or {}
    certl = (json.load(open("liquidity/clv_certified.json")) or {}).get("certified") or {}
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    try:
        lanes = json.load(open(pc.LANES))
    except (OSError, ValueError):
        lanes = {}
    rows = targets(certp, certl, pc.gather(oa.load(oa.SHARP), oa.load(oa.LIQ), lanes, feed))
    T = [r for r in rows if r[3].get("src") == "theoddsapi"]
    O = [r for r in rows if r[3].get("src") != "theoddsapi"]
    tplan, tb_ = plan(T, PILOT)
    oplan, ob_ = plan(O, PILOT // 2 if PILOT else 0) if PILOT else ([], 0)
    print(f"plays from The Odds API needing an alert-time price {len(T)} | distinct snapshots {tb_} | to fetch {len(tplan)}")
    if PILOT:
        print(f"accuracy sample: OddsPapi plays {len(O)} | snapshots to fetch {len(oplan)}")
    est = COST * (len(tplan) + len(oplan))
    print(f"estimated credits {est} | budget {BUDGET} | dry {DRY}")
    if not DRY:
        for (sport, when), _n in tplan + oplan:
            if toa.METER["credits"] + (toa.METER["credits"] // max(toa.METER["calls"], 1) or COST) > BUDGET:
                print("STOPPED: next call would exceed the budget")
                break
            try:
                toa.fetch_snapshot(sport, when)
            except Exception as e:
                print(f"fetch failed ({type(e).__name__}) - stopping")
                break
        print(f"CREDITS: calls {toa.METER['calls']} | credits {toa.METER['credits']} | empty {toa.METER['empty']} | "
              f"per call {toa.METER['credits'] / max(toa.METER['calls'], 1):.1f}")
    toa.reset_cache()

    got = sum(1 for _i, x, s, r, lg, ta in T if toa_fair(x, s, r, lg, ta) is not None)
    print(f"plays from The Odds API with an exact-line alert-time price now: {got} of {len(T)}")
    if PILOT:
        st_ = bl.tb.dec(json.load(open(cl.STATE)))
        mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
        alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
        allfx = dict(alt, **(st_.get("fixtures") or {}))
        d = []
        for _i, x, s, r, lg, ta in O:
            if (toa.SPORT[lg], bucket(ta)) not in {k for k, _n in oplan}:
                continue
            a = toa_fair(x, s, r, lg, ta)
            b, _w = bl.fair_at_alert(x, s, r, allfx, mkmap)
            if a is not None and b is not None:
                d.append(100 * (a - b))
        if d:
            ab = sorted(abs(v) for v in d)
            print(f"ACCURACY vs OddsPapi at the same alert: pairs {len(d)} | median |diff| {st.median(ab):.2f} pts | "
                  f"within 1 pt {100 * sum(v <= 1 for v in ab) / len(ab):.0f}% | within 2 pts "
                  f"{100 * sum(v <= 2 for v in ab) / len(ab):.0f}% | mean signed {st.mean(d):+.3f}")
        else:
            print("ACCURACY: no comparable pairs in the pilot sample")
    return 0


if __name__ == "__main__":
    sys.exit(main())
