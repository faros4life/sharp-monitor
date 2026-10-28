#!/usr/bin/env python3
"""
Exchange liquidity monitor (paper alerts) - Kalshi + Novig + Polymarket, with ProphetX as a confirming book.

Reads public order books (no keys) for NFL / NCAAF / NBA / NHL games today and tomorrow (ET), main
markets only (moneyline, spread, total), and logs a paper alert when one side of a game's market has
heavy resting BIDS.

Trigger: >= $25,000 of NEW bids on one side (and >= 10% of what was there, capped at $100k), confirmed
on the next check (spoof filter). `rule_met` says whether a second book also has $10k+ on the same side
and the same line. ProphetX slots in once its API key arrives.

Bids only: on both exchanges every resting order is a bid to buy one side (a YES bid at p is also a
NO offer at 1-p), so each side's depth is counted from that side's own bids, never both ways.

Output: liquidity/alerts.json, newest first. Results come from each exchange's own settlement.
Standard library only.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
KALSHI = os.environ.get("KALSHI_API", "") or "https://api.elections.kalshi.com/trade-api/v2"
NOVIG = os.environ.get("NOVIG_API", "") or "https://api.novig.com"
PM_GAMMA = os.environ.get("PM_GAMMA", "") or "https://gamma-api.polymarket.com"
PM_CLOB = os.environ.get("PM_CLOB", "") or "https://clob.polymarket.com"
PM_TAGS = {"NFL": "nfl", "NCAAF": "cfb", "NBA": "nba", "NHL": "nhl", "MLB": "mlb", "NCAAB": "cbb"}
PM_TAGS_MULTI = {"TENNIS": ["atp", "wta"]}   # tennis: both tours, one paper-only league
PM_MTYPE = {"moneyline": "moneyline", "spreads": "spread", "spread": "spread", "totals": "total", "total": "total"}
OUT_DIR = os.environ.get("LIQ_DIR", "") or "liquidity"
STATE_FILE = os.path.join(OUT_DIR, "state.json")
ALERTS_FILE = os.path.join(OUT_DIR, "alerts.json")
PRIMARY_MIN = float(os.environ.get("LIQ_PRIMARY_MIN", "") or "25000")   # floor for NEW money on one side
REL_MIN = float(os.environ.get("LIQ_REL_MIN", "") or "0.10")             # ...and >= 10% of what was already on that side
NEED_CAP = float(os.environ.get("LIQ_NEED_CAP", "") or "100000")         # ...but never more than $100k (big books)
SECOND_MIN = float(os.environ.get("LIQ_SECOND_MIN", "") or "10000")
LEAGUES = [x.strip().upper() for x in (os.environ.get("LIQ_LEAGUES", "") or "NFL,NCAAF,NBA,NHL,MLB,NCAAB,TENNIS").split(",") if x.strip()]
# Read order: the original leagues first with their original read limits (so their record is unchanged), then the
# added leagues with whatever time is left. Tennis is PAPER ONLY: logged, never pushed, never an alert lane.
LEAGUE_PRIORITY = {"NFL": 0, "NCAAF": 0, "NBA": 0, "NHL": 0, "MLB": 1, "NCAAB": 1, "TENNIS": 2}
PAPER_ONLY = {"TENNIS"}
ML_ONLY = {"TENNIS"}   # tennis: match winner only (no set/game handicaps or totals)
EXTRA_CALLS = int(os.environ.get("LIQ_EXTRA_BOOKS", "") or "150")      # added leagues: at most this many book reads per exchange
EXTRA_S = float(os.environ.get("LIQ_EXTRA_SEC", "") or "25")           # ...and at most this many seconds, AFTER the original leagues
PX_LEAGUES = {"NFL", "NCAAF", "NBA", "NHL", "MLB", "NCAAB"}   # ProphetX (confirm-only book); tennis IDs change weekly
BOOKS = [x.strip().lower() for x in (os.environ.get("LIQ_BOOKS", "") or "kalshi,novig,polymarket,prophetx").split(",") if x.strip()]
CONFIRM_ONLY_BOOKS = set()   # Oct 24: ProphetX now starts alerts too (same trigger); graded from ESPN finals at the after-fee best price
MAX_CALLS = int(os.environ.get("LIQ_MAX_BOOKS", "") or "900")          # order-book calls per book per run
SLEEP = float(os.environ.get("LIQ_SLEEP", "") or "0.06")
BUDGET_S = float(os.environ.get("LIQ_BUDGET_SEC", "") or "150")   # max seconds reading books, per exchange, per run
T0 = time.time()


_EX = {"t": None, "n0": 0}


def start_clock():
    global T0
    T0 = time.time()
    _EX.update(t=None, n0=0)


def out_of_time():
    return time.time() - T0 > BUDGET_S


def prio(lg):
    return LEAGUE_PRIORITY.get(lg, 1)


def over_limit(lg, calls):
    """Original leagues: the original caps (MAX_CALLS reads, BUDGET_S seconds). Added leagues: only leftover capacity."""
    if prio(lg) == 0:
        return calls >= MAX_CALLS or out_of_time()
    if _EX["t"] is None:   # first added-league read: start its own small time box
        _EX.update(t=time.time(), n0=calls)
    return calls - _EX["n0"] >= EXTRA_CALLS or time.time() - _EX["t"] > EXTRA_S or out_of_time()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def k_price(mk, field):
    """Kalshi market price field in dollars (0-1): handles 'yes_bid' (cents) and 'yes_bid_dollars'."""
    v = num(mk.get(f"{field}_dollars"))
    if v is not None:
        return v
    v = num(mk.get(field))
    return v / 100.0 if v is not None else None


def k_liquidity(mk):
    v = num(mk.get("liquidity_dollars"))
    if v is not None:
        return v
    v = num(mk.get("liquidity"))
    return v / 100.0 if v is not None else None
NEAR = float(os.environ.get("LIQ_NEAR", "") or "0.03")      # only bids within 3c of that side's best bid count
RATIO = float(os.environ.get("LIQ_RATIO", "") or "3")       # new money on the alert side must be >= 3x new money on the other side
BAND_ML = (0.15, 0.85)    # moneyline sides priced 15-85c
BAND_LINE = (0.30, 0.70)  # spread/total sides priced 30-70c (main lines, not alternates)
FRESH_MIN = float(os.environ.get("LIQ_FRESH_MIN", "") or "60")   # compare against a reading at most this many minutes old
STATE_VERSION = 5   # v5: Novig sizes fixed (1 contract = 1c, not $1); record restarts clean
NTFY_TOPIC = os.environ.get("LIQ_NTFY_TOPIC", "")                       # optional push; empty = file only
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")                             # optional: sportsbook prices at alert time
ODDS_SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba", "NHL": "icehockey_nhl",
              "MLB": "baseball_mlb", "NCAAB": "basketball_ncaab"}   # no tennis (paper only, saves credits)
ODDS_MKT = {"moneyline": "h2h", "spread": "spreads", "total": "totals"}
RUN_T0 = time.time()
K_MTYPE = {"GAME": "moneyline", "SPREAD": "spread", "TOTAL": "total"}
K_CODE = {"NCAAB": ["NCAAMB"]}   # Kalshi series codes that differ from our league name
K_SERIES = {}                    # Kalshi series ticker -> (league, kind)
for _lg in LEAGUES:
    if _lg == "TENNIS":
        K_SERIES.update({"KXATPMATCH": ("TENNIS", "GAME"), "KXWTAMATCH": ("TENNIS", "GAME")})
        continue
    for _c in K_CODE.get(_lg, [_lg]):
        for _k in K_MTYPE:
            K_SERIES[f"KX{_c}{_k}"] = (_lg, _k)
N_MTYPE = {"MONEY": "moneyline", "MONEYLINE": "moneyline", "SPREAD": "spread", "TOTAL": "total"}
N_LEAGUE = {"NFL": "NFL", "NBA": "NBA", "NHL": "NHL", "NCAAF": "NCAAF", "NCAAFB": "NCAAF", "CFB": "NCAAF",
            "COLLEGE FOOTBALL": "NCAAF", "NCAA FOOTBALL": "NCAAF", "MLB": "MLB", "BASEBALL": "MLB",
            "NCAAB": "NCAAB", "NCAAMB": "NCAAB", "NCAABB": "NCAAB", "CBB": "NCAAB", "COLLEGE BASKETBALL": "NCAAB",
            "NCAA BASKETBALL": "NCAAB", "ATP": "TENNIS", "WTA": "TENNIS", "TENNIS": "TENNIS"}
MON = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
STOP = {"at", "vs", "v", "the", "fc", "state", "st", "university", "of", "and", "game", "winner", "points", "scored",
        "wins", "by", "over", "under", "more", "than", "total", "spread", "moneyline", "football", "basketball", "hockey"}


def now_utc():
    return datetime.now(timezone.utc)


def get(url, params=None, tries=3):
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "liquidity-monitor/1.1", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(1)
                continue
            raise
        finally:
            time.sleep(SLEEP)


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def update_alert_times(alerts, n):
    """Oct 28 (fix list #4): keep liquidity/alert_times.json current every run instead of a one-off backfill:
    one row per alert key (key + first_seen_utc), every alert time seen, latest result/units. Rows that left the feed
    stay (in_current_feed false). Key-less rows from the Oct 21 format are dropped."""
    path = os.path.join(OUT_DIR, "alert_times.json")
    try:
        doc = json.load(open(path))
    except Exception:
        doc = {"rows": []}
    feed = "LIQ-EXTRA" if "extra" in OUT_DIR else "LIQ-MAIN"
    rows = {(r.get("key"), r.get("first_seen_utc")): r for r in doc.get("rows") or [] if r.get("key")}
    now = n.strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = set()
    for a in alerts:
        if not a.get("key"):
            continue
        k = (a["key"], a.get("first_seen_utc"))
        cur.add(k)
        r = rows.setdefault(k, {"feed": feed, "key": a["key"], "first_seen_utc": a.get("first_seen_utc"), "alerted_utc_seen": []})
        if a.get("alerted_utc") and a["alerted_utc"] not in r["alerted_utc_seen"]:
            r["alerted_utc_seen"].append(a["alerted_utc"])
        r.update(alerted_utc=a.get("alerted_utc"), league=a.get("league"), market=a.get("market"), game=a.get("game"),
                 side=a.get("side_label"), result=a.get("result"), units_flat=a.get("units_flat"),
                 artifact=bool(a.get("artifact")), in_current_feed=True, last_in_feed_utc=now)
    for k, r in rows.items():
        if k not in cur:
            r["in_current_feed"] = False
    doc["rows"] = sorted(rows.values(), key=lambda r: (r.get("alerted_utc") or "", r.get("key") or ""))
    doc["note"] = ("Liquidity alert times, one row per alert record (key + first_seen_utc); kept current every run since "
                   "Oct 28 (was a one-off Oct 27 backfill from git history). alerted_utc_seen = every alert time the feed "
                   "showed for that record. Join to a poller log by key (plus first_seen_utc where a key re-alerted).")
    doc["updated_utc"] = now
    save(path, doc)


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)


# Pro team nickname -> city word, so 'Charlotte' (Kalshi), 'Hornets' (Polymarket), 'Charlotte Hornets' (Novig) all match.
TEAMS = """
NBA: hawks atlanta|celtics boston|nets brooklyn|hornets charlotte|bulls chicago|cavaliers cleveland|cavs cleveland|mavericks dallas|
mavs dallas|nuggets denver|pistons detroit|warriors golden|rockets houston|pacers indiana|grizzlies memphis|heat miami|bucks milwaukee|
timberwolves minnesota|wolves minnesota|pelicans orleans|thunder oklahoma|magic orlando|76ers philadelphia|sixers philadelphia|
suns phoenix|blazers portland|spurs antonio|raptors toronto|jazz utah|wizards washington|
NFL: cardinals arizona|falcons atlanta|ravens baltimore|bills buffalo|bears chicago|bengals cincinnati|browns cleveland|cowboys dallas|
broncos denver|lions detroit|packers green|texans houston|colts indianapolis|jaguars jacksonville|chiefs kansas|raiders vegas|
dolphins miami|vikings minnesota|patriots england|saints orleans|eagles philadelphia|steelers pittsburgh|49ers francisco|
niners francisco|seahawks seattle|buccaneers tampa|bucs tampa|titans tennessee|commanders washington|
NHL: ducks anaheim|bruins boston|sabres buffalo|flames calgary|hurricanes carolina|blackhawks chicago|avalanche colorado|
oilers edmonton|canadiens montreal|predators nashville|devils jersey|senators ottawa|flyers philadelphia|penguins pittsburgh|
sharks jose|kraken seattle|blues louis|lightning tampa|leafs toronto|mammoth utah|canucks vancouver|capitals washington|wings detroit|jackets columbus|knights vegas|stars dallas|wild minnesota
"""
ALIAS = {}
for _blk in re.split(r"(?:NBA|NFL|NHL):", TEAMS)[1:]:
    for _pair in _blk.split("|"):
        _w = _pair.split()
        if len(_w) == 2:
            ALIAS.setdefault(_w[0], set()).add(_w[1])


# Exchange abbreviations (Novig labels sides 'OKC -8.5', 'DEN', 'MEM +11.5') -> city/nickname words.
ABBR = """atl atlanta|bos boston|bkn brooklyn|cha charlotte|chi chicago|cle cleveland|dal dallas|den denver|det detroit|
gsw golden|hou houston|ind indiana|lac clippers chargers|lal lakers|mem memphis|mia miami|mil milwaukee|min minnesota|
nop orleans|nyk knicks york|okc oklahoma|orl orlando|phi philadelphia|phx phoenix|por portland|sac sacramento|
sas antonio|tor toronto|uta utah|was washington|wsh washington|ana anaheim|buf buffalo|cgy calgary|car carolina|
col colorado|cbj columbus|edm edmonton|fla florida|lak kings|mtl montreal|nsh nashville|njd jersey|nyi islanders|
nyr rangers|ott ottawa|pit pittsburgh|sjs jose|sea seattle|stl louis|tbl tampa|van vancouver|vgk vegas|wpg winnipeg|
ari arizona|bal baltimore|cin cincinnati|gb green|jax jacksonville|kc kansas|lv vegas|lar rams|ne england|no orleans|
nyg giants|nyj jets|sf francisco|tb tampa|ten tennessee"""
for _pair in ABBR.split("|"):
    _w = _pair.split()
    if len(_w) >= 2:
        ALIAS.setdefault(_w[0], set()).update(_w[1:])


MLB_TEAMS = """diamondbacks arizona|dbacks arizona|braves atlanta|orioles baltimore|red boston|sox|cubs chicago|reds cincinnati|
guardians cleveland|rockies colorado|tigers detroit|astros houston|royals kansas|angels anaheim angeles|dodgers angeles|
marlins miami|brewers milwaukee|twins minnesota|mets york|yankees york|athletics oakland sacramento|as athletics|phillies philadelphia|
pirates pittsburgh|padres diego|giants francisco|mariners seattle|cardinals louis|rays tampa|rangers texas|blue toronto|jays toronto|
nationals washington|nats washington"""
MLB_ABBR = """ari arizona diamondbacks|az arizona diamondbacks|atl atlanta braves|bal baltimore orioles|bos boston|chc cubs|
cws white|chw white|cin cincinnati reds|cle cleveland guardians|col colorado rockies|det detroit tigers|hou houston astros|
kc kansas royals|kcr kansas royals|laa angels|lad dodgers|mia miami marlins|mil milwaukee brewers|min minnesota twins|
nym mets|nyy yankees|ath athletics|oak athletics|phi philadelphia phillies|pit pittsburgh pirates|sd diego padres|
sdp diego padres|sf francisco giants|sfg francisco giants|sea seattle mariners|stl louis cardinals|tb tampa rays|
tbr tampa rays|tex texas rangers|tor toronto jays|wsh washington nationals|was washington nationals|wsn washington nationals"""
MLB_ALIAS = {}
for _blk in (MLB_TEAMS, MLB_ABBR):
    for _pair in _blk.replace("\n", "").split("|"):
        _w = _pair.split()
        if len(_w) >= 2:
            MLB_ALIAS.setdefault(_w[0], set()).update(_w[1:])


def abbr_match(abbr, team):
    """College/other abbreviations not in the table: 'ECU' = East Carolina (U), 'MEM' = Memphis, 'UNLV' etc."""
    abbr = abbr.lower()
    words = [w for w in re.findall(r"[a-z0-9]+", (team or "").lower()) if w not in ("of", "the", "at")]
    if not words or not (2 <= len(abbr) <= 5):
        return False
    initials = "".join(w[0] for w in words)
    return abbr in (initials, initials + "u", "u" + initials, initials + "s", initials + "su") \
        or (len(abbr) >= 3 and words[0].startswith(abbr))


PHRASES = (("north carolina state", "nc state"),)   # same school, different spellings across books


def toks(s, lg=None):
    s = re.sub(r"(?<=[a-z])\.(?=[a-z])|(?<=[a-z])\.(?=\s|$)", "", (s or "").lower())   # "N.C." -> "nc", "St." -> "st" (keeps 8.5)
    for a, b in PHRASES:
        s = s.replace(a, b)
    base = {w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and not re.fullmatch(r"\d+(\.\d+)?", w)}
    table = MLB_ALIAS if lg == "MLB" else ({} if lg == "TENNIS" else ALIAS)   # tennis: player names as written
    for w in list(base):
        base |= table.get(w, set())
    return base


def split_teams(title):
    """'Charlotte at Brooklyn' / 'Charlotte Hornets @ Brooklyn Nets' -> ('Charlotte', 'Brooklyn')."""
    for sep in (" @ ", " at ", " vs. ", " vs ", " v "):
        if sep in (title or ""):
            a, b = title.split(sep, 1)
            return a.strip(), re.sub(r"\s*[\(\[:\-|].*$", "", b).strip()
    return None


def team_side(text, teams, lg=None):
    """Which of the game's two teams does `text` name? 0, 1 or None."""
    t = toks(text, lg)
    hits = [len(t & toks(x, lg)) for x in teams]
    if hits[0] == hits[1]:
        # no name overlap: try the side's abbreviation ('ECU +6.5', 'MEM') against each team's name
        ab = [w for w in re.findall(r"[A-Za-z]{2,5}", text or "") if w.isupper()]
        hits = [sum(1 for a in ab if abbr_match(a, x)) for x in teams]
        if hits[0] == hits[1]:
            return None
    return 0 if hits[0] > hits[1] else 1


def near_depth(levels):
    """$ of bids within NEAR of the best bid on this side (cheap far-off bids are not sharp money)."""
    if not levels:
        return 0.0
    best = max(p for p, _ in levels)
    return sum(p * q for p, q in levels if p >= best - NEAR - 1e-9)


LINE_TOL = float(os.environ.get("LIQ_LINE_TOL", "") or "0")   # second-book match needs the same line (0 = exact)


def signed_num(text):
    m = re.search(r"([+-]\d+(?:\.\d+)?)", text or "")
    return float(m.group(1)) if m else None


def near_dollars(levels):
    """Like near_depth, for books whose sizes are already dollars (ProphetX maker stake)."""
    if not levels:
        return 0.0
    best = max(p for p, _ in levels)
    return sum(q for p, q in levels if p >= best - NEAR - 1e-9)


def american(p):
    if not p or p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


# ---------------------------------------------------------------- Kalshi
def k_event_date(event_ticker):
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", event_ticker or "")
    if not m or m.group(2) not in MON:
        return None
    try:
        return datetime(2000 + int(m.group(1)), MON[m.group(2)], int(m.group(3))).date()
    except ValueError:
        return None


def k_paged(path, key, params):
    out, cursor = [], None
    for _ in range(20):
        p = dict(params, **({"cursor": cursor} if cursor else {}))
        d = get(KALSHI + path, p)
        out += d.get(key) or []
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def k_series():
    found, unwired = set(), set()
    for params in ({"category": "Sports"}, {}):
        try:
            for s in k_paged("/series", "series", dict(params, limit=1000)):
                t = (s.get("ticker") or "").upper()
                if t in K_SERIES:
                    found.add(t)
                elif re.match(r"^KX(MLB|NCAAMB|ATP|WTA|TENNIS)", t):
                    unwired.add(t)
        except Exception as ex:
            print(f"Kalshi series listing failed ({params}): {ex}")
        if found:
            break
    if unwired:
        print("Kalshi series seen but not read (FYI): " + ", ".join(sorted(unwired)[:25]))
    return sorted(found or set(K_SERIES))


def k_levels(book, side):
    for container in (book.get("orderbook_fp") or {}, book.get("orderbook") or {}):
        raw = container.get(f"{side}_dollars")
        if raw is not None:
            return [(float(p), float(q)) for p, q in raw]
    return [(float(p) / 100.0, float(q)) for p, q in ((book.get("orderbook") or {}).get(side) or [])]


def k_start(mk):
    for f in ("occurrence_datetime", "event_start_time", "game_start_time"):
        v = mk.get(f)
        if v:
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
    return None


def k_sort_time(mk):
    """Soonest-first ordering for Kalshi markets: start time when given, else the market's close/expiry time."""
    st = k_start(mk)
    if st:
        return st
    for f in ("expected_expiration_time", "close_time"):
        v = mk.get(f)
        if v:
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
    return float("inf")


def kalshi_rows(days):
    """[{book, league, date, teams, market, side(0/1/'OVER'/'UNDER'), line, depth, other_depth, price, ...}]"""
    rows, calls = [], 0
    start_clock()
    todo = []   # gather every candidate market first, then read books soonest-start-first (never alphabetical by series)
    for s in k_series():
        league, kind = K_SERIES.get(s, (s[2:-4], "GAME"))
        try:
            evs = k_paged("/events", "events", {"series_ticker": s, "status": "open", "with_nested_markets": "true", "limit": 200})
        except Exception as ex:
            print(f"Kalshi events failed for {s}: {ex}")
            continue
        for ev in evs:
            d = k_event_date(ev.get("event_ticker", ""))
            if d not in days:
                continue
            for mk in ev.get("markets") or []:
                if (mk.get("status") or "active") not in ("active", "open", "initialized"):
                    continue
                liq = k_liquidity(mk)
                if liq is not None and liq < PRIMARY_MIN:
                    continue  # whole book (both sides) under PRIMARY_MIN ($25k): new money that size can't be there
                if K_MTYPE[kind] != "moneyline":
                    yb = k_price(mk, "yes_bid")
                    if yb is not None and not (0.2 <= yb <= 0.8):
                        continue  # far-off alternate strike, not the main line
                todo.append((d, k_sort_time(mk), 0 if kind == "GAME" else 1, league, kind, ev, mk))
    todo.sort(key=lambda t: (prio(t[3]), t[0], t[1], t[2]))   # original leagues first, then added ones
    for d, _, _, league, kind, ev, mk in todo:
        if over_limit(league, calls):
            if prio(league) == 0 and not out_of_time():
                continue   # original leagues' cap reached: move on to the added leagues
            break
        teams = split_teams(ev.get("title", ""))
        try:
            book = get(f"{KALSHI}/markets/{mk['ticker']}/orderbook")
            calls += 1
        except Exception as ex:
            print(f"Kalshi book failed {mk['ticker']}: {ex}")
            continue
        bids = {x: k_levels(book, x) for x in ("yes", "no")}
        dep = {x: near_depth(bids[x]) for x in ("yes", "no")}
        tot = {x: sum(p * q for p, q in bids[x]) for x in ("yes", "no")}
        label = mk.get("yes_sub_title") or mk.get("subtitle") or mk.get("title") or mk["ticker"]
        strike = num(mk.get("floor_strike"))
        if strike is None and K_MTYPE[kind] != "moneyline":
            ms = re.search(r"over ([\d.]+)", label.lower())
            strike = float(ms.group(1)) if ms else None
        if strike is not None and f"{strike:g}" not in label:
            label = f"{label} [{strike:g}]"
        for x in ("yes", "no"):
            other = "no" if x == "yes" else "yes"
            best_other = max((p for p, _ in bids[other]), default=None)
            line = None
            if K_MTYPE[kind] == "total":
                over_yes = "under" not in label.lower()
                side = ("OVER" if over_yes else "UNDER") if x == "yes" else ("UNDER" if over_yes else "OVER")
                line = strike
            else:
                t = team_side(label, teams, league) if teams else None
                side = None if t is None else (t if x == "yes" else 1 - t)
                if K_MTYPE[kind] == "spread" and strike is not None:
                    line = -strike if x == "yes" else strike   # YES "X wins by over S" = X -S; NO = the other team +S
            rows.append(dict(book="kalshi", league=league, date=d.isoformat(), teams=list(teams) if teams else None,
                             game=ev.get("title") or ev.get("event_ticker"), market=K_MTYPE[kind], side=side, line=line,
                             side_label=label if x == "yes" else f"NOT {label}", depth=dep[x], other_depth=dep[other],
                             total_depth=tot[x], other_total=tot[other],
                             best_bid=max((p for p, _ in bids[x]), default=None),
                             price=round(1 - best_other, 4) if best_other is not None else None,
                             event=ev.get("event_ticker"), start=k_start(mk), mid=mk["ticker"],
                             ref={"market_ticker": mk["ticker"], "kalshi_side": x}))
    print(f"Kalshi: {calls} books read in {time.time() - T0:.0f}s of {len(todo)} candidates"
          + (" (time budget hit)" if out_of_time() else ""))
    return rows


def kalshi_result(ref):
    mk = get(f"{KALSHI}/markets/{ref['market_ticker']}").get("market", {})
    res = (mk.get("result") or "").lower()
    if mk.get("status") in ("settled", "finalized", "determined") and res in ("yes", "no"):
        return "W" if res == ref["kalshi_side"] else "L"
    if res in ("void", "canceled", "cancelled"):
        return "VOID"
    return None


# ---------------------------------------------------------------- Novig (public, unsigned routes)
def n_paged(path, params):
    out, after = [], None
    for _ in range(20):
        p = dict(params, **({"after": after} if after else {}))
        d = get(NOVIG + path, p)
        out += d.get("items") or []
        after = d.get("next")
        if not after:
            break
    return out


def novig_rows(days, n):
    lo = int(datetime.combine(min(days), datetime.min.time(), ET).timestamp() * 1000)
    hi = int(datetime.combine(max(days) + timedelta(days=1), datetime.min.time(), ET).timestamp() * 1000)
    lo = max(lo, int(n.timestamp() * 1000))  # pregame only: books empty once a game goes live
    start_clock()
    try:
        evs = n_paged("/v3/public/catalog/events", {"startsAfter": lo, "startsBefore": hi, "limit": 5000})
        mks = n_paged("/v3/public/catalog/markets", {"startsAfter": lo, "startsBefore": hi, "limit": 5000})
    except Exception as ex:
        print(f"Novig catalog failed: {ex}")
        return []
    ev_by = {}
    for e in evs:
        lg = N_LEAGUE.get((e.get("league") or "").upper().strip())
        if lg in LEAGUES:
            ev_by[e["eventId"]] = e
    seen_types = sorted({m.get("marketType", "") for m in mks if m.get("eventId") in ev_by})
    other_lgs = sorted({(e.get("league") or "").upper().strip() for e in evs} - set(N_LEAGUE))
    if other_lgs:
        print(f"Novig leagues not read (FYI): {other_lgs[:25]}")
    print(f"Novig: {len(ev_by)} events in leagues, market types seen: {seen_types}")
    rows, calls, skipped = [], 0, 0
    direction = {"done": False, "ok": True}
    # Pick each game's main strike from the catalog bids BEFORE reading any order book:
    # in-band markets only, and for spreads/totals only the strike nearest 50c per game+market.
    picks = {}
    for mk in mks:
        e = ev_by.get(mk.get("eventId"))
        mtype = N_MTYPE.get((mk.get("marketType") or "").upper())
        oc = mk.get("outcomes") or []
        if not e or not mtype or mk.get("status") != "OPEN" or len(oc) != 2:
            continue
        if mtype != "moneyline" and N_LEAGUE.get((e.get("league") or "").upper().strip()) in ML_ONLY:
            continue
        bids = [num((o.get("bid") or {}).get("price")) for o in oc]
        costs = [1 - bids[1 - i] for i in (0, 1) if bids[1 - i] is not None]
        band = BAND_ML if mtype == "moneyline" else BAND_LINE
        inb = [c for c in costs if band[0] <= c <= band[1]]
        if not inb:
            skipped += 1
            continue
        dist = min(abs(c - 0.5) for c in inb)
        k = (mk["eventId"], mtype)
        if k not in picks or dist < picks[k][0]:
            if k in picks:
                skipped += 1
            picks[k] = (dist, mk)
        else:
            skipped += 1
    def n_lg(m):
        return N_LEAGUE.get((ev_by[m["eventId"]].get("league") or "").upper().strip())
    chosen = sorted((v[1] for v in picks.values()), key=lambda m: (prio(n_lg(m)), m.get("startsTs") or 0))   # soonest first
    for mk in chosen:
        e = ev_by.get(mk.get("eventId"))
        mtype = N_MTYPE.get((mk.get("marketType") or "").upper())
        if over_limit(n_lg(mk), calls):
            if prio(n_lg(mk)) == 0 and not out_of_time():
                continue
            break
        try:
            book = get(f"{NOVIG}/v3/public/catalog/markets/{mk['marketId']}/book", {"depth": 20})
            calls += 1
        except Exception as ex:
            print(f"Novig book failed {mk['marketId']}: {ex}")
            continue
        orders = book.get("orders") or {}
        outs = mk.get("outcomes") or []
        if not direction["done"]:
            # Direction test: the best (highest) order in outcome X's book should equal the catalog's bid for X
            # if the per-outcome orders are BIDS. If they're the take side instead, Novig is excluded this run.
            for o in outs:
                cat_bid = num((o.get("bid") or {}).get("price"))
                prices = [float(r["price"]) for r in orders.get(o["outcomeId"], [])]
                if cat_bid is not None and prices:
                    best = max(prices)
                    direction["done"] = True
                    direction["ok"] = abs(best - cat_bid) < 1e-6
                    print(f"Novig direction test: market {mk['marketId']} outcome '{o.get('name')}': best book order "
                          f"{best} vs catalog bid {cat_bid} -> " + ("MATCH: orders are bids for that outcome"
                          if direction["ok"] else "MISMATCH: orders are NOT the outcome's bids; Novig excluded this run"))
                    break
            if direction["done"] and not direction["ok"]:
                break
        if len(outs) != 2:
            continue  # main markets are two-way
        teams = split_teams(e.get("description") or mk.get("description") or "")
        d = datetime.fromtimestamp(e["startsTs"] / 1000, ET).date().isoformat()
        # Novig: 1 contract pays 1c, so qty/100 = contracts in $1 units (dollars = price x qty / 100)
        lv = {o["outcomeId"]: [(float(r["price"]), int(r["qty"]) / 100.0) for r in orders.get(o["outcomeId"], [])] for o in outs}
        dep = {k: near_depth(v) for k, v in lv.items()}
        tot = {k: sum(p * q for p, q in v) for k, v in lv.items()}
        for i, o in enumerate(outs):
            other = outs[1 - i]
            best_other = max((float(r["price"]) for r in orders.get(other["outcomeId"], [])), default=None)
            name = o.get("name") or ""
            if mtype == "total":
                side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
            else:
                side = team_side(name, teams, n_lg(mk)) if teams else None
            strike = mk.get("strike")
            if mtype == "total":
                line = num(strike)
            elif mtype == "spread":
                line = signed_num(name)   # outcome names carry the side's own line, e.g. 'PHX +21.5'
                if line is None and num(strike) is not None and side in (0, 1):
                    line = num(strike) if side == 1 else -num(strike)   # strike = home (2nd-listed) handicap
            else:
                line = None
            rows.append(dict(book="novig", league=N_LEAGUE.get((e.get("league") or "").upper().strip()), date=d,
                             teams=list(teams) if teams else None, game=e.get("description"), market=mtype, side=side,
                             line=line, mid=mk["marketId"],
                             side_label=name + (f" ({strike})" if strike else ""), depth=dep[o["outcomeId"]],
                             other_depth=dep[other["outcomeId"]], total_depth=tot[o["outcomeId"]],
                             other_total=tot[other["outcomeId"]], best_bid=max((p for p, _ in lv[o["outcomeId"]]), default=None),
                             price=round(1 - best_other, 4) if best_other is not None else None,
                             start=e["startsTs"] / 1000, ref={"market_id": mk["marketId"], "outcome_id": o["outcomeId"]}))
    if not direction["done"]:
        print("Novig direction test: not run (no book with both catalog bid and orders this run)")
    print(f"Novig: {calls} books read in {time.time() - T0:.0f}s of {len(chosen)} main lines, {skipped} alternate/empty lines skipped"
          + (" (time budget hit)" if out_of_time() else ""))
    if direction["done"] and not direction["ok"]:
        return []
    return rows


def novig_result(ref):
    mk = get(f"{NOVIG}/v3/public/catalog/markets/{ref['market_id']}")
    if mk.get("status") != "SETTLED":
        return None
    for o in mk.get("outcomes") or []:
        if o.get("outcomeId") == ref["outcome_id"]:
            st = (o.get("status") or "").upper()
            return {"WIN": "W", "LOSS": "L", "PUSH": "P"}.get(st, "VOID" if st and st != "TBD" else None)
    return None


# ---------------------------------------------------------------- Polymarket (public Gamma + CLOB, no key)
def jl(x):
    if isinstance(x, list):
        return x
    try:
        return json.loads(x or "[]")
    except Exception:
        return []


def pm_start(st):
    if not st:
        return None
    st = st.strip().replace(" ", "T").replace("Z", "+00:00")
    if re.search(r"[+-]\d\d$", st):
        st += ":00"
    try:
        d = datetime.fromisoformat(st)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def pm_rows(days, n):
    rows, calls = [], 0
    start_clock()
    todo = []   # gather all leagues' candidate markets, then read books soonest-start-first
    seen_mk = set()
    for lg in LEAGUES:
        tags = PM_TAGS_MULTI.get(lg) or ([PM_TAGS[lg]] if PM_TAGS.get(lg) else [])
        evs = []
        for tag in tags:
            off = 0
            try:
                while off < 2000:
                    page = get(f"{PM_GAMMA}/events", {"tag_slug": tag, "active": "true", "closed": "false", "limit": 200, "offset": off})
                    page = page if isinstance(page, list) else page.get("data", [])
                    evs += page
                    if len(page) < 200:
                        break
                    off += 200
            except Exception as ex:
                print(f"Polymarket events failed ({tag}): {ex}")
        for ev in evs:
            teams = split_teams(ev.get("title", ""))
            if not teams:
                continue
            for mk in ev.get("markets") or []:
                mtype = PM_MTYPE.get((mk.get("sportsMarketType") or "").lower())
                if not mtype or mk.get("closed") or mk.get("active") is False or str(mk.get("id")) in seen_mk:
                    continue
                if lg in ML_ONLY and mtype != "moneyline":
                    continue
                seen_mk.add(str(mk.get("id")))
                start = pm_start(mk.get("gameStartTime") or ev.get("startTime") or ev.get("endDate"))
                if not start or start <= n or start.astimezone(ET).date() not in days:
                    continue
                outs, tids = jl(mk.get("outcomes")), jl(mk.get("clobTokenIds"))
                if len(outs) != 2 or len(tids) != 2:
                    continue
                pl = num(mk.get("liquidityClob")) or num(mk.get("liquidityNum")) or num(mk.get("liquidity"))
                if pl is not None and pl < PRIMARY_MIN:
                    continue  # whole book under PRIMARY_MIN ($25k): new money that size can't be there
                todo.append((start, lg, ev, teams, mk, mtype, outs, tids))
    todo.sort(key=lambda t: (prio(t[1]), t[0]))   # original leagues first, soonest first
    for start, lg, ev, teams, mk, mtype, outs, tids in todo:
        if over_limit(lg, calls):
            if prio(lg) == 0 and not out_of_time():
                continue
            break
        books = []
        for t in tids:
            try:
                books.append(get(f"{PM_CLOB}/book", {"token_id": t}))
                calls += 1
            except Exception as ex:
                print(f"Polymarket book failed {t}: {ex}")
                books.append({})
        bids = [[(float(b["price"]), float(b["size"])) for b in (bk.get("bids") or [])] for bk in books]
        dep = [near_depth(b) for b in bids]
        tot = [sum(p * q for p, q in b) for b in bids]
        ln = num(mk.get("line"))
        for i in (0, 1):
            name = str(outs[i])
            if mtype == "total":
                side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                line = ln
            else:
                side = team_side(name, teams, lg)
                line = None if (mtype != "spread" or ln is None) else (ln if i == 0 else -ln)   # line is the 1st outcome's
            best_other = max((p for p, _ in bids[1 - i]), default=None)
            rows.append(dict(book="polymarket", league=lg, date=start.astimezone(ET).date().isoformat(),
                             teams=list(teams), game=ev.get("title"), market=mtype, side=side, line=line,
                             side_label=name + (f" ({line:+g})" if (line is not None and mtype == "spread")
                                                else (f" ({line:g})" if line is not None else "")),
                             depth=dep[i], other_depth=dep[1 - i], total_depth=tot[i], other_total=tot[1 - i],
                             best_bid=max((p for p, _ in bids[i]), default=None),
                             price=round(1 - best_other, 4) if best_other is not None else None,
                             start=start.timestamp(), mid=str(mk.get("id")),
                             ref={"pm_market_id": str(mk.get("id")), "outcome_index": i}))
    print(f"Polymarket: {calls} books read in {time.time() - T0:.0f}s of {len(todo)} candidate markets"
          + (" (time budget hit)" if out_of_time() else ""))
    return rows


def pm_result(ref):
    mk = get(f"{PM_GAMMA}/markets/{ref['pm_market_id']}")
    if not mk.get("closed"):
        return None
    prices = [float(x) for x in jl(mk.get("outcomePrices"))]
    if len(prices) != 2:
        return None
    p = prices[ref["outcome_index"]]
    return "W" if p >= 0.99 else ("L" if p <= 0.01 else "P")


# ---------------------------------------------------------------- ProphetX (read-only key; confirming book)
PX_BASE = os.environ.get("PX_BASE", "") or "https://cash.api.prophetx.co/partner"
PX_ACCESS = os.environ.get("PROPHETX_ACCESS_KEY", "")
PX_SECRET = os.environ.get("PROPHETX_SECRET_KEY", "")
PX_TOURNAMENTS = {"NHL": 234, "NFL": 31, "NCAAF": 27653, "NBA": 132, "MLB": 109, "NCAAB": 648}
_PXT = {"token": None}
PX_FEE = float(os.environ.get("PX_FEE", "") or "0.02")   # ProphetX takes 2% of winnings: prices compared after the fee
# Taker fees per contract = coef x P x (1 - P) (checked Oct 22, 2026): Kalshi 0.07 (schedule eff. Jul 7, 2026);
# Polymarket global book 0.03 (Fee Structure V2, Mar 30, 2026). Novig pregame straights: no fee.
TAKER_COEF = {"kalshi": float(os.environ.get("KALSHI_FEE", "") or "0.07"),
              "polymarket": float(os.environ.get("PM_FEE", "") or "0.03"), "novig": 0.0}


def eff_cost(book, c):
    """Cost to buy one $1 contract after taker fees / fee on winnings (what you really pay per $1 of payout)."""
    if c is None or c <= 0 or c >= 1:
        return c
    if book == "prophetx":
        return round(1 / (1 + (1 - PX_FEE) * (1 - c) / c), 4)
    return round(c + TAKER_COEF.get(book, 0.0) * c * (1 - c), 4)


def px_call(path, body=None):
    for i in range(4):
        req = urllib.request.Request(PX_BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                     method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **({"Authorization": f"Bearer {_PXT['token']}"} if _PXT["token"] else {})})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                out = json.loads(r.read().decode())
            time.sleep(1.1)   # ProphetX rate limit
            return out
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and i < 3:
                time.sleep(int(ex.headers.get("Retry-After") or 0) or 5 * (i + 1))
                continue
            raise


