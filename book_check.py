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


def parse_bet(bet, teams):
    """'Oklahoma City Thunder -8.5 (-120)' -> ('spread', team_index, -8.5, -120); 'Under 221 (-111)' -> ('total', 'UNDER', 221, -111)."""
    m = re.search(r"\(([+-]\d+)\)\s*$", bet)
    price = int(m.group(1)) if m else None
    if bet.startswith(("Over", "Under")):
        mt = re.match(r"^(Over|Under) ([\d.]+)", bet)
        return "total", ("OVER" if bet.startswith("Over") else "UNDER"), float(mt.group(2)), price
    if " ML " in bet:
        team = bet.split(" ML ")[0]
        mp = re.search(r"ML ([+-]\d+)", bet)
        return "moneyline", lm.team_side(team, teams), None, int(mp.group(1)) if mp else price
    if re.search(r" (PL|RL) ", bet):
        return None, None, None, None   # puck/run lines: not mapped yet
    ms = re.match(r"^(.*?) ([+-]?\d+(?:\.\d+)?|PK) \(", bet)
    if not ms:
        return None, None, None, None
    line = 0.0 if ms.group(2) == "PK" else float(ms.group(2))
    return "spread", lm.team_side(ms.group(1), teams), line, price


# ---------------------------------------------------------------- ProphetX (read-only)
PX_BASE = os.environ.get("PX_BASE", "") or "https://cash.api.prophetx.co/partner"
PX_ACCESS = os.environ.get("PROPHETX_ACCESS_KEY", "")
PX_SECRET = os.environ.get("PROPHETX_SECRET_KEY", "")
PX_TOURNAMENTS = {"NHL": 234, "NFL": 31, "NCAAF": 27653, "NBA": 132}
_PX = {"token": None, "events": {}, "markets": {}, "logged_shape": False}


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
        for levels in mk.get("selections") or []:
            if not levels:
                continue
            first = levels[0]
            name = first.get("name") or first.get("display_name") or ""
            if mtype == "total":
                oside = "OVER" if "over" in name.lower() else ("UNDER" if "under" in name.lower() else None)
                ok = oside == side
            else:
                t = lm.team_side(name, erow["teams"])
                ok = t is not None and (t == side if how == "same" else t == 1 - side)
            if not ok:
                continue
            lvl_line = lm.num(first.get("strike"))
            if mtype == "spread" and not lvl_line:
                lvl_line = lm.num(mk.get("strike"))
            if mtype == "total" and not lvl_line:
                lvl_line = lm.num(mk.get("strike"))
            if not _PX["logged_shape"] and mtype in ("spread", "total"):
                _PX["logged_shape"] = True
                print(f"  ProphetX {mtype} sample: market strike {mk.get('strike')} | level: "
                      f"{json.dumps({k: first.get(k) for k in ('name', 'display_name', 'price', 'strike', 'quantity', 'value')})}")
            cands.append((mk, levels, lvl_line if mtype != "moneyline" else None))
    if not cands:
        return {"status": "market_not_on_prophetx"}
    if line is None:
        mk, levels, pline = cands[0]
    else:
        mk, levels, pline = min(cands, key=lambda c: abs((c[2] if c[2] is not None else 1e9) - line))
    lv = sorted(({"american": int(x["price"]), "dollars": round(float(x.get("value") or 0)),
                  "to_win": round(float(x.get("quantity") or 0))} for x in levels if x.get("price") is not None),
                key=lambda x: -x["american"])   # best price first (higher American = better for the bettor)
    best = lv[0] if lv else None
    at_or_better = sum(x["dollars"] for x in lv if price is not None and x["american"] >= price)
    return {"status": "ok", "market_name": mk.get("name"), "prophetx_line": pline, "alert_line": line,
            "exact_line": (line is None) or (pline is not None and abs(pline - line) < 1e-9),
            "alert_price": price, "best_price_american": best["american"] if best else None,
            "dollars_at_best": best["dollars"] if best else 0,
            "dollars_at_alert_price_or_better": round(at_or_better), "buy_levels": lv[:10]}


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
    mtype, side, line, price = parse_bet(al["bet"], teams)
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
                t = lm.team_side(name, erow["teams"])
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
    ask_levels = [{"price": c, "american": lm.american(c), "contracts": q, "dollars": round(c * q)}
                  for c, q in sorted(asks.items())]
    bids_mine = sum(float(r["price"]) * int(r["qty"]) for r in orders.get(mine, []))
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
            try:
                tms = lm.split_teams(al["game"])
                mt, sd, ln, pr = parse_bet(al["bet"], tms) if tms else (None, None, None, None)
                pres = px_check(al, mt, sd, ln, pr, tms) if (mt and sd is not None) else {"status": "bet_not_mapped"}
            except Exception as ex:
                pres = {"status": f"error: {str(ex)[:120]}"}
            now_iso = n.strftime("%Y-%m-%dT%H:%M:%SZ")
            entry = {"alert_key": key, "sent_et": al["sent_et"], "sport": al["sport"], "game": al["game"],
                     "bet": al["bet"], "alert_book": al.get("book"), "grade": al.get("grade"), "start_utc": al["start_utc"],
                     "lead_min_now": round((st - n).total_seconds() / 60), "book": "novig", "checked_utc": now_iso,
                     "latest": res, "first": (prev.get(key) or {}).get("first") or dict(res, checked_utc=now_iso),
                     "prophetx_latest": pres,
                     "prophetx_first": (prev.get(key) or {}).get("prophetx_first") or dict(pres, checked_utc=now_iso)}
            checks.append(entry)
            print(f"{al['sport']} {al['game']} | {al['bet']} -> {res.get('status')}"
                  + (f" | best {res.get('best_price_american')} (${res.get('dollars_at_best')}), "
                     f"${res.get('dollars_at_alert_price_or_better')} at alert price or better, line {res.get('novig_line')}"
                     f"{'' if res.get('exact_line') else ' (NOT exact)'}" if res.get("status") == "ok" else "")
                  + f" || ProphetX -> {pres.get('status')}"
                  + (f" | best {pres.get('best_price_american')} (${pres.get('dollars_at_best')}), "
                     f"${pres.get('dollars_at_alert_price_or_better')} at alert price or better, line {pres.get('prophetx_line')}"
                     f"{'' if pres.get('exact_line') else ' (NOT exact)'}" if pres.get("status") == "ok" else ""))
    # keep finished checks for 2 days so the record survives the game start
    keep_after = (n - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = [c for k, c in prev.items() if k not in {c["alert_key"] for c in checks} and c.get("start_utc", "") >= keep_after]
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump({"note": ("Exchange book check (FLAG ONLY) for sharp-monitor phone alerts with 2h+ lead. latest/first = "
                            "Novig (public order books, no key); prophetx_latest/prophetx_first = ProphetX (read-only key): "
                            "best_price_american, dollars_at_best and dollars_at_alert_price_or_better = amount you could bet "
                            "at the alert price or better, buy_levels = the ladder. Novig fields: best_price = cheapest cost to BUY the alert side now (0-1, with American); "
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
