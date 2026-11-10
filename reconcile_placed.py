#!/usr/bin/env python3
"""
PLACEMENT RECONCILIATION (Peter, Nov 10: "Go"). READ-ONLY. 0 paid credits. Counts only - no stake,
no price, no balance, in the log or anywhere else.

THE PROBLEM. My Lane 1 audit reported 3 placements in Nov 4-10. Novig's own fill confirmations show
8 plays in that window. The system's record of what it did disagrees with the book's record of what
happened, by about 3x, and every per-play number built on the ledger inherits that error.

THE SUSPECTED MECHANISM, which this measures rather than assumes. A ledger row can carry THREE
order containers:

    live_order    the first order on the play
    live_rest     a resting bid, which fills later and separately
    live_more     a LIST of further orders on the same play

tracker_build.bot_keys() - the function the tracker itself trusts to decide what the bot placed -
counts a play as placed when ANY of those three has status "placed" AND an order_id. My audit, and
rest_depth_report's funnel, read live_order alone. If a play's placement lives in live_rest or in
live_more, I score it zero; if a play has several legs, I score it one. Both errors run the same
direction - undercounting - which is the direction of the 3-versus-8 gap.

WHAT IT PRINTS. Four counts of the same week, from three independent records:

    A    plays with live_order.status == "placed"            (how I counted)
    A'   plays with ANY container placed + order_id          (how bot_keys counts)
    A''  LEGS placed across all containers                   (what the book would see as orders)
    B    keys from bot_keys() over the "Bets LIVE" emails    (the bot's own claim)
    C    rows the books themselves recorded as the bot's     (tracker, source == "bot")

A versus A' and A'' localizes the loss inside the ledger. A' versus B cross-checks the ledger
against the bot's own mail. C is the book's record, and is the only one of the four that is
authoritative about what actually traded.

A' and A'' cannot be compared to C key-by-key: tracker_build.bot_match returns a boolean and does
not store which key it matched, so a book row knows it was the bot's but not which play it was.
That is a real limit of the existing join and is stated, not papered over.
"""
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import executor as ex
import rest_depth_report as rd
import tracker_build as tb

DAYS = int(os.environ.get("RECON_DAYS", "") or "14")
TSTATE = "tracker/state.enc"
CONTAINERS = ("live_order", "live_rest", "live_more")


def say(*a):
    print(*a, flush=True)


def legs(row):
    """Every order container on the row, flattened. live_more is a LIST; the other two are dicts."""
    out = [row.get("live_order") or {}, row.get("live_rest") or {}]
    out += [x or {} for x in (row.get("live_more") or [])]
    return out


