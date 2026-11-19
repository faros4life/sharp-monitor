#!/usr/bin/env python3
"""
NOVIG FILL AUDIT - READ-ONLY (Peter, 19 Nov 2026).

WHY. Two Novig bets matched today - GS/MEM Under 225.5 at 2.00x and LAC/SA Under 226.5 at 1.92x,
$419.30 of stake between them, both confirmed MATCHED in the Novig app - and BOTH carry
filled_stake: null in our registry. The question this answers is how far that goes: how many Novig
placements since 12 Nov have no confirmed fill, and which of those are missing from grading, CLV
and P/L.

SOURCES, AND WHY NOT EMAIL. reconcile_placed.py already measures the placement side, but it reads
the "Bets LIVE" mailbox, and Peter's standing rule is to work from code, workflow logs, private
registry metadata and test results instead. The private registry now carries the same order rows,
so this reads it directly and the mailbox is not touched.

WHAT IT CANNOT DO, STATED RATHER THAN GUESSED. It cannot ask Novig what actually traded: the
read-only key returns HTTP 401 on /v3/portfolio/orders, and the per-order route needs the trading
key. So "filled" here means OUR RECORD says a fill was read, never that the venue confirmed one,
and "unknown" means our record never read one - NOT that nothing traded. Today proves the
difference: both of today's orders are "unknown" here and both matched.

THREE STATES, NEVER TWO. Peter, 19 Nov: separate confirmed fills, confirmed unfilled orders and
unreadable orders. They have different remedies - a confirmed zero-fill needs nothing, an unknown
needs a venue read - and collapsing them is what let this run for a week.

READ-ONLY: no venue call at all, no write to any state, no email. Counts and prices only.
"""
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_selection as csel
import registry as rg
import tracker_build as tb

FROM = os.environ.get("AUDIT_FROM", "") or "2026-11-12"
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def ident(key):
    """(league, game tokens, market, side) from a registry order key, or None.

    The key is lane|league|game|market|side, or league|game|market|side when no lane prefix.
    """
    parts = [p for p in str(key or "").split("|") if p]
    if parts and parts[0] in ("board", "r1", "rules", "lane2"):
        parts = parts[1:]
    if len(parts) < 4:
        return None
    lg, game, mkt, side = parts[0], parts[1], parts[2], parts[3]
    return (lg.upper(), tb.toks(game) - tb.WEAK, str(mkt).lower(), str(side).upper())


def same_play(a, b):
    if not a or not b:
        return False
    if a[0] != b[0] or a[2] != b[2]:
        return False
    if not (a[1] & b[1]):
        return False
    return a[3] == b[3] or bool(tb.toks(a[3]) & tb.toks(b[3]))


