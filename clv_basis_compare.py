#!/usr/bin/env python3
"""
SCORECARD BASIS RECONCILIATION - side by side, READ-ONLY (Peter, Nov 14 2026).

Peter: "Before switching the scorecard, run both methods side by side and show every discrepancy,
including changes to CLV, first-half/second-half results and PASS/FAIL status." And: "Do not
overwrite previously published results."

So nothing switches here. The scorecard's OWN rows, its OWN registered slices and its OWN
acceptance rules from SCORECARD.md are used unchanged; only the CLV column is computed twice:

  OLD  the stored close the alert pipeline wrote (alerts.json close_fair_prob, liquidity
       close_price) x the quoted price after fees. This is what the published scorecard used.
  NEW  clv_basis: a verified same-line Pinnacle no-vig close from the history we hold, x the same
       quoted price after fees through the same fee model.

The ENTRY price is identical in both columns on purpose. These observations are sightings with a
quoted price, not fills, so clv_basis.after_fee_from_quote is the entry "appropriate to each
observation" in both - which isolates the change to the thing that actually differed, the close.
Changing two inputs at once would make every discrepancy uninterpretable.

ACCEPTANCE RULES, quoted from SCORECARD.md and NOT modified:
  CLEAR FAIL     - realized-unit CI excludes zero on the negative side, or a precise and
                   representative certified CLV CI does.
  POTENTIAL PASS - realized-unit CI excludes zero on the positive side with actual fills,
                   certified CLV >= 0 and precise and representative, both chronological halves
                   positive, multiplicity survived, rule pre-registered.
Only the first two clauses of POTENTIAL PASS can be evaluated mechanically here; "multiplicity
survived" and "pre-registered" are Peter's judgements and are printed as UNEVALUATED rather than
assumed. Nothing is promoted or failed by this script - it reports.

READ-ONLY: no write to any published file, no fetch, no OddsPapi call, no IMAP. Pinnacle history
comes from the hcache files already on disk.
"""
import collections
import glob
import gzip
import json
import os
import statistics as st
import sys
from datetime import datetime, timezone

import clv_basis as cb
import clv_ledger as cl
import clv_std as cs
import fixture_match as fxm
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
SHARP = os.environ.get("SC_SHARP", "") or "alerts.json"
LIQ = os.environ.get("SC_LIQ", "") or "liquidity/alerts.json"
MKFILE = "clv/markets.json"
OUT = "audit/scorecard_reconciled.txt"
L = []
_PIN = {}


def say(t=""):
    L.append(t)
    print(t, flush=True)


def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return []
    if isinstance(d, dict):
        for k in ("alerts", "rows", "sightings"):
            if isinstance(d.get(k), list):
                return d[k]
        return []
    return d if isinstance(d, list) else []


def cached_pin(fid):
    if fid in _PIN:
        return _PIN[fid]
    p = os.path.join(HC, f"{fid}__pinnacle.json.gz")
    d = None
    if os.path.exists(p):
        try:
            with gzip.open(p, "rt") as fh:
                d = json.load(fh)
        except Exception:
            d = None
    _PIN[fid] = {"bookmakers": {"pinnacle": d}} if d is not None else None
    return _PIN[fid]


def ci(xs):
    """(lo, hi) 95% CI of the mean, or None when the sample cannot support one."""
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = st.mean(xs)
    se = st.stdev(xs) / len(xs) ** 0.5
    return (m - 1.96 * se, m + 1.96 * se)


def units_of(rows):
    t = 0.0
    for r in rows:
        am, res = r.get("am"), r.get("res")
        if am is None or res == "P":
            continue
        t += (am / 100 if am > 0 else 100 / abs(am)) if res == "W" else -1.0
    return t


def verdict(rows, clv_key):
    """SCORECARD.md's rules, applied unchanged. Returns (label, why)."""
    use = [r for r in rows if r.get(clv_key) is not None]
    if not use:
        return "NO VERDICT", "no usable observation"
    risk = [r for r in use if r.get("res") in ("W", "L")]
    uci = ci([(r["am"] / 100 if r["am"] > 0 else 100 / abs(r["am"])) if r["res"] == "W" else -1.0
              for r in risk if r.get("am")]) if risk else None
    cci = ci([r[clv_key] for r in use])
    if uci and uci[1] < 0:
        return "CLEAR FAIL", f"realized-unit CI [{uci[0]:+.2f}, {uci[1]:+.2f}]u excludes zero, negative"
    if cci and cci[1] < 0:
        return "CLEAR FAIL", f"certified CLV CI [{cci[0]:+.2f}, {cci[1]:+.2f}]% excludes zero, negative"
    use.sort(key=lambda r: r.get("day") or "")
    half = len(use) // 2
    h1 = st.mean([r[clv_key] for r in use[:half]]) if half else None
    h2 = st.mean([r[clv_key] for r in use[half:]]) if use[half:] else None
    pos_units = bool(uci and uci[0] > 0)
    if pos_units and (cci and st.mean([r[clv_key] for r in use]) >= 0) and \
            h1 is not None and h2 is not None and h1 > 0 and h2 > 0:
        return "POTENTIAL PASS (partly unevaluated)", \
               "unit CI positive, CLV >= 0, both halves positive; multiplicity and pre-registration UNEVALUATED"
    return "CONTINUES", "neither clear-fail clause met, and the pass clauses are not all satisfied"


