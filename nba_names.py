#!/usr/bin/env python3
"""Canonical NBA team names (Nov 5, Peter: "do now").

The liquidity feeds name NBA teams three ways - Kalshi by city ("Milwaukee"), Polymarket by nickname
("Cavaliers"), Novig and ProphetX in full ("Milwaukee Bucks"). The history grader's fixture matcher
requires at least one side to match on two or more distinctive words, so a city-only or nickname-only
name has exactly one word per side and fails - which silently dropped 45 of the board's 48 frozen PLAY
calls out of every CLV measurement. Expanding each name to its full form clears that floor honestly:
the matcher is not loosened, it is handed the team's real name.
"""
FULL = {
    "atlanta": "Atlanta Hawks", "hawks": "Atlanta Hawks",
    "boston": "Boston Celtics", "celtics": "Boston Celtics",
    "brooklyn": "Brooklyn Nets", "nets": "Brooklyn Nets",
    "charlotte": "Charlotte Hornets", "hornets": "Charlotte Hornets",
    "chicago": "Chicago Bulls", "bulls": "Chicago Bulls",
    "cleveland": "Cleveland Cavaliers", "cavaliers": "Cleveland Cavaliers", "cavs": "Cleveland Cavaliers",
    "dallas": "Dallas Mavericks", "mavericks": "Dallas Mavericks", "mavs": "Dallas Mavericks",
    "denver": "Denver Nuggets", "nuggets": "Denver Nuggets",
    "detroit": "Detroit Pistons", "pistons": "Detroit Pistons",
    "golden state": "Golden State Warriors", "warriors": "Golden State Warriors",
    "houston": "Houston Rockets", "rockets": "Houston Rockets",
    "indiana": "Indiana Pacers", "pacers": "Indiana Pacers",
    "los angeles c": "Los Angeles Clippers", "la clippers": "Los Angeles Clippers", "clippers": "Los Angeles Clippers",
    "los angeles l": "Los Angeles Lakers", "la lakers": "Los Angeles Lakers", "lakers": "Los Angeles Lakers",
    "memphis": "Memphis Grizzlies", "grizzlies": "Memphis Grizzlies",
    "miami": "Miami Heat", "heat": "Miami Heat",
    "milwaukee": "Milwaukee Bucks", "bucks": "Milwaukee Bucks",
    "minnesota": "Minnesota Timberwolves", "timberwolves": "Minnesota Timberwolves", "wolves": "Minnesota Timberwolves",
    "new orleans": "New Orleans Pelicans", "pelicans": "New Orleans Pelicans",
    "new york": "New York Knicks", "knicks": "New York Knicks",
    "oklahoma city": "Oklahoma City Thunder", "thunder": "Oklahoma City Thunder",
    "orlando": "Orlando Magic", "magic": "Orlando Magic",
    "philadelphia": "Philadelphia 76ers", "76ers": "Philadelphia 76ers", "sixers": "Philadelphia 76ers",
    "phoenix": "Phoenix Suns", "suns": "Phoenix Suns",
    "portland": "Portland Trail Blazers", "trail blazers": "Portland Trail Blazers", "blazers": "Portland Trail Blazers",
    "sacramento": "Sacramento Kings", "kings": "Sacramento Kings",
    "san antonio": "San Antonio Spurs", "spurs": "San Antonio Spurs",
    "toronto": "Toronto Raptors", "raptors": "Toronto Raptors",
    "utah": "Utah Jazz", "jazz": "Utah Jazz",
    "washington": "Washington Wizards", "wizards": "Washington Wizards",
}


def full(name):
    """The team's full name, or the name unchanged when it is not an NBA team this map knows."""
    k = " ".join(str(name or "").lower().replace(".", " ").split())
    if k in FULL:
        return FULL[k]
    for suf in (" trail blazers", " 76ers"):   # already full
        if k.endswith(suf.strip()) and len(k.split()) > 1:
            return str(name)
    return FULL.get(k.split()[-1] if k.split() else "", str(name))


def teams_of(alert):
    """[{'name': full}, ...] for an NBA alert's teams, for the history grader's fixture matcher; [] otherwise."""
    if (alert.get("league") or "").upper() != "NBA":
        return []
    ts = [t for t in (alert.get("teams") or []) if str(t or "").strip()][:2]
    return [{"name": full(t)} for t in ts] if len(ts) == 2 else []


if __name__ == "__main__":
    for n in ("Magic", "Utah", "76ers", "Cavaliers", "Milwaukee", "Los Angeles C", "Trail Blazers", "Oklahoma City", "Duke"):
        print(f"{n!r:18} -> {full(n)!r}")
