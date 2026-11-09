#!/usr/bin/env python3
"""HARD ROCK SIGHTINGS vs TWO CLOSING ANCHORS - Pinnacle and Circa (Peter, Nov 9).

READ-ONLY. One-off measurement; no rule, no file written, no bet.

WHY. The HR scanner grades a sighting as "+2% EV or better" against PINNACLE's no-vig fair at the
same line. The Nov 9 root-cause audit showed the two sharp anchors disagree by about 2.15 points,
so a 2% edge on Pinnacle can be nothing at all on Circa. Rather than estimate that shift, this
grades each sighting against BOTH closes with the entry price and fee held constant, so only the
anchor changes.

CIRCA ACCESS. hist_cache routes every book except Pinnacle and Hard Rock to the FREE OddsPapi key
(PAID_BOOKS = pinnacle, hardrockbet). Circa history therefore comes on the free key - which is how
the root-cause audit read it for 78 fixtures. The paid key's 403 "Restricted bookmaker(s)" was the
LIVE odds endpoint, a different thing. Coverage is the open question this answers.

Hard Rock carries its vig in the price and takes no commission, so there is no fee on either close
and none on the entry: the HR price is used as quoted.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
FILE = "hrscan.json"
L = []


def say(s):
    L.append(s)
    print(s)


def bet_text(s):
    """The sighting's bet in the feed's format, for tb.parse_bet via cl.close_for."""
    side, pt, mk = s.get("side"), s.get("pt"), s.get("mk")
    if mk == "totals":
        return f"{'Over' if str(side).upper().startswith('O') else 'Under'} {float(pt):g}"
    return f"{side} {float(pt):+g}"


def main():
    now = datetime.now(timezone.utc)
    try:
        d = json.load(open(FILE))
    except Exception as e:
        say(f"no {FILE}: {type(e).__name__}")
        ex.send("Bets HR vs PINNACLE and CIRCA", "\n".join(L))
        return
    S = d if isinstance(d, list) else (d.get("sightings") or d.get("rows") or [])
    say("HARD ROCK SIGHTINGS vs TWO CLOSING ANCHORS - read-only")
    say(f"sightings on file: {len(S)}")
    say("CLV = close win chance x the Hard Rock decimal - 1. No fee either side (HR takes none).")
    say("")

    # Fixtures come off disk, the way clv_rootcause reads them - refresh_fixtures bought nothing here
    # and left the run with zero fixtures, which looked like "Circa has no data" when it was plumbing.
    st = {"billable": {}, "fixtures": {}, "fx_last": {}}
    try:
        prev = tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        say(f"fixture cache: {len(st['fixtures'])} fixtures read from disk - nothing purchased")
    except Exception as e:
        say(f"fixture cache unavailable ({type(e).__name__}) - cannot verify closes, stopping")
        ex.send("Bets HR vs PINNACLE and CIRCA", "\n".join(L))
        return
    try:
        _mk = json.load(open(cl.MKFILE))
        mkmap = _mk.get("m") or {}
        say(f"market map: {len(mkmap)} entries read off disk")
    except Exception:
        mkmap = cl.load_markets(st, now)
    for lg in sorted({s.get("lg") for s in S if s.get("lg")}):
        if lg not in cl.SPORT:
            say(f"  {lg}: not a league this grader covers - its sightings are skipped")
    say("")

    hdr = f"{'league':6} {'bet':34} {'HR':>6} {'PIN CLV':>9} {'CIRCA CLV':>10} {'res':>4}"
    say(hdr)
    say("-" * len(hdr))
    got_p = got_c = 0
    sum_p = sum_c = 0.0
    miss = {}
    for s in S:
        lg = s.get("lg")
        b = {"bet": bet_text(s), "league": lg, "game": s.get("game"), "game_start": s.get("start"), "book": "hardrockbet"}
        label = f"{(s.get('game') or '')[:18]} {bet_text(s)}"[:34]
        res = ((s.get("res") or {}).get("r") or "-") if isinstance(s.get("res"), dict) else "-"
        hr = s.get("hr")
        if lg not in cl.SPORT:
            miss["league not covered"] = miss.get("league not covered", 0) + 1
            continue
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture matched"] = miss.get("no fixture matched", 0) + 1
            say(f"{lg:6} {label:34} {str(hr):>6} {'-':>9} {'-':>10} {res:>4}   (no fixture)")
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(s.get("start"))
        h = hc.get_hist(fid, ["pinnacle", "circasports"], start)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] = miss.get("history error", 0) + 1
            continue
        dec = cl.am_to_dec(hr) if hr is not None else None
        out = {}
        for bk, tag in (("pinnacle", "pin"), ("circasports", "circa")):
            mkts = cl.book_markets(h, bk)
            if not mkts:
                continue
            c, _ = cl.close_for(b, f, mkts, mkmap, start, lg)
            if c and dec:
                out[tag] = 100 * (c["p"] * dec - 1)
        if "pin" in out:
            got_p += 1
            sum_p += out["pin"]
        if "circa" in out:
            got_c += 1
            sum_c += out["circa"]
        if "pin" not in out and "circa" not in out:
            miss["no close at that line"] = miss.get("no close at that line", 0) + 1
        say(f"{lg:6} {label:34} {str(hr):>6} "
            f"{(f'{out['pin']:+.2f}%' if 'pin' in out else '-'):>9} "
            f"{(f'{out['circa']:+.2f}%' if 'circa' in out else '-'):>10} {res:>4}")

    say("")
    say(f"graded vs Pinnacle {got_p} of {len(S)}" + (f", average CLV {sum_p / got_p:+.2f}%" if got_p else ""))
    say(f"graded vs Circa    {got_c} of {len(S)}" + (f", average CLV {sum_c / got_c:+.2f}%" if got_c else ""))
    if miss:
        say("not graded: " + ", ".join(f"{k} {v}" for k, v in miss.items()))
    if got_c == 0:
        say("")
        say("CIRCA COVERAGE IS THE FINDING: no Circa close was available for any of these games.")
        say("Access is not the problem - hist_cache fetches Circa on the free key. Either Circa does not")
        say("price these leagues on this feed, or the history simply has no ticks for them.")
    say("")
    say(f"OddsPapi calls: billable {cl.STATS.get('billable', 0)}, free {cl.STATS.get('free', 0)}")
    say("Read-only. Nothing written, no rule changed.")
    ex.send("Bets HR vs PINNACLE and CIRCA", "\n".join(L))


if __name__ == "__main__":
    main()
