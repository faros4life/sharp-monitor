#!/usr/bin/env python3
"""ONE TARGETED CHECK on the exact graded BETS BOARD PLAYS calls (Peter, 2026-11-09).

Three questions, nothing else:
  1. What is the verified standardized Pinnacle CLV of the exact BETS BOARD PLAYS sample?
  2. How many calls have evidence of an OBTAINABLE RESTING price at the decision time?
  3. Does the evidence support a $200-to-win live pilot, or is it still inconclusive?

Deliberately NOT a research project: no threshold is searched, no rule is tuned, no new population
is built, nothing is registered. The capped historical sample is reported on its own, as instructed.

SPENDS NO ODDSPAPI CREDITS. Pinnacle closes come from the history cache that is already bought;
/historical-odds is free and bypasses the credit gate, and a fixture or market lookup that the gate
refuses degrades to "no verified close" rather than buying anything. Read-only: no bet, no order, no
switch, no state file written.

SIDE TRANSLATION, the one place this could go confidently wrong. The board stores four forms:
    "NOT Over 237.5 points"  Kalshi NO on the Over  -> Under 237.5
    "Over 238.5 points"                             -> Over 238.5
    "Over (228.5)"                                  -> Over 228.5
    "Under (231.5)"                                 -> Under 231.5
Every line in the sample is a half-point, so there is no push and NO(Over) is exactly Under; this is
asserted below rather than assumed. Getting this wrong is the same class of error as reading an
unsigned spread as a moneyline, which produced a confidently wrong -16.60% earlier this month.
"""
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import clv_std as cs
import hist_cache as hc
import nba_names as nn
import tracker_build as tb

CALLS = "board/calls.json"
QUOTES = {}
OU = re.compile(r"^(NOT\s+Over|Over|Under)\s*\(?\s*([0-9]+(?:\.[0-9]+)?)\s*\)?\s*(?:points)?$", re.I)


def bet_of(side):
    """('Over'|'Under', line) for a board side string, or None when it is not a form we know."""
    m = OU.match(str(side or "").strip())
    if not m:
        return None
    head, ln = m.group(1).lower(), float(m.group(2))
    return ("Under" if head.startswith("not") else head.title()), ln


# ---------------------------------------------------------------- O6 (Peter, 11 Nov): BEST BETTABLE VENUE
# The call's recorded price is the TRIGGER venue's. That is not the execution basis: with resting
# bids we get the alert price or nothing, at whichever venue we can actually bet. Pricing at the
# trigger venue understated the entry on 43 of 53 gettable calls by a mean 1.47 probability cents,
# and dropped every globally-triggered call as NotTradeable even where the same line was available
# on Novig at the alert price or better.
#
# DECISION-TIME ONLY. The quotes come from the liquidity row whose key AND alerted_utc are the
# board call's own, i.e. the snapshot taken when the call was made. No later read, no close, no
# result is consulted when choosing the venue - asserted in tests/test_board_clv_venue.py.
#
# FEES VIA clv_std ONLY. net_dec is the single fee model (cs.FEE_MODEL); this file adds no fee
# arithmetic of its own, and a venue clv_std refuses to price (Polymarket Global: NotTradeable)
# can never be selected.
LIQ = os.environ.get("LIQ_ALERTS", "") or "liquidity/alerts.json"
BETTABLE = ("novig.us", "kalshi", "prophetx")   # venues Peter can bet; canonical clv_std names
SRC_NAME = {"novig": "novig.us", "kalshi": "kalshi", "prophetx": "prophetx"}


def liq_quotes(path=None):
    """{(key, alerted_utc): prices_by_book} - the decision-time cross-book snapshot per alert."""
    try:
        rows = json.load(open(path or LIQ)).get("alerts") or []
    except Exception:
        return {}
    return {(r.get("key"), r.get("alerted_utc")): (r.get("prices_by_book") or {})
            for r in rows if r.get("key")}


def _net(book, american, maker, league="NBA"):
    """After-fee decimal for an american price at a venue, via clv_std's one fee model."""
    if american is None:
        return None
    d = 1 + (american / 100.0 if american > 0 else 100.0 / -american)
    try:
        return cs.net_dec(book, d, maker=maker, league=league)
    except Exception:
        return None          # NotTradeable / UnknownVenue: never selectable


