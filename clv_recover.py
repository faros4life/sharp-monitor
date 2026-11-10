#!/usr/bin/env python3
"""
STEP 1 RECOVERY AUDIT (Peter, Nov 10: "GO - Step 1 only"). READ-ONLY. CACHED DATA ONLY.
No production edit, no rule change, no live change. CFB overs remain eligible - nothing here
touches phase 1.

THE QUESTION. Phase 1 has 53 qualifying alerts and 22 CLV readings, and the forensic audit showed
that none of those 22 can be certified: sharp_monitor.close_prob() silently applies
half_point_value() when Pinnacle's close sits at a different number, and records nothing about it.
So before any of the remediation is worth building, one number has to be established - how many of
the 53 can be given a VERIFIED SAME-LINE Pinnacle close from data we already hold.

WHY THIS PATH CAN CERTIFY AND THE FEED CANNOT. clv_ledger.close_for() reports HOW it read the
close, and clv_std.close_verified() admits only "own line" or "moneyline". Anything of the form
"main X moved to Y" is a half-point conversion - a model - and is reported separately here, never
folded into a headline.

CREDITS. Zero. Two independent reasons, both checked rather than assumed:
  1. /historical-odds is in credit_gate.FREE_PATHS, so the gate does not bill it.
  2. This script never asks for a download at all. It reads a fixture's Pinnacle history ONLY when
     the cache file already exists on disk (hist_cache._path), and skips the fixture otherwise with
     that stated as the reason. A missing cache file is reported, never fetched.
The free tier returns no quota header, so the call count is the only meter - which is why the
no-download rule above is a file-existence check and not a trust exercise.

THE FEE BASIS, which is the one decision that can make every number wrong. clv_std.net_clv applies
the venue fee ITSELF via net_dec, so it takes the RAW decimal price. Passing the already-net
price_after_fee would charge the fee twice. The feed's own close_value_pct used sharp_monitor.net()
instead, which is a different fee model - that difference is exactly what produced the four Oct 25
discrepancies, so this script uses the standard's model and reports both where they disagree.

NO SELECTION ON PROFITABILITY. The population is every phase-1 alert, fixed before any close is
read. Alerts that cannot be priced are reported by reason and never dropped.
"""
import collections
import json
import os
import statistics as sts
import sys

import agree_rules
import clv_ledger as cl
import clv_std as cs
import hist_cache as hc
import tracker_build as tb

ALERTS = "alerts.json"
LEAGUES = ("NBA", "NFL", "NCAAF")


def say(s=""):
    print(s, flush=True)


def phase1_ok(a):
    """The coded phase-1 view, built exactly as sharp_monitor.phase1_label builds it. Muse AGREE is
    dropped because it is a human verdict, not a property of the alert."""
    try:
        ok, why = agree_rules.phase1({"book_key": a.get("book_key"), "book": a.get("book"),
                                      "grade": a.get("grade"), "sport": a.get("sport"),
                                      "kind": a.get("kind"), "bet": a.get("bet") or "",
                                      "price_after_fee": a.get("price_after_fee"),
                                      "confirmed_by": a.get("confirmed_by") or [],
                                      "start_utc": a.get("start_utc"),
                                      "alert_utc": a.get("alert_utc"),
                                      "late": bool(a.get("late"))}, True)
    except Exception:
        return False
    return not [w for w in why if w != "no Muse AGREE"]


def raw_dec(am):
    if am is None:
        return None
    try:
        am = float(am)
    except Exception:
        return None
    return 1 + (100.0 / abs(am) if am < 0 else am / 100.0)


