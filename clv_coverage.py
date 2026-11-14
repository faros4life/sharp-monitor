#!/usr/bin/env python3
"""
CLV COVERAGE SCORECARD (Peter, Nov 13 2026). READ-ONLY. Permanent part of the scorecard.

"CLV is our primary measure of betting edge. We cannot make reliable strategy decisions when
closing prices are missing." So coverage is reported beside every figure, not assumed.

Per strategy: unique selections, CLV-certified selections, coverage %, first-half CLV, second-half
CLV, overall CLV, positive-CLV %, ROI, units. Then missing CLV by reason, league and venue, and an
explicit read on whether the missingness could bias the conclusions.

EXCEPTIONS. Every LIVE (bot) selection whose game has finished and whose CLV is still missing is
listed, split into two classes because they have opposite remedies:

  MARKET DATA UNAVAILABLE - no fixture exists in any cache, or no Pinnacle history was ever
                            downloaded, or Pinnacle never hung our number. Nothing in this repo
                            can fix it; it is a limit of what the market published.
  PIPELINE DEFECT         - the data exists somewhere we already hold but the live scorer did not
                            use it: a fixture sitting in another cache, a row retired under a
                            reason since fixed, or a fill whose price was never written back.
                            This one is ours to fix.

Collapsing those two into "missing" is what let a dead feed look benign for nine hours in a
different part of this system. They are never merged here.

UNITS are reported only where the lane is known, because a unit is a lane concept ($300 Phase 1,
$200 Board v3 / R1) and the ledger rows carry no lane. A strategy whose lane cannot be resolved
reports units as UNAVAILABLE rather than being given an assumed unit.

NO PROMOTION LOGIC. This reports; it never changes a stake, a threshold, an eligibility rule or a
live switch, and it never turns a strategy off. Peter: "No strategy gets promoted or its stake
increased based on incomplete or negative CLV evidence. Do not automatically shut off live
strategies or change execution without my approval."

READ-ONLY: no write, no fetch, no IMAP.
"""
import collections
import glob
import gzip
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import clv_selection as csel
import clv_stale as cstale
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
ALT_FX = ["oddspapi/fixtures.json"]
LANE_UNIT = {"rules": 300.0, "board": 200.0, "r1": 200.0, "lane2": 200.0}
LANE_NAME = {"rules": "PHASE 1", "board": "BOARD V3", "r1": "R1", "lane2": "LANE 2 (paper)"}
L, SCREEN = [], []


def say(t="", money=False):
    L.append(t)
    if not money:
        SCREEN.append(t)
        print(t, flush=True)


def all_fixture_ids():
    """Fixture ids this repo holds anywhere, so 'no fixture' can be distinguished from
    'a fixture exists but the live scorer never saw it'."""
    out = {}
    for path in ALT_FX:
        try:
            for fid, f in (json.load(open(path)).get("fixtures") or {}).items():
                out[fid] = (f, path)
        except Exception:
            pass
    for path in sorted(glob.glob("clv_backup/*.enc")):
        try:
            for fid, f in (tb.dec(json.load(open(path))).get("fixtures") or {}).items():
                out.setdefault(fid, (f, path))
        except Exception:
            pass
    return out


