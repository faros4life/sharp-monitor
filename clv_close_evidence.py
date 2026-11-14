#!/usr/bin/env python3
"""
CLOSE EVIDENCE (Peter, Nov 13 2026). READ-ONLY.

For named selections, print the WORKING of the CLV rather than the figure alone: the fixture it
resolved to, the exact Pinnacle line, the last valid pre-start tick on BOTH sides with its
timestamp and limit, the no-vig probability, the bet's own after-fee price, and the CLV those
produce. Peter: "Report the precise closing timestamp, two-sided odds, no-vig probability and
calculated CLV. If the exact same-line closing quote is unavailable, show the verified closing
main line separately. Do not invent a percentage."

READ-ONLY and CACHE-ONLY. No OddsPapi call: Pinnacle history comes from the hcache files already
on disk, and clv/markets.json is read directly rather than through load_markets(), which can
bill. Nothing is written. A selection with no cached history, no fixture or no same-line quote
says so - the main line is reported separately and NEVER converted into a headline figure.

MATCHING is by substring against league + game + bet, given in WANT below or via SELECT (one
pattern per line). Every row that matches is printed, so a selection that still has several rows
is visible as several rows rather than silently collapsed.
"""
import gzip
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
MKFILE = "clv/markets.json"
WANT = [p.strip() for p in (os.environ.get("SELECT") or
        "louisiana|48.5\ndallas|225.5\ncharlotte|214.5\ntoronto|223.5").split("\n") if p.strip()]
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def am(dec):
    return round(-100 / (dec - 1)) if dec < 2 else round(100 * (dec - 1))


def cached(fid, book="pinnacle"):
    p = os.path.join(HC, f"{fid}__{book}.json.gz")
    if not os.path.exists(p):
        return None
    try:
        with gzip.open(p, "rt") as fh:
            return {"bookmakers": {book: json.load(fh)}}
    except Exception:
        return None


def matches(s, pat):
    hay = " ".join(str(s.get(k) or "") for k in ("league", "game", "bet")).lower()
    return all(part in hay for part in pat.lower().split("|"))


def ticks_at(pm, mid, outs, typ, start):
    """{side: (decimal, tick time, limit)} for the two sides of one market."""
    tw = cl.two_way(pm, mid, start)
    nm = {v: k for k, v in outs.items()}
    a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
    if a in tw and b in tw:
        return {"A": tw[a], "B": tw[b]}, (a, b)
    return None, (a, b)


