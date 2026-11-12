#!/usr/bin/env python3
"""
FIXTURE CACHE REPORT (Peter/Muse, Nov 12, Priority 2). READ-ONLY, NO IMAP, NO API CALL.

Peter's item 4: do not run another 30-day IMAP scan if the fixture cache already holds the answer.
It does. fx_last and the fixtures themselves live in clv/state.enc, so this reads that file and
nothing else - no mail, no OddsPapi request, no credit. It runs in seconds rather than 25 minutes.

WHAT IT SEPARATES, which "no OddsPapi fixture matched" does not:

  MISSING FIXTURE      the league has no fixture anywhere near the game. Nothing was ever offered
                       to the matcher, so this is a FETCH question, not a matching one.
  STALE FETCH          the league's newest fixture starts BEFORE the game in question, and
                       fx_last shows the last fetch. If that fetch is inside the 6 h cooldown, the
                       refresh that would have covered the game was refused - a refresh defect.
  MATCHING             fixtures exist in the window and the token test still found no unique
                       winner. Only this is a matching defect.

Nothing is forced. A row with no unique winner stays unmatched: find_fixture returns None on a tie
by design, because a wrong fixture produces a confidently wrong CLV, which is worse than no CLV.
"""
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executed_clv as xc
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
COOLDOWN_H = 6          # refresh_fixtures' own per-league cooldown
L = []


def say(t=""):
    L.append(t)
    print(t)


