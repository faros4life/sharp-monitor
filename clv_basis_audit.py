#!/usr/bin/env python3
"""
CLV BASIS AUDIT (Peter Nov 5). READ-ONLY. Writes no state, places nothing, changes no rule or threshold.

Why: clv_ledger.close_for() will convert Pinnacle's main line to the bet's line with sharp_monitor.half_point_value()
when Pinnacle had no close at the bet's own number, and the totals tolerance is max(1.5, 0.03 * ppt) - which for an
NBA total at 219.5 permits a 6.585-point walk, then clamps the result to [0.01, 0.99]. Every report so far has mixed
those MODELED closes into one headline with genuinely observed SAME-LINE closes. This audit separates them.

FIRST DELIVERABLE, and the reason this runs ahead of everything else: Lane 1's kill-switch is

    alert = len(bot) >= 50 and sum(r["clv"] for r in bot[-50:]) / 50 < 0

computed with no regard to "how". Lane 1 is totals-only, which puts its bets in NBA totals - the one market with the
6.6-point tolerance. So the question is not academic: it is whether a live safety signal has been reading a reliable
number. This prints the mixed-basis average the switch actually uses, the verified-only average beside it, and the
sample size of each.

Bases, taken from each row's own "how" field - nothing is inferred:
    VERIFIED    how == "own line" or "moneyline"  -> Pinnacle closed on the bet's exact market and number
    MODELED     how == "main X moved to Y"        -> converted; the distance |Y - X| is parsed out and bucketed
    UNAVAILABLE no clv at all                     -> counted, never averaged into anything

The 1.5-point totals cap and any tighter spread cap are PROPOSALS. This script only prices what they WOULD exclude,
by league, market and basis. It applies neither. Original numbers are reported unchanged beside the split.

Private email: CLV percentages, counts and units only - no stakes, no balances, no dollar figures, no account data.
The log prints counts only.
"""
import json
import os
import re
import statistics as stt
from datetime import datetime, timedelta, timezone

import executor as ex
import tracker_build as tb

try:                      # find_fixture(), the fixture cache and the league/billing gates - guarded so the audit degrades, never fails
    import clv_ledger as cl
except Exception as _imp:
    cl = None
    _IMPORT_ERR = str(_imp)[:120]

STATE = "clv/state.enc"
ET = tb.ET
SWITCH_N = 50          # the kill-switch window, as clv_ledger defines it
TOT_CAP = 1.5          # PROPOSED totals cap - priced here, never applied
SPR_CAP = 1.5          # PROPOSED spread cap - priced here, never applied
AGE_BUCKETS = ((5, "0-5 min"), (15, "5-15 min"), (60, "15-60 min"), (10 ** 9, "60+ min"))


def bookof(r):
    # module-level and deliberately NOT named bk: main() binds bk as a local dict, so a helper by
    # that name would be shadowed there and every call would raise TypeError at run time.
    return ((r.get("snap") or {}).get("book") or "?")


def tpa(v):
    """tracker_build.tparse forced tz-aware. A bare date ('2026-10-12') parses NAIVE, and any
    comparison against an aware `now` then raises TypeError - which only fires on the old rows this
    recovery analysis is about. Found by exercising the branch; a green run never reaches it."""
    d = tb.tparse(v)
    return d.replace(tzinfo=timezone.utc) if (d is not None and d.tzinfo is None) else d


def basis(r):
    h = (r.get("how") or "").strip()
    if h in ("own line", "moneyline"):
        return "VERIFIED"
    if h.startswith("main ") and " moved to " in h:
        return "MODELED"
    return "OTHER" if h else "UNAVAILABLE"


def conv_of(r):
    """Conversion distance from the row's own 'how' string: 'main 219.5 moved to 225.5' -> 6.0. None if not modeled."""
    m = re.match(r"^main\s+([+-]?\d+(?:\.\d+)?)\s+moved to\s+([+-]?\d+(?:\.\d+)?)$", (r.get("how") or "").strip())
    if not m:
        return None
    try:
        return round(abs(float(m.group(2)) - float(m.group(1))), 2)
    except Exception:
        return None


def cbucket(c):
    if c is None:
        return "n/a"
    return ("0-0.5" if c <= 0.5 else ">0.5-1.0" if c <= 1.0 else ">1.0-1.5" if c <= 1.5
            else ">1.5-3.0" if c <= 3.0 else ">3.0")


def abucket(age):
    if age is None:
        return "unknown"
    for lim, lab in AGE_BUCKETS:
        if age < lim:
            return lab
    return "60+ min"


def mk_of(r):
    s = r.get("snap") or {}
    bet = (s.get("bet") or "").lower()
    if "over" in bet or "under" in bet:
        return "total"
    return "spread/ml"


def stats(rows):
    if not rows:
        return "n 0"
    cv = [r["clv"] for r in rows]
    return (f"n {len(rows)} | mean CLV {100 * stt.mean(cv):+.2f}% | beat close "
            f"{sum(1 for v in cv if v > 0)}/{len(cv)} ({100 * sum(1 for v in cv if v > 0) / len(cv):.0f}%)")