def main():
    now = datetime.now(timezone.utc)
    say("SCORECARD BASIS RECONCILIATION - side by side. READ-ONLY, nothing switched or overwritten.")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say(f"NEW basis: {cb.stamp()}")
    say("OLD basis: the close the alert pipeline stored (alerts.json close_fair_prob / liquidity")
    say("           close_price) x the same quoted price after fees. The entry price is IDENTICAL")
    say("           in both columns, so every discrepancy below is the CLOSE and nothing else.")
    say("Registered strategies, selection criteria, observations and acceptance thresholds are")
    say("unchanged - only the CLV column is recomputed.")
    say("=" * 108)

    try:
        state = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__}) - no NEW column is possible")
        return 1
    fx_state = state.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {MKFILE} unreadable ({type(e).__name__})")
        return 1
    say(f"  fixtures: {len(fx_state)} in state + {len(alt)} from other stores | "
        f"market ids {len(mkmap)} | hcache files {len(os.listdir(HC)) if os.path.isdir(HC) else 0}")

    rows, gaps = [], collections.Counter()

    def add(x, src, day, game, bet, lg, am, book, res, old_close, line_beat=None):
        snap = {"league": lg, "game": game, "bet": bet, "book": book,
                "game_start": x.get("start_utc") or x.get("game_start") or x.get("commence_time")}
        entry = cb.after_fee_from_quote(am, book, cl.am_to_dec, league=lg)
        old = cb.clv(old_close, entry)
        fid, where, note = cb.resolve_fixture(snap, fx_state, alt, cl.find_fixture,
                                              fxm.ordered_match, cl.tp)
        new, why = None, None
        if not fid:
            gaps[f"no fixture ({note[:44]})"] += 1
            why = "no fixture"
        else:
            f = fx_state.get(fid) or alt.get(fid) or {}
            h = cached_pin(fid)
            if h is None:
                gaps["no cached Pinnacle history for the fixture"] += 1
                why = "no history"
            else:
                p, ev = cb.pinnacle_no_vig_close(
                    f, snap, mkmap, cl.book_markets(h, "pinnacle"), cl.parsed, cl.which_team,
                    cl.two_way, cl.novig_p, cl.SPORT, cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
                if p is None:
                    gaps[str(ev)[:52]] += 1
                    why = str(ev)[:40]
                else:
                    new = cb.clv(p, entry)
                    new = None if new is None else 100 * new
        rows.append({"src": src, "day": day, "game": game, "bet": bet, "lg": lg, "am": am,
                     "book": book, "res": res, "old": None if old is None else 100 * old,
                     "new": new, "why": why, "fid": fid, "where": where, "line_beat": line_beat})

    for x in load(SHARP):
        am = tb.num(x.get("price_after_fee"))
        if am is None:
            am = tb.num(x.get("price"))
        add(x, "sharp", str(x.get("alert_utc") or "")[:10], x.get("game"), x.get("bet"),
            x.get("sport") or x.get("league"), am, x.get("book_key"), x.get("result"),
            x.get("close_fair_prob"), x.get("beat_close"))
    for x in load(LIQ):
        add(x, "liquidity", str(x.get("alerted_utc") or "")[:10], x.get("game"), x.get("bet"),
            x.get("league") or x.get("sport"), tb.num(x.get("price")), x.get("book"),
            x.get("result"), x.get("close_price"))

    say("")
    say("COVERAGE OF EACH BASIS")
    say("=" * 108)
    say(f"  observations loaded                      {len(rows)}")
    say(f"  OLD basis computable                     {sum(1 for r in rows if r['old'] is not None)}")
    say(f"  NEW basis computable                     {sum(1 for r in rows if r['new'] is not None)}")
    say(f"  BOTH computable (the comparable set)     {sum(1 for r in rows if r['old'] is not None and r['new'] is not None)}")
    say("")
    say("  why the NEW basis could not be computed - MISSING PRICE DATA, reported separately from")
    say("  pipeline failures as Peter asked:")
    for why, n in gaps.most_common(12):
        say(f"    {n:6d}  {why}")

    both = [r for r in rows if r["old"] is not None and r["new"] is not None]
    if not both:
        say("")
        say("  NO COMPARABLE OBSERVATIONS - the NEW basis needs Pinnacle history for these games")
        say("  and the cache does not hold it. Nothing can be switched on this evidence.")
        return 0

    say("")
    say("DISCREPANCY, OVER THE COMPARABLE SET")
    say("=" * 108)
    d = [r["new"] - r["old"] for r in both]
    say(f"  n {len(both)}   mean OLD {st.mean(r['old'] for r in both):+.2f}%   "
        f"mean NEW {st.mean(r['new'] for r in both):+.2f}%   mean change {st.mean(d):+.2f}pp")
    say(f"  rows where the SIGN of CLV flips          "
        f"{sum(1 for r in both if (r['old'] > 0) != (r['new'] > 0))}")
    say(f"  rows changing by more than 1pp            {sum(1 for x in d if abs(x) > 1)}")
    say(f"  rows changing by more than 5pp            {sum(1 for x in d if abs(x) > 5)}")
    say(f"  largest single change                     {max(d, key=abs):+.2f}pp")
    say("")
    say("  the ten largest changes:")
    for r in sorted(both, key=lambda r: -abs(r["new"] - r["old"]))[:10]:
        say(f"    {r['day']} {str(r['lg']):<6} {str(r['game'])[:34]:<34} {str(r['bet'])[:18]:<18} "
            f"OLD {r['old']:+7.2f}%  NEW {r['new']:+7.2f}%  ({r['new'] - r['old']:+.2f}pp)")

    say("")
    say("PER-SLICE: CLV, HALVES AND ACCEPTANCE STATUS UNDER EACH BASIS")
    say("=" * 108)
    slices = [("ALL comparable", both),
              ("sharp feed", [r for r in both if r["src"] == "sharp"]),
              ("liquidity board", [r for r in both if r["src"] == "liquidity"]),
              ("NBA totals UNDER", [r for r in both if r["lg"] == "NBA"
                                    and "under" in str(r["bet"]).lower()]),
              ("NCAAF", [r for r in both if r["lg"] == "NCAAF"]),
              ("NFL", [r for r in both if r["lg"] == "NFL"]),
              ("NBA", [r for r in both if r["lg"] == "NBA"])]
    for name, xs in slices:
        if not xs:
            continue
        xs = sorted(xs, key=lambda r: r["day"] or "")
        half = len(xs) // 2
        say("")
        say(f"  {name}  n {len(xs)}   units {units_of(xs):+.2f}u")
        for key, lbl in (("old", "OLD"), ("new", "NEW")):
            pooled = st.mean(r[key] for r in xs)
            h1 = st.mean([r[key] for r in xs[:half]]) if half else None
            h2 = st.mean([r[key] for r in xs[half:]]) if xs[half:] else None
            beat = sum(1 for r in xs if r[key] > 0)
            c = ci([r[key] for r in xs])
            v, why = verdict(xs, key)
            say(f"    {lbl}  CLV {pooled:+6.2f}%  "
                f"H1 {('%+6.2f%%' % h1) if h1 is not None else '   n/a':>8}  "
                f"H2 {('%+6.2f%%' % h2) if h2 is not None else '   n/a':>8}  "
                f"beat {beat}/{len(xs)} ({100 * beat / len(xs):.0f}%)  "
                f"CI [{c[0]:+.2f}, {c[1]:+.2f}]%" if c else "")
            say(f"          status: {v} - {why}")
        vo, _ = verdict(xs, "old")
        vn, _ = verdict(xs, "new")
        if vo != vn:
            say(f"    *** STATUS CHANGES: {vo}  ->  {vn} ***")

    say("")
    say("=" * 108)
    say("Nothing was switched. The published scorecard is untouched; this is the reconciled view")
    say("alongside it, identified by basis version. Switching is Peter's call.")
    try:
        os.makedirs("audit", exist_ok=True)
        with open(OUT, "w") as fh:
            fh.write("\n".join(L) + "\n")
        print(f"wrote {OUT} (reconciled view; the published scorecard is untouched)", flush=True)
    except Exception as e:
        print(f"could not write {OUT} ({type(e).__name__})", flush=True)
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send(f"Scorecard basis reconciliation ({cb.BASIS_VERSION})", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"basis compare: {len(rows)} observations, {len(both)} comparable, "
          f"mean change {st.mean(d):+.2f}pp, sign flips "
          f"{sum(1 for r in both if (r['old'] > 0) != (r['new'] > 0))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
