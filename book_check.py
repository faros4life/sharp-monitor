#!/usr/bin/env python3
"""
Exchange book check for sharp-monitor phone alerts (FLAG ONLY: never vetoes or delays anything).

For every ntfy alert that went to the phone (pushed_to_phone, not a repeat) with 2h+ lead and a game that hasn't
started, read the Novig order book for that game's market at the alert's line and publish:
  - best gettable price to BUY the alert side (Novig orders are bids: buying side X takes the resting bids on the
    other outcome at 1 - p),
  - dollars available to buy the alert side at each price, and in total at the alert price or better,
  - dollars resting as bids ON the alert side (others wanting the same side).

Novig: public, unsigned catalog and book routes (no key). ProphetX: read-only, with the PROPHETX_ACCESS_KEY /
PROPHETX_SECRET_KEY GitHub secrets (login -> markets; never places, changes or cancels orders).
Output: books/novig-books.json (both books per alert). Reads alerts.json (sharp-monitor) and never writes to it.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import liquidity_monitor as lm  # shared helpers only: get(), team matching, Novig league map

# Exchange abbreviations ('OKC -8.5', 'DEN') -> city/nickname words, added to the shared matcher for this script only.
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
        lm.ALIAS.setdefault(_w[0], set()).update(_w[1:])

SHARP_FILE = os.environ.get("SHARP_ALERTS", "") or "alerts.json"
OUT_FILE = os.environ.get("BOOKS_FILE", "") or os.path.join("books", "novig-books.json")
MIN_LEAD_MIN = float(os.environ.get("BOOK_MIN_LEAD_MIN", "") or "120")
LOOKBACK_H = float(os.environ.get("BOOK_LOOKBACK_HOURS", "") or "36")
N_MKT = {"MONEY": "moneyline", "MONEYLINE": "moneyline", "SPREAD": "spread", "TOTAL": "total"}


def am_to_prob(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def parse_bet(bet, teams, lg=None):
    """'Oklahoma City Thunder -8.5 (-120)' -> ('spread', team_index, -8.5, -120); 'Under 221 (-111)' -> ('total', 'UNDER', 221, -111)."""
    m = re.search(r"\(([+-]\d+)\)\s*$", bet)
    price = int(m.group(1)) if m else None
    if bet.startswith(("Over", "Under")):
        mt = re.match(r"^(Over|Under) ([\d.]+)", bet)
        return "total", ("OVER" if bet.startswith("Over") else "UNDER"), float(mt.group(2)), price
    if " ML " in bet:
        team = bet.split(" ML ")[0]
        mp = re.search(r"ML ([+-]\d+)", bet)
        return "moneyline", lm.team_side(team, teams, lg), None, int(mp.group(1)) if mp else price
    if re.search(r" (PL|RL) ", bet):
        return None, None, None, None   # puck/run lines: not mapped yet
    ms = re.match(r"^(.*?) ([+-]?\d+(?:\.\d+)?|PK) \(", bet)
    if not ms:
        return None, None, None, None
    line = 0.0 if ms.group(2) == "PK" else float(ms.group(2))
    return "spread", lm.team_side(ms.group(1), teams, lg), line, price


# ---------------------------------------------------------------- ProphetX (read-only)
PX_BASE = os.environ.get("PX_BASE", "") or "https://cash.api.prophetx.co/partner"
PX_ACCESS = os.environ.get("PROPHETX_ACCESS_KEY", "")
PX_SECRET = os.environ.get("PROPHETX_SECRET_KEY", "")
PX_TOURNAMENTS = {"NHL": 234, "NFL": 31, "NCAAF": 27653, "NBA": 132, "MLB": 109}
_PX = {"token": None, "events": {}, "markets": {}, "logged_shape": False}
PX_FEE = float(os.environ.get("PX_FEE", "") or "0.02")   # ProphetX takes 2% of winnings


def after_fee(american, fee):
    """Effective American odds after a fee on winnings: -107 at 2% -> about -109; +455 -> +446."""
    if american is None or not fee:
        return american
    win = (100 / abs(american)) if american < 0 else american / 100   # winnings per $1 risked
    win *= (1 - fee)
    return round(-100 / win) if win < 1 else round(win * 100)


def px_call(path, body=None):
    for i in range(4):
        req = urllib.request.Request(PX_BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                     method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **({"Authorization": f"Bearer {_PX['token']}"} if _PX["token"] else {})})
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


def px_login():
    if _PX["token"] or not (PX_ACCESS and PX_SECRET):
        return bool(_PX["token"])
    d = px_call("/auth/login", {"access_key": PX_ACCESS, "secret_key": PX_SECRET})
    _PX["token"] = (d.get("data") or {}).get("access_token")
    return bool(_PX["token"])


def px_events(league):
    if league not in _PX["events"]:
        tid = PX_TOURNAMENTS.get(league)
        evs = []
        if tid:
            d = px_call(f"/mm/get_sport_events?tournament_id={tid}")
            evs = (d.get("data") or {}).get("sport_events") or []
        _PX["events"][league] = evs
    return _PX["events"][league]


def px_markets(event_id):
    if event_id not in _PX["markets"]:
        d = px_call(f"/v4/mm/get_markets?event_id={event_id}")
        data = d.get("data") or {}
        _PX["markets"][event_id] = data if isinstance(data, list) else (data.get("markets") or data.get(str(event_id)) or [])
    return _PX["markets"][event_id]


def px_lines(mk):
    """[(outcome price levels, line)] for a market. Moneylines carry 'selections' directly; spreads/totals nest one
    entry per line (e.g. market_lines: [{line: -8.5, selections: [[...], [...]]}])."""
    out = [(lv, lm.num(mk.get("strike"))) for lv in (mk.get("selections") or []) if lv]
    if out:
        return out
    for key, val in mk.items():
        if isinstance(val, list) and val and isinstance(val[0], dict) and "selections" in val[0]:
            for ln in val:
                lnum = lm.num(ln.get("line")) if ln.get("line") is not None else lm.num(ln.get("strike"))
                out += [(lv, lnum) for lv in (ln.get("selections") or []) if lv]
    if not out and not _PX.get("keys_logged"):
        _PX["keys_logged"] = True
        print(f"  ProphetX market keys ({mk.get('name')}): {sorted(mk.keys())}")
    return out


def px_check(al, mtype, side, line, price, teams):
    """Best ProphetX price for the alert side and dollars you could bet at the alert price or better.
    ProphetX lists, per outcome, the prices a bettor can take with 'value' = amount bettable at that price."""
    if not px_login():
        return {"status": "no_prophetx_key"}
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": al["sport"], "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    ev, how = None, None
    for e in px_events(al["sport"]):
        comps = e.get("competitors") or []
        home = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "home"), None)
        away = next((c.get("display_name") or c.get("name") for c in comps if c.get("side") == "away"), None)
        if not home or not away:
            tt = lm.split_teams(e.get("name") or "")
            if not tt:
                continue
            away, home = tt
        try:
            d = datetime.fromisoformat(e["scheduled"].replace("Z", "+00:00")).astimezone(lm.ET).date().isoformat()
        except Exception:
            continue
        erow = {"league": al["sport"], "date": d, "teams": [away, home]}
        h = lm.same_game(arow, erow)
        if h:
            ev, how = (e, erow), h
            break
    if not ev:
        return {"status": "game_not_on_prophetx"}
    e, erow = ev
    cands = []
    for mk in px_markets(e["event_id"]):
        if (mk.get("type") or "").lower() != mtype or (mk.get("status") or "active") != "active":
            continue
        if (mk.get("sub_type") or mtype).lower() != mtype:
            continue   # full game only (skip first_half_spread etc.)
        for levels, mline in px_lines(mk):
            if not levels:
                continue
            first = levels[0]
            name = first.get("name") or first.get("display_name") or ""
            if mtype == "total":
                oside = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                ok = oside == side
            else:
                t = lm.team_side(name, erow["teams"], al["sport"])
                ok = t is not None and (t == side if how == "same" else t == 1 - side)
            if not ok:
                continue
            lvl_line = lm.num(first.get("strike"))
            if not lvl_line:
                lvl_line = lm.num(first.get("line"))
            if not lvl_line and mline is not None:
                lvl_line = mline if mtype == "total" else None
            if mtype == "spread" and not lvl_line:
                lvl_line = lm.signed_num((first.get("display_name") or "").replace(str(first.get("display_price") or "#"), ""))
            if not lvl_line:
                lvl_line = lm.num(mk.get("strike"))
            if not _PX["logged_shape"] and mtype in ("spread", "total"):
                _PX["logged_shape"] = True
                print(f"  ProphetX {mtype} sample: market strike {mk.get('strike')} | level: "
                      f"{json.dumps({k: first.get(k) for k in ('name', 'display_name', 'price', 'strike', 'quantity', 'value')})}")
            cands.append((mk, levels, lvl_line if mtype != "moneyline" else None))
    if not cands:
        # diagnostic (one line per miss): how ProphetX lists this game's markets of that kind
        seen = []
        for mk in px_markets(e["event_id"]):
            t = (mk.get("type") or "").lower()
            if t == mtype or mtype in t or (mk.get("sub_type") or "").lower().startswith(mtype):
                sel = [((lv or [{}])[0].get("name"), (lv or [{}])[0].get("strike"), (lv or [{}])[0].get("price"))
                       for lv in (mk.get("selections") or [])]
                seen.append(f"{mk.get('name')}|type={mk.get('type')}|sub={mk.get('sub_type')}|status={mk.get('status')}|"
                            f"strike={mk.get('strike')}|sel={sel}")
        print(f"  ProphetX miss for {al['bet']}: {len(seen)} {mtype} markets: " + " ;; ".join(seen[:6]))
        return {"status": "market_not_on_prophetx", "px_markets_of_type": len(seen)}
    if line is None:
        mk, levels, pline = cands[0]
    else:
        mk, levels, pline = min(cands, key=lambda c: abs((c[2] if c[2] is not None else 1e9) - line))
    lv = sorted(({"american": int(x["price"]), "american_after_fee": after_fee(int(x["price"]), PX_FEE),
                  "dollars": round(float(x.get("value") or 0)),
                  "to_win": round(float(x.get("quantity") or 0))} for x in levels if x.get("price") is not None),
                key=lambda x: -x["american"])   # best price first (higher American = better for the bettor)
    best = lv[0] if lv else None
    # compare AFTER ProphetX's 2% fee on winnings
    at_or_better = sum(x["dollars"] for x in lv if price is not None and x["american_after_fee"] >= price)
    return {"status": "ok", "market_name": mk.get("name"), "prophetx_line": pline, "alert_line": line,
            "exact_line": (line is None) or (pline is not None and abs(pline - line) < 1e-9),
            "alert_price": price, "best_price_american": best["american_after_fee"] if best else None,
            "best_price_american_displayed": best["american"] if best else None, "fee_on_winnings": PX_FEE,
            "dollars_at_best": best["dollars"] if best else 0,
            "dollars_at_alert_price_or_better": round(at_or_better), "buy_levels": lv[:10]}


# ---------------------------------------------------------------- Kalshi + Polymarket (public, no key)
_KC = {"events": {}, "books": {}}
_PMC = {"events": {}}


TAKER_COEF = {"kalshi": float(os.environ.get("KALSHI_FEE", "") or "0.07"),
              "polymarket": float(os.environ.get("PM_FEE", "") or "0.03")}   # per contract = coef x P x (1-P)


def pm_fee_coef(mk):
    """Polymarket fee for this market from gamma: zero-fee markets (feesEnabled false, feeType zero_fees, or rate 0) pay
    nothing; otherwise the default taker coefficient."""
    fs = mk.get("feeSchedule") or {}
    if mk.get("feesEnabled") is False or str(mk.get("feeType") or "").lower() == "zero_fees":
        return 0.0
    if fs.get("rate") is not None and lm.num(fs.get("rate")) == 0:
        return 0.0
    return TAKER_COEF["polymarket"]


def ladder_result(levels, price, line, book_line, extra=None, fee_coef=0.0):
    """levels: [(cost 0-1, dollars)] you can BUY at. Prices compared AFTER the taker fee (coef x P x (1-P) per contract).
    Returns the common result block."""
    agg = {}
    for c, dol in levels:
        if c is None or c <= 0 or c >= 1 or dol <= 0:
            continue
        agg[round(c, 4)] = agg.get(round(c, 4), 0) + dol
    lv = [{"price": c, "american_displayed": lm.american(c), "price_after_fee": round(c + fee_coef * c * (1 - c), 4),
           "american": lm.american(round(c + fee_coef * c * (1 - c), 4)), "dollars": round(d)} for c, d in sorted(agg.items())]
    best = lv[0] if lv else None
    at_or_better = sum(x["dollars"] for x in lv if price is not None and x["american"] is not None and x["american"] >= price)
    out = {"status": "ok" if lv else "no_liquidity", "line": book_line, "alert_line": line,
           "exact_line": (line is None) or (book_line is not None and abs(book_line - line) < 1e-9),
           "alert_price": price, "best_price": best["price_after_fee"] if best else None,
           "best_price_american": best["american"] if best else None,
           "best_price_american_displayed": best["american_displayed"] if best else None, "taker_fee_coef": fee_coef,
           "dollars_at_best": best["dollars"] if best else 0,
           "dollars_at_alert_price_or_better": round(at_or_better), "buy_levels": lv[:10]}
    out.update(extra or {})
    return out


def kalshi_check(al, mtype, side, line, price, teams):
    """Kalshi: buy YES = take NO bids at 1-p; buy NO = take YES bids at 1-p (sizes are contracts at $1)."""
    lg = al["sport"]
    series = f"KX{lm.K_CODE.get(lg, [lg])[0]}" + {"moneyline": "GAME", "spread": "SPREAD", "total": "TOTAL"}[mtype]
    if series not in _KC["events"]:
        try:
            _KC["events"][series] = lm.k_paged("/events", "events", {"series_ticker": series, "status": "open",
                                                                    "with_nested_markets": "true", "limit": 200})
        except Exception as ex:
            print(f"  Kalshi events failed {series}: {ex}")
            _KC["events"][series] = []
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": lg, "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    for ev in _KC["events"][series]:
        d = lm.k_event_date(ev.get("event_ticker", ""))
        kt = lm.split_teams(ev.get("title", ""))
        if not d or not kt:
            continue
        erow = {"league": lg, "date": d.isoformat(), "teams": list(kt)}
        how = lm.same_game(arow, erow)
        if not how:
            continue
        want = side if (side in ("OVER", "UNDER") or how == "same") else 1 - side   # alert side in Kalshi's team order
        options = []   # (market, take 'yes' or 'no', kalshi line for the alert side)
        for mk in ev.get("markets") or []:
            label = mk.get("yes_sub_title") or mk.get("subtitle") or mk.get("title") or ""
            strike = lm.num(mk.get("floor_strike"))
            if strike is None and mtype != "moneyline":
                ms = re.search(r"over ([\d.]+)", label.lower())
                strike = float(ms.group(1)) if ms else None
            if mtype == "total":
                over_yes = "under" not in label.lower()
                buy = "yes" if (want == "OVER") == over_yes else "no"
                options.append((mk, buy, strike))
            else:
                t = lm.team_side(label, kt, al["sport"])
                if t is None:
                    continue
                if mtype == "moneyline":
                    options.append((mk, "yes" if t == want else "no", None))
                else:   # 'T wins by over S': YES = T -S; NO = other team +S
                    if t == want:
                        options.append((mk, "yes", -strike if strike is not None else None))
                    else:
                        options.append((mk, "no", strike))
        if not options:
            return {"status": "market_not_on_kalshi"}
        if mtype == "moneyline":
            picks = options   # both team markets can buy the side: combine
        else:
            best_opt = min(options, key=lambda o: abs((o[2] if o[2] is not None else 1e9) - (line if line is not None else 0)))
            picks = [best_opt]
        levels, kline = [], picks[0][2]
        for mk, buy, _ in picks:
            t = mk["ticker"]
            if t not in _KC["books"]:
                try:
                    _KC["books"][t] = lm.get(f"{lm.KALSHI}/markets/{t}/orderbook")
                except Exception as ex:
                    print(f"  Kalshi book failed {t}: {ex}")
                    _KC["books"][t] = {}
            take = "no" if buy == "yes" else "yes"
            for p, q in lm.k_levels(_KC["books"][t], take):
                c = 1 - p
                levels.append((c, c * q))
        return ladder_result(levels, price, line, kline, {"markets": [o[0]["ticker"] for o in picks]}, TAKER_COEF["kalshi"])
    return {"status": "game_not_on_kalshi"}


def pm_check(al, mtype, side, line, price, teams):
    """Polymarket: buy an outcome = take the asks on that outcome's token."""
    lg = al["sport"]
    tag = lm.PM_TAGS.get(lg)
    if not tag:
        return {"status": "league_not_mapped"}
    if tag not in _PMC["events"]:
        evs, off = [], 0
        try:
            while off < 2000:
                page = lm.get(f"{lm.PM_GAMMA}/events", {"tag_slug": tag, "active": "true", "closed": "false", "limit": 200, "offset": off})
                page = page if isinstance(page, list) else page.get("data", [])
                evs += page
                if len(page) < 200:
                    break
                off += 200
        except Exception as ex:
            print(f"  Polymarket events failed {tag}: {ex}")
        _PMC["events"][tag] = evs
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": lg, "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    for ev in _PMC["events"][tag]:
        pt = lm.split_teams(ev.get("title", ""))
        if not pt:
            continue
        cands = []
        for mk in ev.get("markets") or []:
            mt = lm.PM_MTYPE.get((mk.get("sportsMarketType") or "").lower())
            if mt != mtype or mk.get("closed"):
                continue
            stp = lm.pm_start(mk.get("gameStartTime") or ev.get("startTime") or ev.get("endDate"))
            if not stp:
                continue
            erow = {"league": lg, "date": stp.astimezone(lm.ET).date().isoformat(), "teams": list(pt)}
            how = lm.same_game(arow, erow)
            if not how:
                continue
            outs, tids = lm.jl(mk.get("outcomes")), lm.jl(mk.get("clobTokenIds"))
            if len(outs) != 2 or len(tids) != 2:
                continue
            ln = lm.num(mk.get("line"))
            for i in (0, 1):
                name = str(outs[i])
                if mtype == "total":
                    ok = ("over" in name.lower() and side == "OVER") or ("under" in name.lower() and side == "UNDER")
                    oline = ln
                else:
                    t = lm.team_side(name, pt, al["sport"])
                    ok = t is not None and (t == side if how == "same" else t == 1 - side)
                    oline = None if (mtype != "spread" or ln is None) else (ln if i == 0 else -ln)
                if ok:
                    cands.append((mk, tids[i], oline))
        if not cands:
            continue
        mk, tid, pline = (cands[0] if line is None else
                          min(cands, key=lambda c: abs((c[2] if c[2] is not None else 1e9) - line)))
        try:
            book = lm.get(f"{lm.PM_CLOB}/book", {"token_id": tid})
        except Exception as ex:
            return {"status": f"error: {str(ex)[:80]}"}
        levels = [(float(a["price"]), float(a["price"]) * float(a["size"])) for a in (book.get("asks") or [])]
        return ladder_result(levels, price, line, pline, {"market_id": str(mk.get("id")), "fee_type": mk.get("feeType")}, pm_fee_coef(mk))
    return {"status": "game_not_on_polymarket"}


