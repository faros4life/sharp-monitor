#!/usr/bin/env python3
"""
MODEL LAB (Nov 2, 2026; Peter 15:32: "see what model works"). HYPOTHESIS ONLY - no verdicts, no live use. One simple,
fixed-in-advance model per league, tested against Pinnacle's OPENER on every finished game since Oct 12 (the history
depth), graded on Pinnacle's CLOSE. Reads the shared history cache (hist_cache.py); downloads only what is missing.

MODELS (current-season scores only, from ESPN; ratings use only games on EARLIER dates - no look-ahead):
  NFL / NCAAF: offense / defense points ratings with home edge, solved by iterative averaging and shrunk toward the
    league mean (k = 3 games). Predicts home margin and total. Cover / over chances from a normal curve
    (SD: NFL margin 13.5, total 13.0; NCAAF margin 16.0, total 16.0).
  NHL: offense / defense goal rates with home edge (k = 10 games); Poisson goals -> P(over) for the total and P(win)
    for the moneyline (regulation ties split 50/50 for OT / shootout).
  NBA: no model (v1 is stopped). Peter 15:33: "NBA unders are a play - it's what got me limited at Hard Rock". So NBA runs
    the MARKET-DRIFT baseline instead: EVERY game's total, Under and (for contrast) Over, at the OPEN, graded on the close -
    at Pinnacle's price, the best exchange after fees, and Hard Rock's own open price. Tests whether NBA totals open too
    high this season (the drift found in backtest #1/#2), with no model at all.
SIGHTING: model chance for a side minus Pinnacle's no-vig chance at the OPEN (first tick + 1 min, main line = largest
  limit) >= EDGE (4 pts registered here; 2 and 6 shown). Markets: total, spread (football; NBA), moneyline (NHL).
GRADE: CLV % = Pinnacle no-vig close at that line x decimal - 1, at (a) Pinnacle's own open price and (b) the best
  after-fee exchange price at the open (Novig 0, ProphetX 2% of winnings, Kalshi 0.07, PM US 0.0695 x P x (1-P)).
  FIT = first half of game dates, CHECK = second half. Bar (house): >= 100, CLV > 0 and beat-close >= 53% in BOTH.
Private email; the log prints counts only.
"""
import json
import math
import os
import statistics as stt
import urllib.request
from datetime import date, datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import sharp_monitor as sm
import tracker_build as tb

ET = tb.ET
NOW = datetime.now(timezone.utc)
LO = os.environ.get("LAB_FROM", "") or "2026-10-12"
HI = os.environ.get("LAB_TO", "") or (NOW.astimezone(ET).date() - timedelta(days=1)).isoformat()
LEAGUES = [x.strip() for x in (os.environ.get("LAB_LEAGUES", "") or "NFL,NCAAF,NHL,NBA").split(",") if x.strip()]
EDGES = (2.0, 4.0, 6.0)
EDGE_REG = 4.0
ESPN = {"NFL": ("football/nfl", "", date(2026, 9, 1)), "NCAAF": ("football/college-football", "&groups=80", date(2026, 8, 20)),
        "NHL": ("hockey/nhl", "", date(2026, 10, 1)), "NBA": ("basketball/nba", "", date(2026, 10, 18))}
SD = {"NFL": (13.5, 13.0), "NCAAF": (16.0, 16.0), "NBA": (12.0, 18.0)}
SHRINK = {"NFL": 3.0, "NCAAF": 3.0, "NHL": 10.0}
EXCH = {"novig.us": "Novig", "prophetx": "ProphetX", "kalshi": "Kalshi", "polymarket.us": "PM US"}
BOOKS = ["pinnacle"] + list(EXCH) + ["hardrockbet"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())


def espn_games(lg):
    path, extra, d0 = ESPN[lg]
    out, d = [], d0
    while d.isoformat() <= HI:
        try:
            js = get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={d.strftime('%Y%m%d')}&limit=400{extra}")
            for e in js.get("events") or []:
                c = (e.get("competitions") or [{}])[0]
                t = {x.get("homeAway"): x for x in c.get("competitors") or []}
                st = ((e.get("status") or {}).get("type") or {})
                if "home" in t and "away" in t and st.get("completed"):
                    out.append({"start": e.get("date"), "home": t["home"]["team"]["displayName"], "away": t["away"]["team"]["displayName"],
                                "hs": float(t["home"].get("score") or 0), "as": float(t["away"].get("score") or 0),
                                "neutral": bool(c.get("neutralSite"))})
        except Exception:
            pass
        d += timedelta(days=1)
    return out


