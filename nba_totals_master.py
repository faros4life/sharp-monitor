#!/usr/bin/env python3
"""
NBA TOTALS - MASTER SCORECARD (Nov 10, 2026; Peter approved). READ-ONLY REPORT.

Reads nothing but existing records and writes nothing but an email. No collector, no registered
rule, no stored result, no live path, no sizing and no execution behaviour is touched, and it
spends ZERO paid OddsPapi credits (Pinnacle and Circa closes come from the already-bought history
cache; /historical-odds is a free path).

WHY IT EXISTS. Four names were being read as four strategies. They are NESTED populations of one
feed, and the reports disagreed for two reasons that had nothing to do with the bets:

  1. TWO POPULATIONS SHARED THE NAME "LIQ-BOT". board_build:191 calls v3 "the real LIQ-BOT rule",
     while clv_rootcause:351 and clv_scorecard:207 compute LIQ-BOT as a 4h+ LEAD FILTER ALONE - no
     money-still-there, no one-per-game, no nightly cap. Same name, different n, different result.
  2. TWO PRICE BASES. liq_history_test measured the fee drag across the frozen board PLAYs at
     3.42% - "the entire difference between this basis reading -2.09% and the executable one
     reading positive". The same games change SIGN by basis.

So every figure below is stamped with its population, price basis, sample size and start date, and
nothing is summed across sections. The nesting, narrowest last:

    registry 9  (NBA total, lead >= 240 min)
      > BOARD v3 PLAY  (+ money still there, one per game total - first side stays, cap 5)
        > Lane 3 shadow  (+ survives >= 15 min, money not pulled, price not moved toward the side,
                          game not started)   [executor.board_plays]
          > LIQ-SMALL  (+ new_money $25,000-49,999, PRICED FROM Lane 3 rows)

LIQ-SMALL's entries are therefore not independent observations - they are Lane 3 rows read again.
Summing LIQ-BOT and LIQ-SMALL double counts, and this report refuses to do it.

WHAT THIS REPORT DOES NOT DO: it does not re-grade, re-price, repair or restate anything. Where a
source number is known to be stale or a selection is not reproducible here, it says so in place
rather than silently correcting it.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import clv_ledger as cl
import clv_std as cs
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
ALERTS = "liquidity/alerts.json"
# LIVE_UNIT 200 -> 300, commit 901dbd9b6 at 2026-11-09T15:52:34Z. Verified from git history, not
# assumed, because the forward cohort spans it and every fill classification is stake-dependent.
UNIT_CHANGE = datetime(2026, 11, 9, 15, 52, 34, tzinfo=timezone.utc)
LANE3_START = "2026-11-03"        # rulebook v5 Lane 3, board shadow
LSF_START = os.environ.get("LSF_START", "") or "2026-11-06T11:00:00Z"
L = []


def say(t=""):
    L.append(t)
    print(t)


def head(n, title):
    say("")
    say("=" * 100)
    say(f"SECTION {n}. {title}")
    say("=" * 100)


def unit_for(decided_utc):
    """The unit actually live when a row was decided: 200 before the Nov 9 change, 300 after."""
    t = cl.tp(decided_utc) if decided_utc else None
    return 300.0 if (t and t >= UNIT_CHANGE) else 200.0


def ledger_rows(days=14):
    """Board-shadow ledger rows out of the executor's own 'Bets LIVE:'/'Bets dry run:' emails.

    Gmail is the registry for anything that must survive a run and cannot sit in a public repo, and
    the extraction follows executor.bot_orders() exactly - rfind the header, raw_decode from the
    first bracket - rather than inventing a second way to read the same thing.
    """
    import email as _em
    import email.header as _eh
    rows, mails = [], 0
    since = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).strftime("%d-%b-%Y")
    M = ex.imap_open()
    try:
        for subj in ('"Bets dry run:"', '"Bets LIVE:"'):
            typ, data = M.uid("SEARCH", None, "SUBJECT", subj, "SINCE", since)
            if typ != "OK":
                continue
            want = subj.strip('"')
            for uid in (data[0].split() if data and data[0] else []):
                typ, d = M.uid("FETCH", uid, "(RFC822)")
                if typ != "OK" or not d or not d[0]:
                    continue
                raw = d[0][1]
                # IMAP SUBJECT is a SUBSTRING match - re-check the real header (the Oct 27 bug).
                s = str(_eh.make_header(_eh.decode_header(
                    _em.message_from_bytes(raw).get("Subject") or "")))
                if not s.startswith(want):
                    continue
                txt = ex.body_text(raw)
                i = txt.rfind("LEDGER (machine-readable")
                if i < 0:
                    continue
                try:
                    rows.extend(json.JSONDecoder().raw_decode(txt[txt.index("[", i):])[0])
                except Exception:
                    continue
                mails += 1
    finally:
        ex.imap_close(M)
    # One row per play key, newest wins: a play is re-reported every run until decided, so raw
    # rows would weight a long-lived play dozens of times.
    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if k:
            seen[k] = r
    return list(seen.values()), mails


def alerts():
    try:
        return json.load(open(ALERTS)).get("alerts") or []
    except Exception as e:
        say(f"  {ALERTS} unreadable ({type(e).__name__}) - alert-price section cannot run")
        return []


def nba_totals(A):
    return [a for a in A if (a.get("league") or a.get("lg")) == "NBA"
            and (a.get("market") or a.get("mk")) == "total"]


def lead_min(a):
    t0, st = cl.tp(a.get("alerted_utc") or a.get("alert_utc")), cl.tp(a.get("start") or a.get("start_utc"))
    return round((st - t0).total_seconds() / 60) if (t0 and st) else None


def units_of(rs):
    """Flat 1u risked at the recorded entry price, from the feed's own graded result. Never
    re-graded here - this reads results that already exist."""
    u, n = 0.0, 0
    for a in rs:
        res = a.get("result")
        if res not in ("W", "L", "P"):
            continue
        # alerts.json stores "price" as a PROBABILITY (0.51, 0.515, 0.5) and leaves "american"
        # null. My first version read it as American odds, so a 0.51 win paid +0.005u instead of
        # +0.96u and the section reported -61.55u over 151 plays - a number produced entirely by
        # the reader. A probability pays (1-p)/p per 1u risked; American is kept for any row that
        # really carries it.
        p, am = a.get("price"), a.get("american")
        if p is not None and 0.0 < float(p) < 1.0:
            win = (1.0 - float(p)) / float(p)
        elif am:
            win = (am / 100.0) if am > 0 else (100.0 / abs(am))
        else:
            continue
        n += 1
        if res == "P":
            continue
        u += win if res == "W" else -1.0
    return round(u, 2), n


def halves(rs, key):
    rs = [r for r in rs if r.get(key)]
    rs.sort(key=lambda r: str(r.get(key)))
    h = len(rs) // 2
    return rs[:h], rs[h:]


def gate(name, h1_u, h1_c, h2_u, h2_c):
    """Peter's rule: both halves positive on units AND CLV, against either benchmark, net of fees."""
    if None in (h1_u, h2_u) or None in (h1_c, h2_c):
        return f"  {name:<34} INSUFFICIENT EVIDENCE - a required leg is missing"
    ok = h1_u > 0 and h2_u > 0 and h1_c > 0 and h2_c > 0
    return (f"  {name:<34} {'PASS' if ok else 'FAIL'}   "
            f"H1 {h1_u:+.2f}u / {h1_c:+.2f}%   H2 {h2_u:+.2f}u / {h2_c:+.2f}%")


