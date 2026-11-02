#!/usr/bin/env python3
"""
NBA TOTALS OWN-NUMBER MODEL - PAPER ONLY (spec #1; Peter yes Nov 2, 2026; Muse registrations Nov 2).

Never places orders, never alerts, never touches alerts.json / the executor / lanes / board. Data lives on the
nba-model branch (nba_model.json). The Actions log prints counts only.

NUMBER PER GAME
  Team form: last 10 completed games from ESPN box scores. Possessions = FGA - OREB + TO + 0.44 x FTA (per team,
  averaged over both teams in a game). Pace = possessions per game; ORtg / DRtg = points scored / allowed per 100.
  Shrinkage: each team's pace, ORtg, DRtg = w x team + (1 - w) x league, w = gp / (gp + 10).
  Expected points A = pace x (ORtg_A + DRtg_B - league_rtg) / 100 (same for B); pace = average of the two teams.
  Number = A + B. No home edge, no injury adjustment (v1: flags only, none parsed yet).
POSTING (frozen, one per game): first run at or after tip - 6h. Pinnacle's total at that moment comes from the EV
  study's Pinnacle cache (no new credits); its age (now - Pinnacle last update) is logged. A post later than tip - 6h
  is kept and flagged late (lead logged).
SIGHTING: |number - Pinnacle total| >= 3.0. Side toward our number. Bands 3.0-3.9 / 4.0+.
GRADING
  Gate (primary): Pinnacle close CLV at the sighting line = no-vig close prob (sharp_monitor.close_prob, half points
  priced in) minus the implied prob of Pinnacle's own price at posting, in cents. Pushes count in CLV.
  Secondary: W/L/P at the sighting line, flat 1u at Pinnacle's posting price (pushes excluded from W/L).
  Calibration: MAE of our number vs the final total, and of Pinnacle's 6h line vs the final, on the same games.
  First read at 60 sightings. Stop if CLV <= 0 at 60, or our MAE is more than 1.0 worse than Pinnacle's.
DEVIATION FROM SPEC (labelled): v1 prices sightings at Pinnacle's posting price, not the best exchange price
  (exchange reads come in v1.1). The gate metric (Pinnacle close CLV) is unchanged in meaning.
"""
import json
import os
import statistics as st
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUT_DIR = os.environ.get("NBA_DIR", "") or "nba-model"
OUT = os.path.join(OUT_DIR, "nba_model.json")
EV = os.environ.get("EV_FILE", "") or "ev-study/ev_sightings.json"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
THRESH, FORM_N, SHRINK = 3.0, 10, 10.0
SEASON_FROM = datetime(2026, 10, 20, tzinfo=timezone.utc)
STARTED = "2026-11-02"   # forward only from the day it ships
ALIAS = {"LA Clippers": "Los Angeles Clippers"}   # ESPN name -> Odds API (Pinnacle) name


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pt(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None


def prob(a):
    a = float(a)
    return -a / (-a + 100) if a < 0 else 100 / (a + 100)


def scoreboard(day):
    d = get(f"{ESPN}/scoreboard?dates={day.strftime('%Y%m%d')}&limit=100")
    out = []
    for e in d.get("events") or []:
        c = (e.get("competitions") or [{}])[0]
        teams = {x.get("homeAway"): x for x in c.get("competitors") or []}
        if "home" not in teams or "away" not in teams:
            continue
        stt = (e.get("status") or {}).get("type") or {}
        out.append({"id": str(e["id"]), "start": e.get("date"), "home": teams["home"]["team"]["displayName"],
                    "away": teams["away"]["team"]["displayName"], "completed": bool(stt.get("completed")),
                    "state": stt.get("state"), "hs": teams["home"].get("score"), "as": teams["away"].get("score")})
    return out


def box(gid):
    """{team: {pts, poss}} from an ESPN summary box score, or None."""
    d = get(f"{ESPN}/summary?event={gid}")
    pts = {}
    for c in ((d.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []:
        pts[c["team"]["displayName"]] = float(c.get("score") or 0)
    raw = {}
    for t in (d.get("boxscore") or {}).get("teams") or []:
        name = t["team"]["displayName"]
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics") or []}

        def num(*keys):
            for k in keys:
                v = s.get(k)
                if v not in (None, ""):
                    try:
                        return float(str(v).split("-")[-1]) if "-" in str(v) and k.count("-") else float(v)
                    except ValueError:
                        pass
            return None
        fga = num("fieldGoalsMade-fieldGoalsAttempted")
        fta = num("freeThrowsMade-freeThrowsAttempted")
        orb = num("offensiveRebounds")
        tov = num("totalTurnovers", "turnovers")
        if None in (fga, fta, orb, tov):
            return None
        raw[name] = fga - orb + tov + 0.44 * fta
    if len(raw) != 2 or len(pts) != 2:
        return None
    poss = sum(raw.values()) / 2
    return {n: {"pts": pts[n], "opp": sum(pts.values()) - pts[n], "poss": poss} for n in raw}


def ratings(state):
    games = sorted(state["box"].items(), key=lambda kv: kv[1]["start"])
    by = {}
    for gid, g in games:
        for team, v in g["teams"].items():
            by.setdefault(team, []).append(v)
    allg = [v for vs in by.values() for v in vs]
    if not allg:
        return None
    lg_pace = st.mean(v["poss"] for v in allg)
    lg_rtg = 100 * sum(v["pts"] for v in allg) / sum(v["poss"] for v in allg)
    out = {"_lg": {"pace": lg_pace, "rtg": lg_rtg, "games": len(games)}}
    for team, vs in by.items():
        last = vs[-FORM_N:]
        gp = len(last)
        w = gp / (gp + SHRINK)
        pace = st.mean(v["poss"] for v in last)
        o = 100 * sum(v["pts"] for v in last) / sum(v["poss"] for v in last)
        dr = 100 * sum(v["opp"] for v in last) / sum(v["poss"] for v in last)
        out[team] = {"gp": gp, "pace": w * pace + (1 - w) * lg_pace, "ortg": w * o + (1 - w) * lg_rtg,
                     "drtg": w * dr + (1 - w) * lg_rtg}
    return out


def number(r, home, away):
    if home not in r or away not in r:
        return None
    lg = r["_lg"]["rtg"]
    pace = (r[home]["pace"] + r[away]["pace"]) / 2
    a = pace * (r[away]["ortg"] + r[home]["drtg"] - lg) / 100
    h = pace * (r[home]["ortg"] + r[away]["drtg"] - lg) / 100
    return round(a + h, 1)


def pin_lines():
    """{frozenset(team names): totals dict} from the EV study's Pinnacle cache (no new credits)."""
    try:
        doc = json.load(open(EV))
    except Exception:
        return {}
    out = {}
    for ev, v in (doc.get("pin_cache") or {}).items():
        teams = list(((v.get("spreads") or {}).get("outcomes") or {}).keys())
        tot = v.get("totals") or {}
        oc = tot.get("outcomes") or {}
        if len(teams) == 2 and "Over" in oc and "Under" in oc:
            out[frozenset(teams)] = {"line": oc["Over"][0], "over": oc["Over"][1], "under": oc["Under"][1],
                                     "upd": tot.get("upd"), "fetched": tot.get("fetched")}
    return out


def close_prob(side, line, pin):
    import sharp_monitor as sm
    return sm.close_prob({"kind": "tot", "side": side, "pt": line, "sport": "NBA"},
                         {"totals": {"Over": (pin["line"], pin["over"]), "Under": (pin["line"], pin["under"])}})


def main():
    now = datetime.now(timezone.utc)
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        state = json.load(open(OUT))
    except Exception:
        state = {"spec": "spec #1 NBA totals own-number model, paper, forward from " + STARTED, "box": {}, "games": {}}
    # 1. box scores for every completed game this season (cached by game id)
    day, fetched = SEASON_FROM.astimezone(ET).date(), 0
    while day <= now.astimezone(ET).date():
        try:
            for g in scoreboard(day):
                if g["completed"] and g["id"] not in state["box"]:
                    b = box(g["id"])
                    if b:
                        state["box"][g["id"]] = {"start": g["start"], "teams": b}
                        fetched += 1
        except Exception:
            pass
        day += timedelta(days=1)
    r = ratings(state)
    pins = pin_lines()
    # 2. today's and tomorrow's slate: post, close, grade
    posted = closed = graded = 0
    for dd in (0, 1, -1):
        try:
            slate = scoreboard((now + timedelta(days=dd)).astimezone(ET).date())
        except Exception:
            continue
        for g in slate:
            s0 = pt(g["start"])
            if not s0 or iso(s0)[:10] < STARTED:
                continue
            rec = state["games"].setdefault(g["id"], {"home": g["home"], "away": g["away"], "start": g["start"]})
            pin = pins.get(frozenset(ALIAS.get(n, n) for n in (g["home"], g["away"])))
            if "post" not in rec and now >= s0 - timedelta(hours=6) and now < s0 and r:
                num = number(r, g["home"], g["away"])
                if num is not None:
                    p = {"utc": iso(now), "lead_min": round((s0 - now).total_seconds() / 60), "number": num,
                         "late": (s0 - now) < timedelta(hours=5, minutes=40),
                         "gp": {"home": r[g["home"]]["gp"], "away": r[g["away"]]["gp"]}}
                    if pin:
                        p.update(pin_line=pin["line"], pin_over=pin["over"], pin_under=pin["under"],
                                 ref_age_s=round(now.timestamp() - pin["upd"]) if pin.get("upd") else None)
                        gap = num - pin["line"]
                        if abs(gap) >= THRESH:
                            side = "Over" if gap > 0 else "Under"
                            p["sighting"] = {"side": side, "line": pin["line"], "price": pin[side.lower()],
                                             "gap": round(gap, 1), "band": "4.0+" if abs(gap) >= 4 else "3.0-3.9"}
                    else:
                        p["pin_line"] = None   # no Pinnacle reference at posting: logged, never a sighting
                    rec["post"] = p
                    posted += 1
            if pin and now < s0 and pin.get("fetched") and pin["fetched"] <= s0.timestamp():
                rec["close"] = {"line": pin["line"], "over": pin["over"], "under": pin["under"],
                                "read_utc": iso(datetime.fromtimestamp(pin["fetched"], timezone.utc)),
                                "mins_before": round((s0.timestamp() - pin["fetched"]) / 60)}
                closed += 1
            if g["completed"] and "final" not in rec and g["hs"] is not None:
                rec["final"] = float(g["hs"]) + float(g["as"])
                graded += 1
    # 3. grades
    for rec in state["games"].values():
        p, c, fin = rec.get("post") or {}, rec.get("close"), rec.get("final")
        sg = p.get("sighting")
        if sg and c and "clv_c" not in sg:
            cp = close_prob(sg["side"], sg["line"], c)
            if cp is not None:
                sg["clv_c"] = round(100 * (cp - prob(sg["price"])), 2)
        if sg and fin is not None and "result" not in sg:
            d = (fin - sg["line"]) if sg["side"] == "Over" else (sg["line"] - fin)
            sg["result"] = "P" if abs(d) < 1e-9 else ("W" if d > 0 else "L")
            pr = float(sg["price"])
            sg["units"] = 0.0 if sg["result"] == "P" else ((100 / abs(pr) if pr < 0 else pr / 100) if sg["result"] == "W" else -1.0)
    state["ratings"] = r
    state["updated_utc"] = iso(now)
    state["summary"] = summary(state)
    json.dump(state, open(OUT, "w"), indent=1)
    if "--report" in sys.argv:
        print("\n".join(state["summary"]))
    print(f"NBA model: box scores +{fetched} (total {len(state['box'])}), posted {posted}, close reads {closed}, "
          f"finals {graded}, Pinnacle games in cache {len(pins)}")   # counts only


def summary(state):
    gs = [g for g in state["games"].values() if g.get("post")]
    sg = [g["post"]["sighting"] for g in gs if g["post"].get("sighting")]
    L = [f"NBA TOTALS MODEL (paper), forward from {STARTED}, updated {state.get('updated_utc')}",
         f"Games posted: {len(gs)} | with Pinnacle reference: {sum(1 for g in gs if g['post'].get('pin_line') is not None)} | "
         f"late posts: {sum(1 for g in gs if g['post'].get('late'))} | sightings: {len(sg)} (first read at 60)"]
    for lab, sel in (("ALL", lambda s: True), ("3.0-3.9", lambda s: s["band"] == "3.0-3.9"), ("4.0+", lambda s: s["band"] == "4.0+"),
                     ("Overs", lambda s: s["side"] == "Over"), ("Unders", lambda s: s["side"] == "Under")):
        S = [s for s in sg if sel(s)]
        clv = [s["clv_c"] for s in S if s.get("clv_c") is not None]
        wl = [s for s in S if s.get("result") in ("W", "L")]
        L.append(f"  {lab:<8} n {len(S)} | Pinnacle CLV {st.mean(clv):+.2f}c (n={len(clv)})" if clv else f"  {lab:<8} n {len(S)} | CLV -")
        L[-1] += f" | {sum(s['result'] == 'W' for s in wl)}-{sum(s['result'] == 'L' for s in wl)} {sum(s.get('units') or 0 for s in S):+.2f}u"
    both = [g for g in gs if g.get("final") is not None and g["post"].get("pin_line") is not None]
    if both:
        m = st.mean(abs(g["post"]["number"] - g["final"]) for g in both)
        pnl = st.mean(abs(g["post"]["pin_line"] - g["final"]) for g in both)
        L.append(f"Calibration (same {len(both)} games): our MAE {m:.2f} | Pinnacle 6h MAE {pnl:.2f} | gap {m - pnl:+.2f} (stop if > +1.0 at the read)")
    return L


if __name__ == "__main__":
    main()