def etd(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ET).date().isoformat()


def ratings(games, lg):
    """Offense / defense ratings (points or goals per game vs league mean) + home edge, shrunk toward 0."""
    if len(games) < 20:
        return None
    mu = stt.mean([g["hs"] for g in games] + [g["as"] for g in games])
    hfa = stt.mean(g["hs"] - g["as"] for g in games if not g["neutral"]) / 2 if any(not g["neutral"] for g in games) else 0
    teams = {t for g in games for t in (g["home"], g["away"])}
    o, d = {t: 0.0 for t in teams}, {t: 0.0 for t in teams}
    k = SHRINK[lg]
    for _ in range(25):
        so, sd_, n = {t: 0.0 for t in teams}, {t: 0.0 for t in teams}, {t: 0 for t in teams}
        for g in games:
            h = 0 if g["neutral"] else hfa
            # home scored hs = mu + o[home] + d[away] + h ; away scored as = mu + o[away] + d[home] - h
            so[g["home"]] += g["hs"] - mu - d[g["away"]] - h
            so[g["away"]] += g["as"] - mu - d[g["home"]] + h
            sd_[g["away"]] += g["hs"] - mu - o[g["home"]] - h
            sd_[g["home"]] += g["as"] - mu - o[g["away"]] + h
            n[g["home"]] += 1
            n[g["away"]] += 1
        o = {t: so[t] / (n[t] + k) for t in teams}
        d = {t: sd_[t] / (n[t] + k) for t in teams}
    return {"mu": mu, "hfa": hfa, "o": o, "d": d}


def predict(r, g):
    h = 0 if g["neutral"] else r["hfa"]
    eh = r["mu"] + r["o"].get(g["home"], 0) + r["d"].get(g["away"], 0) + h
    ea = r["mu"] + r["o"].get(g["away"], 0) + r["d"].get(g["home"], 0) - h
    return max(eh, 0.1), max(ea, 0.1)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def pois(lam, k):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def nhl_probs(lh, la):
    ph = [pois(lh, i) for i in range(15)]
    pa = [pois(la, i) for i in range(15)]
    win = sum(ph[i] * pa[j] for i in range(15) for j in range(15) if i > j)
    tie = sum(ph[i] * pa[i] for i in range(15))
    dist = {}
    for i in range(15):
        for j in range(15):
            dist[i + j] = dist.get(i + j, 0) + ph[i] * pa[j]
    return win + tie / 2, dist


def cands(pm, mkmap, sid, typ, when):
    out = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        nmo = {v: k for k, v in outs.items()}
        a, b = (nmo.get("Over"), nmo.get("Under")) if typ == "totals" else (nmo.get("1"), nmo.get("2"))
        tw = cl.two_way(pm, mid, when)
        if a not in tw or b not in tw or when - min(tw[a][1], tw[b][1]) > timedelta(hours=24):
            continue
        out.append({"mid": mid, "line": hcap, "a": a, "b": b, "da": tw[a][0], "db": tw[b][0], "pa": cl.novig_p(tw[a][0], tw[b][0]),
                    "lim": min(tw[a][2], tw[b][2])})
    return out


def main_of(c):
    return max(c, key=lambda x: (x["lim"], -abs(x["pa"] - 0.5))) if c else None


def close_p(c, typ, line, side_a, lg):
    """No-vig close chance for side A ('Over' / team 1) or B at that line."""
    ex_ = next((x for x in c if abs(x["line"] - line) < 1e-9), None)
    if ex_:
        return ex_["pa"] if side_a else 1 - ex_["pa"]
    if typ == "moneyline" or (typ == "spreads" and lg == "NHL"):
        return None
    m = main_of(c)
    if not m or abs(m["line"] - line) > (6 if typ == "totals" else 4.5):
        return None
    p = m["pa"] if side_a else 1 - m["pa"]
    if typ == "totals":
        v = sm.half_point_value(lg, "tot", m["line"], line, m["line"])
        better = (line < m["line"]) if side_a else (line > m["line"])
    else:   # spreads: line is team 1's handicap; side B holds -line
        mine, want = (m["line"], line) if side_a else (-m["line"], -line)
        v = sm.half_point_value(lg, "spr", mine, want, mine)
        better = want > mine
    return min(max(p + (v if better else -v), .01), .99)


