#!/usr/bin/env python3
"""HISTORICAL PINNACLE CLV RECOVERY FROM THE ODDS API (Peter, Nov 26 2026: "Recover ALL missing historical CLV ...
Use up to 2M credits before December 1 ... exact-line Pinnacle no-vig closes ... no estimated CLV").

Fills the shared store (toa.py) for every graded observation the certifier rejects as MISSING_HISTORY or no-fixture,
then re-certifies through the SAME waterfall (clv_obs_audit.classify). Nothing published is written here; the
certifier and the reports pick the store up on their next run.

  pass A  one featured snapshot per (sport, listed start)       10 credits x 3 markets = 30 per call
  pass B  the event's own commence time, where our listed start was late or early
  pass C  alternate spreads/totals for a matched event whose exact line was not Pinnacle's main
Order: tier 1 bot/sent plays and lane entries, tier 2 sharp alerts, tier 3 liquidity research. A snapshot serves every
game of its sport at that time, so the tiers only matter if the budget binds.

Budget is enforced BEFORE each call (TOA_BUDGET, default 2,000,000). TOA_DRY=1 counts the calls and credits only.
Log: counts only.
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
import tracker_build as tb

BUDGET = int(os.environ.get("TOA_BUDGET", "") or "2000000")
DRY = (os.environ.get("TOA_DRY") or "").strip().lower() in ("1", "yes", "on", "true")
FEAT_COST, ALT_COST = 30, 20
GAP = ("MISSING_HISTORY", "FIXTURE_OR_IDENTITY")


def tier(i, x):
    if i.startswith("lane:") or (isinstance(x, dict) and (x.get("sent_to_phone") or x.get("hr1_pushed"))):
        return 1
    return 2 if i.startswith("sharp|") else 3


def run_classify(items, ctx):
    out = {}
    for i, x, src, pre in items:
        if pre:
            out[i] = ("PRE", pre)
            continue
        out[i] = oa.classify(x, src, *ctx)
    return out


def summary(items, res):
    c = collections.Counter()
    for i, *_ in items:
        pop = i.split("|")[0]
        cls, d = res[i]
        ok = cls == "VERIFIED_PINNACLE" and isinstance(d, dict) and str(d.get("how")) in pc.CERT_HOW
        c[(pop, "graded")] += 1
        c[(pop, "certified")] += ok
        c[(pop, "via_toa")] += bool(ok and d.get("src") == toa.SRC)
    return c


def spend_ok(cost):
    return toa.METER["credits"] + cost <= BUDGET


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
    ctx = (fxs, alt, allfx, mkmap)
    src_of = {i: (x, s) for i, x, s, _p in items}

    before = run_classify(items, ctx)
    b_sum = summary(items, before)

    # ---------------- pass A: featured snapshot at each gap row's listed start
    need = {}
    nostart = 0
    for i, x, s, pre in items:
        cls, _d = before[i]
        if cls not in GAP:
            continue
        snap = oa.snap_for(x, s)
        lg = snap.get("league") or x.get("sport") or x.get("league")
        sp, t0 = toa.SPORT.get(lg), cl.tp(snap.get("game_start"))
        if not sp or not t0:
            nostart += 1
            continue
        k = (sp, t0.replace(second=0, microsecond=0))
        need[k] = min(need.get(k, 9), tier(i, x))
    order = sorted(need, key=lambda k: (need[k], k[1]))
    todo = [k for k in order if not toa.have_snap(*k)]
    print(f"gap rows {sum(1 for v in before.values() if v[0] in GAP)} | without a usable league/start {nostart} | "
          f"snapshots needed {len(need)} (already stored {len(need) - len(todo)}) | "
          f"by tier {dict(collections.Counter(need[k] for k in todo))} | est credits {len(todo) * FEAT_COST}")
    if DRY:
        print(f"DRY RUN: pass A would cost ~{len(todo) * FEAT_COST} credits; passes B/C are counted after A runs.")
        return 0
    errs = 0
    for k in todo:
        if not spend_ok(FEAT_COST):
            print("budget reached in pass A - stopping")
            break
        try:
            toa.fetch_snapshot(*k)
        except Exception as ex:
            errs += 1
            if errs <= 3:
                print(f"pass A fetch error: {type(ex).__name__}")
            if errs >= 25:
                print("pass A: 25 errors - stopping")
                break
    toa.reset_cache()

    # ---------------- pass B: event commence time, where our listed start missed the pre-start snapshot
    mid = run_classify(items, ctx)
    needB, needC = set(), set()
    for i, (cls, _d) in mid.items():
        if cls not in GAP:
            continue
        x, s = src_of[i]
        snap = oa.snap_for(x, s)
        lg = snap.get("league") or x.get("sport") or x.get("league")
        if lg not in toa.SPORT:
            continue
        fx = toa.fixtures(lg)
        fid, _n = fxm.ordered_match(snap, fx, cl.tp)
        if not fid:
            continue
        f = fx[fid]
        c, why = toa.close(snap, f, fid, lg, cl.parsed, fxm.resolve_side, cl.which_team, cl.novig_p, cl.FRESH_MIN)
        if c:
            continue
        t0 = cl.tp(f["start"])
        if "not at the close" in why or "no stored Pinnacle snapshot" in why:
            needB.add((toa.SPORT[lg], t0))
        elif "exact line" in why:
            needC.add((toa.SPORT[lg], fid.split(":", 1)[1], t0))
    print(f"pass B (commence-time snapshots) {len(needB)} | pass C (alternate lines) {len(needC)}")
    for k in sorted(needB, key=lambda k: k[1]):
        if not spend_ok(FEAT_COST):
            print("budget reached in pass B - stopping")
            break
        try:
            toa.fetch_snapshot(*k)
        except Exception:
            errs += 1
    for sp, eid, t0 in sorted(needC, key=lambda k: k[2]):
        if not spend_ok(ALT_COST):
            print("budget reached in pass C - stopping")
            break
        try:
            toa.fetch_alts(sp, eid, t0)
        except Exception:
            errs += 1
    toa.reset_cache()

    after = run_classify(items, ctx)
    a_sum = summary(items, after)
    rec = sum(a_sum[(p, "via_toa")] for p in {k[0] for k in a_sum})
    print("BEFORE -> AFTER certified (counts only):")
    for p in sorted({k[0] for k in a_sum}):
        print(f"  {p:<16} graded {a_sum[(p, 'graded')]:>5} | certified {b_sum[(p, 'certified')]:>5} -> "
              f"{a_sum[(p, 'certified')]:>5} (via The Odds API {a_sum[(p, 'via_toa')]})")
    print("still unresolved by class:", dict(collections.Counter(
        v[0] for v in after.values() if not (v[0] == "VERIFIED_PINNACLE" and str(v[1].get('how')) in pc.CERT_HOW))))
    print(f"fetch errors {errs} | recovered closes {rec} | credits {toa.METER['credits']} | "
          f"cost per recovered close {toa.METER['credits'] / rec:.1f}" if rec else
          f"fetch errors {errs} | recovered closes 0 | credits {toa.METER['credits']}")
    print(toa.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
