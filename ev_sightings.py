#!/usr/bin/env python3
"""
EV SIGHTINGS - paper study, MEASUREMENT ONLY (approved by Peter, Oct 27, 2026).

Question: does "EV" on the four exchanges predict closing value?
  A  CROSS-BOOK  the best after-fee cost to buy a side is >= 2c under the MEDIAN after-fee cost of the other books
                 at the same line, with >= $250 bettable at that best price. qualifying = >= 3c.
  B  PINNACLE    the best gettable (>= $250) after-fee cost beats Pinnacle's no-vig fair at the SAME line by >= 3% EV
                 (EV = fair / cost - 1). ref_age_s = seconds from Pinnacle's own last_update for that market to our
                 read of the exchange price (staleness is a measured variable: buckets <60s / 60-300s / 300s+).

Scope (the brief's fallback scope; a true in-process piggyback would mean editing liquidity_monitor.py, which the
executor imports, or sharp_monitor.py, which wakes it): NFL / NCAAF / NBA, spreads + totals, pregame, games starting
in the next 24 h. Runs every 10 min (own workflow, same cadence as the liquidity monitor), 9am-midnight ET for reads;
closes and grading run at any hour from data already stored.

Per sighting: one record per trigger x game x market x line x side (the FIRST sighting is the record; later scans only
update last_seen_utc / scans_seen / max_*). Close = our last pregame read (mins_before_start says how close):
closing consensus = median across books of each book's no-vig mid; Pinnacle close = the sharp monitor's own
close_prob() at the sighting's number (half points priced in when Pinnacle moved; pin_close_same_line flags it).
clv_*_c = (close fair - sighting after-fee cost) x 100: positive = the sighting price beat the close.
Graded after the game from ESPN finals (the sharp monitor's settle), hypothetical flat 1u at the sighting's after-fee cost.

NEVER: places, changes or cancels orders; pushes notifications; touches alerts.json, liquidity/, books/ or any file
the live lanes read. Imports liquidity_monitor / sharp_monitor for read helpers only and never runs either.
Output: ev-study/ev_sightings.json + ev-study/README.md (the workflow commits them to the ev-study branch, not main).
`python ev_sightings.py --report` prints the summary (interim / final reports).
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LIQ_LEAGUES"] = "NFL,NCAAF,NBA"   # this process's copy of the helpers only
import liquidity_monitor as lm  # noqa: E402  read helpers only: get(), team matching, Kalshi/Novig/ProphetX parsing

ET = lm.ET
LEAGUES = ("NFL", "NCAAF", "NBA")
ODDS_SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba"}
ODDS_API = "https://api.the-odds-api.com/v4"
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_BOOKS = "pinnacle,prophetx,novig,kalshi,polymarket_us"   # <= 10 books = 1 credit per market; exchanges = log-only cross-check
ODDS_MIN_CREDITS = int(os.environ.get("EV_ODDS_MIN_CREDITS", "") or "25000")   # never draw the sharp monitor's budget below this
OUT_DIR = os.environ.get("EV_DIR", "") or "ev-study"
OUT_FILE = os.path.join(OUT_DIR, "ev_sightings.json")
WINDOW_H = 24
ACTIVE_ET = (9, 24)
BOOK_SEC = float(os.environ.get("EV_BOOK_SEC", "") or "180")   # per-book read budget (books read in parallel)
BAND = (0.15, 0.85)             # skip far alternate strikes before reading their books
A_MIN, A_QUAL, A_DEPTH = 0.02, 0.03, 250.0
B_MIN_EV, B_DEPTH = 0.03, 250.0
BOOKS = ("prophetx", "novig", "kalshi", "polymarket_us")
READ_BOOKS = [b.strip() for b in (os.environ.get("EV_BOOKS", "") or ",".join(BOOKS)).split(",") if b.strip()]   # off switch per book
TAKER = {"kalshi": 0.07, "polymarket_us": 0.0695}   # per $1 contract = coef x P x (1-P), as sharp_monitor / executor
PX_FEE = 0.02                                       # ProphetX: 2% of winnings
PMUS = "https://gateway.polymarket.us"
PMUS_SLUGS = {"NFL": ["nfl"], "NBA": ["nba"], "NCAAF": ["cfb", "ncaaf", "college-football"]}
LOG = []


def say(msg):
    print(msg)
    LOG.append(msg)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def piso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def after_fee(book, c):
    """What one $1 of payout really costs after the book's fee (0-1)."""
    if c is None or not 0 < c < 1:
        return None
    if book == "prophetx":
        return 1 / (1 + (1 - PX_FEE) * (1 - c) / c)
    k = TAKER.get(book, 0.0)
    return c + k * c * (1 - c)


