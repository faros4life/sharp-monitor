#!/usr/bin/env python3
"""
Exchange liquidity monitor (paper alerts) - Kalshi + Novig + Polymarket.

Reads public order books (no keys) for NFL / NCAAF / NBA / NHL games today and tomorrow (ET), main
markets only (moneyline, spread, total), and logs a paper alert when one side of a game's market has
heavy resting BIDS.

Rule (Peter): >= $50,000 bid depth on one side on one book AND >= $10,000 on that same side on
another book. Every $50k leg is logged; `rule_met` says whether a second book also had $10k+.
A third book (ProphetX) slots in once its API key arrives.

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
PM_TAGS = {"NFL": "nfl", "NCAAF": "cfb", "NBA": "nba", "NHL": "nhl"}
PM_MTYPE = {"moneyline": "moneyline", "spreads": "spread", "spread": "spread", "totals": "total", "total": "total"}
OUT_DIR = os.environ.get("LIQ_DIR", "") or "liquidity"
STATE_FILE = os.path.join(OUT_DIR, "state.json")
ALERTS_FILE = os.path.join(OUT_DIR, "alerts.json")
PRIMARY_MIN = float(os.environ.get("LIQ_PRIMARY_MIN", "") or "50000")
SECOND_MIN = float(os.environ.get("LIQ_SECOND_MIN", "") or "10000")
LEAGUES = [x.strip().upper() for x in (os.environ.get("LIQ_LEAGUES", "") or "NFL,NCAAF,NBA,NHL").split(",") if x.strip()]
BOOKS = [x.strip().lower() for x in (os.environ.get("LIQ_BOOKS", "") or "kalshi,novig,polymarket").split(",") if x.strip()]
MAX_CALLS = int(os.environ.get("LIQ_MAX_BOOKS", "") or "900")          # order-book calls per book per run
SLEEP = float(os.environ.get("LIQ_SLEEP", "") or "0.06")
BUDGET_S = float(os.environ.get("LIQ_BUDGET_SEC", "") or "150")   # max seconds reading books, per exchange, per run
T0 = time.time()


def start_clock():
    global T0
    T0 = time.time()


def out_of_time():
    return time.time() - T0 > BUDGET_S


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
RATIO = float(os.environ.get("LIQ_RATIO", "") or "3")       # alert side needs >= 3x the other side's near depth
NTFY_TOPIC = os.environ.get("LIQ_NTFY_TOPIC", "")                       # optional push; empty = file only
K_SERIES_RE = re.compile(r"^KX(" + "|".join(LEAGUES) + r")(GAME|SPREAD|TOTAL)$")
K_MTYPE = {"GAME": "moneyline", "SPREAD": "spread", "TOTAL": "total"}
N_MTYPE = {"MONEY": "moneyline", "MONEYLINE": "moneyline", "SPREAD": "spread", "TOTAL": "total"}
N_LEAGUE = {"NFL": "NFL", "NBA": "NBA", "NHL": "NHL", "NCAAF": "NCAAF", "NCAAFB": "NCAAF", "CFB": "NCAAF",
            "COLLEGE FOOTBALL": "NCAAF", "NCAA FOOTBALL": "NCAAF"}
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


def toks(s):
    base = {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and not re.fullmatch(r"\d+(\.\d+)?", w)}
    for w in list(base):
        base |= ALIAS.get(w, set())
    return base


def split_teams(title):
    """'Charlotte at Brooklyn' / 'Charlotte Hornets @ Brooklyn Nets' -> ('Charlotte', 'Brooklyn')."""
    for sep in (" @ ", " at ", " vs. ", " vs ", " v "):
        if sep in (title or ""):
            a, b = title.split(sep, 1)
            return a.strip(), re.sub(r"\s*[\(\[:\-|].*$", "", b).strip()
    return None


def team_side(text, teams):
    """Which of the game's two teams does `text` name? 0, 1 or None."""
    t = toks(text)
    hits = [len(t & toks(x)) for x in teams]
    if hits[0] == hits[1]:
        return None
    return 0 if hits[0] > hits[1] else 1


def near_depth(levels):
    """$ of bids within NEAR of the best bid on this side (cheap far-off bids are not sharp money)."""
    if not levels:
        return 0.0
    best = max(p for p, _ in levels)
    return sum(p * q for p, q in levels if p >= best - NEAR - 1e-9)


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
    found = set()
    for params in ({"category": "Sports"}, {}):
        try:
            for s in k_paged("/series", "series", dict(params, limit=1000)):
                t = (s.get("ticker") or "").upper()
                if K_SERIES_RE.match(t):
                    found.add(t)
        except Exception as ex:
            print(f"Kalshi series listing failed ({params}): {ex}")
        if found:
            break
    return sorted(found or {f"KX{lg}{k}" for lg in LEAGUES for k in K_MTYPE})


