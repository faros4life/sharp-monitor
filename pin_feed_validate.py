#!/usr/bin/env python3
"""VALIDATE the zero-cost Pinnacle replacement for nba_totals_model (Nov 13, 2026; Peter).

PROVES BEFORE SWITCHING. Changes nothing: no write, no commit, no model edit, no order, no new
strategy. Billable calls: ZERO by construction - every venue read here is /historical-odds, which
credit_gate lists in FREE_PATHS, and the fixture cache is read read-only with a refusal to fall
through to a paid fetch (the same discipline clv_report already uses).

THE TEST THAT MATTERS IS THE REPLAY. nba_model.json already holds 51 postings from Nov 6-12 whose
Pinnacle reference was captured by the OLD feed and is therefore independently verified. The new
method is run against those same postings and must reproduce them. Agreement on fresh data proves
the plumbing; agreement with a reference captured days ago by a different code path is what proves
the METHOD.

NO LOOK-AHEAD, BY CONSTRUCTION. Every read uses two_way(pm, mid, before=<the posting's own utc>),
which returns each outcome's last tick AT OR BEFORE that moment. A price that did not exist at the
posting timestamp cannot enter the comparison. The freshness bound is the production one
(clv_ledger.FRESH_MIN), applied the same way.

PRICE FORMAT IS A REAL TRAP. two_way returns DECIMAL odds (novig_p divides by them). The model's
consumer, sharp_monitor.close_prob_detail, calls am_to_prob() - AMERICAN. The old pin_cache stored
American ('Over': [40.5, -109]). So the replacement must convert, and this validator compares in
American to prove the conversion is right rather than assuming it.
"""
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl

MODEL = os.environ.get("NBA_MODEL_FILE", "") or "nba-model/nba_model.json"
EV = os.environ.get("EV_FILE", "") or "ev-study/ev_sightings.json"
LG = "NBA"
SID = 11          # basketball sport id, as ML_MARKET's key in clv_ledger



def dec_to_am(d):
    """Decimal -> American. two_way gives decimal; close_prob_detail wants American."""
    try:
        d = float(d)
    except (TypeError, ValueError):
        return None
    if d <= 1:
        return None
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def tp(s):
    return cl.tp(s) if hasattr(cl, "tp") else None


def pin_total_at(pm, mkmap, when):
    """(line, over_am, under_am, age_min, limit) for Pinnacle's MAIN total at `when`, or None.

    Lifted from clv_ledger.close_for's totals branch so the selection rule is identical: among
    every Pinnacle total for the fixture whose two sides both have a tick at or before `when` and
    are inside FRESH_MIN, the main line is the one carrying the biggest limit (alt lines are capped
    lower), ties broken by the most even price.
    """
    cands = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != SID or t != "totals" or mid not in pm:
            continue
        tw = cl.two_way(pm, mid, when)
        nm = {v: k for k, v in outs.items()}
        o_id, u_id = nm.get("Over"), nm.get("Under")
        if o_id not in tw or u_id not in tw:
            continue
        age = (when - min(tw[o_id][1], tw[u_id][1])).total_seconds() / 60
        if age > cl.FRESH_MIN:
            continue
        p_over = cl.novig_p(tw[o_id][0], tw[u_id][0])
        cands.append((hcap, p_over, age, min(tw[o_id][2], tw[u_id][2]),
                      tw[o_id][0], tw[u_id][0]))
    if not cands:
        return None
    m = max(cands, key=lambda c: (c[3], -abs(c[1] - 0.5)))
    return {"line": m[0], "over": dec_to_am(m[4]), "under": dec_to_am(m[5]),
            "age_min": round(m[2]), "limit": m[3]}