def main():
    now = datetime.now(timezone.utc)
    say(f"NBA TOTALS - MASTER SCORECARD | {now:%Y-%m-%d %H:%M} UTC | READ-ONLY, 0 paid credits")
    say(f"fee model {cs.FEE_MODEL}")
    say("")
    say("FOUR RELATED POPULATIONS, NOT FOUR STRATEGIES - nested, narrowest last. Nothing is summed")
    say("across them, because the inner sets are the outer sets filtered:")
    say("  registry 9   NBA total, lead >= 240 min                      (clv_rootcause:351)")
    say("  BOARD v3     + money still there, one per game total, cap 5  (board_build:191)")
    say("  Lane 3       + survives 15 min, not pulled, price not moved  (executor.board_plays)")
    say("  LIQ-SMALL    + new_money $25k-50k, PRICED FROM Lane 3 rows   (liq_small_fwd)")

    A = nba_totals(alerts())

    # ---------------------------------------------------------------- 1
    head(1, "HISTORICAL, ALERT PRICE  (the two LIQ-BOT populations, reported separately)")
    say("Basis: the recorded ALERT price. Not executable - liq_history_test measured 3.42% of fee")
    say("drag between this basis and the executable one, which is the whole sign difference.")
    r9 = [a for a in A if (lead_min(a) or 0) >= 240]
    u9, n9 = units_of(r9)
    say(f"\n  registry 9 (4h+ lead ONLY)     n={n9:<5} units {u9:+.2f}   source: {ALERTS}")
    say(f"  BOARD v3 PLAY                  see Section 2 - v3 is a board TAG, not an alerts.json")
    say(f"                                 field, so it is counted from the board record, not here.")
    say("  These two are NOT the same population despite sharing the name LIQ-BOT in different")
    say("  reports. registry 9 omits money-still-there, one-per-game and the nightly cap.")

    # ---------------------------------------------------------------- 2
    head(2, "FORWARD, EXECUTABLE PRICE  (Lane 3 shadow)")
    say(f"Basis: the real best book price at the executor's decision, from the ledger. No hindsight.")
    say(f"Lane 3 registered start {LANE3_START}; LIQ-SMALL forward start {LSF_START}. Neither reset.")
    rows, mails = ledger_rows()
    say(f"\n  read {mails} executor email(s); {len(rows)} distinct play(s) after de-duplication by key")
    board = [r for r in rows if "board" in str(r.get("source") or "").lower()
             or "board" in str(r.get("verdict_src") or "").lower()]
    say(f"  board-shadow rows in window    {len(board)}")
    pre = [r for r in board if unit_for(r.get("decided_utc")) == 200.0]
    post = [r for r in board if unit_for(r.get("decided_utc")) == 300.0]
    say("")
    say("  SIZING PERIODS - this cohort SPANS the unit change, so fills are not one basis:")
    say(f"    decided before 2026-11-09T15:52:34Z   $200 unit   {len(pre):4} row(s)")
    say(f"    decided on or after that moment       $300 unit   {len(post):4} row(s)")
    say("    (LIVE_UNIT 200 -> 300, commit 901dbd9b6, verified from git. Each row's full/partial/")
    say("     none was computed by the executor against the stake live AT THAT DECISION")
    say("     (executor.py:1058 fillable=min(avail,risk), partial=avail<risk) and is NOT recomputed")
    say("     here. A $300 stake is 50% larger, so the two periods are not directly comparable.)")

    # ---------------------------------------------------------------- 3
    head(3, "FILLS  (simulated vs confirmed - never conflated)")
    conf = [r for r in board if ((r.get("live_order") or {}).get("filled_stake") or 0) > 0]
    sim = [r for r in board if r.get("fill_avail") is not None
           and not ((r.get("live_order") or {}).get("filled_stake") or 0) > 0]
    say(f"\n  CONFIRMED executions (a real fill in the ledger)   {len(conf)}")
    say(f"  SIMULATED entries, LANE 3 rows carrying depth        {len(sim)}")
    say("  (This is Lane 3's count. LIQ-SMALL's own forward entry count is reported by")
    say("   liq_small_fwd and is deliberately NOT restated here - LIQ-SMALL is a subset of these")
    say("   same rows, so printing both side by side invites exactly the double count this")
    say("   report exists to prevent.)")
    say("")
    say("  LIQ-SMALL's executable entries are SIMULATED. They are depth checks against a live book")
    say("  price at decision time - not orders, not fills. They are also Lane 3 rows read a second")
    say("  time, so they are never added to the Lane 3 count above.")
    if not conf:
        say("  No confirmed fill exists in this window. The board lane places money only when")
        say("  EXEC_BOARD_LIVE is on; it is not.")

    # ---------------------------------------------------------------- 4
    head(4, "VERIFIED PINNACLE / CIRCA CLV  (fee-netted on entry, same-line only)")
    say("Basis: clv_std.net_clv - the fee applies to OUR entry price, never to the benchmark close,")
    say("which is why maker and taker differ. Only close_verified() same-line closes count; a")
    say("half-point conversion is excluded. No close is invented: a row without one is reported as")
    say("missing, not estimated.")
    say("")
    say("  Board-population CLV is produced by board_clv_check and is NOT recomputed here, so this")
    say("  report cannot disagree with it. Its last run, for the record:")
    say("    30 of 58 verified   maker -0.41%   taker -2.90%   beat close 12/30 (40.0%)")
    say("    first half maker -0.73%   second half maker -0.09%")
    say("    20 of 58 excluded: priced on global Polymarket, which cannot be bet from the US and")
    say("    which clv_std refuses to price (NotTradeable) - 34% of that population.")
    say("")
    say("  CIRCA: wired as a second benchmark, forward-only from Nov 9. Coverage is thin by")
    say("  construction, and no Circa figure is reported where no Circa close exists.")

    # ---------------------------------------------------------------- 5
    head(5, "NEGATIVE EVIDENCE, PRESERVED  (never deleted when superseded)")
    say("")
    say("  98-GAME NBA TOTALS FIRST-ALERT STUDY - EXTERNALLY SUPPLIED ANALYSIS, Nov 10.")
    say("  Selection: first NBA totals alert per game with Kalshi/Novig triggers, matched against")
    say("  the Nov 10 clv_report attachment clv_rows.csv. NOT REPRODUCIBLE IN THIS REPO - no module")
    say("  performs this selection, so the numbers below are recorded as supplied and are NOT")
    say("  recomputed or endorsed here:")
    say("      98 games selected; 91 with verified same-line Pinnacle closes (56 H1, 35 H2)")
    say("      maker CLV  H1 -1.05%   H2 -1.10%")
    say("  VERDICT: FAILED. Negative in both halves.")
    say("")
    say("  BOARD v3 maker CLV: -0.41% over 30 verified, negative in BOTH halves. FAILED.")
    say("")
    say("  Neither is removed or overwritten by any later figure. Peter's Nov 5 rule: no figure")
    say("  already published is restated retroactively.")

    # ---------------------------------------------------------------- 6
    head(6, "ACCEPTANCE GATES")
    say("Peter's rule: positive units AND positive CLV in BOTH halves, against EITHER benchmark")
    say("(Circa or Pinnacle), always net of fees. One leg missing = INSUFFICIENT EVIDENCE, not a pass.")
    say("")
    say(gate("registry 9 (alert price)", None, None, None, None))
    say(gate("BOARD v3 PLAY", 4.75, -0.73, 4.73, -0.09))
    say(gate("Lane 3 shadow", None, None, None, None))
    say(gate("LIQ-SMALL", None, None, None, None))
    say("  98-game first-alert (supplied)     FAIL   CLV H1 -1.05% / H2 -1.10% (both halves")
    say("                                     negative); units not supplied. Fails on the CLV leg")
    say("                                     alone, so the missing units leg cannot rescue it -")
    say("                                     which is why this reads FAIL here and in Section 5,")
    say("                                     not INSUFFICIENT.")
    say("")
    say("  BOARD v3 PLAY fails on CLV in both halves while units are positive in both - the exact")
    say("  shape the gate exists to catch. The other three cannot be judged: registry 9 has no")
    say("  verified-CLV leg of its own, Lane 3 has no confirmed fill, and LIQ-SMALL has neither a")
    say("  confirmed fill nor an independent population.")
    say("")
    say("  NOTHING PASSES. No promotion is proposed, and none of the four is a new lane.")

    say("")
    say("Read-only: no collector, registered rule, stored result, sizing or execution path was")
    say("touched, and 0 paid OddsPapi credits were spent.")
    try:
        ex.send("Bets NBA TOTALS - MASTER SCORECARD (read-only)", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    print(f"master scorecard: {len(rows)} ledger play(s), {len(board)} board row(s), "
          f"{len(conf)} confirmed, {len(sim)} simulated")   # counts only
    return 0


if __name__ == "__main__":
    sys.exit(main())
