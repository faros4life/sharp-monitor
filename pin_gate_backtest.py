#!/usr/bin/env python3
"""
PRE-ORDER PINNACLE GATE - READ-ONLY BACKTEST (Muse's GO, relayed by Peter, Nov 12).

NO DEPLOYMENT. Nothing is changed: no selection rule, no live switch, no sizing, no routing, no
venue priority, no risk limit, no fail-closed protection, no resting-order behaviour, no executor
schedule. No order of any kind. No paid OddsPapi call - the gate's own evidence is already on disk.

THE QUESTION. The proposed gate adds ONE condition to what already runs: our executable after-fee
price must be strictly better than Pinnacle's CURRENT no-vig fair price at the equivalent line.
Condition 1 (fill at the alert price or better) is already enforced, so this measures the
INCREMENTAL effect of condition 2 - Muse's item 6.

WHY THIS CAN BE ANSWERED WITHOUT HINDSIGHT. executor.pin_check() has run at EVERY live order since
Nov 3 and writes its result onto the ledger row as `pin_check`:

    {ok, age_s, changed_s, pin_line, fair_am, gap_pct, why}

gap_pct = (Pinnacle no-vig fair probability x our after-fee decimal - 1) x 100, computed from the
live Pinnacle read AT THE ORDER. That is precisely the proposed condition 2, recorded at decision
time. So the gate is not simulated from later snapshots - it is replayed from what the executor
actually saw. Muse's "no hindsight prices, no future snapshots, no invented historical reads" is
satisfied by construction, because no price is reconstructed here at all.

THE SAMPLE CEILING, STATED UP FRONT. pin_check was added Nov 3 and only runs when a play reaches
WOULD PLACE with live.go - so the population is live order attempts since Nov 3, not all bets. That
is a small number, and no amount of analysis enlarges it. Every figure below carries its n and a
Wilson interval, and where the interval spans zero this says so rather than reading a direction
into noise.

WHAT CANNOT BE ANSWERED FROM THIS DATA, and is reported as a limitation rather than estimated:
  * Pinnacle's price at the moment a RESTING order filled. pin_check runs at submission; the book
    matches a rested bid later with the executor out of the loop, and no Pinnacle read exists for
    that instant. Muse's item 3 comparison of placement-vs-fill price therefore has no source here.
  * Whether a refused bet would have been a better bet. A refusal removes the fill, so its realized
    result exists only because it was NOT refused. Realized units for the refused group describe
    what the gate would have given up, which is the honest framing.
"""
import collections
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import executor as ex
import rest_depth_report as rd
import tracker_build as tb

ET = tb.ET
DAYS = int(os.environ.get("PG_DAYS", "") or "30")
TSTATE = "tracker/state.enc"
L = []
MONEY = re.compile(r"\$\s*[+-]?[\d,]+(?:\.\d+)?")

# pin_check's own refusal strings, split by what they mean for the gate. "no coverage" is the
# category Muse explicitly does NOT want vetoing yet (item 2); "stale" is the freshness gate
# (item 4). Grouping them together would hide exactly the distinction being decided.
NO_COVER = ("game not on Pinnacle", "Pinnacle has no price for this market",
            "bet not mapped to a Pinnacle market", "Pinnacle not readable here")
READ_FAIL = ("Pinnacle read failed", "Pinnacle read has no time", "Pinnacle check error")


def say(t=""):
    L.append(t)
    if MONEY.search(str(t)):
        print("  [line withheld from the public log: carries a dollar amount]")
        return
    print(t)


def priv(t=""):
    L.append(t)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def wilson(k, n):
    """95% interval for a proportion. Small n is the whole story here, so the interval is printed
    everywhere a rate is, and never replaced by the point estimate alone."""
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.959964
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mean_ci(v):
    """(mean, half-width) for a small sample, normal approximation on the standard error. Returns
    None for the half-width below 2 observations, where no interval is meaningful."""
    if not v:
        return (None, None)
    m = sum(v) / len(v)
    if len(v) < 2:
        return (m, None)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    return (m, 1.959964 * sd / math.sqrt(len(v)))


