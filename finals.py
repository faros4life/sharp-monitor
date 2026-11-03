#!/usr/bin/env python3
"""
FINALS (Nov 3, Peter 12:25: "add [units +/-] to bucket test scorecard as a column").
Final scores from ESPN's free scoreboard (the same lookup sharp_monitor uses for the recap; no OddsPapi credits) ->
W / L / P and flat 1-unit result for backtest sightings that carry only a closing-line grade.

Sighting shape (slow_hr / exchange_lag / slowhr_backtest): league, game "P1 vs P2", start ISO, type (spreads / totals /
moneyline), line (participant 1's handicap for spreads; the total for totals), side "1" / "2" / "Over" / "Under".
units(x, dec): +(dec - 1) on a win at the after-fee decimal price, -1 on a loss, 0 on a push; None if no final found.
"""
from datetime import datetime, timedelta

import sharp_monitor as sm

_GAME = {}


def _start(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def find(lg, game, start):
    """(espn game, participant1_is_home) or (None, None). Cached per game for the run."""
    k = (lg, game, start)
    if k in _GAME:
        return _GAME[k]
    out = (None, None)
    st = _start(start)
    if lg in sm.ESPN_PATH and st and " vs " in str(game):
        n1, n2 = str(game).split(" vs ", 1)
        st = st.astimezone(sm.ET)
        done = False
        for test in (sm.team_match, sm.mascot_match):
            for extra in [None] + sm.ESPN_MORE.get(lg, []):
                for off in (0, 1, -1):
                    day = (st + timedelta(days=off)).date().isoformat()
                    hits = []
                    for g in sm.espn_scoreboard(lg, day, extra):
                        if test(n1, g["away"]) and test(n2, g["home"]):
                            hits.append((g, False))
                        elif test(n1, g["home"]) and test(n2, g["away"]):
                            hits.append((g, True))
                    if hits and (test is sm.team_match or len(hits) == 1):
                        out, done = hits[0], True
                        break
                if done:
                    break
            if done:
                break
    _GAME[k] = out
    return out


def result(x):
    """'W' / 'L' / 'P' for one sighting, or None if the game is not found or not final."""
    lg, mk, side, line = x.get("league"), x.get("type"), str(x.get("side")), x.get("line")
    g, p1home = find(lg, x.get("game"), x.get("start"))
    if not g or not g.get("done"):
        return None
    a, h = g["away"]["pts"], g["home"]["pts"]
    if a is None or h is None:
        return None
    p1, p2 = (h, a) if p1home else (a, h)
    if mk == "totals":
        if line is None:
            return None
        tot = a + h - (1 if (g.get("so") and lg == "NHL") else 0)
        d = (tot - line) if side.lower().startswith("over") else (line - tot)
    elif mk == "spreads":
        if line is None:
            return None
        d = (p1 - p2 + line) if side == "1" else (p2 - p1 - line)
    elif mk == "moneyline":
        d = (p1 - p2) if side == "1" else (p2 - p1)
    else:
        return None
    return "W" if d > 1e-9 else ("L" if d < -1e-9 else "P")


def units_wl(res, dec):
    if res == "W" and dec:
        return round(dec - 1, 4)
    if res == "L":
        return -1.0
    if res == "P":
        return 0.0
    return None


def units(x, dec):
    try:
        return units_wl(result(x), dec)
    except Exception:
        return None


def am_dec(am):
    try:
        am = float(am)
    except (TypeError, ValueError):
        return None
    return 1 + (am / 100 if am > 0 else 100 / abs(am))