def main():
    now = datetime.now(timezone.utc)
    say("FIXTURE CACHE REPORT - why rows read 'no OddsPapi fixture matched'")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("READ-ONLY. No IMAP scan, no OddsPapi call, no credit spent, nothing written.")
    say("=" * 100)

    try:
        cst = cl.tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"  CLV state unreadable ({type(e).__name__}) - nothing to report")
        return 1
    fx = cst.get("fixtures") or {}
    fx_last = cst.get("fx_last") or {}
    bets = cst.get("bets") or {}
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tbets = raw if isinstance(raw, dict) else {}
    except Exception:
        tbets = {}
    st = {"fixtures": fx, "fx_last": fx_last}

    # ---------------------------------------------------------------- the cache itself
    say("")
    say("FIXTURE CACHE, per league")
    say("=" * 100)
    say(f"  {'league':<8} {'fixtures':>9} {'earliest start':>18} {'latest start':>18} "
        f"{'last fetch':>18} {'age':>8}")
    say("  " + "-" * 94)
    byl = collections.defaultdict(list)
    for f in fx.values():
        d = cl.tp(f.get("start"))
        if d:
            byl[str(f.get("lg"))].append(d)
    for lg in sorted(byl):
        ds = sorted(byl[lg])
        lastf = cl.tp(fx_last.get(lg))
        age = f"{(now - lastf).total_seconds()/3600:.1f}h" if lastf else "never"
        say(f"  {lg:<8} {len(ds):9d} {ds[0].astimezone(ET):%Y-%m-%d %H:%M:>18} "
            f"{ds[-1].astimezone(ET):%Y-%m-%d %H:%M:>18} "
            f"{(lastf.astimezone(ET).strftime('%Y-%m-%d %H:%M') if lastf else '-'):>18} {age:>8}")
    say(f"  total fixtures {len(fx)} | leagues with a recorded fetch: {len(fx_last)}")
    say(f"  refresh_fixtures cooldown is {COOLDOWN_H}h per league: a league fetched more recently")
    say("  than that CANNOT refetch, whatever is missing.")

    # ---------------------------------------------------------------- the unscored rows
    say("")
    say("UNSCORED ROWS WHOSE REASON MENTIONS A FIXTURE")
    say("=" * 100)
    rows = [(k, r) for k, r in bets.items()
            if r.get("clv") is None and "fixture" in str(r.get("why") or "").lower()]
    say(f"  {len(rows)} row(s)")
    verdicts = collections.Counter()
    for k, rec in sorted(rows, key=lambda x: str((x[1].get("snap") or {}).get("game_start") or "")):
        s = rec.get("snap") or {}
        tr = tbets.get(k) or {}
        lg = s.get("league") or tr.get("league")
        gs = s.get("game_start") or tr.get("game_start")
        gsd = cl.tp(gs)
        game = str(s.get("game") or tr.get("game") or "")[:46]
        say("")
        say(f"  {k[:34]:<34} {str(lg):<6} {str(gs)[:16]:<16} {game}")
        say(f"      stored reason: {str(rec.get('why'))[:72]}")

        # which gate - replayed against the same cache find_fixture uses
        q = {"bet": s.get("bet") or tr.get("bet"), "league": lg, "game": game,
             "teams": s.get("teams") or tr.get("teams"), "game_start": gs,
             "book": s.get("book") or tr.get("book"), "_start_was_given": bool(gs)}
        # BEFORE/AFTER: does the matcher resolve this row NOW? find_fixture returns a fixture id
        # only on a UNIQUE winner, so a row that resolves here is one the fix recovered - not one
        # it force-matched. A tie still returns None and the row stays unmatched.
        try:
            fid_now = cl.find_fixture(st, q)
        except Exception:
            fid_now = None
        if fid_now:
            f_now = (st.get("fixtures") or {}).get(fid_now) or {}
            verdicts["RESOLVES NOW (fix recovered it)"] += 1
            say(f"      RESOLVES NOW -> {str(f_now.get('p1'))[:28]} v {str(f_now.get('p2'))[:28]}")
            say("      (unique winner; a tie would still return None)")
            continue
        try:
            gate, _, detail = xc.why_no_fixture(st, q, lg)
        except Exception as e:
            gate, detail = f"undetermined ({type(e).__name__})", ""
        say(f"      GATE: {gate}")
        if detail:
            say(f"      {str(detail)[:90]}")

        # was the needed fixture ever fetched? compare the game to the league's coverage
        ds = sorted(byl.get(str(lg) or "", []))
        lastf = cl.tp(fx_last.get(str(lg)))
        if not ds:
            verdicts["league never fetched"] += 1
            say("      VERDICT: MISSING - this league has no fixture in the cache at all.")
        elif gsd and gsd > ds[-1]:
            gap = (gsd - ds[-1]).total_seconds() / 3600
            verdicts["game past the newest fixture"] += 1
            say(f"      VERDICT: STALE FETCH - the game starts {gap:.1f}h AFTER the newest fixture")
            say(f"               the cache holds for {lg}. It was never fetched, so the matcher")
            say("               was never offered it. This is a FETCH question, not matching.")
            if lastf:
                since = (now - lastf).total_seconds() / 3600
                say(f"               last {lg} fetch {since:.1f}h ago"
                    + ("  <- INSIDE the 6h cooldown: a refresh would be REFUSED right now"
                       if since < COOLDOWN_H else "  <- outside the cooldown: a refresh is allowed"))
        elif gsd and gsd < ds[0]:
            verdicts["game before the oldest fixture"] += 1
            say(f"      VERDICT: AGED OUT - the game predates the oldest fixture held for {lg}.")
        else:
            verdicts["in window, matcher found none"] += 1
            say("      VERDICT: MATCHING - fixtures exist around this game and the token test")
            say("               still found no unique winner. This one IS a matching question.")

    say("")
    say("=" * 100)
    say("ROLL-UP")
    say("=" * 100)
    for v, n in verdicts.most_common():
        say(f"  {v:<34} {n:3d}")
    say("")
    say("  Only 'in window, matcher found none' is a matching defect. The rest are fetch coverage,")
    say("  and the cooldown line above says whether a refresh is even permitted right now.")
    say("=" * 100)
    try:
        import executor as ex
        ex.send(f"Bets FIXTURE CACHE REPORT ({len(rows)} unscored rows)", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print(f"fixture cache: {len(fx)} fixtures, {len(rows)} unscored rows, "
          + ", ".join(f"{a}={b}" for a, b in verdicts.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
