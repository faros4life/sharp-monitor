#!/usr/bin/env python3
"""CIRCA + PS3838 CLOSE CAPTURE - a second sharp close, on the free key (Peter, Nov 9:
"Do we have circa to compare clv now" / "Do what you think is best").

THE ANSWER TO THAT QUESTION WAS NO, AND THIS IS WHY IT HAD TO START TONIGHT. Circa is reachable
(run 42566... probe: circasports 5 fixtures on the free key) but NOTHING stored it, so there was no
Circa data to compare any CLV against. Closing lines are perishable: every night without a capture
is a night gone for good. So this starts accumulating now, at zero paid cost, rather than waiting
on the budget figure.

WHAT IT IS FOR. Every CLV number in this system rests on Pinnacle's close, with nothing checking
it. circasports and ps3838 are independent sharp closes - ps3838 is Pinnacle's Asia-facing book, so
it is a near-sibling rather than a true independent, and Circa is a genuinely separate shop. Once
there is history, clv_report / executed_clv can grade the same bet against a second close and the
disagreement is measurable instead of assumed.

WHY THIS IS NOT BOLTED ONTO hcache_fill. That job walks up to 700 games; two more books would be up
to ~1,400 extra free-key calls per run. The free budget is UNKNOWN - the probe found NO rate-limit
header, and the "250/month" in freekey_books.py is a figure I wrote and never verified - so a
careless addition could exhaust the free key and take the EXCHANGE history down with it, which is
what Executed CLV already depends on. This is capped, counted, and separate for exactly that
reason.

COST. Zero paid credits: history is free on both keys, and the books here are never in PAID_BOOKS
so hist_cache routes them to the free key by itself. The paid key is not even in the workflow env.
The call count is hard-capped by CC_MAX games and reported, so the free budget is learned by
measurement instead of assumed.

Read-only as to betting: places nothing, changes no rule, no threshold, no venue permission. It
writes only the shared history cache. The log prints counts and book names only.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
BOOKS = ["circasports", "ps3838"]
LEAGUES = tuple((os.environ.get("CC_LEAGUES") or "NBA,NFL,NCAAF,NHL").split(","))
MAX_GAMES = int(os.environ.get("CC_MAX", "") or "25")
BACK_HOURS = int(os.environ.get("CC_BACK_HOURS", "") or "36")
L = []


def say(t=""):
    L.append(t)
    print(t)


def compare(st):
    say()
    say("=" * 70)
    say("IS CIRCA A HARDER CLOSE THAN PINNACLE?  (Peter, Nov 10)")
    say("=" * 70)
    say("  Same fixture, same market, same side: Circa's no-vig close win probability minus")
    say("  Pinnacle's. POSITIVE means Circa's number is HIGHER, i.e. Circa makes the side look")
    say("  more likely - so betting that side has to clear a HARDER bar against Circa. Negative")
    say("  means Circa is the WEAKER close and easier to beat. This matters directly: Peter's rule")
    say("  is that an edge qualifies by beating EITHER benchmark in both halves, so a systematically")
    say("  weaker Circa would make 'beat either' easier than it sounds, and a harder Circa would")
    say("  make beating it the stronger claim of the two.")
    say("  Cache only - every close compared here was already stored. 0 calls, 0 paid credits.")
    # EVERY fixture that holds BOTH closes, not just tonight's batch. My first version looped over
    # `due`, which is only the games that were MISSING a Circa close before this run - so the
    # comparison would have covered one night's captures and then reset every night, never
    # accumulating. The whole point is that the number becomes meaningful as it grows.
    #
    # Free either way: /historical-odds is a FREE path (credit_gate.FREE_PATHS), and both files are
    # confirmed present on disk before either is read, so this spends nothing on either key.
    # The market map comes from the cached MKFILE, as board_clv_check does it. Passing {} let
    # close_for fall back to inventing outcome ids ({"1": mid, "2": mid+1}), which need not match
    # what is actually stored - the likely cause of the other 5 failures.
    try:
        mkmap = cl.load_markets(st, datetime.now(timezone.utc))
    except Exception as ex0:
        say(f"  market map unavailable ({type(ex0).__name__}) - comparison cannot run")
        return
    diffs, pairs, skipped = [], 0, {}
    both = [(cl.tp(f.get("start")), fid, f) for fid, f in st["fixtures"].items()
            if os.path.exists(hc._path(fid, "pinnacle")) and os.path.exists(hc._path(fid, "circasports"))]
    both = [(s2, fid, f) for s2, fid, f in both if s2]
    both.sort(reverse=True)
    say(f"  fixtures holding BOTH a Pinnacle and a Circa close: {len(both)}")
    for s_, fid, f in both:
        lg = f.get("league") or f.get("lg")
        try:
            hp = hc.get_hist(fid, ["pinnacle"], s_)
            hcc = hc.get_hist(fid, ["circasports"], s_)
        except Exception as ex2:
            skipped[type(ex2).__name__] = skipped.get(type(ex2).__name__, 0) + 1
            continue
        pmk, cmk = cl.book_markets(hp, "pinnacle"), cl.book_markets(hcc, "circasports")
        if not pmk or not cmk:
            skipped["one book had no market in its stored close"] = skipped.get(
                "one book had no market in its stored close", 0) + 1
            continue
        # Moneyline only, and only where BOTH books priced the same side. A spread or total would
        # need the lines to match too, and a mismatched line is a different bet - comparing those
        # would manufacture a difference that is really just two different markets.
        # The bet must be real TEXT, not None. close_for's first guard is parsed(b), which returns
        # "bet text not parsed" on None - that was 20 of the 25 failures on the first run, my bug
        # and not a data problem. A bare participant name is a moneyline bet on that side, and
        # which_team() matches it against the fixture's own p1/p2, so pricing p1 prices the SAME
        # side at both books, which is the whole requirement for a comparison.
        for mt in ("moneyline",):
            b = {"bet": f.get("p1"), "league": lg, "market": mt,
                 "game": f.get("game"), "game_start": f.get("start")}
            if not b["bet"]:
                skipped["fixture has no participant name"] = skipped.get(
                    "fixture has no participant name", 0) + 1
                continue
            try:
                pc, _ = cl.close_for(b, f, pmk, mkmap, s_, lg)
                cc, _ = cl.close_for(b, f, cmk, mkmap, s_, lg)
            except Exception:
                continue
            if not pc or not cc:
                skipped["close_for could not read one of the two"] = skipped.get(
                    "close_for could not read one of the two", 0) + 1
                continue
            if not (cs.close_verified(pc.get("how")) and cs.close_verified(cc.get("how"))):
                skipped["one close was not same-line verified"] = skipped.get(
                    "one close was not same-line verified", 0) + 1
                continue
            pairs += 1
            diffs.append(round(100.0 * (cc["p"] - pc["p"]), 2))
    if pairs:
        diffs.sort()
        mean = sum(diffs) / len(diffs)
        med = diffs[len(diffs) // 2]
        harder = sum(1 for d in diffs if d > 0)
        say(f"\n  comparable pairs: {pairs}")
        say(f"  Circa minus Pinnacle, in points of win probability:")
        say(f"     mean {mean:+.2f}   median {med:+.2f}   Circa higher on {harder}/{len(diffs)}")
        if abs(mean) < 0.5:
            say("  VERDICT: no material difference at this sample. Neither is systematically the")
            say("  harder close, so 'beat either' is not a materially softer bar than 'beat both'.")
        elif mean > 0:
            say("  VERDICT: Circa reads HIGHER on these sides - the HARDER close. Beating Circa is")
            say("  then the stronger of the two claims, and beating Pinnacle alone is the easier.")
        else:
            say("  VERDICT: Circa reads LOWER - the WEAKER close, easier to beat. Under 'beat")
            say("  either', a candidate could qualify on the softer benchmark. Worth knowing before")
            say("  any lane is promoted on a Circa-only pass.")
        say(f"\n  SAMPLE IS TINY. {pairs} pair(s) settles nothing on its own; this prints every")
        say("  night and the number only becomes meaningful as it accumulates.")
    else:
        say("\n  No comparable pair yet.")
        for k, n in sorted(skipped.items(), key=lambda x: -x[1]):
            say(f"      {n:3}  {k}")
        say("  Expected this early: a pair needs the SAME game to have both a stored Pinnacle close")
        say("  and a stored Circa close, and Circa capture only began Nov 9.")


def main():
    if not hc.FREE_KEY:
        say("ODDSPAPI_FREE_KEY not set - nothing run, 0 calls")
        return 1
    now = datetime.now(timezone.utc)
    say("CIRCA + PS3838 CLOSE CAPTURE - free key only, zero paid credits")
    say(f"books {BOOKS} | leagues {list(LEAGUES)} | cap {MAX_GAMES} games | "
        f"finished within the last {BACK_HOURS}h")
    say()

    # Confirm the two books are not on the paid route, rather than trusting that they are not.
    on_paid = [b for b in BOOKS if b in hc.PAID_BOOKS]
    if on_paid:
        say(f"REFUSING TO RUN: {on_paid} would be fetched on the PAID key (hist_cache.PAID_BOOKS).")
        say("This job exists to spend nothing. Fix the routing before running it again.")
        return 1
    say(f"  routing check: neither book is in hist_cache.PAID_BOOKS, so both go to the FREE key")

    # Fixtures come from the ledger's existing cache - no /fixtures purchase.
    st = {"fixtures": {}, "fx_last": {}}
    try:
        prev = tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        say(f"  fixture cache: {len(st['fixtures'])} fixtures read from disk - nothing purchased")
    except Exception as e:
        say(f"  fixture cache unavailable ({type(e).__name__}) - nothing to capture, 0 calls")
        return 1

    lo = now - timedelta(hours=BACK_HOURS)
    due = []
    for fid, f in st["fixtures"].items():
        s = cl.tp(f.get("start"))
        if not s or not (lo <= s <= now):
            continue
        if now - s < hc.FINAL_AFTER:      # not final yet: its close is not settled
            continue
        lg = f.get("league") or f.get("lg")
        if LEAGUES and lg and lg not in LEAGUES:
            continue
        missing = [b for b in BOOKS if not os.path.exists(hc._path(fid, b))]
        if missing:
            due.append((s, fid, missing))
    due.sort(reverse=True)                # newest first: tonight's closes matter most
    say(f"  games finished in the window, missing a Circa/ps3838 close: {len(due)}")
    if len(due) > MAX_GAMES:
        say(f"  capping at {MAX_GAMES}; the rest are picked up by the next run")
    due = due[:MAX_GAMES]
    if not due:
        say("\n  Nothing to capture this run. 0 calls.")
        # The comparison reads the CACHE, not tonight's captures, so it must still run here. My
        # first version put it after the capture loop only - and this early return skipped it, so
        # the very first run printed nothing at all. "Nothing due" is in fact the common case once
        # capture keeps up with the schedule.
        compare(st)
        try:
            import executor as ex
            ex.send("Bets CIRCA CLOSE CAPTURE (nothing due)", "\n".join(L))
        except Exception:
            pass
        return 0

    got = {b: 0 for b in BOOKS}
    empty = {b: 0 for b in BOOKS}
    err = {}
    calls = 0
    for s, fid, missing in due:
        h = hc.get_hist(fid, missing, s)
        calls += 1
        if isinstance(h, dict) and h.get("_error"):
            k = str(h["_error"])[:40]
            err[k] = err.get(k, 0) + 1
            continue
        for b in missing:
            mk = cl.book_markets(h, b)
            if mk:
                got[b] += 1
            else:
                empty[b] += 1

    say()
    say("=" * 70)
    say("WHAT WAS CAPTURED  (counts only; this is market data, no account figures)")
    say("=" * 70)
    say(f"  games attempted            {len(due)}")
    for b in BOOKS:
        say(f"  {b:14s} closes stored {got[b]:4d}   empty answers {empty[b]:4d}")
    if err:
        say(f"  errors: {err}")
    say()
    say(f"  get_hist batches issued    {calls}   (FREE meter; paid credits spent: 0)")
    say("  The free tier returns no quota header, so this count IS the measurement. If it climbs")
    say("  toward whatever the real monthly limit turns out to be, lower CC_MAX or the cadence.")
    say()
    compare(st)

    try:
        import executor as ex
        ex.send("Bets CIRCA CLOSE CAPTURE", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    print(f"circa close capture: attempted {len(due)}, "
          + ", ".join(f"{b} {got[b]}" for b in BOOKS) + f", batches {calls}, paid credits 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