def main():
    now = datetime.now(timezone.utc)
    say("NOVIG FILL AUDIT - READ-ONLY, no venue call, no email, no write")
    say(f"generated {now.astimezone(cl.ET):%Y-%m-%d %H:%M} ET   placements from {FROM}")
    say("=" * 104)
    reg = rg.load()
    if reg is None:
        say("FATAL: private registry unreadable - this audit has no other source and refuses to "
            "estimate one.")
        return 1

    # ---------------------------------------------------------------- 1. every Novig placement
    legs = []
    for row in (reg.get("orders") or []):
        dec = str(row.get("decided_utc") or "")[:10]
        for fld in ("live_order", "live_rest"):
            lo = row.get(fld) or {}
            if isinstance(lo, dict) and lo.get("book") == "novig" and lo.get("order_id"):
                legs.append((row, fld, lo, dec))
        for lo in (row.get("live_more") or []):
            if isinstance(lo, dict) and lo.get("book") == "novig" and lo.get("order_id"):
                legs.append((row, "live_more", lo, dec))
    legs = [x for x in legs if not x[3] or x[3] >= FROM]
    # one leg per order id: the same order can appear in a journal row and an end-of-run row
    seen, uniq = set(), []
    for row, fld, lo, dec in sorted(legs, key=lambda x: str(x[0].get("decided_utc") or "")):
        oid = str(lo["order_id"])
        if oid in seen:
            continue
        seen.add(oid)
        uniq.append((row, fld, lo, dec))
    say(f"Novig order legs on record from {FROM}: {len(uniq)} "
        f"(from {len(legs)} container entries; duplicates across journal and ledger rows collapsed)")
    say("")

    # ---------------------------------------------------------------- 2. three states
    filled, zero, unknown = [], [], []
    for row, fld, lo, dec in uniq:
        fs = lo.get("filled_stake")
        if fs is None:
            unknown.append((row, fld, lo, dec))
        elif float(fs) > 0:
            filled.append((row, fld, lo, dec))
        else:
            zero.append((row, fld, lo, dec))
    say("STATE OF EACH PLACEMENT - three states, never two")
    say("-" * 104)
    say(f"  {len(filled):4d}  FILL READ      our record read a fill back (stake recorded)")
    say(f"  {len(zero):4d}  ZERO FILL READ our record read the fill and it was nothing")
    say(f"  {len(unknown):4d}  UNKNOWN        the fill was never read - NOT a no-fill")
    say("")
    say("  'FILL READ' is our record, not the venue. No venue call is possible here: the")
    say("  read-only Novig key gets HTTP 401 on /v3/portfolio/orders and the per-order route")
    say("  needs the trading key. Today's two matched bets both sit in UNKNOWN below, which is")
    say("  exactly why UNKNOWN must never be reported as a no-fill.")
    say("")

    by_day = collections.Counter(d for _r, _f, _l, d in unknown)
    if by_day:
        say("  UNKNOWN by day placed:")
        for d, n in sorted(by_day.items()):
            say(f"    {d}  {n}")
        say("")

    # ---------------------------------------------------------------- 3. grading / CLV / P&L
    say("MISSING GRADING, CLV AND P/L")
    say("-" * 104)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
        bets = st.get("bets") or {}
    except Exception as e:
        say(f"  clv/state.enc unreadable ({type(e).__name__}) - the CLV column cannot be built, "
            f"and is reported as UNAVAILABLE rather than empty.")
        bets = None
    try:
        trk = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        say(f"  tracker/state.enc unreadable ({type(e).__name__}) - the grading column cannot be "
            f"built, and is reported as UNAVAILABLE rather than empty.")
        trk = None

    led_idents = []
    if bets is not None:
        for rid, rec in bets.items():
            s = rec.get("snap") or {}
            pb = tb.parse_bet(s.get("bet") or "")
            side = ""
            if pb:
                side = str(pb[1]).upper()
            led_idents.append((str(s.get("league") or "").upper(),
                               tb.toks(s.get("game")) - tb.WEAK,
                               str(pb[0]).lower() if pb else "",
                               side, rid, rec))
    trk_idents = []
    if trk is not None:
        for tid, b in trk.items():
            pb = tb.parse_bet(b.get("bet") or "")
            trk_idents.append((str(b.get("league") or "").upper(),
                               tb.toks(b.get("game")) - tb.WEAK,
                               str(pb[0]).lower() if pb else "",
                               str(pb[1]).upper() if pb else "", tid, b))

    no_track, no_clv, rows = 0, 0, []
    for row, fld, lo, dec in uniq:
        idt = ident(row.get("key"))
        tr = next((t for t in trk_idents if same_play(idt, t[:4])), None) if trk is not None else "NA"
        le = next((l for l in led_idents if same_play(idt, l[:4])), None) if bets is not None else "NA"
        has_clv = (le not in (None, "NA")) and (le[5].get("clv") is not None)
        if tr is None:
            no_track += 1
        if le is None or (le != "NA" and not has_clv):
            no_clv += 1
        rows.append((row, fld, lo, dec, tr, le, has_clv))
    if trk is not None:
        say(f"  {no_track} of {len(uniq)} Novig placements have NO tracker row - not graded, so no "
            f"result and no P/L.")
    if bets is not None:
        say(f"  {no_clv} of {len(uniq)} have no certified CLV row.")
    say("")

    say("THE PLACEMENTS THAT NEED A VENUE ANSWER (unknown fill), newest first")
    say("-" * 104)
    for row, fld, lo, dec, tr, le, has_clv in reversed(
            [r for r in rows if r[2].get("filled_stake") is None]):
        key = str(row.get("key") or "").replace("|", " ")[:48]
        say(f"  {str(row.get('decided_utc') or '')[:16]:<17} {key:<48} [{fld}]"
            f" limit {lo.get('limit')}"
            + ("  tracker: none" if tr is None else "  tracker: yes")
            + ("  CLV: none" if not has_clv else "  CLV: yes"))
    say("")
    say("Counts and prices only. No dollar figures. No venue call, no email, nothing written.")
    os.makedirs("audit", exist_ok=True)
    json.dump({"generated": cl.iso(now), "from": FROM, "legs": len(uniq),
               "fill_read": len(filled), "zero_fill": len(zero), "unknown": len(unknown),
               "no_tracker": no_track, "no_clv": no_clv},
              open("audit/novig_fill_audit.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
