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
CONFIRM = os.environ.get("CONFIRM_BOOK", "") or "betonlineag"
if CONFIRM.lower() == "none":
    CONFIRM = ""
BOOKS = list(dict.fromkeys([SHARP] + RETAIL + ([CONFIRM] if CONFIRM else [])))
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


def notify(title, body):
    if not NTFY_TOPIC:
        print(f"[dry-run alert] {title}\n{body}\n")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST",
        headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": "moneybag"})
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
         "pinnacle": "Pinnacle", "betonlineag": "BetOnline", "lowvig": "LowVig"}


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


def crossed_key(old, new, keys):
    lo, hi = sorted((abs(old), abs(new)))
    return any(lo <= k <= hi and lo != hi for k in keys) if keys else False


# ---------------------------------------------------------------- detection
def detect(event, cfg, lines, base):
    """Compare sharp lines now vs. baseline values; return list of alert dicts."""
    alerts = []
    sb = lines.get(SHARP, {})
    retail = {b: lines[b] for b in RETAIL if b in lines}
    cv = sharp_values(lines, CONFIRM) if CONFIRM else {}
    game = f"{event['away_team']} @ {event['home_team']}"
    start = parse_iso(event["commence_time"]).astimezone(ET).strftime("%a %-I:%M %p ET")

    def agree(key, old, new):
        """Does the confirm book sit on the moved side of the sharp move? yes / no / na (no line)."""
        if not CONFIRM:
            return "off"
        c = cv.get(key)
        if c is None:
            return "na"
        mid = (old + new) / 2
        return "yes" if ((c <= mid + 1e-9) if new < old else (c >= mid - 1e-9)) else "no"

    def add(kind, side, pt, price, book, new_key, text, why, conf):
        if conf == "no":
            return  # confirm book disagrees: likely noise or stale sharp data
        note = {"yes": f" (confirmed by {nm(CONFIRM)})", "na": f" ({nm(SHARP)} only)", "off": ""}[conf]
        alerts.append(dict(id=f"{event['id']}|{new_key}", ev=event["id"], game=game, start=start,
                           commence=event["commence_time"], kind=kind, side=side, pt=pt, price=price,
                           book=book, conf=conf, text=text, why=why + note))

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
        pt, pr, b = max(offers, key=lambda x: (x[0], x[1]))
        if pt > new:
            add("spr", team, pt, pr, b, f"spr|{team}|{new}",
                f"{team} {fmt_pt(pt)} ({fmt_price(pr)}) at {nm(b)}" + also([x[2] for x in offers if x[0] > new], b),
                f"{nm(SHARP)} moved {fmt_pt(old)} -> {fmt_pt(new)}; bet only at {fmt_pt(new + 0.5)} or better",
                agree(f"spreads|{team}", old, new))

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
                    pt, pr, b = min(offers, key=lambda x: (x[0], -x[1]))
                    ok, thr = pt < new, new - 0.5
                else:
                    pt, pr, b = max(offers, key=lambda x: (x[0], x[1]))
                    ok, thr = pt > new, new + 0.5
                if ok:
                    add("tot", side, pt, pr, b, f"tot|{side}|{new}",
                        f"{side} {pt:g} ({fmt_price(pr)}) at {nm(b)}"
                        + also([x[2] for x in offers if (x[0] < new if side == "Over" else x[0] > new)], b),
                        f"{nm(SHARP)} total moved {old:g} -> {new:g}; bet only at {thr:g} or better",
                        agree("totals|Over", old, new))

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
            pr, b = max(offers, key=lambda x: 1 / am_to_prob(x[0]))
            if edge_ok(pr, new):
                add("rl", team, pt, pr, b, f"rl|{team}|{pt:g}|{round(new, 2)}",
                    f"{team} {fmt_pt(pt)} {cfg.get('rl_name', 'RL')} {fmt_price(pr)} at {nm(b)}"
                    + also([x[1] for x in offers if edge_ok(x[0], new)], b),
                    (f"{nm(SHARP)} {fmt_pt(pt)} fair moved {fmt_price(prob_to_am(old))} -> "
                     f"{fmt_price(prob_to_am(new))}; bet only at {fmt_price(edge_price(new))} or better"),
                    agree(k, old, new))

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
            pr, b = max(offers, key=lambda x: 1 / am_to_prob(x[0]))
            if edge_ok(pr, new):  # retail price beats the sharp fair price by MIN_EDGE
                add("ml", team, None, pr, b, f"ml|{team}|{round(new, 2)}",
                    f"{team} ML {fmt_price(pr)} at {nm(b)}" + also([x[1] for x in offers if edge_ok(x[0], new)], b),
                    (f"{nm(SHARP)} fair moved {fmt_price(prob_to_am(old))} -> {fmt_price(prob_to_am(new))}; "
                     f"bet only at {fmt_price(edge_price(new))} or better"),
                    agree(f"h2h|{team}", old, new))
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
    v = (c / am_to_prob(e["price"]) - 1) * 100   # % edge of your price vs closing fair odds
    return v, f"{v:+.1f}%"


