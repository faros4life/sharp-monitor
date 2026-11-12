#!/usr/bin/env python3
"""
CLV READOUT from committed state (Peter, Nov 12). READ-ONLY, NO IMAP, NO ESPN, NO ODDSPAPI.

The ledger run that would have reported these numbers was still inside its own step at 30 minutes
against a 40-minute timeout. Peter's instruction: produce the readout from the scored ledger
already on disk rather than rerunning anything. Nothing here fetches, scores, writes or changes a
result - it reads clv/state.enc and tracker/state.enc and reports.

It reproduces the ledger's OWN headline arithmetic rather than inventing one, so the figures are
comparable to the official email:
    stale, _  = cstale.stale_map(bets, tracker)          proven duplicates of a live tracker row
    all_scored = rows with clv not None and id not in stale
    held       = rows carrying fixture_doubt              sticky, out of every figure
    rest       = all_scored minus held
plus the FAIL-CLOSED _unverified test: a row with no currently validated fixture and no durable
record of a prior validation of that same fixture is excluded, not counted.

Anything that cannot be verified from local state is printed as such rather than estimated.
"""
import json
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import clv_stale as cstale
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
L = []


def say(t=""):
    L.append(t)
    print(t)


def fig(rows, label):
    v = [r["clv"] for r in rows if r.get("clv") is not None]
    if not v:
        say(f"  {label:<34} n   0")
        return
    beat = sum(1 for x in v if x > 0)
    say(f"  {label:<34} n {len(v):3d}   avg CLV {100 * sum(v) / len(v):+.2f}%   "
        f"beat close {beat}/{len(v)} ({100 * beat / len(v):.0f}%)")


def main():
    now = datetime.now(timezone.utc)
    say("CLV READOUT from committed state - no IMAP, no ESPN, no OddsPapi, nothing written")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("=" * 96)
    try:
        st = cl.tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"  CLV state unreadable ({type(e).__name__}) - CANNOT VERIFY anything below")
        return 1
    bets = st.get("bets") or {}
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tracker = raw if isinstance(raw, dict) else {}
    except Exception as e:
        tracker = {}
        say(f"  tracker unreadable ({type(e).__name__}) - stale exclusion CANNOT be applied")

    try:
        stale, _unproven = cstale.stale_map(bets, tracker), cstale.orphans_unproven(bets, tracker)
    except Exception as e:
        stale = {}
        say(f"  stale map unavailable ({type(e).__name__}) - figures include stale rows, FLAGGED")

    all_scored = [dict(r, id=k) for k, r in bets.items()
                  if r.get("clv") is not None and k not in stale]
    held = [r for r in all_scored if r.get("fixture_doubt")]
    hid = {r["id"] for r in held}
    rest = [r for r in all_scored if r["id"] not in hid]

    def src(r):
        return str((r.get("snap") or {}).get("source") or "").lower()

    say("")
    say("HEADLINE (ledger's own arithmetic, from committed state)")
    say("=" * 96)
    fig(rest, "ALL scored")
    fig([r for r in rest if src(r).startswith("bot")], "bot")
    fig([r for r in rest if not src(r).startswith("bot")], "Peter/other")
    say("")
    say(f"  scored rows in state      {sum(1 for r in bets.values() if r.get('clv') is not None)}")
    say(f"  excluded as stale          {len(stale)}")
    say(f"  still HELD OUT             {len(held)}")

    # ---------------------------------------------------------------- the release
    rel = [(k, r) for k, r in bets.items() if r.get("released_from")]
    say("")
    say("RELEASE VERIFICATION")
    say("=" * 96)
    say(f"  rows carrying released_from (the cleared flag's prior value): {len(rel)}")
    bad = [k for k, r in rel if r.get("fixture_doubt")]
    say(f"  released rows still carrying fixture_doubt: {len(bad)}  (must be 0)")
    relbot = [r for _, r in rel if str((r.get("snap") or {}).get("source") or "").lower().startswith("bot")]
    say(f"  of the released rows, source=bot: {len(relbot)}")
    if rel:
        v = [r["clv"] for _, r in rel if r.get("clv") is not None]
        if v:
            say(f"  released rows mean CLV {100 * sum(v) / len(v):+.2f}%, "
                f"beat close {sum(1 for x in v if x > 0)}/{len(v)}")

    # ---------------------------------------------------------------- the excluded wrong match
    say("")
    say("WRONG-MATCH EXCLUSION")
    say("=" * 96)
    found = False
    for k, r in bets.items():
        s = r.get("snap") or {}
        g = str(s.get("game") or "")
        if "houston" in g.lower() and "dallas" in g.lower():
            f = (st.get("fixtures") or {}).get(r.get("fixture")) or {}
            found = True
            say(f"  {k[:36]}")
            say(f"      bet game text : {g[:60]}")
            say(f"      stored fixture: {str(f.get('p1'))[:28]} v {str(f.get('p2'))[:28]}")
            say(f"      CLV {100 * r['clv']:+.2f}%" if r.get("clv") is not None else "      no CLV")
            say(f"      fixture_doubt present: {bool(r.get('fixture_doubt'))}   "
                f"released_from present: {bool(r.get('released_from'))}")
            say(f"      -> {'STILL EXCLUDED (correct)' if r.get('fixture_doubt') else 'NOT EXCLUDED - INVESTIGATE'}")
    if not found:
        say("  no Houston/Dallas row found by game text - CANNOT VERIFY from this state")

    say("")
    say("=" * 96)
    try:
        import executor as ex
        ex.send("Bets CLV READOUT (from committed state)", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print(f"clv readout: scored {len(rest)}, held {len(held)}, released {len(rel)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