def px_lines(mk):
    """[(outcome price levels, line)]: moneylines carry 'selections'; spreads/totals nest one entry per line."""
    out = [(lv, num(mk.get("strike"))) for lv in (mk.get("selections") or []) if lv]
    if out:
        return out
    for val in mk.values():
        if isinstance(val, list) and val and isinstance(val[0], dict) and "selections" in val[0]:
            for ln in val:
                lnum = num(ln.get("line")) if ln.get("line") is not None else num(ln.get("strike"))
                out += [(lv, lnum) for lv in (ln.get("selections") or []) if lv]
    return out


def am_prob(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def px_find_tournaments():
    """ProphetX tournament ids for the added leagues, found by name (one call). Tennis: ATP/WTA singles events only."""
    try:
        tl = ((px_call("/mm/get_tournaments").get("data") or {}).get("tournaments")) or []
    except Exception as ex:
        print(f"ProphetX tournaments failed: {ex}")
        return []
    out = []
    for t in tl:
        nm = (t.get("name") or "").strip()
        lo = nm.lower()
        lg = None
        if lo in ("mlb", "major league baseball"):
            lg = "MLB"
        elif lo in ("ncaab", "ncaa basketball", "college basketball", "ncaam", "ncaa men's basketball") or \
                ("ncaa" in lo and "basketball" in lo and "women" not in lo):
            lg = "NCAAB"
        elif lo.startswith(("atp", "wta")) and not any(w in lo for w in ("doubles", "challenger", "itf", "qualif")):
            lg = "TENNIS"
        if lg in LEAGUES and t.get("id") is not None:
            out.append((lg, t["id"]))
    print("ProphetX added tournaments: " + (", ".join(f"{lg} {tid}" for lg, tid in out[:30]) or "none found"))
    return out


def px_rows(days, n):
    """ProphetX lists, per outcome, the prices a bettor can TAKE. Those are resting orders from makers on the other
    outcome, so money wanting side X = the ladder listed under X's opponent (maker stake = 'quantity'), at bid
    price 1 - p(taker price). Cost to buy X = p(best price on X's own ladder)."""
    if not (PX_ACCESS and PX_SECRET):
        print("ProphetX: no key secrets, skipped")
        return []
    start_clock()
    rows, calls = [], 0
    try:
        d = px_call("/auth/login", {"access_key": PX_ACCESS, "secret_key": PX_SECRET})
        _PXT["token"] = (d.get("data") or {}).get("access_token")
    except Exception as ex:
        print(f"ProphetX login failed: {ex}")
        return []
    todo = []
    tours = [(lg, PX_TOURNAMENTS[lg]) for lg in LEAGUES if lg in PX_TOURNAMENTS and lg in PX_LEAGUES]
    for lg, tid in tours:
        try:
            evs = (px_call(f"/mm/get_sport_events?tournament_id={tid}").get("data") or {}).get("sport_events") or []
        except Exception as ex:
            if "404" not in str(ex):   # 404 = no games listed yet (e.g. NCAAB before the opener)
                print(f"ProphetX events failed ({lg}): {ex}")
            continue
        for e in evs:
            try:
                st = datetime.fromisoformat(e["scheduled"].replace("Z", "+00:00"))
            except Exception:
                continue
            if st <= n or st.astimezone(ET).date() not in days or (e.get("status") or "not_started") != "not_started":
                continue
            todo.append((st, lg, e))
    todo.sort(key=lambda t: (prio(t[1]), t[0]))
    for st, lg, e in todo:
        if over_limit(lg, 0):
            if prio(lg) == 0 and not out_of_time():
                continue
            break
        comps = e.get("competitors") or []
        home = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "home"), None)
        away = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "away"), None)
        teams = (away, home) if (home and away) else split_teams(e.get("name") or "")
        if not teams:
            continue
        try:
            data = px_call(f"/v4/mm/get_markets?event_id={e['event_id']}").get("data") or {}
            calls += 1
        except Exception as ex:
            print(f"ProphetX markets failed {e.get('event_id')}: {ex}")
            continue
        mks = data if isinstance(data, list) else (data.get("markets") or data.get(str(e["event_id"])) or [])
        for mk in mks:
            mtype = (mk.get("type") or "").lower()
            if lg in ML_ONLY and mtype != "moneyline":
                continue
            if mtype not in ("moneyline", "spread", "total") or (mk.get("sub_type") or mtype).lower() != mtype \
                    or (mk.get("status") or "active") != "active":
                continue
            by_line = {}
            for levels, mline in px_lines(mk):
                f = levels[0]
                name = f.get("name") or ""
                if mtype == "total":
                    side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                    line = num(f.get("strike")) or mline
                    gkey = line
                else:
                    side = team_side(name, teams, lg)
                    line = num(f.get("strike")) if mtype == "spread" else None
                    gkey = abs(line) if line is not None else 0
                if side is None:
                    continue
                by_line.setdefault(gkey, []).append((side, line, name, levels))
            for gkey, outs in by_line.items():
                if len(outs) != 2:
                    continue
                for i in (0, 1):
                    side, line, name, levels = outs[i]
                    opp_levels = outs[1 - i][3]
                    bids = [(round(1 - am_prob(x["price"]), 4), float(x.get("quantity") or 0)) for x in opp_levels
                            if x.get("price") is not None]
                    obids = [(round(1 - am_prob(x["price"]), 4), float(x.get("quantity") or 0)) for x in levels
                             if x.get("price") is not None]
                    best_own = max((x["price"] for x in levels if x.get("price") is not None), default=None)
                    cost = round(am_prob(best_own), 4) if best_own is not None else None

                    mid = f"{e['event_id']}|{mk.get('id')}|{gkey}"
                    rows.append(dict(book="prophetx", league=lg, date=st.astimezone(ET).date().isoformat(), teams=list(teams),
                                     game=e.get("name"), market=mtype, side=side, line=line,
                                     side_label=name + (f" ({line:+g})" if (line is not None and mtype == "spread") else
                                                        (f" ({line:g})" if line is not None else "")),
                                     depth=near_dollars(bids), other_depth=near_dollars(obids),
                                     total_depth=sum(q for _, q in bids), other_total=sum(q for _, q in obids),
                                     best_bid=max((p for p, _ in bids), default=None), price=cost,
                                     start=st.timestamp(), mid=mid,
                                     ref={"px_event": e["event_id"], "px_market": mk.get("id"), "line": gkey, "side": str(side)}))
    print(f"ProphetX: {calls} games read in {time.time() - T0:.0f}s of {len(todo)} candidates"
          + (" (time budget hit)" if out_of_time() else ""))
    return rows


