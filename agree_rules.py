#!/usr/bin/env python3
"""
Muse's AGREE rules, coded for zero-latency decisions (checklist of Oct 25, 2026 - Peter's current rules).

decide(entry) takes ONE entry of alerts.json["alerts"] (the first alert per game+market+side; repeats never get a
decision) and returns {"verdict": AGREE | DISAGREE | NO_VERDICT, "gate", "reason", "flags"}.

Gates run IN ORDER; the first failure decides DISAGREE. Gates 7 (stacking / conflict across every book) and 8 (line
floor: at the alert number or better, never chase) are applied by the executor after routing, against live positions
and live books - they need data an alert entry doesn't carry.

Oct 26: global-Polymarket-priced alerts are ROUTED like Hard Rock (gate 6 no longer DISAGREEs them; paper split only).
phase1() = the phase-1 LIVE filter; first_side() = first side stays against ANY earlier sent alert.

FLAGS NEVER VETO and never change the stake (monitor grade incl. C, edge_pct, Muse grade, confirm count, Hard Rock as
the price source, liquidity stars). Pending decisions stay flags until Peter's Oct 30 review.
"""
CAP = -130                       # gate 3: spreads/totals, effective price after the bet book's fee
ML_EDGE_MIN = 2.0                # gate 4: moneylines need >= 2% edge vs Pinnacle no-vig at the alert number
EXEC_BOOKS = {"hardrockbet_fl", "hardrockbet", "prophetx", "novig", "kalshi", "polymarket_us"}   # gate 6
HARD_ROCK = {"hardrockbet_fl", "hardrockbet"}
PM_GLOBAL = {"polymarket"}       # Oct 26: global-Polymarket-priced alerts are ROUTED (like Hard Rock), not DISAGREE
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
    if (a.get("book_key") or "") in PM_GLOBAL:
        f.append("global-Polymarket-priced (routed to the best exchange; paper split, never live in phase 1)")
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
    if kind in ("spr", "tot", "rl") and book not in HARD_ROCK | PM_GLOBAL:
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
    # 6. EXECUTABLE BOOK (dropped retail books are not executable; global Polymarket is routed, Oct 26)
    if book not in EXEC_BOOKS | PM_GLOBAL:
        return dict(out, verdict="DISAGREE", gate=6, reason=f"alert book {a.get('book')} is not an executable book")
    return dict(out, verdict="AGREE", gate=None, reason="all alert gates pass (stacking + line floor checked at routing)")


# ---------------------------------------------------------------- Oct 26 additions
MKT = {"spr": "side", "rl": "side", "ml": "side", "tot": "total"}


def _t(x):
    from datetime import datetime
    try:
        return datetime.fromisoformat((x or "").replace("Z", "+00:00"))
    except Exception:
        return None


def lead_min(a):
    """Minutes from the alert to the listed start (alerts.json minutes_before_start, else alert_utc -> start_utc)."""
    if a.get("minutes_before_start") is not None:
        return float(a["minutes_before_start"])
    t, s = _t(a.get("alert_utc")), _t(a.get("start_utc"))
    return (s - t).total_seconds() / 60 if t and s else None


def side_of(a):
    """OVER / UNDER for totals, else the team name the bet is on."""
    import re
    b = a.get("bet") or ""
    if a.get("kind") == "tot":
        return "OVER" if b.lower().startswith("over") else "UNDER"
    return re.split(r"\s[+-]\d|\sML\b|\sPK\b|\s\(", b)[0].strip()


def first_side(a, feed):
    """Coded fix 2 (Oct 26): the earliest SENT alert on the OTHER side of this game+market, or None.
    First side stays against ANY earlier sent alert, not only positions the executor took or can see."""
    t0 = _t(a.get("alert_utc"))
    if t0 is None:
        return None
    mine, opp = side_of(a), []
    for x in feed or []:
        if x is a or not x.get("sent_to_phone") or x.get("game") != a.get("game") or x.get("sport") != a.get("sport"):
            continue
        if MKT.get(x.get("kind")) != MKT.get(a.get("kind")):
            continue
        tx = _t(x.get("alert_utc"))
        if tx and tx < t0 and side_of(x) != mine:
            opp.append((tx, x))
    return min(opp, key=lambda z: z[0])[1] if opp else None


PHASE1 = ("ProphetX-priced at alert time, Grade A/B, Muse AGREE, NCAAF + NBA spreads + unders, NFL unders only, "
          "not sent 12-24h before start, $50 unit, ProphetX only")


def phase1(a, muse_agree, tag_nfl=False):
    """Phase-1 LIVE filter (Muse + Peter, Oct 25). Returns (eligible, [reasons it is not]).
    tag_nfl=True (Peter's amendment, Oct 26): the DRY RUN also tags NFL plays; NFL in/out is decided at the pre-live
    review. The paper splits keep the NCAAF + NBA definition."""
    why = []
    if (a.get("book_key") or "") != "prophetx":
        why.append(f"priced on {a.get('book') or '?'}, not ProphetX")
    if a.get("grade") not in ("A", "B"):
        why.append(f"grade {a.get('grade') or 'none'}")
    sp = (a.get("sport") or "").upper()
    under = a.get("kind") == "tot" and side_of(a) == "UNDER"
    if sp not in ("NCAAF", "NBA", "NFL"):
        why.append(f"{a.get('sport')} (NCAAF, NBA, NFL only)")
    elif sp == "NFL" and not under:
        why.append("NFL: unders only (Peter, Oct 26)")
    if sp != "NFL" and not (a.get("kind") == "spr" or under):
        why.append("overs and moneylines stay paper")
    ld = lead_min(a)
    if ld is not None and 720 <= ld < 1440:
        why.append(f"sent {ld / 60:.0f}h before start (12-24h window is paper)")
    if a.get("late"):
        why.append("late")
    if not muse_agree:
        why.append("no Muse AGREE")
    return (not why), why
