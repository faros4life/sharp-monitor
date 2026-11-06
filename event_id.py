#!/usr/bin/env python3
"""
CANONICAL EVENT IDENTITY (Peter, Nov 6). One identity for one game across Kalshi, Polymarket and the
sharp-alert feed, so the board stops counting one bet twice.

Why this is needed: the three sources name the same game three ways.
  Kalshi      city, truncated to 13 chars   "Cleveland" / "Oklahoma City" / "Los Angeles C"
  Polymarket  nickname                      "Cavaliers" / "Thunder" / "76ers" / "Trail Blazers"
  sharp feed  city + nickname               "Cleveland Cavaliers" / "Philadelphia 76ers"
The board keyed on that string, so "Cleveland vs Oklahoma City" and "Cavaliers vs. Thunder" were two
different games to it - which both inflated the call count and defeated v3's "one play per game total".

The matching standard is the hardened one Peter set: BOTH teams must resolve distinctively, and the
resolution must be unique. Anything else returns None and is reported, never guessed:
  - an exact match on any known form (city, nickname, city+nickname, common short forms) resolves;
  - otherwise a prefix match against full forms resolves ONLY if exactly one team can match, which is
    what rescues Kalshi's truncation: "los angeles c" -> LAC, "los angeles l" -> LAL, while a bare
    "los angeles" matches two and is therefore REFUSED rather than guessed;
  - the event key carries the ET date, so two different games that tip at the same minute (Nov 4 had
    three games at 01:00Z) stay distinct, and a team pair on different days stays distinct too.

Note on sides: the feed's "side" field is ALREADY canonical OVER/UNDER - "NOT Over 228.5" and
"Under (228.5)" are the same stored side and differ only in "side_label", which is the book's own
display text. So side normalisation needs no mapping; use "side", and show "side_label" only as a label.

Read-only helper: no network, no credits, no state. Public data only.
"""
import re
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# code: (city, nickname, extra short forms)
NBA = {
    "ATL": ("Atlanta", "Hawks", ()),
    "BOS": ("Boston", "Celtics", ()),
    "BKN": ("Brooklyn", "Nets", ("bkn",)),
    "CHA": ("Charlotte", "Hornets", ()),
    "CHI": ("Chicago", "Bulls", ()),
    "CLE": ("Cleveland", "Cavaliers", ("cavs",)),
    "DAL": ("Dallas", "Mavericks", ("mavs",)),
    "DEN": ("Denver", "Nuggets", ()),
    "DET": ("Detroit", "Pistons", ()),
    "GSW": ("Golden State", "Warriors", ("gs", "golden st")),
    "HOU": ("Houston", "Rockets", ()),
    "IND": ("Indiana", "Pacers", ()),
    "LAC": ("Los Angeles Clippers", "Clippers", ("la clippers", "lac", "clips")),
    "LAL": ("Los Angeles Lakers", "Lakers", ("la lakers", "lal")),
    "MEM": ("Memphis", "Grizzlies", ("grizz",)),
    "MIA": ("Miami", "Heat", ()),
    "MIL": ("Milwaukee", "Bucks", ()),
    "MIN": ("Minnesota", "Timberwolves", ("wolves",)),
    "NOP": ("New Orleans", "Pelicans", ("pels",)),
    "NYK": ("New York", "Knicks", ("nyk",)),
    "OKC": ("Oklahoma City", "Thunder", ("okc",)),
    "ORL": ("Orlando", "Magic", ()),
    "PHI": ("Philadelphia", "76ers", ("sixers", "phi")),
    "PHX": ("Phoenix", "Suns", ("phx",)),
    "POR": ("Portland", "Trail Blazers", ("blazers", "portland trail blazers")),
    "SAC": ("Sacramento", "Kings", ()),
    "SAS": ("San Antonio", "Spurs", ("sa",)),
    "TOR": ("Toronto", "Raptors", ("raps",)),
    "UTA": ("Utah", "Jazz", ("uta",)),
    "WAS": ("Washington", "Wizards", ("wsh",)),
}


def _n(s):
    """lowercase, drop accents and punctuation, collapse spaces"""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _tables(league="NBA"):
    """exact-form table, and the list of full forms used for prefix rescue"""
    teams = {"NBA": NBA}.get((league or "").upper())
    if not teams:
        return None, None
    exact, full = {}, []
    for code, (city, nick, extra) in teams.items():
        forms = {city, nick, f"{city} {nick}", code, *extra}
        if nick not in city:
            forms.add(f"{city} {nick}")
        for f in forms:
            exact.setdefault(_n(f), code)
        # full forms a truncated string could be a prefix of
        full += [(_n(city), code), (_n(f"{city} {nick}"), code), (_n(nick), code)]
    return exact, full


def team_code(s, league="NBA"):
    """Canonical code, or None. None is a refusal to guess, not a failure to try."""
    exact, full = _tables(league)
    if exact is None:
        return None
    k = _n(s)
    if not k:
        return None
    if k in exact:
        return exact[k]
    # strip a trailing market suffix the feed sometimes leaves on ("... total points")
    k2 = re.sub(r"\b(total points|total|spread|moneyline|points)\b.*$", "", k).strip()
    if k2 and k2 in exact:
        return exact[k2]
    # prefix rescue for truncated names - unique match only
    cands = {code for form, code in full if form.startswith(k) or (k2 and form.startswith(k2))}
    return cands.pop() if len(cands) == 1 else None


def event_key(league, teams, start_utc, game=None):
    """"NBA|2026-11-04|CLE-OKC", or None when the hardened standard is not met.

    Returns (key, note). note says why on a refusal, so callers can report instead of silently
    dropping a row."""
    lg = (league or "").upper()
    if lg != "NBA":
        return None, f"league {lg or '?'} not mapped (NBA only so far)"
    names = list(teams or [])
    if len(names) != 2 and game:
        names = re.split(r"\s+(?:vs\.?|@|at)\s+", re.sub(r":.*$", "", str(game)), maxsplit=1)
    if len(names) != 2:
        return None, f"could not read two team names from {teams!r} / {game!r}"
    a, b = (team_code(names[0], lg), team_code(names[1], lg))
    if a is None or b is None:
        bad = [n for n, c in zip(names, (a, b)) if c is None]
        return None, f"not distinctive: {bad!r}"
    if a == b:
        return None, f"both names resolved to {a} ({names!r})"
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
    d = st.astimezone(ET).strftime("%Y-%m-%d")
    return f"{lg}|{d}|{'-'.join(sorted((a, b)))}", ""


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
