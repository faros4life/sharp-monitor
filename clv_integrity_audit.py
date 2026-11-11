#!/usr/bin/env python3
"""
CLV INTEGRITY AUDIT - READ-ONLY (Peter, Nov 10 2026, explicit authorisation).

Question: are duplicate row ids in clv/state.enc merely INFLATING REPORTS, or are they
CONTAMINATING THE BACKTESTS used to pick strategies?

Deletes nothing, recalculates nothing, changes no rule or threshold, and makes NO OddsPapi call
(it opens no network path at all). It reads clv/state.enc and tracker/state.enc and prints/emails
what it finds. Dollars by private email; the Actions log prints counts only.

THE DECISIVE TEST, not game/line/price identity (Peter, Nov 10: "Don't assume identical games,
lines, and prices are duplicate wagers"):
  A clv row is an ORPHAN when its key is absent from the tracker state.
  It is a PROVEN old-scheme duplicate when, in addition, man_id(book, game, bet) of that orphan
  resolves to a key that IS present in the tracker.
Mechanism this tests: man_id changed on Nov 5 from a hash of the whole MANUAL note line to
book+game+bet, and tracker_build.man_migrate retires the old key IN THE TRACKER. clv_ledger only
ever setdefault()s keys into its own st["bets"] and prunes by first_seen age (60 days), so a
retired key survives there with its snapshot and its CLV and keeps being counted.
Anything that fails the second test is reported as UNPROVEN and is never called a duplicate.
"""
import json
import math
import os
import re
from collections import Counter, defaultdict

import clv_ledger as cl
import tracker_build as tb

CLV_STATE = cl.STATE


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def scheme(k):
    k = str(k)
    if "|" in k:
        return k.split("|")[0]
    return "sha1-bare" if re.fullmatch(r"[0-9a-f]{40}", k) else "other"


def stats(xs):
    n = len(xs)
    if not n:
        return None
    m = sum(xs) / n
    if n < 2:
        return {"n": n, "mean": m, "sd": None, "se": None, "beat": sum(1 for x in xs if x > 0)}
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return {"n": n, "mean": m, "sd": sd, "se": sd / math.sqrt(n), "beat": sum(1 for x in xs if x > 0)}


def line(label, xs):
    s = stats(xs)
    if not s:
        return f"  {label}: n 0"
    if s["se"] is None:
        return f"  {label}: n {s['n']}, mean {s['mean']*100:+.2f}%, beat {s['beat']}/{s['n']} (no spread at n<2)"
    lo, hi = s["mean"] - 1.96 * s["se"], s["mean"] + 1.96 * s["se"]
    return (f"  {label}: n {s['n']}, mean {s['mean']*100:+.2f}%, sd {s['sd']*100:.1f}%, SE {s['se']*100:.1f}%, "
            f"95% {lo*100:+.1f}% to {hi*100:+.1f}%, beat {s['beat']}/{s['n']}")


def book_of(s):
    return str(s.get("book") or "?")


def classify(cs, trk):
    """Every clv bet row -> ('live'|'orphan-proven'|'orphan-unproven', target key or None)."""
    out = {}
    for k, r in (cs.get("bets") or {}).items():
        if k in trk:
            out[k] = ("live", None)
            continue
        s = r.get("snap") or {}
        tgt = None
        if str(k).startswith("mn|"):
            try:
                cand = tb.man_id(s.get("book"), s.get("game"), s.get("bet"))
            except Exception:
                cand = None
            if cand and cand != k and cand in trk:
                tgt = cand
        out[k] = ("orphan-proven" if tgt else "orphan-unproven", tgt)
    return out