def main():
    now = datetime.now(timezone.utc)
    if not os.environ.get("TRACKER_PASSPHRASE"):
        print("clv basis audit: TRACKER_PASSPHRASE not set; skipped")
        return
    st = tb.dec(json.load(open(STATE)))
    bets = st.get("bets") or {}

    # the ledger's own definitions, copied verbatim so this audits the same population the switch reads
    scored = sorted([dict(r, id=k) for k, r in bets.items() if r.get("clv") is not None],
                    key=lambda r: r.get("scored") or "")
    bot = [r for r in scored if (r["snap"].get("source") or "") == "bot"]
    man = [r for r in scored if (r["snap"].get("source") or "") != "bot"]
    unavail = [dict(r, id=k) for k, r in bets.items() if r.get("clv") is None]

    L = [f"CLV BASIS AUDIT - READ-ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Separates VERIFIED same-line closes from MODELED (line-converted) ones. Applies nothing; changes no rule,",
         "threshold, stake or execution path. Proposed caps are PRICED here, not enforced.", ""]

    # ---------------------------------------------------------------- 1. the kill-switch
    w = bot[-SWITCH_N:]
    ver = [r for r in w if basis(r) == "VERIFIED"]
    mod = [r for r in w if basis(r) == "MODELED"]
    oth = [r for r in w if basis(r) not in ("VERIFIED", "MODELED")]
    L += ["=" * 60, f"1. LANE 1 KILL-SWITCH AUDIT - last {SWITCH_N} scored BOT bets", "=" * 60,
          f"Bot bets scored in total: {len(bot)}. Window used by the switch: the newest {len(w)}.", ""]
    if not w:
        L.append("No scored bot bets: the switch cannot fire and there is nothing to audit.")
    else:
        mixed = stt.mean([r["clv"] for r in w])
        L += [f"  MIXED BASIS (what the switch actually reads today): {stats(w)}",
              f"  VERIFIED same-line only:                           {stats(ver)}",
              f"  MODELED (line-converted) only:                     {stats(mod)}"]
        if oth:
            L.append(f"  neither (no usable 'how'):                         {stats(oth)}")
        L += ["", f"  Switch arithmetic: mixed average {100 * mixed:+.3f}% -> "
                  f"{'WOULD ALERT' if (len(bot) >= SWITCH_N and mixed < 0) else 'would not alert'}"]
        if ver:
            va = stt.mean([r["clv"] for r in ver])
            L.append(f"  Verified-only average {100 * va:+.3f}% (n {len(ver)}) -> "
                     f"{'WOULD ALERT' if va < 0 else 'would not alert'}")
            L.append("  *** THE TWO DISAGREE - the switch's verdict depends on the basis ***"
                     if (mixed < 0) != (va < 0) else
                     "  The two agree, so the switch's verdict does not turn on the basis in this window.")
        else:
            L.append("  No verified rows in the window: the switch is running entirely on converted closes.")
        if mod:
            cs = [c for c in (conv_of(r) for r in mod) if c is not None]
            if cs:
                L.append(f"  Conversion distances in the window: max {max(cs):g} pt, median {stt.median(cs):g} pt, "
                         f"over {TOT_CAP:g} pt: {sum(1 for c in cs if c > TOT_CAP)} of {len(cs)}")
    L.append("")

    # ---------------------------------------------------------------- 2. basis split, whole ledger
    L += ["=" * 60, "2. BASIS SPLIT - every scored bet", "=" * 60]
    for nm, rows in (("BOT", bot), ("Peter / other", man), ("ALL scored", scored)):
        L.append(f"  {nm}:")
        for b in ("VERIFIED", "MODELED", "OTHER"):
            sub = [r for r in rows if basis(r) == b]
            if sub:
                L.append(f"     {b:<10} {stats(sub)}")
        L.append(f"     original mixed headline, unchanged: {stats(rows)}")
    L.append(f"  UNAVAILABLE (no CLV at all, never averaged anywhere): n {len(unavail)}")
    L.append("")

    # ---------------------------------------------------------------- 3. conversion distance
    L += ["=" * 60, "3. CONVERSION DISTANCE on MODELED rows (parsed from each row's own 'how')", "=" * 60]
    allmod = [r for r in scored if basis(r) == "MODELED"]
    if not allmod:
        L.append("  No modeled closes anywhere in the ledger - every scored bet closed on its own line.")
    else:
        by = {}
        for r in allmod:
            key = f"{(r['snap'].get('league') or '?')} {mk_of(r)}"
            by.setdefault(key, []).append(r)
        for key in sorted(by):
            rows = by[key]
            bk = {}
            for r in rows:
                bk.setdefault(cbucket(conv_of(r)), []).append(r)
            L.append(f"  {key}: {stats(rows)}")
            for b in ("0-0.5", ">0.5-1.0", ">1.0-1.5", ">1.5-3.0", ">3.0", "n/a"):
                if b in bk:
                    L.append(f"       {b:<10} {stats(bk[b])}")
    L.append("")

    # ---------------------------------------------------------------- 4. what a cap would exclude (PRICED, NOT APPLIED)
    L += ["=" * 60, f"4. EXCLUSION PREVIEW - a {TOT_CAP:g}pt totals cap / {SPR_CAP:g}pt spread cap. NOT APPLIED.", "=" * 60,
          "  These are proposals. Nothing below is enforced and no historical result is restated by this run."]
    for nm, rows in (("BOT (real bets)", bot), ("Peter / other (real bets)", man)):
        drop = [r for r in rows if (conv_of(r) or 0) > (TOT_CAP if mk_of(r) == "total" else SPR_CAP)]
        dids = {r["id"] for r in drop}
        keep = [r for r in rows if r["id"] not in dids]
        L += [f"  {nm}: would exclude {len(drop)} of {len(rows)}",
              f"     excluded rows:  {stats(drop)}",
              f"     surviving rows: {stats(keep)}"]
        if drop:
            per = {}
            for r in drop:
                per.setdefault(f"{(r['snap'].get('league') or '?')} {mk_of(r)}", 0)
                per[f"{(r['snap'].get('league') or '?')} {mk_of(r)}"] += 1
            L.append("     by league x market: " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())))
    L += ["  NOTE: paper-test populations (SENT, LIQ-MAIN, SLOW-HR, Lane 2) are NOT in this ledger - it holds real",
          "  bets only. Their exclusion counts come from the per-play exports, reported separately."]
    L.append("")

    # ---------------------------------------------------------------- 5. freshness, by basis
    L += ["=" * 60, "5. CLOSE FRESHNESS by basis (age of Pinnacle's read before start)", "=" * 60]
    for b in ("VERIFIED", "MODELED"):
        rows = [r for r in scored if basis(r) == b]
        if not rows:
            continue
        L.append(f"  {b}:")
        bk = {}
        for r in rows:
            bk.setdefault(abucket(r.get("age_min")), []).append(r)
        for _, lab in AGE_BUCKETS:
            if lab in bk:
                L.append(f"     {lab:<10} {stats(bk[lab])}")
        if "unknown" in bk:
            L.append(f"     {'unknown':<10} {stats(bk['unknown'])}")
    # ---------------------------------------------------------------- 6. WHY 212 BETS HAVE NO CLV
    # Nov 5 (Peter, ranked above everything else in the study): every CLV figure in the system rests on the scored
    # minority. If the unscored majority is unscored for SYSTEMATIC reasons - a book, a league, a fixture-matching
    # failure - then the scored sample is not representative and no CLV figure generalises. This section reports the
    # ledger's OWN reason fields; it infers nothing.
    L += ["=" * 60, f"6. UNSCORED COVERAGE - why {len(unavail)} of {len(bets)} bets have no CLV", "=" * 60,
          f"  Scored: {len(scored)} of {len(bets)} ({100 * len(scored) / max(1, len(bets)):.0f}%). "
          f"Every CLV figure above rests on that share.", ""]

    def tally(rows, keyf, label, top=14):
        c = {}
        for r in rows:
            c[str(keyf(r) or "(blank)")] = c.get(str(keyf(r) or "(blank)"), 0) + 1
        L.append(f"  by {label}:")
        for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:top]:
            L.append(f"     {v:>5}  {k[:96]}")
        if len(c) > top:
            L.append(f"     ... +{len(c) - top} more values")

    tally(unavail, lambda r: r.get("why"), "the ledger's own reason ('why')")
    tally(unavail, lambda r: "done (given up)" if r.get("done") else f"still retrying (tries {r.get('tries') or 0})",
          "retry state")
    tally(unavail, lambda r: (r.get("snap") or {}).get("league"), "league")
    tally(unavail, lambda r: (r.get("snap") or {}).get("book"), "book")
    tally(unavail, lambda r: (r.get("snap") or {}).get("source"), "source")
    tally(unavail, lambda r: ((r.get("snap") or {}).get("game_start") or "")[:7], "game month")
    tally(unavail, lambda r: "fixture matched" if r.get("fixture") else "NO fixture matched", "fixture match")

    # the same cuts on the SCORED rows, so systematic skew is visible as a difference rather than asserted
    L += ["", "  For comparison, the SCORED rows on the same cuts (a large gap here means the scored sample is skewed):"]
    tally(scored, lambda r: (r.get("snap") or {}).get("league"), "league (scored)")
    tally(scored, lambda r: (r.get("snap") or {}).get("book"), "book (scored)")
    tally(scored, lambda r: (r.get("snap") or {}).get("source"), "source (scored)")
    L.append("")

    # ---------------------------------------------------------------- 7. CROSS-TAB: reason x book
    # Nov 5 (agreed first output of the coverage diagnosis): two close marginals - 117 blank-reason rows and 104
    # ProphetX rows - say NOTHING about overlap. 104 + 13 MLB = 117 is arithmetic, not structure: the MLB rows carry
    # their own reason string, so they are not in the blank 117 at all. Only the cross-tab answers whether the
    # never-attempted rows ARE the ProphetX rows. No backfill is specced before this table.
    books = sorted({((r.get("snap") or {}).get("book") or "?") for r in unavail})
    rsn = lambda r: (r.get("why") or "(blank)")
    reasons = sorted({rsn(r) for r in unavail}, key=lambda x: -sum(1 for r in unavail if rsn(r) == x))
    w = max([len(x) for x in reasons] + [20])
    L += ["=" * 60, "7. CROSS-TAB - unscored reason x book (the overlap question)", "=" * 60,
          "  " + "reason".ljust(w) + "".join(f"{b[:11]:>13}" for b in books) + f"{'TOTAL':>8}"]
    for rr in reasons:
        rows = [r for r in unavail if rsn(r) == rr]
        cells = [sum(1 for r in rows if ((r.get("snap") or {}).get("book") or "?") == b) for b in books]
        L.append("  " + rr[:w].ljust(w) + "".join(f"{c:>13}" for c in cells) + f"{len(rows):>8}")
    tot = [sum(1 for r in unavail if ((r.get("snap") or {}).get("book") or "?") == b) for b in books]
    L.append("  " + "TOTAL".ljust(w) + "".join(f"{c:>13}" for c in tot) + f"{len(unavail):>8}")

    # the never-attempted subset, profiled on its own
    na = [r for r in unavail if not r.get("why") and not r.get("tries")]
    L += ["", f"  NEVER ATTEMPTED (blank reason AND tries 0): n {len(na)}"]
    if na:
        for lab, keyf in (("book", lambda r: (r.get("snap") or {}).get("book")),
                          ("source", lambda r: (r.get("snap") or {}).get("source")),
                          ("league", lambda r: (r.get("snap") or {}).get("league")),
                          ("has a game_start", lambda r: "yes" if (r.get("snap") or {}).get("game_start") else "NO"),
                          ("has a line/bet text", lambda r: "yes" if (r.get("snap") or {}).get("bet") else "NO")):
            c = {}
            for r in na:
                c[str(keyf(r) or "(blank)")] = c.get(str(keyf(r) or "(blank)"), 0) + 1
            L.append(f"     by {lab}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1])))
        L.append("     Read this before any backfill: a row missing game_start or bet text cannot be matched at all,")
        L.append("     whereas a row that has both and was still never attempted is a queueing failure, not a data gap.")
    L.append("")

    # ============================================================ 8. BASIS x BOOK
    L += ["=" * 70, "8. BASIS x BOOK on the scored rows", "=" * 70]
    sbk = sorted({bookof(r) for r in scored})
    L.append("  " + "basis".ljust(10) + "".join(f"{b[:11]:>13}" for b in sbk) + f"{'TOTAL':>8}")
    for b in ("VERIFIED", "MODELED", "OTHER"):
        rows = [r for r in scored if basis(r) == b]
        if rows:
            L.append("  " + b.ljust(10) + "".join(f"{sum(1 for r in rows if bookof(r) == x):>13}" for x in sbk)
                     + f"{len(rows):>8}")
    L.append("")

    # ============================================================ 9. RECOVERABILITY
    # Nov 5 (Peter): the spend decision. Priced from the ledger's OWN gates, never assumed:
    #   /fixtures is 1 billable credit per league over a whole [lo,hi] range; /historical-odds is free.
    #   find_fixture() needs sc==2 - a token hit on BOTH participants - so a row naming one side can
    #   never match, however many fixtures we buy. cl.SPORT gates which leagues can be called at all.
    SUP = set(getattr(cl, "SPORT", {}) or {})
    fxc = (st.get("fixtures") or {})
    fetch_days = getattr(cl, "FETCH_DAYS", 14) if cl else 14
    SEP = re.compile(r"\s+(?:vs\.?|v\.?|@|at|-)\s+", re.I)

    def sides(s):
        """How many distinct named sides find_fixture() would have to reach sc==2 on."""
        tms = [(t.get("name") or "").strip() for t in (s.get("teams") or []) if (t.get("name") or "").strip()]
        if len(tms) >= 2:
            return 2, "teams[] names both sides"
        g = s.get("game") or ""
        if len([p for p in SEP.split(g) if tb.toks(p)]) >= 2:
            return 2, "game text names both sides"
        if tms or tb.toks(g):
            return 1, "only ONE side is named - sc==2 is unreachable"
        return 0, "no team names and no usable team token in the game text"

    def candidate(s):
        """Is a fixture for this league already cached inside find_fixture's own 36h window?"""
        lg, gs = s.get("league"), tpa(s.get("game_start"))
        for f in fxc.values():
            if f.get("lg") != lg:
                continue
            fs = tpa(f.get("start"))
            if gs and fs and abs((fs - gs).total_seconds()) > 36 * 3600:
                continue
            return True
        return False

    def classify(r):
        s = r.get("snap") or {}
        lg, gs = s.get("league"), tpa(s.get("game_start"))
        n, why_n = sides(s)
        if r.get("fixture"):
            return "A. fixture ALREADY on the row (the failure is downstream, not matching)", "free"
        if not gs:
            return ("B. NO START TIME - nothing to match a fixture against" if n else
                    "C. NO START and NO team identification"), "no"
        if cl and cl.find_fixture(st, s):
            return "A. resolvable NOW against the cache", "free"
        if n < 2:
            return f"D. INSUFFICIENT IDENTIFICATION - {why_n}", "no"
        if lg not in SUP:
            return f"E. LEAGUE NOT SUPPORTED - {lg or '?'} is not in cl.SPORT, /fixtures cannot be called", "no"
        if candidate(s):
            return "F. MATCH FAILURE - fixtures ARE cached for this league/date and the teams still do not match", "no"
        return "G. RECOVERABLE - fixture absent, league supported, both sides named", "spend"

    cls, cost = {}, {}
    for r in unavail:
        k, c = classify(r)
        cls.setdefault(k, []).append(r)
        cost[r["id"]] = c
    L += ["=" * 70, f"9. RECOVERABILITY of the {len(unavail)} unscored rows", "=" * 70,
          f"  gates read from clv_ledger: FETCH_DAYS={fetch_days}, SPORT={sorted(SUP)}, "
          f"cache holds {len(fxc)} fixtures"
          + ("" if cl else f"   (clv_ledger did NOT import: {_IMPORT_ERR} - sections 9-12 degraded)"), ""]
    for k in sorted(cls):
        cnt = {}
        for r in cls[k]:
            cnt[bookof(r)] = cnt.get(bookof(r), 0) + 1
        L.append(f"  {len(cls[k]):>5}  {k}")
        L.append("           " + ", ".join(f"{a} {b}" for a, b in sorted(cnt.items(), key=lambda kv: -kv[1])))
    L.append("")

    # ============================================================ 10. Novig by window / cache / match
    nv = [r for r in unavail if bookof(r) == "Novig"]
    L += ["=" * 70, f"10. Novig unscored ({len(nv)}) split by WINDOW / CACHE / MATCH", "=" * 70,
          "  Peter's check 2. Three different failures with three different fixes:",
          "    WINDOW = the game predates the fetch floor, so no call was ever made for it",
          "    CACHE  = inside the window but the fixture is not cached (pruned, or league never fetched)",
          "    MATCH  = the fixture IS cached and the team names still do not reach sc==2", ""]
    floor = now - timedelta(days=fetch_days)
    nvb = {}
    for r in nv:
        s = r.get("snap") or {}
        gs = tpa(s.get("game_start"))
        if not gs:
            k = "no start time"
        elif cl and cl.find_fixture(st, s):
            k = "resolvable now (no failure)"
        elif candidate(s):
            k = "MATCH - fixture cached, teams do not match"
        elif gs < floor:
            k = f"WINDOW - game older than the {fetch_days}d fetch floor"
        else:
            k = "CACHE - inside the window, fixture missing"
        nvb[k] = nvb.get(k, 0) + 1
    for k, v in sorted(nvb.items(), key=lambda kv: -kv[1]):
        L.append(f"  {v:>5}  {k}")
    L.append("")

    # ============================================================ 11. RECOVERY BATCHES by bets per credit
    sp = [r for r in unavail if cost[r["id"]] == "spend"]
    L += ["=" * 70, "11. RECOVERY BATCHES - ranked by recoverable bets per credit", "=" * 70,
          "  One /fixtures call covers a whole [from,to] range for ONE league = 1 billable credit.",
          "  /historical-odds is free, so scoring every bet behind a recovered fixture costs nothing more.",
          "  refresh_fixtures() is capped at one call per league per 6h, so a multi-league batch needs",
          "  either separate runs or a one-off loop."]
    if not sp:
        L.append("  NO rows qualify for spend. Buying fixtures would not add a single scored bet.")
    bat = {}
    for r in sp:
        bat.setdefault(((r.get("snap") or {}).get("league") or "?"), []).append(r)
    # Nov 5 (Peter/Muse): MEASURED, not derived. A credit only helps a row the fetch window would
    # actually ask for. clv_ledger line ~745 clamps the request to
    #     d0 = max(game_start, now - FETCH_DAYS)
    # so a game BEFORE the floor is never requested, and buying its league's fixtures today fetches
    # the wrong dates. Three buckets, because they have three different costs:
    #   FUTURE    - game has not started: it scores itself, no credit and no code change
    #   IN-WINDOW - past and inside the floor: a credit recovers it TODAY
    #   PRE-FLOOR - past and older than the floor: needs the window fix FIRST, then the same credit
    def wbucket(r):
        gs = tpa(((r.get("snap") or {}).get("game_start")))
        if gs and gs > now:
            return "future"
        if gs and gs >= floor:
            return "inwin"
        return "prefloor"

    rank = []
    for lg, rows in bat.items():
        ds = sorted((((r.get("snap") or {}).get("game_start") or "")[:10]) for r in rows)
        credits = 1 + (1 if lg == "NCAAF" and not st.get("ncaaf_tid") else 0)
        b = {k: sum(1 for r in rows if wbucket(r) == k) for k in ("future", "inwin", "prefloor")}
        rank.append((b["inwin"] / credits, lg, rows, ds[0], ds[-1], credits, b))
    rank.sort(reverse=True)
    if rank:
        L += ["", "  rank  league   date range                 total  future  in-win  pre-floor  credits  per-credit",
              "  " + "-" * 94]
        for i, (pc, lg, rows, d0, d1, cr, b) in enumerate(rank, 1):
            L.append(f"  {i:>4}  {lg:<8} {d0} to {d1}  {len(rows):>5}  {b['future']:>6}  {b['inwin']:>6}  "
                     f"{b['prefloor']:>9}  {cr:>7}  {pc:>10.1f}")
        tr, tc = sum(len(x[2]) for x in rank), sum(x[5] for x in rank)
        tf = sum(x[6]["future"] for x in rank)
        ti = sum(x[6]["inwin"] for x in rank)
        tp_ = sum(x[6]["prefloor"] for x in rank)
        L.append("  " + "-" * 94)
        L.append(f"  {'ALL':>4}  {'':<8} {'':<25}  {tr:>5}  {tf:>6}  {ti:>6}  {tp_:>9}  {tc:>7}  "
                 f"{ti / max(1, tc):>10.1f}")
        L += ["",
              "  per-credit is IN-WINDOW only: what 4 credits buys with no code change. The pre-floor column",
              "  is what the held window fix unlocks, at the same credit cost - the credits are not the gate.",
              "", "  STAGED COVERAGE LADDER (each step measured, none applied):",
              f"    now                                        {len(scored):>3} of {len(bets)}"
              f"  ({100.0 * len(scored) / max(1, len(bets)):.1f}%)",
              f"    + {ti} in-window recovered for {tc} credit(s)        {len(scored) + ti:>3} of {len(bets)}"
              f"  ({100.0 * (len(scored) + ti) / max(1, len(bets)):.1f}%)",
              f"    + {tf} future games, settle on their own     {len(scored) + ti + tf:>3} of {len(bets)}"
              f"  ({100.0 * (len(scored) + ti + tf) / max(1, len(bets)):.1f}%)",
              f"    + {tp_} pre-floor, needs the window fix      {len(scored) + ti + tf + tp_:>3} of {len(bets)}"
              f"  ({100.0 * (len(scored) + ti + tf + tp_) / max(1, len(bets)):.1f}%)"]
        nmatch = sum(len(v) for k, v in cls.items() if k.startswith("F."))
        ndone = sum(len(v) for k, v in cls.items() if k.startswith("A."))
        L += [f"    + {ndone} already-resolvable, blocked on the done flag"
              f"  {len(scored) + ti + tf + tp_ + ndone:>3} of {len(bets)}"
              f"  ({100.0 * (len(scored) + ti + tf + tp_ + ndone) / max(1, len(bets)):.1f}%)",
              f"    + {nmatch} team-name match failures, code fix only  "
              f"{len(scored) + ti + tf + tp_ + ndone + nmatch:>3} of {len(bets)}"
              f"  ({100.0 * (len(scored) + ti + tf + tp_ + ndone + nmatch) / max(1, len(bets)):.1f}%)",
              "    Everything above this line costs 4 credits in total; the rest is code, not spend."]
        if any(x[1] == "NCAAF" for x in rank) and not st.get("ncaaf_tid"):
            L.append("  NOTE: NCAAF carries +1 credit for the one-off /tournaments lookup (ncaaf_tid not cached).")
    used = (st.get("billable") or {}).get(f"{now:%Y-%m}", 0)
    L += ["", f"  Month-to-date billable consumption (ledger state): {used}",
          f"  CLV_MONTH_CAP in this workflow's env: {os.environ.get('CLV_MONTH_CAP') or '(unset -> code default 1000)'}",
          f"  cl.CAP as this process sees it: {getattr(cl, 'CAP', '?') if cl else '?'}", ""]

    # ============================================================ 12. COVERAGE BEFORE / AFTER
    L += ["=" * 70, "12. PROJECTED CLV COVERAGE, before and after recovery", "=" * 70,
          "  'Recoverable' counts ONLY group G - fixture absent, league supported, both sides named.",
          "  Groups B/C/D/E/F are NOT counted: no credit fixes them. This is an UPPER BOUND, not a",
          "  guarantee - a bought fixture still has to reach sc==2 on the team names.", ""]
    allb = sorted({bookof(r) for r in scored} | {bookof(r) for r in unavail})
    L.append("  book          total   scored  now %   +recoverable   projected   proj %   still unscored")
    L.append("  " + "-" * 92)
    GT = [0, 0, 0]
    for b in allb:
        btot = sum(1 for r in scored if bookof(r) == b) + sum(1 for r in unavail if bookof(r) == b)
        bsc = sum(1 for r in scored if bookof(r) == b)
        brc = sum(1 for r in sp if bookof(r) == b)
        GT[0] += btot
        GT[1] += bsc
        GT[2] += brc
        L.append(f"  {b[:12]:<12} {btot:>6}   {bsc:>6}  {100.0 * bsc / max(1, btot):>5.1f}%   {brc:>12}   "
                 f"{bsc + brc:>9}   {100.0 * (bsc + brc) / max(1, btot):>5.1f}%   {btot - bsc - brc:>14}")
    L.append("  " + "-" * 92)
    L.append(f"  {'PORTFOLIO':<12} {GT[0]:>6}   {GT[1]:>6}  {100.0 * GT[1] / max(1, GT[0]):>5.1f}%   {GT[2]:>12}   "
             f"{GT[1] + GT[2]:>9}   {100.0 * (GT[1] + GT[2]) / max(1, GT[0]):>5.1f}%   "
             f"{GT[0] - GT[1] - GT[2]:>14}")
    L += ["", f"  Baseline for the record: {GT[1]} of {GT[0]} ({100.0 * GT[1] / max(1, GT[0]):.1f}%).",
          "  The ledger is PRESERVED - this script writes nothing. Re-running this section after any",
          "  recovery gives the MEASURED after-figure against that baseline.", ""]

    # ============================================================ 13. ProphetX - separate track
    px = [r for r in unavail if bookof(r) == "ProphetX"]
    L += ["=" * 70, f"13. ProphetX ({len(px)}) - SEPARATE ingestion/identification track", "=" * 70,
          "  Peter, Nov 5: fixture recovery does not address these. Free history cannot help a row whose",
          "  game and bet are unknown. The question is whether the EXISTING ESPN start-time backfill",
          "  (<=6 tries, settled within 45 days) ever ran on them, or never reached them at all."]
    for lab, fn in (("espn_tries", lambda r: r.get("espn_tries", 0)),
                    ("has game_start", lambda r: "yes" if (r.get("snap") or {}).get("game_start") else "no"),
                    ("has bet text", lambda r: "yes" if (r.get("snap") or {}).get("bet") else "no"),
                    ("named sides", lambda r: sides(r.get("snap") or {})[0]),
                    ("settled age", lambda r: ("no date" if not tpa((r.get("snap") or {}).get("settled"))
                                               else "<=45d"
                                               if (now - tpa((r.get("snap") or {}).get("settled"))).days <= 45
                                               else ">45d (past the backfill window)"))):
        cnt = {}
        for r in px:
            cnt[str(fn(r))] = cnt.get(str(fn(r)), 0) + 1
        L.append(f"  by {lab:<15}: " + ", ".join(f"{k} = {v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])))
    L.append("")

    # ============================================================ 14. never attempted but HAS a start
    q = [r for r in unavail if not r.get("why") and not r.get("tries") and (r.get("snap") or {}).get("game_start")]
    L += ["=" * 70, f"14. NEVER ATTEMPTED yet HAS a start time ({len(q)}) - queueing, not a data gap", "=" * 70]
    for r in q[:20]:
        s = r.get("snap") or {}
        gs = tpa(s.get("game_start"))
        L.append(f"   {s.get('league') or '?':<6} {bookof(r):<10} {(s.get('game_start') or '')[:16]}"
                 f" | past start+{getattr(cl, 'SCORE_AFTER_MIN', '?') if cl else '?'}min: "
                 f"{'yes' if (gs and now > gs) else 'NO - game is in the future'}"
                 f" | sides {sides(s)[0]} | {(s.get('bet') or '(no bet text)')[:26]}")
    if len(q) > 20:
        L.append(f"   ... +{len(q) - 20} more")
    L.append("")

    # ============================================================ 15. DONE-FLAG + NAME-MATCH INSPECTION
    # Nov 5 (Peter): "Inspect the 15 done-flags and the 25 name mismatches before clearing or
    # normalizing anything." Read-only - nothing is cleared, reset or normalized by this script.
    # Step 3 of the ledger skips any row with done=True:
    #     if rec.get("clv") is not None or rec.get("done"): continue
    # so a done row is unreachable by the widened window until its flag is cleared.
    L += ["=" * 70, "15. DONE-FLAG and NAME-MATCH INSPECTION (read-only, nothing cleared)", "=" * 70]
    grp = {r["id"]: classify(r)[0][:2] for r in unavail}
    L += ["  A. done x recoverability group x window bucket - what the window fix can actually reach:",
          "     group  done  retrying   future  in-win  pre-floor   what unblocks it"]
    for g in sorted(set(grp.values())):
        rows = [r for r in unavail if grp[r["id"]] == g]
        dn = sum(1 for r in rows if r.get("done"))
        wb = {k: sum(1 for r in rows if wbucket(r) == k) for k in ("future", "inwin", "prefloor")}
        need = ("window fix + clearing done" if g == "G." and dn else
                "window fix alone" if g == "G." else
                "name normalisation + clearing done" if g == "F." and dn else
                "name normalisation" if g == "F." else
                "clearing done only" if g == "A." and dn else
                "nothing - already resolvable" if g == "A." else "not recoverable")
        L.append(f"     {g:<6} {dn:>4}  {len(rows) - dn:>8}   {wb['future']:>6}  {wb['inwin']:>6}  "
                 f"{wb['prefloor']:>9}   {need}")
    gdone = sum(1 for r in unavail if grp[r["id"]] == "G." and r.get("done"))
    L += ["", f"     MEASURED: {gdone} of the {sum(1 for r in unavail if grp[r['id']] == 'G.')} group-G rows carry "
          f"done=True. The window fix alone recovers the other "
          f"{sum(1 for r in unavail if grp[r['id']] == 'G.') - gdone}.", ""]
    L.append("  B. why the done rows gave up (their own 'why' and try count):")
    wc = {}
    for r in unavail:
        if r.get("done"):
            wc[f"{(r.get('why') or '(no reason recorded)')[:52]} | tries {r.get('tries', 0)}"] = \
                wc.get(f"{(r.get('why') or '(no reason recorded)')[:52]} | tries {r.get('tries', 0)}", 0) + 1
    for k, v in sorted(wc.items(), key=lambda kv: -kv[1]):
        L.append(f"     {v:>5}  {k}")
    L.append("")

    # C. replay find_fixture's own scoring on the F rows and report WHERE it fell short of sc==2
    def diag(s):
        lg, gs = s.get("league"), tpa(s.get("game_start"))
        words = (tb.toks(" ".join(t.get("name", "") for t in s.get("teams") or []))
                 or tb.toks(s.get("game")))
        best, sc, tsb = None, -1, -1
        for f in fxc.values():
            if f.get("lg") != lg:
                continue
            fs = tpa(f.get("start"))
            if gs and fs and abs((fs - gs).total_seconds()) > 36 * 3600:
                continue
            h = (1 if tb.toks(f["p1"]) & words else 0) + (1 if tb.toks(f["p2"]) & words else 0)
            t_ = len(tb.toks(f["p1"]) & words) + len(tb.toks(f["p2"]) & words)
            if h > sc or (h == sc and t_ > tsb):
                best, sc, tsb = f, h, t_
        return words, best, sc

    frows = [r for r in unavail if grp[r["id"]] == "F."]
    L += [f"  C. the {len(frows)} match failures, scored exactly as find_fixture() scores them",
          "     (sc==2 is required; sc==1 means one side matched, sc==0 means no token overlap at all):"]
    verdict = {}
    for r in frows[:25]:
        s = r.get("snap") or {}
        words, best, sc = diag(s)
        if not best:
            verdict["no candidate fixture in the 36h window"] = verdict.get("no candidate fixture in the 36h window", 0) + 1
            L.append(f"     sc  -  {s.get('league') or '?':<6} {bookof(r):<8} no candidate | bet words "
                     f"{sorted(words)[:5]}")
            continue
        w1, w2 = tb.toks(best["p1"]), tb.toks(best["p2"])
        miss = "p2" if (w1 & words) and not (w2 & words) else "p1" if (w2 & words) else "both"
        v = (f"sc {sc}: only {('p1' if miss == 'p2' else 'p2')} matched, {miss} did not" if sc == 1
             else "sc 0: no token overlap with either side" if sc == 0 else f"sc {sc}")
        verdict[v] = verdict.get(v, 0) + 1
        L.append(f"     sc {sc}  {s.get('league') or '?':<6} {bookof(r):<8} bet {sorted(words)[:4]}")
        L.append(f"            fixture p1 {sorted(w1)[:4]} | p2 {sorted(w2)[:4]} | unmatched side: {miss}")
    if len(frows) > 25:
        L.append(f"     ... +{len(frows) - 25} more")
    L += ["", "     verdict counts over the rows shown:"]
    for k, v in sorted(verdict.items(), key=lambda kv: -kv[1]):
        L.append(f"       {v:>4}  {k}")
    L += ["",
          "     Read this before normalising: an sc==1 row is a one-sided naming gap (an abbreviation or a",
          "     short name) and normalisation plausibly fixes it. An sc==0 row shares no token with either",
          "     participant, which is more often the WRONG GAME than a spelling problem - normalising names",
          "     would not fix it and could create a false match. These two need different treatment.", ""]

    # ============================================================ 16. SCORED-ROW FIXTURE VALIDATION
    # Nov 5 (Peter, check 2): "Previously stored fixture IDs can bypass the new matcher. Please verify
    # that the 65 scored bets, particularly the 34 newly recovered, reference the correct games and
    # betting sides. This should be a read-only validation first."
    # Nothing is changed here. A row that fails is REPORTED, never un-scored - invalidating an
    # assignment needs Peter's word, per his condition 3.
    L += ["=" * 70, "16. SCORED-ROW FIXTURE VALIDATION (read-only, nothing changed)", "=" * 70,
          "  Re-tests each scored row's STORED fixture against the hardened rule, which the stored id",
          "  otherwise bypasses (both call sites read rec['fixture'] before calling find_fixture).", ""]

    def quals(s):
        """Every fixture that would qualify under the HARDENED rule - the list, not just the winner."""
        lg, gs = s.get("league"), tpa(s.get("game_start"))
        words = (tb.toks(" ".join(t.get("name", "") for t in s.get("teams") or []))
                 or tb.toks(s.get("game"))) - tb.WEAK
        out = []
        if not words:
            return out, words
        # Call the LEDGER'S OWN per-fixture test. A second implementation that merely agrees today is
        # how the earlier divergence started: the audit required uniqueness while the ledger did not.
        # The local copy below is a fallback for the case where clv_ledger could not be imported, and
        # it is the only thing here that could ever drift - it is kept deliberately minimal.
        for fid, f in fxc.items():
            if cl is not None and hasattr(cl, "_qualifies"):
                if cl._qualifies(f, lg, gs, words):
                    out.append(fid)
                continue
            if f.get("lg") != lg:
                continue
            fs = tpa(f.get("start"))
            if gs and fs and abs((fs - gs).total_seconds()) > 36 * 3600:
                continue
            a = (tb.toks(f.get("p1") or "") - tb.WEAK) & words
            c = (tb.toks(f.get("p2") or "") - tb.WEAK) & words
            if a and c and (a - c) and (c - a) and max(len(a), len(c)) >= 2:
                out.append(fid)
        return out, words

    NEW_FROM = "2026-11-05T14:56"          # the recovery run; rows scored at or after it are the new ones
    v = {}
    fails, sides = [], []
    for r in scored:
        s = r.get("snap") or {}
        fid = r.get("fixture")
        tag = "new" if (r.get("scored") or "") >= NEW_FROM else "pre-existing"
        if not fid:
            v[f"{tag}: no fixture id on the row (scored another way)"] = \
                v.get(f"{tag}: no fixture id on the row (scored another way)", 0) + 1
            continue
        f = fxc.get(fid)
        if not f:
            v[f"{tag}: fixture no longer cached - cannot re-validate"] = \
                v.get(f"{tag}: fixture no longer cached - cannot re-validate", 0) + 1
            continue
        ok, words = quals(s)
        lg_ok = (f.get("lg") == s.get("league"))
        gs, fs = tpa(s.get("game_start")), tpa(f.get("start"))
        dt_ok = not (gs and fs) or abs((fs - gs).total_seconds()) <= 36 * 3600
        if fid in ok and len(ok) == 1 and lg_ok and dt_ok:
            k = f"{tag}: PASS - stored fixture is the unique hardened match"
        elif fid in ok and len(ok) > 1:
            k = f"{tag}: AMBIGUOUS - stored fixture qualifies but so do {len(ok) - 1} other(s)"
            fails.append((r, f, ok, "ambiguous"))
        elif not lg_ok:
            k = f"{tag}: LEAGUE MISMATCH"
            fails.append((r, f, ok, "league"))
        elif not dt_ok:
            k = f"{tag}: DATE OUTSIDE 36h"
            fails.append((r, f, ok, "date"))
        else:
            k = f"{tag}: WOULD NOT BE CHOSEN NOW - fails the hardened rule"
            fails.append((r, f, ok, "hardened"))
        v[k] = v.get(k, 0) + 1
        # side check: the bet text must resolve to exactly one participant
        try:
            pb = tb.parse_bet(s.get("bet") or "", bool(s.get("flip")))
        except Exception:
            pb = None
        if pb and pb[0] in ("spread", "ml") and pb[1]:
            w = tb.toks(pb[1]) - tb.WEAK
            h1 = bool((tb.toks(f.get("p1") or "") - tb.WEAK) & w)
            h2 = bool((tb.toks(f.get("p2") or "") - tb.WEAK) & w)
            if h1 == h2:                   # neither side, or BOTH - the side is not established
                sides.append((r, f, pb[1], "both sides" if h1 else "neither side"))

    L.append("  A. stored fixture re-validated:")
    for a, b in sorted(v.items(), key=lambda kv: -kv[1]):
        L.append(f"     {b:>5}  {a}")
    L += ["", f"  B. rows whose stored fixture would NOT be chosen now: {len(fails)}"]
    for r, f, ok, kind in fails[:15]:
        s = r.get("snap") or {}
        L.append(f"     [{kind}] {s.get('league') or '?':<6} {bookof(r):<9} clv {r.get('clv')} | "
                 f"bet {(s.get('bet') or '')[:24]}")
        L.append(f"            stored fixture: {(f.get('n1') or f.get('p1') or '?')[:26]} vs "
                 f"{(f.get('n2') or f.get('p2') or '?')[:26]} | qualifying now: {len(ok)}")
    if len(fails) > 15:
        L.append(f"     ... +{len(fails) - 15} more")
    L += ["", f"  C. rows whose BETTING SIDE is not established by the fixture names: {len(sides)}"]
    for r, f, txt, kind in sides[:12]:
        s = r.get("snap") or {}
        L.append(f"     {s.get('league') or '?':<6} {bookof(r):<9} side text {txt[:18]!r} matches {kind} | "
                 f"{(f.get('n1') or '?')[:18]} vs {(f.get('n2') or '?')[:18]}")
    if len(sides) > 12:
        L.append(f"     ... +{len(sides) - 12} more")
    L.append("")

    # ---- D. ambiguity census: answers the Colorado/Dallas question directly
    L += ["  D. AMBIGUITY CENSUS on the unmatched rows - how many fixtures qualify under the hardened",
          "     rule. Exactly 1 means it SHOULD have matched; 2+ means the uniqueness check correctly",
          "     refused to guess; 0 means the fixture genuinely is not cached.", ""]
    cen, multi = {}, []
    for r in unavail:
        s = r.get("snap") or {}
        if not tpa(s.get("game_start")):
            continue
        ok, words = quals(s)
        cen[len(ok) if len(ok) < 3 else "3+"] = cen.get(len(ok) if len(ok) < 3 else "3+", 0) + 1
        if len(ok) >= 1:
            multi.append((r, ok, words))
    for a in sorted(cen, key=lambda x: str(x)):
        L.append(f"     {cen[a]:>5}  {a} qualifying fixture(s)")
    L += ["", f"     rows with at least one qualifying fixture ({len(multi)}) - these are the ones to look at:"]
    for r, ok, words in multi[:12]:
        s = r.get("snap") or {}
        L.append(f"     {s.get('league') or '?':<6} {bookof(r):<9} n={len(ok)} | bet {sorted(words)[:4]} | "
                 f"why {(r.get('why') or '-')[:28]}")
        for fid in ok[:3]:
            f = fxc.get(fid) or {}
            L.append(f"            cand {(f.get('n1') or f.get('p1') or '?')[:24]} vs "
                     f"{(f.get('n2') or f.get('p2') or '?')[:24]}  start {(f.get('start') or '')[:16]}")
    if len(multi) > 12:
        L.append(f"     ... +{len(multi) - 12} more")
    L.append("")
    L += ["", "Read-only: this script wrote no state and changed no rule. Verified and modeled CLV are never again to",
          "be combined into a primary headline."]

    body = "\n".join(L)
    ex.send("Bets CLV BASIS AUDIT (read-only)", body)
    print(f"clv basis audit: scored {len(scored)}, bot {len(bot)}, verified "
          f"{sum(1 for r in scored if basis(r) == 'VERIFIED')}, modeled "
          f"{sum(1 for r in scored if basis(r) == 'MODELED')}, no-CLV {len(unavail)}")


if __name__ == "__main__":
    main()
