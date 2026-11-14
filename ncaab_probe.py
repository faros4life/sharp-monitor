#!/usr/bin/env python3
"""
NCAAB COVERAGE PROBE (Peter, Nov 13 2026). ONE-OFF. Stage 5 stays OFF.

Answers one question with measurements instead of argument: if NCAAB were added to SPORT, how
many of the 125 outstanding NCAAB rows could actually be certified? A sample of ten is matched
against real OddsPapi fixtures and real Pinnacle history, and each of the four gates that a row
must clear is counted separately, because they have different remedies:

    1 fixture matched            - OddsPapi lists the game and the token matcher finds it uniquely
    2 two-sided Pinnacle close   - both sides have a tick before start, inside the freshness limit
    3 quote at OUR exact line    - the bet's own number was hung, not just a nearby main line
    4 CLV computable             - and the row carries an after-fee price to compare it against

WHAT IT DOES NOT DO:
  * It does NOT enable NCAAB. SPORT is untouched, so the ledger still skips NCAAB rows.
  * It does NOT write clv/state.enc. The state is deep-copied and the copy is thrown away, so
    fetched fixtures do not persist and nothing about this run changes the ledger's behaviour.
  * It does NOT set up continuous fetching. There is no schedule; it runs on dispatch only.
  * It does NOT extrapolate beyond what it measured: the estimate is a proportion of the sample
    with its binomial interval, stated as a range, not a single confident number.

COST. Billable: the NCAAB tournament lookup, once, only if the id is not already cached in
state, plus ONE /fixtures call covering the sample's date window. Free: /historical-odds per
matched fixture, and the hcache files already on disk are used first so a cached game costs
nothing. Every call is counted and printed.

SAMPLE. Small-conference games are preferred, because that is where Peter's NCAAB bets live and
where Pinnacle coverage is most doubtful - a sample of major-conference games would flatter the
result. MAJOR below is used only to DE-prioritise, never to exclude.
"""
import collections
import copy
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
MKFILE = "clv/markets.json"
N_WANT = int(os.environ.get("PROBE_N", "") or "10")
L = []

# Power-conference and perennial-Top-25 programs, used ONLY to prefer small-conference games in
# the sample. Deliberately rough: it shapes the sample, never the verdict.
MAJOR = {
    "duke", "kentucky", "kansas", "gonzaga", "villanova", "arizona", "ucla", "michigan", "purdue",
    "houston", "baylor", "texas", "tennessee", "alabama", "auburn", "florida", "georgia", "iowa",
    "illinois", "indiana", "wisconsin", "ohio", "maryland", "rutgers", "connecticut", "marquette",
    "creighton", "xavier", "providence", "georgetown", "butler", "syracuse", "louisville", "miami",
    "virginia", "clemson", "pittsburgh", "notre", "stanford", "california", "oregon", "washington",
    "colorado", "utah", "byu", "texas", "oklahoma", "missouri", "arkansas", "lsu", "mississippi",
    "vanderbilt", "memphis", "cincinnati", "dayton", "vcu", "saint", "wichita", "nevada", "unlv",
    "boise", "smu", "tulane", "temple", "michigan", "minnesota", "nebraska", "northwestern",
    "penn", "iowa", "kansas", "tcu", "wake", "forest", "carolina", "state", "usc",
}


def say(t=""):
    L.append(t)
    print(t, flush=True)


def am(dec):
    return round(-100 / (dec - 1)) if dec < 2 else round(100 * (dec - 1))


def smallness(game):
    """0 when neither side looks major, 1 when one does, 2 when both do."""
    toks = tb.toks(game or "")
    halves = str(game or "").replace(" v ", " @ ").split("@")
    n = 0
    for h in halves[:2]:
        if tb.toks(h) & MAJOR:
            n += 1
    return n if halves else (1 if toks & MAJOR else 0)


def cached_hist(fid, book="pinnacle"):
    p = os.path.join(HC, f"{fid}__{book}.json.gz")
    if not os.path.exists(p):
        return None
    try:
        with gzip.open(p, "rt") as fh:
            return {"bookmakers": {book: json.load(fh)}}
    except Exception:
        return None


