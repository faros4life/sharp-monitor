#!/usr/bin/env python3
"""
Forensic recap, REAL MONEY part (Nov 2, 2026; Peter via Muse). PRIVATE: emailed to the Bets inbox, never written to
this public repo; the Actions log prints counts only. Read-only.

Site numbers per book (the same readers as the private tracker): ProphetX settled trades, Kalshi settlements,
Polymarket US settlement activities, Novig settled positions from the home snapshot (35 days, both wallets).
Hard Rock has no read path (balance figure only, from Peter's manual update).

Source split: bot (executor ledger keys / Novig auto-place wallet) vs Peter manual, with Peter's Nov 2 manual-record
rule applied: ntfy plays he placed by hand while testing them count in the ntfy stream, not his own record.
Periods (ET, by settle time): WEEK Mon Oct 26 - Sun Nov 1, OCTOBER, and everything the books return (overall).
"""
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import executor as ex
import tracker_build as tb

ET = ZoneInfo("America/New_York")
W0, W1 = datetime(2026, 10, 26, tzinfo=ET), datetime(2026, 11, 2, tzinfo=ET)
O0, O1 = datetime(2026, 10, 1, tzinfo=ET), datetime(2026, 11, 1, tzinfo=ET)


def money(x):
    return f"${x:,.2f}" if x >= 0 else f"-${-x:,.2f}"


def main():
    since = datetime(2026, 9, 1, tzinfo=ET)
    rows, notes = [], []
    for name, fn in (("ProphetX", tb.read_prophetx), ("Kalshi", lambda: tb.read_kalshi(since)),
                     ("Polymarket US", lambda: tb.read_pmus(since)), ("Novig", tb.read_novig)):
        try:
            _, s = fn()
            rows += s
        except (Exception, SystemExit) as e:
            notes.append(f"{name}: read failed ({type(e).__name__})")
    try:
        _, keys = tb.read_manual_and_bot()
    except (Exception, SystemExit):
        keys = set()
    out = []
    for b in rows:
        t = tb.tparse(b.get("settled"))
        if not t:
            continue
        t = t.astimezone(ET)
        src = b.get("source") or ("bot" if tb.bot_match(b, keys) else "Peter")
        if src == "bot":
            src = "ntfy (bot fill)"
        if src == "Peter" and tb.reclass(b):
            src = "ntfy (Peter manual, testing)"
        out.append({**b, "_t": t, "_src": src})

    def block(title, a, b0=None):
        sel = [r for r in out if (a is None or a <= r["_t"]) and (b0 is None or r["_t"] < b0)]
        L = [title]
        tot = 0.0
        groups = {}
        for r in sel:
            groups.setdefault((r["_src"], r["book"]), []).append(r)
        for (src, book), rs in sorted(groups.items(), key=lambda kv: -sum(x.get("profit") or 0 for x in kv[1])):
            w = sum(r["result"] == "W" for r in rs)
            l_ = sum(r["result"] == "L" for r in rs)
            p = sum(r["result"] == "P" for r in rs)
            pnl = sum(r.get("profit") or 0 for r in rs)
            stake = sum(r.get("stake") or 0 for r in rs)
            tot += pnl
            L.append(f"  {src:<30} {book:<14} {w}-{l_}-{p}  staked {money(stake)}  P&L {money(round(pnl, 2))}")
        bysrc = {}
        for r in sel:
            bysrc[r["_src"]] = bysrc.get(r["_src"], 0) + (r.get("profit") or 0)
        L.append("  -- by source: " + "; ".join(f"{k} {money(round(v, 2))}" for k, v in sorted(bysrc.items(), key=lambda kv: -kv[1])))
        L.append(f"  TOTAL (site numbers, 4 exchanges; Hard Rock not included) {money(round(tot, 2))}  ({len(sel)} settled bets)")
        return L + [""]

    body = ["FORENSIC RECAP - REAL MONEY (site numbers), built " + datetime.now(ET).strftime("%a %b %d %I:%M %p ET"), ""]
    body += block("WEEK Mon Oct 26 - Sun Nov 1 (by settle time ET)", W0, W1)
    body += block("OCTOBER (settled Oct 1 - Oct 31 ET)", O0, O1)
    body += block("OVERALL (everything the books return; Novig = last 35 days only)", None, None)
    body += ["Labels: stream = source as tagged (bot = executor ledger / Novig auto-place wallet; Peter = everything else);",
             "Peter's Nov 2 manual-record rule applied by date + team words (Bengals 10/25, Mavs-Pacers 10/23, Clippers 10/23,",
             "Heat 10/24, Rays 10/28, Magic 10/28); Hard Rock add-ons are not in exchange data. Street Value NFL/CFB and",
             "OddsJam parlays are inside 'Peter' here: Muse's tracker holds those tags.",
             "Hard Rock: no read path (balance only, from Peter's latest manual figure)."] + ([""] + notes if notes else [])
    ex.send("Bets RECAP: real money (site numbers)", "\n".join(body))
    print(f"Recap emailed: {len(out)} settled bets read; {len(notes)} read problems")   # counts only


if __name__ == "__main__":
    main()
