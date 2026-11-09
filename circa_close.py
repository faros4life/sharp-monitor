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
    say("  NOT YET A CLV COMPARISON. This only builds the history. Grading a bet against a Circa")
    say("  close is a separate, approved-in-advance change to the reporters, and it needs enough")
    say("  stored closes to be worth running - which is what this is accumulating.")

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