# ---------------------------------------------------------------- matching across books
def game_key(row):
    """Same game on both books: same date and both teams' names overlap."""
    return row["league"], row["date"]


def same_game(a, b):
    if a["league"] != b["league"] or a["date"] != b["date"] or not a["teams"] or not b["teams"]:
        return None
    lg = a["league"]
    ta, tb = [toks(x, lg) for x in a["teams"]], [toks(x, lg) for x in b["teams"]]
    if ta[0] & tb[0] and ta[1] & tb[1]:
        return "same"
    if ta[0] & tb[1] and ta[1] & tb[0]:
        return "flipped"   # one book lists the teams in the other order
    return None


def same_side(a, b, how, check_line=True):
    if a["side"] is None or b["side"] is None:
        return False
    if a["market"] == "total" or b["market"] == "total":
        ok = a["side"] == b["side"]
    else:
        ok = a["side"] == (b["side"] if how == "same" else 1 - b["side"])
    if ok and check_line and a["market"] == b["market"] and a["market"] in ("spread", "total"):
        la, lb = a.get("line"), b.get("line")
        ok = la is not None and lb is not None and abs(la - lb) <= LINE_TOL + 1e-9   # same line, not just same side
    return ok


def side_key(r):
    if r["side"] in ("OVER", "UNDER"):
        return r["side"]
    if r["side"] is None or not r["teams"]:
        return r["side_label"]
    return r["teams"][r["side"]]


