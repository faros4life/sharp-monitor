#!/usr/bin/env python3
"""
STAGE 2 BEFORE/AFTER (Peter, Nov 13 2026). READ-ONLY.

Shows what selection-level collapsing does to the headline, so the feature flag can be turned on
with the numbers already in hand rather than discovered afterwards.

Three columns, each computed with the LEDGER'S OWN arithmetic so they are comparable:
  BEFORE        today's figures: one row per fill, released rows still reflagged
  + STAGE 1     released rows honoured (clv_ledger.apply_doubt over a copy)
  + STAGE 2     and then one observation per selection

NO WRITE, NO FETCH, NO IMAP, NO OddsPapi call. It reads clv/state.enc and tracker/state.enc and
prints. The flag CLV_SELECTION_MODE is NOT consulted here - this report exists to decide it.

MONEY RULE (CLAUDE.md): the log prints counts, percentages and ratios. Dollar amounts go to the
private email only.
"""
import copy
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import clv_selection as csel
import clv_stale as cstale
import tracker_build as tb

ET = tb.ET
L, SCREEN = [], []


def say(t="", money=False):
    L.append(t)
    if not money:
        SCREEN.append(t)
        print(t, flush=True)


def ledger_scored(st, bets, tracker):
    """The ledger's own 'scored' set: not stale, not held out, not unvalidatable."""
    try:
        stale = cstale.stale_map(bets, tracker)
    except Exception:
        stale = {}
    all_scored = {k: r for k, r in bets.items() if r.get("clv") is not None and k not in stale}
    rest = {k: r for k, r in all_scored.items() if not r.get("fixture_doubt")}

    def unverified(r):
        if cl.fixture_check(st, r)[0] != "unvalidatable":
            return False
        prev = r.get("fixture_ok") or {}
        return not (prev.get("fixture") and prev["fixture"] == r.get("fixture"))

    return {k: r for k, r in rest.items() if not unverified(r)}, stale


def line(label, s):
    if not s.get("n"):
        say(f"  {label:<26} n    0")
        return
    se = f" +/-{100 * s['se']:.2f}" if s.get("se") is not None else ""
    # ROI prints UNAVAIL, never 0.00%, when no observation carried a profit - see
    # clv_selection.stats(): the ledger snapshot does not capture profit at all.
    roi = (f"{s['roi_pct']:+.2f}% on {s['n_settled']} settled" if s.get("roi_pct") is not None
           else f"UNAVAIL ({s.get('has_profit', 0)}/{s['n']} rows carry profit)")
    say(f"  {label:<26} n {s['n']:4d}   mean CLV {100 * s['mean']:+.2f}%{se}   "
        f"pos {s['pos']}/{s['n']} ({s['pos_pct']:.0f}%)   ROI {roi}   fills {s['fills']}")


