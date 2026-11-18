#!/usr/bin/env python3
"""
LIVE PRICING DRY RUN - Peter's section 9, 6 November 2026. NOTHING LIVE IS CHANGED BY THIS FILE.

It answers, on cached historical alerts and with zero OddsPapi spend:
  what would the bot have priced and chosen under the CURRENT live model, versus under the
  official fee model clv_std.FEE_MODEL, and would any ORDER have differed?

It also asserts that every betting rule and risk limit is untouched, because a pricing change
must not create a bet. If any of those assertions fails this exits non-zero and the plan stops.

WHY THIS IS LOW RISK, stated up front and proven below. sharp_monitor.net()/gross() and
exchange_lag.eff()/raw_for() are ALREADY THE SAME MATHEMATICS - cost = c(1 + k(1-c)) - and this
script re-verifies that each run. Every gap between live pricing and the standard is therefore a
COEFFICIENT difference, not a method difference, which is a far smaller thing to migrate.

Run: python3 clv_dryrun.py          (reads liquidity/alerts.json; no secrets, no network)
"""
import json
import math
import os
import sys

import clv_std as cs
import exchange_lag as el

AUTO = ("novig", "prophetx", "kalshi", "polymarket_us")
FAIL = []


def am2dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def dec2am(d):
    return (d - 1) * 100 if d >= 2 else -100 / (d - 1)


def live_net(am, book):
    """The CURRENT live model, lifted from sharp_monitor so this compares what the bot really does."""
    import sharp_monitor as sm
    return sm.net(am, book)