# ---------------------------------------------------------------- settlement, notify
_SM = {}


def espn_result(a, n):
    """Grade from ESPN final scores (the sharp-monitor's own scoring) when the exchange won't give a result."""
    if "mod" not in _SM:
        try:
            import sharp_monitor as sm
            _SM["mod"] = sm
        except Exception as ex:
            print(f"ESPN grading unavailable: {ex}")
            _SM["mod"] = None
    sm = _SM["mod"]
    teams = a.get("teams")
    if not sm or not teams or not a.get("start_utc") or a.get("league") not in getattr(sm, "ESPN_PATH", {}):
        return None   # e.g. tennis: graded only from the exchange's own settlement
    if datetime.fromisoformat(a["start_utc"].replace("Z", "+00:00")) > n - timedelta(hours=3):
        return None   # not over yet
    kind = {"moneyline": "ml", "spread": "spr", "total": "tot"}.get(a["market"])
    side = a.get("side")
    if kind == "tot":
        side = "Over" if side == "OVER" else ("Under" if side == "UNDER" else None)
    if kind is None or side is None or (kind != "ml" and a.get("line") is None):
        return None
    for g_order in ((teams[0], teams[1]), (teams[1], teams[0])):   # some books list home first
        e = {"game": f"{g_order[0]} @ {g_order[1]}", "sport": a["league"], "start": a["start_utc"], "kind": kind,
             "side": side, "pt": a.get("line") if kind != "ml" else None}
        try:
            g = sm.find_game(e)
            res = sm.settle(e, g) if g else None
        except Exception as ex:
            print(f"ESPN grading failed {a.get('game')}: {ex}")
            return None
        if res:
            return res[0]
    return None


