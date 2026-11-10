#!/usr/bin/env python3
"""HARD ROCK MANUAL P&L PULL - read-only (Peter, Nov 10 2026: "my ACTUAL manual HR bets ... that is my true HR P&L").

Reads tracker/state.enc (decryptable only inside Actions), takes every row whose BOOK is Hard Rock, and reports real
stake, real price, result and profit - not the flat-1u alert-price figures in alerts.json.

It INVENTORIES the state's own source / book values and field names first and filters on what is present (the
tracker tags Hard Rock notes "Peter (Hard Rock note[, est. stake])", and RECLASS can move some into
"ntfy (Peter manual)", so filtering on source == "manual" would find nothing). Rows are selected on BOOK.

Ungraded rows are reported as ungraded, never as zero. Stakes the tracker ESTIMATED (note had no stake: Peter's
sizing) are counted and flagged. Mean return per bet is reported with sd, SE and a 95% range.

READ-ONLY: writes nothing, places nothing, changes no rule. Dollars go to the private email only; the Actions log
prints COUNTS only.
"""
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone

STATE = "tracker/state.enc"
UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def is_hr(b):
    """Book is Hard Rock. NOT the source: the tracker labels EVERY 'Bets manual' note 'Peter (Hard Rock note)'
    whatever its book (Nov 10: two ProphetX notes carried that label and were wrongly pulled into the HR total)."""
    return "hardrock" in str(b.get("book") or "").lower().replace(" ", "")


def price_of(b):
    """The row's price; if None, a trailing/bare American price in the bet text ('Under 230.5 -120').
    tracker_build only parses '(-120)' in parentheses, so un-parenthesised notes come through with price None."""
    pr = num(b.get("price"))
    if pr:
        return pr, False
    m = re.search(r"(?<![\d.])([+-]\d{3})(?!\d)\s*$", str(b.get("bet") or ""))
    return (float(m.group(1)), True) if m else (None, False)


def stake_of(b):
    return num(b.get("stake")) or num(b.get("risk"))


def profit_of(b):
    """(profit, derived?) - the row's own profit when present, else from result + stake + price."""
    p = num(b.get("profit"))
    pr, pr_derived = price_of(b)
    if p is not None and not (pr_derived and b.get("result") == "W" and p == 0):
        return p, False   # (a W with profit 0 and no stored price is the unparsed-price bug: recompute below)
    st, res = stake_of(b), b.get("result")
    if st is None or res not in ("W", "L", "P"):
        return None, False
    if res == "P":
        return 0.0, True
    if res == "L":
        return -st, True
    if pr is None or pr == 0:
        return None, False
    return (st * 100.0 / abs(pr) if pr < 0 else st * pr / 100.0), True


def stats(xs):
    n = len(xs)
    if n == 0:
        return None
    m = sum(xs) / n
    if n < 2:
        return n, m, None, None, None
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    se = sd / math.sqrt(n)
    return n, m, sd, se, (m - 1.96 * se, m + 1.96 * se)


def tot(xs, label):
    g = [b for b in xs if b.get("result") in ("W", "L", "P")]
    pairs = [(b, profit_of(b)) for b in g]
    ok = [(b, p) for b, (p, _) in pairs if p is not None and stake_of(b)]
    prof = sum(p for _, p in ok)
    stk = sum(stake_of(b) for b, _ in ok)
    w = sum(1 for b in g if b["result"] == "W")
    l_ = sum(1 for b in g if b["result"] == "L")
    pu = sum(1 for b in g if b["result"] == "P")
    out = [f"  {label}: graded {len(g)}  {w}-{l_}" + (f"-{pu}" if pu else "")
           + f"  staked ${stk:,.2f}  P&L ${prof:+,.2f}"
           + (f"  ROI {100 * prof / stk:+.1f}%" if stk else "")
           + f"  ({prof / UNIT:+.2f}u at a ${UNIT:,.0f} unit)"]
    r = stats([p / stake_of(b) for b, p in ok])
    if r and r[2] is not None:
        n, m, sd, se, ci = r
        out.append(f"      return per bet: mean {100 * m:+.1f}%  sd {100 * sd:.1f}%  SE {100 * se:.1f}%  "
                   f"95% range {100 * ci[0]:+.1f}% to {100 * ci[1]:+.1f}%  (n={n})")
    elif r:
        out.append(f"      return per bet: n={r[0]}, too few for a spread")
    nd = sum(1 for _, (p, d) in pairs if d)
    miss = len(g) - len(ok)
    if nd or miss:
        out.append(f"      {nd} graded rows had no profit field (derived from result+stake+price); "
                   f"{miss} graded rows unusable (no stake/price) and excluded from $ and return")
    return out


