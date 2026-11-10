#!/usr/bin/env python3
"""STANDARDIZED CLV SCORECARD - Priority 4 (Peter, 9 Nov): every candidate on ONE documented basis.

THE BASIS, and only this one:

    standardized CLV % = (Pinnacle no-vig CLOSE probability x net entry decimal AFTER FEES - 1) x 100

per CLV_STANDARD.md, fee model clv_std.FEE_MODEL. Nothing here reads a stored CLV field, because
the stored fields are three different things under similar names:

    alerts.json "clv"               a STRING in POINTS of line movement ('+1.5 pts'), not CLV
    alerts.json "beat_close"        LINE-based
    alerts.json "close_value_pct"   PRICE-based - the real thing
    liquidity "clv_cents"           probability CENTS, not percent

The line/price split is not cosmetic: beat_close and the price-based figure DISAGREE on 253 of 595
rows (42.5%), always the same way - beat_close True while close value is negative. That is beating
the closing LINE while losing on PRICE, because the price paid was too high. Every "beat the close"
figure quoted from beat_close therefore overstates price value about four times in ten, including
figures in earlier reports. This script reports the PRICE-based rate and prints the line-based one
beside it so the gap stays visible instead of being inherited.

WHAT IT CANNOT DO, stated rather than fudged:
  * P-LIMIT LOW cannot be recalculated here - the liquidity population carries no Pinnacle-limit
    field (checked: 0 of 2,245 rows). It needs Item 56's own data, so it is listed as a gap.
  * Rows without a close probability, a price or a known venue are EXCLUDED and counted, never
    substituted. Coverage is printed per candidate (Guard 2).
  * SLOW-HR and Executed CLV live in other populations and are quoted by reference with their run
    id, not recomputed here, so nothing is silently re-derived.

Read-only: no bet, no rule, no threshold, no file written. Flat 1u throughout, so there are no
dollar figures to leak; the log carries units and percentages only.
"""
import json
import os
import re
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timezone

import clv_ledger as cl
import clv_std as cs
import price_basis as pb

SHARP = os.environ.get("SC_SHARP", "") or "alerts.json"
LIQ = os.environ.get("SC_LIQ", "") or "liquidity/alerts.json"
L = []


def say(t=""):
    L.append(t)
    print(t)


def load(p):
    try:
        d = json.load(open(p))
    except Exception as e:
        say(f"  {p} unreadable ({type(e).__name__})")
        return []
    return d if isinstance(d, list) else (d.get("alerts") or d.get("bets") or [])


def tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def toks(s):
    return set(re.findall(r"[a-z]{3,}", str(s or "").lower()))


def std_clv(close_prob, price):
    """The one basis, over a price_basis.Price (explicitly RAW or NET). None when it cannot be computed.

    Nov 10 audit fix. This used to take a bare American number and ALWAYS apply the venue fee, so a stored
    price_after_fee (already net) was charged twice: Kalshi -2.98 pt, ProphetX -0.91 pt. The caller now
    states which kind of price it holds, and price_basis takes the fee off at most once."""
    if close_prob is None or price is None:
        return None
    try:
        return pb.pin_clv(close_prob, price)
    except Exception:
        return None


def units(rows):
    t = 0.0
    for r in rows:
        am, res = r["am"], r["res"]
        if am is None or res == "P":
            continue
        t += (am / 100 if am > 0 else 100 / abs(am)) if res == "W" else -1.0
    return t


def games(rows):
    """Distinct games, so a candidate cannot inflate its own sample with two bets on one game."""
    return len({(r["day"], frozenset(toks(r["game"]))) for r in rows})


def table(name, rows, excluded, note=""):
    """One scorecard line per candidate, with its halves."""
    say("")
    say(f"  {name}")
    if note:
        say(f"    {note}")
    use = [r for r in rows if r["clv"] is not None]
    if not use:
        say(f"    n 0 usable ({len(rows)} rows, {sum(excluded.values())} excluded) - nothing to report")
        for k, v in excluded.most_common():
            say(f"      excluded, {k}: {v}")
        return
    use.sort(key=lambda r: r["day"])
    half = len(use) // 2
    for lbl, xs in (("pooled", use), ("H1 (first half by date)", use[:half]), ("H2 (second half)", use[half:])):
        if not xs:
            continue
        w = sum(1 for r in xs if r["res"] == "W")
        l_ = sum(1 for r in xs if r["res"] == "L")
        p_ = sum(1 for r in xs if r["res"] == "P")
        u = units(xs)
        risk = sum(1.0 for r in xs if r["res"] in ("W", "L"))
        beat = sum(1 for r in xs if r["clv"] > 0)
        line_beat = [r for r in xs if r.get("line_beat") is not None]
        lb = sum(1 for r in line_beat if r["line_beat"])
        extra = (f" | LINE-based beat {lb}/{len(line_beat)} = {100 * lb / len(line_beat):.0f}%"
                 if line_beat else "")
        say(f"    {lbl:24s} n {len(xs):4d} | games {games(xs):4d} | {w}-{l_}" + (f"-{p_}" if p_ else "")
            + f" | {u:+7.2f}u | ROI {(100 * u / risk if risk else 0):+6.1f}%"
            + f" | CLV {st.mean(r['clv'] for r in xs):+6.2f}%"
            + f" | beat {beat}/{len(xs)} = {100 * beat / len(xs):4.1f}%" + extra)
    say(f"    coverage {len(use)}/{len(rows)} rows usable"
        + (f"; excluded: {dict(excluded.most_common())}" if excluded else ""))