def placed_legs(r):
    """Every order container that actually placed, with which kind it was.

    taker  = live_order, the immediate fill at the chosen venue
    rest   = live_rest, a resting bid the book matches later
    more   = live_more, the next-venue remainder legs

    The split matters because pin_check runs ONCE, before live_order - live_remainder is called
    after it and the resting path is filled with the executor absent. So 'rest' and 'more' legs are
    the ones the proposed gate cannot actually cover, and they are counted separately rather than
    folded into one 'fills' number."""
    out = []
    lo = r.get("live_order") or {}
    if lo.get("status") == "placed" and lo.get("order_id"):
        out.append(("taker", lo))
    lr = r.get("live_rest") or {}
    if lr.get("status") == "placed" and lr.get("order_id"):
        out.append(("rest", lr))
    for o in (r.get("live_more") or []):
        o = o or {}
        if o.get("status") == "placed" and o.get("order_id"):
            out.append(("more", o))
    return out


def lane_of(r):
    s = str(r.get("source") or "").lower()
    if s.startswith("board"):
        return "Board v3"
    if s in ("r1", "lane1") or s.startswith("r1"):
        return "R1"
    if s == "lane2":
        return "Lane 2"
    return "Phase 1"


def line_kind(pc, r):
    """exact | adjacent | unknown - Pinnacle's own line versus the line we took.

    Muse's item 5 keeps these populations apart because the adjacent case relies on the half-point
    conversion, and a conversion good enough to log is not automatically good enough to veto money:
    clv_verified is False on every converted close for exactly this reason."""
    pl, ours = num(pc.get("pin_line")), num(r.get("fill_line"))
    if pl is None or ours is None:
        return "unknown"
    return "exact" if abs(pl - ours) < 1e-9 else "adjacent"


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say("PRE-ORDER PINNACLE GATE - READ-ONLY BACKTEST")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET | window {DAYS}d | fee model {cs.FEE_MODEL}")
    say("NO deployment, no order, no rule/switch/sizing/routing/limit change. 0 paid OddsPapi calls.")
    say("Evidence: executor.pin_check() as recorded on each ledger row AT THE ORDER - replayed,")
    say("not reconstructed, so no hindsight price enters this.")
    say("=" * 100)

    # ---------------------------------------------------------------- the ledger
    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in rd.SUBJECTS:
            r, n = rd.ledger_rows(M, s, since)
            rows += r
            mails += n
    finally:
        try:
            M.logout()
        except Exception:
            pass
    # De-duplicate preferring the row that records a placement - the last-wins rule previously
    # overwrote placements with a later candidate row and undercounted by more than half.
    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if not k:
            continue
        cur = seen.get(k)
        if cur is None or (placed_legs(r) and not placed_legs(cur)):
            seen[k] = r
    say(f"  {mails} ledger email(s), {len(rows)} row(s), {len(seen)} distinct play(s)")

    # ---------------------------------------------------------------- population
    # Only rows that actually reached the order carry a pin_check. A row without one was never a
    # live order attempt, so the gate could not have applied to it and it is not in the population.
    pop = []
    for k, r in seen.items():
        pc = r.get("pin_check")
        if isinstance(pc, dict):
            pop.append((k, r, pc))
    say(f"  live order attempts carrying a pin_check: {len(pop)}")
    if not pop:
        say("")
        say("  ANSWER: UNANSWERABLE from local data. No ledger row in the window carries a")
        say("  pin_check, so the executor made no live order attempt in it. The gate's own")
        say("  evidence is written only at an order, and there are none to replay.")
        say("  This is a SAMPLE limitation, not a defect, and no further analysis changes it.")
        try:
            ex.send("Bets PIN GATE BACKTEST (no population)", "\n".join(L))
        except Exception:
            pass
        return 0

    # ---------------------------------------------------------------- classify
    rec = []
    for k, r, pc in pop:
        why = str(pc.get("why") or "")
        gap = num(pc.get("gap_pct"))
        cover = "no coverage" if any(w in why for w in NO_COVER) else (
            "read failed" if any(w in why for w in READ_FAIL) else "covered")
        stale = ("old (max" in why) or (why.startswith("Pinnacle read") and "s old" in why)
        age = num(pc.get("age_s"))
        # THE GATE, as specified: strictly better than Pinnacle no-vig, equality insufficient.
        # A row with no gap_pct cannot satisfy a strict inequality, so under fail-closed it is a
        # REFUSE - which is precisely the no-coverage question Muse is holding open.
        if gap is None:
            verdict = "REFUSE (no comparison)"
        elif gap > 0:
            verdict = "PASS"
        else:
            verdict = "REFUSE (price)"
        if stale:
            verdict = "REFUSE (stale)"
        rec.append({"key": k, "row": r, "pc": pc, "gap": gap, "cover": cover, "stale": stale,
                    "age": age, "changed": num(pc.get("changed_s")), "verdict": verdict,
                    "lane": lane_of(r), "lk": line_kind(pc, r), "legs": placed_legs(r),
                    "ok": bool(pc.get("ok")), "why": why})

    say("")
    say("=" * 100)
    say("1. PASS vs REFUSE  (condition 2 only - condition 1, alert price or better, already runs)")
    say("=" * 100)
    vc = collections.Counter(x["verdict"] for x in rec)
    n = len(rec)
    for v, c in vc.most_common():
        lo, hi = wilson(c, n)
        say(f"  {v:24s} {c:4d}  {100*c/n:5.1f}%   95% CI {100*lo:5.1f}-{100*hi:5.1f}%")
    npass = vc.get("PASS", 0)
    say(f"  TOTAL                    {n:4d}")
    say("")
    say(f"  The gate would have allowed {npass} of {n} live order attempts and refused {n-npass}.")

    # ---------------------------------------------------------------- CLV by group
    # Certified closing CLV comes from the CLV ledger's own scored rows, never recomputed here.
    # The CLV ledger stores scored rows in st["bets"], keyed by the TRACKER's own bet id
    # ("mn|0ed39.."), and rec["clv"] is a FRACTION (round(p*d - 1, 4)), not a percentage. Neither
    # fact is cosmetic: keying by tracker id means the executor's play key does NOT join to it, so
    # the join below is on game+bet TEXT and is labelled as such. A text join can miss, and a
    # missing CLV is reported as missing - a forced key join would produce a confidently wrong CLV,
    # which is the failure mode that made a hand-rolled matcher read -7.30% on Nov 10.
    scored = {}
    try:
        st = cl.tb.dec(json.load(open(cl.STATE)))
        for kk, r0 in (st.get("bets") or {}).items():
            if r0.get("clv") is None:
                continue
            s = r0.get("snap") or {}
            txt = (str(s.get("game") or "").lower().strip() + "|"
                   + str(s.get("bet") or "").lower().strip())
            scored.setdefault(txt, []).append(r0)
        say(f"  certified CLV available for {sum(len(v) for v in scored.values())} scored row(s) "
            f"across {len(scored)} game+bet text(s)")
    except Exception as e:
        say(f"  CLV ledger unreadable ({type(e).__name__}) - closing CLV columns unavailable")

    joined = 0
    for x in rec:
        r = x["row"]
        txt = (str(r.get("game") or "").lower().strip() + "|"
               + str(r.get("bet") or "").lower().strip())
        v = scored.get(txt) or []
        # several scored rows for one text are the partial fills of one play; their CLV is the
        # same price against the same close, so the mean is that one value, not an average of plays
        vv = [num(z.get("clv")) for z in v if num(z.get("clv")) is not None]
        x["clv"] = (100.0 * (sum(vv) / len(vv))) if vv else None     # fraction -> percent
        if x["clv"] is not None:
            joined += 1
    say(f"  of {n} order attempts, {joined} join to a certified closing CLV (game+bet TEXT join,")
    say("    not an id join - the CLV ledger keys on tracker ids, which the ledger row does not carry)")

    say("")
    say("=" * 100)
    say("2. CLV AND RESULT BY GROUP")
    say("=" * 100)
    say(f"  {'group':<24} {'n':>4} {'cert CLV':>10} {'95% CI':>18} {'beat close':>12}")
    say("  " + "-" * 94)

    def block(name, sel):
        v = [x["clv"] for x in rec if sel(x) and x["clv"] is not None]
        m, h = mean_ci(v)
        beat = sum(1 for z in v if z > 0)
        ci = (f"+/-{h:.2f}" if h is not None else "n/a")
        say(f"  {name:<24} {len(v):4d} {(f'{m:+.2f}%' if m is not None else 'n/a'):>10} {ci:>18} "
            f"{(f'{beat}/{len(v)}' if v else 'n/a'):>12}")
        return v

    vp = block("PASS", lambda x: x["verdict"] == "PASS")
    vr = block("REFUSE (all)", lambda x: x["verdict"].startswith("REFUSE"))
    block("  REFUSE (price)", lambda x: x["verdict"] == "REFUSE (price)")
    block("  REFUSE (no comparison)", lambda x: x["verdict"] == "REFUSE (no comparison)")
    block("  REFUSE (stale)", lambda x: x["verdict"] == "REFUSE (stale)")
    if vp and vr:
        mp, _ = mean_ci(vp)
        mr, _ = mean_ci(vr)
        say("")
        say(f"  difference PASS - REFUSE: {mp - mr:+.2f} percentage points of CLV")
        say("  With these sample sizes, read the intervals above before the difference: if they")
        say("  overlap, this number is not evidence the gate separates good fills from bad.")

    say("")
    say("  by lane:")
    for lane in ("Phase 1", "Board v3", "R1", "Lane 2"):
        sub = [x for x in rec if x["lane"] == lane]
        if sub:
            p = sum(1 for x in sub if x["verdict"] == "PASS")
            say(f"    {lane:<12} attempts {len(sub):3d} | would PASS {p:3d} | REFUSE {len(sub)-p:3d}")

    say("")
    say("  exact line vs adjacent line (Muse item 5 - populations kept apart):")
    for lk in ("exact", "adjacent", "unknown"):
        sub = [x for x in rec if x["lk"] == lk]
        if sub:
            p = sum(1 for x in sub if x["verdict"] == "PASS")
            g = [x["gap"] for x in sub if x["gap"] is not None]
            mg, hg = mean_ci(g)
            say(f"    {lk:<9} n {len(sub):3d} | PASS {p:3d} | mean gap "
                f"{(f'{mg:+.2f}%' if mg is not None else 'n/a')}"
                f"{(f' +/-{hg:.2f}' if hg is not None else '')}")
    adj = [x for x in rec if x["lk"] == "adjacent"]
    if adj:
        near = sum(1 for x in adj if x["gap"] is not None and abs(x["gap"]) < 1.0)
        say(f"    of {len(adj)} adjacent-line attempts, {near} sit within +/-1.00% of the")
        say("    threshold - i.e. the half-point conversion, not the price, decides them.")

    say("")
    say("  taker vs passive legs (Muse item 3):")
    kinds = collections.Counter(kind for x in rec for kind, _ in x["legs"])
    for kk in ("taker", "rest", "more"):
        if kinds.get(kk):
            say(f"    {kk:<6} placed legs {kinds[kk]:4d}"
                + ("   <- pin_check runs before this one" if kk == "taker" else
                   "   <- NOT covered: filled with the executor out of the loop" if kk == "rest" else
                   "   <- NOT covered: live_remainder runs AFTER pin_check"))
    tot = sum(kinds.values())
    unc = kinds.get("rest", 0) + kinds.get("more", 0)
    if tot:
        lo, hi = wilson(unc, tot)
        say(f"    {unc} of {tot} placed legs ({100*unc/tot:.1f}%, 95% CI {100*lo:.1f}-{100*hi:.1f}%)")
        say("    are on paths the proposed gate cannot reach as specified.")

    say("")
    say("=" * 100)
    say("3. COVERAGE AND FRESHNESS (Muse items 2 and 4)")
    say("=" * 100)
    cc = collections.Counter(x["cover"] for x in rec)
    for c, k2 in cc.most_common():
        say(f"  {c:<14} {k2:4d}")
    nocov = [x for x in rec if x["cover"] == "no coverage"]
    if nocov:
        say("")
        say(f"  {len(nocov)} attempt(s) had NO Pinnacle comparison. Under a blanket fail-closed")
        say("  veto these never place. Muse item 2 holds this open; shown separately:")
        for x in nocov[:12]:
            say(f"    {x['lane']:<9} {str(x['row'].get('key'))[:46]:<46} {x['why'][:34]}")
        lgs = collections.Counter(str(x["row"].get("key") or "").split("|")[0] for x in nocov)
        say(f"  by league: {', '.join(f'{a} {b}' for a, b in lgs.most_common())}")

    ages = [x["age"] for x in rec if x["age"] is not None]
    if ages:
        ages.sort()
        say("")
        say(f"  our-read age (age_s): n {len(ages)}, min {ages[0]:.0f}s, "
            f"median {ages[len(ages)//2]:.0f}s, max {ages[-1]:.0f}s")
        for b in (60, 120, 240, 300):
            k2 = sum(1 for a in ages if a <= b)
            say(f"    within {b:3d}s: {k2:3d} of {len(ages)} ({100*k2/len(ages):5.1f}%)")
        say("  A 60s bound on age_s refuses everything above that row. _pin_events() caches per")
        say("  sport and only re-reads above 240s, so this distribution reflects WHERE IN THE")
        say("  CACHE CYCLE the order landed - not whether Pinnacle's quote was actually stale.")
        say("  That is the mechanical objection to 60s against the current cache, and it is also")
        say("  the thing an on-demand per-order read would fix.")
    ch = [x["changed"] for x in rec if x["changed"] is not None]
    if ch:
        ch.sort()
        q = ch[len(ch)//2]
        say("")
        say(f"  market-movement age (changed_s): n {len(ch)}, median {q:.0f}s, max {ch[-1]:.0f}s")
        over = sum(1 for a in ch if a > 60)
        say(f"    Pinnacle had not moved for >60s on {over} of {len(ch)} attempts "
            f"({100*over/len(ch):.1f}%)")
        say("  Muse item 4 is right to exclude changed_s: gating on it would refuse these as")
        say("  'stale' when the quote was current. A quiet market is not a stale market.")

    # ---------------------------------------------------------------- rounding
    say("")
    say("=" * 100)
    say("4. ROUNDING AT THE THRESHOLD (Muse item 4, evaluated separately as asked)")
    say("=" * 100)
    gaps = [x["gap"] for x in rec if x["gap"] is not None]
    if gaps:
        for b in (0.1, 0.25, 0.5, 1.0):
            k2 = sum(1 for g in gaps if abs(g) <= b)
            say(f"  within +/-{b:.2f}% of the threshold: {k2:3d} of {len(gaps)} "
                f"({100*k2/len(gaps):5.1f}%)")
        say("  These are the attempts a rounding allowance would move across the line. Muse asks")
        say("  for no arbitrary margin, and that is right: the figure to report is how many")
        say("  decisions rest on the last rounded point, not a margin chosen to pass more bets.")
        say("  Pinnacle's own price arrives as a whole American point, so a gap inside the width")
        say("  of one point is below the resolution of the inputs either way.")

    # ---------------------------------------------------------------- realized, private
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        brows = list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        prof = {}
        for b in brows:
            if b.get("result") in ("W", "L", "P") and num(b.get("profit")) is not None:
                prof.setdefault(str(b.get("game") or "") + "|" + str(b.get("bet") or ""), []).append(b)
        priv("")
        priv("REALIZED (private): graded tracker rows reachable by game+bet text")
        for v, nm in (("PASS", "would PASS"), ("REFUSE (price)", "would be REFUSED on price")):
            tot2, st2 = 0.0, 0.0
            hit = 0
            for x in rec:
                if x["verdict"] != v:
                    continue
                kk = str(x["row"].get("game") or "") + "|" + str(x["row"].get("bet") or "")
                for b in prof.get(kk, []):
                    tot2 += num(b.get("profit")) or 0.0
                    st2 += num(b.get("stake")) or 0.0
                    hit += 1
            priv(f"  {nm}: {hit} graded row(s), staked ${st2:,.2f}, P&L ${tot2:+,.2f}")
        priv("  A refused bet's realized result exists only because it was NOT refused, so this")
        priv("  describes what the gate would have given up - not what it would have earned.")
    except Exception as e:
        say(f"  realized figures unavailable ({type(e).__name__})")

    say("")
    say("=" * 100)
    say("LIMITATIONS - stated, not estimated around")
    say("=" * 100)
    say("  1. pin_check exists only from Nov 3 and only at live order attempts, so the population")
    say(f"     is {n} attempt(s). No analysis enlarges it.")
    say("  2. Pinnacle's price at the moment a RESTING order filled does not exist anywhere in")
    say("     local data - pin_check runs at submission and the book matches later. Muse item 3's")
    say("     placement-vs-fill comparison has no source here and is NOT estimated.")
    say("  3. Converted (adjacent-line) comparisons inherit the half-point conversion's error. The")
    say("     same conversion is already disqualified from certifying CLV (clv_verified False), so")
    say("     it is reported separately rather than mixed into one PASS rate.")
    say("  4. Both the certified-CLV join and realized P&L are joined on game+bet TEXT, not on an")
    say("     id: the CLV ledger keys on tracker bet ids and tracker_build.bot_match stores no key,")
    say("     so no id is common to both records. Rows that do not join are omitted, never guessed.")
    say("")
    say("=" * 100)
    try:
        ex.send(f"Bets PIN GATE BACKTEST ({n} attempts, {npass} would pass)", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print(f"pin gate backtest: {n} attempts, PASS {npass}, "
          + ", ".join(f"{a}={b}" for a, b in vc.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