# ---------------------------------------------------------------- Hard Rock (sportsbook, via The Odds API)
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
HR_BOOKS = os.environ.get("HR_BOOKS", "") or "hardrockbet"
HR_REFRESH_MIN = float(os.environ.get("HR_REFRESH_MIN", "") or "30")   # credit saver: re-read Hard Rock at most every 30 min
_HR = {}
ODDS_SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba", "NHL": "icehockey_nhl"}
ODDS_MKT = {"moneyline": "h2h", "spread": "spreads", "total": "totals"}


def hr_check(al, mtype, side, line, price, teams):
    """Hard Rock price for the alert side (no order book: price and line only)."""
    if not ODDS_KEY:
        return {"status": "no_odds_key"}
    sport, mkt = ODDS_SPORT.get(al["sport"]), ODDS_MKT.get(mtype)
    if not sport or not mkt:
        return {"status": "league_not_mapped"}
    ck = (sport, mkt)
    if ck not in _HR:
        try:
            _HR[ck] = lm.get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                             {"apiKey": ODDS_KEY, "bookmakers": HR_BOOKS, "markets": mkt, "oddsFormat": "american"})
        except Exception as ex:
            return {"status": f"error: {str(ex)[:80]}"}
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": al["sport"], "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    for ev in _HR[ck] or []:
        try:
            d = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).astimezone(lm.ET).date().isoformat()
        except Exception:
            continue
        erow = {"league": al["sport"], "date": d, "teams": [ev.get("away_team", ""), ev.get("home_team", "")]}
        how = lm.same_game(arow, erow)
        if not how:
            continue
        for bk in ev.get("bookmakers", []):
            for m in bk.get("markets", []):
                for o in m.get("outcomes", []):
                    name, pt = o.get("name", ""), o.get("point")
                    if mtype == "total":
                        ok = name.lower() == side.lower() if isinstance(side, str) else False
                    else:
                        t = lm.team_side(name, erow["teams"], al["sport"])
                        ok = t is not None and (t == side if how == "same" else t == 1 - side)
                    if ok:
                        hl = float(pt) if pt is not None else None
                        exact = (line is None) or (hl is not None and abs(hl - line) < 1e-9)
                        return {"status": "ok", "book_key": bk["key"], "price_american": o.get("price"), "line": hl,
                                "alert_line": line, "exact_line": exact, "alert_price": price,
                                "at_alert_price_or_better": (exact and price is not None and o.get("price") is not None
                                                             and o["price"] >= price)}
        return {"status": "market_not_on_hardrock"}
    return {"status": "game_not_on_hardrock"}


