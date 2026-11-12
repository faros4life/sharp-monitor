#!/usr/bin/env python3
"""PINNACLE ALTERNATE-LINE PRICE BENCHMARK (Nov 12, 2026). Reads the OddsPapi history cache, writes nothing to it.

WHAT IS MEASURED. For one fixture, one market type (spreads / totals), one SIDE, at one sample time T: Pinnacle's
quoted price at line L and at a BETTER line L' for that side, both read from the same book at contemporaneous ticks.
The observation is the quoted price difference in cents. It is an independent quoted-price benchmark of what a
half point / full point costs at Pinnacle. It is NOT a de-vigged probability and NOT a push mass.

MATCHING. Same fixture, same market type, same side (same outcome id), same sample time T. Each line's quote is its
LAST tick at or before T; both ticks must be within MAX_TICK_AGE_MIN of T and within SYNC_MIN of each other.

MOVE CLASSES (reported separately; c = the bettor's cover threshold as in line_value, a lower c is a better line):
  half_half   both endpoints are half-integers, 1.0 apart   (-3.5 -> -2.5): neither pushes; no push mass needed
  half_whole  0.5 apart, one endpoint is a whole number     (-3.5 -> -3.0): the whole endpoint can push, so the
              quoted price embeds Pinnacle's settlement rule (spreads: refund stated on pinnacle.com; totals: NOT
              verified) - reported, and marked settlement-dependent
  whole_whole both whole, 1.0 apart (-3 -> -2): both endpoints can push; reported, marked settlement-dependent

CENTS CONVENTION. cents(-110) = -10, cents(+105) = +5, cents(-100) = cents(+100) = 0 (the usual ladder with no gap at
even money). diff = cents(better line) - cents(worse line); it is normally NEGATIVE (the better line costs more).
Tables print -diff, "cents paid for the better line".

OUTPUT. Counts, means, medians, spreads: no stakes, no keys. The per-observation CSV goes to an artifact (public
Pinnacle prices and fixture ids only). Leagues come from the cache: NBA, NFL, NCAAF, NHL, NCAAB (Top-100 games). MLB is
not in the cache; it is reported as a missing cell, never estimated.
"""
import csv
import gzip
import json
import os
import statistics as stx
import sys
from collections import defaultdict
from datetime import timedelta

import clv_ledger as cl
import hist_cache as hc

SAMPLE_H = (0, 3, 12, 24)        # hours before start: close, and three earlier reads
MAX_TICK_AGE_MIN = 120           # a line whose last tick is older than this at T is not "quoted at T"
SYNC_MIN = 30                    # the two lines' ticks must be this close to each other
SPORT_LG = {11: "NBA", 14: "NFL", 15: "NHL"}   # OddsPapi sport ids; NCAAF shares 14 with NFL, NCAAB is 11 - league comes from the fixture
OUTDIR = "summary"


def am(dec):
    return (dec - 1) * 100 if dec >= 2 else -100 / (dec - 1)


def cents(a):
    return a + 100 if a < 0 else a - 100


def cls(c0, c1):
    w0, w1 = abs(c0 - round(c0)) < 1e-9, abs(c1 - round(c1)) < 1e-9
    if not w0 and not w1:
        return "half_half"
    if w0 and w1:
        return "whole_whole"
    return "half_whole"


def sides_for(typ, outs):
    """[(side_label, outcome_id, sign)] where cover threshold c = sign * handicap (team1 spread: c = -h; team2: c = +h;
    over: c = +T; under: c = -T)."""
    nm = {v: k for k, v in outs.items()}
    if typ == "spreads":
        return [("team1", nm.get("1"), -1), ("team2", nm.get("2"), +1)]
    return [("over", nm.get("Over"), +1), ("under", nm.get("Under"), -1)]


def quotes_at(pm, mids, T):
    """{mid: {oid: (american, tick_time)}} for markets whose BOTH sides have a fresh last tick at T."""
    out = {}
    for mid in mids:
        tw = cl.two_way(pm, mid, T)
        if len(tw) < 2:
            continue
        if any((T - t[1]).total_seconds() > MAX_TICK_AGE_MIN * 60 for t in tw.values()):
            continue
        out[mid] = {oid: (am(d), ts) for oid, (d, ts, _lim) in tw.items()}
    return out


