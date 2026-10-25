#!/usr/bin/env python3
"""
Sharp line-move monitor.

Polls The Odds API, watches the sharp book (Pinnacle by default), and pushes an
alert to your phone (via ntfy.sh) when the sharp line moves meaningfully AND at
least one retail book still offers the old (better) number. If every retail
book has already moved, no alert is sent -- you only hear about bettable spots.

Standard library only. Configure with environment variables (see README).
"""
import json
import math
import os
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
API = "https://api.the-odds-api.com/v4"

KEY = os.environ.get("ODDS_API_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
SHARP = os.environ.get("SHARP_BOOK", "") or "pinnacle"
# Books you can actually bet. Sharp book + these must stay <= 10 to cost 1 credit per market.
RETAIL = [b.strip() for b in (os.environ.get("RETAIL_BOOKS", "") or
    "hardrockbet_fl,prophetx,novig,kalshi,polymarket,betmgm,fanduel,draftkings"
).split(",") if b.strip()]
# Second sharp-leaning book that must agree with the sharp move ("none" to turn off).
# CONFIRM_BOOK may list several, comma separated: a sharp move is confirmed when at least as many of them
# agree as disagree (books with no line are ignored).
_cb = os.environ.get("CONFIRM_BOOK", "") or "betonlineag,matchbook,betfair_ex_eu,smarkets"
CONFIRMS = [] if _cb.strip().lower() == "none" else [b.strip() for b in _cb.split(",") if b.strip()]
CONFIRM = CONFIRMS[0] if CONFIRMS else ""
BOOKS = list(dict.fromkeys([SHARP] + RETAIL + CONFIRMS))
LOG_DAYS = 45   # keep graded alerts this long
LOOKAHEAD_H = float(os.environ.get("LOOKAHEAD_HOURS", "") or "24")
WINDOW_H = float(os.environ.get("MOVE_WINDOW_HOURS", "") or "2")   # compare against lines seen in this window (catches fast moves)
# Moneyline / run line: your book must beat the new sharp fair price by at least this much (0.02 = 2%).
MIN_EDGE = float(os.environ.get("MIN_EDGE", "") or "0.02")
ACTIVE_START_ET = int(os.environ.get("ACTIVE_START_ET", "") or "9")  # only poll 9am..midnight ET
ACTIVE_END_ET = int(os.environ.get("ACTIVE_END_ET", "") or "24")
RESERVE = int(os.environ.get("CREDIT_RESERVE", "") or "15")          # never spend below this
MIN_INTERVAL = float(os.environ.get("MIN_INTERVAL_MIN", "") or "5")  # fastest polling per sport
ONLY = [s.strip() for s in os.environ.get("SPORTS", "").split(",") if s.strip()]
# College football: "filter" = only push alerts for games with an AP Top 25 team (others are still
# scored silently for comparison), "tag" = push everything but label Top 25 / non-Top 25, "off" = no change.
NCAAF_TOP25 = (os.environ.get("NCAAF_TOP25", "") or "filter").lower()
# Spreads/totals: skip alerts when the best available price is worse than this (e.g. -130). "off" disables.
_mj = (os.environ.get("MAX_JUICE", "") or "-130").strip().lower()
MAX_JUICE = None if _mj in ("off", "none", "0") else float(_mj)
# One-time replay: set RECAP_REPLAY_HOURS (e.g. 36) to re-send a full results recap for the last N hours of alerts.
REPLAY_H = float(os.environ.get("RECAP_REPLAY_HOURS", "") or "0")
# Alerts that fire this close to the start (minutes) are tagged LATE. LATE_MODE: "tag" = push with a LATE label (default),
# "mute" = log and grade them but do not push. Either way early vs late results are compared in the recap.
LATE_MIN = float(os.environ.get("LATE_MINUTES", "") or "60")
LATE_MODE = (os.environ.get("LATE_MODE", "") or "tag").lower()
# Repeat alerts (line kept moving on a bet already alerted): "mute" = log them in alerts.json but don't push (default),
# "send" = push them too.
REPEAT_MODE = (os.environ.get("REPEAT_MODE", "") or "mute").lower()
RANKINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"

SPORTS = {
    "americanfootball_nfl":   dict(label="NFL",   markets=["spreads", "totals"], spread=1.0, total=1.0, keys=[3, 7]),
    "americanfootball_ncaaf": dict(label="NCAAF", markets=["spreads", "totals"], spread=1.0, total=1.0, keys=[3, 7]),
    "basketball_nba":         dict(label="NBA",   markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    "basketball_wnba":        dict(label="WNBA",  markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    "basketball_ncaab":       dict(label="NCAAB", markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    # MLB/NHL "spreads" are run/puck lines: watched by price at a fixed +/-1.5 (rl), never by point moves,
    # because a point flip (+1.5 -> -1.5) just means the favorite changed (the moneyline alert covers that).
    "baseball_mlb":           dict(label="MLB",   markets=["h2h", "spreads", "totals"], ml=0.03, rl=0.03, total=0.5,
                                   no_point_moves=True),
    "icehockey_nhl":          dict(label="NHL",   markets=["h2h", "spreads", "totals"], ml=0.03, rl=0.03, total=0.5,
                                   no_point_moves=True, rl_name="PL"),
}


# ---------------------------------------------------------------- helpers
def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_pt(p):
    p = float(p)
    s = f"{p:+.1f}".replace(".0", "")
    return "PK" if p == 0 else s


def fmt_price(a):
    a = int(round(a))
    return f"+{a}" if a > 0 else str(a)


def am_to_prob(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def prob_to_am(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return (100 * (1 - p) / p) if p < 0.5 else (-100 * p / (1 - p))


def http_get(path, params):
    params = dict(params, apiKey=KEY)
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        body = json.loads(r.read().decode())
        rem = r.headers.get("x-requests-remaining")
        return body, (int(float(rem)) if rem is not None else None)


def notify(title, body, red=False, yellow=False):
    """red = late alert; yellow = an earlier alert already came in on this game (the first alert is the play)."""
    if not NTFY_TOPIC:
        print(f"[dry-run alert] {title}\n{body}\n")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST",
        headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high",
                 "Tags": ",".join(t for t, on in (("red_circle", red), ("yellow_circle", yellow), ("moneybag", True)) if on)})
    urllib.request.urlopen(req, timeout=15).read()


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    with open(STATE_FILE, "w") as f:
        json.dump(st, f)


# ---------------------------------------------------------------- odds parsing
def book_lines(event):
    """{book: {'spreads': {team: (pt, price)}, 'totals': {'Over': (pt, price)}, 'h2h': {team: price}}}"""
    out = {}
    for bk in event.get("bookmakers", []):
        d = out.setdefault(bk["key"], {})
        for m in bk.get("markets", []):
            mk = m["key"]
            for o in m.get("outcomes", []):
                if mk == "h2h":
                    d.setdefault("h2h", {})[o["name"]] = o["price"]
                elif "point" in o:
                    d.setdefault(mk, {})[o["name"]] = (o["point"], o["price"])
    return out


def sharp_values(lines, book=None):
    """Flatten one book's lines (sharp book by default) into comparable values: {mkey: value}."""
    v = {}
    sb = lines.get(book or SHARP, {})
    sp = sb.get("spreads", {})
    for team, (pt, _) in sp.items():
        v[f"spreads|{team}"] = pt
    if len(sp) == 2:  # no-vig price of each side at its current point (used for MLB run lines)
        probs = {t: am_to_prob(pr) for t, (_, pr) in sp.items()}
        tot = sum(probs.values())
        for t, (pt, _) in sp.items():
            v[f"rl|{t}|{pt:g}"] = probs[t] / tot
    if "Over" in sb.get("totals", {}):
        v["totals|Over"] = sb["totals"]["Over"][0]
    h = sb.get("h2h", {})
    if len(h) == 2:  # no-vig win probabilities
        probs = {t: am_to_prob(p) for t, p in h.items()}
        tot = sum(probs.values())
        for t, p in probs.items():
            v[f"h2h|{t}"] = p / tot
    return v


NAMES = {"hardrockbet_fl": "Hard Rock FL", "hardrockbet": "Hard Rock", "prophetx": "ProphetX",
         "novig": "Novig", "kalshi": "Kalshi", "polymarket": "Polymarket", "betmgm": "BetMGM", "fanduel": "FanDuel", "draftkings": "DraftKings",
         "pinnacle": "Pinnacle", "betonlineag": "BetOnline", "lowvig": "LowVig", "matchbook": "Matchbook", "betfair_ex_eu": "Betfair", "smarkets": "Smarkets"}


def nm(b):
    return NAMES.get(b, b)


def also(books, best):
    rest = [nm(b) for b in dict.fromkeys(books) if b != best]
    return f" (also: {', '.join(rest)})" if rest else ""


def edge_ok(price, fair):
    """True when betting `price` beats fair win probability `fair` by at least MIN_EDGE."""
    return fair / am_to_prob(price) - 1 >= MIN_EDGE - 1e-9


def edge_price(fair):
    """Worst American price that still clears MIN_EDGE against `fair`."""
    return prob_to_am(fair / (1 + MIN_EDGE))


# Fees on winnings by book (ProphetX keeps 2% of a win). Every comparison, edge, cap, floor and grade uses the
# after-fee price; the alert text still shows the price on the book's screen. Kalshi/Novig/Hard Rock: no win fee.
WIN_FEE = {"prophetx": float(os.environ.get("PX_FEE", "") or "0.02")}


def net(price, book):
    """American price after the book's fee on winnings: ProphetX -114 -> about -116, +150 -> +147."""
    fee = WIN_FEE.get(book, 0)
    if not fee or price is None:
        return price
    w = (100 / abs(price) if price < 0 else price / 100) * (1 - fee)
    return -100 / w if w < 1 else w * 100


def gross(price, book):
    """Inverse of net(): the price the book must show to equal `price` after its fee."""
    fee = WIN_FEE.get(book, 0)
    if not fee or price is None:
        return price
    w = (100 / abs(price) if price < 0 else price / 100) / (1 - fee)
    return -100 / w if w < 1 else w * 100


def fee_note(price, book):
    return f" [{fmt_price(net(price, book))} after {nm(book)} fee]" if WIN_FEE.get(book) else ""


def floor_note(fl, book):
    return f" ({nm(book)}: {fmt_price(gross(fl, book))} or better on screen)" if WIN_FEE.get(book) else ""


UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")   # + money: risk UNIT; - money: risk to win UNIT (resets ~Nov 1)


def bet_size(price, book):
    """'Bet: risk $220 to win $200' at the price on the book's screen; ProphetX adds what the win nets after its fee."""
    p = float(price)
    risk, win = (UNIT, UNIT * p / 100) if p > 0 else (UNIT * abs(p) / 100, UNIT)
    s = f"Bet: risk ${risk:,.0f} to win ${win:,.0f}"
    fee = WIN_FEE.get(book, 0)
    return s + (f" (nets ${win * (1 - fee):,.0f} after {nm(book)} fee)" if fee else "")


def too_juiced(price):
    """Spread/total price worse than MAX_JUICE (e.g. -150 when the cap is -130)."""
    return MAX_JUICE is not None and price < 0 and price < MAX_JUICE


def crossed_key(old, new, keys):
    lo, hi = sorted((abs(old), abs(new)))
    return any(lo <= k <= hi and lo != hi for k in keys) if keys else False


# ---------------------------------------------------------------- AP Top 25 (college football)
ALIASES = {"ole miss": ["mississippi"], "usc": ["southern california", "southern cal"],
           "miami": ["miami (fl)", "miami fl", "miami florida"], "lsu": ["louisiana state"],
           "smu": ["southern methodist"], "byu": ["brigham young"], "ucf": ["central florida"],
           "tcu": ["texas christian"], "pitt": ["pittsburgh"], "uconn": ["connecticut"],
           # ESPN short names vs the Odds API's full names (grading)
           "app state": ["appalachian state"], "southern miss": ["southern mississippi"], "massachusetts": ["umass"],
           "umass": ["massachusetts"], "the citadel": ["citadel"], "sam houston": ["sam houston state"],
           "ul monroe": ["louisiana monroe", "louisiana-monroe", "ulm"], "louisiana": ["louisiana lafayette", "louisiana-lafayette"],
           "fiu": ["florida international"], "utsa": ["ut san antonio", "texas san antonio"], "nc state": ["north carolina state"],
           "uab": ["alabama birmingham"], "unlv": ["nevada las vegas"]}


def _norm(x):
    # accents and apostrophes off so "San José State", "Hawai'i" and "Montréal" match the plain spellings
    x = "".join(ch for ch in unicodedata.normalize("NFKD", str(x)) if not unicodedata.combining(ch))
    for ch in ("'", "\u2019", "\u02bb", "`"):
        x = x.replace(ch, "")
    return " ".join(x.lower().replace(".", "").replace("&", " and ").split())


def load_top25(st, n):
    """{rank: [name variants]} from ESPN's AP poll, cached once per ET day. None if unavailable."""
    today = n.astimezone(ET).date().isoformat()
    cache = st.get("top25")
    if cache and cache.get("day") == today:
        return cache.get("teams")
    teams = None
    try:
        req = urllib.request.Request(RANKINGS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        polls = data.get("rankings", [])
        ap = next((p for p in polls if "ap" in _norm(p.get("name", "")).split()
                   or _norm(p.get("type", "")) == "ap"), polls[0] if polls else None)
        if ap:
            teams = []
            for r_ in ap.get("ranks", []):
                t = r_.get("team", {})
                loc = _norm(t.get("location", "") or t.get("nickname", ""))
                locs = [loc] + ALIASES.get(loc, []) + [_norm(t.get("nickname", "")), _norm(t.get("abbreviation", ""))]
                teams.append({"rank": r_.get("current"), "locs": [x for x in dict.fromkeys(locs) if x],
                              "mascot": _norm(t.get("name", "")), "label": t.get("location") or t.get("nickname", "")})
            teams = teams or None
    except Exception as ex:
        print(f"Top 25 fetch failed: {ex}")
    if teams is not None or not cache:
        st["top25"] = {"day": today if teams is not None else "", "teams": teams}
    return teams if teams is not None else (cache or {}).get("teams")


def top25_rank(team_name, teams):
    """(rank, label) if an Odds API team name ('Georgia Bulldogs') is in the Top 25, else None."""
    full = _norm(team_name)
    for t in teams or []:
        for loc in t["locs"]:
            if full == loc or (full.startswith(loc + " ") and (not t["mascot"] or full.endswith(" " + t["mascot"])
                                                               or full == f"{loc} {t['mascot']}")):
                return t["rank"], t["label"]
    return None


def top25_tag(event, teams):
    """(is_top25, ' [Top 25: #5 Indiana]' / ' [non-Top 25]' / ' [Top 25 n/a]')."""
    if teams is None:
        return True, " [Top 25 n/a]"
    hits = [h for h in (top25_rank(event["away_team"], teams), top25_rank(event["home_team"], teams)) if h]
    if hits:
        return True, " [Top 25: " + ", ".join(f"#{r} {lbl}" for r, lbl in hits) + "]"
    return False, " [non-Top 25]"


# ---------------------------------------------------------------- estimated edge (EV) for spreads/totals
# Approximate chance the final margin (spreads) or total lands exactly on each number, by sport.
# Each half point between the bettor's number and Pinnacle's new number is worth about half that chance.
NFL_MARGIN = {1: .035, 2: .035, 3: .15, 4: .05, 5: .035, 6: .055, 7: .09, 8: .03, 9: .02, 10: .055,
              11: .025, 12: .02, 13: .025, 14: .045, 16: .02, 17: .035, 21: .03}
NCAAF_MARGIN = {1: .03, 2: .03, 3: .08, 4: .035, 6: .035, 7: .06, 10: .045, 14: .045, 17: .03, 21: .03}
NFL_TOTAL_KEYS = {37: .04, 40: .035, 41: .045, 43: .035, 44: .04, 47: .04, 51: .035, 54: .03}


def number_mass(sport, kind, k, line):
    k = int(round(abs(k))) if kind == "spr" else int(round(k))
    if kind == "spr":
        if sport == "NFL":
            return NFL_MARGIN.get(k, .015)
        if sport == "NCAAF":
            return NCAAF_MARGIN.get(k, .025)
        return .03 if k <= 12 else .025          # NBA / NCAAB / WNBA
    if sport in ("NHL", "MLB"):                   # goals/runs: Poisson around the line (MLB fatter tails)
        lam = max(float(line), 0.5)
        pm = math.exp(-lam) * lam ** k / math.factorial(k) if k >= 0 else 0
        return pm * (0.8 if sport == "MLB" else 1.0)
    if sport == "NFL":
        return NFL_TOTAL_KEYS.get(k, .025)
    if sport == "NCAAF":
        return .02
    return .022                                    # basketball totals


def half_point_value(sport, kind, a, b, line):
    """Win-probability gained moving from number a to the better number b (b > a in the bettor's favour)."""
    lo, hi = sorted((a, b))
    v, x = 0.0, lo
    while x < hi - 1e-9:
        nxt = x + 0.5
        k = nxt if abs(nxt - round(nxt)) < 1e-9 else x   # the whole number this half step touches
        v += number_mass(sport, kind, k, line) / 2
        x = nxt
    return v


def ev_pct(p, price):
    """Expected value per 1 unit risked at American `price` with win chance p (pushes counted as half)."""
    dec = 1 + (100 / abs(price) if price < 0 else price / 100)
    return p * (dec - 1) - (1 - p)


# ---------------------------------------------------------------- detection
def detect(event, cfg, lines, base):
    """Compare sharp lines now vs. baseline values; return list of alert dicts."""
    alerts = []
    sb = lines.get(SHARP, {})
    retail = {b: lines[b] for b in RETAIL if b in lines}
    cvs = {b: sharp_values(lines, b) for b in CONFIRMS if b in lines}
    cnames = []
    game = f"{event['away_team']} @ {event['home_team']}"
    start = parse_iso(event["commence_time"]).astimezone(ET).strftime("%a %-I:%M %p ET")

    def agree(key, old, new):
        """Does the confirm book sit on the moved side of the sharp move? yes / no / na (no line)."""
        if not CONFIRMS:
            return "off"
        mid = (old + new) / 2
        yes, no = [], []
        for b, cv in cvs.items():
            c = cv.get(key)
            if c is None:
                continue
            (yes if ((c <= mid + 1e-9) if new < old else (c >= mid - 1e-9)) else no).append(b)
        cnames[:] = yes
        if not yes and not no:
            return "na"
        return "yes" if len(yes) >= len(no) and yes else "no"

    def add(kind, side, pt, price, book, new_key, text, why, conf, mag=1.0, nb=1, edge=None, evp=None):
        nc = len(cnames) if conf == "yes" else 0
        if conf == "no":
            return  # confirm book disagrees: likely noise or stale sharp data
        note = {"yes": f" (confirmed by {', '.join(nm(b) for b in cnames)})", "na": f" ({nm(SHARP)} only)", "off": ""}[conf]
        alerts.append(dict(id=f"{event['id']}|{new_key}", ev=event["id"], game=game, start=start,
                           commence=event["commence_time"], kind=kind, side=side, pt=pt, price=price,
                           book=book, net=round(net(price, book), 1), conf=conf, text=text, why=why + note,
                           mag=round(mag, 2), nb=nb, edge=edge, nconf=nc, cby=[nm(b) for b in cnames] if conf == "yes" else [],
                           evp=round(100 * (evp if evp is not None else edge), 1) if (evp is not None or edge is not None) else None))

    # Spreads: sharp side = team whose number got worse (money pushed it).
    for team, (new, _) in ({} if cfg.get("no_point_moves") else sb.get("spreads", {})).items():
        old = base.get(f"spreads|{team}")
        if old is None or new >= old:
            continue
        move = old - new
        if move < cfg.get("spread", 99) and not crossed_key(old, new, cfg.get("keys", [])):
            continue
        offers = [(pt, pr, b) for b, d in retail.items()
                  for t, (pt, pr) in d.get("spreads", {}).items() if t == team]
        if not offers:
            continue
        pt, pr, b = max(offers, key=lambda x: (x[0], net(x[1], x[2])))
        if pt > new and not too_juiced(net(pr, b)):
            opp = [p2 for t2, (_, p2) in sb["spreads"].items() if t2 != team]
            p0 = (am_to_prob(sb["spreads"][team][1]) / (am_to_prob(sb["spreads"][team][1]) + am_to_prob(opp[0]))) if opp else 0.5
            evp = ev_pct(min(max(p0 + half_point_value(cfg["label"], "spr", new, pt, new), .01), .99), net(pr, b))
            add("spr", team, pt, pr, b, f"spr|{team}|{new}",
                f"{team} {fmt_pt(pt)} ({fmt_price(pr)}) at {nm(b)}{fee_note(pr, b)}" + also([x[2] for x in offers if x[0] > new], b),
                f"{nm(SHARP)} moved {fmt_pt(old)} -> {fmt_pt(new)}; bet only at {fmt_pt(new + 0.5)} or better",
                agree(f"spreads|{team}", old, new),
                mag=move / (cfg.get("spread") or 1), nb=len([x for x in offers if x[0] > new]), evp=evp)

    # Totals
    if "Over" in sb.get("totals", {}):
        new = sb["totals"]["Over"][0]
        old = base.get("totals|Over")
        if old is not None and abs(new - old) >= cfg["total"]:
            side = "Over" if new > old else "Under"
            offers = [(d["totals"][side][0], d["totals"][side][1], b)
                      for b, d in retail.items() if side in d.get("totals", {})]
            if offers:
                if side == "Over":
                    pt, pr, b = min(offers, key=lambda x: (x[0], -net(x[1], x[2])))
                    ok, thr = pt < new, new - 0.5
                else:
                    pt, pr, b = max(offers, key=lambda x: (x[0], net(x[1], x[2])))
                    ok, thr = pt > new, new + 0.5
                if ok and not too_juiced(net(pr, b)):
                    tt = sb["totals"]
                    p0 = (am_to_prob(tt[side][1]) / (am_to_prob(tt["Over"][1]) + am_to_prob(tt["Under"][1]))
                          if "Under" in tt and side in tt else 0.5)
                    evp = ev_pct(min(max(p0 + half_point_value(cfg["label"], "tot", pt, new, new), .01), .99), net(pr, b))
                    add("tot", side, pt, pr, b, f"tot|{side}|{new}",
                        f"{side} {pt:g} ({fmt_price(pr)}) at {nm(b)}{fee_note(pr, b)}"
                        + also([x[2] for x in offers if (x[0] < new if side == "Over" else x[0] > new)], b),
                        f"{nm(SHARP)} total moved {old:g} -> {new:g}; bet only at {thr:g} or better",
                        agree("totals|Over", old, new),
                        mag=abs(new - old) / cfg["total"],
                        nb=len([x for x in offers if (x[0] < new if side == "Over" else x[0] > new)]), evp=evp)

    # Run lines (MLB) and puck lines (NHL): point usually stays at 1.5, so watch the price at that point.
    # Sharp side = team whose no-vig run-line probability rose at an unchanged point.
    if "rl" in cfg and len(sb.get("spreads", {})) == 2:
        sv = sharp_values({SHARP: sb})
        for team, (pt, _) in sb["spreads"].items():
            k = f"rl|{team}|{pt:g}"
            new, old = sv.get(k), base.get(k)
            if old is None or new - old < cfg["rl"]:
                continue
            offers = [(pr, b) for b, d in retail.items()
                      for t, (p2, pr) in d.get("spreads", {}).items() if t == team and p2 == pt]
            if not offers:
                continue
            pr, b = max(offers, key=lambda x: 1 / am_to_prob(net(x[0], x[1])))
            if edge_ok(net(pr, b), new):
                add("rl", team, pt, pr, b, f"rl|{team}|{pt:g}|{round(new, 2)}",
                    f"{team} {fmt_pt(pt)} {cfg.get('rl_name', 'RL')} {fmt_price(pr)} at {nm(b)}{fee_note(pr, b)}"
                    + also([x[1] for x in offers if edge_ok(net(x[0], x[1]), new)], b),
                    (f"{nm(SHARP)} {fmt_pt(pt)} fair moved {fmt_price(prob_to_am(old))} -> "
                     f"{fmt_price(prob_to_am(new))}; bet only at {fmt_price(edge_price(new))} or better"
                     + floor_note(edge_price(new), b)),
                    agree(k, old, new),
                    mag=(new - old) / cfg["rl"], nb=len([x for x in offers if edge_ok(net(x[0], x[1]), new)]),
                    edge=new / am_to_prob(net(pr, b)) - 1)

    # Moneyline (MLB/NHL): sharp side = team whose no-vig win prob rose.
    if "ml" in cfg and len(sb.get("h2h", {})) == 2:
        sv = sharp_values({SHARP: sb})
        for team in sb["h2h"]:
            new, old = sv.get(f"h2h|{team}"), base.get(f"h2h|{team}")
            if old is None or new - old < cfg["ml"]:
                continue
            offers = [(d["h2h"][team], b) for b, d in retail.items() if team in d.get("h2h", {})]
            if not offers:
                continue
            pr, b = max(offers, key=lambda x: 1 / am_to_prob(net(x[0], x[1])))
            if edge_ok(net(pr, b), new):  # retail price (after any win fee) beats the sharp fair price by MIN_EDGE
                add("ml", team, None, pr, b, f"ml|{team}|{round(new, 2)}",
                    f"{team} ML {fmt_price(pr)} at {nm(b)}{fee_note(pr, b)}"
                    + also([x[1] for x in offers if edge_ok(net(x[0], x[1]), new)], b),
                    (f"{nm(SHARP)} fair moved {fmt_price(prob_to_am(old))} -> {fmt_price(prob_to_am(new))}; "
                     f"bet only at {fmt_price(edge_price(new))} or better" + floor_note(edge_price(new), b)),
                    agree(f"h2h|{team}", old, new),
                    mag=(new - old) / cfg["ml"], nb=len([x for x in offers if edge_ok(net(x[0], x[1]), new)]),
                    edge=new / am_to_prob(net(pr, b)) - 1)
    return alerts


# ---------------------------------------------------------------- closing-line tracking
def close_value(e, vals):
    """The sharp book's current number for a logged alert's market (None if not comparable)."""
    if e["kind"] == "spr":
        return vals.get(f"spreads|{e['side']}")
    if e["kind"] == "tot":
        return vals.get("totals|Over")
    if e["kind"] == "ml":
        return vals.get(f"h2h|{e['side']}")
    if e["kind"] == "rl":
        return vals.get(f"rl|{e['side']}|{e['pt']:g}")
    return None


def grade(e):
    """CLV vs the sharp closing number: (value, text). Positive = beat the close."""
    c = e.get("close")
    if c is None:
        return None
    if e["kind"] == "spr":
        v = e["pt"] - c
        return v, f"{v:+g} pts"
    if e["kind"] == "tot":
        v = (c - e["pt"]) if e["side"] == "Over" else (e["pt"] - c)
        return v, f"{v:+g} pts"
    v = (c / am_to_prob(net(e["price"], e.get("book"))) - 1) * 100   # % edge of your after-fee price vs closing fair odds
    return v, f"{v:+.1f}%"


def describe(e):
    if e["kind"] == "spr":
        return f"{e['side']} {fmt_pt(e['pt'])} ({fmt_price(e['price'])})"
    if e["kind"] == "tot":
        return f"{e['side']} {e['pt']:g} ({fmt_price(e['price'])})"
    if e["kind"] == "rl":
        return f"{e['side']} {fmt_pt(e['pt'])} {'PL' if e.get('sport') == 'NHL' else 'RL'} {fmt_price(e['price'])}"
    return f"{e['side']} ML {fmt_price(e['price'])}"


# ---------------------------------------------------------------- timing and confidence grade
def lead_text(m):
    m = max(int(round(m)), 0)
    return f"{m}m" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def sport_rate(st, n, label):
    """(share of this sport's last-30-day alerts that beat the close, sample size)."""
    g = [c for e, c in graded(st, n, 30) if c and e["sport"] == label and not e.get("muted")]
    return (sum(1 for v, _ in g if v > 0) / len(g), len(g)) if g else (None, 0)


def confidence(a, st, n, lead_min):
    """0-100 heuristic and an A-D grade. Not a win probability: the recap shows how each grade has actually done.
    25 confirm book agrees (10 if Pinnacle only) + 25 size of the sharp move vs the sport's trigger (caps at 3x)
    + 15 books offering the number (1=5, 2=10, 3+=15) + 15 price (edge vs fair, or juice) + 15 sport's 30-day
    beat-the-close rate (neutral 50% until 10 samples) + 5 lead time (3h+ = 5, 1h+ = 3, under 1h = 0)."""
    s = {"yes": 25, "na": 10}.get(a.get("conf"), 0)
    s += min(a.get("mag", 1.0), 3.0) / 3.0 * 25
    s += {1: 5, 2: 10}.get(a.get("nb", 1), 15)
    if a.get("edge") is not None:
        s += min(max(a["edge"], 0) / 0.06, 1.0) * 15
    else:
        p = float(net(a["price"], a.get("book")))
        s += 15 if p >= -110 else 10 if p >= -120 else 5 if p >= -130 else 0
    rate, cnt = sport_rate(st, n, a.get("sport") or a.get("label") or "")
    s += (rate if cnt >= 10 else 0.5) * 15
    s += 5 if lead_min >= 180 else 3 if lead_min >= 60 else 0
    s = int(round(min(max(s, 0), 100)))
    return s, ("A" if s >= 75 else "B" if s >= 60 else "C" if s >= 45 else "D")


# ---------------------------------------------------------------- final scores (ESPN, free) and W/L
ESPN_PATH = {"NFL": "football/nfl", "NCAAF": "football/college-football", "NBA": "basketball/nba",
             "WNBA": "basketball/wnba", "NCAAB": "basketball/mens-college-basketball",
             "MLB": "baseball/mlb", "NHL": "hockey/nhl"}
ESPN_EXTRA = {"NCAAF": {"groups": "80"}, "NCAAB": {"groups": "50"}}
ESPN_MORE = {"NCAAF": [{"groups": "81"}]}   # FCS scoreboard too (e.g. The Citadel at Texas A&M)
_SB_CACHE = {}


def espn_scoreboard(sport, day, extra=None):
    """Finished/pending games for one sport on one ET date: [{done, so, away, home}] (cached per run)."""
    key = (sport, day, json.dumps(extra, sort_keys=True) if extra else None)
    if key in _SB_CACHE:
        return _SB_CACHE[key]
    games = []
    try:
        q = {"dates": day.replace("-", ""), "limit": "400"}
        q.update(extra if extra is not None else ESPN_EXTRA.get(sport, {}))
        url = f"https://site.api.espn.com/apis/site/v2/sports/{ESPN_PATH[sport]}/scoreboard?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            ty = (comp.get("status") or ev.get("status") or {}).get("type", {})
            g = {"done": bool(ty.get("completed")),
                 "so": "so" in str(ty.get("shortDetail", "")).lower().split("/")}
            for c in comp.get("competitors", []):
                t = c.get("team", {})
                names = {_norm(t[k]) for k in ("displayName", "shortDisplayName", "location", "name") if t.get(k)}
                try:
                    pts = int(float(c.get("score")))
                except (TypeError, ValueError):
                    pts = None
                g[c.get("homeAway")] = {"names": names, "loc": _norm(t.get("location", "")), "mascot": _norm(t.get("name", "")),
                                        "abbr": t.get("abbreviation", ""), "pts": pts}
            if "home" in g and "away" in g:
                games.append(g)
    except Exception as ex:
        print(f"Scoreboard fetch failed ({sport} {day}): {ex}")
        return []  # not cached: try again next run
    _SB_CACHE[key] = games
    return games


def team_match(odds_name, side):
    full = _norm(odds_name)
    if full in side["names"]:
        return True
    for alias in [side["loc"]] + [a for k, v in ALIASES.items() if k == side["loc"] for a in v]:
        if alias and (full == alias or full.startswith(alias + " ")):
            return True
    return any(full == alias for alias in ALIASES.get(full, []) if alias in side["names"])


def mascot_match(odds_name, side):
    """Loose fallback: the odds name ends with ESPN's nickname ('... Mountaineers'). Used only when BOTH teams match."""
    m = side.get("mascot")
    full = _norm(odds_name)
    return bool(m) and (full == m or full.endswith(" " + m))


def find_game(e):
    away, home = e["game"].split(" @ ", 1)
    start = parse_iso(e["start"]).astimezone(ET)
    boards = [None] + ESPN_MORE.get(e["sport"], [])
    for test in (team_match, mascot_match):   # exact names first, nicknames only if no exact match anywhere
        for extra in boards:
            for off in (0, 1):  # late games can be filed under the next ET date
                day = (start + timedelta(days=off)).date().isoformat()
                hits = [g for g in espn_scoreboard(e["sport"], day, extra)
                        if test(away, g["away"]) and test(home, g["home"])]
                if hits and (test is team_match or len(hits) == 1):   # nickname match must be unique
                    return hits[0]
    return None


def settle(e, g):
    """('W'|'L'|'P', 'AWY 27, HME 24') at the alert number, or None if not final yet."""
    a, h = g["away"]["pts"], g["home"]["pts"]
    if not g["done"] or a is None or h is None:
        return None
    away, home = e["game"].split(" @ ", 1)
    if e["kind"] == "tot":
        tot = a + h - (1 if (g["so"] and e["sport"] == "NHL") else 0)  # shootout goal doesn't count toward totals
        d = tot - e["pt"]
        if e["side"] == "Under":
            d = -d
    else:
        mine_home = _norm(e["side"]) == _norm(home)
        my, opp = (h, a) if mine_home else (a, h)
        d = (my - opp) + (e["pt"] if e["kind"] in ("spr", "rl") else 0)
    r = "W" if d > 1e-9 else ("L" if d < -1e-9 else "P")
    return r, f"{g['away']['abbr'] or away} {a}, {g['home']['abbr'] or home} {h}"


def units(e, r):
    """Flat 1 unit risked at the alert price, after the book's fee on winnings (ProphetX win at -110 = +0.89u)."""
    if r == "L":
        return -1.0
    if r == "P":
        return 0.0
    p = float(net(e["price"], e.get("book")))
    return 100 / abs(p) if p < 0 else p / 100


# ---------------------------------------------------------------- true closing line (Oct 25)
# One Pinnacle-only read per game in the last CLOSE_WINDOW minutes before start (runs at any hour, cheap: 1 credit per
# market per game). Closing value = expected profit per 1u of the play's AFTER-FEE price at Pinnacle's no-vig closing
# win chance at the play's own number (half points between Pinnacle's number and the play's number are priced in).
CLOSE_WINDOW = float(os.environ.get("CLOSE_WINDOW_MIN", "") or "15")
LABEL_KEY = {v["label"]: k for k, v in SPORTS.items()}
EXEC_BOOKS = ("novig", "kalshi", "prophetx", "polymarket")   # books the executor can place (Polymarket US via the feed's polymarket)


def close_prob(e, pin):
    """Pinnacle no-vig closing win chance for the play at its own number, or None."""
    k, side, pt, lab = e["kind"], e["side"], e.get("pt"), e.get("sport", "")
    if k == "ml":
        h = pin.get("h2h", {})
        if len(h) != 2 or side not in h:
            return None
        pr = {t: am_to_prob(p) for t, p in h.items()}
        return pr[side] / sum(pr.values())
    if k in ("spr", "rl"):
        sp = pin.get("spreads", {})
        if len(sp) != 2 or side not in sp:
            return None
        (ppt, ppr), (_, opr) = sp[side], [v for t, v in sp.items() if t != side][0]
        p = am_to_prob(ppr) / (am_to_prob(ppr) + am_to_prob(opr))
        if abs(ppt - pt) > 1e-9:
            if k == "rl":
                return None   # run/puck line at a different point: not comparable
            v = half_point_value(lab, "spr", ppt, pt, ppt)
            p += v if pt > ppt else -v
        return min(max(p, .01), .99)
    if k == "tot":
        tt = pin.get("totals", {})
        if "Over" not in tt or "Under" not in tt:
            return None
        ppt = tt["Over"][0]
        p = am_to_prob(tt[side][1]) / (am_to_prob(tt["Over"][1]) + am_to_prob(tt["Under"][1]))
        if abs(ppt - pt) > 1e-9:
            v = half_point_value(lab, "tot", ppt, pt, ppt)
            better = (pt < ppt) if side == "Over" else (pt > ppt)
            p += v if better else -v
        return min(max(p, .01), .99)
    return None


def closing_reads(st, n):
    """Take the final Pinnacle read for every logged play whose game starts within CLOSE_WINDOW minutes."""
    due = {}
    for e in st["log"]:
        if e.get("cl") or e.get("sport") not in LABEL_KEY:
            continue
        mins = (parse_iso(e["start"]) - n).total_seconds() / 60
        if 0 < mins <= CLOSE_WINDOW:
            due.setdefault((LABEL_KEY[e["sport"]], e["ev"]), []).append(e)
    for (key, ev), es in due.items():
        if st.get("remaining") is not None and st["remaining"] <= RESERVE:
            print("Closing reads skipped: credit reserve reached.")
            return
        mk = sorted({"h2h" if e["kind"] == "ml" else "totals" if e["kind"] == "tot" else "spreads" for e in es})
        try:
            body, rem = http_get(f"/sports/{key}/events/{ev}/odds",
                                 {"bookmakers": SHARP, "markets": ",".join(mk), "oddsFormat": "american"})
        except Exception as ex:
            print(f"Closing read failed {key} {ev}: {str(ex)[:120]}")
            continue
        if rem is not None:
            st["remaining"] = rem
        pin = book_lines(body).get(SHARP, {})
        for e in es:
            p = close_prob(e, pin)
            if p is None:
                continue
            ev_close = ev_pct(p, net(e["price"], e.get("book")))
            e["cl"] = {"p": round(p, 4), "ev": round(100 * ev_close, 1),
                       "mins_before": round((parse_iso(e["start"]) - n).total_seconds() / 60)}
            print(f"Closing read: {describe(e)} {e['game']}: close fair {p:.3f}, value {100 * ev_close:+.1f}%")


def executable(e, sent_text=None):
    """Could the executor have bet this? (alert book or an 'also' book is one it places on)"""
    if e.get("book") in EXEC_BOOKS:
        return True
    t = sent_text or ""
    return any(f"also:" in t and nm(b) in t.split("also:", 1)[1] for b in EXEC_BOOKS)


def settle_pending(st, n):
    """Fill in final score + W/L for alerts whose game should be over (cheap: one scoreboard call per sport/day)."""
    for e in st["log"]:
        if e.get("res") or parse_iso(e["start"]) > n - timedelta(hours=3) or e["sport"] not in ESPN_PATH:
            continue
        g = find_game(e)
        s = settle(e, g) if g else None
        if s:
            e["res"] = {"r": s[0], "score": s[1]}


def graded(st, n, days=None):
    """Started alerts that have a closing number and/or a final result: [(e, clv)] (clv may be None)."""
    out = []
    for e in st["log"]:
        if parse_iso(e["start"]) > n:
            continue
        if days and parse_iso(e["start"]) < n - timedelta(days=days):
            continue
        g = grade(e)
        if g or e.get("res"):
            out.append((e, g))
    return out


ICON = {"W": "\u2705", "L": "\u274c", "P": "\u2796"}


def line_for(e, g):
    res = e.get("res")
    icon = ICON[res["r"]] if res else "\u23f3"
    word = {"W": "WON", "L": "LOST", "P": "PUSH"}[res["r"]] + " " if res else ""
    s = f"{icon} {word}{e['sport']} {describe(e)}: " + (res["score"] if res else "score pending")
    if g:
        s += f" | CLV {g[1]}"
    if e.get("grade"):
        s += f" | {e['grade']}{e['score']}" + (f" {e['evp']:+.1f}%" if e.get("evp") is not None else "") + (" LATE" if e.get("late") else "")
    return s


def record(items):
    w = sum(1 for e, _ in items if e.get("res", {}).get("r") == "W")
    l = sum(1 for e, _ in items if e.get("res", {}).get("r") == "L")
    p = sum(1 for e, _ in items if e.get("res", {}).get("r") == "P")
    u = sum(units(e, e["res"]["r"]) for e, _ in items if e.get("res"))
    return w, l, p, u


def notify_chunks(title, header, lines, footer):
    """ntfy bodies cap near 4 KB: split long recaps into numbered parts instead of dropping alerts."""
    parts, cur = [], []
    size = len(header) + len(footer) + 40
    for ln in lines:
        if size + len(ln) + 1 > 3300 and cur:
            parts.append(cur)
            cur, size = [], 40
        cur.append(ln)
        size += len(ln.encode()) + 1
    parts.append(cur)
    for i, chunk in enumerate(parts, 1):
        body = (header + "\n" if i == 1 else "") + "\n".join(chunk) + (("\n" + footer) if i == len(parts) else "")
        notify(title + (f" ({i}/{len(parts)})" if len(parts) > 1 else ""), body)


def recap(st, n):
    """Once per ET day: push a recap (W/L, final score, CLV) of every newly settled alert, none dropped."""
    today = n.astimezone(ET).date().isoformat()
    replay = REPLAY_H > 0 and st.get("replay_done") != f"{today}:{REPLAY_H:g}"
    if st.get("recap_day") == today and not replay:
        return
    st["recap_day"] = today
    if replay:
        st["replay_done"] = f"{today}:{REPLAY_H:g}"
        cutoff = n - timedelta(hours=REPLAY_H)
        allnew = [(e, g) for e, g in graded(st, n) if parse_iso(e["start"]) >= cutoff]
    else:
        allnew = [(e, g) for e, g in graded(st, n) if not e.get("reported")]
    # alerts still waiting on a final score stay unreported until it posts (or 2 days pass)
    for e, _ in allnew:
        if e.get("res") or parse_iso(e["start"]) < n - timedelta(days=2):
            e["reported"] = True
    new = [(e, g) for e, g in allnew if not e.get("muted") and (replay or e.get("reported"))]
    if not new:
        return
    w, l, p, u = record(new)
    clv = [(e, g) for e, g in new if g]
    beat = sum(1 for _, g in clv if g[0] > 0)
    header = (f"{'Replay: ' if replay else ''}Results {w}-{l}" + (f"-{p}" if p else "") + f" ({u:+.2f}u flat)"
              + (f" | {beat} of {len(clv)} beat {nm(SHARP)}'s close" if clv else ""))
    lines = [line_for(e, g) for e, g in sorted(new, key=lambda x: x[0]["start"])]
    allm = [x for x in graded(st, n, 30) if not x[0].get("muted")]
    month = [x for x in allm if x[0]["sport"] != "NBA"]   # NBA is its own bucket, not part of the system record
    mw, ml, mp, mu = record(month)
    mclv = [x for x in month if x[1]]
    footer = (f"Last 30 days (ex-NBA): {mw}-{ml}" + (f"-{mp}" if mp else "") + f" ({mu:+.2f}u), "
              f"{sum(1 for _, g in mclv if g[0] > 0)}/{len(mclv)} beat the close")
    nba = [x for x in allm if x[0]["sport"] == "NBA"]
    if nba:
        bw, bl, bp, bu = record(nba)
        bclv = [x for x in nba if x[1]]
        footer += (f"\nNBA (30d): {bw}-{bl}" + (f"-{bp}" if bp else "") + f" ({bu:+.2f}u), "
                   f"{sum(1 for _, g in bclv if g[0] > 0)}/{len(bclv)} beat the close")
    cfb = [x for x in graded(st, n, 30) if "t25" in x[0] and x[1]]
    if cfb:
        def split(flag):
            g = [v for e, (v, _) in cfb if e["t25"] is flag]
            return f"{sum(1 for v in g if v > 0)}/{len(g)}"
        footer += f"\nCollege 30d beat close: Top 25 {split(True)}, non-Top 25 {split(False)} (not sent)"
    def rec_line(label, items):
        w_, l_, p_, u_ = record(items)
        c_ = [x for x in items if x[1]]
        bc = f", {round(100 * sum(1 for x in c_ if x[1][0] > 0) / len(c_))}% beat close" if c_ else ""
        return f"{label} {w_}-{l_}" + (f"-{p_}" if p_ else "") + f" ({u_:+.2f}u{bc})"
    tagged = [x for x in month if x[0].get("res") and x[0].get("grade")]   # ex-NBA, ties to the headline record
    if tagged:
        footer += "\nBy grade (30d): " + ", ".join(rec_line(gr, [x for x in tagged if x[0]["grade"] == gr])
                                                    for gr in "ABCD" if any(x[0]["grade"] == gr for x in tagged))
        footer += ("\nTiming (30d): " + rec_line("Early", [x for x in tagged if not x[0].get("late")]) + " | "
                   + rec_line("Late" + (" (not sent)" if LATE_MODE == "mute" else ""),
                              [x for x in tagged if x[0].get("late")]))
    nba_t = [x for x in nba if x[0].get("res") and x[0].get("grade")]
    if len(nba_t) >= 10:
        footer += "\nNBA by grade (30d): " + ", ".join(rec_line(gr, [x for x in nba_t if x[0]["grade"] == gr])
                                                        for gr in "ABCD" if any(x[0]["grade"] == gr for x in nba_t))
    nc_items = [x for x in month if x[0].get("res") and "nconf" in x[0]]
    if nc_items:
        footer += "\nBy confirm books (30d): " + ", ".join(
            rec_line(f"{lab}", [x for x in nc_items if sel(x[0]["nconf"])])
            for lab, sel in (("0-1", lambda k: k <= 1), ("2", lambda k: k == 2), ("3+", lambda k: k >= 3))
            if any(sel(x[0]["nconf"]) for x in nc_items))
    ev_items = [x for x in month if x[0].get("res") and x[0].get("evp") is not None]
    if ev_items:
        footer += "\nBy edge (30d): " + ", ".join(
            rec_line(lab, [x for x in ev_items if sel(x[0]["evp"])])
            for lab, sel in (("<0%", lambda v: v < 0), ("0-3%", lambda v: 0 <= v < 3), ("3%+", lambda v: v >= 3))
            if any(sel(x[0]["evp"]) for x in ev_items))
    cl_items = [x[0] for x in month if x[0].get("cl")]
    if cl_items:
        beat = sum(1 for e in cl_items if e["cl"]["ev"] > 0)
        avg = sum(e["cl"]["ev"] for e in cl_items) / len(cl_items)
        footer += f"\nTrue closing value (30d): beat close {beat}/{len(cl_items)}, avg {avg:+.1f}% per play"
    notify_chunks("Sharp recap", header, lines, footer)


def weekly_recap(st, n):
    """Mondays (first run after the daily recap): Monday-to-Sunday totals for the week that just ended, in addition to the daily."""
    et = n.astimezone(ET)
    if et.weekday() != 0 or st.get("weekly_day") == et.date().isoformat():
        return
    st["weekly_day"] = et.date().isoformat()
    start = (et - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = et.replace(hour=0, minute=0, second=0, microsecond=0)
    wk_all = [x for x in graded(st, n, 9) if not x[0].get("muted") and start <= parse_iso(x[0]["start"]).astimezone(ET) < end]
    if not wk_all:
        return
    wk = [x for x in wk_all if x[0]["sport"] != "NBA"]       # system record ex-NBA (matches the daily footer)
    wk_nba = [x for x in wk_all if x[0]["sport"] == "NBA"]

    def rl(items):
        w_, l_, p_, u_ = record(items)
        return f"{w_}-{l_}" + (f"-{p_}" if p_ else "") + f" ({u_:+.2f}u)"
    clv = [x for x in wk if x[1]]
    beat = sum(1 for _, g in clv if g[0] > 0)
    pend = sum(1 for e, _ in wk if not e.get("res"))
    lines = [f"Week {start.strftime('%b %-d')} - {(end - timedelta(days=1)).strftime('%b %-d')} (ex-NBA): {rl(wk)} flat"
             + (f" | {beat} of {len(clv)} beat {nm(SHARP)}'s close" if clv else "")
             + (f" | {pend} ungraded" if pend else "")]
    lines.append("By day:")
    for i in range(7):
        d0 = start + timedelta(days=i)
        day = [x for x in wk if parse_iso(x[0]["start"]).astimezone(ET).date() == d0.date()]
        if day:
            lines.append(f"{d0.strftime('%a %b %-d')}: {rl(day)}")
    lines.append("By sport:")
    for sp in sorted({x[0]["sport"] for x in wk}):
        lines.append(f"{sp}: {rl([x for x in wk if x[0]['sport'] == sp])}")
    tagged = [x for x in wk if x[0].get("res") and x[0].get("grade")]
    if tagged:
        lines.append("By grade: " + ", ".join(f"{gr} {rl([x for x in tagged if x[0]['grade'] == gr])}"
                                              for gr in "ABCD" if any(x[0]["grade"] == gr for x in tagged)))
    if wk_nba:
        nclv = [x for x in wk_nba if x[1]]
        lines.append(f"NBA (own bucket): {rl(wk_nba)}" + (f" | {sum(1 for _, g in nclv if g[0] > 0)} of {len(nclv)} beat the close" if nclv else ""))
        nt = [x for x in wk_nba if x[0].get("res") and x[0].get("grade")]
        if len(nt) >= 10:
            lines.append("NBA by grade: " + ", ".join(f"{gr} {rl([x for x in nt if x[0]['grade'] == gr])}"
                                                      for gr in "ABCD" if any(x[0]["grade"] == gr for x in nt)))
    notify("Sharp weekly recap", "\n".join(lines))


def write_alerts_file(st, n):
    """alerts.json: every alert from the last 45 days (bet, book, price, grade, confirm books, result) for agents/other tools.
    Rewritten each run; the workflow commits it only when it changed."""
    path = os.environ.get("ALERTS_FILE", "") or "alerts.json"
    out = []
    for e in sorted(st["log"], key=lambda x: x["start"], reverse=True):
        res = e.get("res")
        g = grade(e)
        out.append({
            "start_utc": e["start"], "game": e["game"], "sport": e["sport"], "bet": describe(e),
            "book": nm(e["book"]), "price": e["price"], "price_after_fee": round(net(e["price"], e["book"])),
            "point": e.get("pt"),
            "grade": e.get("grade"), "score": e.get("score"), "edge_pct": e.get("evp"), "late": bool(e.get("late")),
            "minutes_before_start": e.get("lead"), "confirm": e.get("conf"), "confirmed_by": e.get("cby", []),
            "sent_to_phone": not e.get("muted", False),
            "top25": e.get("t25"), "result": res["r"] if res else None, "final": res["score"] if res else None,
            "beat_close": (g[0] > 0) if g else None, "clv": g[1] if g else None,
            "units_flat": round(units(e, res["r"]), 2) if res else None})
    first_text = {}
    for x in sorted(st.get("sent", []), key=lambda x: x["t"]):
        first_text.setdefault((x["ev"], x["kind"], x["side"]), x.get("text"))
    for row, e in zip(out, sorted(st["log"], key=lambda x: x["start"], reverse=True)):
        cl = e.get("cl") or {}
        row.update({"close_fair_prob": cl.get("p"), "close_value_pct": cl.get("ev"),
                    "beat_true_close": (cl["ev"] > 0) if cl else None, "close_read_mins_before": cl.get("mins_before"),
                    "executable_book": executable(e, first_text.get((e["ev"], e["kind"], e["side"])))})
    bets = {(e["ev"], e["kind"], e["side"]): e for e in st["log"]}
    every = []
    for e in sorted(st.get("sent", []), key=lambda x: x["t"], reverse=True):
        b = bets.get((e["ev"], e["kind"], e["side"]), {})
        res = b.get("res")
        every.append({
            "sent_et": datetime.fromtimestamp(e["t"], ET).strftime("%Y-%m-%d %H:%M"), "start_utc": e["start"],
            "game": e["game"], "sport": e["sport"], "bet": describe(e), "book": nm(e["book"]), "price": e["price"],
            "price_after_fee": round(net(e["price"], e["book"])),
            "alert_text": e.get("text"), "why": e.get("why"), "grade": e.get("grade"), "score": e.get("score"),
            "edge_pct": e.get("evp"), "confirmed_by": e.get("cby", []), "late": bool(e.get("late")),
            "minutes_before_start": e.get("lead"), "repeat": e["repeat"], "pushed_to_phone": e["pushed"],
            "bet_result": res["r"] if res else None, "final": res["score"] if res else None})
    try:
        with open(path, "w") as f:
            json.dump({"note": ("alerts = one entry per bet (game/market/side), used for the record; result W/L/P or null. "
                                "all_alerts = every alert sent, newest first, repeats marked repeat=true (logged from Oct 21). "
                                "units_flat = 1u risked at the first alert's price, after the book's fee on winnings (ProphetX 2%; price_after_fee). "
                                "Edge, the -130 cap, best-book choice and CLV all use price_after_fee. "
                                "close_value_pct = TRUE closing value (from Oct 25): expected profit per 1u of price_after_fee at Pinnacle's "
                                "no-vig win chance from one final read just before start, at the play's own number; beat_true_close = "
                                "close_value_pct > 0. The older beat_close/clv fields beat the close almost by construction (ignore). "
                                "executable_book = the alert book or an 'also' book is Novig/Kalshi/ProphetX/Polymarket. pushed_to_phone/sent_to_phone = not muted "
                                "(delivery to the phone is not confirmed)."),
                       "alerts": out, "all_alerts": every}, f, indent=1, sort_keys=True)
    except Exception as ex:
        print(f"alerts file failed: {ex}")


CONF_LABEL = {"yes": "Yes", "na": "Pinnacle only", "off": "-"}


def write_summary(st, n):
    """Table of the last 30 days' alerts (result, score, vs close) on the GitHub run page."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    month = graded(st, n, 30)
    w, l, p, u = record(month)
    clv = [x for x in month if x[1]]
    beat = sum(1 for _, g in clv if g[0] > 0)
    rows = ["| Date | Sport | Bet | Book | Confirmed | Grade | Timing | Result | Score | vs close |", "|---|---|---|---|---|---|---|---|---|---|"]
    for e, g in sorted(month, key=lambda x: x[0]["start"], reverse=True):
        d = parse_iso(e["start"]).astimezone(ET).strftime("%b %-d")
        res = e.get("res")
        c = (ICON["W" if g[0] > 0 else ("P" if g[0] == 0 else "L")] + " " + g[1]) if g else ""
        gr = (f"{e['grade']} {e['score']}" if e.get("grade") else "") + (f" / {e['evp']:+.1f}%" if e.get("evp") is not None else "")
        tm = (("LATE " if e.get("late") else "") + lead_text(e["lead"])) if "lead" in e else ""
        rows.append(f"| {d} | {e['sport']} | {describe(e)} | {nm(e['book'])} | {CONF_LABEL.get(e.get('conf'), '')}{' (' + str(e['nconf']) + ')' if e.get('nconf') else ''} | {gr} | {tm} | "
                    f"{ICON[res['r']] + ' ' + res['r'] if res else ''} | {res['score'] if res else ''} | {c} |")
    pending = sum(1 for e in st["log"] if parse_iso(e["start"]) > n)
    with open(path, "a") as f:
        f.write(f"## Sharp alerts, last 30 days\n\n**Record {w}-{l}-{p} ({u:+.2f}u flat).** "
                f"{beat} of {len(clv)} beat {nm(SHARP)}'s close. {pending} alert(s) waiting for their game to start.\n\n"
                + "\n".join(rows) + "\n")


# ---------------------------------------------------------------- main loop
def poll_interval_min(st, active_sports):
    """Spread the remaining monthly credits across the rest of the month."""
    rem = st.get("remaining")
    if rem is None:
        return 0  # unknown: poll once to learn the balance
    n = now_utc().astimezone(ET)
    nxt = (n.replace(day=28) + timedelta(days=4)).replace(day=1)
    days_left = max((nxt.date() - n.date()).days, 1)
    daily = max(rem - RESERVE, 0) / days_left
    cost = sum(len(SPORTS[s]["markets"]) * math.ceil(len(BOOKS) / 10) for s in active_sports)
    if daily <= 0 or cost == 0:
        return float("inf")
    active_min = (ACTIVE_END_ET - ACTIVE_START_ET) * 60
    return max(MIN_INTERVAL, active_min * cost / daily)


def run():
    if not KEY:
        sys.exit("Set ODDS_API_KEY")
    st = load_state()
    st.setdefault("hist", {})
    st.setdefault("last_poll", {})
    st.setdefault("alerted", {})
    st.setdefault("log", [])
    n = now_utc()
    hour_et = n.astimezone(ET).hour
    before_cl = sum(1 for e in st["log"] if e.get("cl"))
    closing_reads(st, n)   # true closing line: final Pinnacle read just before each start (any hour)
    if not (ACTIVE_START_ET <= hour_et < ACTIVE_END_ET):
        # no odds polling overnight, but keep grading finished games (ESPN is free) so late games don't wait till morning
        before = sum(1 for e in st["log"] if e.get("res"))
        settle_pending(st, n)
        if sum(1 for e in st["log"] if e.get("res")) != before or sum(1 for e in st["log"] if e.get("cl")) != before_cl:
            save_state(st)
            write_alerts_file(st, n)
        print("Outside active hours; graded finished games only.")
        return
    settle_pending(st, n)  # final scores + W/L for finished games
    recap(st, n)  # once a day: how yesterday's alerts did (W/L, score, closing line)
    weekly_recap(st, n)  # Mondays: last Monday-Sunday totals

    # Free endpoints: which sports are in season, and which have games soon.
    sports, _ = http_get("/sports", {})
    in_season = {s["key"] for s in sports if s.get("active")}
    active = []
    for key in SPORTS:
        if (ONLY and key not in ONLY) or key not in in_season:
            continue
        evs, _ = http_get(f"/sports/{key}/events", {
            "commenceTimeFrom": iso(n), "commenceTimeTo": iso(n + timedelta(hours=LOOKAHEAD_H))})
        if evs:
            active.append(key)
    interval = poll_interval_min(st, active)
    print(f"Books: {SHARP} (sharp)" + (f" + {CONFIRM} (confirm)" if CONFIRM else "") + f" vs {RETAIL}")
    print(f"Active sports: {active}; credits left: {st.get('remaining')}; interval: {interval:.0f} min")

    books = ",".join(BOOKS)
    sent = 0
    top25 = load_top25(st, n) if (NCAAF_TOP25 != "off" and "americanfootball_ncaaf" in active) else None
    for key in active:
        if st.get("remaining") is not None and st["remaining"] <= RESERVE:
            print("Credit reserve reached; stopping.")
            break
        last = st["last_poll"].get(key, 0)
        if time.time() - last < interval * 60:
            continue
        cfg = SPORTS[key]
        events, rem = http_get(f"/sports/{key}/odds", {
            "bookmakers": books, "markets": ",".join(cfg["markets"]), "oddsFormat": "american",
            "commenceTimeFrom": iso(n), "commenceTimeTo": iso(n + timedelta(hours=LOOKAHEAD_H))})
        if rem is not None:
            st["remaining"] = rem
        st["last_poll"][key] = time.time()
        for ev in events:
            lines = book_lines(ev)
            vals = sharp_values(lines)
            if not vals:
                continue
            for e in st["log"]:  # keep each pending alert's closing number current
                if e["ev"] == ev["id"]:
                    c = close_value(e, vals)
                    if c is not None:
                        e["close"] = c
            h = st["hist"].setdefault(ev["id"], {"start": ev["commence_time"], "obs": []})
            cutoff = time.time() - WINDOW_H * 3600
            # Keep readings inside the window; if polls are spaced wider than the window,
            # keep the most recent older reading so there is always something to compare to.
            h["obs"] = [o for o in h["obs"] if o[0] >= cutoff] or h["obs"][-1:]
            if h["obs"]:
                # baseline: earliest value seen in the window for each market key
                base = {}
                for _, v in h["obs"]:
                    for k, x in v.items():
                        base.setdefault(k, x)
                is_t25, tag = (top25_tag(ev, top25) if key == "americanfootball_ncaaf" and NCAAF_TOP25 != "off"
                               else (None, ""))
                for a in detect(ev, cfg, lines, base):
                    if a["id"] in st["alerted"]:
                        continue
                    lead = (parse_iso(a["commence"]) - now_utc()).total_seconds() / 60
                    late = lead < LATE_MIN
                    a["sport"] = cfg["label"]
                    score, grade = confidence(a, st, n, lead)
                    # repeat = the line kept moving on a bet already alerted (same game/market/side)
                    repeat = any(x["ev"] == a["ev"] and x["kind"] == a["kind"] and x["side"] == a["side"]
                                 for x in st["log"])
                    # earlier alert on this game: the first alert is the play (opposite side = do not bet)
                    mkt = lambda k: "spr" if k in ("spr", "rl") else k
                    prior = sorted((x for x in st["log"] if x["ev"] == a["ev"] and not (x["kind"] == a["kind"] and x["side"] == a["side"])),
                                   key=lambda x: x.get("t", 0))
                    opp = [x for x in prior if mkt(x["kind"]) == mkt(a["kind"])]
                    prior_note = ""
                    if opp:
                        prior_note = f"\nOPPOSITE of earlier alert {describe(opp[0])} - first alert is the play, don't bet this"
                    elif prior:
                        prior_note = f"\nEarlier alert on this game: {describe(prior[0])} - first alert is the play"
                    if is_t25 is False and NCAAF_TOP25 == "filter":
                        print(f"Skipped (non-Top 25): {a['text']} | {a['game']}")
                    elif late and LATE_MODE == "mute":
                        print(f"Not sent (late, {lead_text(lead)} to start): {a['text']} | {a['game']}")
                    elif repeat and REPEAT_MODE == "mute":
                        print(f"Not sent (repeat): {a['text']} | {a['game']}")
                    else:
                        notify(f"Sharp alert {cfg['label']}" + (" LATE" if late else ""),
                               f"{a['text']}\n{bet_size(a['price'], a['book'])}{prior_note}\n{a['game']}{tag}, {a['start']}\n{a['why']}\n"
                               f"Grade {grade} ({score}/100)" + (f" | Edge {a['evp']:+.1f}%" if a.get("evp") is not None else "") + " | "
                               + (f"LATE: starts in {lead_text(lead)}" if late else f"starts in {lead_text(lead)}"),
                               red=late, yellow=(not late) and bool(prior or (repeat and REPEAT_MODE != "mute")))   # late = red only
                    st["alerted"][a["id"]] = time.time()
                    e = {k: a[k] for k in ("id", "ev", "game", "kind", "side", "pt", "price", "book", "conf", "nconf", "cby", "evp")}
                    e.update(sport=cfg["label"], start=a["commence"], t=time.time(), lead=round(lead), late=late,
                             score=score, grade=grade)
                    if is_t25 is not None:
                        e["t25"] = is_t25
                        e["muted"] = bool(is_t25 is False and NCAAF_TOP25 == "filter")
                    e["close"] = close_value(e, vals)
                    # one scorecard entry per bet, even if the line keeps moving
                    if not repeat:
                        st["log"].append(e)
                    # every alert, repeats included (the record above still counts one bet per game/market/side)
                    st.setdefault("sent", []).append(dict(e, repeat=repeat, text=a["text"], why=a["why"],
                                                          pushed=not e.get("muted") and not (late and LATE_MODE == "mute")
                                                          and not (repeat and REPEAT_MODE == "mute")))
                    sent += 0 if ((is_t25 is False and NCAAF_TOP25 == "filter") or (late and LATE_MODE == "mute")
                                  or (repeat and REPEAT_MODE == "mute")) else 1
            h["obs"].append([time.time(), vals])

    # Tidy: drop started games and old alert keys.
    st["hist"] = {k: v for k, v in st["hist"].items() if parse_iso(v["start"]) > n}
    st["alerted"] = {k: t for k, t in st["alerted"].items() if t > time.time() - 3 * 86400}
    st["log"] = [e for e in st["log"] if parse_iso(e["start"]) > n - timedelta(days=LOG_DAYS)]
    st["sent"] = [e for e in st.get("sent", []) if parse_iso(e["start"]) > n - timedelta(days=LOG_DAYS)]
    save_state(st)
    write_summary(st, n)
    write_alerts_file(st, n)
    print(f"Done. Alerts sent: {sent}. Credits left: {st.get('remaining')}")


if __name__ == "__main__":
    run()