def best_bettable(pbb, line, target_net, maker, league="NBA"):
    """(canonical venue, american, net decimal) for the best BETTABLE quote on the SAME line whose
    after-fee price is at least as good as target_net. None when no such quote exists.

    pbb is a decision-time snapshot only. Nothing here reads a close, a result or a later price."""
    best = None
    for src, q in (pbb or {}).items():
        v = SRC_NAME.get(str(src).lower())
        if v not in BETTABLE or not isinstance(q, dict):
            continue
        pt, am = q.get("point"), q.get("price")
        if pt is None or am is None or abs(float(pt) - float(line)) > 1e-9:
            continue                      # same line only - never a different number
        nd = _net(v, am, maker, league)
        if nd is None:
            continue
        if best is None or nd > best[2]:
            best = (v, am, nd)
    if best is None or target_net is None or best[2] < target_net - 1e-12:
        return None
    return best


def graded():
    """PLAY calls, each carrying its own registry key under _k so the decision-time liquidity
    snapshot can be joined. The stored call is never mutated: _k is added to a shallow copy."""
    d = json.load(open(CALLS))
    rows = [dict(r, _k=k) for k, r in (d.get("calls") or {}).items()
            if r.get("call") == "PLAY" and r.get("result") in ("W", "L", "P")]
    rows.sort(key=lambda r: str(r.get("at") or ""))
    return rows


