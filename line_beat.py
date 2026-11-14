#!/usr/bin/env python3
"""
LINE-BEAT SCORECARD - SHADOW ONLY (Peter, Nov 14 2026: "Build the line-beat scorecard - yes. Keep it shadow-only").

Did the ticket get a BETTER NUMBER than Pinnacle's closing main line? This module answers that and nothing else. It
is pure: no I/O, no network, no import of any execution, grading or registry module. It is NOT CLV and it is never
monetised here - a line beat is reported in POINTS, and turning points into price needs a validated conversion that
does not exist for this sample (conv_measured = conv_estimated = 0), so no "line-adjusted CLV" is produced.

DEFINITIONS (positive = Pinnacle's main line moved TOWARD the ticket between placement and close)
  total OVER   close_main - open_main         (main 44.5 when we bet Over, 46.5 at close -> +2.0)
  total UNDER  open_main - close_main         (main 46.5 when we bet Under, 44.5 at close -> +2.0)
  spread       open_main - close_main, both in the BETTOR'S team orientation
               (our team +3.5 at placement, +2.5 at close -> +1.0;  -2.5 -> -3.5 -> +1.0)
  The ticket's own line is NOT compared with the close: an alternate line differs from the main by construction,
  so "entry vs closing main" scores bought points as a beat (the defect found in run 43636940519).
  moneyline    no line: points are N/A, the ticket is counted only in the price columns

CLOSING MAIN LINE. The ladder's entries are every fresh two-sided Pinnacle line at close, already in the bettor's
orientation. "Main" = among lines whose limit is at least MAIN_LIMIT_FLOOR of the largest limit, the one whose
no-vig probability is nearest 50/50. Largest-limit alone is unreliable here: run 43612799474 showed alternate lines
at a median 0.95 of the main line's limit. When two candidates inside the floor sit on different lines and are
equally near 50/50, the main line is AMBIGUOUS and the ticket is excluded from verified line metrics, not guessed.

PRICE. A same-line price beat is the existing same-line CLV > 0 (Pinnacle no-vig close at the ticket's OWN line x
after-fee entry - 1). "Line OR price beat" is a non-double-counted union:
  line beat (points > 0)                      -> counted, whatever the price
  line tie  (points = 0) and price beat       -> counted
  line loss (points < 0)                      -> NOT counted even with a good price: a worse number plus a better
                                                 price is not a proven win without a validated conversion
"""
MAIN_LIMIT_FLOOR = 0.90
EPS = 1e-9

BEAT, TIE, LOSS = "beat", "tie", "loss"


def main_line(entries, floor=MAIN_LIMIT_FLOOR):
    """(line, why). entries = [(bettor_line, q_bettor, age_min, limit), ...]. why is None, or a fixed reason."""
    ents = [e for e in entries or [] if e and e[0] is not None and e[1] is not None]
    if not ents:
        return None, "no line on the ladder"
    mx = max((e[3] or 0) for e in ents)
    if mx <= 0:
        return None, "no limit on the ladder"
    cand = [e for e in ents if (e[3] or 0) >= floor * mx - EPS]
    best = min(abs(e[1] - 0.5) for e in cand)
    tied = {round(e[0], 6) for e in cand if abs(abs(e[1] - 0.5) - best) < 1e-6}
    if len(tied) > 1:
        return None, "main line ambiguous"
    return next(iter(tied)), None


def signed_points(mtype, side, entry_line, close_line):
    """Signed line advantage in points (positive = beat the close), or None when not defined."""
    if entry_line is None or close_line is None:
        return None
    if mtype == "total":
        if side == "OVER":
            return round(close_line - entry_line, 6)
        if side == "UNDER":
            return round(entry_line - close_line, 6)
        return None
    if mtype == "spread":
        return round(entry_line - close_line, 6)
    return None


def outcome(points):
    if points is None:
        return None
    return BEAT if points > EPS else (LOSS if points < -EPS else TIE)


def grade(info, same_line_clv=None, open_info=None, open_why=None):
    """One ticket. info = the CLOSE ladder (mtype, side, bet_line, entries); open_info = the same ladder read at the
    ticket's placement time. Points = movement of Pinnacle's MAIN line from placement to close, in the ticket's
    direction. The ticket's own line is not compared to the close (an alternate line differs from the main by design).

    Returns {status, mtype, open_line, close_line, points, line, price, any}. status 'ok' or a fixed exclusion."""
    out = {"status": None, "mtype": None, "open_line": None, "close_line": None, "points": None, "line": None,
           "price": None, "any": None}
    price = None if same_line_clv is None else (same_line_clv > EPS)
    out["price"] = price
    if not info:
        out["status"] = "no Pinnacle close"
        return out
    out["mtype"] = info.get("mtype")
    if out["mtype"] == "moneyline":
        out["status"] = "moneyline points not applicable"
        out["any"] = price
        return out
    if out["mtype"] not in ("spread", "total"):
        out["status"] = "market not graded"
        return out
    if out["mtype"] == "total" and info.get("side") not in ("OVER", "UNDER"):
        out["status"] = "total side unknown"
        return out
    if not open_info:
        out["status"] = open_why if open_why in OPEN_REASONS else "no Pinnacle line at placement"
        return out
    if open_info.get("mtype") != out["mtype"] or open_info.get("side") != info.get("side"):
        out["status"] = "placement ladder does not match"
        return out
    cl_, why = main_line(info.get("entries"))
    if cl_ is None:
        out["status"] = why
        return out
    op_, why = main_line(open_info.get("entries"))
    if op_ is None:
        out["status"] = why + " at placement"
        return out
    pts = signed_points(out["mtype"], info.get("side"), op_, cl_)
    out.update(status="ok", open_line=op_, close_line=cl_, points=pts, line=outcome(pts))
    out["any"] = True if out["line"] == BEAT else (bool(price) if out["line"] == TIE and price is not None else
                                                     (None if out["line"] == TIE else False))
    return out


OPEN_REASONS = ("no placement time", "placed after start", "no Pinnacle line at placement")


def tally(grades):
    """Counts for a group: beat/tie/loss among verified, the excluded buckets, and price / union counts."""
    ok = [g for g in grades if g["status"] == "ok"]
    t = {"n": len(grades), "verified": len(ok),
         BEAT: sum(1 for g in ok if g["line"] == BEAT), TIE: sum(1 for g in ok if g["line"] == TIE),
         LOSS: sum(1 for g in ok if g["line"] == LOSS),
         "excluded": {}, "price_n": 0, "price_beat": 0, "any_n": 0, "any_beat": 0}
    for g in grades:
        if g["status"] != "ok":
            t["excluded"][g["status"]] = t["excluded"].get(g["status"], 0) + 1
        if g["price"] is not None:
            t["price_n"] += 1
            t["price_beat"] += 1 if g["price"] else 0
        if g["any"] is not None:
            t["any_n"] += 1
            t["any_beat"] += 1 if g["any"] else 0
    return t


def pct(k, n):
    return f"{100.0 * k / n:.1f}% ({k}/{n})" if n else f"n/a (0/{n})"