def main():
    now = datetime.now(timezone.utc)
    say("NCAAB COVERAGE PROBE - one-off. Stage 5 remains OFF; SPORT is untouched.")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("No state is written: the ledger state is deep-copied and the copy is discarded, so")
    say("fetched fixtures do not persist and nothing here changes the ledger's behaviour.")
    say("=" * 100)
    try:
        real = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    st = copy.deepcopy(real)          # everything below mutates the COPY only
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {MKFILE} unreadable ({type(e).__name__})")
        return 1

    rows = [(k, r) for k, r in (st.get("bets") or {}).items()
            if (r.get("snap") or {}).get("league") == "NCAAB" and r.get("clv") is None]
    say(f"  outstanding NCAAB rows in the ledger: {len(rows)}")
    if not rows:
        say("  nothing to probe")
        return 0
    scored = []
    for k, r in rows:
        s = r.get("snap") or {}
        gs = cl.tp(s.get("game_start"))
        if not gs or not cl.parsed(s):
            continue              # no start time or unparsable: a different problem, not coverage
        scored.append((smallness(s.get("game")), gs, k, r))
    scored.sort(key=lambda x: (x[0], -x[1].timestamp()))
    sample = scored[:N_WANT]
    say(f"  rows with a start time and a parsable bet: {len(scored)}")
    say(f"  sample taken: {len(sample)} (small-conference first; "
        f"{sum(1 for x in sample if x[0] == 0)} with neither side major, "
        f"{sum(1 for x in sample if x[0] == 1)} with one, "
        f"{sum(1 for x in sample if x[0] == 2)} with two)")
    say("")
    for sm, gs, k, r in sample:
        s = r.get("snap") or {}
        say(f"    {gs.astimezone(ET):%Y-%m-%d} major-sides={sm}  {str(s.get('game'))[:48]:<48} "
            f"{str(s.get('bet'))[:18]}")

    # ---------------------------------------------------------------- tournament id
    say("")
    say("STEP 1: NCAAB tournament id")
    say("=" * 100)
    before = dict(cl.STATS)
    tid = st.get("ncaab_tid")
    if tid:
        say(f"  already cached in state: {tid} (no call)")
    else:
        tid = cl.tournament(st, now, "NCAAB")
        say(f"  resolved by a billable /tournaments(sportId=11) call: {tid}")
    if not tid:
        say("  NO TOURNAMENT ID - OddsPapi returned no non-women USA NCAA basketball tournament")
        say("  with upcoming fixtures. That alone would block Stage 5; reported, not worked around.")
        say(f"  credits this run: billable {cl.STATS['billable'] - before['billable']}")
        return 0

    # ---------------------------------------------------------------- fixtures
    say("")
    say("STEP 2: one /fixtures call over the sample's window")
    say("=" * 100)
    lo = min(x[1] for x in sample) - timedelta(days=1)
    hi = max(x[1] for x in sample) + timedelta(days=1)
    say(f"  window {lo.astimezone(ET):%Y-%m-%d} .. {hi.astimezone(ET):%Y-%m-%d}")
    st.setdefault("fx_last", {}).pop("NCAAB", None)      # the copy: no cooldown to fight
    got = cl.refresh_fixtures(st, now, "NCAAB", lo.astimezone(ET), hi.astimezone(ET))
    for ln in cl.FX_LOG:
        say(f"  fixtures: {ln}")
    ncaab_fx = {fid: f for fid, f in (st.get("fixtures") or {}).items() if f.get("lg") == "NCAAB"}
    say(f"  fresh lookup reached OddsPapi: {got}")
    say(f"  NCAAB fixtures now in the (discarded) copy: {len(ncaab_fx)}")
    if not ncaab_fx:
        say("  NO NCAAB FIXTURES RETURNED for that window - nothing further can be measured.")
        say(f"  credits this run: billable {cl.STATS['billable'] - before['billable']}")
        return 0

    # ---------------------------------------------------------------- the four gates
    say("")
    say("STEP 3: the four gates, per sampled row")
    say("=" * 100)
    tally = collections.Counter()
    hist_calls = [0, 0]      # [from cache, fetched free]
    for sm, gs, k, r in sample:
        s = r.get("snap") or {}
        say("")
        say(f"  {str(s.get('game'))[:52]} | {s.get('bet')} | {gs.astimezone(ET):%Y-%m-%d}")
        fid = cl.find_fixture(st, s)
        if not fid:
            say("    GATE 1 FAIL: no unique fixture matched")
            tally["no_fixture"] += 1
            continue
        f = ncaab_fx.get(fid) or (st.get("fixtures") or {}).get(fid) or {}
        tally["matched"] += 1
        say(f"    GATE 1 ok: {fid}  {str(f.get('p1'))[:26]} v {str(f.get('p2'))[:26]}")
        start = cl.tp(f.get("start")) or gs
        h = cached_hist(fid)
        if h is not None:
            hist_calls[0] += 1
            say("    history: from hcache (no call)")
        else:
            h = {"bookmakers": {"pinnacle": cl.api("/historical-odds", False,
                                                   fixtureId=fid, bookmakers="pinnacle")}}
            hist_calls[1] += 1
            inner = (h.get("bookmakers") or {}).get("pinnacle")
            if isinstance(inner, dict) and inner.get("_error"):
                say(f"    GATE 2 FAIL: history HTTP {inner['_error']} (free call)")
                tally["no_history"] += 1
                continue
            say("    history: fetched on the FREE path")
        pm = cl.book_markets(h, "pinnacle")
        if not pm:
            say("    GATE 2 FAIL: no Pinnacle markets for this fixture")
            tally["no_pinnacle"] += 1
            continue
        pz = cl.parsed(s)
        typ = "spreads" if pz[0] == "spread" else "totals" if pz[0] == "total" else "ml"
        if typ == "ml":
            say("    (moneyline: no line to match)")
        cands = []
        for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
            if sp != 11 or t != typ or mid not in pm:
                continue
            tw = cl.two_way(pm, mid, start)
            nm = {v: kk for kk, v in outs.items()}
            a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
            if a in tw and b in tw:
                age = (start - min(tw[a][1], tw[b][1])).total_seconds() / 60
                if age <= cl.FRESH_MIN:
                    cands.append((hcap, cl.novig_p(tw[a][0], tw[b][0]), age, tw[a][0], tw[b][0]))
        if not cands:
            say(f"    GATE 2 FAIL: no fresh two-sided Pinnacle {typ} ticks before start")
            tally["no_two_sided"] += 1
            continue
        tally["two_sided"] += 1
        say(f"    GATE 2 ok: {len(cands)} fresh two-sided line(s); "
            f"closest tick {min(c[2] for c in cands):.0f} min before start")
        want = pz[2]
        side_is_a = (pz[1] == "OVER") if typ == "totals" else None
        if typ == "spreads":
            sd = cl.which_team(f, pz[1])
            if not sd:
                say("    GATE 3 FAIL: held team not matched to either side")
                tally["no_side"] += 1
                continue
            if pz[3]:
                sd, want = ("2" if sd == "1" else "1"), -want
            want = want if sd == "1" else -want
            side_is_a = (sd == "1")
        exact = [c for c in cands if abs(c[0] - want) < 1e-9]
        if not exact:
            say(f"    GATE 3 FAIL: {want:g} not hung; Pinnacle had "
                f"{', '.join(f'{c[0]:g}' for c in sorted(cands)[:8])}")
            tally["no_exact"] += 1
            continue
        tally["exact"] += 1
        p_a = exact[0][1]
        p_held = p_a if side_is_a else 1 - p_a
        say(f"    GATE 3 ok: own line {want:g} hung "
            f"({am(exact[0][3]):+d} / {am(exact[0][4]):+d}), no-vig P(held) {p_held:.4f}")
        dec = cl.eff_dec(s)
        if not dec:
            say("    GATE 4 FAIL: the row carries no after-fee price")
            tally["no_price"] += 1
            continue
        tally["recoverable"] += 1
        say(f"    GATE 4 ok: after-fee {dec:.4f} ({am(dec):+d})  "
            f"CLV would be {100 * (p_held * dec - 1):+.2f}%")

    # ---------------------------------------------------------------- verdict
    n = len(sample)
    rec = tally["recoverable"]
    say("")
    say("RESULTS")
    say("=" * 100)
    say(f"  sampled                                  {n}")
    say(f"  1 fixture matched                        {tally['matched']}/{n}")
    say(f"  2 valid two-sided Pinnacle close         {tally['two_sided']}/{n}")
    say(f"  3 quote at OUR exact betting line        {tally['exact']}/{n}")
    say(f"  4 actual recoverable CLV                 {rec}/{n}")
    say("")
    say(f"  failure reasons: {dict(tally)}")
    say(f"  history: {hist_calls[0]} from cache, {hist_calls[1]} fetched on the FREE path")
    say(f"  ADDITIONAL API CREDITS SPENT (billable): {cl.STATS['billable'] - before['billable']}")
    say(f"  free calls this run: {cl.STATS['free'] - before['free']}")
    if n:
        p = rec / n
        se = (p * (1 - p) / n) ** 0.5
        lo_, hi_ = max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)
        say("")
        say(f"  recoverable fraction of the sample: {rec}/{n} = {100 * p:.0f}%")
        say(f"  95% interval on that proportion: {100 * lo_:.0f}% to {100 * hi_:.0f}%")
        say(f"  applied to the 125 outstanding NCAAB rows: roughly {125 * p:.0f} rows, "
            f"plausibly {125 * lo_:.0f} to {125 * hi_:.0f}")
        say(f"  At n={n} that interval is wide by construction. It is a RANGE, not an estimate to")
        say("  plan against, and it says nothing about rows outside the sampled date window.")
    say("")
    say("=" * 100)
    say("Stage 5 remains OFF. SPORT is unchanged, no state was written, no schedule was created.")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("NCAAB coverage probe (one-off)", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"ncaab probe: matched {tally['matched']}/{n}, two-sided {tally['two_sided']}/{n}, "
          f"exact {tally['exact']}/{n}, recoverable {rec}/{n}, "
          f"billable {cl.STATS['billable'] - before['billable']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
