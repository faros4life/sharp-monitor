#!/usr/bin/env python3
"""CANONICAL TEAM IDENTITY for NHL and NFL fixture matching (CLV forensic audit, 10 Nov 2026).
PREPARED FOR REVIEW. NOT wired into clv_ledger.find_fixture or any live path. Pure, stdlib only.

The gap (clv_ledger.py:376-385): _qualifies demands that at least one side match on TWO distinctive tokens, so
"Flyers vs. Canucks" or "Buffalo vs Minnesota" (one token per side) can never match, although the fixture
"Vancouver Canucks v Philadelphia Flyers" is in the cache. NBA is rescued by nba_names.teams_of; NHL and NFL
have nothing. In the committed-fixture window 110/138 NHL, 37/103 NFL and 105/136 NCAAF alerts fail.

This does NOT relax the identity rule. It replaces fuzzy token overlap with EXACT identity:
  a side resolves to one canonical team by its nickname, else by a city that belongs to exactly one team in
  that league, else it does not resolve; the game matches a fixture only if BOTH sides resolve and equal the
  fixture's two teams (either order); start within +-36h; and exactly one fixture qualifies.
A bare shared city ("New York", "Los Angeles") resolves to nothing; with the books' one-letter suffix
("New York I") it resolves only if that letter is the first letter of exactly one team sharing the city.
Anything else stays UNMATCHED rather than guessed. NCAAF is not attempted: school identity is not a closed list.
"""
import re
from datetime import datetime

NHL = {"ana": ("Anaheim", "Ducks"), "bos": ("Boston", "Bruins"), "buf": ("Buffalo", "Sabres"),
       "cgy": ("Calgary", "Flames"), "car": ("Carolina", "Hurricanes"), "chi": ("Chicago", "Blackhawks"),
       "col": ("Colorado", "Avalanche"), "cbj": ("Columbus", "Blue Jackets"), "dal": ("Dallas", "Stars"),
       "det": ("Detroit", "Red Wings"), "edm": ("Edmonton", "Oilers"), "fla": ("Florida", "Panthers"),
       "lak": ("Los Angeles", "Kings"), "min": ("Minnesota", "Wild"), "mtl": ("Montreal", "Canadiens"),
       "nsh": ("Nashville", "Predators"), "njd": ("New Jersey", "Devils"), "nyi": ("New York", "Islanders"),
       "nyr": ("New York", "Rangers"), "ott": ("Ottawa", "Senators"), "phi": ("Philadelphia", "Flyers"),
       "pit": ("Pittsburgh", "Penguins"), "sj": ("San Jose", "Sharks"), "sea": ("Seattle", "Kraken"),
       "stl": ("St. Louis", "Blues"), "tb": ("Tampa Bay", "Lightning"), "tor": ("Toronto", "Maple Leafs"),
       "utah": ("Utah", "Mammoth"), "van": ("Vancouver", "Canucks"), "vgk": ("Vegas", "Golden Knights"),
       "wsh": ("Washington", "Capitals"), "wpg": ("Winnipeg", "Jets")}
NFL = {"ari": ("Arizona", "Cardinals"), "atl": ("Atlanta", "Falcons"), "bal": ("Baltimore", "Ravens"),
       "buf": ("Buffalo", "Bills"), "car": ("Carolina", "Panthers"), "chi": ("Chicago", "Bears"),
       "cin": ("Cincinnati", "Bengals"), "cle": ("Cleveland", "Browns"), "dal": ("Dallas", "Cowboys"),
       "den": ("Denver", "Broncos"), "det": ("Detroit", "Lions"), "gb": ("Green Bay", "Packers"),
       "hou": ("Houston", "Texans"), "ind": ("Indianapolis", "Colts"), "jax": ("Jacksonville", "Jaguars"),
       "kc": ("Kansas City", "Chiefs"), "lv": ("Las Vegas", "Raiders"), "lac": ("Los Angeles", "Chargers"),
       "lar": ("Los Angeles", "Rams"), "mia": ("Miami", "Dolphins"), "min": ("Minnesota", "Vikings"),
       "ne": ("New England", "Patriots"), "no": ("New Orleans", "Saints"), "nyg": ("New York", "Giants"),
       "nyj": ("New York", "Jets"), "phi": ("Philadelphia", "Eagles"), "pit": ("Pittsburgh", "Steelers"),
       "sf": ("San Francisco", "49ers"), "sea": ("Seattle", "Seahawks"), "tb": ("Tampa Bay", "Buccaneers"),
       "ten": ("Tennessee", "Titans"), "wsh": ("Washington", "Commanders")}
TABLES = {"NHL": NHL, "NFL": NFL}


def _norm(s):
    return " " + re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower().replace(".", "")).strip() + " "


def resolve(league, text):
    """Canonical team id for one side's name, or None (unknown or ambiguous). Never guesses."""
    t = TABLES.get(league)
    if not t:
        return None
    s = _norm(text)
    by_nick = [k for k, (c, n) in t.items() if _norm(n) in s]
    if len(by_nick) == 1:
        return by_nick[0]
    if len(by_nick) > 1:
        return None
    # no nickname: a city that belongs to exactly one team. "Tampa Bay" must not be read as "Bay".
    hit = [k for k, (c, n) in t.items() if _norm(c) in s]
    if len(hit) == 1:
        return hit[0]
    # Shared city ("New York", "Los Angeles"): the books append ONE letter, "New York I", "Los Angeles R".
    # Exact rule: that letter must be the first letter of exactly one of the teams sharing the city.
    # A bare shared city with no letter, or a letter two teams share, stays unresolved.
    for city in {t[h][0] for h in hit}:
        m = re.search(r"\b" + re.escape(_norm(city).strip()) + r" ([a-z])\b", s)
        if m:
            same = [k for k in hit if t[k][0] == city and _norm(t[k][1]).strip().startswith(m.group(1))]
            if len(same) == 1:
                return same[0]
    return None


def game_sides(game):
    """('Flyers', 'Canucks') from 'Flyers vs. Canucks: Total Goals' / 'Buffalo @ Minnesota' / 'A at B'."""
    g = re.split(r":", str(game or ""), 1)[0]
    parts = re.split(r"\s+(?:vs\.?|v|@|at)\s+", g.strip(), flags=re.I)
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)


def find_fixture_canon(fixtures, league, game, game_start, teams=None, window_h=36):
    """fixture id or None. fixtures: {fid: {lg, start, p1, p2}}; game_start / start: datetime or ISO string."""
    if league not in TABLES:
        return None
    a, b = (teams[0], teams[1]) if teams and len(teams) == 2 else game_sides(game)
    ia, ib = resolve(league, a), resolve(league, b)
    if not ia or not ib or ia == ib:
        return None
    want = {ia, ib}
    gs = _dt(game_start)
    hits = []
    for fid, f in fixtures.items():
        if f.get("lg") != league:
            continue
        fs = _dt(f.get("start"))
        if gs and fs and abs((fs - gs).total_seconds()) > window_h * 3600:
            continue
        if {resolve(league, f.get("p1")), resolve(league, f.get("p2"))} == want:
            hits.append(fid)
    return hits[0] if len(hits) == 1 else None


def _dt(x):
    if isinstance(x, datetime):
        return x
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None