def settle(alerts, n):
    today = n.astimezone(ET).date().isoformat()
    for a in alerts:
        if a.get("result") is not None or (a.get("date") or "9999") > today:
            continue
        try:
            r = {"kalshi": kalshi_result, "novig": novig_result, "polymarket": pm_result}.get(a["book"], lambda _r: None)(a["ref"])
        except Exception as ex:
            r = None
            if "404" not in str(ex):
                print(f"settle lookup failed {a['ref']}: {ex}")
        if r is None:
            r = espn_result(a, n)
            if r:
                a["graded_by"] = "espn"
        if r:
            a["result"] = r
            if a.get("close_price") is None:   # never got a real pregame close read: graded, but kept out of the record
                a["artifact"] = "no_pregame_close"
            p = a.get("best_price") or a.get("price")   # graded at the best price available across books at alert time
            a["units_flat"] = round((1 - p) / p, 2) if (r == "W" and p) else (-1.0 if r == "L" else 0.0)
            fp = eff_cost(a["book"], a.get("fade_price")) if a.get("fade_price") else None
            if fp and 0 < fp < 1 and r in ("W", "L", "P"):   # paper: betting AGAINST the print, after the book's fee
                a["fade_units"] = -1.0 if r == "W" else (round((1 - fp) / fp, 2) if r == "L" else 0.0)
            a["settled_utc"] = n.strftime("%Y-%m-%dT%H:%M:%SZ")


def tg_mirror(text, html=False):
    """Oct 27 (Peter): every ntfy push is mirrored to Telegram (@sharp_fills_bot) so all alerts land in one place.
    Secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID; missing or failing = silently skipped. ntfy is unchanged and always
    fires first. Nothing is printed to the public log."""
    tok, chat = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip(), (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not tok or not chat:
        return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=json.dumps(dict({"chat_id": chat, "text": text[:3500]},
                                                          **({"parse_mode": "HTML"} if html else {}))).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        print("telegram mirror failed")


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


LIQ_BOOK_NAME = {"kalshi": "Kalshi", "polymarket": "Polymarket", "novig": "Novig", "prophetx": "ProphetX"}


def notify(title, body, headline=None):
    if not NTFY_TOPIC:
        return
    try:
        hdr = {"Title": title.encode("ascii", "ignore").decode(), "Tags": "droplet"}
        if headline:
            hdr["Markdown"] = "yes"
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=((f"**{headline}**\n" if headline else "") + body).encode(),
                                     method="POST", headers=hdr)
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as ex:
        print(f"ntfy failed: {ex}")
    if headline:
        tg_mirror(f"<b>{_esc(headline)}</b>\n\U0001F4A7 {_esc(title)}\n{_esc(body)}", html=True)
    else:
        tg_mirror(f"\U0001F4A7 {title}\n{body}")


# ---------------------------------------------------------------- main
def merge_kalshi_ml(rows):
    """Kalshi lists one market per team. Team A's side = YES on A's market + NO on B's market; combine per game."""
    keep, groups = [], {}
    for r in rows:
        if r["book"] == "kalshi" and r["market"] == "moneyline" and r["side"] in (0, 1) and r.get("event"):
            groups.setdefault((r["event"], r["side"]), []).append(r)
        else:
            keep.append(r)
    for (ev, side), rs in groups.items():
        opp = groups.get((ev, 1 - side), [])
        yes = [r for r in rs if r["ref"]["kalshi_side"] == "yes"] or rs
        base = dict(yes[0])
        base["depth"] = sum(r["depth"] for r in rs)
        base["other_depth"] = sum(r["depth"] for r in opp)
        base["total_depth"] = sum(r.get("total_depth", r["depth"]) for r in rs)
        base["other_total"] = sum(r.get("total_depth", r["depth"]) for r in opp)
        bbs = [r["best_bid"] for r in rs if r.get("best_bid") is not None]
        base["best_bid"] = max(bbs) if bbs else None
        prices = [r["price"] for r in rs if r["price"] is not None]
        base["price"] = min(prices) if prices else None   # cheapest way to buy this team
        base["side_label"] = base["teams"][side] if base.get("teams") else base["side_label"]
        keep.append(base)
    return keep


def main_line_only(rows):
    """Spreads/totals: if several strikes of the same book+game+market are in band, keep only the one closest to 50c."""
    groups, out = {}, []
    for r in rows:
        if r["market"] in ("spread", "total") and r.get("mid"):
            groups.setdefault((r["book"], r["game"], r["market"]), {}).setdefault(r["mid"], []).append(r)
        else:
            out.append(r)
    for mids in groups.values():
        best = min(mids.values(), key=lambda rs: min(abs((x["price"] if x["price"] is not None else 0) - 0.5) for x in rs))
        out += best
    return out


def in_band(r):
    if r["price"] is None:
        return False
    lo, hi = BAND_ML if r["market"] == "moneyline" else BAND_LINE
    return lo <= r["price"] <= hi


def row_key(r):
    if r["book"] == "kalshi" and r["market"] == "moneyline" and r.get("event"):
        return f"kalshi|{r['event']}|ml|{r['side']}"
    return f"{r['book']}|{json.dumps(r['ref'], sort_keys=True)}"


SHARP_FILE = os.environ.get("SHARP_ALERTS", "") or "alerts.json"   # the sharp-monitor's feed, same repo
CONFIRM_KEEP = 0.75    # a pending alert confirms only if >= 75% of the new money is still there on the next check
PULLED_KEEP = 0.25     # after alerting, if < 25% of the new money remains before the game, mark it pulled
PENDING_MAX_MIN = 30


def matches(r, rows, check_line=True):
    """Rows on any book (including r's own) for the same game, market, side and line as r."""
    out = []
    for o in rows:
        if o["market"] != r["market"]:
            continue
        if o is r:
            out.append(o)
            continue
        how = same_game(r, o)
        if how and same_side(r, o, how, check_line=check_line):
            out.append(o)
    return out


def best_across(r, rows):
    """Cheapest cost to buy r's side (same game/market/side/line) across every book read, AFTER fees: (price, book)."""
    best = None
    for o in matches(r, rows):
        e = eff_cost(o["book"], o["price"])
        if e is not None and (best is None or e < best[0]):
            best = (e, o["book"])
    return best or (eff_cost(r["book"], r["price"]), r["book"])