def build(R):
    """Pure: rows in, (report lines, counts dict) out."""
    L = ["HARD ROCK MANUAL P&L PULL - read-only", ""]
    books = Counter(str(b.get("book") or "(none)") for b in R)
    srcs = Counter(str(b.get("source") or "(none)") for b in R)
    L += ["=" * 74, "INVENTORY (so nothing is dropped silently)", "=" * 74,
          f"  rows in state: {len(R)}", "  books:"]
    L += [f"    {n:>5}  {k}" for k, n in books.most_common()]
    L += ["  sources:"] + [f"    {n:>5}  {k}" for k, n in srcs.most_common()]
    keys = sorted(Counter(k for b in R for k in b).keys())
    L += [f"  field names: {keys}", ""]

    hr = [b for b in R if is_hr(b)]
    mism = [b for b in R if not is_hr(b) and "hard rock note" in str(b.get("source") or "").lower()]
    noprice = [b for b in hr if price_of(b)[1]]
    est = [b for b in hr if "est. stake" in str(b.get("source"))]
    def when(b):
        return str(b.get("game_start") or b.get("placed") or b.get("settled") or b.get("first_seen") or "")[:10]
    days = sorted(d for d in (when(b) for b in hr) if d)
    open_ = [b for b in hr if b.get("result") not in ("W", "L", "P")]
    L += ["=" * 74, f"HARD ROCK ROWS: {len(hr)}  (selected on BOOK; {len(open_)} ungraded/open, "
          f"{len(est)} with an ESTIMATED stake)", "=" * 74,
          f"  'Hard Rock note'-labelled rows whose BOOK is not Hard Rock (EXCLUDED): {len(mism)} "
          f"{[str(b.get('book')) for b in mism]}",
          f"  rows whose price was missing on the row and read from the bet text: {len(noprice)}",
          f"  date coverage of these rows: {days[0] if days else '-'} to {days[-1] if days else '-'}",
          "  The tracker only re-reads 'Bets manual' notes from the last 10 days; older rows are what the stored",
          "  state kept. Check this coverage before comparing with the Oct 8 - Nov 10 alert window.", ""]
    for b in sorted(hr, key=when):
        st = stake_of(b)
        p, d = profit_of(b)
        L.append(f"  {when(b)}  {str(b.get('bet'))[:34]:<34} price {str(price_of(b)[0]):>6}  "
                 f"stake {('$%.2f' % st) if st is not None else '?':>9}  {str(b.get('result') or 'OPEN'):<4} "
                 f"P&L {('$%+.2f' % p) if p is not None else '?':>10}{'*' if d else ' '} "
                 f"{str(b.get('source'))[:32]}")
    L += ["  (* = profit derived, not on the row)", "", "=" * 74, "TOTALS (graded only)", "=" * 74]
    L += tot(hr, "ALL HARD ROCK")
    for s in sorted({str(b.get("source")) for b in hr}):
        L += tot([b for b in hr if str(b.get("source")) == s], f"source {s[:40]}")
    real = [b for b in hr if "est. stake" not in str(b.get("source"))]
    if est and real:
        L += tot(real, "EXCLUDING estimated stakes")
    def f(b, *ks):
        return "  ".join(f"{k}={str(b.get(k))[:70]}" for k in ks if b.get(k) not in (None, ""))
    L += ["", "=" * 74, "DIAGNOSTIC: per-row grading evidence for the Hard Rock rows", "=" * 74]
    for b in sorted(hr, key=when):
        L.append(f"  {when(b)} {str(b.get('bet'))[:30]}")
        L.append("      " + f(b, "id", "game", "score", "g_state", "status", "placed", "settled", "site", "dup_of", "to_pay"))
    L += ["", "=" * 74, "DIAGNOSTIC: 'Hard Rock note'-labelled rows that are NOT Hard Rock, and the state rows for the same games", "=" * 74]
    key = lambda b: str(b.get("game") or "").lower()
    for m in mism:
        L.append(f"  NOT HR: {m.get('book')} | {m.get('bet')} | " + f(m, "id", "stake", "price", "to_pay", "result", "placed", "open", "dup_of", "game_start"))
        toks = [w for w in re.findall(r"[a-z]{4,}", key(m)) if w not in ("hawks", "wizards") or True][:6]
        for x in R:
            if x is m:
                continue
            kx = (str(x.get("game") or "") + " " + str(x.get("bet") or "")).lower()
            if any(t in kx for t in toks) and when(x) >= when(m)[:8] + "00":
                L.append("      same-game row: " + f(x, "book", "source", "bet", "stake", "price", "result", "profit", "placed", "strike", "dup_of", "open", "id"))
    L += ["", "=" * 74, "DIAGNOSTIC: any state row on the three Hard Rock bets that have notes but no row above", "=" * 74]
    for kw in ("celtics", "buccaneers", "tampa bay"):
        for x in R:
            kx = (str(x.get("game") or "") + " " + str(x.get("bet") or "")).lower()
            if kw in kx and when(x) >= "2026-11-07":
                L.append(f"  [{kw}] " + f(x, "book", "source", "bet", "stake", "price", "result", "profit", "placed", "id", "dup_of"))
    L += ["", "Stake and price are the tracker's (the note's price, the note's stake or Peter's sizing).",
          "Read-only: no file written, no bet placed, no rule changed. Dollars are in this email only."]
    graded = [b for b in hr if b.get("result") in ("W", "L", "P")]
    return L, {"rows": len(R), "hr": len(hr), "graded": len(graded), "open": len(open_), "est_stake": len(est)}


def main():
    import executor as ex
    import tracker_build as tb
    try:
        st = tb.dec(json.load(open(STATE)))
        bets = (st or {}).get("bets")
        R = list(bets.values()) if isinstance(bets, dict) else (bets or [])
    except Exception as e:
        ex.send("Bets HR MANUAL P&L (failed)", f"could not read {STATE}: {str(e)[:200]}")
        print(f"hr manual pull: state unreadable ({type(e).__name__})")
        return
    L, c = build(R)
    ex.send("Bets HR MANUAL P&L (read-only)", "\n".join(L))
    print(f"hr manual pull: rows {c['rows']}, hard rock {c['hr']}, graded {c['graded']}, open {c['open']}, "
          f"est-stake {c['est_stake']}")   # counts only


if __name__ == "__main__":
    main()