def classify_missing(r, st, alt, hc_has):
    """(class, reason) for a row with no CLV. class is 'market' | 'pipeline' | 'policy'."""
    s = r.get("snap") or {}
    why = str(r.get("why") or "").lower()
    if r.get("done") and any(p in why for p in ("placed after start", "not parsed",
                                                "not comparable", "far from")):
        return "policy", str(r.get("why"))[:60]
    lg = s.get("league")
    if not lg:
        # A row with NO league recorded is our own data gap, not a limit of what the market
        # published - nothing was ever asked of OddsPapi for it. The first version of this
        # classifier filed these under "market" and they are the single largest bucket (103 rows,
        # almost all ProphetX), which made the shortfall look like a coverage problem in leagues
        # we do not buy. It is a missing field on our side and it is ours to fix.
        return "pipeline", "no league recorded on the row - nothing was ever looked up for it"
    if lg not in cl.SPORT:
        return "market", f"league {lg} not covered by the ledger's sport map"
    fid = r.get("fixture") or cl.find_fixture(st, s)
    if fid:
        if not hc_has(fid):
            return "market", "fixture known, no Pinnacle history ever downloaded"
        return "pipeline", "fixture and history both present - the live scorer did not use them"
    # the live matcher found nothing; does ANY cache hold a plausible fixture for it?
    gs = cl.tp(s.get("game_start"))
    near = 0
    for f, _src in alt.values():
        if f.get("lg") != lg:
            continue
        fs = cl.tp(f.get("start"))
        if gs and fs and abs((fs - gs).total_seconds()) <= 12 * 3600:
            w = (tb.toks(s.get("game")) - tb.WEAK)
            if ((tb.toks(f.get("p1") or "") - tb.WEAK) & w) and ((tb.toks(f.get("p2") or "") - tb.WEAK) & w):
                near += 1
    if near:
        return "pipeline", f"{near} fixture(s) for this game sit in another cache the live scorer does not read"
    if not cl.eff_dec(s):
        return "pipeline", "no after-fee execution price was ever written back to this row"
    return "market", "no fixture for this game in any cache we hold"


def fig(label, obs, unit=None):
    s = csel.stats(obs)
    if not s.get("n"):
        say(f"    {label:<22} n    0")
        return s
    se = f" +/-{100 * s['se']:.2f}" if s.get("se") is not None else ""
    roi = (f"ROI {s['roi_pct']:+.2f}%" if s.get("roi_pct") is not None
           else f"ROI UNAVAIL ({s.get('has_profit', 0)}/{s['n']})")
    units = f"{s['stake'] / unit:.1f}u" if (unit and s.get("stake")) else "units UNAVAIL"
    say(f"    {label:<22} n {s['n']:4d}  CLV {100 * s['mean']:+.2f}%{se}  "
        f"pos {s['pos']}/{s['n']} ({s['pos_pct']:.0f}%)  {roi}  {units}  fills {s['fills']}")
    return s


