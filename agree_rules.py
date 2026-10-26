#!/usr/bin/env python3
"""
Muse's AGREE rules, coded for zero-latency decisions (checklist of Oct 25, 2026 - Peter's current rules).

decide(entry) takes ONE entry of alerts.json["alerts"] (the first alert per game+market+side; repeats never get a
decision) and returns {"verdict": AGREE | DISAGREE | NO_VERDICT, "gate", "reason", "flags"}.

Gates run IN ORDER; the first failure decides DISAGREE. Gates 7 (stacking / conflict across every book) and 8 (line
floor: at the alert number or better, never chase) are applied by the executor after routing, against live positions
and live books - they need data an alert entry doesn't carry.

FLAGS NEVER VETO and never change the stake (monitor grade incl. C, edge_pct, Muse grade, confirm count, Hard Rock as
the price source, liquidity stars). Pending decisions stay flags until Peter's Oct 30 review.
"""
CAP = -130                       # gate 3: spreads/totals, effective price after the bet book's fee
ML_EDGE_MIN = 2.0                # gate 4: moneylines need >= 2% edge vs Pinnacle no-vig at the alert number
EXEC_BOOKS = {"hardrockbet_fl", "hardrockbet", "prophetx", "novig", "kalshi", "polymarket_us"}   # gate 6
HARD_ROCK = {"hardrockbet_fl", "hardrockbet"}
COLLEGE = {"NCAAF", "NCAAB"}


def flags(a):
    f = []
    if a.get("grade"):
        f.append(f"monitor grade {a['grade']}" + (f" ({a.get('score')})" if a.get("score") is not None else ""))
    if a.get("edge_pct") is not None:
        f.append(f"edge {a['edge_pct']:+.1f}%")
    f.append(f"confirms {len(a.get('confirmed_by') or [])}")
    if (a.get("book_key") or "") in HARD_ROCK:
        f.append("Hard Rock-priced (routed to the best exchange; Oct 30 review)")
    return f


def decide(a):
    out = {"flags": flags(a)}
    kind, book, sport = a.get("kind"), (a.get("book_key") or ""), (a.get("sport") or "").upper()
    # 1. SENT
    if not a.get("sent_to_phone"):
        return dict(out, verdict="NO_VERDICT", gate=1, reason="not sent to phone (log only)")
    # 2. LATE
    if a.get("late"):
        return dict(out, verdict="DISAGREE", gate=2, reason="late alert")
    # 3. AFTER-FEE PRICE CAP (spreads/totals; Hard Rock-priced alerts are judged at the routed exchange price)
    if kind in ("spr", "tot", "rl") and book not in HARD_ROCK:
        paf = a.get("price_after_fee")
        if paf is not None and paf < CAP:
            return dict(out, verdict="DISAGREE", gate=3, reason=f"after-fee price {paf:+d} worse than {CAP}")
    # 4. MONEYLINE EDGE
    if kind == "ml":
        e = a.get("edge_pct")
        if e is None or e < ML_EDGE_MIN - 0.05:
            return dict(out, verdict="DISAGREE", gate=4, reason=f"moneyline edge {e if e is not None else 'n/a'}% under 2%")
    # 5. COLLEGE TOP 25
    if sport in COLLEGE and a.get("top25") is not True:
        why = "neither team AP Top 25" if a.get("top25") is False else "Top 25 not tagged for this game"
        return dict(out, verdict="DISAGREE", gate=5, reason=why)
    # 6. EXECUTABLE BOOK (global Polymarket and dropped retail books are not executable)
    if book not in EXEC_BOOKS:
        return dict(out, verdict="DISAGREE", gate=6, reason=f"alert book {a.get('book')} is not an executable book")
    return dict(out, verdict="AGREE", gate=None, reason="all alert gates pass (stacking + line floor checked at routing)")