def opposite(o, rows):
    """The other side of the same market on the same book (for a fair mid price)."""
    for x in rows:
        same_mkt = x.get("mid") == o.get("mid") or (x["book"] == "kalshi" and x["market"] == "moneyline")   # Kalshi ML: merged per game
        if x is not o and x["book"] == o["book"] and same_mkt and x["market"] == o["market"] \
                and x.get("event", x["game"]) == o.get("event", o["game"]) and x["side"] != o["side"]:
            return x
    return None


def price_rule(r, rows, best_price):
    if r["market"] in ("spread", "total"):
        am = american(best_price)
        return "fails_cap" if (am is not None and am < -130) else "ok"
    fair = []
    for o in matches(r, rows):
        opp = opposite(o, rows)
        if o["price"] is not None and opp is not None and opp["price"] is not None:
            fair.append((o["price"] + 1 - opp["price"]) / 2)   # mid of buy-this-side and 1 - buy-other-side
    if not fair or not best_price:
        return "ml_edge_unknown"
    edge = (sum(fair) / len(fair)) / best_price - 1
    return "ml_edge_ok" if edge >= 0.02 else "ml_edge_fail"


_ODDS = {}


def odds_prices(r):
    """Sportsbook prices for r's side from The Odds API (us + us_ex), read-only. {} when no key or no match."""
    sport, mkt = ODDS_SPORT.get(r["league"]), ODDS_MKT.get(r["market"])
    if not ODDS_KEY or not sport or not mkt:
        return {}
    ck = (sport, mkt)
    if ck not in _ODDS:
        try:
            _ODDS[ck] = get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                            {"apiKey": ODDS_KEY, "regions": "us,us_ex", "markets": mkt, "oddsFormat": "american"})
        except Exception as ex:
            print(f"Odds API failed ({sport} {mkt}): {ex}")
            _ODDS[ck] = []
    out = {}
    for ev in _ODDS[ck] or []:
        try:
            d = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).astimezone(ET).date().isoformat()
        except Exception:
            continue
        erow = {"league": r["league"], "date": d, "teams": [ev.get("away_team", ""), ev.get("home_team", "")]}
        how = same_game(r, erow)
        if not how:
            continue
        for bk in ev.get("bookmakers", []):
            for m in bk.get("markets", []):
                for o in m.get("outcomes", []):
                    name, pt = o.get("name", ""), o.get("point")
                    if r["market"] == "total":
                        side = "OVER" if name.lower() == "over" else ("UNDER" if name.lower() == "under" else None)
                    else:
                        side = team_side(name, erow["teams"], r["league"])
                    if side is None:
                        continue
                    orow = {"market": r["market"], "side": side, "line": pt}
                    if same_side(r, orow, how, check_line=False):
                        out[bk["key"]] = {"price": o.get("price"), "point": pt}
        break
    return out


START_PRIORITY = {"odds": -1, "polymarket": 0, "prophetx": 1, "novig": 2, "kalshi": 9}   # Kalshi's time field is not the tip-off


def odds_start_rows(leagues):
    """Oct 28 (forensic): the scheduled start of every game from The Odds API /events (a FREE endpoint: no credits),
    used as the first start source. Kalshi-only games carried Kalshi's time field (not the tip-off, often hours late),
    so the 'pregame' close kept reading the game live (closes of 1c/99c). NBA/NHL :10/:40 tips are moved back 10 min
    to the listed time, the same rule as the sharp monitor."""
    out = []
    if not ODDS_KEY:
        return out
    for lg in sorted(set(leagues)):
        sport = ODDS_SPORT.get(lg)
        if not sport:
            continue
        try:
            evs = get(f"https://api.the-odds-api.com/v4/sports/{sport}/events", {"apiKey": ODDS_KEY}) or []
        except Exception as ex:
            print(f"Odds API events failed ({lg}): {str(ex)[:60]}")
            continue
        for ev in evs:
            try:
                t = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
            except Exception:
                continue
            if lg in ("NBA", "NHL") and t.minute in (10, 40) and t.second == 0:
                t -= timedelta(minutes=10)
            out.append({"league": lg, "date": t.astimezone(ET).date().isoformat(), "book": "odds", "start": t.timestamp(),
                        "teams": [ev.get("away_team", ""), ev.get("home_team", "")], "_odds": True})
    return out


def fill_starts(rows, extra=()):
    """One start time per game across all books: take it from the most reliable book that lists the game
    (Polymarket gameStartTime, then ProphetX scheduled, then Novig, Kalshi only if nothing else). Lead-time buckets
    are computed from this, so every book's entry for a game carries the same start."""
    groups = {}
    for r in list(rows) + list(extra):
        groups.setdefault((r.get("league"), r.get("date")), []).append(r)
    for grp in groups.values():
        clusters = []   # [[rows of one game]]
        for r in grp:
            for c in clusters:
                if r.get("teams") and c[0].get("teams") and same_game(r, c[0]):
                    c.append(r)
                    break
            else:
                clusters.append([r])
        for c in clusters:
            src = sorted((x for x in c if x.get("start")), key=lambda x: START_PRIORITY.get(x["book"], 5))
            if not src:
                continue
            st, book = src[0]["start"], src[0]["book"]
            earliest = min(x["start"] for x in src)   # Oct 28: the EARLIEST start any book lists closes the pregame window
            for x in c:
                x["start"], x["start_source"] = st, book
                x["start_min"] = earliest


GAP_BOOKS = ("kalshi", "novig", "prophetx")   # executable exchanges this monitor reads (Polymarket here is the global book)
GAP_MIN = float(os.environ.get("LIQ_GAP_MIN", "") or "0.005")   # log when both sides cost < $1 - 0.5c after fees


def find_gaps(rows, n):
    """PAPER: same game/market/line, opposite sides on two different exchanges, total cost after fees under $1
    (buying both locks a profit if both fill). Logged to gaps.json for measurement only - never alerted or bet."""
    groups = {}
    for r in rows:
        if r.get("book") in GAP_BOOKS and r.get("teams") and r.get("side") is not None and r.get("price") \
                and 0 < r["price"] < 1:
            groups.setdefault((r["league"], r["date"], r["market"]), []).append(r)
    out = []
    for (lg, d, mkt), rs in groups.items():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a["book"] == b["book"]:
                    continue
                how = same_game(a, b)
                if not how:
                    continue
                if mkt == "total":
                    opp = a["side"] != b["side"] and a.get("line") is not None and a.get("line") == b.get("line")
                elif mkt == "spread":
                    opp = (not same_side(a, b, how, check_line=False) and a.get("line") is not None
                           and b.get("line") is not None and abs(a["line"] + b["line"]) < 1e-9)
                else:
                    opp = not same_side(a, b, how, check_line=False)
                if not opp:
                    continue
                ca, cb = eff_cost(a["book"], a["price"]), eff_cost(b["book"], b["price"])
                tot = ca + cb
                if tot < 1 - GAP_MIN:
                    out.append({"seen_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ"), "league": lg, "game": a.get("game"),
                                "market": mkt, "line": a.get("line"), "edge_pct": round(100 * (1 - tot) / tot, 2),
                                "total_cost": round(tot, 4),
                                "size_est": round(min(a.get("other_depth") or 0, b.get("other_depth") or 0)),
                                "legs": [{"book": x["book"], "side": x.get("side_label"), "price": x["price"],
                                          "cost_after_fee": c} for x, c in ((a, ca), (b, cb))]})
    return out


def save_gaps(new, n):
    """Oct 26 (Muse): one entry per game/market/line/books while the gap stays open. Each later scan that still sees it
    updates last_seen_utc / scans_seen, so lifetime_min = how long it lived (resolution = the scan interval).
    scan_sec = seconds from this run's start to the save: both legs were read inside that window (not the same instant),
    so it bounds how far apart the two legs' snapshots can be. size_est stays an upper bound."""
    path = os.path.join(OUT_DIR, "gaps.json")
    try:
        with open(path) as f:
            old = json.load(f).get("gaps") or []
    except Exception:
        old = []
    ts = n.strftime("%Y-%m-%dT%H:%M:%SZ")
    cut = (n - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    gap_open = (n - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")   # seen within 30 min = the same gap still open
    keyf = lambda g: (g["game"], g["market"], g["line"], tuple(sorted(x["book"] for x in g["legs"])))
    live = {}
    for g in old:
        g.setdefault("first_seen_utc", g.get("seen_utc"))
        g.setdefault("last_seen_utc", g.get("seen_utc"))
        g.setdefault("scans_seen", 1)
        if g["last_seen_utc"] >= gap_open:
            live[keyf(g)] = g
    scan_sec = round(time.time() - RUN_T0)
    added = 0
    for g in new:
        k = keyf(g)
        if k in live:
            o = live[k]
            o["last_seen_utc"], o["scans_seen"] = ts, o["scans_seen"] + 1
            o["max_edge_pct"] = max(o.get("max_edge_pct", o["edge_pct"]), g["edge_pct"])
            o["last_edge_pct"], o["last_size_est"] = g["edge_pct"], g["size_est"]
        else:
            g.update(first_seen_utc=ts, last_seen_utc=ts, scans_seen=1, max_edge_pct=g["edge_pct"], scan_sec=scan_sec)
            old.append(g)
            live[k] = g
            added += 1
    for g in old:
        try:
            g["lifetime_min"] = round((datetime.fromisoformat(g["last_seen_utc"].replace("Z", "+00:00"))
                                       - datetime.fromisoformat(g["first_seen_utc"].replace("Z", "+00:00"))).total_seconds() / 60)
        except Exception:
            pass
    keep = [g for g in old if g["last_seen_utc"] >= cut]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"note": "PAPER ONLY (Oct 25; persistence added Oct 26): opposite sides of the same game/market/line on two "
                           "different exchanges whose combined cost after fees is under $1 (Kalshi/Novig/ProphetX; Polymarket "
                           "here is the global book, excluded). edge_pct = locked profit per $ staked at first sight; "
                           "max/last_edge_pct while open. size_est = smaller leg's near-price depth (UPPER BOUND). "
                           "first/last_seen_utc, scans_seen, lifetime_min = how long the gap stayed open (scan-interval "
                           "resolution; a 1-scan gap may be a feed artifact). scan_sec = seconds from run start to this save, "
                           "the most the two legs' reads can be apart. Measurement only: never alerted, never bet.", "gaps": keep},
                  f, indent=1)
    return added


def sharp_alerts(n):
    """Recent Pinnacle-move alerts from the sharp-monitor (alerts.json in this repo), as comparable rows."""
    try:
        d = load(SHARP_FILE, {})
        items = d.get("all_alerts") or d.get("alerts") or []
    except Exception:
        return []
    out = []
    for x in items:
        try:
            st = datetime.fromisoformat(x["start_utc"].replace("Z", "+00:00"))
        except Exception:
            continue
        if st < n - timedelta(hours=6) or st > n + timedelta(days=2):
            continue
        bet = x.get("bet", "")
        teams = split_teams(x.get("game", ""))
        if bet.startswith(("Over", "Under")):
            market, side = "total", ("OVER" if bet.startswith("Over") else "UNDER")
        elif " ML " in bet:
            market, side = "moneyline", (team_side(bet.split(" ML ")[0], teams, x.get("sport")) if teams else None)
        elif re.search(r" (PL|RL) ", bet):
            continue
        else:
            m = re.match(r"^(.*?) [+-]?\d", bet)
            market, side = "spread", (team_side(m.group(1), teams, x.get("sport")) if (m and teams) else None)
        if side is None:
            continue
        out.append(dict(league=x.get("sport"), date=st.astimezone(ET).date().isoformat(), teams=list(teams) if teams else None,
                        market=market, side=side, bet=bet, book="sharp"))
    return out