def ex_best(hist, mkmap, mid, oid, t):
    """Best after-fee exchange decimal on that outcome at time t (last tick <= t under 24 h old) -> (dec, book)."""
    best = None
    for bk in EXCH:
        m = (cl.book_markets(hist, bk) or {}).get(mid) or {}
        lt = cl.last_tick((((m.get("outcomes") or {}).get(oid) or {}).get("players") or {}).get("0"), t)
        if lt and tb.num(lt[1].get("price")) and t - lt[0] <= timedelta(hours=24):
            dec = el.eff(bk, float(lt[1]["price"]))
            if best is None or dec > best[0]:
                best = (dec, EXCH[bk])
    return best


def first_tick(pm, mkmap, sid):
    ts = []
    for mid, (s, t, _, _) in mkmap.items():
        if s == sid and mid in pm and t in ("totals", "spreads", "moneyline"):
            for o in (pm[mid].get("outcomes") or {}).values():
                for x in (o.get("players") or {}).get("0") or []:
                    c = cl.tp(x.get("createdAt"))
                    if c:
                        ts.append(c)
    return min(ts) if ts else None


def run_league(lg, mkmap, st, sigs, why):
    sid = cl.SPORT[lg]
    games = espn_games(lg)
    cl.refresh_fixtures(st, NOW, lg, (datetime.fromisoformat(LO) - timedelta(days=1)).astimezone(ET),
                        (datetime.fromisoformat(HI) + timedelta(days=2)).astimezone(ET))
    fx = {k: v for k, v in (st.get("fixtures") or {}).items() if v.get("lg") == lg}
    graded = [g for g in games if LO <= etd(g["start"]) <= HI]
    why[lg] = {"espn games": len(games), "in window": len(graded)}
    for g in sorted(graded, key=lambda x: x["start"]):
        prior = [x for x in games if etd(x["start"]) < etd(g["start"])]
        r = ratings(prior, lg) if lg != "NBA" else {"drift": True}
        if not r:
            why[lg]["too early"] = why[lg].get("too early", 0) + 1
            continue
        s0 = datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
        words = tb.toks(g["home"]) | tb.toks(g["away"])
        fid = next((k for k, f in fx.items() if cl.tp(f.get("start")) and abs((cl.tp(f["start"]) - s0).total_seconds()) <= 6 * 3600
                    and tb.toks(f["p1"]) & tb.toks(g["home"]) and tb.toks(f["p2"]) & tb.toks(g["away"])
                    or (cl.tp(f.get("start")) and abs((cl.tp(f["start"]) - s0).total_seconds()) <= 6 * 3600
                        and tb.toks(f["p1"]) & tb.toks(g["away"]) and tb.toks(f["p2"]) & tb.toks(g["home"]))), None)
        if not fid:
            why[lg]["no fixture"] = why[lg].get("no fixture", 0) + 1
            continue
        f = fx[fid]
        home_is_1 = bool(tb.toks(f["p1"]) & tb.toks(g["home"]))
        hist = hc.get_hist(fid, BOOKS, s0)
        if isinstance(hist, dict) and hist.get("_error"):
            why[lg]["history error"] = why[lg].get("history error", 0) + 1
            continue
        pm = cl.book_markets(hist, "pinnacle")
        ft = first_tick(pm, mkmap, sid)
        if not ft:
            why[lg]["no Pinnacle history"] = why[lg].get("no Pinnacle history", 0) + 1
            continue
        t_open = min(ft + timedelta(minutes=1), s0)
        if lg == "NBA":   # market-drift baseline: every game, both sides of the total at the open
            co, cc = cands(pm, mkmap, sid, "totals", t_open), cands(pm, mkmap, sid, "totals", s0)
            m = main_of(co)
            if not m or not cc:
                continue
            hr = (cl.book_markets(hist, "hardrockbet") or {}).get(m["mid"]) or {}
            for side_a in (True, False):
                pc = close_p(cc, "totals", m["line"], side_a, lg)
                dec = m["da"] if side_a else m["db"]
                oid = m["a"] if side_a else m["b"]
                exb = ex_best(hist, mkmap, m["mid"], oid, t_open)
                lt = cl.last_tick((((hr.get("outcomes") or {}).get(oid) or {}).get("players") or {}).get("0"), t_open)
                hrd = float(lt[1]["price"]) if lt and tb.num(lt[1].get("price")) and t_open - lt[0] <= timedelta(hours=24) else None
                dlt = (g["hs"] + g["as"] - m["line"]) * (1 if side_a else -1)
                res = "P" if abs(dlt) < 1e-9 else ("W" if dlt > 0 else "L")
                sigs.append({"lg": lg, "typ": "all-unders" if not side_a else "all-overs", "day": etd(g["start"]), "edge": 99.0,
                             "game": f"{g['away']} @ {g['home']}", "side": "Over" if side_a else "Under", "line": m["line"], "dec": dec,
                             "res": res, "clv": None if pc is None else round(100 * (pc * dec - 1), 2),
                             "clv_x": None if (pc is None or not exb) else round(100 * (pc * exb[0] - 1), 2),
                             "clv_hr": None if (pc is None or not hrd) else round(100 * (pc * hrd - 1), 2),
                             "move": None if pc is None else round(100 * (pc - (m["pa"] if side_a else 1 - m["pa"])), 2),
                             "u": 0.0 if res == "P" else (dec - 1 if res == "W" else -1.0)})
            continue
        eh, ea = predict(r, g)
        day = etd(g["start"])
        final_m, final_t = g["hs"] - g["as"], g["hs"] + g["as"]
        for typ in (("totals", "moneyline") if lg == "NHL" else ("totals", "spreads")):
            co, cc = cands(pm, mkmap, sid, typ, t_open), cands(pm, mkmap, sid, typ, s0)
            m = main_of(co)
            if not m or not cc:
                continue
            line = m["line"]
            if lg == "NHL":
                pwin, dist = nhl_probs(eh, ea)
                if typ == "totals":
                    p_a = sum(v for k, v in dist.items() if k > line) / max(1e-9, sum(v for k, v in dist.items() if abs(k - line) > 1e-9))
                else:
                    p_a = pwin if home_is_1 else 1 - pwin
            else:
                sdm, sdt = SD[lg]
                if typ == "totals":
                    p_a = 1 - phi((line - (eh + ea)) / sdt)
                else:
                    margin1 = (eh - ea) if home_is_1 else (ea - eh)
                    p_a = phi((margin1 + line) / sdm)
            for side_a in (True, False):
                edge = 100 * ((p_a if side_a else 1 - p_a) - (m["pa"] if side_a else 1 - m["pa"]))
                if edge < min(EDGES):
                    continue
                pc = close_p(cc, typ, line, side_a, lg)
                dec = m["da"] if side_a else m["db"]
                exb = ex_best(hist, mkmap, m["mid"], m["a"] if side_a else m["b"], t_open)
                if typ == "totals":
                    dlt = (final_t - line) * (1 if side_a else -1)
                elif typ == "spreads":
                    m1 = final_m if home_is_1 else -final_m
                    dlt = (m1 + line) * (1 if side_a else -1)
                else:
                    m1 = final_m if home_is_1 else -final_m
                    dlt = m1 * (1 if side_a else -1)
                res = "P" if abs(dlt) < 1e-9 else ("W" if dlt > 0 else "L")
                sigs.append({"lg": lg, "typ": typ, "day": day, "edge": round(edge, 1), "game": f"{g['away']} @ {g['home']}",
                             "side": ("Over" if side_a else "Under") if typ == "totals" else ("team1" if side_a else "team2"),
                             "line": line, "dec": dec, "res": res,
                             "clv": None if pc is None else round(100 * (pc * dec - 1), 2),
                             "clv_x": None if (pc is None or not exb) else round(100 * (pc * exb[0] - 1), 2),
                             "xbook": exb[1] if exb else None,
                             "u": 0.0 if res == "P" else (dec - 1 if res == "W" else -1.0)})


