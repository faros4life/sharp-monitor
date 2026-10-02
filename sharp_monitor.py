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
SHARP = os.environ.get("SHARP_BOOK", "pinnacle")
RETAIL = [b.strip() for b in os.environ.get(
    "RETAIL_BOOKS", "draftkings,fanduel,betmgm,williamhill_us,espnbet,betrivers"
).split(",") if b.strip()]
LOOKAHEAD_H = float(os.environ.get("LOOKAHEAD_HOURS", "24"))
WINDOW_H = float(os.environ.get("MOVE_WINDOW_HOURS", "6"))   # compare against lines seen in this window
ACTIVE_START_ET = int(os.environ.get("ACTIVE_START_ET", "9"))  # only poll 9am..midnight ET
ACTIVE_END_ET = int(os.environ.get("ACTIVE_END_ET", "24"))
RESERVE = int(os.environ.get("CREDIT_RESERVE", "15"))          # never spend below this
MIN_INTERVAL = float(os.environ.get("MIN_INTERVAL_MIN", "5"))  # fastest polling per sport
ONLY = [s.strip() for s in os.environ.get("SPORTS", "").split(",") if s.strip()]

SPORTS = {
    "americanfootball_nfl":   dict(label="NFL",   markets=["spreads", "totals"], spread=1.0, total=1.0, keys=[3, 7]),
    "americanfootball_ncaaf": dict(label="NCAAF", markets=["spreads", "totals"], spread=1.0, total=1.0, keys=[3, 7]),
    "basketball_nba":         dict(label="NBA",   markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    "basketball_wnba":        dict(label="WNBA",  markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    "basketball_ncaab":       dict(label="NCAAB", markets=["spreads", "totals"], spread=1.0, total=1.5, keys=[]),
    "baseball_mlb":           dict(label="MLB",   markets=["h2h", "totals"], ml=0.03, total=0.5),
    "icehockey_nhl":          dict(label="NHL",   markets=["h2h", "totals"], ml=0.03, total=0.5),
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


def sharp_values(lines):
    """Flatten the sharp book's lines into comparable values: {mkey: value}."""
    v = {}
    sb = lines.get(SHARP, {})
    for team, (pt, _) in sb.get("spreads", {}).items():
        v[f"spreads|{team}"] = pt
    if "Over" in sb.get("totals", {}):
        v["totals|Over"] = sb["totals"]["Over"][0]
    h = sb.get("h2h", {})
    if len(h) == 2:  # no-vig win probabilities
        probs = {t: am_to_prob(p) for t, p in h.items()}
        tot = sum(probs.values())
        for t, p in probs.items():
            v[f"h2h|{t}"] = p / tot
    return v


def crossed_key(old, new, keys):
    lo, hi = sorted((abs(old), abs(new)))
    return any(lo <= k <= hi and lo != hi for k in keys) if keys else False


# ---------------------------------------------------------------- detection
def detect(event, cfg, lines, base):
    """Compare sharp lines now vs. baseline values; return list of alert dicts."""
    alerts = []
    sb = lines.get(SHARP, {})
    retail = {b: lines[b] for b in RETAIL if b in lines}
    game = f"{event['away_team']} @ {event['home_team']}"
    start = parse_iso(event["commence_time"]).astimezone(ET).strftime("%a %-I:%M %p ET")

    # Spreads: sharp side = team whose number got worse (money pushed it).
    for team, (new, _) in sb.get("spreads", {}).items():
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
            alerts.append(dict(
                id=f"{event['id']}|spr|{team}|{new}", game=game, start=start,
                text=f"{team} {fmt_pt(pt)} ({fmt_price(pr)}) at {b}",
                why=f"{SHARP} moved {fmt_pt(old)} -> {fmt_pt(new)}; bet only at {fmt_pt(new + 0.5)} or better"))

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
                    alerts.append(dict(
                        id=f"{event['id']}|tot|{side}|{new}", game=game, start=start,
                        text=f"{side} {pt:g} ({fmt_price(pr)}) at {b}",
                        why=f"{SHARP} total moved {old:g} -> {new:g}; bet only at {thr:g} or better"))

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
            if am_to_prob(pr) < new:  # retail price beats the sharp fair price
                alerts.append(dict(
                    id=f"{event['id']}|ml|{team}|{round(new, 2)}", game=game, start=start,
                    text=f"{team} ML {fmt_price(pr)} at {b}",
                    why=(f"{SHARP} fair moved {fmt_price(prob_to_am(old))} -> {fmt_price(prob_to_am(new))}; "
                         f"bet only at {fmt_price(prob_to_am(new))} or better")))
    return alerts


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
    cost = sum(len(SPORTS[s]["markets"]) * math.ceil((len(RETAIL) + 1) / 10) for s in active_sports)
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
    n = now_utc()
    hour_et = n.astimezone(ET).hour
    if not (ACTIVE_START_ET <= hour_et < ACTIVE_END_ET):
        print("Outside active hours; skipping.")
        return

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
    print(f"Active sports: {active}; credits left: {st.get('remaining')}; interval: {interval:.0f} min")

    books = ",".join([SHARP] + RETAIL)
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
            h = st["hist"].setdefault(ev["id"], {"start": ev["commence_time"], "obs": []})
            cutoff = time.time() - WINDOW_H * 3600
            h["obs"] = [o for o in h["obs"] if o[0] >= cutoff]
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
                    sent += 1
            h["obs"].append([time.time(), vals])

    # Tidy: drop started games and old alert keys.
    st["hist"] = {k: v for k, v in st["hist"].items() if parse_iso(v["start"]) > n}
    st["alerted"] = {k: t for k, t in st["alerted"].items() if t > time.time() - 3 * 86400}
    save_state(st)
    print(f"Done. Alerts sent: {sent}. Credits left: {st.get('remaining')}")


if __name__ == "__main__":
    run()