def describe(e):
    if e["kind"] == "spr":
        return f"{e['side']} {fmt_pt(e['pt'])} ({fmt_price(e['price'])})"
    if e["kind"] == "tot":
        return f"{e['side']} {e['pt']:g} ({fmt_price(e['price'])})"
    if e["kind"] == "rl":
        return f"{e['side']} {fmt_pt(e['pt'])} {'PL' if e.get('sport') == 'NHL' else 'RL'} {fmt_price(e['price'])}"
    return f"{e['side']} ML {fmt_price(e['price'])}"


def graded(st, n, days=None):
    out = []
    for e in st["log"]:
        if parse_iso(e["start"]) > n:
            continue
        if days and parse_iso(e["start"]) < n - timedelta(days=days):
            continue
        g = grade(e)
        if g:
            out.append((e, g))
    return out


def recap(st, n):
    """Once per ET day: push a recap of newly graded alerts (if any)."""
    today = n.astimezone(ET).date().isoformat()
    if st.get("recap_day") == today:
        return
    st["recap_day"] = today
    new = [(e, g) for e, g in graded(st, n) if not e.get("reported")]
    for e, _ in new:
        e["reported"] = True
    if not new:
        return
    beat = sum(1 for _, (v, _) in new if v > 0)
    lines = [f"{'✅' if v > 0 else ('➖' if v == 0 else '❌')} {e['sport']} {describe(e)}: {t}"
             for e, (v, t) in new[:12]]
    month = graded(st, n, 30)
    mbeat = sum(1 for _, (v, _) in month if v > 0)
    body = (f"{beat} of {len(new)} alerts beat {nm(SHARP)}'s closing number.\n" + "\n".join(lines)
            + (f"\n+{len(new) - 12} more" if len(new) > 12 else "")
            + f"\nLast 30 days: {mbeat}/{len(month)} beat the close")
    notify("Sharp recap", body)


CONF_LABEL = {"yes": "Yes", "na": "Pinnacle only", "off": "-"}


def write_summary(st, n):
    """Table of the last 30 days' graded alerts on the GitHub run page."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    month = graded(st, n, 30)
    beat = sum(1 for _, (v, _) in month if v > 0)
    rows = ["| Date | Sport | Bet | Book | Confirmed | vs close |", "|---|---|---|---|---|---|"]
    for e, (v, t) in sorted(month, key=lambda x: x[0]["start"], reverse=True):
        d = parse_iso(e["start"]).astimezone(ET).strftime("%b %-d")
        rows.append(f"| {d} | {e['sport']} | {describe(e)} | {nm(e['book'])} | {CONF_LABEL.get(e.get('conf'), '')} | "
                    f"{'✅' if v > 0 else ('➖' if v == 0 else '❌')} {t} |")
    pending = sum(1 for e in st["log"] if parse_iso(e["start"]) > n)
    with open(path, "a") as f:
        f.write(f"## Sharp alerts vs closing line (last 30 days)\n\n**{beat} of {len(month)} beat "
                f"{nm(SHARP)}'s close.** {pending} alert(s) waiting for their game to start.\n\n"
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
    if not (ACTIVE_START_ET <= hour_et < ACTIVE_END_ET):
        print("Outside active hours; skipping.")
        return
    recap(st, n)  # once a day: how yesterday's alerts did vs the closing line

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
                for a in detect(ev, cfg, lines, base):
                    if a["id"] in st["alerted"]:
                        continue
                    notify(f"Sharp alert {cfg['label']}",
                           f"{a['text']}\n{a['game']}, {a['start']}\n{a['why']}")
                    st["alerted"][a["id"]] = time.time()
                    e = {k: a[k] for k in ("id", "ev", "game", "kind", "side", "pt", "price", "book", "conf")}
                    e.update(sport=cfg["label"], start=a["commence"], t=time.time())
                    e["close"] = close_value(e, vals)
                    # one scorecard entry per bet, even if the line keeps moving and we push again
                    if not any(x["ev"] == e["ev"] and x["kind"] == e["kind"] and x["side"] == e["side"]
                               for x in st["log"]):
                        st["log"].append(e)
                    sent += 1
            h["obs"].append([time.time(), vals])

    # Tidy: drop started games and old alert keys.
    st["hist"] = {k: v for k, v in st["hist"].items() if parse_iso(v["start"]) > n}
    st["alerted"] = {k: t for k, t in st["alerted"].items() if t > time.time() - 3 * 86400}
    st["log"] = [e for e in st["log"] if parse_iso(e["start"]) > n - timedelta(days=LOG_DAYS)]
    save_state(st)
    write_summary(st, n)
    print(f"Done. Alerts sent: {sent}. Credits left: {st.get('remaining')}")


if __name__ == "__main__":
    run()