def k_levels(book, side):
    for container in (book.get("orderbook_fp") or {}, book.get("orderbook") or {}):
        raw = container.get(f"{side}_dollars")
        if raw is not None:
            return [(float(p), float(q)) for p, q in raw]
    return [(float(p) / 100.0, float(q)) for p, q in ((book.get("orderbook") or {}).get(side) or [])]


def kalshi_rows(days):
    """[{book, league, date, teams, market, side(0/1/'OVER'/'UNDER'), depth, other_depth, price, ...}]"""
    rows, calls = [], 0
    start_clock()
    for s in k_series():
        m = K_SERIES_RE.match(s)
        league, kind = (m.group(1), m.group(2)) if m else (s[2:-4], "GAME")
        try:
            evs = k_paged("/events", "events", {"series_ticker": s, "status": "open", "with_nested_markets": "true", "limit": 200})
        except Exception as ex:
            print(f"Kalshi events failed for {s}: {ex}")
            continue
        for ev in evs:
            d = k_event_date(ev.get("event_ticker", ""))
            if d not in days:
                continue
            teams = split_teams(ev.get("title", ""))
            for mk in ev.get("markets") or []:
                if (mk.get("status") or "active") not in ("active", "open", "initialized") or calls >= MAX_CALLS:
                    continue
                liq = k_liquidity(mk)
                if liq is not None and liq < PRIMARY_MIN:
                    continue  # whole book (both sides) under $50k: can't trigger
                if K_MTYPE[kind] != "moneyline":
                    yb = k_price(mk, "yes_bid")
                    if yb is not None and not (0.2 <= yb <= 0.8):
                        continue  # far-off alternate strike, not the main line
                if out_of_time():
                    break
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
                for x in ("yes", "no"):
                    other = "no" if x == "yes" else "yes"
                    best_other = max((p for p, _ in bids[other]), default=None)
                    if K_MTYPE[kind] == "total":
                        over_yes = "under" not in label.lower()
                        side = ("OVER" if over_yes else "UNDER") if x == "yes" else ("UNDER" if over_yes else "OVER")
                    else:
                        t = team_side(label, teams) if teams else None
                        side = None if t is None else (t if x == "yes" else 1 - t)
                    rows.append(dict(book="kalshi", league=league, date=d.isoformat(), teams=list(teams) if teams else None,
                                     game=ev.get("title") or ev.get("event_ticker"), market=K_MTYPE[kind], side=side,
                                     side_label=label if x == "yes" else f"NOT {label}", depth=dep[x], other_depth=dep[other],
                                     total_depth=tot[x],
                                     price=round(1 - best_other, 4) if best_other is not None else None,
                                     ref={"market_ticker": mk["ticker"], "kalshi_side": x}))
    print(f"Kalshi: {calls} books read in {time.time() - T0:.0f}s" + (" (time budget hit)" if out_of_time() else ""))
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
    print(f"Novig: {len(ev_by)} events in leagues, market types seen: {seen_types}")
    rows, calls = [], 0
    for mk in mks:
        e = ev_by.get(mk.get("eventId"))
        mtype = N_MTYPE.get((mk.get("marketType") or "").upper())
        if not e or not mtype or mk.get("status") != "OPEN" or calls >= MAX_CALLS:
            continue
        if out_of_time():
            break
        try:
            book = get(f"{NOVIG}/v3/public/catalog/markets/{mk['marketId']}/book", {"depth": 20})
            calls += 1
        except Exception as ex:
            print(f"Novig book failed {mk['marketId']}: {ex}")
            continue
        orders = book.get("orders") or {}
        outs = mk.get("outcomes") or []
        if len(outs) != 2:
            continue  # main markets are two-way
        teams = split_teams(e.get("description") or mk.get("description") or "")
        d = datetime.fromtimestamp(e["startsTs"] / 1000, ET).date().isoformat()
        lv = {o["outcomeId"]: [(float(r["price"]), int(r["qty"])) for r in orders.get(o["outcomeId"], [])] for o in outs}
        dep = {k: near_depth(v) for k, v in lv.items()}
        tot = {k: sum(p * q for p, q in v) for k, v in lv.items()}
        for i, o in enumerate(outs):
            other = outs[1 - i]
            best_other = max((float(r["price"]) for r in orders.get(other["outcomeId"], [])), default=None)
            name = o.get("name") or ""
            if mtype == "total":
                side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
            else:
                side = team_side(name, teams) if teams else None
            strike = mk.get("strike")
            rows.append(dict(book="novig", league=N_LEAGUE.get((e.get("league") or "").upper().strip()), date=d,
                             teams=list(teams) if teams else None, game=e.get("description"), market=mtype, side=side,
                             side_label=name + (f" ({strike})" if strike else ""), depth=dep[o["outcomeId"]],
                             other_depth=dep[other["outcomeId"]], total_depth=tot[o["outcomeId"]],
                             price=round(1 - best_other, 4) if best_other is not None else None,
                             ref={"market_id": mk["marketId"], "outcome_id": o["outcomeId"]}))
    print(f"Novig: {calls} books read in {time.time() - T0:.0f}s" + (" (time budget hit)" if out_of_time() else ""))
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
    for lg in LEAGUES:
        tag = PM_TAGS.get(lg)
        if not tag:
            continue
        evs, off = [], 0
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
            continue
        for ev in evs:
            teams = split_teams(ev.get("title", ""))
            if not teams:
                continue
            for mk in ev.get("markets") or []:
                mtype = PM_MTYPE.get((mk.get("sportsMarketType") or "").lower())
                if not mtype or mk.get("closed") or mk.get("active") is False:
                    continue
                start = pm_start(mk.get("gameStartTime") or ev.get("startTime") or ev.get("endDate"))
                if not start or start <= n or start.astimezone(ET).date() not in days:
                    continue
                outs, tids = jl(mk.get("outcomes")), jl(mk.get("clobTokenIds"))
                if len(outs) != 2 or len(tids) != 2 or calls >= MAX_CALLS:
                    continue
                pl = num(mk.get("liquidityClob")) or num(mk.get("liquidityNum")) or num(mk.get("liquidity"))
                if pl is not None and pl < PRIMARY_MIN:
                    continue  # whole book under $50k: can't trigger
                if out_of_time():
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
                line = mk.get("line")
                for i in (0, 1):
                    name = str(outs[i])
                    if mtype == "total":
                        side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                    else:
                        side = team_side(name, teams)
                    best_other = max((p for p, _ in bids[1 - i]), default=None)
                    rows.append(dict(book="polymarket", league=lg, date=start.astimezone(ET).date().isoformat(),
                                     teams=list(teams), game=ev.get("title"), market=mtype, side=side,
                                     side_label=name + (f" ({line})" if line not in (None, "") else ""),
                                     depth=dep[i], other_depth=dep[1 - i], total_depth=tot[i],
                                     price=round(1 - best_other, 4) if best_other is not None else None,
                                     ref={"pm_market_id": str(mk.get("id")), "outcome_index": i}))
    print(f"Polymarket: {calls} books read in {time.time() - T0:.0f}s" + (" (time budget hit)" if out_of_time() else ""))
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


