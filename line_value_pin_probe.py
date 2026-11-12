#!/usr/bin/env python3
"""BOUNDED PINNACLE REFERENCE DIAGNOSTIC (Nov 12, 2026). Exercises line_value_ref on LIVE data, once, on purpose.

WHY ITS OWN JOB. executor-dry-run is dispatched externally every ~10 minutes and its concurrency group drops queued
runs, so a manually dispatched flag on that workflow rarely executes. This job is separate, manual-only, and makes
AT MOST ONE Pinnacle read per league in today's alerts (PROBE_MAX_LEAGUES caps it).

WHAT IT DOES. For each distinct (league, game, market, side) in alerts.json: read Pinnacle once per league, build the
independent reference through line_value_ref (game/market/line/period/freshness/settlement checks), then run the
shared line_value.convert() for the alert line against the half-point and full-point neighbours, and report, as COUNTS
ONLY: how many references were usable, each failure reason by name, and the actual The Odds API credit usage.

It places no orders, imports no order code, sends no email, and writes nothing but a summary file.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import book_check as bc           # parse_bet only
import liquidity_monitor as lm    # split_teams / toks only (same helpers executor uses)
import line_value as lv
import line_value_ref as lvr

MAX_LEAGUES = int(os.environ.get("PROBE_MAX_LEAGUES") or 6)
PIN_SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba",
             "NCAAB": "basketball_ncaab", "NHL": "icehockey_nhl", "MLB": "baseball_mlb"}
USAGE = {}


def pin_read(sk, key):
    """One Odds API call for one league. Records the quota headers (counts only)."""
    import urllib.request
    url = (f"https://api.the-odds-api.com/v4/sports/{sk}/odds?bookmakers=pinnacle&markets=spreads,totals"
           f"&oddsFormat=american&dateFormat=iso&apiKey={key}")
    with urllib.request.urlopen(url, timeout=25) as resp:
        data = json.loads(resp.read().decode())
        USAGE.update({k: resp.headers.get(k) for k in ("x-requests-used", "x-requests-remaining", "x-requests-last")})
        USAGE["calls"] = USAGE.get("calls", 0) + 1
    return data


def pin_input(evs, lg, game, mtype, side, now):
    teams = lm.split_teams(game)
    if not teams:
        return {"why": "teams_not_parsed"}
    tt = [lm.toks(x, lg) for x in teams]
    hits = [e for e in evs if all(any(t & lm.toks(n, lg) for n in (e.get("home_team"), e.get("away_team"))) for t in tt)]
    if not hits:
        return {"why": "game_not_on_pinnacle"}
    if len(hits) > 1:
        return {"why": f"game_ambiguous:{len(hits)}"}
    ev = hits[0]
    bk = next((b for b in ev.get("bookmakers") or [] if b.get("key") == "pinnacle"), None)
    mk = next((m for m in (bk or {}).get("markets") or [] if m.get("key") == ("totals" if mtype == "total" else "spreads")), None)
    if not mk or len(mk.get("outcomes") or []) != 2:
        return {"why": "pinnacle_market_missing"}
    oc = mk["outcomes"]
    if mtype == "total":
        mine = next((o for o in oc if str(o.get("name", "")).upper() == str(side).upper()), None)
    else:
        mine = next((o for o in oc if lm.toks(o.get("name"), lg) & tt[side]), None)
    return {"market": {"outcomes": [{"name": o.get("name"), "point": o.get("point"), "price": o.get("price")} for o in oc],
                       "last_update": mk.get("last_update") or (bk or {}).get("last_update")},
            "mine": (mine or {}).get("name"), "book": "pinnacle",
            "read_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "commence_utc": ev.get("commence_time")}


def main():
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        print("probe: ODDS_API_KEY not set; nothing read.")
        return 0
    now = datetime.now(timezone.utc)
    try:
        alerts = (json.load(open("alerts.json")) or {}).get("alerts") or []
    except Exception as ex:
        print(f"probe: alerts.json unreadable ({str(ex)[:40]})")
        return 0
    seen, plays = set(), []
    for a in alerts:
        lg, game, bet = (a.get("league") or a.get("sport") or "").upper(), (a.get("game") or "").split(":")[0], a.get("bet") or ""
        if lg not in PIN_SPORT or not game or not bet:
            continue
        teams = lm.split_teams(game)
        mt, sd, ln, pr = bc.parse_bet(bet, teams, lg) if teams else (None, None, None, None)
        if mt not in ("spread", "total") or sd is None or ln is None or pr is None:
            continue
        k = (lg, game, mt, str(sd), ln)
        if k in seen:
            continue
        seen.add(k)
        plays.append({"lg": lg, "game": game, "mt": mt, "sd": sd, "ln": ln, "af": pr, "start": a.get("start_utc")})
    lgs = sorted({p["lg"] for p in plays})[:MAX_LEAGUES]
    evs_by = {}
    for lg in lgs:
        try:
            evs_by[lg] = pin_read(PIN_SPORT[lg], key)
        except Exception as ex:
            evs_by[lg] = None
            print(f"probe: {lg} read failed ({type(ex).__name__})")
    why, conv, detail = Counter(), Counter(), []
    for p in plays:
        if p["lg"] not in evs_by:
            why["league_not_probed(cap)"] += 1
            continue
        evs = evs_by[p["lg"]]
        if evs is None:
            why["pinnacle_read_failed"] += 1
            continue
        inp = pin_input(evs, p["lg"], p["game"], p["mt"], p["sd"], now)
        ref, rec = lvr.pinnacle_reference(inp, p["mt"], p["sd"], p["start"], now, p["lg"])
        why[rec["why"] or "ok"] += 1
        if ref is None:
            continue
        step = 0.5 if p["mt"] == "total" else 0.5
        for d in (-step, step, -2 * step, 2 * step):
            tgt = round(p["ln"] + d, 1)
            for book in ("novig", "prophetx", "kalshi", "polymarket_us"):
                cv = lv.convert(p["lg"], p["mt"], p["sd"], p["ln"], p["af"], tgt, None, book, 0, None, ref)
                conv[f"{cv['status']}:{cv.get('reason') or cv.get('method')}"] += 1
                if cv["status"] == "ok":
                    detail.append({"lg": p["lg"], "mt": p["mt"], "side": str(p["sd"]), "alert_line": p["ln"], "alert_af": p["af"],
                                   "target": tgt, "book": book, "method": cv["method"], "allowance": cv["allowance"],
                                   "max_af": round(cv["max_am_after_fee"], 1), "ref_line": ref.line, "ref_q": round(ref.q, 4),
                                   "ref_ts": ref.ts, "age_s": rec.get("age_s")})
    print(f"probe: {len(plays)} distinct alert markets, leagues probed {lgs} (cap {MAX_LEAGUES})")
    print("  reference outcome: " + ", ".join(f"{k} {v}" for k, v in sorted(why.items())))
    print("  conversions attempted: " + (", ".join(f"{k} {v}" for k, v in sorted(conv.items())) or "none"))
    print(f"  Pinnacle calls this run: {USAGE.get('calls', 0)}; The Odds API used {USAGE.get('x-requests-used')}, "
          f"remaining {USAGE.get('x-requests-remaining')}, last call cost {USAGE.get('x-requests-last')}")
    os.makedirs("summary", exist_ok=True)
    json.dump({"when": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "reference_outcome": dict(why), "conversions": dict(conv),
               "usage": USAGE, "supported": detail}, open("summary/line_value_pin_probe.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