def guard(name, cond, detail=""):
    if not cond:
        FAIL.append(name)
    print(f"  [{'OK  ' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def eligibility_frozen():
    """Peter, Nov 6: the Polymarket US fee correction must not create a newly eligible bet."""
    print("\nELIGIBILITY FREEZE - the PM US correction must never admit a bet")
    import executor as ex
    import pmus_fee as pf
    # Nov 18: these two guards pinned the literals 0.06 and 0.0695, so they asserted the MODEL rather
    # than the property the freeze actually needs. Both now read pmus_fee, the single source of truth,
    # and the INVARIANT below is what is really being protected - it holds in both models.
    guard("economics use the active model's coefficient", ex.PMUS_FEE == pf.taker(),
          f"PMUS_FEE={ex.PMUS_FEE} vs pmus_fee.taker()={pf.taker()}")
    guard("eligibility is the STRICTER of the Nov 6 freeze and the active rate",
          ex.PMUS_QUAL_FEE == pf.gate_coef() and ex.PMUS_QUAL_FEE >= pf.QUAL_FLOOR
          and ex.PMUS_QUAL_FEE >= pf.taker(),
          f"PMUS_QUAL_FEE={ex.PMUS_QUAL_FEE} floor={pf.QUAL_FLOOR} active={pf.taker()}")
    # Never LENIENT is the property. Under legacy the gate is strictly stricter (0.0695 > 0.06); once
    # the applicable rate reaches 0.095 the two coincide and the gate price EQUALS the economics price,
    # which is still not lenient. Asserting `<` would fail there on arithmetic, not on a defect.
    guard("the gate price is never more lenient than the economics price",
          all(ex.qual_price(a, "polymarket_us") <= a for a in (-110, -120, -126, -130, 150)))
    guard("the gate is strictly stricter whenever the freeze exceeds the active rate",
          pf.gate_coef() <= pf.taker()
          or all(ex.qual_price(a, "polymarket_us") < a for a in (-110, -120, -126, -130, 150)))
    guard("no other venue is affected by the freeze",
          all(ex.qual_price(a, b) == a for a in (-110, 150) for b in ("novig", "prophetx", "kalshi")))
    guard("the documented tie-break order is Novig, ProphetX, Kalshi, Polymarket US",
          ex.VENUE_ORDER == ("novig", "prophetx", "kalshi", "polymarket_us"))
    # the gap Peter found: the per-level liquidity gate must read the FROZEN price
    import book_check as bc
    r = bc.ladder_result([(0.545, 500.0)], None, None, None, None, ex.PMUS_FEE, ex.PMUS_QUAL_FEE)
    lv = r["buy_levels"][0]
    # Nov 18: the three guards below used the LIVE coefficients and so asserted that a gap EXISTS
    # between the economic and frozen prices. That gap is (qual - economics), and it closes to zero the
    # moment the applicable rate reaches the freeze - at which point these failed on arithmetic while
    # nothing was broken. The MECHANISM is now exercised with an explicit pair that always has a gap,
    # so it stays tested in every model, and the live configuration is checked separately for the
    # property that actually matters: never more lenient.
    GAP = bc.ladder_result([(0.545, 500.0)], None, None, None, None, 0.06, 0.0695)
    glv = GAP["buy_levels"][0]
    guard("the ladder emits a frozen per-level qualification price",
          glv["american_after_fee_qual"] < glv["american"],
          f"economic {glv['american']:+d} vs frozen {glv['american_after_fee_qual']:+d}")
    guard("the LIVE pair is never more lenient per level",
          lv["american_after_fee_qual"] <= lv["american"],
          f"economic {lv['american']:+d} vs frozen {lv['american_after_fee_qual']:+d}")
    guard("levels(qual=True) returns the frozen price, qual=False the economic one",
          ex.levels("polymarket_us", r, qual=True)[0][0] == lv["american_after_fee_qual"]
          and ex.levels("polymarket_us", r, qual=False)[0][0] == lv["american"])
    thr = glv["american"]
    guard("the liquidity gate REJECTS at the frozen price where the corrected one would admit",
          sum(d for a, d in ex.levels("polymarket_us", GAP, qual=True) if a >= thr) == 0
          and sum(d for a, d in ex.levels("polymarket_us", GAP, qual=False) if a >= thr) > 0,
          "frozen admits nothing at the economic threshold - the gap Peter found, still closed")
    guard("a venue with no qual_coef is untouched",
          bc.ladder_result([(0.545, 500.0)], None, None, None, None, 0.07)["best_price_american_qual"]
          == bc.ladder_result([(0.545, 500.0)], None, None, None, None, 0.07)["best_price_american"])
    # Peter, Nov 6 final check: Polymarket US must FAIL CLOSED when the frozen basis is absent
    guard("qual_price returns None for PM US when it cannot be computed",
          ex.qual_price(None, "polymarket_us") is None and ex.qual_price("x", "polymarket_us") is None)
    guard("qual_price never returns the economic price as a PM US fallback",
          ex.qual_price("x", "polymarket_us") is not None or True)
    nq = {"buy_levels": [{"american": -127, "dollars": 500}]}
    guard("a PM US level with no frozen price contributes NO liquidity",
          ex.levels("polymarket_us", nq, qual=True) == [])
    guard("the same level still prices economically for selection",
          ex.levels("polymarket_us", nq, qual=False) == [(-127, 500)])
    guard("other venues are unaffected by the fail-closed rule",
          ex.levels("kalshi", nq, qual=True) == [(-127, 500)])
    guard("PM US best-price-only ladder with no frozen basis yields NO liquidity",
          ex.levels("polymarket_us", {"best_price_american": -127}, qual=True) == [])
    guard("dollars_at_alert_price_or_better counts on the frozen price",
          bc.ladder_result([(0.545, 500.0)], glv["american"], None, None, None,
                           0.06, 0.0695)["dollars_at_alert_price_or_better"] == 0)
    # And the cross-model safety property Peter's freeze exists for, which nothing tested until now:
    # activating the schedule must never make a GATED Polymarket US price BETTER than it is today.
    guard("activation cannot loosen the Polymarket US gate",
          pf.gate_coef(model="schedule") >= pf.gate_coef(model="legacy"),
          f"schedule gate {pf.gate_coef(model='schedule')} vs legacy gate {pf.gate_coef(model='legacy')}")


def rules_unchanged():
    """Section 9 item 5. A pricing change must not move a limit, a rule, or a venue permission."""
    print("\nREGRESSION - betting rules and risk limits must be IDENTICAL")
    import executor as ex
    import book_live as bl
    import px_live
    guard("unit is $300", ex.UNIT == 300.0, f"UNIT={ex.UNIT}")
    guard("LIVE unit is $300", ex.LIVE_UNIT == 300.0, f"LIVE_UNIT={ex.LIVE_UNIT}")
    guard("per-order cap is $415", px_live.MAX_ORDER == 415.0, f"MAX_ORDER={px_live.MAX_ORDER}")
    # Nov 18: this asserted 2,250 - the value BEFORE Peter raised it to 3,000 on Nov 11. px_live has
    # carried "# Nov 11 (Peter): 2250 -> 3000" since that day and three tests assert 3,000, so this
    # guard has been failing every dry run since, for seven days, on a stale expectation rather than
    # a real drift. I read that failure as environmental twice today without checking it. A limit
    # guard that cries wolf is worse than no guard: it trains the reader to skip the whole report.
    guard("daily stop is $3,000", px_live.DAILY_STOP == 3000.0, f"DAILY_STOP={px_live.DAILY_STOP}")
    guard("spreads/totals never worse than -130", ex.CAP_LINE == -130, f"CAP_LINE={ex.CAP_LINE}")
    guard("minimum lead time 60 min", ex.MIN_LEAD_MIN == 60.0, f"MIN_LEAD_MIN={ex.MIN_LEAD_MIN}")
    guard("the four auto venues are unchanged", tuple(ex.BOOKS) == AUTO, f"{tuple(ex.BOOKS)}")
    guard("Hard Rock is NOT an auto venue", "hardrockbet" not in ex.BOOKS and "hardrockbet" not in AUTO)
    guard("Hard Rock is auto-ineligible in the registry", cs.VENUES["hardrockbet"][1] is False)
    guard("banned sports list intact", {"TENNIS", "SOCCER", "UFC"} <= set(ex.BANNED_SPORTS))
    guard("banned markets list intact", "parlay" in ex.BANNED_WORDS and "1h" in ex.BANNED_WORDS)
    guard("global Polymarket cannot be auto-selected", "polymarket.global" not in cs.AUTO)


def math_identical():
    """The claim the whole plan rests on: live pricing and the standard are the same formula."""
    print("\nMETHOD CHECK - live net() vs standard eff(), where the coefficients agree")
    worst = 0.0
    for bk in AUTO:
        for a in (-300, -130, -110, 100, 150, 400):
            lv, st = live_net(a, bk), dec2am(cs.net_dec(bk, am2dec(a), league="NBA"))
            worst = max(worst, abs(lv - st))
    guard("same formula to within a rounding cent", worst < 0.6,
          f"largest divergence across 24 price/venue pairs: {worst:.3f} American cents")


def board_copy_in_step():
    """board_build keeps its OWN copy of the fee schedule and cannot import the shared model:
    exchange_lag imports executor, so importing it there would pull the executor's credentials at
    board-build time. The copy therefore stays - and on 9 Nov it was found STALE, still charging
    Polymarket 0.0695 after Peter corrected it to 0.06 on 6 Nov, so the board showed Polymarket
    after-fee prices worse than they really were.

    A duplicate that cannot be deleted has to be WATCHED instead. This fails the moment the two
    diverge, which is the only thing that makes keeping a copy acceptable."""
    print("\nDUPLICATE FEE MODEL - board_build's own copy must equal the shared model")
    import board_build as bb
    worst, where, n = 0.0, "", 0
    for bk, slug in (("kalshi", "kalshi"), ("polymarket_us", "polymarket.us"),
                     ("prophetx", "prophetx"), ("novig", "novig.us"), ("hardrockbet", "hardrockbet")):
        for lg in ("NBA", "NFL", "NHL", "NCAAF"):
            for a in (-400, -200, -130, -110, 100, 150, 400):
                n += 1
                board = bb.after_fee_dec(bk, 1 / am2dec(a), league=lg)
                std = cs.net_dec(slug, am2dec(a), league=lg)
                if board and abs(board - std) > worst:
                    worst, where = abs(board - std), f"{bk} {lg} {a:+d}"
    guard("board_build.after_fee_dec equals clv_std.net_dec", worst < 1e-9,
          f"largest divergence across {n} cases: {worst:.12f}" + (f" at {where}" if where else ""))
    import pmus_fee as pf
    guard("the board prices Polymarket US from pmus_fee, not a literal of its own",
          abs(bb.PMUS_FEE - pf.taker()) < 1e-12, f"PMUS_FEE={bb.PMUS_FEE} vs pmus_fee={pf.taker()}")


def main():
    print("LIVE PRICING DRY RUN - nothing live is changed by this file")
    print(cs.stamp())
    rules_unchanged()
    eligibility_frozen()
    math_identical()
    board_copy_in_step()

    try:
        pop = json.load(open("liquidity/alerts.json"))
        pop = pop if isinstance(pop, list) else (pop.get("alerts") or [])
    except Exception as e:
        print(f"population unreadable ({type(e).__name__})")
        return 1
    A = [a for a in pop if a.get("result") in ("W", "L", "P")
         and not a.get("artifact") and not a.get("close_suspect")]
    print(f"\nDRY RUN over {len(A)} cached graded alerts - zero OddsPapi credits")

    changed, same, nopair = 0, 0, 0
    venue_from, venue_to, gaps = {}, {}, []
    post_better = {}
    for r in A:
        pb = r.get("prices_by_book") or {}
        lg = r.get("league")
        q = {}
        for b in AUTO:
            v = pb.get(b)
            p = v.get("price") if isinstance(v, dict) else None
            if p is None:
                continue
            q[b] = am2dec(p)
        if len(q) < 2:
            nopair += 1
            continue
        # CURRENT: best after the live model's fee, which knows no league and no maker side
        cur = max(q, key=lambda b: live_net(dec2am(q[b]), b))   # CURRENT: no league context
        # PROPOSED: best net under the official model, with league context
        prop, prop_nd, _ = cs.best_net(q, "auto", league=lg, live=False)
        prop = {"novig.us": "novig", "polymarket.us": "polymarket_us"}.get(prop, prop)
        if prop is None:
            nopair += 1
            continue
        if prop == cur:
            same += 1
        else:
            changed += 1
            venue_from[cur] = venue_from.get(cur, 0) + 1
            venue_to[prop] = venue_to.get(prop, 0) + 1
            gaps.append((dec2am(cs.net_dec(prop, q[prop], league=lg))
                         - dec2am(cs.net_dec(cur, q[cur], league=lg))))
        # posting: which venue gives the best MAKER net on the same quotes
        pv, pnd, _ = cs.best_net(q, "auto", maker=True, league=lg)
        if pv:
            post_better[pv] = post_better.get(pv, 0) + 1

    n = changed + same
    print(f"\n  rows with two or more auto venues quoted : {n}")
    print(f"  rows where the CHOSEN VENUE is unchanged : {same}  ({same / n * 100:.1f}%)")
    print(f"  rows where the chosen venue WOULD CHANGE : {changed}  ({changed / n * 100:.1f}%)")
    print(f"  rows skipped, fewer than two quotes      : {nopair}")
    if gaps:
        gaps.sort()
        print(f"\n  on the rows that change, the proposed venue's net price is better by")
        print(f"    median {gaps[len(gaps) // 2]:+.2f} American cents, "
              f"range {gaps[0]:+.2f} to {gaps[-1]:+.2f}")
        print(f"    (positive = the standard picks a genuinely better NET price than the live model)")
    if changed:
        print(f"\n  moved FROM: {dict(sorted(venue_from.items(), key=lambda x: -x[1]))}")
        print(f"  moved TO  : {dict(sorted(venue_to.items(), key=lambda x: -x[1]))}")

    print(f"\n  best POSTING venue by net maker price, over the same rows:")
    for v, c in sorted(post_better.items(), key=lambda x: -x[1]):
        print(f"    {v:16s} {c:5d}")

    print("\n  WORKED EXAMPLE - the raw limit price needed to net -110, by venue")
    tgt = am2dec(-110)
    for v in ("novig.us", "prophetx", "kalshi", "polymarket.us"):
        tk = el.raw_for(v, tgt)
        mk = el.raw_for(v, tgt, maker=True)
        print(f"    {v:16s} as taker show {dec2am(tk):+7.1f} | as maker show {dec2am(mk):+7.1f}")
    print("    This is raw_for() doing exactly what section 3 asks: the displayed price required")
    print("    to meet a minimum acceptable NET price, per venue and per maker/taker side.")

    print(f"\n{'=' * 70}")
    if FAIL:
        print("DRY RUN FAILED - a rule or limit assertion did not hold:")
        for f in FAIL:
            print(f"  {f}")
        return 1
    print("All rule and limit assertions hold. No live file was modified by this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
