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
OU = re.compile(r"^(NOT\s+Over|Over|Under)\s*\(?\s*([0-9]+(?:\.[0-9]+)?)\s*\)?\s*(?:points)?$", re.I)


def bet_of(side):
    """('Over'|'Under', line) for a board side string, or None when it is not a form we know."""
    m = OU.match(str(side or "").strip())
    if not m:
        return None
    head, ln = m.group(1).lower(), float(m.group(2))
    return ("Under" if head.startswith("not") else head.title()), ln


def graded():
    d = json.load(open(CALLS))
    rows = [r for r in (d.get("calls") or {}).values()
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
            v = cs.canon(rec["book"])
        except Exception:
            v = rec["book"]
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
        rec["pin"] = cs.net_clv(c["p"], dec, v, maker=True, league="NBA")
        rec["pin_taker"] = cs.net_clv(c["p"], dec, v, maker=False, league="NBA")
        out.append(rec)

    ver = [r for r in out if r["pin"] is not None]
    print(f"\nCLOSE COVERAGE: {len(ver)} of {len(rows)} calls have a VERIFIED same-line Pinnacle "
          f"close ({100.0 * len(ver) / max(len(rows), 1):.1f}%)")
    print(f"  {len(rows) - len(ver)} do NOT. Why:")
    for k, n in exc.most_common():
        print(f"      {n:3}  {k}")

    def agg(rs, label):
        if not rs:
            print(f"  {label:<46} n=0")
            return None
        mk = sum(r["pin"] for r in rs) / len(rs)
        tk = sum(r["pin_taker"] for r in rs) / len(rs)
        u = sum(r["units"] or 0 for r in rs)
        beat = sum(1 for r in rs if r["pin"] > 0)
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