def report_row(rid, rec, st, mkmap):
    s = rec.get("snap") or {}
    say("")
    say(f"  ROW {rid}")
    say(f"    {s.get('league')} | {s.get('game')} | {s.get('bet')} | book {s.get('book')} | "
        f"source {s.get('source')}")
    shown = "NONE" if rec.get("clv") is None else "{:+.2f}%".format(100 * rec["clv"])
    say(f"    result {s.get('result') or 'UNSETTLED'}   stored CLV {shown}   "
        f"how {rec.get('how') or '-'}   tries {rec.get('tries')}   done {bool(rec.get('done'))}")
    if rec.get("clv") is None and rec.get("why"):
        say(f"    stored reason: {rec['why']}")
    fid = rec.get("fixture")
    if not fid:
        try:
            fid = cl.find_fixture(st, s)
        except Exception:
            fid = None
        if fid:
            say(f"    fixture (resolves now, not stored): {fid}")
    if not fid:
        say("    NO FIXTURE - no close can be quoted. Unknown stays unknown.")
        return
    f = (st.get("fixtures") or {}).get(fid) or {}
    start = cl.tp(f.get("start")) or cl.tp(s.get("game_start"))
    say(f"    fixture {fid}  {f.get('p1')} v {f.get('p2')}")
    say(f"    start   {start.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ} "
        f"({start.astimezone(ET):%Y-%m-%d %H:%M} ET)" if start else "    start UNKNOWN")
    h = cached(fid)
    if h is None:
        say(f"    NO CACHED PINNACLE HISTORY for {fid} - cannot quote a close without a fetch.")
        return
    pm = cl.book_markets(h, "pinnacle")
    pz = cl.parsed(s)
    if not pz or not start:
        say("    bet text did not parse, or no start time - no close quoted.")
        return
    sid = cl.SPORT.get(s.get("league"))
    if sid is None:
        say(f"    league {s.get('league')} has no OddsPapi sport id - out of scope, not a gap.")
        return
    typ = "spreads" if pz[0] == "spread" else "totals" if pz[0] == "total" else "ml"
    if typ == "ml":
        say("    moneyline: no line to match (reported as EQUIVALENT elsewhere)")
        return
    want = pz[2]
    side_is_a = (pz[1] == "OVER") if typ == "totals" else None
    if typ == "spreads":
        sd = cl.which_team(f, pz[1])
        if not sd:
            say("    held team not matched to either side of the fixture - no close quoted.")
            return
        if pz[3]:
            sd, want = ("2" if sd == "1" else "1"), -want
        want = want if sd == "1" else -want
        side_is_a = (sd == "1")
    rows = []
    for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
        if sp != sid or t != typ or mid not in pm:
            continue
        tk, _ = ticks_at(pm, mid, outs, typ, start)
        if tk:
            rows.append((hcap, tk, mid))
    if not rows:
        say(f"    no two-sided Pinnacle {typ} ticks before start in the cache - no close quoted.")
        return
    exact = [r for r in rows if abs(r[0] - want) < 1e-9]
    dec = cl.eff_dec(s)

    def quote(label, hcap, tk):
        (da, ta, la), (db, tb_, lb) = tk["A"], tk["B"]
        age = (start - min(ta, tb_)).total_seconds() / 60
        p_a = cl.novig_p(da, db)
        p_held = p_a if side_is_a else 1 - p_a
        nameA, nameB = ("team 1", "team 2") if typ == "spreads" else ("Over", "Under")
        say(f"    {label} line {hcap:g}")
        say(f"      {nameA:<7} {da:.4f} dec ({am(da):+d})  last tick "
            f"{ta.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ}  limit {la:g}")
        say(f"      {nameB:<7} {db:.4f} dec ({am(db):+d})  last tick "
            f"{tb_.astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ}  limit {lb:g}")
        say(f"      closing tick is {age:.0f} min before start "
            f"(freshness limit {cl.FRESH_MIN / 60:.0f}h: {'PASS' if age <= cl.FRESH_MIN else 'FAIL'})")
        say(f"      no-vig P({nameA}) {p_a:.4f}   P(held side) {p_held:.4f} "
            f"= {tb.p_to_american(p_held):+d}")
        if dec:
            say(f"      bet after-fee price {dec:.4f} dec ({am(dec):+d}) from "
                f"stake/to_pay or the stored price")
            say(f"      CLV = {p_held:.4f} x {dec:.4f} - 1 = {100 * (p_held * dec - 1):+.2f}%")
        else:
            say("      the row carries NO after-fee price, so no CLV can be computed from it.")
        return p_held

    if exact:
        say("    SAME-LINE CLOSE AVAILABLE (certifiable):")
        quote("EXACT own", exact[0][0], exact[0][1])
    else:
        say(f"    NO SAME-LINE CLOSE: Pinnacle did not hang {want:g} with two sides before start.")
        say("    The verified closing MAIN line is shown separately below. It is NOT this bet's")
        say("    CLV and is not converted into one here.")
        main = max(rows, key=lambda r: (min(r[1]["A"][2], r[1]["B"][2]),
                                        -abs(cl.novig_p(r[1]["A"][0], r[1]["B"][0]) - 0.5)))
        quote("VERIFIED MAIN (reference only)", main[0], main[1])
        say(f"    lines Pinnacle did hang: {', '.join(f'{r[0]:g}' for r in sorted(rows, key=lambda r: r[0]))}")


def main():
    now = datetime.now(timezone.utc)
    say("CLOSE EVIDENCE - READ-ONLY, cache only, no OddsPapi call, nothing written")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say(f"selections requested: {WANT}")
    say("=" * 100)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {MKFILE} unreadable ({type(e).__name__})")
        return 1
    bets = st.get("bets") or {}
    say(f"  ledger rows {len(bets)} | market ids {len(mkmap)} | "
        f"hcache files {len(os.listdir(HC)) if os.path.isdir(HC) else 0}")
    for pat in WANT:
        say("")
        say("=" * 100)
        say(f"SELECTION PATTERN: {pat}")
        say("=" * 100)
        hit = [(k, r) for k, r in bets.items() if matches(r.get("snap") or {}, pat)]
        if not hit:
            say("  no ledger row matches this pattern")
            continue
        say(f"  {len(hit)} matching ledger row(s)")
        for k, r in sorted(hit):
            report_row(k, r, st, mkmap)
    say("")
    say("=" * 100)
    say("END. Nothing fetched, nothing written, no percentage invented.")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("CLV close evidence (read-only)", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