# ---------------------------------------------------------------- matching across books
def game_key(row):
    """Same game on both books: same date and both teams' names overlap."""
    return row["league"], row["date"]


def same_game(a, b):
    if a["league"] != b["league"] or a["date"] != b["date"] or not a["teams"] or not b["teams"]:
        return None
    ta, tb = [toks(x) for x in a["teams"]], [toks(x) for x in b["teams"]]
    if ta[0] & tb[0] and ta[1] & tb[1]:
        return "same"
    if ta[0] & tb[1] and ta[1] & tb[0]:
        return "flipped"   # one book lists the teams in the other order
    return None


def same_side(a, b, how):
    if a["side"] is None or b["side"] is None:
        return False
    if a["market"] == "total":
        return a["side"] == b["side"]
    return a["side"] == (b["side"] if how == "same" else 1 - b["side"])


def side_key(r):
    if r["side"] in ("OVER", "UNDER"):
        return r["side"]
    if r["side"] is None or not r["teams"]:
        return r["side_label"]
    return r["teams"][r["side"]]


# ---------------------------------------------------------------- settlement, notify
def settle(alerts, n):
    today = n.astimezone(ET).date().isoformat()
    for a in alerts:
        if a.get("result") is not None or (a.get("date") or "9999") > today:
            continue
        try:
            r = {"kalshi": kalshi_result, "novig": novig_result, "polymarket": pm_result}[a["book"]](a["ref"])
        except Exception as ex:
            print(f"settle lookup failed {a['ref']}: {ex}")
            continue
        if r:
            a["result"] = r
            p = a.get("price")
            a["units_flat"] = round((1 - p) / p, 2) if (r == "W" and p) else (-1.0 if r == "L" else 0.0)
            a["settled_utc"] = n.strftime("%Y-%m-%dT%H:%M:%SZ")