def main():
    try:
        feed = json.load(open(ALERTS))
    except Exception as e:
        say(f"alerts.json unreadable ({type(e).__name__}) - STOP")
        return 1
    A = [x for x in (feed.get("alerts") or []) if x.get("sent_to_phone")]
    pop = [a for a in A if phase1_ok(a)]
    say("STEP 1 RECOVERY AUDIT | phase-1 alerts | READ-ONLY | cached history only | 0 paid credits")
    say("=" * 108)
    say(f"  phase-1 population fixed before any close was read: {len(pop)} alert(s)")
    say(f"  with a feed CLV reading today: {sum(1 for a in pop if a.get('close_value_pct') is not None)}")

    st = {"fixtures": {}}
    try:
        st["fixtures"] = dict((tb.dec(json.load(open(cl.STATE))).get("fixtures") or {}))
        say(f"  fixture cache: {len(st['fixtures'])} fixture(s)")
    except Exception as e:
        say(f"  fixture cache UNAVAILABLE ({type(e).__name__}: {str(e)[:60]}) - cannot certify. STOP")
        return 1
    mkmap = {}
    try:
        from datetime import datetime as _d, timezone as _tz
        mkmap = cl.load_markets(st, _d.now(_tz.utc))
    except Exception as e:
        say(f"  market map unavailable ({type(e).__name__}) - continuing; close_for may still read")

    def fixture_for(a, lg):
        """clv_ledger.find_fixture, NOT a matcher of my own.

        My first version matched >=2 shared tokens against p1/p2 across all 1,862 fixtures, with no
        league filter, and returned the first hit. It produced a verified CLV of -7.30% that diverged
        from the feed by 12.91 points on average and 31.59 at worst, and close_for's own reason text
        said "wrong league" - the fixtures were from other sports. find_fixture's docstring describes
        exactly that failure: a "New Orleans" bet matching a "New York" fixture on the shared word
        "new" is "a wrong fixture, and so a confidently wrong CLV, which is worse than no CLV".
        It filters on league, demands a distinctive token on BOTH participants with a two-token floor
        on at least one, and returns None unless the winner is unique. An unmatched alert is reported
        missing, which is the correct outcome.
        """
        try:
            fid = cl.find_fixture(st, {"bet": a.get("bet") or "", "league": lg,
                                       "game": a.get("game"), "game_start": a.get("start_utc"),
                                       "teams": None})
        except Exception:
            return None, None
        if not fid:
            return None, None
        return fid, (st.get("fixtures") or {}).get(fid) or {}

    out = collections.defaultdict(lambda: {"ver": [], "mod": [], "miss": collections.Counter()})
    reads = 0
    for a in pop:
        lg = str(a.get("sport") or "").upper()
        b = out[lg]
        bet = a.get("bet") or ""
        if not bet.strip():
            b["miss"]["alert carries no bet text"] += 1
            continue
        fid, f = fixture_for(a, lg)
        if not fid:
            b["miss"]["find_fixture: no unique same-league fixture (left unscored)"] += 1
            continue
        p = hc._path(fid, "pinnacle")
        if not os.path.exists(p):
            b["miss"]["no CACHED Pinnacle history (not fetched, by design)"] += 1
            continue
        start = cl.tp(f.get("start"))
        if not start:
            b["miss"]["fixture has no start time"] += 1
            continue
        try:
            h = hc.get_hist(fid, ["pinnacle"], start)
            reads += 1
        except Exception as e:
            b["miss"][f"cached history unreadable ({type(e).__name__})"] += 1
            continue
        pmk = cl.book_markets(h, "pinnacle")
        if not pmk:
            b["miss"]["cached history holds no Pinnacle market"] += 1
            continue
        mt = "total" if str(a.get("kind")) == "tot" else "spread" if str(a.get("kind")) == "spr" else "moneyline"
        try:
            c, why = cl.close_for({"bet": bet, "league": lg, "market": mt,
                                   "game": f.get("game"), "game_start": f.get("start")},
                                  f, pmk, mkmap, start, lg)
        except Exception as e:
            b["miss"][f"close_for raised {type(e).__name__}"] += 1
            continue
        if not c:
            b["miss"][f"no close: {str(why)[:50]}"] += 1
            continue
        how = c.get("how")
        rd = raw_dec(a.get("price"))
        pct = None
        if rd is not None:
            try:
                pct = cs.net_clv(c["p"], rd, cs.canon(a.get("book_key")), maker=False, league=lg)
            except Exception:
                pct = None
        rec = {"a": a, "how": how, "pct": pct, "p": c.get("p"),
               "feed": a.get("close_value_pct")}
        if cs.close_verified(how):
            b["ver"].append(rec)
        else:
            b["mod"].append(rec)

    def stats(recs):
        v = [r["pct"] for r in recs if r["pct"] is not None]
        if not v:
            return "no CLV computable"
        m = sum(v) / len(v)
        sd = sts.stdev(v) if len(v) > 1 else 0.0
        se = sd / len(v) ** 0.5 if len(v) > 1 else 0.0
        beat = 100.0 * sum(1 for x in v if x > 0) / len(v)
        return (f"n{len(v):3} mean {m:+6.2f}% sd {sd:5.2f} SE {se:5.2f} "
                f"95% {m - 1.96 * se:+6.2f}..{m + 1.96 * se:+6.2f}  beat {beat:3.0f}%")

    say("")
    say("  " + "-" * 104)
    tot_v = tot_m = tot_x = 0
    for lg in LEAGUES + tuple(sorted(set(out) - set(LEAGUES))):
        if lg not in out:
            continue
        b = out[lg]
        nv, nm = len(b["ver"]), len(b["mod"])
        nx = sum(b["miss"].values())
        tot_v += nv
        tot_m += nm
        tot_x += nx
        say(f"  {lg:<6} total {nv + nm + nx:3}   VERIFIED same-line {nv:3}   modeled/converted {nm:3}   missing {nx:3}")
        say(f"           verified CLV   {stats(b['ver'])}")
        if nm:
            say(f"           modeled  CLV   {stats(b['mod'])}   (reported apart, never in a headline)")
        for k, n in b["miss"].most_common(6):
            say(f"             missing: {n:3}  {k}")
    say("  " + "-" * 104)
    allv = [r for lg in out for r in out[lg]["ver"]]
    allm = [r for lg in out for r in out[lg]["mod"]]
    say(f"  ALL    VERIFIED {tot_v}   modeled {tot_m}   missing {tot_x}   of {len(pop)}")
    say(f"           verified CLV   {stats(allv)}")
    if allm:
        say(f"           modeled  CLV   {stats(allm)}")

    # the standard's number vs the feed's, on the same observations
    pair = [(r["pct"], r["feed"]) for r in allv + allm
            if r["pct"] is not None and r["feed"] is not None]
    say("")
    if pair:
        d = [abs(x - y) for x, y in pair]
        say(f"  standard vs feed on the same {len(pair)} observation(s): mean |diff| {sum(d) / len(d):.2f} pt, "
            f"max {max(d):.2f} pt, over 1 pt: {sum(1 for x in d if x > 1)}")
        say("  (different fee models: clv_std.net_dec on the raw price vs sharp_monitor.net - not an error by itself)")
    else:
        say("  no observation has both a standard and a feed figure, so the two models cannot be compared here")
    say("")
    say(f"  CREDITS: 0 paid. Cached-history reads: {reads}. No download was requested: a fixture with")
    say("  no cache file on disk is reported as missing, never fetched. /historical-odds is in")
    say("  credit_gate.FREE_PATHS in any case.")
    say("=" * 108)
    return 0


if __name__ == "__main__":
    sys.exit(main())