def placed(lo):
    """bot_keys()'s own test, copied deliberately so the two can never drift apart."""
    return lo.get("status") == "placed" and lo.get("order_id")


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say(f"PLACEMENT RECONCILIATION | last {DAYS} days | read-only, 0 paid credits, counts only")
    say("=" * 92)

    # ---- the ledger, read out of the executor's own emails (the same loader the audit uses) ----
    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in rd.SUBJECTS:
            r, n = rd.ledger_rows(M, s, since)
            rows += r
            mails += n
        # De-duplicate by key PREFERRING the row that records a placement. The previous rule was
        # seen[k] = r, last row wins - so a play alerted again on a later run had its placement
        # overwritten by the later candidate row, which carries no order at all. That is why 15
        # plays the bot's own mail reports as placed read back here as "None, None".
        seen = {}
        for r in rows:
            k = r.get("key") or r.get("play_key")
            if not k:
                continue
            cur = seen.get(k)
            if cur is None or (any(placed(lo) for lo in legs(r))
                               and not any(placed(lo) for lo in legs(cur))):
                seen[k] = r
        say(f"  {mails} ledger email(s), {len(rows)} row(s), {len(seen)} distinct play(s)")

        # ---- B: what the bot's own mail says it placed ----
        try:
            B = tb.bot_keys(M, days=DAYS)
        except Exception as e:
            B = None
            say(f"  bot_keys unavailable ({type(e).__name__}: {str(e)[:70]})")
    finally:
        try:
            M.logout()
        except Exception:
            pass

    A = [r for r in seen.values() if (r.get("live_order") or {}).get("status") == "placed"]
    Ap = [r for r in seen.values() if any(placed(lo) for lo in legs(r))]
    App = sum(1 for r in seen.values() for lo in legs(r) if placed(lo))

    say("")
    say("  A    plays with live_order.status == 'placed'        "
        f"{len(A):4}   <- how I counted")
    say("  A'   plays with ANY container placed + order_id      "
        f"{len(Ap):4}   <- how bot_keys counts")
    say(f"  A''  placed LEGS across all containers               {App:4}")
    if B is not None:
        say(f"  B    keys from the bot's own 'Bets LIVE' emails      {len(B):4}")

    # ---- where, precisely, the loss happens ----
    extra = [r for r in Ap if (r.get("live_order") or {}).get("status") != "placed"]
    if extra:
        say("")
        say(f"  {len(extra)} play(s) ARE placed but invisible to the live_order test. Container per play:")
        for r in extra[:25]:
            where = []
            if placed(r.get("live_rest") or {}):
                where.append("live_rest")
            nm = sum(1 for x in (r.get("live_more") or []) if placed(x or {}))
            if nm:
                where.append(f"live_more x{nm}")
            say(f"      {str(r.get('key'))[:58]:<58} {', '.join(where) or 'unknown'}")
        if len(extra) > 25:
            say(f"      ... and {len(extra) - 25} more")
        say("")
        say("  This is the undercount, and it is mechanical: the placement is recorded, in a field")
        say("  the reader never looked at. No bet was missed; the MEASUREMENT was.")
    else:
        say("")
        say("  Every placed play is visible to the live_order test, so the 3-versus-8 gap is NOT")
        say("  the container bug. Look below at B and C before blaming the ledger.")

    # WHEN those placements happened. My per-day supply figures came from the same broken reader,
    # so "no automated plays since Nov 9" rests on a count that was wrong by more than half. This
    # dates every placement instead of inferring the drought from an aggregate.
    if Ap:
        from zoneinfo import ZoneInfo as _Z
        et = _Z("America/New_York")
        per = collections.Counter()
        undated = 0
        for r in Ap:
            v = str(r.get("decided_utc") or r.get("sent_utc") or "")
            try:
                d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                per[d.astimezone(et).strftime("%Y-%m-%d")] += 1
            except Exception:
                undated += 1
        say("")
        say("  WHEN the placements happened (ET day of the decision):")
        for d in sorted(per):
            say(f"      {d}  {per[d]:3}  {'#' * min(per[d], 40)}")
        if undated:
            say(f"      {undated} placement(s) carry no readable date")
        say("")
        say("  A day missing from that list had NO placement. A day present had one, whatever an")
        say("  aggregate built on the old reader said.")

    multi = [r for r in seen.values() if sum(1 for lo in legs(r) if placed(lo)) > 1]
    if multi:
        say("")
        say(f"  {len(multi)} play(s) carry MORE THAN ONE placed leg, so a per-play count understates")
        say("  orders even when every play is seen:")
        for r in multi[:12]:
            say(f"      {str(r.get('key'))[:58]:<58} "
                f"{sum(1 for lo in legs(r) if placed(lo))} legs")

    if B is not None:
        only_mail = sorted(B - set(k for k, r in seen.items() if any(placed(lo) for lo in legs(r))))
        only_ledg = sorted(set(k for k, r in seen.items() if any(placed(lo) for lo in legs(r))) - B)
        say("")
        say(f"  in the bot's mail but not placed in the ledger rows   {len(only_mail):4}")
        for k in only_mail[:10]:
            r = seen.get(k)
            st = [str((lo or {}).get("status")) for lo in legs(r)] if r else ["no row at all"]
            say(f"      {str(k)[:58]:<58} ledger says: {', '.join(st)}")
        say(f"  placed in the ledger rows but not in the bot's mail   {len(only_ledg):4}")
        for k in only_ledg[:10]:
            say(f"      {str(k)[:58]}")

    # ---- C: the books' own records ----
    say("")
    say("  C - what the books themselves recorded as the bot's:")
    try:
        st = tb.dec(json.load(open(TSTATE)))
    except Exception as e:
        say(f"      tracker state unreadable ({type(e).__name__}: {str(e)[:70]}) - C unavailable.")
        st = None
    if st:
        raw = (st or {}).get("bets")
        brows = list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        bot = [b for b in brows if str(b.get("source") or "") == "bot"]
        # Field names are PRINTED, not assumed - guessing them is what produced the last wrong zero.
        if bot:
            ks = collections.Counter()
            for b in bot[:400]:
                for k in b:
                    ks[k] += 1
            say(f"      {len(brows)} tracker row(s), {len(bot)} tagged source=='bot' (all time)")
            say(f"      fields on those rows: {', '.join(sorted(ks))[:150]}")
            datef = next((f for f in ("placed_at", "at", "matched_at", "date", "ts", "created_at")
                          if f in ks), None)
            if datef:
                cut = (now - timedelta(days=DAYS))
                inw = 0
                for b in bot:
                    v = str(b.get(datef) or "")
                    try:
                        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                        if d.tzinfo is None:
                            d = d.replace(tzinfo=timezone.utc)
                        if d >= cut:
                            inw += 1
                    except Exception:
                        continue
                say(f"      {inw} of them inside the last {DAYS} days, by '{datef}'")
                say("")
                say(f"      C = {inw} book-recorded bot bets vs A = {len(A)} by my count, "
                    f"A' = {len(Ap)} plays, A'' = {App} legs.")
            else:
                say(f"      no recognizable date field among them, so C cannot be windowed; "
                    f"the all-time figure above is not comparable to A.")
            say("      bot_match stores no key, so C cannot be joined play-by-play to A or B.")
        else:
            say("      no tracker row is tagged source=='bot' - the tagging, not the ledger, is")
            say("      then the thing to fix, and C says nothing about placements until it is.")
    say("")
    say("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