def novig_catalog(lo_ms, hi_ms):
    evs = lm.n_paged("/v3/public/catalog/events", {"startsAfter": lo_ms, "startsBefore": hi_ms, "limit": 5000})
    mks = lm.n_paged("/v3/public/catalog/markets", {"startsAfter": lo_ms, "startsBefore": hi_ms, "limit": 5000})
    return evs, mks


def outcome_line(mtype, name, strike, idx, teams):
    if mtype == "total":
        return lm.num(strike)
    if mtype == "spread":
        v = lm.signed_num(name)
        if v is None and lm.num(strike) is not None:
            v = lm.num(strike) if idx == 1 else -lm.num(strike)
        return v
    return None


def check_alert(al, evs_by, mks_by_event):
    teams = lm.split_teams(al["game"])
    if not teams:
        return {"status": "no_teams"}
    mtype, side, line, price = parse_bet(al["bet"], teams, al.get("sport"))
    if not mtype or side is None:
        return {"status": "bet_not_mapped"}
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": al["sport"], "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    ev, how = None, None
    for e in evs_by.values():
        erow = {"league": lm.N_LEAGUE.get((e.get("league") or "").upper().strip()),
                "date": datetime.fromtimestamp(e["startsTs"] / 1000, lm.ET).date().isoformat(),
                "teams": list(lm.split_teams(e.get("description") or "") or [])}
        h = lm.same_game(arow, erow) if erow["teams"] else None
        if h:
            ev, how = (e, erow), h
            break
    if not ev:
        return {"status": "game_not_on_novig"}
    e, erow = ev
    cands = []
    for mk in mks_by_event.get(e["eventId"], []):
        if N_MKT.get((mk.get("marketType") or "").upper()) != mtype or mk.get("status") != "OPEN":
            continue
        outs = mk.get("outcomes") or []
        if len(outs) != 2:
            continue
        for i, o in enumerate(outs):
            name = o.get("name") or ""
            if mtype == "total":
                oside = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                ok = oside == side
            else:
                t = lm.team_side(name, erow["teams"], al["sport"])
                ok = t is not None and (t == side if how == "same" else t == 1 - side)
            if ok:
                cands.append((mk, i, outcome_line(mtype, name, mk.get("strike"), i, erow["teams"])))
    if not cands:
        return {"status": "market_not_on_novig"}
    # exact alert line first; otherwise the nearest line (reported, flagged exact_line=false)
    if line is None:
        pick = cands[0]
    else:
        pick = min(cands, key=lambda c: abs((c[2] if c[2] is not None else 1e9) - line))
    mk, i, nline = pick
    book = lm.get(f"{lm.NOVIG}/v3/public/catalog/markets/{mk['marketId']}/book", {"depth": 20})
    outs = mk["outcomes"]
    mine, other = outs[i]["outcomeId"], outs[1 - i]["outcomeId"]
    orders = book.get("orders") or {}
    # buying my side = taking resting bids on the other outcome at (1 - p)
    asks = {}
    for r in orders.get(other, []):
        c = round(1 - float(r["price"]), 4)
        asks[c] = asks.get(c, 0) + int(r["qty"])
    # Novig: 1 contract pays 1c, so dollars = price x contracts / 100
    ask_levels = [{"price": c, "american": lm.american(c), "contracts": q, "dollars": round(c * q / 100)}
                  for c, q in sorted(asks.items())]
    bids_mine = sum(float(r["price"]) * int(r["qty"]) / 100 for r in orders.get(mine, []))
    alert_prob = am_to_prob(price) if price is not None else None
    # compare in American odds as displayed (higher = better for the bettor), so -108 on Novig (52.0c) counts as -108
    at_or_better = sum(lv["dollars"] for lv in ask_levels
                       if price is not None and lv["american"] is not None and lv["american"] >= price)
    best = ask_levels[0] if ask_levels else None
    return {
        "status": "ok",
        "market_id": mk["marketId"], "novig_label": outs[i].get("name"), "novig_line": nline,
        "alert_line": line, "exact_line": (line is None) or (nline is not None and abs(nline - line) < 1e-9),
        "alert_price": price, "alert_price_prob": round(alert_prob, 4) if alert_prob else None,
        "best_price": best["price"] if best else None, "best_price_american": best["american"] if best else None,
        "dollars_at_best": best["dollars"] if best else 0,
        "dollars_at_alert_price_or_better": round(at_or_better),
        "buy_levels": ask_levels[:10],
        "resting_bids_on_this_side_dollars": round(bids_mine),
    }