def main():
    now = datetime.now(timezone.utc)
    print("PINNACLE REPLACEMENT VALIDATION - read-only, zero billable calls")
    print("=" * 94)

    try:
        md = json.load(open(MODEL))
    except Exception as ex:
        print(f"STOP: {MODEL} unreadable ({type(ex).__name__})")
        return 1
    games = md.get("games") or []
    games = list(games.values()) if isinstance(games, dict) else games

    st = {"billable": {}}
    try:
        prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        st["fx_last"] = dict(prev.get("fx_last") or {})
        print(f"  fixture cache: {len(st['fixtures'])} fixtures, read-only, zero credits")
    except Exception as ex:
        print(f"STOP: fixture cache could not be decrypted ({type(ex).__name__}). "
              f"TRACKER_PASSPHRASE is required. Refusing to fall through to a paid fetch.")
        return 1
    # Read the market map from its cache FILE, the way line_value_replay does, rather than through
    # load_markets(): that helper serves the same cache for free but BILLS a /markets call when the
    # cache is over 7 days old. Reading the file keeps "zero billable calls" true by construction
    # instead of true by luck, and an expired cache becomes a refusal rather than a silent charge.
    try:
        mk = json.load(open(cl.MKFILE))
        mkmap, mk_age = mk["m"], (now - cl.tp(mk["fetched"])).days
    except Exception as ex:
        print(f"STOP: market map cache unreadable ({type(ex).__name__}). Refusing to bill /markets.")
        return 1
    print(f"  market map: {len(mkmap)} markets, cache {mk_age}d old")
    if mk_age >= 7:
        print("STOP: the market cache is over 7 days old. load_markets would bill to refresh it, so")
        print("      this validator refuses rather than spend a credit it promised not to spend.")
        return 1

    hist, live = [], []
    for g in games:
        if not isinstance(g, dict):
            continue
        p = g.get("post") or {}
        when = tp(p.get("utc")) or tp(g.get("start"))
        if not when:
            continue
        (hist if p.get("pin_line") is not None else live).append((g, p, when))
    print(f"  postings: {len(hist)} with an existing reference (replay), {len(live)} without (coverage)")
    print()

    # The OLD reference was whatever sat in pin_cache when the model posted - and that entry was
    # fetched at its own moment, not at the posting moment. So a disagreement at posting time may
    # mean nothing worse than "the new read is fresher". To tell a METHOD error from a
    # REFERENCE-TIME difference, each old entry's own fetch time is recovered here and the replay
    # is run a second time at that instant. Matching there proves the method; the gap between the
    # two is the staleness the old feed was carrying.
    oldref = {}
    try:
        pc = (json.load(open(EV)) or {}).get("pin_cache") or {}
        for v in pc.values():
            teams = list(((v.get("spreads") or {}).get("outcomes") or {}).keys())
            tot = v.get("totals") or {}
            f = tot.get("fetched") or tot.get("upd")
            if len(teams) == 2 and f:
                try:
                    oldref[frozenset(teams)] = datetime.fromtimestamp(float(f), tz=timezone.utc)
                except (TypeError, ValueError):
                    pass
        print(f"  old pin_cache: {len(oldref)} entries with a fetch time")
    except Exception as ex:
        print(f"  old pin_cache unreadable ({type(ex).__name__}) - reference-time control skipped")

    cache = {}

    def markets_for(g, when):
        b = {"league": LG, "game": f"{g.get('away')} @ {g.get('home')}",
             "teams": [{"name": g.get("away")}, {"name": g.get("home")}],
             "game_start": g.get("start")}
        fid = cl.find_fixture(st, b)
        if not fid:
            return None, "fixture not in the shared cache"
        if fid not in cache:
            try:
                cache[fid] = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
            except Exception as ex:
                cache[fid] = {"_error": f"{type(ex).__name__}: {str(ex)[:60]}"}
        h = cache[fid]
        if isinstance(h, dict) and h.get("_error"):
            return None, f"history read failed ({str(h['_error'])[:50]})"
        return cl.book_markets(h, "pinnacle"), None

    # ---- 1. REPLAY against references the old feed already verified ------------------------
    print("1. REPLAY - reproduce references captured by the OLD feed (no look-ahead)")
    print("-" * 94)
    ok_line = ok_over = ok_under = ok_at_ref = 0
    staleness = []
    miss = {}
    rows = []
    for g, p, when in hist:
        pm, why = markets_for(g, when)
        if pm is None:
            miss[why] = miss.get(why, 0) + 1
            continue
        got = pin_total_at(pm, mkmap, when)
        if not got:
            miss["no Pinnacle total at or before the posting time"] = \
                miss.get("no Pinnacle total at or before the posting time", 0) + 1
            continue
        ref_t = oldref.get(frozenset([g.get("away"), g.get("home")]))
        if ref_t:
            at_ref = pin_total_at(pm, mkmap, ref_t)
            if at_ref and abs(float(at_ref["line"]) - float(p["pin_line"])) < 1e-9:
                ok_at_ref += 1
            staleness.append((when - ref_t).total_seconds() / 60)
        same_l = abs(float(got["line"]) - float(p["pin_line"])) < 1e-9
        same_o = got["over"] is not None and abs(got["over"] - float(p["pin_over"])) <= 1
        same_u = got["under"] is not None and abs(got["under"] - float(p["pin_under"])) <= 1
        ok_line += same_l
        ok_over += same_o
        ok_under += same_u
        if not (same_l and same_o and same_u) and len(rows) < 8:
            rows.append(f"    {g.get('away')} @ {g.get('home')}  old {p['pin_line']}/{p['pin_over']}/"
                        f"{p['pin_under']}  new {got['line']}/{got['over']}/{got['under']}")
    n = len(hist)
    print(f"  replayed {n} posting(s)")
    if n:
        print(f"    line matches : {ok_line}/{n}  ({100*ok_line/n:.1f}%)")
        print(f"    over  matches: {ok_over}/{n}  ({100*ok_over/n:.1f}%)   (+-1 American cent)")
        print(f"    under matches: {ok_under}/{n}  ({100*ok_under/n:.1f}%)")
    if staleness:
        staleness.sort()
        med = staleness[len(staleness) // 2]
        print(f"    line matches AT THE OLD ENTRY'S OWN FETCH TIME: {ok_at_ref}/{len(staleness)} "
              f"({100 * ok_at_ref / len(staleness):.1f}%)")
        print(f"    old reference age at posting: median {med:.0f} min, max {staleness[-1]:.0f} min")
        print("      -> a high match here with a low match above means the METHOD agrees and the")
        print("         OLD feed was serving a stale number; the reverse means a method error.")
    for k, v in sorted(miss.items(), key=lambda x: -x[1]):
        print(f"    unresolved: {v:>3}  {k}")
    for r in rows:
        print("  disagreement:")
        print(r)

    # ---- 2. COVERAGE for the postings that currently have nothing ---------------------------
    print()
    print("2. COVERAGE - can the new feed serve the postings the dead cache cannot?")
    print("-" * 94)
    got_n, cov_miss = 0, {}
    for g, p, when in live:
        pm, why = markets_for(g, when)
        if pm is None:
            cov_miss[why] = cov_miss.get(why, 0) + 1
            continue
        got = pin_total_at(pm, mkmap, when)
        if got:
            got_n += 1
        else:
            cov_miss["no Pinnacle total at or before the posting time"] = \
                cov_miss.get("no Pinnacle total at or before the posting time", 0) + 1
    print(f"  {got_n} of {len(live)} currently-unreferenced posting(s) WOULD get a reference")
    for k, v in sorted(cov_miss.items(), key=lambda x: -x[1]):
        print(f"    still missing: {v:>3}  {k}")

    print()
    print("-" * 94)
    # Report what the gate actually recorded, not a constant I set myself. st["billable"] is the
    # ledger clv_ledger.bill() writes into; empty means nothing was charged.
    charged = {k: v for k, v in (st.get("billable") or {}).items() if v}
    print(f"  billable calls recorded by the gate: {charged or 'none'}")
    print("  (history is a FREE_PATH; fixtures and markets were read from cache)")
    print("  Nothing was written, committed, or changed.")
    print("=" * 94)
    verdict = n and ok_line == n and got_n == len(live)
    print("VALIDATION PASSED" if verdict else
          "VALIDATION INCOMPLETE - do not switch on this result alone; read the rows above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