def observe(fid, lg, pm, mkmap, start):
    """All (league, typ, side, class, move, integer, c0, c1, cents0, cents1, diff, T, fid) observations for one fixture."""
    obs = []
    for typ in ("spreads", "totals"):
        mk = {mid: v for mid, v in mkmap.items() if v[1] == typ and mid in pm}
        if not mk:
            continue
        for hrs in SAMPLE_H:
            T = start - timedelta(hours=hrs)
            q = quotes_at(pm, list(mk), T)
            if len(q) < 2:
                continue
            # by side: {c: (american, tick_time, handicap)}
            by_side = defaultdict(dict)
            for mid, qq in q.items():
                _s, _t, hcap, outs = mk[mid]
                for label, oid, sign in sides_for(typ, outs):
                    if oid in qq:
                        by_side[label][round(sign * hcap, 2)] = qq[oid] + (hcap,)
            for label, cs in by_side.items():
                for c1 in cs:                       # c1 = better (lower) threshold
                    for step in (0.5, 1.0):
                        c0 = round(c1 + step, 2)    # c0 = worse line
                        if c0 not in cs:
                            continue
                        (a1, t1, h1), (a0, t0, h0) = cs[c1], cs[c0]
                        if abs((t1 - t0).total_seconds()) > SYNC_MIN * 60:
                            continue
                        k = cls(c0, c1)
                        if k == "half_half":
                            integer = int(round(c1 + 0.5))
                        else:
                            integer = int(round(c0)) if abs(c0 - round(c0)) < 1e-9 else int(round(c1))
                        obs.append({"lg": lg, "typ": typ, "side": label, "cls": k, "move": step, "k": abs(integer),
                                    "line_worse": h0, "line_better": h1, "am_worse": round(a0), "am_better": round(a1),
                                    "diff": round(cents(a1) - cents(a0), 1), "T_h": hrs, "fid": fid,
                                    "tick_worse": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "tick_better": t1.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return obs


def summarize(obs):
    """{(lg, typ, cls, move, k_or_*): stats}. k='*' pools every integer for that cell."""
    g = defaultdict(list)
    for o in obs:
        g[(o["lg"], o["typ"], o["cls"], o["move"], o["k"])].append(o)
        g[(o["lg"], o["typ"], o["cls"], o["move"], "*")].append(o)
    out = {}
    for key, rows in g.items():
        d = [-o["diff"] for o in rows]          # cents paid for the better line
        n, nf = len(d), len({o["fid"] for o in rows})
        sd = stx.pstdev(d) if n > 1 else 0.0
        out[key] = {"n_obs": n, "n_fixtures": nf, "mean": round(stx.mean(d), 2), "median": round(stx.median(d), 2),
                    "sd": round(sd, 2), "se": round(sd / n ** 0.5, 2) if n else None,
                    "p10": round(sorted(d)[int(0.1 * (n - 1))], 1), "p90": round(sorted(d)[int(0.9 * (n - 1))], 1)}
    return out


def render(summ, leagues_in_cache, fixtures_seen, fixtures_with_pin):
    L = ["PINNACLE ALTERNATE-LINE BENCHMARK (quoted price differences, cents paid for the BETTER line; not de-vigged)",
         f"  fixtures in state: {fixtures_seen}, with a Pinnacle history file: {fixtures_with_pin}",
         f"  leagues in cache: {', '.join(sorted(leagues_in_cache)) or 'none'}; MLB: NOT IN CACHE (missing cell)",
         "  class: half_half = no push either end | half_whole / whole_whole = whole endpoint, settlement-dependent",
         "  se = ONE standard error of the mean; p10/p90 = spread of observations; n_obs counts side x time samples, n_fixtures counts games",
         "  league  market   class        move  k    n_obs  n_fix  mean   median  sd    se    p10   p90"]
    for key in sorted(summ, key=lambda k: (k[0], k[1], k[2], k[3], str(k[4]) if k[4] == "*" else f"{k[4]:03d}")):
        lg, typ, k_, mv, k = key
        s = summ[key]
        L.append(f"  {lg:<6}  {typ:<8} {k_:<12} {mv:<4} {str(k):<4} {s['n_obs']:<6} {s['n_fixtures']:<5} "
                 f"{s['mean']:<6} {s['median']:<7} {s['sd']:<5} {str(s['se']):<5} {s['p10']:<5} {s['p90']}")
    missing = []
    for lg in ("NBA", "NFL", "NCAAF", "NHL", "NCAAB", "MLB"):
        for typ in ("spreads", "totals"):
            if not any(k[0] == lg and k[1] == typ and k[2] == "half_half" and k[4] == "*" for k in summ):
                missing.append(f"{lg} {typ}" + (" (league not in cache)" if lg not in leagues_in_cache else " (no contemporaneous alternate pairs found)"))
    L.append("  MISSING CELLS (half_half): " + ("; ".join(missing) or "none"))
    return "\n".join(L)


def main():
    st = cl.tb.dec(json.load(open(cl.STATE)))
    mkmap = json.load(open("clv/markets.json"))["m"]
    fx = st.get("fixtures") or {}
    obs, lgs, with_pin = [], set(), 0
    for fid, f in fx.items():
        p = hc._path(fid, "pinnacle")
        if not os.path.exists(p):
            continue
        start = cl.tp(f.get("start"))
        if not start:
            continue
        try:
            pm = (json.load(gzip.open(p, "rt")) or {}).get("markets") or {}
        except Exception:
            continue
        with_pin += 1
        lgs.add(f.get("lg"))
        obs += observe(fid, f.get("lg"), pm, mkmap, start)
    summ = summarize(obs)
    os.makedirs(OUTDIR, exist_ok=True)
    print(render(summ, lgs, len(fx), with_pin))
    with open(os.path.join(OUTDIR, "pin_alt_obs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(obs[0]) if obs else ["lg"])
        w.writeheader()
        w.writerows(obs)
    json.dump({str(k): v for k, v in summ.items()}, open(os.path.join(OUTDIR, "pin_alt_summary.json"), "w"), indent=1)
    print(f"  observations written: {len(obs)}")


if __name__ == "__main__":
    sys.exit(main())