def notify(title, body):
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(), "Tags": "droplet"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as ex:
        print(f"ntfy failed: {ex}")


# ---------------------------------------------------------------- main
def run():
    n = now_utc()
    today = n.astimezone(ET).date()
    days = {today, today + timedelta(days=1)}
    state = load(STATE_FILE, {"alerted": {}})
    alerts = load(ALERTS_FILE, {"alerts": []}).get("alerts", [])
    settle(alerts, n)

    rows = []
    if "kalshi" in BOOKS:
        rows += kalshi_rows(days)
    if "novig" in BOOKS:
        rows += novig_rows(days, n)
    if "polymarket" in BOOKS:
        rows += pm_rows(days, n)
    print(f"Rows: {len(rows)} (book/market/side)")

    fired = 0
    for r in rows:
        if r["depth"] < PRIMARY_MIN or r["depth"] < RATIO * r["other_depth"]:
            continue  # need $50k near the price AND one-sided (>= 3x the other side): two-sided size is market making
        key = f"{r['book']}|{json.dumps(r['ref'], sort_keys=True)}"
        if key in state["alerted"]:
            continue
        # same side of the same game & market on the other book(s): best depth there
        others = {}
        for o in rows:
            if o["book"] == r["book"] or o["market"] != r["market"]:
                continue
            how = same_game(r, o)
            if how and same_side(r, o, how):
                if o["depth"] > others.get(o["book"], {}).get("depth", -1):
                    others[o["book"]] = {"depth": round(o["depth"]), "price": o["price"], "label": o["side_label"]}
        second = {b: v for b, v in others.items() if v["depth"] >= SECOND_MIN}
        a = {
            "alerted_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ"), "book": r["book"], "league": r["league"],
            "date": r["date"], "game": r["game"], "market": r["market"], "side": side_key(r), "side_label": r["side_label"],
            "price": r["price"], "price_american": american(r["price"]),
            "depth_by_book": dict({r["book"]: {"this_side": round(r["depth"]), "other_side": round(r["other_depth"]),
                                                 "this_side_all_levels": round(r.get("total_depth", r["depth"])),
                                                 "ratio": round(r["depth"] / max(r["other_depth"], 1), 1)}},
                                  **{b: {"this_side": v["depth"], "label": v["label"], "price": v["price"]} for b, v in others.items()}),
            "second_book": sorted(second) if second else ("none_10k" if others else "no_match"),
            "rule_met": bool(second), "books_live": BOOKS, "ref": r["ref"], "result": None, "units_flat": None,
        }
        alerts.insert(0, a)
        state["alerted"][key] = a["alerted_utc"]
        fired += 1
        print(f"ALERT {a['league']} {a['game']} | {a['market']} {a['side_label']} | {r['book']} ${r['depth']:,.0f}"
              f" | 2nd: {a['second_book']}")
        notify(f"Liquidity {a['league']}" + (" RULE MET" if a["rule_met"] else ""),
               f"{a['side_label']} ({a['market']}) on {r['book']}\n{a['game']}\n"
               f"Bids ${r['depth']:,.0f} this side vs ${r['other_depth']:,.0f} other side\n"
               + (f"Price {r['price']:.2f} ({a['price_american']:+d})\n" if a['price_american'] else "")
               + "2nd book: " + (", ".join(f"{b} ${v['depth']:,}" for b, v in others.items()) or "no match"))

    cutoff = (n - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    alerts = [a for a in alerts if a["alerted_utc"] >= cutoff]
    state["alerted"] = {k: v for k, v in state["alerted"].items() if v >= cutoff}
    save(ALERTS_FILE, {"note": ("Liquidity paper alerts (Kalshi + Novig + Polymarket public books), newest first. One alert per book+market+side "
                                "with >= $%d resting bids within %.0fc of the best bid on that side and >= %gx the other side's near bids. rule_met = another book also had >= $%d on the same side "
                                "of the same game & market (second_book lists them; 'no_match' = game not found on the other book). "
                                "price = cost to buy that side when alerted (0-1). result W/L/P/VOID from the exchange's own "
                                "settlement; units_flat = 1u at price." % (PRIMARY_MIN, NEAR * 100, RATIO, SECOND_MIN)),
                       "alerts": alerts})
    save(STATE_FILE, state)
    print(f"Done. New alerts: {fired}. Open alerts: {sum(1 for a in alerts if a['result'] is None)}")


if __name__ == "__main__":
    try:
        run()
    except Exception as ex:
        print(f"Run failed: {ex}")
        sys.exit(1)
