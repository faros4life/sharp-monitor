#!/usr/bin/env python3
"""
CANONICAL EVENT / BET IDENTITY (Peter, Nov 6). One identity for one game across Kalshi, Polymarket and
the sharp-alert feed, so the board stops counting one bet twice.

The names are NOT resolved here. nba_names.py (Nov 5) already owns that: the feeds name NBA teams three
ways - Kalshi by city truncated to 13 chars ("Cleveland", "Los Angeles C"), Polymarket by nickname
("Cavaliers", "76ers"), Novig/ProphetX in full - and nba_names.full() expands any of them to the one
full name. This module adds only what was missing: turning a resolved pair into a key that identifies
the EVENT and the BET, so duplicates collapse.
  (an earlier version of this file carried its own 30-team table, which duplicated nba_names for no
  reason; it now has no team data at all and there is one source of truth for names.)

Why it was needed: the board keyed on the raw game string, so "Cleveland vs Oklahoma City" and
"Cavaliers vs. Thunder" were two different games to it - which inflated the call count AND defeated
v3's own "one play per game total" rule, since the second string never collided with the first.

The matching standard is the hardened one Peter set: BOTH teams must resolve distinctively and the
result must be unique. A name that nba_names does not know comes back unchanged, which is treated as a
REFUSAL, not a match - so bare "Los Angeles" (ambiguous between Clippers and Lakers) is refused rather
than guessed, while "Los Angeles C" resolves. Every refusal returns a reason so the caller reports the
row instead of silently dropping it. The key carries the ET date, so three different games tipping at
the same minute (Nov 4 had three at 01:00Z) stay distinct, and one pair on two nights stays distinct.

On sides: the feed's "side" field is ALREADY canonical OVER/UNDER. "NOT Over 228.5" and "Under (228.5)"
are the same stored side and differ only in "side_label", the book's display text. Nothing to map.

Read-only helper: no network, no credits, no state. Public data only.
"""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import nba_names as nn

ET = ZoneInfo("America/New_York")
KNOWN = set(nn.FULL.values())          # the 30 full names, from nba_names - not a second table


def team_name(s, league="NBA"):
    """The canonical full name, or None. None is a refusal to guess, not a failure to try."""
    if (league or "").upper() != "NBA":
        return None
    raw = str(s or "").strip()
    if not raw:
        return None
    f = nn.full(raw)
    if f in KNOWN:
        return f
    # the feed sometimes leaves a market suffix on the name ("Atlanta vs Washington: Total Points")
    f2 = nn.full(re.sub(r"\b(total points|total|spread|moneyline|points)\b.*$", "", raw, flags=re.I).strip())
    return f2 if f2 in KNOWN else None


def event_key(league, teams, start_utc, game=None):
    """"NBA|2026-11-04|Cleveland Cavaliers+Oklahoma City Thunder", or (None, reason)."""
    lg = (league or "").upper()
    if lg != "NBA":
        return None, f"league {lg or '?'} not mapped (NBA only so far)"
    names = [t for t in (teams or []) if str(t or "").strip()][:2]
    if len(names) != 2 and game:
        names = re.split(r"\s+(?:vs\.?|@|at)\s+", re.sub(r":.*$", "", str(game)), maxsplit=1)
    if len(names) != 2:
        return None, f"could not read two team names from {teams!r} / {game!r}"
    a, b = team_name(names[0], lg), team_name(names[1], lg)
    if a is None or b is None:
        return None, f"not distinctive: {[n for n, c in zip(names, (a, b)) if c is None]!r}"
    if a == b:
        return None, f"both names resolved to {a!r} ({names!r})"
    st = start_utc
    if isinstance(st, str):
        try:
            st = datetime.fromisoformat(st.replace("Z", "+00:00"))
        except Exception:
            st = None
    if st is None:
        return None, "no start time"
    if st.tzinfo is None:
        st = st.replace(tzinfo=timezone.utc)
    return f"{lg}|{st.astimezone(ET):%Y-%m-%d}|{'+'.join(sorted((a, b)))}", ""


def bet_key(league, teams, start_utc, market, side, line, game=None):
    """The identity of a BET, not just an event: same event + market + side + line is the same bet
    whichever book shows it. This is what collapses "Cleveland vs Oklahoma City NOT Over 228.5" and
    "Cavaliers vs. Thunder Under (228.5)" into one row."""
    ek, note = event_key(league, teams, start_utc, game)
    if ek is None:
        return None, note
    sd = str(side or "").strip().upper()
    if sd not in ("OVER", "UNDER"):
        return None, f"side {side!r} is not OVER/UNDER"
    try:
        ln = f"{float(line):g}"
    except Exception:
        return None, f"line {line!r} unreadable"
    return f"{ek}|{str(market or '?').lower()}|{sd}|{ln}", ""
