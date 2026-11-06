#!/usr/bin/env python3
"""
NCAAB TOP 100 (Nov 6, 2026; Peter yes 5:16 / 5:18 AM). Which college basketball games go into the shared history cache
and the model lab: a game counts when EITHER team is in the Top 100.

Ranking: last season's (2025-26) net rating (ORtg - DRtg) from ncaab_prior.json, which the NCAAB openers lane already
builds from ESPN box scores (ncaab-openers branch). Teams with fewer than 15 games are left out. NET rankings are not
published until December; switch to NET then (Peter Nov 6).
Matching leans INCLUSIVE: an extra game only costs a little storage, a missed game is data lost.
Missing ratings file -> load() returns None and callers skip NCAAB (never "all games").
"""
import json
import os

import tracker_build as tb

F = os.environ.get("NCAAB_PRIOR", "") or "ncaab_prior.json"
N, MIN_GP = 100, 15


def load(path=F):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    rows = sorted(((v.get("ortg", 0) - v.get("drtg", 0), k) for k, v in (d.get("teams") or {}).items()
                   if (v.get("gp") or 0) >= MIN_GP), reverse=True)[:N]
    return [w for w in ((tb.toks(k) - tb.WEAK) for _, k in rows) if w] or None


def is_top(name, top):
    """True when this team name (ESPN or OddsPapi form, full or short) belongs to a Top 100 team."""
    w = tb.toks(name) - tb.WEAK
    return bool(w) and any(t <= w or w <= t for t in top)


def game_in(names, top):
    return bool(top) and any(is_top(n, top) for n in names if n)