def main():
    now = datetime.now(timezone.utc)
    say("STAGE 2 BEFORE/AFTER - selection-level CLV. READ-ONLY, nothing written or fetched.")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("=" * 100)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    bets = st.get("bets") or {}
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        tracker = {}
        say(f"WARNING: tracker unreadable ({type(e).__name__}) - dup_of CANNOT be honoured, "
            f"so the Stage 2 column understates the collapse")

    before, stale = ledger_scored(st, bets, tracker)
    say(f"  ledger rows {len(bets)} | excluded stale {len(stale)} | tracker rows {len(tracker)}")

    # --- Stage 1 applied to a COPY: released rows honoured, nothing written
    s1 = copy.deepcopy(bets)
    for r in s1.values():
        if r.get("released_from") and r.get("fixture_doubt"):
            r.pop("fixture_doubt")
    for r in s1.values():
        if r.get("clv") is not None:
            cl.apply_doubt(st, r, now)
    after1, _ = ledger_scored(st, s1, tracker)

    # --- Stage 2 on top: one observation per selection
    obs = csel.selections(after1, tracker, exclude=set(stale))
    rows2 = list(obs.values())

    def as_obs(d):
        """A per-row set expressed as observations, so the three columns use one stats()."""
        out = []
        for k, r in d.items():
            s = r.get("snap") or {}
            out.append({"clv": r.get("clv"), "stake": tb.num(s.get("stake")),
                        "profit": tb.num(s.get("profit")), "result": s.get("result"),
                        "source": s.get("source"), "game_start": s.get("game_start"), "n_fills": 1})
        return out

    b_obs, a1_obs = as_obs(before), as_obs(after1)

    say("")
    say("HEADLINE")
    say("=" * 100)
    line("BEFORE (today)", csel.stats(b_obs))
    line("+ STAGE 1", csel.stats(a1_obs))
    line("+ STAGE 2 (selections)", csel.stats(rows2))
    say("")
    say(f"  certified UNIQUE SELECTIONS: {len(rows2)}   (from {len(after1)} certified fill rows)")
    say(f"  rows collapsed away: {len(after1) - len(rows2)}")

    say("")
    say("BY SOURCE (Stage 2 basis)")
    say("=" * 100)
    for src in sorted({str(o.get("source") or "unknown") for o in rows2}):
        line(src, csel.stats([o for o in rows2 if str(o.get("source") or "unknown") == src]))

    say("")
    say("FIRST HALF vs SECOND HALF (by game start, split by count)")
    say("=" * 100)
    for label, rows in (("BEFORE (per fill)", b_obs), ("+ STAGE 2 (selections)", rows2)):
        h1, h2, nod = csel.halves(rows)
        say(f"  {label}")
        line("    first half", csel.stats(h1))
        line("    second half", csel.stats(h2))
        if nod:
            say(f"    excluded from the split (no game start): {len(nod)}")

    say("")
    say("WHAT COLLAPSED THE MOST")
    say("=" * 100)
    big = sorted(rows2, key=lambda o: -o.get("n_fills", 1))[:8]
    for o in big:
        if o.get("n_fills", 1) < 2:
            continue
        say(f"  {o['n_fills']:3d} fills -> 1   clv {100 * o['clv']:+.2f}%   {o.get('basis')}")
        say(f"              {str(o.get('book')):<12} {str(o.get('game_start'))[:10]} "
            f"how={','.join(o.get('how') or []) or '-'} close spread {o.get('close_spread')}")
    say("")
    fb = [o for o in rows2 if str(o.get("basis", "")).startswith("FALLBACK")]
    say(f"  observations built from the position itself: {len(rows2) - len(fb)}")
    say(f"  observations on a FALLBACK mean (no summable stake/payout): {len(fb)}")
    unid = [k for k in obs if k.startswith("UNIDENTIFIED|")]
    say(f"  rows whose bet text would not parse, kept as their own selection: {len(unid)}")
    dups = [o for o in rows2 if str(o.get("why", "")).startswith("dup_of")]
    say(f"  selections whose identity came from dup_of: {len(dups)}")

    say("")
    say("UNITS")
    say("=" * 100)
    say("  Units are NOT reported here. A unit is a lane concept ($300 Phase 1, $200 Board/R1)")
    say("  and the ledger rows carry no lane - only 36 registry orders exist against 363 rows, so")
    say("  any per-row unit figure would be a guess for most of the sample. ROI above needs no")
    say("  unit and is reported. Stage 3 persists the lane with the order, which is what makes a")
    say("  units column honest; it is left blank rather than filled in with an assumption.")
    say("  ROI is also blank: clv_ledger's snapshot captures stake and to_pay but NOT profit")
    say("  (its field list is at clv_ledger.py:915), so profit sums to zero across the ledger and")
    say("  any ROI computed from it would be a fabricated +0.00%. Capturing profit on the snapshot")
    say("  is a one-field addition and belongs with Stage 3; it is not assumed here.")
    say("  Total staked is in the private email.", money=False)
    for label, rows in (("BEFORE", b_obs), ("STAGE 2", rows2)):
        s = csel.stats(rows)
        say(f"  {label}: staked {s['stake']} profit {s['profit']}", money=True)

    say("")
    say("=" * 100)
    say("Nothing was written, released, rescored or fetched. CLV_SELECTION_MODE is unchanged.")

    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as ex
            ex.send("Stage 2 selection-level CLV: before/after", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as e:
            print(f"email skipped ({type(e).__name__})", flush=True)
    sb, s2 = csel.stats(b_obs), csel.stats(rows2)
    print(f"stage2: before n={sb['n']} mean={100 * sb['mean']:+.2f}% | "
          f"selections n={s2['n']} mean={100 * s2['mean']:+.2f}%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