def sharp_view(r, sharp):
    agree, oppose = [], []
    for x in sharp:
        team_mkts = ("spread", "moneyline")
        if not (x["market"] == r["market"] or (x["market"] in team_mkts and r["market"] in team_mkts)):
            continue  # a team's spread and moneyline point the same way; totals only match totals
        how = same_game(r, x)
        if not how:
            continue
        (agree if same_side(r, x, how, check_line=False) else oppose).append(x["bet"])
    return agree, oppose


_T25 = {}
_NORM = {"st": "state", "st.": "state"}


def _words(x):
    return [_NORM.get(w, w) for w in re.findall(r"[a-z0-9&.]+", (x or "").lower().replace("(", " ").replace(")", " "))]


def top25_names():
    """[(location words, nickname words)] from ESPN's AP poll, once per run."""
    if "v" in _T25:
        return _T25["v"]
    names = None
    try:
        d = get("https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings")
        polls = d.get("rankings", [])
        ap = next((p for p in polls if "ap" in (p.get("name", "") + " " + p.get("type", "")).lower().split()), polls[0] if polls else None)
        names = [(_words((t.get("team") or {}).get("location")), _words((t.get("team") or {}).get("name")))
                 for t in (ap or {}).get("ranks", [])] or None
    except Exception as ex:
        print(f"Top 25 fetch failed: {ex}")
    _T25["v"] = names
    return names


def is_top25(r):
    """True only on a full school match: 'Michigan' or 'Michigan Wolverines' matches Michigan, 'Michigan State' does not.
    None when it can't tell (no poll, or a nickname-only name like 'Tigers')."""
    names = top25_names()
    if not names or not r.get("teams"):
        return None
    unsure = False
    for t in r["teams"]:
        tw = [w.rstrip(".") for w in _words(t)]
        for loc, nick in names:
            loc = [w.rstrip(".") for w in loc]
            nick = [w.rstrip(".") for w in nick]
            if tw == loc or tw == loc + nick:
                return True
            if nick and tw == nick:
                unsure = True
    return None if unsure else False


def fmt_clv(a):
    v = a.get("clv_cents")
    return f"{v:+.1f}c" if v is not None else ""