def stats(S, key="clv"):
    c = [s[key] for s in S if s.get(key) is not None]
    if not c:
        return f"n {len(S)}"
    w, l_ = sum(s["res"] == "W" for s in S), sum(s["res"] == "L" for s in S)
    return (f"n {len(S)} | CLV {stt.mean(c):+.2f}% beat-close {sum(x > 0 for x in c)}/{len(c)} ({100 * sum(x > 0 for x in c) / len(c):.0f}%)"
            + (f" | {w}-{l_} {sum(s['u'] for s in S):+.2f}u" if key == "clv" else ""))


def passes(S, key):
    c = [s[key] for s in S if s.get(key) is not None]
    return len(c) >= 1 and stt.mean(c) > 0 and sum(x > 0 for x in c) / len(c) >= 0.53


def main():
    if not cl.KEY:
        print("model lab: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    mkmap = cl.load_markets(st, NOW)
    sigs, why = [], {}
    for lg in LEAGUES:
        if lg in ESPN and lg in cl.SPORT:
            try:
                run_league(lg, mkmap, st, sigs, why)
            except Exception as e:
                why.setdefault(lg, {})["crashed"] = type(e).__name__
    days = sorted({s["day"] for s in sigs})
    mid = days[(len(days) - 1) // 2] if days else ""
    L = [f"MODEL LAB - HYPOTHESIS ONLY | games {LO} to {HI} | opener vs model, graded on Pinnacle close | FIT <= {mid} < CHECK",
         "Models fixed in advance (see header of model_lab.py). Sighting = model chance - Pinnacle no-vig chance at the OPEN >= edge.",
         "CLV % = Pinnacle no-vig close at that line x decimal - 1; 'exch' = best after-fee exchange price at the open.", "",
         "Coverage: " + "; ".join(f"{k}: " + ", ".join(f"{a} {b}" for a, b in v.items()) for k, v in why.items()),
         f"History cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}", ""]
    for typ in ("all-unders", "all-overs"):
        S = [s for s in sigs if s["typ"] == typ]
        if S:
            F, C = [s for s in S if s["day"] <= mid], [s for s in S if s["day"] > mid]
            mv = [s["move"] for s in S if s.get("move") is not None]
            L += [f"NBA {typ.upper()} AT THE OPEN (no model; Peter's NBA-unders read):",
                  f"  Pinnacle price: {stats(S)} | avg no-vig move open->close {stt.mean(mv):+.2f} pts" if mv else f"  Pinnacle price: {stats(S)}",
                  f"  best exchange after fees: {stats(S, 'clv_x')}", f"  Hard Rock open price: {stats(S, 'clv_hr')}",
                  f"  FIT  {stats(F)} | exch {stats(F, 'clv_x')} | HR {stats(F, 'clv_hr')}",
                  f"  CHECK {stats(C)} | exch {stats(C, 'clv_x')} | HR {stats(C, 'clv_hr')}",
                  f"  bar (>= 100, CLV > 0, beat-close >= 53% both halves) at best exchange: "
                  + ("MEETS" if len(S) >= 100 and passes(F, "clv_x") and passes(C, "clv_x") else "no")
                  + f"; at Hard Rock: " + ("MEETS" if len(S) >= 100 and passes(F, "clv_hr") and passes(C, "clv_hr") else "no"), ""]
    for lg in LEAGUES:
        for typ in ("totals", "spreads", "moneyline"):
            S0 = [s for s in sigs if s["lg"] == lg and s["typ"] == typ]
            if not S0:
                continue
            L.append(f"{lg} {typ}:")
            for e in EDGES:
                S = [s for s in S0 if s["edge"] >= e]
                F, C = [s for s in S if s["day"] <= mid], [s for s in S if s["day"] > mid]
                tag = ""
                if e == EDGE_REG:
                    ok = len(S) >= 100 and passes(F, "clv") and passes(C, "clv")
                    okx = len(S) >= 100 and passes(F, "clv_x") and passes(C, "clv_x")
                    tag = f"  [bar at Pinnacle price: {'MEETS' if ok else 'no'}; at best exchange: {'MEETS' if okx else 'no'}]"
                L.append(f"  edge >= {e:g}: Pinnacle price {stats(S)}{tag}")
                L.append(f"      best exchange after fees: {stats(S, 'clv_x')}")
                if e == EDGE_REG:
                    L.append(f"      FIT  {stats(F)} | exch {stats(F, 'clv_x')}")
                    L.append(f"      CHECK {stats(C)} | exch {stats(C, 'clv_x')}")
    L += ["", f"Calls: {len(cl.CALLS)} (billable {cl.STATS['billable']})"]
    ex.send("Bets MODEL LAB (HYPOTHESIS)", "\n".join(L))
    print(f"model lab: sightings {len(sigs)}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