def table_self(name, rows, note=""):
    """Liquidity candidates: record, units and EXCHANGE SELF-CLOSE MOVEMENT. Deliberately no CLV column:
    this file holds no Pinnacle close, and an exchange's own close is never labelled Pinnacle CLV."""
    say("")
    say(f"  {name}")
    if note:
        say(f"    {note}")
    use = sorted(rows, key=lambda r: r["day"])
    if not use:
        say("    n 0")
        return
    mv = [r["self_move_c"] for r in use if r.get("self_move_c") is not None]
    w = sum(1 for r in use if r["res"] == "W")
    l_ = sum(1 for r in use if r["res"] == "L")
    u = units(use)
    risk = sum(1.0 for r in use if r["res"] in ("W", "L"))
    say(f"    n {len(use):4d} | games {games(use):4d} | {w}-{l_} | {u:+7.2f}u | ROI {(100 * u / risk if risk else 0):+6.1f}%"
        + (f" | Exchange Self-Close Movement {st.mean(mv):+.2f}c over {len(mv)} rows (NOT CLV)" if mv else "")
        + " | Pinnacle CLV: not computed here (clv_report.py)")


def main():
    say("STANDARDIZED CLV SCORECARD - one basis for every candidate (Priority 4)")
    say(cs.stamp())
    say("")
    say("BASIS: (Pinnacle no-vig close prob x net entry decimal AFTER FEES - 1) x 100.")
    say("No stored CLV field is used. 'beat' below is PRICE-based; the LINE-based rate the system")
    say("stores is printed beside it where available, because the two disagree on 42.5% of rows.")

    # ---------------------------------------------------------------- sharp alert population
    S = load(SHARP)
    srows, sexc = [], Counter()
    for x in S:
        if x.get("result") not in ("W", "L", "P"):
            continue
        try:
            pr = pb.best_price(x, x.get("book_key"), "price_after_fee", "price") if x.get("book_key") else None
        except cs.UnknownVenue:
            pr = None                       # unregistered retail venue: excluded and counted, never priced as free
        am = pr.american if pr else None
        c = std_clv(x.get("close_fair_prob"), pr)
        if c is None:
            sexc["no close prob / price / known venue"] += 1
        srows.append({"day": str(x.get("alert_utc") or "")[:10], "game": x.get("game"),
                      "am": am, "res": x.get("result"), "clv": c,
                      "line_beat": x.get("beat_close"), "sent": bool(x.get("sent_to_phone")),
                      "lg": x.get("league") or x.get("sport"), "bet": str(x.get("bet") or "")})

    say("")
    say("=" * 108)
    say("SHARP ALERT POPULATION  (the feed Lane 1 and PETER FEED PLAYS draw on)")
    say("=" * 108)
    table("ALL graded sharp alerts", srows, sexc)
    table("SENT to phone only", [r for r in srows if r["sent"]], Counter())
    und = [r for r in srows if "under" in r["bet"].lower()]
    table("NBA unders (Lane 1's own market)",
          [r for r in und if r["lg"] == "NBA"], Counter(),
          "Lane 1 is ProphetX-priced NBA/NFL unders + NCAAF unders and Top-25 overs")

    # ---------------------------------------------------------------- liquidity population
    Q = load(LIQ)
    qrows, qexc = [], Counter()
    for x in Q:
        if x.get("result") not in ("W", "L", "P") or x.get("artifact") or x.get("close_suspect"):
            continue
        am = x.get("price_american")
        # Nov 10 audit fix (defect A). close_price is the TRIGGER EXCHANGE'S OWN last pregame price
        # (liquidity_monitor.py:2013), never Pinnacle's close, so it can not produce Pinnacle CLV and the
        # old close_price x net_dec figure was mostly fee drag. This file carries no Pinnacle close, so
        # CLV is None here and the exchange's own movement is reported, in cents, under its own name.
        # Pinnacle CLV for this population is clv_report.py's, on its own verified-close sample.
        mv = (None if x.get("close_price") is None or x.get("price") is None
              else 100.0 * (x["close_price"] - x["price"]))
        c = None
        qexc["no Pinnacle close in this file (see clv_report.py)"] += 1
        qrows.append({"day": str(x.get("alerted_utc") or "")[:10], "game": x.get("game"),
                      "am": am, "res": x.get("result"), "clv": c, "self_move_c": mv, "line_beat": None,
                      "lg": x.get("league") or x.get("sport"), "mk": x.get("market"),
                      "side": x.get("side"), "book": x.get("book"),
                      "lead": x.get("lead_min"), "new_money": x.get("new_money")})

    say("")
    say("=" * 108)
    say("LIQUIDITY-BOARD CANDIDATES  (registered slices, each on the same basis)")
    say("=" * 108)
    nbau = [r for r in qrows if r["lg"] == "NBA" and r["mk"] == "total" and r["side"] == "UNDER"]
    # The liquidity monitor's "polymarket" is Polymarket GLOBAL - it reads gamma-api.polymarket.com
    # and clob.polymarket.com, the international endpoints, not the US gateway the executor uses.
    # clv_std.canon agrees ('polymarket' -> polymarket.global) and global is NOT auto-eligible, so
    # net_dec refuses it and every one of those rows has no net price. That exclusion is CORRECT -
    # we cannot bet that venue - but it has to be VISIBLE, because a pooled "all triggers" line
    # that silently drops 38 of 123 rows is really a Kalshi-only line wearing a wider label.
    pm = [r for r in nbau if str(r["book"] or "").startswith("polymarket")]
    ks = [r for r in nbau if r["book"] == "kalshi"]
    table_self("NBA UNDER signal - BETTABLE venues only", ks,
          f"Kalshi-triggered. The {len(pm)} Polymarket-triggered rows are Polymarket GLOBAL, "
          f"which we cannot bet, so they carry no net price and are excluded by venue, not dropped.")
    table_self("  - Polymarket GLOBAL triggers (NOT BETTABLE, shown for completeness)", pm,
               "Units and record are real; never pool these with the bettable line above.")
    t4 = [r for r in qrows if r["lg"] == "NBA" and r["mk"] == "total"
          and r["lead"] is not None and r["lead"] >= 240]
    table_self("NBA totals, 4h+ lead", t4, "LIQ-BOT's population (registry 9)")
    pr = [r for r in qrows if r["lg"] == "NBA" and r["mk"] == "total"
          and r["new_money"] is not None and 25000 <= r["new_money"] <= 50000]
    table_self("NBA totals, $25-50k prints", pr, "LIQ-SMALL (registry 13)")

    # ---------------------------------------------------------------- quoted by reference
    say("")
    say("=" * 108)
    say("QUOTED BY REFERENCE - other populations, not recomputed here")
    say("=" * 108)
    say("  LANE 1 EXECUTED CLV      n 33 verified of 41 graded bot fills | +0.37% | beat 24/33 = 72.7%")
    say("                           CI [55.8, 84.9] excludes a coin flip | run 42612929620")
    say("                           Basis: actual FILLED price from the venues' own records, taker side.")
    say("  SLOW-HR decisive cell    n 63 plays / 63 games | 21-42 | +23.05u | CLV +6.76% | beat 49/63")
    say("                           screened of EV > +15%: 56 | 20-36 | +17.05u | +5.14% | run 42617747894")
    say("                           DIAGNOSTIC ONLY - 63 < 100 distinct games.")
    say("    NOTE on SLOW-HR CLV: it is a % at a moneyline price, so it is NOT comparable across")
    say("    price bands - the same % on a +1000 dog is a far smaller probability edge than at +150.")
    say("    Ranking candidates by % CLV puts the weakest band first. Rank on units and games.")

    say("")
    say("=" * 108)
    say("GAPS - what this scorecard cannot answer")
    say("=" * 108)
    say("  P-LIMIT LOW              NOT recalculable here: the liquidity population carries no")
    say("                           Pinnacle-limit field (0 of 2,245 rows). Needs Item 56's data.")
    say("  MODEL LAB                its own population and basis; not in these two files.")
    say("  LINE vs PRICE            where a LINE-based rate is printed above and differs from the")
    say("                           price-based one, the price-based one is the standard's.")

    say("")
    say("GUARD 1 - scope: each line above names its own population. None of these is 'the system'.")
    say("GUARD 2 - exclusions and coverage are printed per candidate. Nothing is substituted.")
    say("Flat 1u throughout. Positive CLV is evidence of pricing value, not realised profit.")

    try:
        import executor as ex
        ex.send("Bets STANDARDIZED CLV SCORECARD (Priority 4)", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
