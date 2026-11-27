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


def fills_pass():
    """Nov 26 (Peter): actual bot fills first. Every graded bot fill without a stored close gets its snapshot; the
    fill's own after-fee price is applied later by executed_clv, exactly as before. Returns (fills, resolved)."""
    import executed_clv as xc
    import live_ledger as ll
    _src = ll.load()   # Nov 27: include the bot fills the ledger proves (24 ProphetX fills are tagged "Peter")
    xc.ACCT = ll.account(*_src, ll.feed_alerts()) if _src else None
    xc.LEDGER_LANE = ll.lane_of_rows(xc.ACCT) if xc.ACCT else {}
    F, _n = xc.fill_rows()

    def q_of(b):
        g = b.get("game_start") or b.get("settled") or b.get("placed") or b.get("first_seen")
        return {"bet": b.get("bet"), "league": b.get("league"), "game": b.get("game"), "teams": b.get("teams"),
                "game_start": g}, bool(b.get("game_start"))

    for _round in range(3):
        need_f, need_a = set(), set()
        for b in F:
            q, given = q_of(b)
            lg = q["league"]
            if lg not in toa.SPORT:
                continue
            c, why = toa.close_for_row(q, lg)
            if c:
                continue
            t0 = cl.tp(q["game_start"])
            if not t0:
                continue
            if "no unique event" in str(why) or "no stored" in str(why):
                # no listed start: the settle time is after the game - look 3 hours earlier for the event
                need_f.add((toa.SPORT[lg], (t0 if given else t0 - timedelta(hours=3)).replace(second=0, microsecond=0)))
                continue
            fx = toa.fixtures(lg)
            fid, _ = fxm.ordered_match(dict(q, league=lg), fx, cl.tp)
            if not fid:
                continue
            ts = cl.tp(fx[fid]["start"])
            if "not at the close" in str(why):
                need_f.add((toa.SPORT[lg], ts))
            elif "exact line" in str(why):
                need_a.add((toa.SPORT[lg], fid.split(":", 1)[1], ts))
        need_f = {k for k in need_f if not toa.have_snap(*k)}
        need_a = {k for k in need_a if not os.path.exists(toa._path(k[0], toa.alt_name(k[1], k[2])))}
        print(f"fills round {_round + 1}: snapshots {len(need_f)} | alternate lines {len(need_a)}")
        if not need_f and not need_a:
            break
        for k in need_f:
            if spend_ok(FEAT_COST):
                try:
                    toa.fetch_snapshot(*k)
                except Exception:
                    ERRS[0] += 1
        for k in need_a:
            if spend_ok(ALT_COST):
                try:
                    toa.fetch_alts(*k)
                except Exception:
                    ERRS[0] += 1
        toa.reset_cache()
    res = sum(1 for b in F if q_of(b)[0]["league"] in toa.SPORT and toa.close_for_row(q_of(b)[0], q_of(b)[0]["league"])[0])
    print(f"bot fills: {len(F)} graded | with a stored exact-line close {res}")
    return len(F), res


def diag():
    """Unmatched gap rows: the row's team text and listed start next to the closest stored events (names and times
    only - no prices, no money). Read-only, zero credits. Nov 26: before touching matching, see why it fails."""
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
    kinds = collections.Counter()
    shown = 0
    for i, x, s, pre in items:
        if pre:
            continue
        cls, _d = oa.classify(x, s, fxs, alt, allfx, mkmap)
        if cls not in GAP:
            continue
        snap = oa.snap_for(x, s)
        lg = snap.get("league") or x.get("sport") or x.get("league")
        if lg not in toa.SPORT:
            continue
        fx = toa.fixtures(lg)
        fid, note = fxm.ordered_match(snap, fx, cl.tp)
        if fid:
            continue
        t0 = cl.tp(snap.get("game_start"))
        near = sorted([(abs((cl.tp(f["start"]) - t0).total_seconds()), f) for f in fx.values()
                       if t0 and cl.tp(f["start"]) and abs((cl.tp(f["start"]) - t0).total_seconds()) < 6 * 3600],
                      key=lambda z: z[0])
        k = "AMBIGUOUS" if "AMBIGUOUS" in note or "ambiguous" in note else ("no event within 6h" if not near
                                                                             else "names do not map")
        kinds[(lg, k)] += 1
        if shown < 40 and k != "AMBIGUOUS":
            shown += 1
            tm = [t.get("name") for t in (snap.get("teams") or [])]
            print(f"  {lg} | row: {tm or snap.get('game')} @ {snap.get('game_start')} | "
                  f"nearest: {[(f['p2'] + ' @ ' + f['p1'], f['start']) for _d, f in near[:2]]}")
    print("unmatched by league and kind:", dict(kinds))
    return 0


