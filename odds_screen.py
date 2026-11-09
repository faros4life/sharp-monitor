"""Nov 5: odds screen feed (odds_screen.json) - every game, every one of Peter's books, side by side.

Built from the odds sharp_monitor.py already pulls each poll: 0 extra Odds API credits.
All college football games are included (no Top 25 filter); Top 25 games carry their rank so the page can flag them.
Books shown are RETAIL_BOOKS (Hard Rock FL, ProphetX, Novig, Kalshi, Polymarket US; plus FanDuel/DraftKings/BetMGM
when the RETAIL_BOOKS variable is set for NY). Pinnacle rides along as the fair-price reference.
Each sport is replaced when it is polled and kept otherwise; games past their start are dropped.
Viewing screen only: it sends no alerts.
"""
import json
import os
import time
from datetime import datetime, timezone

FILE = os.environ.get("ODDS_SCREEN_FILE", "") or "odds_screen.json"
WEEK_LG = ("NFL", "NCAAF")   # Nov 9: shown all week on the screen
_new = {}   # sport label -> list of games from this run


def _prob(am):
    return 100 / (am + 100) if am > 0 else -am / (-am + 100)


def _am(p):
    if p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def _fair(two):
    """No-vig American price for each side of a two-way market {side: price}."""
    if len(two) != 2:
        return {}
    (a, pa), (b, pb) = two.items()
    qa, qb = _prob(pa), _prob(pb)
    s = qa + qb
    return {a: _am(qa / s), b: _am(qb / s)}


def add(label, event, lines, rank_info, show_books, sharp):
    """Record one game. lines = sharp_monitor.book_lines(event); rank_info = list of (team, rank) for Top 25 teams."""
    books = {}
    for bk in list(show_books) + [sharp]:
        d = lines.get(bk)
        if not d:
            continue
        b = {}
        if d.get("spreads"):
            b["s"] = {t: [pt, px] for t, (pt, px) in d["spreads"].items()}
        if d.get("totals"):
            b["t"] = {t: [pt, px] for t, (pt, px) in d["totals"].items()}
        if d.get("h2h"):
            b["m"] = dict(d["h2h"])
        if b:
            books[bk] = b
    if not books:
        return
    links = {}   # Nov 5: deepest link each book gives (outcome > market > event), per market and side
    for bk in event.get("bookmakers", []):
        if bk["key"] not in books:
            continue
        L = {"e": bk.get("link")}
        for m in bk.get("markets", []):
            short = {"spreads": "s", "totals": "t", "h2h": "m"}.get(m["key"])
            if not short:
                continue
            for o in m.get("outcomes", []):
                u = o.get("link") or m.get("link") or bk.get("link")
                if u:
                    L.setdefault(short, {})[o["name"]] = u
        L = {k: v for k, v in L.items() if v}
        if L:
            links[bk["key"]] = L
    fair = {}
    p = lines.get(sharp, {})
    for mk, short in (("spreads", "s"), ("totals", "t")):
        sides = p.get(mk) or {}
        pts = {round(abs(pt), 2) for pt, _ in sides.values()}
        if len(sides) == 2 and len(pts) == 1:   # both sides on the same number
            f = _fair({k: px for k, (pt, px) in sides.items()})
            fair[short] = {k: [sides[k][0], v] for k, v in f.items()}
    if p.get("h2h"):
        f = _fair(p["h2h"])
        if f:
            fair["m"] = f
    _new.setdefault(label, []).append({
        "id": event["id"], "lg": label, "start": event["commence_time"],
        "away": event["away_team"], "home": event["home_team"],
        "t25": [[t, r] for t, r in (rank_info or [])], "books": books, "fair": fair, "links": links})


def save(retail, sharp, names, remaining=None):
    """Merge this run's sports into the published file."""
    try:
        old = json.load(open(FILE))
    except Exception:
        old = {}
    by = {}
    for g in old.get("games", []):
        by.setdefault(g["lg"], []).append(g)
    now = time.time()
    for lg, gs in _new.items():
        for g in gs:
            g["upd"] = round(now)
        # Nov 9 (Peter: "show cfb and nfl all week"): a 24h monitor pull must not wipe the week-ahead games
        # from the weekly screen pull - keep old games that start after this pull's last game.
        ids = {g["id"] for g in gs}
        last = max((g["start"] for g in gs), default="")
        keep = [g for g in by.get(lg, []) if g["id"] not in ids and g["start"] > last and lg in WEEK_LG]
        by[lg] = gs + keep
    games = []
    for lg, gs in by.items():
        for g in gs:
            try:
                st = datetime.fromisoformat(g["start"].replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if st > now:
                games.append(g)
    games.sort(key=lambda g: (g["start"], g["lg"], g["away"]))
    sports = dict(old.get("sports", {}))
    for lg in _new:
        sports[lg] = now
    out = {"updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "books": list(retail), "sharp": sharp,
           "names": {b: names.get(b, b) for b in list(retail) + [sharp]},
           "sports": sports, "games": games,
           "credits_left": remaining if remaining is not None else old.get("credits_left")}
    for k in ("fast_poll", "week_poll"):   # Nov 9: keep poll timers across monitor saves
        if k in old:
            out[k] = old[k]
    tmp = FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    os.replace(tmp, FILE)
    _new.clear()
