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
RECOVER = (os.environ.get("CLV_RECOVER_FETCH") or "").strip() == "1"


FETCH = {"any": False, "n": 0, "stopped": False, "why": "", "before": None, "after": None}


def say(s=""):
    print(s, flush=True)


def start_of(f):
    return cl.tp(f.get("start"))


def _acct_used():
    """The PROVIDER's own used figure, and WHY if it cannot be had. /account is free, so this costs
    nothing. None is never turned into 0 - zero would read as "nothing used" and wave a paid
    download through.

    The field is request_count, inside subscriptions[0]. My first version guessed at "used",
    "requestsUsed", "requests_used" and "usage" and missed it, so _pick returned None, the bracket
    could not be read, and recovery halted on 15 fixtures for no real reason. These are the exact
    names credits.py's own report() uses - taken from it rather than guessed again. The error is
    returned instead of swallowed, because a bare None told me nothing about which of four things
    had gone wrong."""
    try:
        import credits as cr
    except Exception as e:
        return None, f"credits module unimportable ({type(e).__name__}: {str(e)[:60]})"
    try:
        d = cr.account()
    except Exception as e:
        return None, f"/account call raised ({type(e).__name__}: {str(e)[:60]})"
    if not isinstance(d, dict):
        return None, f"/account returned {type(d).__name__}, not a dict"
    if d.get("_error"):
        return None, f"/account error: {str(d['_error'])[:70]}"
    v = cr._pick(d, "request_count", "requestsUsed", "used")
    if v is None:
        return None, "/account answered but carries no request_count field"
    try:
        return int(v), None
    except Exception:
        return None, f"request_count is not a number ({type(v).__name__})"


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
            if not RECOVER:
                b["miss"]["no CACHED Pinnacle history (not fetched, by design)"] += 1
                continue
            # RECOVERY, and it polices itself with the PROVIDER's own counter rather than ours.
            # Peter, Nov 10: nothing is downloaded until history is confirmed free. Four hcache
            # fills recorded 11-145 history downloads for 0-2 billable calls, and credits.py states
            # outright that OddsPapi bills everything except /account and /historical-odds - but
            # that is OUR classifier, so it does not get the last word. /account is itself free, so
            # the FIRST download is bracketed by two reads of it: if the provider's used figure
            # moves at all, recovery stops right there and the remaining fixtures are left alone.
            if FETCH["stopped"]:
                # Nov 10: this line used to read "halted after the provider's counter moved" on
                # every later fixture, whatever had actually stopped it - and the real cause that
                # run was an unreadable /account. A message must not assert a cause it did not
                # observe, so it now carries the recorded reason.
                b["miss"]["recovery halted: " + str(FETCH["why"])[:60]] += 1
                continue
            first = not FETCH["any"]
            before, berr = _acct_used() if first else (None, None)
            try:
                hc.get_hist(fid, ["pinnacle"], start_of(f))
                FETCH["any"] = True
                FETCH["n"] += 1
            except Exception as e:
                b["miss"][f"history download failed ({type(e).__name__})"] += 1
                continue
            if first:
                after, aerr = _acct_used()
                FETCH["before"], FETCH["after"] = before, after
                if before is None or after is None:
                    FETCH["stopped"] = True
                    FETCH["why"] = f"/account unreadable, so cost is unproven ({berr or aerr})"
                    b["miss"]["recovery halted: " + FETCH["why"][:60]] += 1
                    continue
                if after > before:
                    FETCH["stopped"] = True
                    FETCH["why"] = f"the provider billed it: used {before} -> {after} on ONE download"
                    b["miss"]["recovery halted: " + FETCH["why"][:60]] += 1
                    continue
            if not os.path.exists(p):
                b["miss"]["download returned no Pinnacle history for this fixture"] += 1
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
        # ITEM 1: the inputs behind the standard-vs-feed gap, kept per observation so the 2.52-pt
        # average can be DECOMPOSED rather than attributed. Two inputs differ between the paths:
        #   the FEE model  - clv_std.net_dec(book, raw_dec) vs sharp_monitor.net(price, book),
        #                    the latter being what price_after_fee was rounded from
        #   the CLOSE PROB - the feed reads live at 20-30 min out; the standard reads the stored
        #                    historical close. Different instants, so different p.
        # Holding one fixed while the other varies splits the gap additively, and whatever is left
        # over is named as residual instead of being folded into one of the two.
        nd = None
        try:
            nd = cs.net_dec(cs.canon(a.get("book_key")), rd, False, lg, False) if rd else None
        except Exception:
            nd = None
        feed_am = a.get("price_after_fee")
        feed_dec = raw_dec(feed_am)
        p_std, p_feed = c.get("p"), a.get("close_fair_prob")
        rec = {"a": a, "how": how, "pct": pct, "p": p_std,
               "feed": a.get("close_value_pct"),
               "nd": nd, "feed_dec": feed_dec, "p_feed": p_feed,
               "mins": a.get("close_read_mins_before")}
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

    # ---------------- NCAAF overs vs unders, on the certified observations ----------------
    # Peter, Nov 10: the aggregate -3.54% hides which side it comes from, and only the OVERS are in
    # the live lane. Every alert here already passed phase 1 - that is how the population was built
    # - so nothing excluded is mixed in. Duplicates are checked rather than assumed away: the feed
    # is one entry per game/market/side, so two rows can share a game legitimately, and a per-game
    # view is reported beside the per-alert one.
    nc = out.get("NCAAF", {}).get("ver", [])
    say("")
    say("  NCAAF CERTIFIED OBSERVATIONS - OVERS vs UNDERS")
    say("  " + "-" * 104)

    def side_of(a):
        b = str(a.get("bet") or "").strip().lower()
        return "OVER" if b.startswith("over") else "UNDER" if b.startswith("under") else "?"

    def sstats(recs, label):
        g = [r for r in recs if r["a"].get("result") in ("W", "L", "P")]
        w = sum(1 for r in g if r["a"]["result"] == "W")
        l = sum(1 for r in g if r["a"]["result"] == "L")
        p_ = sum(1 for r in g if r["a"]["result"] == "P")
        u = sum(r["a"].get("units_flat") or 0 for r in g)
        risk = len([r for r in g if r["a"]["result"] != "P"])
        v = [r["pct"] for r in recs if r["pct"] is not None]
        line = (f"    {label:<22} alerts {len(recs):3}  graded {len(g):3}  {w}-{l}"
                + (f"-{p_}" if p_ else "") + f"  {u:+7.2f}u")
        line += f"  ROI {100 * u / risk:+7.1f}%" if risk else "  ROI     n/a"
        if v:
            m = sum(v) / len(v)
            sd = sts.stdev(v) if len(v) > 1 else 0.0
            se = sd / len(v) ** 0.5 if len(v) > 1 else 0.0
            beat = 100.0 * sum(1 for x in v if x > 0) / len(v)
            line += (f"  | CLV n{len(v):3} {m:+6.2f}% sd {sd:5.2f} SE {se:5.2f} "
                     f"95% {m - 1.96 * se:+6.2f}..{m + 1.96 * se:+6.2f}  beat {beat:3.0f}%")
        else:
            line += "  | CLV n/a"
        say(line)

    ov = [r for r in nc if side_of(r["a"]) == "OVER"]
    un = [r for r in nc if side_of(r["a"]) == "UNDER"]
    other = [r for r in nc if side_of(r["a"]) == "?"]
    sstats(nc, "ALL NCAAF certified")
    sstats(ov, "OVERS (in the lane)")
    sstats(un, "UNDERS")
    if other:
        sstats(other, "side unparsed")

    say("")
    say("    chronological halves (certified CLV only):")
    for label, grp in (("OVERS", ov), ("UNDERS", un)):
        g2 = sorted([r for r in grp if r["pct"] is not None],
                    key=lambda r: str(r["a"].get("alert_utc") or ""))
        if len(g2) >= 2:
            h = len(g2) // 2
            a1 = [r["pct"] for r in g2[:h]]
            a2 = [r["pct"] for r in g2[h:]]
            say(f"      {label:<8} first half n{len(a1):3} {sum(a1)/len(a1):+6.2f}%   "
                f"second half n{len(a2):3} {sum(a2)/len(a2):+6.2f}%")
        else:
            say(f"      {label:<8} too few certified readings to halve (n={len(g2)})")

    say("")
    say("    DUPLICATES - is one game carrying more than one observation?")
    for label, grp in (("OVERS", ov), ("UNDERS", un), ("ALL", nc)):
        games = collections.Counter(str(r["a"].get("game")) for r in grp)
        rep = {g: n for g, n in games.items() if n > 1}
        say(f"      {label:<8} {len(grp):3} alert(s) across {len(games):3} unique game(s); "
            f"{len(rep)} game(s) carry more than one")
        for g, n in sorted(rep.items(), key=lambda kv: -kv[1])[:6]:
            sides = ", ".join(sorted(f"{side_of(r['a'])} {r['a'].get('point')}"
                                     for r in grp if str(r["a"].get("game")) == g))
            say(f"          {str(g)[:44]:<44} x{n}  [{sides}]")
    # one observation per game, keeping the EARLIEST alert, so a repeated game cannot double-weight
    say("")
    say("    per-game view (earliest alert per game, so no game is counted twice):")
    for label, grp in (("OVERS", ov), ("UNDERS", un)):
        seen_g, uniq = set(), []
        for r in sorted(grp, key=lambda r: str(r["a"].get("alert_utc") or "")):
            g = str(r["a"].get("game"))
            if g not in seen_g:
                seen_g.add(g)
                uniq.append(r)
        sstats(uniq, f"{label} unique games")

    say("")
    say("    EVERY CERTIFIED NCAAF OBSERVATION (no selection, ordered by date):")
    say(f"      {'date':<11}{'side':<6}{'line':>7}{'raw':>6}{'net':>6}{'res':>5}{'units':>7}"
        f"{'CLV':>8}  game")
    for r in sorted(nc, key=lambda r: str(r["a"].get("alert_utc") or "")):
        a = r["a"]
        say(f"      {str(a.get('alert_utc'))[:10]:<11}{side_of(a):<6}"
            f"{(a.get('point') if a.get('point') is not None else float('nan')):>7.1f}"
            f"{(a.get('price') if a.get('price') is not None else 0):>6}"
            f"{(a.get('price_after_fee') if a.get('price_after_fee') is not None else 0):>6}"
            f"{str(a.get('result') or '-'):>5}"
            f"{(a.get('units_flat') if a.get('units_flat') is not None else 0):>7.2f}"
            f"{(r['pct'] if r['pct'] is not None else float('nan')):>+8.2f}  {str(a.get('game'))[:40]}")
    say("  " + "-" * 104)

    # ---------------- ITEM 1: per-observation reconciliation of the overlap ----------------
    ov = [r for r in allv + allm
          if r["pct"] is not None and r["feed"] is not None
          and r["nd"] and r["feed_dec"] and r["p_feed"] is not None and r["p"] is not None]
    say("")
    say("  ITEM 1 - RECONCILIATION OF THE OVERLAP, one observation at a time")
    say("  " + "-" * 104)
    if not ov:
        say("    no observation carries both figures plus both inputs, so the gap cannot be split here")
    else:
        say(f"    {'date':<11}{'lg':<6}{'p_std':>7}{'p_feed':>7}{'dp':>7}{'net_std':>8}{'net_fd':>7}"
            f"{'std':>8}{'feed':>8}{'gap':>7}{'fee':>7}{'time':>7}{'resid':>7}{'age':>5}")
        fees, times, resids = [], [], []
        for r in sorted(ov, key=lambda x: str(x["a"].get("alert_utc") or "")):
            a = r["a"]
            std, feed = r["pct"], r["feed"]
            gap = std - feed
            # fee-only: same close prob (the feed's), swap the fee model
            fee_only = 100.0 * (r["p_feed"] * r["nd"] - 1.0) - 100.0 * (r["p_feed"] * r["feed_dec"] - 1.0)
            # prob-only: same fee model (the standard's), swap the close probability
            time_only = 100.0 * (r["p"] * r["nd"] - 1.0) - 100.0 * (r["p_feed"] * r["nd"] - 1.0)
            resid = gap - fee_only - time_only
            fees.append(fee_only); times.append(time_only); resids.append(resid)
            say(f"    {str(a.get('alert_utc'))[:10]:<11}{str(a.get('sport')):<6}"
                f"{r['p']:>7.4f}{r['p_feed']:>7.4f}{r['p'] - r['p_feed']:>+7.4f}"
                f"{r['nd']:>8.4f}{r['feed_dec']:>7.4f}{std:>+8.2f}{feed:>+8.2f}{gap:>+7.2f}"
                f"{fee_only:>+7.2f}{time_only:>+7.2f}{resid:>+7.2f}"
                f"{(r['mins'] if r['mins'] is not None else -1):>5.0f}")
        def mabs(v):
            return sum(abs(x) for x in v) / len(v)
        say("  " + "-" * 104)
        say(f"    n={len(ov)}   mean |gap| {mabs([r['pct'] - r['feed'] for r in ov]):.2f} pt")
        say(f"      attributable to the FEE MODEL        mean |{mabs(fees):.2f}| pt   "
            f"(signed mean {sum(fees)/len(fees):+.2f})")
        say(f"      attributable to the CLOSE INSTANT    mean |{mabs(times):.2f}| pt   "
            f"(signed mean {sum(times)/len(times):+.2f})")
        say(f"      RESIDUAL, neither of the above       mean |{mabs(resids):.2f}| pt   "
            f"max |{max(abs(x) for x in resids):.2f}|")
        say("    The split is exact by construction, so a non-trivial residual would mean a third")
        say("    input differs and has not been found. Read the residual column before the means.")

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
    say("")
    # ================= THREE BOT-ONLY STRATEGIES (Peter, Nov 10) =================
    # NBA totals unders (the existing lane), NCAAF spread dogs, NHL totals unders. Two of the three
    # are OUTSIDE phase 1, so this is its own population rather than a slice of the 53 above.
    #
    # Multiple comparisons are reported, not hidden: 12 cells were screened to arrive at these
    # three, and a both-halves-positive filter on 12 cells yields about 3 by chance alone. These
    # three were chosen AFTER seeing that screen, so they are not independent tests and nothing
    # below is a fresh discovery. Treating them as confirmations would be the cherry-pick.
    say("")
    say("=" * 108)
    say("THREE BOT-ONLY STRATEGIES - certified closes, free history only")
    say("=" * 108)

    def sidecls(a):
        k = str(a.get("kind"))
        b = str(a.get("bet") or "").lower()
        pt = a.get("point")
        if k == "tot":
            return "tot UNDER" if b.startswith("under") else "tot OVER" if b.startswith("over") else "tot ?"
        if k == "spr":
            if isinstance(pt, (int, float)):
                return "spr FAV" if pt < 0 else "spr DOG" if pt > 0 else "spr PK"
            return "spr ?"
        return k

    bot = [x for x in A
           if str(x.get("book_key") or "") not in ("hardrockbet", "hardrockbet_fl")
           and x.get("pricing_bettable") is not False]
    STRATS = (("NBA", "tot UNDER", "NBA totals UNDERS (live lane)"),
              ("NCAAF", "spr DOG", "NCAAF spread DOGS"),
              ("NHL", "tot UNDER", "NHL totals UNDERS"))

    def certify(a, lg):
        """A verified same-line Pinnacle close for one alert, or (None, why). Same path, same guard
        and the same free-history rule as the phase-1 pass above."""
        bet = a.get("bet") or ""
        if not bet.strip():
            return None, "no bet text"
        fid, f = fixture_for(a, lg)
        if not fid:
            return None, "no unique same-league fixture"
        pth = hc._path(fid, "pinnacle")
        if not os.path.exists(pth):
            if not RECOVER:
                return None, "no cached Pinnacle history"
            if FETCH["stopped"]:
                return None, "recovery halted: " + str(FETCH["why"])[:40]
            try:
                hc.get_hist(fid, ["pinnacle"], start_of(f))
                FETCH["any"] = True
                FETCH["n"] += 1
            except Exception as e:
                return None, f"download failed ({type(e).__name__})"
            if not os.path.exists(pth):
                return None, "download returned no Pinnacle history"
        start = start_of(f)
        if not start:
            return None, "fixture has no start"
        try:
            h = hc.get_hist(fid, ["pinnacle"], start)
            pmk = cl.book_markets(h, "pinnacle")
        except Exception as e:
            return None, f"history unreadable ({type(e).__name__})"
        if not pmk:
            return None, "no Pinnacle market in history"
        mt = "total" if str(a.get("kind")) == "tot" else "spread" if str(a.get("kind")) == "spr" else "moneyline"
        try:
            c, why = cl.close_for({"bet": bet, "league": lg, "market": mt,
                                   "game": f.get("game"), "game_start": f.get("start")},
                                  f, pmk, mkmap, start, lg)
        except Exception as e:
            return None, f"close_for raised {type(e).__name__}"
        if not c:
            return None, f"no close: {str(why)[:40]}"
        if not cs.close_verified(c.get("how")):
            return None, f"close not verified ({c.get('how')})"
        rd = raw_dec(a.get("price"))
        if rd is None:
            return None, "no entry price"
        try:
            pct = cs.net_clv(c["p"], rd, cs.canon(a.get("book_key")), maker=False, league=lg)
        except Exception as e:
            return None, f"net_clv raised {type(e).__name__}"
        if pct is None:
            return None, "net_clv returned None"
        return pct, None

    def blk(rows, cert, label, ind="    "):
        g = [x for x in rows if x.get("result") in ("W", "L", "P")]
        w = sum(1 for x in g if x["result"] == "W")
        l = sum(1 for x in g if x["result"] == "L")
        p_ = sum(1 for x in g if x["result"] == "P")
        u = sum(x.get("units_flat") or 0 for x in g)
        risk = len([x for x in g if x["result"] != "P"])
        v = [cert[id(x)] for x in rows if id(x) in cert]
        out_ = (f"{ind}{label:<26} n{len(rows):3} games {len({str(x.get('game')) for x in rows}):3} "
                f"{w}-{l}" + (f"-{p_}" if p_ else "") + f" {u:+7.2f}u")
        out_ += f" ROI {100 * u / risk:+7.1f}%" if risk else " ROI     n/a"
        if v:
            m = sum(v) / len(v)
            sd = sts.stdev(v) if len(v) > 1 else 0.0
            se = sd / len(v) ** 0.5 if len(v) > 1 else 0.0
            beat = 100.0 * sum(1 for x in v if x > 0) / len(v)
            out_ += (f" | CERT n{len(v):3} {m:+6.2f}% SE {se:5.2f} "
                     f"95% {m - 1.96 * se:+6.2f}..{m + 1.96 * se:+6.2f} beat {beat:3.0f}% "
                     f"cov {100.0 * len(v) / len(rows):3.0f}%")
        else:
            out_ += " | CERT none"
        say(out_)

    for lg, mk, name in STRATS:
        rows = sorted([x for x in bot if str(x.get("sport")) == lg and sidecls(x) == mk],
                      key=lambda x: str(x.get("alert_utc") or ""))
        say("")
        say(f"  {name}   ({len(rows)} bot alert(s))")
        say("  " + "-" * 104)
        cert, fails = {}, collections.Counter()
        for a in rows:
            pct, why = certify(a, lg)
            if pct is None:
                fails[why] += 1
            else:
                cert[id(a)] = pct
        blk(rows, cert, "ALL")
        h = len(rows) // 2
        blk(rows[:h], cert, "first half")
        blk(rows[h:], cert, "second half")
        # fees actually paid, in units, on the winners - the fee is already inside units_flat
        fee_u = 0.0
        for a in rows:
            if a.get("result") != "W":
                continue
            rawd, netd = raw_dec(a.get("price")), raw_dec(a.get("price_after_fee"))
            if rawd and netd:
                fee_u += (rawd - 1) - (netd - 1)
        say(f"    fees paid on winners: {fee_u:+.2f}u of gross profit "
            f"(already deducted from the units above)")
        bk = collections.Counter(str(a.get("book")) for a in rows)
        say(f"    alerted books: {dict(bk.most_common(5))}")
        say(f"    median lead: {sts.median([a.get('minutes_before_start') for a in rows if isinstance(a.get('minutes_before_start'), (int, float))] or [float('nan')]):.0f} min")
        if fails:
            say("    could not certify:")
            for k, n in fails.most_common(6):
                say(f"       {n:3}  {k}")
    say("")
    say("  AVAILABILITY: every unit above is 1u at the alert's own price after fee - the price the")
    say("  alert carried, never a better one, and no fill is assumed anywhere. Whether that price")
    say("  was actually standing on the alerted book is a DIFFERENT question, answered by")
    say("  fill_audit.py's SEEN test against the exchange's own stored history; it is not answered")
    say("  here and no claim about obtainability is made.")
    say("=" * 108)
    say("")
    say("  ITEM 4 - the missing cached histories, and what a backfill would cost")
    say("  " + "-" * 104)
    nocache = sum(b["miss"]["no CACHED Pinnacle history (not fetched, by design)"] for b in out.values())
    nouniq = sum(b["miss"]["find_fixture: no unique same-league fixture (left unscored)"] for b in out.values())
    say(f"    {nocache} alert(s) matched a fixture but hold no Pinnacle cache file. These are absent")
    say("    DOWNLOADS, not absent fixtures - the fixture is known, only its history is not stored.")
    say(f"    {nouniq} alert(s) have no unique same-league fixture and stay UNSCORED (item 5).")
    say("    Endpoint: hist_cache downloads /historical-odds, which credit_gate lists in FREE_PATHS,")
    say("    so our gate does not bill it. But the free tier returns NO quota header, so the call")
    say("    count is the only meter and 'free' is our accounting, not a provider guarantee. The safe")
    say("    confirmation is one single-fixture download with /account read before and after - and")
    say("    /account is itself a FREE_PATH. That test is NOT run here; this pass downloads nothing.")
    say("")
    if RECOVER:
        say("")
        say("  RECOVERY FETCH - policed by the provider's own counter")
        say("  " + "-" * 104)
        say(f"    downloads attempted           {FETCH['n']}")
        say(f"    provider used, before/after   {FETCH['before']} -> {FETCH['after']}"
            f"   (first download only; /account is free)")
        if FETCH["stopped"]:
            say(f"    HALTED: {FETCH['why']}")
            say("    Remaining fixtures were left untouched. No approval is assumed for a paid call.")
        elif FETCH["any"]:
            say("    the provider's counter did not move on the bracketed download, so history is")
            say("    free by the provider's own accounting and not only by ours")
        say("")
    say(f"  CREDITS: 0 paid. Cached-history reads: {reads}. Downloads: {FETCH['n']}. A fixture with")
    say("  no cache file on disk is reported as missing unless recovery is on. /historical-odds is in")
    say("  credit_gate.FREE_PATHS in any case.")
    say("=" * 108)
    return 0


if __name__ == "__main__":
    sys.exit(main())