def main():
    if (os.environ.get("TOA_FILLS") or "1") == "1" and not DRY:
        fills_pass()
    if (os.environ.get("TOA_DIAG") or "") == "1":
        return diag()
    if (os.environ.get("TOA_ONLY_FILLS") or "") == "1":
        print(toa.report())
        return 0
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
    for k in todo:
        if not spend_ok(FEAT_COST):
            print("budget reached in pass A - stopping")
            break
        try:
            toa.fetch_snapshot(*k)
        except Exception as ex:
            ERRS[0] += 1
            if ERRS[0] <= 3:
                print(f"pass A fetch error: {type(ex).__name__}")
            if ERRS[0] >= 25:
                print("pass A: 25 errors - stopping")
                break
    toa.reset_cache()

    # ---------------- pass B/C, repeated: a row matched only after a pass-B snapshot needs its own pass-C read
    for _round in range(3):
        if not _pass_bc(items, ctx, src_of):
            break
    toa.reset_cache()
    after = run_classify(items, ctx)
    _finish(items, after, b_sum)
    return 0


def _why(items, res, src_of):
    """Why each still-open gap row failed on the store, by first reason word (counts only)."""
    c = collections.Counter()
    for i, (cls, _d) in res.items():
        if cls not in GAP:
            continue
        x, s = src_of[i]
        snap = oa.snap_for(x, s)
        lg = snap.get("league") or x.get("sport") or x.get("league")
        if lg not in toa.SPORT:
            c["league not on The Odds API"] += 1
            continue
        fx = toa.fixtures(lg)
        fid, n = fxm.ordered_match(snap, fx, cl.tp)
        if not fid:
            c["no unique event: " + str(n)[:40]] += 1
            continue
        _c, why = toa.close(snap, fx[fid], fid, lg, cl.parsed, fxm.resolve_side, cl.which_team, cl.novig_p,
                            cl.FRESH_MIN)
        c[str(why)[:70]] += 1
    return c


def _pass_bc(items, ctx, src_of):
    """One round of pass B and pass C. Returns the number of calls made."""
    made = 0
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
    needB = {k for k in needB if not toa.have_snap(*k)}
    needC = {k for k in needC if not os.path.exists(toa._path(k[0], toa.alt_name(k[1], k[2])))}
    print(f"pass B (commence-time snapshots) {len(needB)} | pass C (alternate lines) {len(needC)}")
    for k in sorted(needB, key=lambda k: k[1]):
        if not spend_ok(FEAT_COST):
            print("budget reached in pass B - stopping")
            break
        try:
            toa.fetch_snapshot(*k)
            made += 1
        except Exception:
            ERRS[0] += 1
    for sp, eid, t0 in sorted(needC, key=lambda k: k[2]):
        if not spend_ok(ALT_COST):
            print("budget reached in pass C - stopping")
            break
        try:
            toa.fetch_alts(sp, eid, t0)
            made += 1
        except Exception:
            ERRS[0] += 1
    toa.reset_cache()
    return made


ERRS = [0]


def _finish(items, after, b_sum):
    src_of = {i: (x, s) for i, x, s, _p in items}
    errs = ERRS[0]
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
    print("open gap rows on the store, by reason:")
    for k, v in _why(items, after, src_of).most_common(12):
        print(f"  {v:>5}  {k}")


if __name__ == "__main__":
    sys.exit(main())
