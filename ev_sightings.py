#!/usr/bin/env python3
"""
EV SIGHTINGS - paper study, MEASUREMENT ONLY (approved by Peter, Oct 27, 2026).

Question: does "EV" on the four exchanges predict closing value?
  A  CROSS-BOOK  the best after-fee cost to buy a side is >= 2c under the MEDIAN after-fee cost of the other books
                 at the same line, with >= $250 bettable at that best price. qualifying = >= 3c.
  B  PINNACLE    the best gettable (>= $250) after-fee cost beats Pinnacle's no-vig fair at the SAME line by >= 3% EV
                 (EV = fair / cost - 1). ref_age_s = seconds from Pinnacle's own last_update for that market to our
                 read of the exchange price (staleness is a measured variable: buckets <60s / 60-300s / 300s+).

AMENDMENT A1 (approved Oct 27): M  PINNACLE MOVE-WATCH. Pinnacle (The Odds API) polled per sport, spreads + totals,
                 games today/tomorrow ET: every 5 min while one of that sport's games starts within 6 h, every 20 min
                 otherwise. A move = line change >= 0.5 pts between consecutive polls (primary) or >= 5 cents on an
                 unchanged line. Same cycle: all four exchanges read at the OLD number for the side the market moved
                 toward; gettable = after-fee cost <= Pinnacle's pre-move price with >= $250 at that price or better.
                 Every move is logged (not gettable = control group); detection_lag_s = detection - Pinnacle last_update.
                 Graded like A/B, reported separately. Credit guard: polls only from credits the sharp monitor doesn't
                 need for the rest of the month (it sets its own polling speed from what's left).

AMENDMENT A2 (Oct 29): MK MAKER TEST. Paper resting bids on Novig and ProphetX at Pinnacle no-vig fair minus 1c / 2c
                 (after fees), main lines, games within 6 h, 60-min life. Filled when the book later trades through the
                 bid. Fills graded (Pinnacle CLV + flat 1u); unfilled CLV kept for the adverse-selection comparison.
                 Stored under "maker" / "maker_agg" in the same file. No extra credits or reads.

Scope: NFL / NCAAF / NBA, spreads + totals, pregame. A/B full exchange reads cover games starting in the next 24 h, every
10 min (own workflow), 9am-midnight ET; each run then keeps polling in-window sports for ~7 min and reads the exchanges
only for games whose Pinnacle line moved. Closes and grading run at any hour from data already stored.

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


def quote(book, lg, teams, start, date, market, side, line, cost, depth, opp_cost, ts, ref, ladder=None):
    """ladder = [(screen cost 0-1, dollars)] you can BUY at, best first (A1: dollars at a price or better)."""
    lad = sorted(((round(c, 4), round(d, 2)) for c, d in (ladder or []) if c is not None and 0 < c < 1 and d > 0))[:12]
    return dict(book=book, league=lg, teams=list(teams) if teams else None, start=start, date=date, market=market,
                side=side, line=line, cost=cost, depth=round(depth or 0.0, 2), opp_cost=opp_cost, read_ts=ts, ref=ref,
                ladder=lad)


def wanted(lg, teams, date, start, only):
    """A1 targeted reads: True when no filter, else only for the canonical games in `only`."""
    if only is None:
        return True
    if not teams:
        return False
    return canon_for({"league": lg, "teams": list(teams), "date": date, "start": start}, only)[0] is not None


def horizon_days(n, horizon):
    d, out = n.astimezone(ET).date(), set()
    while datetime.combine(d, datetime.min.time(), ET) <= horizon.astimezone(ET):
        out.add(d)
        d += timedelta(days=1)
    return out


def best_level(levels):
    """[(price, size)] -> (best price, total size at exactly that price) using the highest price."""
    if not levels:
        return None, 0.0
    p = max(x for x, _ in levels)
    return p, sum(q for x, q in levels if abs(x - p) < 1e-9)


# ---------------------------------------------------------------- Kalshi (public)
def read_kalshi(n, stop_at, horizon=None, only=None):
    out, todo = [], []
    horizon = horizon or n + timedelta(hours=WINDOW_H)
    days = horizon_days(n, horizon)
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
                if d not in days or not teams or not wanted(lg, teams, d.isoformat(), None, only):
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
        buy, lad = {}, {}
        for x in ("yes", "no"):   # buy YES = take the best NO bid at 1 - p (sizes are $1 contracts)
            lv = lm.k_levels(book, "no" if x == "yes" else "yes")
            p, q = best_level(lv)
            buy[x] = (round(1 - p, 4), (1 - p) * q) if p is not None else (None, 0.0)
            lad[x] = [(1 - pp, (1 - pp) * qq) for pp, qq in lv]
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
                             buy[o][0], ts, {"ticker": mk["ticker"], "kalshi_side": x}, lad[x]))
    say(f"Kalshi: {reads} books read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- Novig (public, unsigned)
def read_novig(n, stop_at, horizon=None, only=None):
    horizon = horizon or n + timedelta(hours=WINDOW_H)
    lo, hi = int(n.timestamp() * 1000), int(horizon.timestamp() * 1000)
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
        lg0 = lm.N_LEAGUE.get((e.get("league") or "").upper().strip())
        st0 = (e.get("startsTs") or 0) / 1000
        if only is not None and not wanted(lg0, lm.split_teams(e.get("description") or ""),
                                           datetime.fromtimestamp(st0, ET).date().isoformat(), st0, only):
            continue
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
        buy, lad = [], []
        for i in (0, 1):   # Novig orders are bids: buy outcome i = take the best bid on the other outcome at 1 - p
            lv = [(float(r["price"]), int(r["qty"]) / 100.0) for r in orders.get(outs[1 - i]["outcomeId"], [])]
            p, q = best_level(lv)
            buy.append((round(1 - p, 4), (1 - p) * q) if p is not None else (None, 0.0))
            lad.append([(1 - pp, (1 - pp) * qq) for pp, qq in lv])
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
                             {"market_id": mk["marketId"], "outcome_id": o["outcomeId"]}, lad[i]))
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


def read_pmus(n, stop_at, horizon=None, only=None):
    out, reads = [], 0
    horizon = horizon or n + timedelta(hours=WINDOW_H)
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
            if teams and n < st <= horizon and wanted(lg, teams, st.astimezone(ET).date().isoformat(), st.timestamp(), only):
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
            long_lad = [(p, p * q) for p, q in offers]
            short_lad = [(1 - p, (1 - p) * q) for p, q in bids]
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
                                 side, line, mine[0], mine[1], other[0], ts, {"slug": mk["slug"], "long": is_long},
                                 long_lad if is_long else short_lad))
    say(f"Polymarket US: {reads} books read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- ProphetX (read-only key: login + markets, never orders)
def read_px(n, stop_at, horizon=None, only=None):
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
    horizon = horizon or n + timedelta(hours=WINDOW_H)
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
            if n < st <= horizon and (e.get("status") or "not_started") == "not_started":
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
        if not teams or not wanted(lg, teams, st.astimezone(ET).date().isoformat(), st.timestamp(), only):
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
                    by_line.setdefault(gkey, []).append((side, line, None, 0.0, []))
                    continue
                best = max(int(x["price"]) for x in prices)   # higher American = better for the bettor
                dollars = sum(float(x.get("value") or 0) for x in prices if int(x["price"]) == best)   # 'value' = bettable $
                lad = [(am_prob(int(x["price"])), float(x.get("value") or 0)) for x in prices]
                by_line.setdefault(gkey, []).append((side, line, round(am_prob(best), 4), dollars, lad))
            for gkey, outs in by_line.items():
                if len(outs) != 2 or (mt == "spread" and abs(outs[0][1] + outs[1][1]) > 1e-9):
                    continue
                for i in (0, 1):
                    side, line, cost, dol, lad = outs[i]
                    out.append(quote("prophetx", lg, teams, st.timestamp(), st.astimezone(ET).date().isoformat(), mt,
                                     side, line, cost, dol, outs[1 - i][2], ts,
                                     {"event_id": e["event_id"], "market_id": mk.get("id"), "line": gkey}, lad))
    say(f"ProphetX: {reads} games read, {len(out)} quotes")
    return out


# ---------------------------------------------------------------- The Odds API: canonical games (free) + Pinnacle polls
# Amendment A1 (Oct 27): one Pinnacle poll schedule serves all legs. Per sport: every FAST_S while one of its games
# starts within NEAR_H hours, every SLOW_S otherwise. A poll = /odds, 2 markets, <= 10 books = 2 credits.
# Credit guard: the sharp monitor sets its own polling speed from the credits left this month, so this study spends
# only what is left over after the sharp monitor's projected need (SM_DAILY per remaining day + SM_MARGIN).
FAST_S = float(os.environ.get("EV_FAST_SEC", "") or "300")
SLOW_S = float(os.environ.get("EV_SLOW_SEC", "") or "1200")
NEAR_H = float(os.environ.get("EV_NEAR_HOURS", "") or "6")
LOOP_S = float(os.environ.get("EV_LOOP_SEC", "") or "420")          # keep polling in-window sports this long per run
CREDITS_PER_POLL = 2
SM_DAILY = float(os.environ.get("EV_SM_DAILY", "") or "2600")       # sharp monitor at its 5-min floor (~11 credits x 216 polls)
SM_MARGIN = float(os.environ.get("EV_SM_MARGIN", "") or "3000")     # liquidity monitor / book check / closing reads
MOVE_LINE, MOVE_CENTS, M_DEPTH = 0.5, 5.0, 250.0
# Data-quality rules (Oct 28, Peter approved): a best price 10c+ under the other books is almost always a misread quote
# (e.g. a wrong line on an alternate market), so it is flagged suspect and kept out of the headline rows; and the
# Pinnacle close is only trusted within 3 points of Pinnacle's own number (farther out the half-point estimate breaks).
SUSPECT_C = 10.0
PIN_NEAR_PTS = 3.0


def is_suspect(s):
    """Flag computed from stored fields, so it applies to every sighting already logged."""
    if s.get("trigger") in ("A", "B"):
        if (s.get("discrepancy_c") or 0) >= SUSPECT_C - 1e-9:
            return True
        return bool(((s.get("prices") or {}).get(s.get("best_book")) or {}).get("crossed"))
    if s.get("trigger") == "M" and s.get("sighting_cost_af") is not None:
        others = [v["cost_after_fee"] for b, v in (s.get("books") or {}).items()
                  if b != s.get("best_book") and v.get("cost_after_fee") is not None]
        return bool(others) and 100 * (statistics.median(others) - s["sighting_cost_af"]) >= SUSPECT_C - 1e-9
    return False


def pin_close_far(s):
    pl = s.get("pin_close_line")
    return pl is not None and abs(float(pl) - float(s["line"])) > PIN_NEAR_PTS + 1e-9


def odds_get(path, params, acct):
    url = f"{ODDS_API}{path}?{urllib.parse.urlencode(dict(params, apiKey=ODDS_KEY))}"
    with urllib.request.urlopen(url, timeout=30) as r:
        rem = r.headers.get("x-requests-remaining")
        last = r.headers.get("x-requests-last")
        body = json.loads(r.read().decode())
    if rem is not None:
        acct["remaining"] = int(float(rem))
    acct["used"] += int(float(last)) if last is not None else (CREDITS_PER_POLL if path.endswith("/odds") else 0)
    return body


def end_of_tomorrow(n):
    return datetime.combine(n.astimezone(ET).date() + timedelta(days=2), datetime.min.time(), ET).astimezone(timezone.utc)


def credit_need(n):
    """Credits to leave for the sharp monitor (and the other monitors) for the rest of this month."""
    d = n.astimezone(ET).date()
    nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (nxt - d).days * SM_DAILY + SM_MARGIN


def read_games(n, horizon, acct):
    """[{id, league, teams [away, home], start_ts, date}] for games starting now..horizon (free /events route)."""
    games = []
    for lg, key in ODDS_SPORT.items():
        try:
            evs = odds_get(f"/sports/{key}/events", {"commenceTimeFrom": iso(n), "commenceTimeTo": iso(horizon)}, acct)
        except Exception as ex:
            say(f"Odds API events failed {lg}: {str(ex)[:80]}")
            continue
        for ev in evs:
            st = piso(ev["commence_time"])
            games.append(dict(id=ev["id"], league=lg, teams=[ev["away_team"], ev["home_team"]], start_ts=st.timestamp(),
                              date=st.astimezone(ET).date().isoformat()))
    return games


def poll_due(lg, games, polls, now_s):
    gs = [g for g in games if g["league"] == lg and g["start_ts"] > now_s]
    if not gs:
        return None, False
    near = any(g["start_ts"] - now_s <= NEAR_H * 3600 for g in gs)
    last = (polls.get(lg) or {}).get("t", 0)
    return last + (FAST_S if near else SLOW_S), near


def poll_sport(n, lg, horizon, acct):
    """One Pinnacle poll (+ the exchanges' Odds API lines, log-only). {event_id: {market: {outcomes, upd, fetched}}}."""
    body = odds_get(f"/sports/{ODDS_SPORT[lg]}/odds", {"bookmakers": ODDS_BOOKS, "markets": "spreads,totals",
                                                       "oddsFormat": "american", "commenceTimeFrom": iso(n),
                                                       "commenceTimeTo": iso(horizon)}, acct)
    fetched = time.time()
    pin, xb = {}, {}
    for ev in body:
        for bk in ev.get("bookmakers", []):
            dst = pin if bk["key"] == "pinnacle" else xb.setdefault(bk["key"], {})
            for m in bk.get("markets", []):
                try:
                    upd = piso(m.get("last_update") or bk.get("last_update")).timestamp()
                except Exception:
                    upd = None
                dst.setdefault(ev["id"], {})[m["key"]] = {
                    "outcomes": {o["name"]: [o.get("point"), o.get("price")] for o in m.get("outcomes", [])},
                    "upd": upd, "fetched": fetched}
    return pin, xb


def cents(a):
    """American price on a straight 'cents' scale: -110 -> 110, -105 -> 105, +100 -> 100, +105 -> 95."""
    a = float(a)
    return -a if a < 0 else 200 - a


def detect_moves(old, new, g, now_s):
    """Pinnacle moves on one game between two consecutive polls. A line move (>= 0.5 pts) is primary; a price move
    (>= 5 cents on an unchanged line) is logged too. The bet = the side the market moved toward, at its OLD number."""
    out = []
    for mk, market in (("spreads", "spread"), ("totals", "total")):
        o, w = (old or {}).get(mk), (new or {}).get(mk)
        if not o or not w or len(o["outcomes"]) != 2 or set(o["outcomes"]) != set(w["outcomes"]):
            continue
        oo, nn = o["outcomes"], w["outcomes"]
        if any(oo[k][0] is None or nn[k][0] is None or oo[k][1] is None or nn[k][1] is None for k in oo):
            continue
        kind, mover = None, None
        if market == "total":
            d = float(nn["Over"][0]) - float(oo["Over"][0]) if "Over" in oo else 0
            if abs(d) >= MOVE_LINE - 1e-9:
                kind, mover = "line", ("Over" if d > 0 else "Under")
        else:
            for k in oo:
                d = float(nn[k][0]) - float(oo[k][0])
                if d <= -(MOVE_LINE - 1e-9):   # this side's number got worse = money came on it
                    kind, mover = "line", k
        if kind is None and all(abs(float(nn[k][0]) - float(oo[k][0])) < 1e-9 for k in oo):
            dc = {k: cents(nn[k][1]) - cents(oo[k][1]) for k in oo}
            k = max(dc, key=dc.get)
            if dc[k] >= MOVE_CENTS - 1e-9:
                kind, mover = "price", k
        if kind is None:
            continue
        other = [k for k in oo if k != mover][0]
        p_before = am_prob(oo[mover][1]) / (am_prob(oo[mover][1]) + am_prob(oo[other][1]))
        p_after = am_prob(nn[mover][1]) / (am_prob(nn[mover][1]) + am_prob(nn[other][1]))
        out.append({"game": g, "market": market, "side": (mover.upper() if market == "total" else mover),
                    "move_type": kind, "old_line": float(oo[mover][0]), "new_line": float(nn[mover][0]),
                    "old_price": oo[mover][1], "new_price": nn[mover][1],
                    "old_other_price": oo[other][1], "new_other_price": nn[other][1],
                    "line_delta": round(float(nn[mover][0]) - float(oo[mover][0]), 2),
                    "price_delta_cents": round(cents(nn[mover][1]) - cents(oo[mover][1]), 1),
                    "fair_before": round(p_before, 5), "fair_after_own_line": round(p_after, 5),
                    "threshold_cost": round(am_prob(oo[mover][1]), 5),
                    "prev_fetched": o.get("fetched"), "pin_upd": w.get("upd"), "new_market": w})
    return out


def run_polls(n, games, horizon, pin, polls, acct, fast_only=False):
    """Poll every due sport (credit guard first). Updates the Pinnacle cache; returns (moves, xbooks, status)."""
    now_s = n.timestamp()
    moves, xbooks, status = [], {}, []
    for lg in LEAGUES:
        due, near = poll_due(lg, games, polls, now_s)
        if due is None or due > time.time() + 1 or (fast_only and not near):
            continue
        need = credit_need(n)
        prev = polls.get(lg) or {}
        if acct.get("remaining") is not None and acct["remaining"] - CREDITS_PER_POLL < need:
            status.append(f"{lg}:guard")
            acct["guarded"] = acct.get("guarded", 0) + 1
            polls[lg] = dict(prev, t=time.time(), skipped="guard")   # try again at the next due time, not in a loop
            continue
        try:
            new_pin, xb = poll_sport(n, lg, horizon, acct)
        except Exception as ex:
            say(f"Pinnacle poll failed {lg}: {str(ex)[:80]}")
            status.append(f"{lg}:fail")
            polls[lg] = dict(prev, t=time.time(), skipped="fail")
            continue
        acct["polls"] = acct.get("polls", 0) + 1
        prev_t = prev.get("poll_t")   # last SUCCESSFUL poll (moves compare consecutive polls)
        polls[lg] = {"t": time.time(), "poll_t": time.time(), "near": near}
        status.append(f"{lg}:{'fast' if near else 'slow'}")
        for gid, nm in new_pin.items():
            g = next((x for x in games if x["id"] == gid), None)
            if g and g["start_ts"] > now_s and prev_t and gid in pin:
                for mv in detect_moves(pin[gid], nm, g, now_s):
                    mv["prev_poll_gap_s"] = round(time.time() - prev_t)
                    moves.append(mv)
            pin[gid] = nm
        for b, d in xb.items():
            xbooks.setdefault(b, {}).update(d)
    return moves, xbooks, ",".join(status) or "none_due"


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
    """Close = last pregame read. Consensus close needs the exchanges to list the sighting's line; the Pinnacle close
    (at the sighting's own number, half points priced in) does not."""
    now = n.timestamp()
    for s in sightings:
        if s.get("close_final"):
            continue
        st = piso(s["start_utc"]).timestamp()
        if st <= now:   # game started: the last pregame read is the close
            s["close_final"] = True
            if s.get("close_read_utc") is None and s.get("pin_close_read_utc") is None:
                s["close_missing"] = True
            continue
        c = s.get("sighting_cost_af")
        grp = groups.get((s["game_id"], s["market"], s["line"], s["side"]))
        snap = snapshot(grp) if grp else None
        if snap:
            s["close_read_utc"] = iso(n)
            s["close_mins_before_start"] = round((st - now) / 60)
            s["close_consensus_fair"] = snap["consensus_mid"]
            s["close_median_cost_af"] = snap["median_cost_af"]
            s["close_n_books"] = snap["n_books"]
            s["close_prices"] = {b: (v["cost_after_fee"] if v else None) for b, v in snap["prices"].items()}
            s["clv_consensus_c"] = (round(100 * (snap["consensus_mid"] - c), 2)
                                    if (snap["consensus_mid"] is not None and c is not None) else None)
        pm = pin.get(s["game_id"])
        mk = (pm or {}).get("spreads" if s["market"] == "spread" else "totals") or {}
        if pm and mk.get("fetched") and mk["fetched"] < st:
            p, pl, same = pin_close_fair(s, pm)
            if p is not None and mk["fetched"] != s.get("_pin_close_fetched"):
                s["_pin_close_fetched"] = mk["fetched"]
                s["pin_close_read_utc"] = iso(datetime.fromtimestamp(mk["fetched"], timezone.utc))
                s["pin_close_mins_before_start"] = round((st - mk["fetched"]) / 60)
                s["pin_close_fair"], s["pin_close_line"], s["pin_close_same_line"] = p, pl, same
                s["pin_close_far"] = pin_close_far(s)
                s["clv_pinnacle_c"] = (round(100 * (p - c), 2) if (c is not None and not s["pin_close_far"]) else None)
                if s.get("pin_before_fair") is not None:   # A1: did Pinnacle's move hold to the close?
                    s["move_held_c"] = round(100 * (p - s["pin_before_fair"]), 2)


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
            c = s.get("sighting_cost_af")
            s["result"], s["graded_utc"] = r, iso(n)
            s["units_flat"] = (None if c is None else
                               (round((1 - c) / c, 4) if r == "W" else (-1.0 if r == "L" else 0.0)))


# ---------------------------------------------------------------- A1: Pinnacle move-watch
def dollars_at_or_better(book, ladder, thr):
    return round(sum(d for c, d in ladder or [] if (after_fee(book, c) or 9) <= thr + 1e-9))


def record_moves(moves, groups, n, sightings):
    """One record per Pinnacle move (gettable or not: the not-gettable ones are the control group)."""
    added = 0
    for mv in moves:
        g, thr = mv["game"], mv["threshold_cost"]
        side_key = mv["side"] if mv["market"] == "total" else mv["side"]
        grp = groups.get((g["id"], mv["market"], round(mv["old_line"], 2), side_key)) or {"books": {}}
        per, best_any, best_get = {}, None, None
        for b in BOOKS:
            q = grp["books"].get(b)
            if not q or q.get("cost_af") is None:
                per[b] = {"status": "no_line" if not q else "no_offer"}
                continue
            dol = dollars_at_or_better(b, q.get("ladder"), thr)
            ok_price = q["cost_af"] <= thr + 1e-9
            st = "gettable" if (ok_price and dol >= M_DEPTH) else ("thin" if ok_price else "worse")
            per[b] = {"status": st, "cost": q["cost"], "cost_after_fee": round(q["cost_af"], 4),
                      "american_after_fee": lm.american(round(q["cost_af"], 4)), "depth_at_best_usd": round(q["depth"]),
                      "dollars_at_or_better_usd": dol,
                      "read_utc": iso(datetime.fromtimestamp(q["read_ts"], timezone.utc)),
                      "read_after_detect_s": round(q["read_ts"] - mv["detected_ts"], 1)}
            if best_any is None or q["cost_af"] < best_any[1]["cost_af"]:
                best_any = (b, q)
            if st == "gettable" and (best_get is None or q["cost_af"] < best_get[1]["cost_af"]):
                best_get = (b, q)
        src = best_get or best_any
        upd = mv.get("pin_upd")
        rec = {
            "key": f"M|{g['id']}|{mv['market']}|{mv['old_line']:g}|{mv['side']}|{int(mv['detected_ts'])}",
            "trigger": "M", "move_type": mv["move_type"], "gettable": best_get is not None,
            "cost_source": "gettable" if best_get else ("best_available_not_gettable" if best_any else None),
            "sighted_utc": iso(datetime.fromtimestamp(mv["detected_ts"], timezone.utc)),
            "game_id": g["id"], "league": g["league"], "game": f"{g['teams'][0]} @ {g['teams'][1]}", "teams": g["teams"],
            "start_utc": iso(datetime.fromtimestamp(g["start_ts"], timezone.utc)),
            "lead_min": round((g["start_ts"] - mv["detected_ts"]) / 60),
            "market": mv["market"], "line": round(mv["old_line"], 2), "side": side_key,
            "pin_before": {"line": mv["old_line"], "price": mv["old_price"], "other_price": mv["old_other_price"]},
            "pin_after": {"line": mv["new_line"], "price": mv["new_price"], "other_price": mv["new_other_price"]},
            "line_delta": mv["line_delta"], "price_delta_cents": mv["price_delta_cents"],
            "pin_before_fair": mv["fair_before"], "pin_after_fair_own_line": mv["fair_after_own_line"],
            "threshold_cost": thr,
            "pinnacle_update_utc": iso(datetime.fromtimestamp(upd, timezone.utc)) if upd else None,
            "detection_lag_s": round(mv["detected_ts"] - upd, 1) if upd else None,
            "prev_poll_gap_s": mv.get("prev_poll_gap_s"),
            "books": per, "best_book": src[0] if src else None,
            "depth_at_best_usd": round(src[1]["depth"]) if src else None,
            "sighting_cost": src[1]["cost"] if src else None,
            "sighting_cost_af": round(src[1]["cost_af"], 5) if src else None,
            "sighting_american_af": lm.american(round(src[1]["cost_af"], 4)) if src else None,
            "result": None, "units_flat": None, "close_final": False,
        }
        p_after_old, _, _ = pin_close_fair(rec, mv["new_market_pm"])
        rec["pin_after_fair_old_line"] = p_after_old
        sightings.append(rec)
        added += 1
        say(f"MOVE {mv['move_type']} {g['league']} {rec['game']} | {mv['market']} {mv['side']} {mv['old_line']:+g} -> "
            f"{mv['new_line']:+g} ({mv['old_price']} -> {mv['new_price']}) | lag {rec['detection_lag_s']}s | "
            f"{'GETTABLE ' + best_get[0] if best_get else 'not gettable'}")
    return added


# ---------------------------------------------------------------- A2: maker test (paper resting orders)
# Amendment A2 (Oct 29, Peter: "do what you think is best"). Hypothetical bids on Novig and ProphetX at Pinnacle's no-vig
# fair minus 1c and 2c (after fees), main lines only (Pinnacle's own number), games within MK_NEAR_H hours. One order per
# book/side/line/margin at a time, living MK_LIFE_S or until the start. FILLED when a later read shows that book's best
# price to BUY the side BELOW our bid (the market traded through us; equal-price fills and between-read touches are not
# counted, so the fill rate is a lower bound). Filled orders are graded (Pinnacle CLV + flat 1u at our after-fee price);
# unfilled orders get Pinnacle CLV too, so filled vs unfilled shows adverse selection.
MK_BOOKS = ("novig", "prophetx")
MK_MARGINS = (0.01, 0.02)
MK_NEAR_H = float(os.environ.get("EV_MK_NEAR_HOURS", "") or "6")
MK_LIFE_S = float(os.environ.get("EV_MK_LIFE_SEC", "") or "3600")


def screen_for_cost(book, e):
    """Screen price whose after-fee cost is e (inverse of after_fee)."""
    if book == "prophetx":
        return (1 - PX_FEE) / ((1 / e - 1) + (1 - PX_FEE))
    return e   # Novig: no fee


def maker_step(doc, groups, pin, n):
    """Fill/expire open paper orders against this read, then post new ones. Returns (posted, filled)."""
    orders = doc.setdefault("maker", [])
    agg = doc.setdefault("maker_agg", {})
    keep = []
    for o in orders:   # unfilled orders whose game has started: fold into counters (keeps the file small), drop detail
        if o.get("status") == "expired" and o.get("close_final"):
            a = agg.setdefault(f"{o['book']}|{o['margin']}", {"n": 0, "clv_n": 0, "clv_sum": 0.0})
            a["n"] += 1
            if o.get("clv_pinnacle_c") is not None:
                a["clv_n"] += 1
                a["clv_sum"] = round(a["clv_sum"] + o["clv_pinnacle_c"], 2)
        else:
            keep.append(o)
    orders[:] = keep
    now = n.timestamp()
    posted = filled = 0
    open_keys = set()
    for o in orders:
        if o.get("status") != "open":
            continue
        grp = groups.get((o["game_id"], o["market"], o["line"], o["side"]))
        q = (grp or {}).get("books", {}).get(o["book"]) if grp else None
        if q and q.get("cost") is not None and q["read_ts"] > o["posted_ts"] and q["cost"] < o["bid_screen"] - 1e-9:
            o.update(status="filled", filled_utc=iso(n), fill_read_cost=q["cost"])
            filled += 1
        elif now >= o["expires_ts"] or now >= piso(o["start_utc"]).timestamp():
            o["status"] = "expired"
        else:
            open_keys.add((o["book"], o["game_id"], o["market"], o["line"], o["side"], o["margin"]))
    for (gid, market, line, side), grp in groups.items():
        g = grp["game"]
        lead = g["start_ts"] - now
        if not 0 < lead <= MK_NEAR_H * 3600:
            continue
        fair, pline, pupd = pin_fair(pin.get(gid), market, side, line, g["teams"])
        if not fair:
            continue   # main lines only: Pinnacle must price this exact number
        for b in MK_BOOKS:
            q = grp["books"].get(b)
            if not q or q.get("cost") is None:
                continue
            for m in MK_MARGINS:
                if (b, gid, market, line, side, m) in open_keys:
                    continue
                e = fair - m
                if not 0.05 < e < 0.95:
                    continue
                bid = screen_for_cost(b, e)
                if b == "novig":
                    bid = int(bid * 100 + 1e-9) / 100.0   # 1c ticks, rounded down (never better than fair - margin)
                if bid >= q["cost"] - 1e-9:
                    continue   # at or above the price you can already take: that is a take, not a resting order
                orders.append({
                    "trigger": "MK", "status": "open", "book": b, "margin": m, "game_id": gid, "league": g["league"],
                    "game": f"{g['teams'][0]} @ {g['teams'][1]}", "teams": g["teams"], "market": market, "line": line,
                    "side": side, "start_utc": iso(datetime.fromtimestamp(g["start_ts"], timezone.utc)),
                    "lead_min": round(lead / 60), "posted_utc": iso(n), "posted_ts": q["read_ts"],
                    "expires_ts": q["read_ts"] + MK_LIFE_S, "pin_fair_at_post": fair,
                    "bid_screen": round(bid, 4), "sighting_cost_af": round(after_fee(b, bid), 5),
                    "taker_cost_at_post": q["cost"], "result": None, "units_flat": None, "close_final": False})
                posted += 1
    return posted, filled


def maker_rows(doc):
    """Report rows per book x margin (+ all): orders, fill rate, filled CLV/record, unfilled CLV (adverse selection)."""
    ms = doc.get("maker") or []
    agg = doc.get("maker_agg") or {}
    out = []
    for b in MK_BOOKS + ("all",):
        for m in MK_MARGINS:
            rows = [o for o in ms if (b == "all" or o["book"] == b) and o["margin"] == m]
            ag = [v for k, v in agg.items() if (b == "all" or k.split("|")[0] == b) and abs(float(k.split("|")[1]) - m) < 1e-9]
            fl = [o for o in rows if o["status"] == "filled"]
            un = [o for o in rows if o["status"] == "expired"]
            n_un = len(un) + sum(v["n"] for v in ag)
            ucl = [o["clv_pinnacle_c"] for o in un if o.get("clv_pinnacle_c") is not None and o.get("close_final")]
            u_n = len(ucl) + sum(v["clv_n"] for v in ag)
            u_sum = sum(ucl) + sum(v["clv_sum"] for v in ag)
            st = bucket_stats(fl)
            out.append(dict(name=f"MK {b} fair-{m * 100:g}c", orders=len(fl) + n_un + sum(1 for o in rows if o["status"] == "open"),
                            filled=len(fl), fill_rate_pct=round(100 * len(fl) / max(len(fl) + n_un, 1), 1),
                            unfilled_clv_pinnacle_avg_c=round(u_sum / u_n, 2) if u_n else None,
                            gate=(gate(st, "clv_pinnacle_avg_c") if b == "all" else ""), **st))
    return out


# ---------------------------------------------------------------- sightings A / B
def sightings_from(groups, pin, n, existing, xbooks):
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
        pfetched = (((pin.get(gid) or {}).get("spreads" if market == "spread" else "totals")) or {}).get("fetched")
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
                "pin_fetch_to_read_s": round(bq["read_ts"] - pfetched, 1) if (pfetched and fair) else None,
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
    pinc = [s for s in rows if s.get("clv_pinnacle_c") is not None and s.get("close_final") and not pin_close_far(s)]
    gr = [s for s in rows if s.get("result") in ("W", "L", "P") and s.get("units_flat") is not None]
    w = sum(1 for s in gr if s["result"] == "W")
    l = sum(1 for s in gr if s["result"] == "L")
    p = sum(1 for s in gr if s["result"] == "P")
    u = sum(s["units_flat"] for s in gr)
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    held = [s["move_held_c"] for s in rows if s.get("move_held_c") is not None and s.get("close_final")]
    lags = [s["detection_lag_s"] for s in rows if s.get("detection_lag_s") is not None]
    return {"n": len(rows), "n_closed": len(closed), "clv_consensus_avg_c": avg([s["clv_consensus_c"] for s in closed]),
            "beat_consensus_pct": round(100 * sum(1 for s in closed if s["clv_consensus_c"] > 0) / len(closed), 1) if closed else None,
            "n_pin_closed": len(pinc), "clv_pinnacle_avg_c": avg([s["clv_pinnacle_c"] for s in pinc]),
            "beat_pinnacle_pct": round(100 * sum(1 for s in pinc if s["clv_pinnacle_c"] > 0) / len(pinc), 1) if pinc else None,
            "graded": len(gr), "record": f"{w}-{l}-{p}", "units": round(u, 2),
            "roi_pct": round(100 * u / len(gr), 1) if gr else None,
            "move_held_avg_c": avg(held), "detection_lag_median_s": round(statistics.median(lags)) if lags else None}


def gate(st, clv_key="clv_consensus_avg_c"):
    ok = st["graded"] >= 50 and (st[clv_key] or 0) > 0 and st["units"] > 0
    return ("criteria met - eligible for discussion at the scheduled review only" if ok else
            f"criteria not met ({st['graded']}/50 graded" + (", CLV not positive" if not (st[clv_key] or 0) > 0 else "")
            + (", record not positive" if st["units"] <= 0 else "") + ")")


def credit_projection(doc, n):
    """Study's own credits/day and all-monitor burn/day (from x-requests-remaining), each projected to 30 days."""
    log = (doc.get("credits") or {}).get("log") or []
    if len(log) < 2:
        return {"note": "not enough runs yet"}
    t0, t1 = piso(log[0][0]), piso(log[-1][0])
    days = max((t1 - t0).total_seconds() / 86400, 1 / 24)
    used = sum(x[2] or 0 for x in log)
    burn, seg = 0.0, None   # sum of decreases in remaining (a monthly reset shows as an increase: skipped)
    for x in log:
        if x[1] is None:
            continue
        if seg is not None and x[1] <= seg:
            burn += seg - x[1]
        seg = x[1]
    return {"days_observed": round(days, 2), "study_credits_used": used,
            "study_per_day": round(used / days), "study_projected_30d": round(30 * used / days),
            "all_monitors_per_day": round(burn / days), "all_monitors_projected_30d": round(30 * burn / days),
            "remaining_now": next((x[1] for x in reversed(log) if x[1] is not None), None),
            "guard_need_now": round(credit_need(n)),
            "guarded_polls": sum(x[3] if len(x) > 3 else 0 for x in log),
            "plan": 100000}


def report(doc):
    ss = doc.get("sightings", [])
    for x in ss:
        x["suspect"] = is_suspect(x)
    C = [x for x in ss if not x["suspect"]]
    M = [x for x in C if x["trigger"] == "M"]
    groups = [("A cross-book (>= 2c)", [x for x in C if x["trigger"] == "A"], "clv_consensus_avg_c"),
              ("A qualifying (>= 3c)", [x for x in C if x["trigger"] == "A" and x.get("qualifying")], "clv_consensus_avg_c"),
              ("B Pinnacle (>= 3% EV)", [x for x in C if x["trigger"] == "B"], "clv_consensus_avg_c")]
    for bk in ("<60s", "1-5m", "5m+"):
        groups.append((f"  B ref age {bk}", [x for x in C if x["trigger"] == "B" and x.get("ref_age_bucket") == bk], None))
    groups += [("M move-watch: gettable (sightings)", [x for x in M if x.get("gettable")], "clv_pinnacle_avg_c"),
               ("  M gettable, line moves", [x for x in M if x.get("gettable") and x["move_type"] == "line"], None),
               ("  M gettable, price moves", [x for x in M if x.get("gettable") and x["move_type"] == "price"], None),
               ("M control: not gettable", [x for x in M if not x.get("gettable")], None),
               ("M all moves", M, None),
               ("Suspect (10c+ gap / crossed), all legs - excluded above", [x for x in ss if x["suspect"]], None)]
    out = {"study": doc.get("study"), "generated_utc": iso(datetime.now(timezone.utc)), "rows": []}
    for name, rows, gk in groups:
        st = bucket_stats(rows)
        st["gate"] = gate(st, gk) if gk else ""
        out["rows"].append(dict(name=name, **st))
    both = {s["key"].split("|", 1)[1] for s in ss if s["trigger"] == "A"} & {s["key"].split("|", 1)[1] for s in ss if s["trigger"] == "B"}
    out["overlap_A_and_B"] = len(both)
    out["maker"] = maker_rows(doc)
    out["credits"] = credit_projection(doc, datetime.now(timezone.utc))
    return out


def report_md(rep, runs):
    L = ["# EV sightings study (paper, measurement only)", "",
         f"Started {(rep.get('study') or {}).get('started_utc')}. Updated {rep['generated_utc']}. "
         f"Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). "
         f"Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. "
         f"A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move "
         f"fair at the old number (+ = the move held). Rows exclude suspect sightings (best price {SUSPECT_C:g}c+ under the "
         f"other books, or a crossed quote: usually a misread line); Pinnacle CLV only within {PIN_NEAR_PTS:g} points of "
         f"Pinnacle's number.", "",
         "| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rep["rows"]:
        f = lambda v, sfx="": "" if v is None else f"{v}{sfx}"
        L.append(f"| {r['name'].strip()} | {r['n']} | {r['n_closed']} | {f(r['clv_consensus_avg_c'], 'c')} | {f(r['beat_consensus_pct'], '%')} | "
                 f"{r['n_pin_closed']} | {f(r['clv_pinnacle_avg_c'], 'c')} | {r['graded']} | {r['record']} | {r['units']:+.2f}u | "
                 f"{f(r['roi_pct'], '%')} | {f(r['move_held_avg_c'], 'c')} | {f(r['detection_lag_median_s'], 's')} | {r['gate']} |")
    L += ["", "## A2 maker test (paper resting orders, Novig + ProphetX, main lines)", "",
          "Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled "
          "would have gained; if fills do much worse than unfilled, that is adverse selection.", "",
          "| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rep.get("maker") or []:
        f = lambda v, sfx="": "" if v is None else f"{v}{sfx}"
        L.append(f"| {r['name']} | {r['orders']} | {r['filled']} | {r['fill_rate_pct']}% | {f(r['clv_pinnacle_avg_c'], 'c')} | "
                 f"{f(r['unfilled_clv_pinnacle_avg_c'], 'c')} | {r['record']} | {r['units']:+.2f}u | {r['gate']} |")
    c = rep.get("credits") or {}
    L += ["", f"A and B on the same side/line: {rep['overlap_A_and_B']}.", "",
          "## Odds API credits (100K/month plan)", "",
          "Study: " + (f"{c.get('study_per_day')}/day, projected {c.get('study_projected_30d')}/30 days. "
                       f"All monitors on the key: {c.get('all_monitors_per_day')}/day, projected {c.get('all_monitors_projected_30d')}/30 days. "
                       f"Remaining {c.get('remaining_now')}; guard holds {c.get('guard_need_now')} for the sharp monitor; "
                       f"polls skipped by the guard: {c.get('guarded_polls')}." if "study_per_day" in c else c.get("note", "")),
          "", "## Last runs", ""]
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
        "B = best gettable (>= $250) after-fee cost beats Pinnacle no-vig fair at the same line by >= 3% EV; "
        "M (Amendment A1, Oct 27) = Pinnacle move-watch: Pinnacle line moves >= 0.5 pts between consecutive polls (primary) or "
        "price moves >= 5 cents on an unchanged line (cents scale: -110=110, +100=100, +105=95); the four exchanges are read "
        "the same cycle at the OLD number for the side the market moved toward. gettable = a book's after-fee cost <= "
        "Pinnacle's pre-move price on that side (threshold_cost, with vig) AND >= $250 resting at that price or better. "
        "Every move is logged; not-gettable moves are the control group (graded at the best available price at the old "
        "number when any book lists it). detection_lag_s = detection time - Pinnacle's market last_update. "
        "move_held_c = Pinnacle close fair at the old number - pre-move fair. One record per A/B trigger/game/market/line/side "
        "(first sighting; last_seen/scans_seen while it persists); one record per move. Costs are 0-1 per $1 payout "
        "after fees (Kalshi 0.07 and Polymarket US 0.0695 x P x (1-P) taker; ProphetX 2% of winnings; Novig none). "
        "depth_usd = $ bettable at that book's best price. ref_age_s = exchange read time - Pinnacle market last_update. "
        "Close = last pregame read; close_consensus_fair = median of books' no-vig mids; pin_close_fair = "
        "sharp_monitor.close_prob at the sighting's number from the last pregame Pinnacle poll (pin_close_same_line false = "
        "half points priced in). clv_*_c = (close fair - sighting_cost_af) x 100. result/units_flat = ESPN final, flat 1u at "
        "sighting_cost_af. crossed = that book's two sides cost < 97c total (stale/crossed quote). Pinnacle polls: every "
        "{FAST}s per sport while a game starts within {NEAR}h, every {SLOW}s otherwise; skipped when the credits left would fall below "
        "the sharp monitor's projected need for the rest of the month. A2 maker test: see the maker list (paper resting bids). Oct 28 data-quality rules: suspect = best price "
        "10c+ under the other books' median or a crossed quote (kept, flagged, excluded from headline report rows); "
        "clv_pinnacle_c only when the sighting's line is within 3 points of Pinnacle's (pin_close_far)." .replace("{FAST}", f"{FAST_S:g}").replace("{NEAR}", f"{NEAR_H:g}").replace("{SLOW}", f"{SLOW_S:g}"))


def read_all(n, stop_at, horizon=None, only=None):
    quotes = []
    readers = {"kalshi": read_kalshi, "novig": read_novig, "polymarket_us": read_pmus, "prophetx": read_px}
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(fn, n, stop_at, horizon, only) for b, fn in readers.items() if b in READ_BOOKS]
        for f in futs:
            try:
                quotes += f.result()
            except Exception as e:
                say(f"book reader failed: {str(e)[:80]}")
    return quotes


def snapshot_moves(moves, n, games, base_quotes, horizon, sightings):
    """Read the exchanges for the moved games (reusing this cycle's full read when it covers them) and record moves."""
    if not moves:
        return 0
    now_s = time.time()
    for mv in moves:
        mv["detected_ts"] = now_s
        mv["new_market_pm"] = {("spreads" if mv["market"] == "spread" else "totals"): mv["new_market"]}
    moved = list({mv["game"]["id"]: mv["game"] for mv in moves}.values())
    covered = {mv["game"]["id"] for mv in moves if base_quotes is not None
               and mv["game"]["start_ts"] <= n.timestamp() + WINDOW_H * 3600}
    need = [g for g in moved if g["id"] not in covered]
    quotes = list(base_quotes or [])
    if need:
        quotes += read_all(n, time.time() + 90, horizon, need)
    groups, _ = build_groups(quotes, games)
    return record_moves(moves, groups, n, sightings)


def run():
    n = datetime.now(timezone.utc)
    t0 = time.time()
    doc = load_doc()
    doc.setdefault("study", {"started_utc": iso(n), "approved": "2026-10-27", "interim_due": "1 week after start",
                             "final_due": "2 weeks after start"})
    doc["study"]["params"] = {"A_min_c": 100 * A_MIN, "A_qual_c": 100 * A_QUAL, "A_depth": A_DEPTH, "B_min_ev": B_MIN_EV,
                              "B_depth": B_DEPTH, "leagues": LEAGUES, "markets": ["spread", "total"], "window_h": WINDOW_H,
                              "A1": {"approved": "2026-10-27", "move_line_pts": MOVE_LINE, "move_price_cents": MOVE_CENTS,
                                     "depth": M_DEPTH, "fast_s": FAST_S, "slow_s": SLOW_S, "near_h": NEAR_H,
                                     "sm_daily": SM_DAILY, "sm_margin": SM_MARGIN}}
    doc["study"].setdefault("a1_started_utc", iso(n))
    sightings = doc.setdefault("sightings", [])
    runs = doc.setdefault("runs", [])
    pin = doc.setdefault("pin_cache", {})
    polls = doc.setdefault("polls", {})
    acct = {"used": 0, "remaining": None}
    hr = n.astimezone(ET).hour
    summary, err = "", None
    try:
        if ACTIVE_ET[0] <= hr < ACTIVE_ET[1] and ODDS_KEY:
            horizon = end_of_tomorrow(n)
            games = read_games(n, horizon, acct)
            moves, xbooks, pst = run_polls(n, games, horizon, pin, polls, acct)
            games24 = [g for g in games if g["start_ts"] <= n.timestamp() + WINDOW_H * 3600]
            quotes = read_all(n, time.time() + BOOK_SEC) if games24 else []
            groups, unmatched = build_groups(quotes, games)
            n_moves = snapshot_moves(moves, n, games, quotes, horizon, sightings)
            added = sightings_from(groups, pin, n, sightings, xbooks)
            update_closes(sightings, groups, pin, n)
            mk_posted, mk_filled = maker_step(doc, groups, pin, n)
            loop_polls = []
            while True:   # A1: keep polling in-window sports until LOOP_S; read exchanges only on a move
                dues = [poll_due(lg, games, polls, time.time()) for lg in LEAGUES]
                nxt = min((d for d, near in dues if d is not None and near), default=None)
                if nxt is None or nxt > t0 + LOOP_S:
                    break
                time.sleep(max(0.0, nxt - time.time()))
                n2 = datetime.now(timezone.utc)
                mv2, _, p2 = run_polls(n2, games, horizon, pin, polls, acct, fast_only=True)
                loop_polls.append(p2)
                n_moves += snapshot_moves(mv2, n2, games, None, horizon, sightings)
                update_closes(sightings, {}, pin, n2)   # Pinnacle close only (consensus close needs the full read)
                update_closes(doc.get("maker") or [], {}, pin, n2)
            by_book = {b: sum(1 for q in quotes if q["book"] == b) for b in BOOKS}
            summary = (f"{len(games)} games ({len(games24)} in 24h), quotes {by_book}, {unmatched} unmatched, {len(groups)} side/lines, "
                       f"polls [{pst}{'; ' + '; '.join(loop_polls) if loop_polls else ''}], moves {n_moves}, "
                       f"new A {added['A']} B {added['B']}, maker posted {mk_posted} filled {mk_filled}, credits used {acct['used']} left {acct['remaining']}, "
                       f"{time.time() - t0:.0f}s")
        else:
            update_closes(sightings, {}, pin, n)
            update_closes(doc.get("maker") or [], {}, pin, n)
            summary = "outside read hours: closes/grades only" if ODDS_KEY else "no ODDS_API_KEY"
        update_closes(doc.get("maker") or [], {}, pin, n)
        grade(sightings, n)
        grade([o for o in doc.get("maker") or [] if o["status"] == "filled"], n)
    except Exception as ex:   # never lose the record: log the failure and still save
        import traceback
        err = traceback.format_exc()[-600:]
        summary = f"RUN ERROR: {str(ex)[:150]}"
        say(err)
    finally:
        cutoff = n.timestamp() - 86400
        doc["pin_cache"] = {gid: pm for gid, pm in pin.items()
                            if max((m.get("fetched") or 0) for m in pm.values()) > cutoff}
        cl = doc.setdefault("credits", {}).setdefault("log", [])
        cl.append([iso(n), acct["remaining"], acct["used"], acct.get("guarded", 0)])
        doc["credits"]["log"] = cl[-5000:]
        runs.append({"utc": iso(n), "summary": summary, **({"error": err} if err else {})})
        doc["runs"] = runs[-300:]
        doc["note"] = NOTE
        try:
            rep = report(doc)
            doc["summary"] = rep
            md = report_md(rep, doc["runs"])
        except Exception as ex:
            md = f"report failed: {ex}\n"
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(OUT_FILE, "w") as f:
            json.dump(doc, f, indent=1)
        with open(os.path.join(OUT_DIR, "README.md"), "w") as f:
            f.write(md)
        say(f"Done: {summary}")
    if err:
        sys.exit(1)


def print_report():
    doc = load_doc()
    rep = report(doc)
    print(report_md(rep, doc.get("runs", [])))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report()
    else:
        run()