def main():
    now = datetime.now(timezone.utc)
    say("CLV COVERAGE SCORECARD - READ-ONLY. Nothing written, fetched or changed.")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("Coverage is reported beside every figure: a CLV number without its coverage is not a")
    say("result. No stake, threshold, eligibility rule or live switch is touched by this report.")
    say("=" * 104)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    bets = st.get("bets") or {}
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        tracker = {}
        say(f"WARNING: tracker unreadable ({type(e).__name__}) - dup_of not honoured")
    reg = None
    try:
        import registry
        reg = registry.load() if registry.enabled() else None
    except Exception:
        pass
    if reg is None:
        say("WARNING: registry unreadable - lanes UNKNOWN, so units are unavailable per strategy")
    alt = all_fixture_ids()
    hc_names = set(os.listdir(HC)) if os.path.isdir(HC) else set()

    def hc_has(fid):
        return f"{fid}__pinnacle.json.gz" in hc_names

    try:
        stale = cstale.stale_map(bets, tracker)
    except Exception:
        stale = {}

    # strategy per selection key, from the registry's own lane where it can be linked
    lane_by_sel = {}
    for o in ((reg or {}).get("orders") or []):
        parts = [p for p in str(o.get("key") or "").split("|") if p]
        if parts and parts[0] in LANE_UNIT:
            lane = parts[0]
            rest = parts[1:]
        else:
            lane, rest = (o.get("source") or ""), parts
        if len(rest) >= 4 and lane in LANE_UNIT:
            g = "+".join(sorted(tb.toks(rest[1]) - tb.WEAK)) or "?"
            lane_by_sel.setdefault(f"{rest[0].upper()}|{g}|{rest[2]}|{rest[3]}", lane)


    # ------------------------------------------------------------------ selections
    certified = {k: r for k, r in bets.items()
                 if r.get("clv") is not None and not r.get("fixture_doubt") and k not in stale}
    missing = {k: r for k, r in bets.items() if r.get("clv") is None and k not in stale}
    obs = csel.selections(certified, tracker, exclude=set(stale))
    # attach lane and the row's own source to each observation
    for key, o in obs.items():
        base = "|".join(key.split("|")[:4])
        o["_lane"] = lane_by_sel.get(base) or lane_by_sel.get(key)
    miss_obs = csel.selections({k: dict(r, clv=-999) for k, r in missing.items()}, tracker,
                               exclude=set(stale))
    for key, o in miss_obs.items():
        o["_lane"] = lane_by_sel.get("|".join(key.split("|")[:4])) or lane_by_sel.get(key)
        o["clv"] = None

    say("")
    say("1. COVERAGE BY STRATEGY")
    say("=" * 104)
    say("  'certified' means a verified same-line Pinnacle close, net of fees, on a deduplicated")
    say("  selection - one bet is one observation however many fills it took.")
    groups = collections.defaultdict(lambda: {"cert": [], "miss": []})
    for o in obs.values():
        groups[o.get("_lane") or (o.get("source") or "unknown")]["cert"].append(o)
    for o in miss_obs.values():
        groups[o.get("_lane") or (o.get("source") or "unknown")]["miss"].append(o)
    tot_c = tot_m = 0
    for g in sorted(groups, key=lambda x: str(x)):
        c, m = groups[g]["cert"], groups[g]["miss"]
        tot_c += len(c)
        tot_m += len(m)
        n = len(c) + len(m)
        unit = LANE_UNIT.get(g)
        say("")
        say(f"  {LANE_NAME.get(g, str(g)).upper()}   unique selections {n}   certified {len(c)}   "
            f"coverage {100 * len(c) / n:.0f}%" + (f"   unit ${unit:.0f}" if unit else "   unit UNKNOWN"))
        if c:
            h1, h2, nod = csel.halves(c)
            fig("overall", c, unit)
            fig("first half", h1, unit)
            fig("second half", h2, unit)
            if nod:
                say(f"    {len(nod)} selection(s) excluded from the half split (no game start)")
        if m:
            say(f"    MISSING CLV: {len(m)} selection(s) - see section 3")
    n_all = tot_c + tot_m
    say("")
    say(f"  ALL STRATEGIES: unique selections {n_all}, certified {tot_c}, "
        f"coverage {100 * tot_c / n_all:.1f}%" if n_all else "  no selections")

    # ------------------------------------------------------------------ live only
    say("")
    say("2. THE HEADLINE NUMBER - LIVE BOT SELECTIONS ONLY")
    say("=" * 104)
    live_c = [o for o in obs.values() if str(o.get("source") or "").lower().startswith("bot")]
    live_m = [o for o in miss_obs.values() if str(o.get("source") or "").lower().startswith("bot")]
    lt = len(live_c) + len(live_m)
    if lt:
        say(f"  live bot selections            {lt}")
        say(f"  with trustworthy CLV           {len(live_c)}  ({100 * len(live_c) / lt:.1f}%)")
        say(f"  missing                        {len(live_m)}  ({100 * len(live_m) / lt:.1f}%)")
        fig("live, certified", live_c)
    else:
        say("  no live bot selections found")

    # ------------------------------------------------------------------ missing
    say("")
    say("3. MISSING CLV BY REASON, LEAGUE AND VENUE")
    say("=" * 104)
    by_reason, by_lg, by_bk, by_class = (collections.Counter() for _ in range(4))
    rows_by_class = collections.defaultdict(list)
    for k, r in missing.items():
        cls, reason = classify_missing(r, st, alt, hc_has)
        s = r.get("snap") or {}
        by_class[cls] += 1
        by_reason[f"[{cls}] {reason}"] += 1
        by_lg[f"{s.get('league') or 'unknown'} [{cls}]"] += 1
        by_bk[f"{s.get('book') or 'unknown'} [{cls}]"] += 1
        rows_by_class[cls].append((k, r, reason))
    say(f"  rows missing CLV: {len(missing)}   by class: {dict(by_class)}")
    say("")
    say("  by reason:")
    for why, n in by_reason.most_common():
        say(f"    {n:5d}  {why}")
    say("")
    say("  by league:")
    for lg, n in by_lg.most_common():
        say(f"    {n:5d}  {lg}")
    say("")
    say("  by venue:")
    for bk, n in by_bk.most_common():
        say(f"    {n:5d}  {bk}")

    # ------------------------------------------------------------------ bias
    say("")
    say("4. COULD THE MISSINGNESS BIAS THE CONCLUSIONS?")
    say("=" * 104)
    say("  Missingness biases a CLV figure when it is correlated with the thing being measured.")
    say("  It is NOT random here, and the direction matters, so both are stated.")
    cl_lg = collections.Counter((r.get("snap") or {}).get("league") or "unknown" for r in certified.values())
    mi_lg = collections.Counter((r.get("snap") or {}).get("league") or "unknown" for r in missing.values())
    say("")
    say(f"    {'league':<10} {'certified':>10} {'missing':>9} {'missing %':>10}")
    for lg in sorted(set(cl_lg) | set(mi_lg)):
        c, m = cl_lg.get(lg, 0), mi_lg.get(lg, 0)
        say(f"    {lg:<10} {c:10d} {m:9d} {(100 * m / (c + m) if c + m else 0):9.0f}%")
    worst = [lg for lg in set(mi_lg) if mi_lg[lg] and not cl_lg.get(lg)]
    say("")
    if worst:
        say(f"  STRUCTURAL: {', '.join(sorted(worst))} contribute ZERO certified selections, so every")
        say("  CLV figure above is silent about them. Any conclusion drawn from the overall mean")
        say("  does not apply to those leagues - it is not evidence about them either way.")
    say("  The missingness is concentrated by league and venue rather than spread evenly, so the")
    say("  certified sample is NOT a random sample of the bets placed. Treat the overall mean as")
    say("  a statement about the covered leagues only.")
    say("  What it does NOT tell us: whether the uncovered bets were better or worse. No direction")
    say("  is inferred, because nothing in the data supports one.")

    # ------------------------------------------------------------------ exceptions
    say("")
    say("5. EXCEPTIONS - LIVE SELECTIONS WITH NO CLV AFTER THE GAME")
    say("=" * 104)
    say("  Split by remedy: market data nobody has, versus a pipeline that did not use what we do.")
    ex_pipe = [(k, r, w) for k, r, w in rows_by_class["pipeline"]
               if str((r.get("snap") or {}).get("source") or "").lower().startswith("bot")]
    ex_mkt = [(k, r, w) for k, r, w in rows_by_class["market"]
              if str((r.get("snap") or {}).get("source") or "").lower().startswith("bot")]
    say("")
    say(f"  PIPELINE DEFECT - ours to fix: {len(ex_pipe)}")
    for k, r, w in ex_pipe[:12]:
        s = r.get("snap") or {}
        say(f"    {k[:40]:<40} {s.get('league')} | {str(s.get('game'))[:34]} | {str(s.get('bet'))[:16]}")
        say(f"        {w}")
    if len(ex_pipe) > 12:
        say(f"    ... {len(ex_pipe)} in total")
    say("")
    say(f"  MARKET DATA UNAVAILABLE - not fixable here: {len(ex_mkt)}")
    for k, r, w in ex_mkt[:12]:
        s = r.get("snap") or {}
        say(f"    {k[:40]:<40} {s.get('league')} | {str(s.get('game'))[:34]} | {str(s.get('bet'))[:16]}")
        say(f"        {w}")
    if len(ex_mkt) > 12:
        say(f"    ... {len(ex_mkt)} in total")

    say("")
    say("=" * 104)
    say("No promotion, demotion, stake change or switch flip follows from this report.")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("CLV coverage scorecard", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"coverage: selections {n_all}, certified {tot_c} ({100 * tot_c / n_all:.1f}%), "
          f"live {len(live_c)}/{lt}, pipeline exceptions {len(ex_pipe)}, "
          f"market-data exceptions {len(ex_mkt)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