def am_prob(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def quote(book, lg, teams, start, date, market, side, line, cost, depth, opp_cost, ts, ref):
    return dict(book=book, league=lg, teams=list(teams) if teams else None, start=start, date=date, market=market,
                side=side, line=line, cost=cost, depth=round(depth or 0.0, 2), opp_cost=opp_cost, read_ts=ts, ref=ref)


def best_level(levels):
    """[(price, size)] -> (best price, total size at exactly that price) using the highest price."""
    if not levels:
        return None, 0.0
    p = max(x for x, _ in levels)
    return p, sum(q for x, q in levels if abs(x - p) < 1e-9)


# ---------------------------------------------------------------- Kalshi (public)
def read_kalshi(n, stop_at):
    out, todo = [], []
    days = {n.astimezone(ET).date(), (n + timedelta(hours=WINDOW_H)).astimezone(ET).date()}
    for lg in LEAGUES:
        for kind, mt in (("SPREAD", "spread"), ("TOTAL", "total")):
            try:
                evs = lm.k_paged("/events", "events", {"series_ticker": f"KX{lg}{kind}", "status": "open",
                                                       "with_nested_markets": "true", "limit": 200})
            except Exception as ex:
                say(f"Kalshi events failed KX{lg}{kind}: {str(ex)[:80]}")
                continue
            for ev in evs:
                d = lm.k_event_date(ev.get("event_ticker", ""))
                teams = lm.split_teams(ev.get("title", ""))
                if d not in days or not teams:
                    continue
                for mk in ev.get("markets") or []:
                    if (mk.get("status") or "active") not in ("active", "open"):
                        continue
                    ref = lm.k_price(mk, "yes_bid")
                    ref = ref if ref is not None else lm.k_price(mk, "yes_ask")
                    if ref is None or not BAND[0] <= ref <= BAND[1]:
                        continue
                    todo.append((lm.k_sort_time(mk), lg, mt, ev, teams, d, mk))
    todo.sort(key=lambda t: t[0])
    reads = 0
    for _, lg, mt, ev, teams, d, mk in todo:
        if time.time() > stop_at:
            say(f"Kalshi: time budget hit after {reads} of {len(todo)} books")
            break
        try:
            book = lm.get(f"{lm.KALSHI}/markets/{mk['ticker']}/orderbook")
            reads += 1
        except Exception as ex:
            say(f"Kalshi book failed {mk['ticker']}: {str(ex)[:60]}")
            continue
        ts = time.time()
        label = mk.get("yes_sub_title") or mk.get("subtitle") or mk.get("title") or ""
        strike = lm.num(mk.get("floor_strike"))
        if strike is None:
            m = re.search(r"over ([\d.]+)", label.lower())
            strike = float(m.group(1)) if m else None
        if strike is None:
            continue
        buy = {}
        for x in ("yes", "no"):   # buy YES = take the best NO bid at 1 - p (sizes are $1 contracts)
            p, q = best_level(lm.k_levels(book, "no" if x == "yes" else "yes"))
            buy[x] = (round(1 - p, 4), (1 - p) * q) if p is not None else (None, 0.0)
        for x in ("yes", "no"):
            o = "no" if x == "yes" else "yes"
            if mt == "total":
                over_yes = "under" not in label.lower()
                side = ("OVER" if over_yes else "UNDER") if x == "yes" else ("UNDER" if over_yes else "OVER")
                line = strike
            else:
                t = lm.team_side(label, teams, lg)
                if t is None:
                    continue
                side, line = (t, -strike) if x == "yes" else (1 - t, strike)   # YES "X wins by over S" = X -S
            out.append(quote("kalshi", lg, teams, lm.k_start(mk), d.isoformat(), mt, side, line, buy[x][0], buy[x][1],
                             buy[o][0], ts, {"ticker": mk["ticker"], "kalshi_side": x}))
    say(f"Kalshi: {reads} books read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- Novig (public, unsigned)
def read_novig(n, stop_at):
    lo, hi = int(n.timestamp() * 1000), int((n + timedelta(hours=WINDOW_H)).timestamp() * 1000)
    try:
        evs = lm.n_paged("/v3/public/catalog/events", {"startsAfter": lo, "startsBefore": hi, "limit": 5000})
        mks = lm.n_paged("/v3/public/catalog/markets", {"startsAfter": lo, "startsBefore": hi, "limit": 5000})
    except Exception as ex:
        say(f"Novig catalog failed: {str(ex)[:80]}")
        return []
    ev_by = {e["eventId"]: e for e in evs if lm.N_LEAGUE.get((e.get("league") or "").upper().strip()) in LEAGUES}
    todo = []
    for mk in mks:
        e = ev_by.get(mk.get("eventId"))
        mt = lm.N_MTYPE.get((mk.get("marketType") or "").upper())
        oc = mk.get("outcomes") or []
        if not e or mt not in ("spread", "total") or mk.get("status") != "OPEN" or len(oc) != 2:
            continue
        costs = [1 - b for b in (lm.num((o.get("bid") or {}).get("price")) for o in oc) if b is not None]
        if any(BAND[0] <= c <= BAND[1] for c in costs):
            todo.append((e.get("startsTs") or 0, e, mt, mk))
    todo.sort(key=lambda t: t[0])
    out, reads = [], 0
    for st, e, mt, mk in todo:
        if time.time() > stop_at:
            say(f"Novig: time budget hit after {reads} of {len(todo)} books")
            break
        try:
            book = lm.get(f"{lm.NOVIG}/v3/public/catalog/markets/{mk['marketId']}/book", {"depth": 20})
            reads += 1
        except Exception as ex:
            say(f"Novig book failed {mk['marketId']}: {str(ex)[:60]}")
            continue
        ts = time.time()
        orders, outs = book.get("orders") or {}, mk["outcomes"]
        lg = lm.N_LEAGUE.get((e.get("league") or "").upper().strip())
        teams = lm.split_teams(e.get("description") or mk.get("description") or "")
        buy = []
        for i in (0, 1):   # Novig orders are bids: buy outcome i = take the best bid on the other outcome at 1 - p
            lv = [(float(r["price"]), int(r["qty"]) / 100.0) for r in orders.get(outs[1 - i]["outcomeId"], [])]
            p, q = best_level(lv)
            buy.append((round(1 - p, 4), (1 - p) * q) if p is not None else (None, 0.0))
        d = datetime.fromtimestamp(st / 1000, ET).date().isoformat()
        for i, o in enumerate(outs):
            name, strike = o.get("name") or "", mk.get("strike")
            if mt == "total":
                side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                line = lm.num(strike)
            else:
                side = lm.team_side(name, teams, lg) if teams else None
                line = lm.signed_num(name)
                if line is None and lm.num(strike) is not None and side in (0, 1):
                    line = lm.num(strike) if side == 1 else -lm.num(strike)
            if side is None or line is None:
                continue
            out.append(quote("novig", lg, teams, st / 1000, d, mt, side, line, buy[i][0], buy[i][1], buy[1 - i][0], ts,
                             {"market_id": mk["marketId"], "outcome_id": o["outcomeId"]}))
    say(f"Novig: {reads} books read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- Polymarket US (public gateway; same routes as the executor)
def pmus_type(mk):
    smt = (mk.get("sportsMarketType") or mk.get("sportsMarketTypeV2") or mk.get("marketType") or "").lower()
    if "full_game" not in smt or any(w in smt for w in ("half", "quarter", "period", "inning", "team_total", "player")):
        return None
    if any(w in smt for w in ("spread", "handicap")):
        return "spread"
    if "total" in smt or "over_under" in smt:
        return "total"
    return None


def pmus_game_markets(ev, markets):
    gid = next((m.get("gameId") for m in markets if m.get("gameId")), None) or ev.get("gameId")
    tries = []
    if gid:
        tries.append((f"{PMUS}/v1/markets", {"gameId": gid, "limit": 100}))
    if ev.get("slug"):
        tries += [(f"{PMUS}/v1/events/slug/{ev['slug']}", None), (f"{PMUS}/v1/events", {"slug": ev["slug"]})]
    for url, params in tries:
        try:
            d = lm.get(url, params)
        except Exception:
            continue
        mks = d.get("markets") if isinstance(d, dict) else d
        if isinstance(d, dict) and not mks:
            mks = (d.get("event") or {}).get("markets")
        if isinstance(d, dict) and not mks and d.get("events"):
            mks = [m for e in d["events"] for m in (e.get("markets") or [])]
        if mks:
            return [m for m in mks if isinstance(m, dict)]
    return []


def pmus_px(x):
    v = x.get("px")
    return lm.num(v.get("value") if isinstance(v, dict) else v)


def read_pmus(n, stop_at):
    out, reads = [], 0
    games = []
    for lg in LEAGUES:
        evs = []
        for slug in PMUS_SLUGS[lg]:
            try:
                evs = (lm.get(f"{PMUS}/v2/leagues/{slug}/events", {"limit": 200}) or {}).get("events") or []
            except Exception:
                evs = []
            if evs:
                break
        for ev in evs:
            names = [t.get("name") for t in (ev.get("teams") or []) if t.get("name")]
            teams = tuple(names[:2]) if len(names) >= 2 else lm.split_teams(ev.get("title") or "")
            try:
                st = piso(str(ev.get("startTime") or ev.get("startDate") or ev.get("eventDate")))
            except Exception:
                continue
            if teams and n < st <= n + timedelta(hours=WINDOW_H):
                games.append((st, lg, ev, teams))
    games.sort(key=lambda g: g[0])
    for st, lg, ev, teams in games:
        if time.time() > stop_at:
            say(f"Polymarket US: time budget hit after {reads} books")
            break
        markets = list(ev.get("markets") or [])
        markets += pmus_game_markets(ev, markets)
        seen = set()
        for mk in markets:
            mt = pmus_type(mk)
            if mt is None or not mk.get("slug") or mk["slug"] in seen or len(mk.get("marketSides") or []) != 2:
                continue
            seen.add(mk["slug"])
            if time.time() > stop_at:
                break
            try:
                book = (lm.get(f"{PMUS}/v1/markets/{mk['slug']}/book") or {}).get("marketData") or {}
                reads += 1
            except Exception as ex:
                say(f"Polymarket US book failed {mk['slug']}: {str(ex)[:60]}")
                continue
            ts = time.time()
            offers = [(pmus_px(o), lm.num(o.get("qty")) or 0) for o in book.get("offers") or [] if pmus_px(o) is not None]
            bids = [(pmus_px(b), lm.num(b.get("qty")) or 0) for b in book.get("bids") or [] if pmus_px(b) is not None]
            long_buy = (None, 0.0)
            if offers:
                p = min(x for x, _ in offers)
                long_buy = (round(p, 4), p * sum(q for x, q in offers if abs(x - p) < 1e-9))
            bb, bq = best_level(bids)
            short_buy = (round(1 - bb, 4), (1 - bb) * bq) if bb is not None else (None, 0.0)   # buy NO = sell YES into bids
            ln = lm.num(mk.get("line"))
            for s in mk["marketSides"]:
                is_long = s.get("long") is not False
                desc = s.get("description") or s.get("identifier") or ""
                if mt == "total":
                    side = "OVER" if "over" in desc.lower() else ("UNDER" if "under" in desc.lower() else None)
                    line = ln
                else:
                    tid = s.get("teamId") or s.get("participantId")
                    nm = next((t.get("name") for t in ev.get("teams") or []
                               if tid is not None and str(tid) in (str(t.get("id")), str(t.get("participantId")))), None)
                    side = lm.team_side(nm or desc, list(teams), lg)
                    sl = lm.signed_num(desc)
                    line = sl if sl is not None else (ln if is_long else (-ln if ln is not None else None))
                if side is None or line is None:
                    continue
                mine, other = (long_buy, short_buy) if is_long else (short_buy, long_buy)
                out.append(quote("polymarket_us", lg, teams, st.timestamp(), st.astimezone(ET).date().isoformat(), mt,
                                 side, line, mine[0], mine[1], other[0], ts, {"slug": mk["slug"], "long": is_long}))
    say(f"Polymarket US: {reads} books read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- ProphetX (read-only key: login + markets, never orders)
def read_px(n, stop_at):
    if not (lm.PX_ACCESS and lm.PX_SECRET):
        say("ProphetX: no key secrets, skipped")
        return []
    try:
        d = lm.px_call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
        lm._PXT["token"] = (d.get("data") or {}).get("access_token")
    except Exception as ex:
        say(f"ProphetX login failed: {str(ex)[:60]}")
        return []
    todo = []
    for lg in LEAGUES:
        try:
            evs = (lm.px_call(f"/mm/get_sport_events?tournament_id={lm.PX_TOURNAMENTS[lg]}").get("data") or {}).get("sport_events") or []
        except Exception as ex:
            if "404" not in str(ex):
                say(f"ProphetX events failed ({lg}): {str(ex)[:60]}")
            continue
        for e in evs:
            try:
                st = piso(e["scheduled"])
            except Exception:
                continue
            if n < st <= n + timedelta(hours=WINDOW_H) and (e.get("status") or "not_started") == "not_started":
                todo.append((st, lg, e))
    todo.sort(key=lambda t: t[0])
    out, reads = [], 0
    for st, lg, e in todo:
        if time.time() > stop_at:
            say(f"ProphetX: time budget hit after {reads} of {len(todo)} games")
            break
        comps = e.get("competitors") or []
        home = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "home"), None)
        away = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "away"), None)
        teams = (away, home) if (home and away) else lm.split_teams(e.get("name") or "")
        if not teams:
            continue
        try:
            data = lm.px_call(f"/v4/mm/get_markets?event_id={e['event_id']}").get("data") or {}
            reads += 1
        except Exception as ex:
            say(f"ProphetX markets failed {e.get('event_id')}: {str(ex)[:60]}")
            continue
        ts = time.time()
        mks = data if isinstance(data, list) else (data.get("markets") or data.get(str(e["event_id"])) or [])
        for mk in mks:
            mt = (mk.get("type") or "").lower()
            if mt not in ("spread", "total") or (mk.get("sub_type") or mt).lower() != mt or (mk.get("status") or "active") != "active":
                continue
            by_line = {}
            for levels, mline in lm.px_lines(mk):
                f = levels[0]
                name = f.get("name") or f.get("display_name") or ""
                line = lm.num(f.get("strike"))
                if line is None:
                    line = lm.num(f.get("line"))
                if mt == "total":
                    side = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                    line = line if line else mline
                    gkey = line
                else:
                    side = lm.team_side(name, teams, lg)
                    gkey = abs(line) if line is not None else None
                if side is None or line is None:
                    continue
                prices = [x for x in levels if x.get("price") is not None]
                if not prices:
                    by_line.setdefault(gkey, []).append((side, line, None, 0.0))
                    continue
                best = max(int(x["price"]) for x in prices)   # higher American = better for the bettor
                dollars = sum(float(x.get("value") or 0) for x in prices if int(x["price"]) == best)   # 'value' = bettable $
                by_line.setdefault(gkey, []).append((side, line, round(am_prob(best), 4), dollars))
            for gkey, outs in by_line.items():
                if len(outs) != 2 or (mt == "spread" and abs(outs[0][1] + outs[1][1]) > 1e-9):
                    continue
                for i in (0, 1):
                    side, line, cost, dol = outs[i]
                    out.append(quote("prophetx", lg, teams, st.timestamp(), st.astimezone(ET).date().isoformat(), mt,
                                     side, line, cost, dol, outs[1 - i][2], ts,
                                     {"event_id": e["event_id"], "market_id": mk.get("id"), "line": gkey}))
    say(f"ProphetX: {reads} games read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- The Odds API: canonical games (free) + Pinnacle
def odds_get(path, params):
    url = f"{ODDS_API}{path}?{urllib.parse.urlencode(dict(params, apiKey=ODDS_KEY))}"
    with urllib.request.urlopen(url, timeout=30) as r:
        rem = r.headers.get("x-requests-remaining")
        return json.loads(r.read().decode()), (int(float(rem)) if rem is not None else None)


def read_odds(n, want_prices):
    """games: [{id, league, teams [away, home], start_ts, date}] from the free /events route.
    pin: {event_id: {market: {"outcomes": {name: (pt, price)}, "upd": ts}}}; xbooks: same shape per exchange (log-only)."""
    games, pin, xbooks, credits, fetched = [], {}, {}, None, None
    if not ODDS_KEY:
        say("No ODDS_API_KEY: no canonical games, no sightings this run")
        return games, pin, xbooks, credits, fetched, "no_key"
    frm, to = iso(n), iso(n + timedelta(hours=WINDOW_H))
    live = []
    for lg, key in ODDS_SPORT.items():
        try:
            evs, credits = odds_get(f"/sports/{key}/events", {"commenceTimeFrom": frm, "commenceTimeTo": to})
        except Exception as ex:
            say(f"Odds API events failed {lg}: {str(ex)[:80]}")
            continue
        for ev in evs:
            st = piso(ev["commence_time"])
            games.append(dict(id=ev["id"], league=lg, teams=[ev["away_team"], ev["home_team"]], start_ts=st.timestamp(),
                              date=st.astimezone(ET).date().isoformat()))
        if evs:
            live.append((lg, key))
    status = "ok"
    if not want_prices:
        return games, pin, xbooks, credits, fetched, "not_read"
    if credits is not None and credits < ODDS_MIN_CREDITS:
        say(f"Pinnacle not read: {credits} credits left (< {ODDS_MIN_CREDITS} floor kept for the sharp monitor)")
        return games, pin, xbooks, credits, fetched, "credit_floor"
    fetched = time.time()
    for lg, key in live:
        try:
            body, credits = odds_get(f"/sports/{key}/odds", {"bookmakers": ODDS_BOOKS, "markets": "spreads,totals",
                                                             "oddsFormat": "american", "commenceTimeFrom": frm, "commenceTimeTo": to})
        except Exception as ex:
            say(f"Odds API odds failed {lg}: {str(ex)[:80]}")
            status = "partial"
            continue
        for ev in body:
            for bk in ev.get("bookmakers", []):
                dst = pin if bk["key"] == "pinnacle" else xbooks.setdefault(bk["key"], {})
                for m in bk.get("markets", []):
                    try:
                        upd = piso(m.get("last_update") or bk.get("last_update")).timestamp()
                    except Exception:
                        upd = None
                    dst.setdefault(ev["id"], {})[m["key"]] = {
                        "outcomes": {o["name"]: (o.get("point"), o.get("price")) for o in m.get("outcomes", [])}, "upd": upd}
    return games, pin, xbooks, credits, fetched, status


def pin_fair(pm, market, side_name, line, teams):
    """Pinnacle no-vig fair for side_name at EXACTLY `line`, else None. Also returns Pinnacle's own line for that side."""
    m = (pm or {}).get("spreads" if market == "spread" else "totals")
    if not m or len(m["outcomes"]) != 2:
        return None, None, None
    oc = m["outcomes"]
    if market == "total":
        key = "Over" if side_name == "OVER" else "Under"
        if key not in oc or "Over" not in oc or "Under" not in oc:
            return None, None, m["upd"]
        pt = oc[key][0]
        p = am_prob(oc[key][1]) / (am_prob(oc["Over"][1]) + am_prob(oc["Under"][1]))
    else:
        if side_name not in oc:
            return None, None, m["upd"]
        other = [k for k in oc if k != side_name][0]
        pt = oc[side_name][0]
        p = am_prob(oc[side_name][1]) / (am_prob(oc[side_name][1]) + am_prob(oc[other][1]))
    if pt is None or abs(float(pt) - line) > 1e-9:
        return None, pt, m["upd"]
    return round(p, 5), pt, m["upd"]


def pin_lines(pm):
    """Pinnacle data in sharp_monitor.book_lines shape ({'spreads': {team: (pt, price)}, 'totals': {...}})."""
    return {mk: dict(v["outcomes"]) for mk, v in (pm or {}).items()}


# ---------------------------------------------------------------- grouping quotes across books
def canon_for(q, games):
    """The Odds API game this quote belongs to: same league, both team names overlap, same ET date (or, when a book
    files a late game under another date, a start within 6 h). Returns (game, 'same'|'flipped')."""
    if not q.get("teams"):
        return None, None
    for g in games:
        if g["league"] != q["league"]:
            continue
        how = lm.same_game(q, g)
        if not how and q.get("start") and abs(q["start"] - g["start_ts"]) < 6 * 3600:
            how = lm.same_game(dict(q, date=g["date"]), g)
        if how:
            return g, how
    return None, None


def build_groups(quotes, games):
    """{(game_id, market, line, side_name): {"game": g, "books": {book: quote}}} - best quote per book."""
    groups, unmatched = {}, 0
    for q in quotes:
        if q["cost"] is None:
            continue
        g, how = canon_for(q, games)
        if not g:
            unmatched += 1
            continue
        if q["market"] == "total":
            side = q["side"]
        else:
            idx = q["side"] if how == "same" else 1 - q["side"]
            side = g["teams"][idx]
        k = (g["id"], q["market"], round(float(q["line"]), 2), side)
        q = dict(q, cost_af=after_fee(q["book"], q["cost"]))
        slot = groups.setdefault(k, {"game": g, "books": {}})["books"]
        cur = slot.get(q["book"])
        if q["cost_af"] is not None and (cur is None or q["cost_af"] < cur["cost_af"]):
            slot[q["book"]] = q
    return groups, unmatched


def snapshot(grp):
    """Per-book prices for one group + best book + cross-book numbers."""
    books = grp["books"]
    prices = {}
    for b in BOOKS:
        q = books.get(b)
        prices[b] = None if not q else {
            "cost": q["cost"], "cost_after_fee": round(q["cost_af"], 4), "american_after_fee": lm.american(round(q["cost_af"], 4)),
            "depth_usd": round(q["depth"]), "opp_cost": q["opp_cost"],
            "crossed": bool(q["opp_cost"] is not None and q["cost"] + q["opp_cost"] < 0.97),   # stale/crossed quote flag
            "read_utc": iso(datetime.fromtimestamp(q["read_ts"], timezone.utc))}
    live = [(b, q) for b, q in books.items() if q["cost_af"] is not None and 0.05 < q["cost_af"] < 0.95]
    if not live:
        return None
    best_b, best_q = min(live, key=lambda x: (x[1]["cost_af"], -x[1]["depth"]))
    others = [q["cost_af"] for b, q in live if b != best_b]
    mids = [(q["cost"] + 1 - q["opp_cost"]) / 2 for _, q in live if q["opp_cost"] is not None]
    return {"prices": prices, "best_book": best_b, "best_q": best_q, "n_books": len(live),
            "median_others": statistics.median(others) if others else None,
            "disc_c": round(100 * (statistics.median(others) - best_q["cost_af"]), 2) if others else None,
            "consensus_mid": round(statistics.median(mids), 5) if mids else None,
            "median_cost_af": round(statistics.median(q["cost_af"] for _, q in live), 5)}


def age_bucket(s):
    if s is None:
        return None
    return "<60s" if s < 60 else ("1-5m" if s < 300 else "5m+")


# ---------------------------------------------------------------- close + grading
_SM = {}


def sm():
    if "m" not in _SM:
        try:
            import sharp_monitor
            _SM["m"] = sharp_monitor
        except Exception as ex:
            say(f"sharp_monitor helpers unavailable: {str(ex)[:60]}")
            _SM["m"] = None
    return _SM["m"]


def pin_close_fair(s, pm):
    """Pinnacle no-vig closing win chance at the sighting's own number (sharp_monitor.close_prob: same method as the
    ntfy record's closing value). Returns (fair, pinnacle_line, same_line)."""
    m = sm()
    if not m or not pm:
        return None, None, None
    kind = "tot" if s["market"] == "total" else "spr"
    side = ("Over" if s["side"] == "OVER" else "Under") if kind == "tot" else s["side"]
    e = {"kind": kind, "side": side, "pt": s["line"], "sport": s["league"]}
    try:
        p = m.close_prob(e, pin_lines(pm))
    except Exception:
        p = None
    mk = (pm.get("totals") if kind == "tot" else pm.get("spreads")) or {}
    oc = mk.get("outcomes", {})
    pl = (oc.get(side) or (None,))[0]
    return (round(p, 5) if p is not None else None), pl, (pl is not None and abs(float(pl) - s["line"]) < 1e-9)


def update_closes(sightings, groups, pin, n):
    now = n.timestamp()
    for s in sightings:
        if s.get("close_final"):
            continue
        st = piso(s["start_utc"]).timestamp()
        if st <= now:   # game started: the last pregame read is the close
            s["close_final"] = True
            if s.get("close_read_utc") is None:
                s["close_missing"] = True
            continue
        grp = groups.get((s["game_id"], s["market"], s["line"], s["side"]))
        if not grp:
            continue
        snap = snapshot(grp)
        if not snap:
            continue
        s["close_read_utc"] = iso(n)
        s["close_mins_before_start"] = round((st - now) / 60)
        s["close_consensus_fair"] = snap["consensus_mid"]
        s["close_median_cost_af"] = snap["median_cost_af"]
        s["close_n_books"] = snap["n_books"]
        s["close_prices"] = {b: (v["cost_after_fee"] if v else None) for b, v in snap["prices"].items()}
        c = s["sighting_cost_af"]
        s["clv_consensus_c"] = round(100 * (snap["consensus_mid"] - c), 2) if snap["consensus_mid"] is not None else None
        pm = pin.get(s["game_id"])
        if pm:
            p, pl, same = pin_close_fair(s, pm)
            s["pin_close_fair"], s["pin_close_line"], s["pin_close_same_line"] = p, pl, same
            s["clv_pinnacle_c"] = round(100 * (p - c), 2) if p is not None else None


def grade(sightings, n):
    m = sm()
    for s in sightings:
        if s.get("result") or piso(s["start_utc"]) > n - timedelta(hours=3):
            continue
        a = {"teams": s["teams"], "start_utc": s["start_utc"], "league": s["league"], "market": s["market"],
             "side": s["side"], "line": s["line"], "game": s["game"]}
        try:
            r = lm.espn_result(a, n) if m else None
        except Exception as ex:
            say(f"grading failed {s['game']}: {str(ex)[:60]}")
            r = None
        if r in ("W", "L", "P"):
            c = s["sighting_cost_af"]
            s["result"], s["graded_utc"] = r, iso(n)
            s["units_flat"] = round((1 - c) / c, 4) if r == "W" else (-1.0 if r == "L" else 0.0)


# ---------------------------------------------------------------- sightings
def sightings_from(groups, pin, pin_fetched, n, existing, xbooks):
    """New sightings this scan (and last_seen updates on existing ones). Returns count added per trigger."""
    by_key = {s["key"]: s for s in existing}
    added = {"A": 0, "B": 0}
    ts = iso(n)
    for (gid, market, line, side), grp in groups.items():
        g = grp["game"]
        if g["start_ts"] <= n.timestamp():
            continue
        snap = snapshot(grp)
        if not snap:
            continue
        fair, pline, pupd = pin_fair(pin.get(gid), market, side, line, g["teams"])
        # A: the single best after-fee price, which must have >= $250 behind it.
        # B: the best price that is GETTABLE (>= $250 behind it), compared with Pinnacle at the same line.
        gettable = [(b, q) for b, q in grp["books"].items()
                    if q["cost_af"] is not None and 0.05 < q["cost_af"] < 0.95 and q["depth"] >= B_DEPTH]
        gb = min(gettable, key=lambda x: x[1]["cost_af"]) if gettable else None
        evs = {}
        if fair and gb:
            evs = {"book": gb[0], "q": gb[1], "ev": fair / gb[1]["cost_af"] - 1}
        fires = []
        if snap["disc_c"] is not None and snap["disc_c"] >= 100 * A_MIN - 1e-9 and snap["best_q"]["depth"] >= A_DEPTH:
            fires.append(("A", snap["best_book"], snap["best_q"]))
        if evs and evs["ev"] >= B_MIN_EV - 1e-9:
            fires.append(("B", evs["book"], evs["q"]))
        for trig, sb, bq in fires:
            best_c = bq["cost_af"]
            ev = (fair / best_c - 1) if fair else None
            ref_age = round(bq["read_ts"] - pupd, 1) if (fair and pupd) else None
            key = f"{trig}|{gid}|{market}|{line:g}|{side}"
            old = by_key.get(key)
            if old:
                old["last_seen_utc"], old["scans_seen"] = ts, old.get("scans_seen", 1) + 1
                old["max_disc_c"] = max(old.get("max_disc_c") or -99, snap["disc_c"] or -99)
                if ev is not None:
                    old["max_ev_pct"] = max(old.get("max_ev_pct") or -99, round(100 * ev, 2))
                continue
            xb = {b: (xbooks.get(b, {}).get(gid, {}).get("spreads" if market == "spread" else "totals") or {}).get("outcomes")
                  for b in ("prophetx", "novig", "kalshi", "polymarket_us")}
            s = {
                "key": key, "trigger": trig, "sighted_utc": ts, "first_seen_utc": ts, "last_seen_utc": ts, "scans_seen": 1,
                "game_id": gid, "league": g["league"], "game": f"{g['teams'][0]} @ {g['teams'][1]}", "teams": g["teams"],
                "start_utc": iso(datetime.fromtimestamp(g["start_ts"], timezone.utc)),
                "lead_min": round((g["start_ts"] - n.timestamp()) / 60),
                "market": market, "line": line, "side": side,
                "prices": snap["prices"], "best_book": sb, "depth_at_best_usd": round(bq["depth"]),
                "sighting_cost": bq["cost"], "sighting_cost_af": round(best_c, 5),
                "sighting_american_af": lm.american(round(best_c, 4)), "n_books": snap["n_books"],
                "median_others_af": round(snap["median_others"], 5) if snap["median_others"] is not None else None,
                "discrepancy_c": snap["disc_c"], "max_disc_c": snap["disc_c"],
                "qualifying": bool(trig == "A" and snap["disc_c"] is not None and snap["disc_c"] >= 100 * A_QUAL - 1e-9),
                "pinnacle_fair": fair, "pinnacle_line": pline, "ev_pct": round(100 * ev, 2) if ev is not None else None,
                "max_ev_pct": round(100 * ev, 2) if ev is not None else None,
                "pinnacle_last_update_utc": iso(datetime.fromtimestamp(pupd, timezone.utc)) if pupd else None,
                "ref_age_s": ref_age, "ref_age_bucket": age_bucket(ref_age),
                "pin_fetch_to_read_s": round(bq["read_ts"] - pin_fetched, 1) if (pin_fetched and fair) else None,
                "odds_api_exchange_lines": xb,   # log-only cross-check of the feed vs our own book reads
                "consensus_fair_at_sighting": snap["consensus_mid"],
                "result": None, "units_flat": None, "close_final": False,
            }
            existing.append(s)
            by_key[key] = s
            added[trig] += 1
            say(f"SIGHTING {trig} {g['league']} {s['game']} | {market} {side} {line:+g} | {sb} "
                f"{best_c:.3f} (${bq['depth']:,.0f}) | disc {snap['disc_c']}c | EV {s['ev_pct']}% age {ref_age}s")
    return added


# ---------------------------------------------------------------- report
def bucket_stats(rows):
    closed = [s for s in rows if s.get("clv_consensus_c") is not None and s.get("close_final")]
    pinc = [s for s in rows if s.get("clv_pinnacle_c") is not None and s.get("close_final")]
    gr = [s for s in rows if s.get("result") in ("W", "L", "P")]
    w = sum(1 for s in gr if s["result"] == "W")
    l = sum(1 for s in gr if s["result"] == "L")
    p = sum(1 for s in gr if s["result"] == "P")
    u = sum(s["units_flat"] for s in gr)
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    return {"n": len(rows), "n_closed": len(closed), "clv_consensus_avg_c": avg([s["clv_consensus_c"] for s in closed]),
            "beat_consensus_pct": round(100 * sum(1 for s in closed if s["clv_consensus_c"] > 0) / len(closed), 1) if closed else None,
            "n_pin_closed": len(pinc), "clv_pinnacle_avg_c": avg([s["clv_pinnacle_c"] for s in pinc]),
            "beat_pinnacle_pct": round(100 * sum(1 for s in pinc if s["clv_pinnacle_c"] > 0) / len(pinc), 1) if pinc else None,
            "graded": len(gr), "record": f"{w}-{l}-{p}", "units": round(u, 2),
            "roi_pct": round(100 * u / len(gr), 1) if gr else None}


def gate(st):
    ok = st["graded"] >= 50 and (st["clv_consensus_avg_c"] or 0) > 0 and st["units"] > 0
    return ("criteria met - eligible for discussion at the scheduled review only" if ok else
            f"criteria not met ({st['graded']}/50 graded" + (", CLV not positive" if not (st["clv_consensus_avg_c"] or 0) > 0 else "")
            + (", record not positive" if st["units"] <= 0 else "") + ")")


def report(doc):
    ss = doc.get("sightings", [])
    groups = [("A cross-book (>= 2c)", [s for s in ss if s["trigger"] == "A"]),
              ("A qualifying (>= 3c)", [s for s in ss if s["trigger"] == "A" and s.get("qualifying")]),
              ("B Pinnacle (>= 3% EV)", [s for s in ss if s["trigger"] == "B"])]
    for b in ("<60s", "1-5m", "5m+"):
        groups.append((f"  B ref age {b}", [s for s in ss if s["trigger"] == "B" and s.get("ref_age_bucket") == b]))
    out = {"study": doc.get("study"), "generated_utc": iso(datetime.now(timezone.utc)), "rows": []}
    for name, rows in groups:
        st = bucket_stats(rows)
        st["gate"] = gate(st) if not name.startswith("  ") else ""
        out["rows"].append(dict(name=name, **st))
    both = {s["key"].split("|", 1)[1] for s in ss if s["trigger"] == "A"} & {s["key"].split("|", 1)[1] for s in ss if s["trigger"] == "B"}
    out["overlap_A_and_B"] = len(both)
    return out


def report_md(rep, runs):
    L = ["# EV sightings study (paper, measurement only)", "",
         f"Started {(rep.get('study') or {}).get('started_utc')}. Updated {rep['generated_utc']}. "
         f"Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). "
         f"Gate: >= 50 graded, positive average consensus CLV and positive flat record; reviewed only at a scheduled review.", "",
         "| Bucket | Sightings | Closed | Avg CLV vs consensus | Beat % | Pin-closed | Avg CLV vs Pinnacle | Graded | Record | Units | ROI | Gate |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rep["rows"]:
        f = lambda v, sfx="": "" if v is None else f"{v}{sfx}"
        L.append(f"| {r['name'].strip()} | {r['n']} | {r['n_closed']} | {f(r['clv_consensus_avg_c'], 'c')} | {f(r['beat_consensus_pct'], '%')} | "
                 f"{r['n_pin_closed']} | {f(r['clv_pinnacle_avg_c'], 'c')} | {r['graded']} | {r['record']} | {r['units']:+.2f}u | "
                 f"{f(r['roi_pct'], '%')} | {r['gate']} |")
    L += ["", f"A and B on the same side/line: {rep['overlap_A_and_B']}.", "", "## Last runs", ""]
    L += [f"- {r['utc']}: {r.get('summary')}" for r in runs[-10:][::-1]]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main
def load_doc():
    try:
        with open(OUT_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


NOTE = ("EV SIGHTINGS - PAPER STUDY, MEASUREMENT ONLY. Never bets, never pushed. Triggers: A = best after-fee cost >= 2c "
        "under the median after-fee cost of the other books at the same line, >= $250 at the best price (qualifying >= 3c); "
        "B = best gettable (>= $250) after-fee cost beats Pinnacle no-vig fair at the same line by >= 3% EV. One record per "
        "trigger/game/market/line/side (first sighting; last_seen/scans_seen while it persists). Costs are 0-1 per $1 payout "
        "after fees (Kalshi 0.07 and Polymarket US 0.0695 x P x (1-P) taker; ProphetX 2% of winnings; Novig none). "
        "depth_usd = $ bettable at that book's best price. ref_age_s = exchange read time - Pinnacle market last_update. "
        "Close = last pregame read (close_mins_before_start); close_consensus_fair = median of books' no-vig mids; "
        "pin_close_fair = sharp_monitor.close_prob at the sighting's number (pin_close_same_line false = half points priced in). "
        "clv_*_c = (close fair - sighting_cost_af) x 100. result/units_flat = ESPN final, flat 1u at sighting_cost_af. "
        "crossed = that book's two sides cost < 97c total (stale/crossed quote).")


def run():
    n = datetime.now(timezone.utc)
    t0 = time.time()
    doc = load_doc()
    doc.setdefault("study", {"started_utc": iso(n), "approved": "2026-10-27", "interim_due": "1 week after start",
                             "final_due": "2 weeks after start",
                             "params": {"A_min_c": 100 * A_MIN, "A_qual_c": 100 * A_QUAL, "A_depth": A_DEPTH, "B_min_ev": B_MIN_EV,
                                        "B_depth": B_DEPTH, "leagues": LEAGUES, "markets": ["spread", "total"],
                                        "window_h": WINDOW_H}})
    sightings = doc.setdefault("sightings", [])
    runs = doc.setdefault("runs", [])
    hr = n.astimezone(ET).hour
    reading = ACTIVE_ET[0] <= hr < ACTIVE_ET[1]
    summary = ""
    if reading:
        games, pin, xbooks, credits, pin_fetched, pin_status = read_odds(n, want_prices=True)
        quotes = []
        if games:
            stop_at = time.time() + BOOK_SEC
            with ThreadPoolExecutor(4) as ex:
                readers = {"kalshi": read_kalshi, "novig": read_novig, "polymarket_us": read_pmus, "prophetx": read_px}
                futs = [ex.submit(fn, n, stop_at) for b, fn in readers.items() if b in READ_BOOKS]
                for f in futs:
                    try:
                        quotes += f.result()
                    except Exception as e:
                        say(f"book reader failed: {str(e)[:80]}")
        groups, unmatched = build_groups(quotes, games)
        added = sightings_from(groups, pin, pin_fetched, n, sightings, xbooks) if games else {"A": 0, "B": 0}
        update_closes(sightings, groups, pin, n)
        by_book = {b: sum(1 for q in quotes if q["book"] == b) for b in BOOKS}
        summary = (f"{len(games)} games, quotes {by_book}, {unmatched} unmatched, {len(groups)} side/lines, "
                   f"Pinnacle {pin_status} ({len(pin)} games), credits {credits}, new A {added['A']} B {added['B']}, "
                   f"{time.time() - t0:.0f}s")
    else:
        update_closes(sightings, {}, {}, n)
        summary = "outside read hours: closes/grades only"
    grade(sightings, n)
    runs.append({"utc": iso(n), "summary": summary})
    doc["runs"] = runs[-300:]
    doc["note"] = NOTE
    rep = report(doc)
    doc["summary"] = rep
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(doc, f, indent=1)
    with open(os.path.join(OUT_DIR, "README.md"), "w") as f:
        f.write(report_md(rep, doc["runs"]))
    say(f"Done: {summary}")


def print_report():
    doc = load_doc()
    rep = report(doc)
    print(report_md(rep, doc.get("runs", [])))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report()
    else:
        try:
            run()
        except Exception as ex:
            print(f"Run failed: {ex}")
            sys.exit(1)