def write_page(alerts, n, stats):
    """liquidity/README.md: a readable table GitHub shows as a web page at github.com/<repo>/tree/main/liquidity."""
    def money(x):
        return f"${x/1000:,.0f}k" if x is not None else ""
    lines = ["# Liquidity alerts (paper)", "",
             f"Updated {n.astimezone(ET).strftime('%a %b %-d, %-I:%M %p ET')}. {stats}", "",
             "New money ($25k+, 10% of the side, capped at $100k) that stayed on the next check. "
             "**Rule** = a second book has $10k+ on the same side and line. **Sharp** = a sharp-monitor alert agrees. "
             "**CLV** = cents the exchange price moved toward this side before the game.", ""]
    for a in alerts:   # Oct 25 regrade: resulted plays that never had a real pregame close read (in-game reads)
        if a.get("result") in ("W", "L", "P") and a.get("close_price") is None:
            a["artifact"] = "no_pregame_close"
    graded = [a for a in alerts if a.get("result") in ("W", "L", "P") and not a.get("artifact")]
    if graded:
        w = sum(1 for a in graded if a["result"] == "W"); l = sum(1 for a in graded if a["result"] == "L")
        u = sum(a.get("units_flat") or 0 for a in graded)
        rm = [a for a in graded if a.get("rule_met")]
        lines += [f"**Record:** {w}-{l} ({u:+.2f}u flat)" + (f" | rule met: {sum(1 for a in rm if a['result']=='W')}-"
                  f"{sum(1 for a in rm if a['result']=='L')}" if rm else ""), ""]
    fd = [a for a in graded if a.get("fade_units") is not None]
    if fd:
        lines += [f"**Fade (paper, betting against the print):** {sum(1 for a in fd if a['fade_units'] > 0)}-"
                  f"{sum(1 for a in fd if a['fade_units'] < 0)} ({sum(a['fade_units'] for a in fd):+.2f}u flat, after fees)", ""]
    lines += ["| Logged (ET) | League | Game | Bet | Book | New $ | Price | Rule | Sharp | CLV | Pulled | Result |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in alerts[:200]:
        t = datetime.fromisoformat(a["alerted_utc"].replace("Z", "+00:00")).astimezone(ET).strftime("%b %-d %-I:%M%p")
        nb = ((a.get("depth_by_book") or {}).get(a["book"]) or {}).get("new_this_side")
        pa = a.get("price_american")
        lines.append(f"| {t} | {a['league']} | {a['game']} | {a['market']}: {a['side_label']} | {a['book']} | {money(nb)} | "
                     f"{(f'{pa:+d}' if pa else '')} | {'✅ ' + ','.join(a['second_book']) if a.get('rule_met') else ''} | "
                     f"{'✅' if a.get('sharp_agree') else ('❌' if a.get('sharp_oppose') else '')} | "
                     f"{fmt_clv(a)} | "
                     f"{'yes' if a.get('pulled') else ''} | {a.get('result') or 'pending'} |")
    if not alerts:
        lines.append("| | | No alerts yet | | | | | | | | | |")
    save_text(os.path.join(OUT_DIR, "README.md"), "\n".join(lines) + "\n")


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def run():
    n = now_utc()
    now_s = n.timestamp()
    today = n.astimezone(ET).date()
    days = {today, today + timedelta(days=1)}
    state = load(STATE_FILE, None)
    doc = load(ALERTS_FILE, {"alerts": []})
    alerts = doc.get("alerts", [])
    if state is None:
        # unreadable state (e.g. damaged by a save collision): KEEP the alert record, rebuild baselines and dedupe keys
        print("State file unreadable: keeping the alert record, rebuilding baselines")
        state = {"v": doc.get("v", STATE_VERSION),
                 "alerted": {a["key"]: a["alerted_utc"] for a in alerts if a.get("key")}}
    if state.get("v") != STATE_VERSION:   # older rules logged standing market-maker size: start the record clean
        print(f"New rules (v{STATE_VERSION}): clearing old alerts and state")
        state, alerts = {"v": STATE_VERSION}, []
    for k in ("alerted", "seen", "pending"):
        state.setdefault(k, {})
    settle(alerts, n)
    for a in alerts:   # Oct 25 regrade: resulted plays that never had a real pregame close read are kept out of records
        if a.get("result") in ("W", "L", "P") and a.get("close_price") is None:
            a["artifact"] = "no_pregame_close"
    for a in alerts:   # Oct 28 (fix list #3): second_book is always a list; the old string values move to second_book_status
        sb = a.get("second_book")
        if isinstance(sb, str):
            a["second_book_status"], a["second_book"] = sb, []
        elif isinstance(sb, list) and "second_book_status" not in a:
            a["second_book_status"] = "ok" if sb else "no_match"
    for a in alerts:   # Oct 28 (forensic): a close at an in-game extreme (<= 3c / >= 97c) was read live, not pregame:
        # flag it so CLV cuts can exclude it (W/L and units are graded from settlement and stay valid)
        cp = a.get("close_price")
        if cp is not None and (cp <= 0.03 or cp >= 0.97) and not (a.get("price") and (a["price"] <= 0.05 or a["price"] >= 0.95)):
            a["close_suspect"] = "in_game_extreme"

    rows = []
    if "kalshi" in BOOKS:
        rows += kalshi_rows(days)
    if "novig" in BOOKS:
        rows += novig_rows(days, n)
    if "polymarket" in BOOKS:
        rows += pm_rows(days, n)
    if "prophetx" in BOOKS:
        rows += px_rows(days, n)
    rows = merge_kalshi_ml(rows)
    fill_starts(rows, odds_start_rows({r.get("league") for r in rows if r.get("league")}))
    all_by_key = {row_key(r): r for r in rows}                  # every side (for closing price / pulled checks)
    pre = {k: r for k, r in all_by_key.items()
           if (min(r["start"], r.get("start_min") or r["start"]) > now_s if r.get("start")
               else r.get("league") not in PAPER_ONLY)}   # pregame only (tennis: start must be known; Oct 28: earliest start)
    by_key = {row_key(r): r for r in main_line_only([r for r in pre.values() if in_band(r)])}   # main lines (for new triggers)
    print(f"Rows: {len(rows)} sides; {len(by_key)} pregame main-line sides")

    pre_rows = list(pre.values())
    try:
        print(f"Price gaps (paper): {save_gaps(find_gaps(pre_rows, n), n)} new")   # count only
    except Exception as ex:
        print(f"gap scan failed: {str(ex)[:80]}")

    # --- open alerts: closing price (last pregame price), pulled money, 15-minute actionability
    for a in alerts:
        r = pre.get(a.get("key"))
        if a.get("result") is not None or not r:
            continue
        a_start = a.get("start_utc")
        started = bool(a_start) and datetime.fromisoformat(a_start.replace("Z", "+00:00")).timestamp() <= now_s
        if r["price"] is not None and 0.03 < r["price"] < 0.97 and not started and not a.get("close_frozen"):
            # Oct 25: a side with NO offers left = game already live (wrong/late start time): keep the last real close.
            # Oct 28 (forensic): never take a close at/after the alert's own start or at an in-game extreme (3c/97c):
            # closes of 0.01/0.99 showed games read live when one book listed a late start.
            a["close_price"] = r["price"]
            a["clv_cents"] = round(100 * (r["price"] - a["price"]), 1) if a.get("price") else None
        elif a.get("close_price") is not None:
            a["close_frozen"] = True
        base, new = a.get("base_depth"), a.get("new_money")
        tot = r.get("total_depth", r["depth"])
        if base is not None and new and not a.get("pulled") and tot < base + PULLED_KEEP * new:
            a["pulled"] = True
            a["pulled_utc"] = n.strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"PULLED {a['game']} | {a['side_label']} ({a['book']}): now ${tot:,.0f} vs ${base + new:,.0f} at alert")
        age_m = (now_s - datetime.fromisoformat(a["alerted_utc"].replace("Z", "+00:00")).timestamp()) / 60
        if "price_after_15m" not in a and age_m >= 15:
            bp, bb = best_across(r, pre_rows)
            a["price_after_15m"], a["price_after_15m_book"] = bp, bb
            a["still_actionable"] = (bp is not None and a.get("best_price") is not None and bp <= a["best_price"] + 1e-9)

    # --- new money since the last reading, on TOTAL side depth (all levels): a 1c move in the best bid can pull a
    # standing market-maker wall into the near-price window, so near depth would show phantom new money.
    prev = state["seen"]
    for k, r in by_key.items():
        p = prev.get(k)
        fresh = p and now_s - p["t"] <= FRESH_MIN * 60
        r["tot"] = r.get("total_depth", r["depth"])
        r["otot"] = r.get("other_total", r["other_depth"])
        r["delta"] = (r["tot"] - p["d"]) if fresh else None
        r["other_delta"] = (r["otot"] - p["o"]) if fresh else None
        r["prev_depth"] = p["d"] if fresh else None
        r["prev_bid"] = p.get("b") if fresh else None
        r["prev_nd"] = p.get("nd") if fresh else None
    state["seen"] = {k: {"d": round(r["tot"]), "o": round(r["otot"]), "t": now_s, "b": r.get("best_bid"),
                         "nd": round(r["delta"]) if r["delta"] is not None else None} for k, r in by_key.items()}

    def improved(now_bid, then_bid):
        return None if (now_bid is None or then_bid is None) else now_bid > then_bid + 1e-9

    sharp = sharp_alerts(n)
    fired = dropped = 0

    # --- confirm pending signals from the last check (spoof filter: the money has to still be there)
    for key, pd in list(state["pending"].items()):
        r = by_key.get(key)
        age = (now_s - pd["t"]) / 60
        if not r or key in state["alerted"]:
            if age > PENDING_MAX_MIN or key in state["alerted"]:
                state["pending"].pop(key, None)
                if key not in state["alerted"]:
                    dropped += 1
            continue
        if age < 2:
            continue  # same run / too soon to judge
        state["pending"].pop(key, None)
        if age > PENDING_MAX_MIN:
            dropped += 1
            print(f"Not confirmed (pending > {PENDING_MAX_MIN} min, dropped): {r['game']} | {r['side_label']} ({r['book']})")
            continue
        if r["tot"] < pd["base"] + CONFIRM_KEEP * pd["new"] or r["tot"] <= r["otot"]:
            dropped += 1
            print(f"Not confirmed (money pulled or side no longer heavier): {r['game']} | {r['side_label']} ({r['book']})")
            continue
        others = {}
        for o in by_key.values():
            if o["book"] == r["book"] or o["market"] != r["market"]:
                continue
            how = same_game(r, o)
            if how and same_side(r, o, how) and o["depth"] > others.get(o["book"], {}).get("depth", -1):
                others[o["book"]] = {"depth": round(o["depth"]), "price": o["price"], "label": o["side_label"],
                                     "heavier": o["depth"] > o["other_depth"],
                                     "fresh": max(o.get("delta") or 0, o.get("prev_nd") or 0) >= SECOND_MIN}
        second = {b: v for b, v in others.items() if v["depth"] >= SECOND_MIN and v.get("heavier")}
        agree, oppose = sharp_view(r, sharp)
        bp, bpb = best_across(r, pre_rows)
        a = {
            "alerted_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ"), "first_seen_utc": pd["first_utc"], "confirmed_after_min": round(age),
            "key": key, "book": r["book"], "league": r["league"], "date": r["date"], "game": r["game"],
            "start_utc": datetime.fromtimestamp(r["start"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if r.get("start") else None,
            "start_source": r.get("start_source"),
            "market": r["market"], "side": side_key(r), "side_label": r["side_label"], "line": r.get("line"),
            "teams": r.get("teams"),
            "price": r["price"], "price_american": american(r["price"]), "price_when_first_seen": pd["price"],
            "base_depth": pd["base"], "new_money": pd["new"],
            "depth_by_book": dict({r["book"]: {"this_side": round(r["depth"]), "other_side": round(r["other_depth"]),
                                                 "this_side_all_levels": round(r["tot"]), "other_side_all_levels": round(r["otot"]),
                                                 "ratio": round(r["depth"] / max(r["other_depth"], 1), 1),
                                                 "new_this_side": pd["new"], "new_other_side": pd["new_other"]}},
                                  **{b: {"this_side": v["depth"], "label": v["label"], "price": v["price"], "heavier_side": v["heavier"]}
                                     for b, v in others.items()}),
            "second_book": sorted(second) if second else [],   # Oct 28: always a list (fix list #3)
            "second_book_status": "ok" if second else ("none_10k" if others else "no_match"),
            "rule_met": bool(second), "sharp_agree": agree, "sharp_oppose": oppose,
            "top25": is_top25(r) if r["league"] == "NCAAF" else None,
            "books_live": BOOKS, "ref": r["ref"], "pulled": False, "close_price": r["price"], "clv_cents": 0.0,
            "bid_improved_at_pending": pd.get("bid_improved"), "bid_improved": improved(r.get("best_bid"), pd.get("bb")),
            "best_price": bp, "best_price_book": bpb, "best_price_american": american(bp),
            # Oct 25 paper column: the OTHER side's cost on the same book at alert time (= 1 - best bid on this side)
            "fade_price": round(1 - r["best_bid"], 4) if r.get("best_bid") else None,
            "prices_by_book": odds_prices(r),
            "second_book_fresh": any(v.get("fresh") for v in second.values()),
            "lead_min": round((r["start"] - now_s) / 60) if r.get("start") else None,
            "price_rule": price_rule(r, pre_rows, bp),
            "result": None, "units_flat": None,
            "paper_only": r["league"] in PAPER_ONLY,
        }
        alerts.insert(0, a)
        state["alerted"][key] = a["alerted_utc"]
        fired += 1
        print(f"ALERT {a['league']} {a['game']} | {a['market']} {a['side_label']} | {r['book']} +${pd['new']:,.0f} new, held "
              f"{round(age)}m (now ${r['tot']:,.0f}) | 2nd: {a['second_book']} | sharp agree: {len(agree)} oppose: {len(oppose)}"
              f" | best {bp} on {bpb} | {a['price_rule']}")
        if r["league"] not in PAPER_ONLY:   # tennis never pushes, whatever the topic setting
            notify(f"Liquidity {a['league']}" + (" RULE MET" if a["rule_met"] else "") + (" + SHARP" if agree else ""),
                   f"{a['side_label']} ({a['market']}) on {r['book']}\n{a['game']}\n"
                   f"+${pd['new']:,.0f} new bids, still there after {round(age)}m; now ${r['tot']:,.0f} vs ${r['otot']:,.0f}\n"
                   + (f"Price {r['price']:.2f} ({a['price_american']:+d})\n" if a['price_american'] else "")
                   + "2nd book: " + (", ".join(f"{b} ${v['depth']:,}" for b, v in others.items()) or "no match")
                   + (f"\nSharp alert agrees: {', '.join(agree)}" if agree else ""),
                   headline=f"{a['game']} \u2014 {a['side_label']}"
                            + (f" ({a['price_american']:+d})" if a.get('price_american') else "")
                            + f" @ {LIQ_BOOK_NAME.get(r['book'], r['book'])}")

    # --- new signals -> pending (confirmed or dropped on the next check)
    for key, r in by_key.items():
        if r["delta"] is None or key in state["alerted"] or key in state["pending"]:
            continue
        if r["book"] in CONFIRM_ONLY_BOOKS:
            continue  # confirming book only: counts as a second book and for best price, never starts an alert
        need = min(max(PRIMARY_MIN, REL_MIN * r["prev_depth"]), NEED_CAP)
        if r["delta"] < need:
            continue  # need $25k+ of NEW bids, and >= 10% of what was already there (scales with the book)
        if r["delta"] < RATIO * max(r["other_delta"] or 0, 0):
            continue  # both sides growing together = market making
        if r["tot"] <= r["otot"]:
            continue  # this side must now be the heavier one
        bi = improved(r.get("best_bid"), r.get("prev_bid"))
        state["pending"][key] = {"t": now_s, "first_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ"), "base": round(r["prev_depth"]),
                                 "new": round(r["delta"]), "new_other": round(r["other_delta"] or 0), "price": r["price"],
                                 "bb": r.get("best_bid"), "bid_improved": bi}
        print(f"Pending (confirm next check): {r['game']} | {r['side_label']} ({r['book']}) +${r['delta']:,.0f}"
              f" | bid improved: {bi}")

    cutoff = (n - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    alerts = [a for a in alerts if a["alerted_utc"] >= cutoff]
    state["alerted"] = {k: v for k, v in state["alerted"].items() if v >= cutoff}
    state["v"] = STATE_VERSION
    try:
        update_alert_times(alerts, n)
    except Exception as ex:
        print(f"alert_times update failed: {str(ex)[:80]}")
    save(ALERTS_FILE, {"note": (
        "Liquidity paper alerts (Kalshi + Novig + Polymarket public books; ProphetX read-only key, a trigger book from Oct 24), newest first. Trigger: >= $%d (and >= 10%% of the "
        "side's prior size, capped at $100k) of NEW bids on one side since the last check, measured on total side depth (all price "
        "levels; near-price depth within %.0fc is shown and used for the second-book test), >= %gx any new money on the "
        "other side, leaving that side heavier; main lines only (ML 15-85c, spread/total 30-70c), pregame; Kalshi moneylines "
        "combined per game. Spoof filter: logged only if >= 75%% of the new money is still there on the next check "
        "(confirmed_after_min). pulled = the new money later disappeared before the game. rule_met = another book has >= $%d on "
        "the same side and it is the heavier side there. sharp_agree/sharp_oppose = sharp-monitor (Pinnacle move) alerts on the "
        "same game & market. price = cost to buy the side when logged (0-1); close_price = last pregame price; clv_cents = "
        "close_price - price (positive = the market moved toward this side). result W/L/P/VOID from the exchange's settlement; "
        "units_flat = 1u at best_price (cheapest across books at alert). "
        "artifact = 'no_pregame_close': the play never got a real pregame close read (reads continued after a wrong/late "
        "start time); EXCLUDE these from every record (Oct 25 regrade; from then on, a read with no offers keeps the last "
        "real close and sets close_frozen). Log-only fields: bid_improved (best bid on the alert side "
        "rose between readings), best_price/best_price_book, prices_by_book (Odds API sportsbooks), second_book_fresh (second book "
        "added >= $10k on the side in the last two checks), lead_min, price_rule (fails_cap = worse than -130 on spread/total; "
        "ml_edge_ok/fail = 2%% edge vs cross-book fair mid), price_after_15m/still_actionable. Leagues: NFL, NCAAF, NBA, NHL, "
        "plus MLB and NCAAB (added Oct 23, same rules; read after the original leagues with leftover capacity) and TENNIS "
        "(ATP/WTA match winner, paper_only = true: data collection only, never pushed, not a betting lane; graded only from "
        "Kalshi/Polymarket settlement)." % (PRIMARY_MIN, NEAR * 100, RATIO, SECOND_MIN)),
        "v": STATE_VERSION, "alerts": alerts})
    save(STATE_FILE, state)
    stats = (f"This run: {fired} new, {dropped} not confirmed, {len(state['pending'])} pending. "
             f"Open alerts: {sum(1 for a in alerts if a['result'] is None)}.")
    write_page(alerts, n, stats)
    print(f"Done. New alerts: {fired}. Not confirmed: {dropped}. Pending: {len(state['pending'])}. "
          f"Open alerts: {sum(1 for a in alerts if a['result'] is None)}. Total run: {time.time() - RUN_T0:.0f}s")


if __name__ == "__main__":
    try:
        run()
    except Exception as ex:
        print(f"Run failed: {ex}")
        sys.exit(1)