def run():
    t0 = time.time()
    n = datetime.now(timezone.utc)
    try:
        with open(SHARP_FILE) as f:
            sharp = json.load(f)
    except Exception as ex:
        print(f"Cannot read {SHARP_FILE}: {ex}")
        return
    todo = []
    for al in sharp.get("all_alerts") or []:
        if not al.get("pushed_to_phone") or al.get("repeat"):
            continue
        if (al.get("minutes_before_start") or 0) < MIN_LEAD_MIN:
            continue
        try:
            st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
            sent = datetime.strptime(al["sent_et"], "%Y-%m-%d %H:%M").replace(tzinfo=lm.ET)
        except Exception:
            continue
        if st <= n or sent < n - timedelta(hours=LOOKBACK_H):
            continue
        todo.append((st, al))
    prev = {}
    try:
        with open(OUT_FILE) as f:
            for c in json.load(f).get("checks", []):
                prev[c["alert_key"]] = c
    except Exception:
        pass
    checks = []
    if todo:
        lo = int(n.timestamp() * 1000)
        hi = int(max(st for st, _ in todo).timestamp() * 1000) + 1
        try:
            evs, mks = novig_catalog(lo, hi)
        except Exception as ex:
            print(f"Novig catalog failed: {ex}")
            evs, mks = [], []
        evs_by = {e["eventId"]: e for e in evs}
        mks_by_event = {}
        for mk in mks:
            mks_by_event.setdefault(mk.get("eventId"), []).append(mk)
        for st, al in sorted(todo, key=lambda x: x[0]):
            key = f"{al['sent_et']}|{al['game']}|{al['bet']}"
            try:
                res = check_alert(al, evs_by, mks_by_event)
            except Exception as ex:
                res = {"status": f"error: {ex}"}
            tms = lm.split_teams(al["game"])
            mt, sd, ln, pr = parse_bet(al["bet"], tms, al.get("sport")) if tms else (None, None, None, None)
            extra = {}
            for bname, fn in (("prophetx", px_check), ("kalshi", kalshi_check), ("polymarket", pm_check)):
                try:
                    extra[bname] = fn(al, mt, sd, ln, pr, tms) if (mt and sd is not None) else {"status": "bet_not_mapped"}
                except Exception as ex:
                    extra[bname] = {"status": f"error: {str(ex)[:120]}"}
            pres = extra["prophetx"]
            old = (prev.get(key) or {}).get("hardrock_latest")
            if old and old.get("checked_utc") and (n - datetime.fromisoformat(old["checked_utc"].replace("Z", "+00:00"))
                                                   ).total_seconds() < HR_REFRESH_MIN * 60:
                extra["hardrock"] = old   # reuse: saves Odds API credits
            else:
                try:
                    extra["hardrock"] = dict(hr_check(al, mt, sd, ln, pr, tms) if (mt and sd is not None)
                                             else {"status": "bet_not_mapped"}, checked_utc=n.strftime("%Y-%m-%dT%H:%M:%SZ"))
                except Exception as ex:
                    extra["hardrock"] = {"status": f"error: {str(ex)[:120]}", "checked_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ")}
            now_iso = n.strftime("%Y-%m-%dT%H:%M:%SZ")
            entry = {"alert_key": key, "sent_et": al["sent_et"], "sport": al["sport"], "game": al["game"],
                     "bet": al["bet"], "alert_book": al.get("book"), "grade": al.get("grade"), "start_utc": al["start_utc"],
                     "lead_min_now": round((st - n).total_seconds() / 60), "book": "novig", "checked_utc": now_iso,
                     "latest": res, "first": (prev.get(key) or {}).get("first") or dict(res, checked_utc=now_iso),
                     "prophetx_latest": pres,
                     "prophetx_first": (prev.get(key) or {}).get("prophetx_first") or dict(pres, checked_utc=now_iso)}
            for bname in ("kalshi", "polymarket", "hardrock"):
                entry[f"{bname}_latest"] = extra[bname]
                entry[f"{bname}_first"] = (prev.get(key) or {}).get(f"{bname}_first") or dict(extra[bname], checked_utc=now_iso)
            # best gettable price across all four books right now (American, higher = better for you)
            allb = {"novig": res, **extra}
            okb = {b: r_ for b, r_ in allb.items() if b != "hardrock" and r_.get("status") == "ok"
                   and r_.get("best_price_american") is not None}
            if okb:
                bb = max(okb, key=lambda b: okb[b]["best_price_american"])
                entry["best_now"] = {"book": bb, "american": okb[bb]["best_price_american"],
                                     "line": okb[bb].get("line", okb[bb].get("novig_line", okb[bb].get("prophetx_line"))),
                                     "exact_line": okb[bb].get("exact_line"),
                                     "dollars_at_alert_price_or_better_all_books":
                                         sum(r_.get("dollars_at_alert_price_or_better") or 0 for r_ in okb.values()
                                             if r_.get("exact_line"))}
            hr = extra.get("hardrock") or {}
            if hr.get("status") == "ok" and hr.get("exact_line") and hr.get("price_american") is not None:
                if "best_now" not in entry or hr["price_american"] > entry["best_now"]["american"]:
                    entry["best_now"] = dict(entry.get("best_now") or {}, book="hardrock", american=hr["price_american"],
                                             line=hr.get("line"), exact_line=True)
            checks.append(entry)
            print(f"{al['sport']} {al['game']} | {al['bet']} -> {res.get('status')}"
                  + (f" | best {res.get('best_price_american')} (${res.get('dollars_at_best')}), "
                     f"${res.get('dollars_at_alert_price_or_better')} at alert price or better, line {res.get('novig_line')}"
                     f"{'' if res.get('exact_line') else ' (NOT exact)'}" if res.get("status") == "ok" else "")
                  + f" || ProphetX -> {pres.get('status')}"
                  + (f" | best {pres.get('best_price_american')} (${pres.get('dollars_at_best')}), "
                     f"${pres.get('dollars_at_alert_price_or_better')} at alert price or better, line {pres.get('prophetx_line')}"
                     f"{'' if pres.get('exact_line') else ' (NOT exact)'}" if pres.get("status") == "ok" else "")
                  + "".join(f" || {b.title()} -> {extra[b].get('status')}"
                            + (f" | best {extra[b].get('best_price_american')} (${extra[b].get('dollars_at_best')}), "
                               f"${extra[b].get('dollars_at_alert_price_or_better')} at alert price or better, line {extra[b].get('line')}"
                               f"{'' if extra[b].get('exact_line') else ' (NOT exact)'}" if extra[b].get("status") == "ok" else "")
                            for b in ("kalshi", "polymarket"))
                  + (f" || Hard Rock -> {extra['hardrock'].get('status')}"
                     + (f" | {extra['hardrock'].get('price_american')} at {extra['hardrock'].get('line')}"
                        f"{'' if extra['hardrock'].get('exact_line') else ' (NOT exact)'}"
                        if extra['hardrock'].get('status') == 'ok' else "")))
    # keep finished checks for 2 days so the record survives the game start
    keep_after = (n - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = [c for k, c in prev.items() if k not in {c["alert_key"] for c in checks} and c.get("start_utc", "") >= keep_after]
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump({"note": ("Exchange book check (FLAG ONLY) for sharp-monitor phone alerts with 2h+ lead. latest/first = "
                            "Novig (public order books, no key); prophetx_latest/prophetx_first = ProphetX (read-only key; prices are AFTER its "
                            "2%% fee on winnings, displayed price kept as best_price_american_displayed): "
                            "best_price_american, dollars_at_best and dollars_at_alert_price_or_better = amount you could bet "
                            "at the alert price or better, buy_levels = the ladder. kalshi_latest/_first and polymarket_latest/_first: "
                            "same fields (public books, no key), prices AFTER taker fees (Kalshi 0.07, Polymarket global 0.03 x P x (1-P) per contract unless gamma marks the market zero-fee; "
                            "displayed price kept as best_price_american_displayed). Novig pregame: no fee. hardrock_latest/_first: Hard Rock sportsbook price and line via The Odds API "
                            "(no order book; refreshed every 30 min). best_now = best gettable price across the books, plus total "
                            "dollars at the alert price or better on books with the exact line. Novig fields: best_price = cheapest cost to BUY the alert side now (0-1, with American); "
                            "dollars_at_alert_price_or_better = dollars you could buy at the alert's price or better on the "
                            "same line; exact_line=false means Novig had no market at the alert's line and the nearest "
                            "line is shown. resting_bids_on_this_side_dollars = others bidding the same side. 'first' = first "
                            "check after the alert, 'latest' = this run. Novig orders are bids (verified Oct 21)."),
                   "updated_utc": n.strftime("%Y-%m-%dT%H:%M:%SZ"), "checks": checks + done}, f, indent=1, sort_keys=True)
    print(f"Book check done: {len(checks)} live alerts checked, {len(done)} finished kept. {time.time() - t0:.0f}s")


if __name__ == "__main__":
    try:
        run()
    except Exception as ex:
        print(f"Run failed: {ex}")
        sys.exit(1)