def main():
    now = datetime.now(timezone.utc)
    rows = graded()
    print(f"BETS BOARD PLAYS - targeted CLV and obtainability check | {now:%Y-%m-%d %H:%M} UTC")
    print(f"fee model {cs.FEE_MODEL} | basis: Pinnacle no-vig, VERIFIED same-line close, "
          f"net of fees, at the registered entry decision time")
    print(f"sample: {len(rows)} graded PLAY calls (the CAPPED historical population, kept separate "
          f"from any uncapped configuration)")
    print("=" * 112)

    # push safety, asserted not assumed
    ints = [r for r in rows if float(r["line"]) == int(float(r["line"]))]
    assert not ints, f"{len(ints)} integer lines: NOT Over is not Under where a push is possible"

    global QUOTES
    QUOTES = liq_quotes()
    print(f"decision-time cross-book snapshots loaded: {len(QUOTES)}")
    st_ = tb.dec(json.load(open(cl.STATE)))
    mkmap = cl.load_markets(st_, now)      # gate-refusal safe: falls back to the cached list

    out, exc = [], collections.Counter()
    for r in rows:
        b_ = bet_of(r.get("side"))
        gm = str(r.get("game") or "").split(":")[0]
        parts = re.split(r"\s+vs\.?\s+", gm)
        rec = {"at": r.get("at"), "game": gm, "book": r.get("book"), "am": r.get("price"),
               "res": r.get("result"), "units": r.get("units"), "line": r.get("line"),
               "bet": None, "pin": None, "canon": None, "auto": None, "rest": None}
        if not b_ or len(parts) != 2:
            exc["unparseable side or game"] += 1
            out.append(rec)
            continue
        ou, ln = b_
        rec["bet"] = f"{ou} {ln:g}"
        b = {"bet": rec["bet"], "league": "NBA", "game": gm,
             "teams": nn.teams_of({"league": "NBA", "teams": parts}),
             # the decision time is the alert; the fixture's own start is used once matched
             "game_start": r.get("at"), "book": r.get("book")}
        fid = cl.find_fixture(st_, b)
        if not fid:
            exc["no fixture matched"] += 1
            out.append(rec)
            continue
        f = st_["fixtures"][fid]
        start = cl.tp(f.get("start"))
        if not start or now - start < hc.FINAL_AFTER:
            exc["game not final"] += 1
            out.append(rec)
            continue
        if not os.path.exists(hc._path(fid, "pinnacle")):
            exc["Pinnacle close not in cache (not bought)"] += 1
            out.append(rec)
            continue
        h = hc.get_hist(fid, ["pinnacle"], start)
        if isinstance(h, dict) and h.get("_error"):
            exc["history error"] += 1
            out.append(rec)
            continue
        c, why = cl.close_for(b, f, cl.book_markets(h, "pinnacle"), mkmap, start, "NBA")
        # close_for returns (close, ERROR REASON). On SUCCESS the error is None and the "how" lives
        # INSIDE the close dict. This passed `why` to close_verified, so every successful lookup was
        # tested as close_verified(None) - which is False by design, asserted in clv_std's own test.
        # The result: 100% of good closes rejected, 50 of 54 calls landing in one bucket with
        # identical text, and the board reporting 0 of 54 verified closes since it was written.
        # Every other caller in the repo (clv_report, lane2_search x3) already used c.get("how").
        # I previously blamed the empty history cache for this 0/54 and told Peter so; the cache was
        # a real second problem, but THIS is why the number was zero.
        #
        # The counter is split too, because merging `not c` with `not verified` is what made the bug
        # invisible: one bucket cannot distinguish "no close found" from "close found but not
        # same-line", and those have opposite remedies.
        if not c:
            exc["no Pinnacle close found" + (f" ({why})" if why else "")] += 1
            out.append(rec)
            continue
        if not cs.close_verified(c.get("how")):
            exc[f"close found but not same-line ({c.get('how')})"] += 1
            out.append(rec)
            continue
        if rec["am"] is None:
            exc["no recorded entry price"] += 1
            out.append(rec)
            continue
        dec = 1 + (rec["am"] / 100.0 if rec["am"] > 0 else 100.0 / -rec["am"])
        try:
            trig = cs.canon(rec["book"])
        except Exception:
            trig = rec["book"]
        rec["trigger_venue"] = trig
        # O6: price at the best BETTABLE venue offering the SAME line at the alert price or better,
        # after fees, from the decision-time snapshot. Maker and taker are resolved separately
        # because the target to beat differs by basis.
        kk = str(r.get("_k") or "").rsplit("|", 1)
        pbb = QUOTES.get((kk[0], kk[1])) if len(kk) == 2 else None
        rec["snapshot"] = pbb is not None
        for basis, mk_ in (("maker", True), ("taker", False)):
            tgt = _net(trig, rec["am"], mk_)
            pick = best_bettable(pbb, rec["line"], tgt, mk_) if (pbb and tgt) else None
            rec[f"{basis}_venue"] = pick[0] if pick else None
            rec[f"{basis}_am"] = pick[1] if pick else None
            rec[f"{basis}_net"] = pick[2] if pick else None
            rec[f"{basis}_trigger_net"] = tgt
        rec["gettable"] = rec["maker_venue"] is not None or rec["taker_venue"] is not None
        if not rec["gettable"]:
            exc["not gettable: no bettable venue at the alert price on that line"] += 1
            out.append(rec)
            continue
        v = rec["taker_venue"] or rec["maker_venue"]
        rec["canon"] = v
        rec["auto"] = v in cs.AUTO
        # RESTING, not taking: the maker leg. A venue that cannot rest an order cannot produce this
        # price at all, whatever its screen showed.
        rec["rest"] = v in tuple(x.strip() for x in
                                 (os.environ.get("EXEC_REST_BOOKS") or "novig,kalshi").split(","))
        # net_clv wants the close PROBABILITY, not the close dict. close_for returns
        # {"p": <prob>, "how": ..., "age_min": ...}; every other caller passes a float. This
        # passed `c` and crashed with "float() argument must be ... not 'dict'" the first time it
        # ever ran - which was today, because the close_verified bug above rejected 100% of closes
        # and this line was unreachable. Two bugs stacked, the second hidden by the first: fixing
        # one exposed the other immediately, and nothing downstream of here has ever executed.
        # NotTradeable is a RULE, not a failure. net_dec raises it for venues whose quotes are
        # visible but that have no fee model - Polymarket Global - and clv_std is explicit that
        # such a venue must not enter AUTO or MANUAL opportunity. The board has calls on one, so
        # they are EXCLUDED with their own reason rather than crashing the report or, worse, being
        # silently priced with some other venue's fee model. Third issue in this chain, and the
        # only one that is not a bug: it was simply never reached before today.
        # SECOND BENCHMARK: CIRCA (Peter, Nov 10: "We using circa and pinical clv always taking
        # into account fees" / "From now on future").
        #
        # Circa closes are captured by circa_close.py into the SAME hist_cache as Pinnacle, as
        # hc._path(fid, "circasports"), so grading against them reuses this exact machinery - the
        # same close_for, the same close_verified same-line rule, the same net_clv with the same
        # fee model on OUR entry price. Nothing about the fee treatment changes: the fee has
        # always applied to the entry, not to the benchmark close, which is why the figures split
        # into maker and taker.
        #
        # FORWARD-ONLY FALLS OUT FOR FREE. Capture began Nov 9, so no cache file exists for any
        # earlier game and the exists() check below simply reports "pre-capture". No date logic,
        # and no risk of back-filling a benchmark that was never recorded.
        #
        # Circa is a BENCHMARK, not an entry venue - which is why cs.canon("circa") correctly
        # raises UnknownVenue and is not being "fixed". It needs a no-vig close, not a fee model.
        #
        # A missing Circa close NEVER drops the row: the Pinnacle leg stands on its own and the
        # Circa leg is reported as coverage. Making Circa mandatory today would zero the report,
        # because at 25 games/night the history is about a day and a half deep.
        rec["circa"] = rec["circa_taker"] = None
        rec["circa_why"] = "pre-capture (Circa capture began Nov 9)"
        if os.path.exists(hc._path(fid, "circasports")):
            try:
                hcc = hc.get_hist(fid, ["circasports"], start)
                if isinstance(hcc, dict) and hcc.get("_error"):
                    rec["circa_why"] = "history error"
                else:
                    cc, cwhy = cl.close_for(b, f, cl.book_markets(hcc, "circasports"), mkmap, start, "NBA")
                    if not cc:
                        rec["circa_why"] = f"no Circa close found ({cwhy})" if cwhy else "no Circa close found"
                    elif not cs.close_verified(cc.get("how")):
                        rec["circa_why"] = f"Circa close not same-line ({cc.get('how')})"
                    else:
                        rec["circa_p"] = round(cc["p"], 5)
                        rec["circa_why"] = None
            except Exception as ex2:
                rec["circa_why"] = f"{type(ex2).__name__}"
        try:
            # The entry decimal is the SELECTED venue's after-fee price, not the trigger's.
            # net_clv applies the fee itself, so it is handed the venue's RAW american converted
            # to decimal; _net is used only to compare candidates.
            def _raw(am):
                return 1 + (am / 100.0 if am > 0 else 100.0 / -am)
            rec["pin"] = (cs.net_clv(c["p"], _raw(rec["maker_am"]), rec["maker_venue"],
                                     maker=True, league="NBA")
                          if rec["maker_venue"] else None)
            rec["pin_taker"] = (cs.net_clv(c["p"], _raw(rec["taker_am"]), rec["taker_venue"],
                                           maker=False, league="NBA")
                                if rec["taker_venue"] else None)
            if rec.get("circa_p") is not None:
                rec["circa"] = cs.net_clv(rec["circa_p"], dec, v, maker=True, league="NBA")
                rec["circa_taker"] = cs.net_clv(rec["circa_p"], dec, v, maker=False, league="NBA")
        except cs.NotTradeable as ex:
            exc[f"book not tradeable ({v}): no fee model"] += 1
            rec["not_tradeable"] = str(ex)[:80]
            out.append(rec)
            continue
        out.append(rec)

    ver = [r for r in out if r["pin"] is not None]
    # CIRCA COVERAGE, reported separately and never mixed into the Pinnacle figure. At 25
    # games/night the history is about a day and a half deep, so this will read mostly
    # "pre-capture" for a while - which is the honest state, not a failure.
    cver = [r for r in ver if r.get("circa") is not None]
    print(f"\nCIRCA (second benchmark, forward-only from Nov 9): {len(cver)} of {len(ver)} verified "
        f"rows also have a verified same-line CIRCA close")
    if cver:
        cm = [r["circa"] for r in cver]
        ct = [r["circa_taker"] for r in cver]
        pm = [r["pin"] for r in cver]
        cb = sum(1 for x in cm if x > 0)
        print(f"  on those {len(cver)} rows: Circa CLV maker {sum(cm)/len(cm):+.2f}%  taker "
            f"{sum(ct)/len(ct):+.2f}%  beat Circa close {cb}/{len(cver)}")
        print(f"  same rows vs Pinnacle:      maker {sum(pm)/len(pm):+.2f}%   (the two benchmarks "
            f"are reported side by side, never averaged together)")
    else:
        from collections import Counter as _C
        wc = _C(r.get("circa_why") or "?" for r in ver)
        for k, n in wc.most_common(4):
            print(f"      {n:3}  {k}")
        print("  No Circa-graded row yet, so no candidate can be judged on the Circa leg today.")
    # O6 reconciliation: every call accounted for, gettable or not, before any CLV is shown.
    got = [r for r in out if r.get("gettable")]
    nog = [r for r in out if r.get("snapshot") and not r.get("gettable")]
    nosnap = [r for r in out if not r.get("snapshot")]
    print("\n" + "=" * 112)
    print("0. EXECUTABILITY RECONCILIATION (decision-time quotes, same line, alert price or better)")
    print("=" * 112)
    print(f"  graded PLAY calls                                  {len(rows)}")
    print(f"  with a decision-time cross-book snapshot           {len(rows) - len(nosnap)}")
    print(f"  GETTABLE at a bettable venue                       {len(got)}")
    print(f"  NOT gettable                                       {len(nog)}")
    print(f"  no snapshot joined (cannot be judged)              {len(nosnap)}")
    mig = collections.Counter((r.get("trigger_venue"), r.get("taker_venue") or r.get("maker_venue"))
                              for r in got)
    print("  trigger venue -> venue actually priced:")
    for (a, b), n in mig.most_common():
        print(f"      {n:3}  {a or '?':<20} -> {b or '?'}")
    print(f"\nCLOSE COVERAGE: {len(ver)} of {len(rows)} calls have a VERIFIED same-line Pinnacle "
          f"close ({100.0 * len(ver) / max(len(rows), 1):.1f}%)")
    print(f"  {len(rows) - len(ver)} do NOT. Why:")
    for k, n in exc.most_common():
        print(f"      {n:3}  {k}")

    def agg(rs, label):
        if not rs:
            print(f"  {label:<46} n=0")
            return None
        mks = [r["pin"] for r in rs if r["pin"] is not None]
        tks = [r["pin_taker"] for r in rs if r["pin_taker"] is not None]
        mk = (sum(mks) / len(mks)) if mks else float("nan")
        tk = (sum(tks) / len(tks)) if tks else float("nan")
        u = sum(r["units"] or 0 for r in rs)
        beat = sum(1 for r in rs if (r["pin"] or 0) > 0)
        print(f"  {label:<46} n={len(rs):3}  CLV maker {mk:+6.2f}%  taker {tk:+6.2f}%  "
              f"beat close {beat}/{len(rs)} ({100.0 * beat / len(rs):4.1f}%)  units {u:+6.2f}")
        return mk

    print("\n" + "=" * 112)
    print("1. VERIFIED CLV OF THE EXACT SAMPLE")
    print("=" * 112)
    all_mk = agg(ver, "all verified BETS BOARD PLAYS calls")
    print()
    bettable = [r for r in ver if r["auto"] and r["rest"]]
    agg([r for r in ver if r["canon"] == "kalshi"], "  kalshi (auto-eligible, can rest)")
    agg([r for r in ver if r["canon"] == "polymarket.global"],
        "  polymarket.global (NOT auto-eligible)")
    print()
    agg(bettable, "BETTABLE ONLY (auto-eligible AND can rest)")

    # halves, on the bettable set, to see whether one stretch carries it
    if len(bettable) >= 8:
        h = sorted(bettable, key=lambda r: str(r["at"]))
        mid = len(h) // 2
        print()
        agg(h[:mid], "  bettable, first half")
        agg(h[mid:], "  bettable, second half")

    print("\n" + "=" * 112)
    print("2. OBTAINABLE RESTING PRICE AT THE DECISION TIME")
    print("=" * 112)
    byv = collections.Counter(r["canon"] or "?" for r in out)
    print("  venue of the recorded alert price, all 54 graded calls:")
    for v, n in byv.most_common():
        ok_auto = v in cs.AUTO
        ok_rest = v in ("novig.us", "kalshi")
        print(f"      {n:3}  {v:<20} auto-eligible {'yes' if ok_auto else 'NO '}   "
              f"can rest {'yes' if ok_rest else 'NO '}")
    print()
    print(f"  calls the bot could have placed a RESTING bid on at all: "
          f"{sum(1 for r in out if r['rest'] and r['auto'])} of {len(rows)}")
    print("\n  EVIDENCE OF A FILL, which is the actual question:")
    print("     The board records a DISPLAYED quote at the decision time. It does not record")
    print("     resting-order depth, queue position, or whether the market later traded through")
    print("     that price. A resting bid fills only if someone crosses to it, and none of those")
    print("     three facts is in board/calls.json or in any state file this check can read.")
    print("     So for 0 of 54 calls is there timestamped evidence that a resting bid WOULD have")
    print("     filled. The displayed price is necessary but not sufficient, and Peter's own")
    print("     instruction is not to assume a fill from a displayed quote.")
    print("     The recorded units therefore describe TAKER fills at the alert price - which is")
    print("     not the execution method this spec authorizes.")
    return out, ver, bettable


if __name__ == "__main__":
    main()