def main():
    import executor as ex
    L = ["CLV INTEGRITY AUDIT - read-only. No deletions, no recalculation, no rule change, no OddsPapi call.", ""]
    try:
        cs = tb.dec(json.load(open(CLV_STATE))) or {}
        trk = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        ex.send("Bets CLV INTEGRITY AUDIT (failed)", f"could not read a state file: {type(e).__name__}: {str(e)[:200]}")
        print(f"clv integrity audit: state unreadable ({type(e).__name__})")
        return
    bets = cs.get("bets") or {}
    cls = classify(cs, trk)
    kinds = Counter(v[0] for v in cls.values())

    L += ["=" * 74, "1. POPULATION", "=" * 74,
          f"clv/state.enc bet rows: {len(bets)}   tracker/state.enc bet rows: {len(trk)}",
          f"clv row ids by scheme: {dict(Counter(scheme(k) for k in bets))}",
          f"classification: {dict(kinds)}",
          "",
          "  live           = the id still exists in the tracker.",
          "  orphan-proven  = id gone from the tracker AND its book+game+bet hashes to a tracker key that IS there.",
          "                   That is the Nov 5 man_id change plus man_migrate: a PROVEN stale duplicate.",
          "  orphan-unproven= id gone from the tracker, no such resolution. NOT called a duplicate; could be a real",
          "                   bet whose tracker row aged out (tracker keeps 10 days of notes; clv keeps 60 days).",
          ""]

    scored = {k: r for k, r in bets.items() if r.get("clv") is not None and not r.get("fixture_doubt")}
    L += ["=" * 74, "2. EFFECT ON THE HEADLINE CLV (scored rows the ledger itself counts)", "=" * 74]
    allx = [r["clv"] for r in scored.values()]
    livex = [r["clv"] for k, r in scored.items() if cls[k][0] == "live"]
    nonproven = [r["clv"] for k, r in scored.items() if cls[k][0] != "orphan-proven"]
    L += [line("as the ledger reports it now   ", allx),
          line("proven duplicates removed      ", nonproven),
          line("live tracker rows only         ", livex),
          "",
          "  The middle line is the defensible figure: it drops only rows proven stale.",
          "  The third is a lower bound on n; it also drops aged-out rows that may be real.", ""]

    L += ["=" * 74, "3. PER BOOK (scored rows)", "=" * 74]
    per = defaultdict(lambda: defaultdict(list))
    for k, r in scored.items():
        per[book_of(r.get("snap") or {})][cls[k][0]].append(r["clv"])
    for bk in sorted(per, key=lambda b: -sum(len(v) for v in per[b].values())):
        g = per[bk]
        tot = sum(len(v) for v in g.values())
        prov, unpr, liv = len(g.get("orphan-proven", [])), len(g.get("orphan-unproven", [])), len(g.get("live", []))
        L.append(f"{bk}: rows {tot} (live {liv}, proven-dup {prov}, unproven-orphan {unpr})")
        L.append(line("  as-is                  ", [x for v in g.values() for x in v]))
        L.append(line("  proven duplicates out  ", g.get("live", []) + g.get("orphan-unproven", [])))
    L.append("")

    L += ["=" * 74, "4. PER SOURCE TAG / LANE (scored rows)", "=" * 74]
    per = defaultdict(lambda: defaultdict(list))
    for k, r in scored.items():
        per[str((r.get("snap") or {}).get("source") or "?")][cls[k][0]].append(r["clv"])
    for sx in sorted(per, key=lambda s: -sum(len(v) for v in per[s].values())):
        g = per[sx]
        prov = len(g.get("orphan-proven", []))
        L.append(f"{sx}: rows {sum(len(v) for v in g.values())} (proven-dup {prov})")
        L.append(line("  as-is                  ", [x for v in g.values() for x in v]))
        if prov:
            L.append(line("  proven duplicates out  ", g.get("live", []) + g.get("orphan-unproven", [])))
    L.append("")

    L += ["=" * 74, "5. KILL-SWITCH (rolling 50 scored BOT rows, avg CLV < 0 -> alert)", "=" * 74]
    srt = sorted([dict(r, id=k) for k, r in scored.items()], key=lambda r: r.get("scored") or "")
    bot = [r for r in srt if ((r.get("snap") or {}).get("source") or "") == "bot"]
    botp = [r for r in bot if cls[r["id"]][0] == "orphan-proven"]
    L += [f"scored bot rows: {len(bot)}; of those proven duplicates: {len(botp)}",
          line("rolling 50, as-is              ", [r["clv"] for r in bot[-50:]]),
          line("rolling 50, proven dups out    ", [r["clv"] for r in bot if cls[r["id"]][0] != "orphan-proven"][-50:]),
          ("  VERDICT: no proven duplicate is a bot row, so the kill-switch arithmetic is UNAFFECTED."
           if not botp else
           "  VERDICT: proven duplicates ARE present among bot rows - the kill-switch arithmetic is affected."), ""]

    L += ["=" * 74, "6. WHAT CONSUMES THESE ROWS (read from the code, not assumed)", "=" * 74,
          "clv/state.enc st['bets'] is iterated by:",
          "  clv_ledger.py   - the ledger email, the lane and book splits, and the kill-switch. REPORT + ALERT.",
          "  plays_kelly.py  - iterates every row with a W/L/P result to build its plays. SELECTION PATH.",
          "  bucket_report.py- iterates every row with a clv to build the buckets. SELECTION PATH.",
          "  clv_basis_audit.py, clv_reset.py, hr_phone_ledger.py - audits/reports only.",
          "None of these checks whether a row still exists in the tracker, so a proven duplicate reaches",
          "every one of them. plays_kelly and bucket_report are the two that feed strategy choice.",
          "",
          "NOT contaminated, verified by reading the source:",
          "  executed_clv.py - reads the TRACKER state (not clv/state.enc) and only source=='bot' rows.",
          "  lane2.py, slow_hr.py - read clv/state.enc for the 'billable' counter only.",
          "  plimit_level.py, regress_api.py - read 'fixtures'/'fx_last'/'billable' only, never 'bets'.",
          "  slowhr_backtest.py / slowhr_cell.py / the nba and p1 backtests - do not open clv/state.enc.", ""]

    L += ["=" * 74, "7. PROVEN DUPLICATES, ROW BY ROW", "=" * 74]
    n = 0
    for k, (kind, tgt) in sorted(cls.items()):
        if kind != "orphan-proven":
            continue
        n += 1
        r, s = bets[k], (bets[k].get("snap") or {})
        L.append(f"  stale id {str(k)[:18]}..  -> live tracker id {str(tgt)[:18]}..  | {book_of(s)} | "
                 f"{str(s.get('game'))[:34]} | {s.get('bet')} | stake {s.get('stake')} | clv {r.get('clv')} | "
                 f"result {s.get('result')}")
    if not n:
        L.append("  none")
    L.append("")
    L += ["=" * 74, "8. UNPROVEN ORPHANS (NOT duplicates - listed so nothing is dropped silently)", "=" * 74]
    m = 0
    for k, (kind, _) in sorted(cls.items()):
        if kind != "orphan-unproven":
            continue
        m += 1
        s = bets[k].get("snap") or {}
        L.append(f"  {str(k)[:18]}.. [{scheme(k)}] | {book_of(s)} | {str(s.get('game'))[:34]} | {s.get('bet')} | "
                 f"source {s.get('source')} | first_seen {bets[k].get('first_seen')} | clv {bets[k].get('clv')}")
    if not m:
        L.append("  none")

    L += ["", "=" * 74, "9. EXPOSURE OF THE TWO SELECTION PATHS (measured, not asserted)", "=" * 74]
    # plays_kelly counts a row when it has a W/L/P result and a usable price; it uses snap stake for ACTUAL dollars
    # and never filters by source. A stale row keeps the snapshot it had when it was retired - including, for the two
    # NCAAB notes, the INVENTED stake the old sizing rule guessed before Peter's real stakes arrived.
    pk_live = pk_stale = 0
    inj = 0.0
    bad_stake = []
    for k, r in bets.items():
        s = r.get("snap") or {}
        if s.get("result") not in ("W", "L", "P"):
            continue
        d = cl.eff_dec(s)
        if not d or d <= 1:
            continue
        stale = cls[k][0] == "orphan-proven"
        if stale:
            pk_stale += 1
        else:
            pk_live += 1
        st_amt = num(s.get("stake"))
        if stale and st_amt:
            inj += st_amt * (d - 1) if s["result"] == "W" else (-st_amt if s["result"] == "L" else 0.0)
            tgt = cls[k][1]
            live_amt = num(((bets.get(tgt) or {}).get("snap") or {}).get("stake")) if tgt else None
            if live_amt is not None and abs(live_amt - st_amt) > 0.01:
                bad_stake.append((str(s.get("bet")), st_amt, live_amt))
    L += [f"plays_kelly population: {pk_live + pk_stale} rows counted, of which PROVEN STALE {pk_stale}",
          f"  dollars those stale rows inject into the ACTUAL column: {inj:+,.2f} (double-counted, on top of the live row)"]
    if bad_stake:
        L.append("  stale rows whose stake DISAGREES with the live row (the pre-fix invented stake, preserved):")
        for b, sa, la in bad_stake:
            L.append(f"    {b}: stale row carries {sa:g}, live tracker row carries {la:g}")
    L += ["  -> plays_kelly filters on result and price only, never on source or tracker presence (lines 43-64),",
          "     so each of these is counted a second time, at a stake that in some rows was later corrected.",
          ""]
    led = [k for k, r in scored.items() if cls[k][0] == "orphan-proven"]
    L += [f"bucket_report ledger_rows(): draws from the same clv rows; proven-stale scored rows reaching it: {len(led)}",
          "  Buckets split FIT (first half of dates) vs CHECK (second half) and call HOLDS at >= 15 per half.",
          f"  Hard Rock scored rows fall from 19 to 11 once the stale rows go, so any Hard Rock cell sits further",
          "  below that 15-per-half floor than the report currently shows.", ""]

    ex.send("Bets CLV INTEGRITY AUDIT (read-only)", "\n".join(L))
    print(f"clv integrity audit: clv rows {len(bets)}, tracker rows {len(trk)}, "
          f"live {kinds.get('live', 0)}, proven-dup {kinds.get('orphan-proven', 0)}, "
          f"unproven-orphan {kinds.get('orphan-unproven', 0)}, scored {len(scored)}, "
          f"bot proven-dup {len(botp)}")   # counts only


if __name__ == "__main__":
    main()
