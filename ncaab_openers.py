#!/usr/bin/env python3
"""
NCAAB OPENERS - PAPER FORWARD LANE (item 28; Muse registered Nov 2, 2026; Claude amendments 1-3 accepted; Peter yes
Nov 3 6:13 AM). PAPER ONLY: never places orders, never alerts, never touches alerts.json / the executor / lanes /
board. Data lives on the ncaab-openers branch (ncaab_openers.json, ncaab_prior.json). The Actions log prints counts only.

THIS FILE = v1 FREEZER (the time-critical part: a frozen number cannot be made after the fact).
  Number per game (full-game TOTAL only, amendment 2): pace x efficiency, as NBA spec #1.
    Possessions = FGA - OREB + TO + 0.475 x FTA (college FT factor), averaged over both teams in a game.
    Expected points A = pace x (ORtg_A + DRtg_B - D1_rtg) / 100; pace = mean of the two teams. No home edge (v1).
  Ratings: this season's ESPN box scores (all D1, groups=50), last 10 games per team, shrunk toward the team's
    PRESEASON PRIOR with w = gp / (gp + k), k = 10 (fixed before launch, amendment 3).
    Prior = last season's (2025-26) full-season pace / ORtg / DRtg from ESPN box scores, itself shrunk toward the D1
    mean with gp / (gp + 10). A team with no prior uses the D1 mean.
  Freeze (amendment 1): every scheduled D1 game gets ONE number, frozen at the first run that sees it on the schedule
    and before tip. on_time = frozen no later than 06:00 ET the day before tip (the registered rule); later freezes are
    kept and flagged late, with the freeze-to-tip lead logged. Games whose teams cannot be rated are logged "no number".
GRADER (v1.1, next): after each game, Pinnacle's opener (first totals tick + 1 min) and close, and the best after-fee
  exchange price at the open time, from OddsPapi's FREE history. Sighting = |frozen number - Pinnacle open| >= 3.0,
  bands 3.0-3.9 / 4.0+, side toward our number; freeze time, open time and their lag logged per sighting; a freeze
  after the open is never a sighting. Primary grade = Pinnacle no-vig close CLV at the sighting line (half points priced
  in); secondary = flat 1u at the best after-fee exchange price at the open. MAE vs Pinnacle's OPEN on all posted games.
  First read at 60 sightings. STOP if CLV <= 0 at 60 or MAE more than 1.0 point worse than the open. History is kept
  by OddsPapi, so the grader loses nothing by shipping after the freezer.
"""
import json
import os
import statistics as st
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUT_DIR = os.environ.get("NCAAB_DIR", "") or "ncaab-openers"
OUT = os.path.join(OUT_DIR, "ncaab_openers.json")
PRIOR = os.path.join(OUT_DIR, "ncaab_prior.json")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
FORM_N, K = 10, 10.0
SEASON_FROM = date(2026, 11, 2)          # 2026-27 season opening day
PRIOR_FROM, PRIOR_TO = date(2025, 11, 3), date(2026, 4, 7)   # 2025-26 season
STARTED = "2026-11-03"                   # forward only from the day it ships
AHEAD_DAYS = 2                           # freeze games on today's ET date and the next 2


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception:
            if i == tries - 1:
                raise
    return None


def iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None
    except Exception:
        return None


def scoreboard(day):
    d = get(f"{ESPN}/scoreboard?dates={day.strftime('%Y%m%d')}&groups=50&limit=500")
    out = []
    for e in (d or {}).get("events") or []:
        c = (e.get("competitions") or [{}])[0]
        teams = {x.get("homeAway"): x for x in c.get("competitors") or []}
        if "home" not in teams or "away" not in teams:
            continue
        stt = (e.get("status") or {}).get("type") or {}
        out.append({"id": str(e["id"]), "start": e.get("date"), "home": teams["home"]["team"].get("displayName"),
                    "away": teams["away"]["team"].get("displayName"), "neutral": bool(c.get("neutralSite")),
                    "completed": bool(stt.get("completed")), "state": stt.get("state"),
                    "hs": teams["home"].get("score"), "as": teams["away"].get("score")})
    return out


def _stat(s, *keys):
    for k in keys:
        v = s.get(k)
        if v in (None, ""):
            continue
        v = str(v)
        try:
            return float(v.split("-")[1]) if "-" in v and "-" in k else float(v)
        except (ValueError, IndexError):
            continue
    return None


def box(gid):
    """{team: {pts, opp, poss}} from an ESPN summary box score, or None."""
    try:
        d = get(f"{ESPN}/summary?event={gid}")
    except Exception:
        return None
    pts = {}
    for c in ((d.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []:
        try:
            pts[c["team"]["displayName"]] = float(c.get("score") or 0)
        except (KeyError, ValueError):
            pass
    raw = {}
    for t in (d.get("boxscore") or {}).get("teams") or []:
        name = (t.get("team") or {}).get("displayName")
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics") or []}
        fga = _stat(s, "fieldGoalsMade-fieldGoalsAttempted", "fieldGoalsAttempted")
        fta = _stat(s, "freeThrowsMade-freeThrowsAttempted", "freeThrowsAttempted")
        orb = _stat(s, "offensiveRebounds")
        tov = _stat(s, "totalTurnovers", "turnovers")
        if None in (fga, fta, orb, tov) or not name:
            return None
        raw[name] = fga - orb + tov + 0.475 * fta
    if len(raw) != 2 or len(pts) != 2 or set(raw) != set(pts):
        return None
    poss = sum(raw.values()) / 2
    if poss <= 0:
        return None
    return {n: {"pts": pts[n], "opp": sum(pts.values()) - pts[n], "poss": poss} for n in raw}


def collect(d0, d1, have):
    """Completed games between two ET dates -> {gid: {start, teams}} (new ones only), box scores fetched in parallel."""
    games, day = [], d0
    while day <= d1:
        try:
            games += [g for g in scoreboard(day) if g["completed"] and g["id"] not in have]
        except Exception:
            pass
        day += timedelta(days=1)
    out, fail = {}, 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for g, b in zip(games, pool.map(lambda g: box(g["id"]), games)):
            if b:
                out[g["id"]] = {"start": g["start"], "teams": b}
            else:
                fail += 1
    return out, len(games), fail


def team_ratings(boxes, last_n=None):
    by = {}
    for gid, g in sorted(boxes.items(), key=lambda kv: kv[1]["start"] or ""):
        for team, v in g["teams"].items():
            by.setdefault(team, []).append(v)
    allg = [v for vs in by.values() for v in vs]
    if not allg:
        return {}, None
    lg = {"pace": st.mean(v["poss"] for v in allg), "rtg": 100 * sum(v["pts"] for v in allg) / sum(v["poss"] for v in allg)}
    out = {}
    for team, vs in by.items():
        use = vs[-last_n:] if last_n else vs
        p = sum(v["poss"] for v in use)
        out[team] = {"gp": len(use), "pace": st.mean(v["poss"] for v in use),
                     "ortg": 100 * sum(v["pts"] for v in use) / p, "drtg": 100 * sum(v["opp"] for v in use) / p}
    return out, lg


def build_prior(prior):
    """Last season's ratings, shrunk toward the D1 mean (gp / (gp + K)). Built once, then kept."""
    if prior.get("teams"):
        return prior, 0, 0
    boxes, n, fail = collect(PRIOR_FROM, PRIOR_TO, set())
    raw, lg = team_ratings(boxes)
    teams = {}
    for t, r in raw.items():
        w = r["gp"] / (r["gp"] + K)
        teams[t] = {"gp": r["gp"], "pace": w * r["pace"] + (1 - w) * lg["pace"],
                    "ortg": w * r["ortg"] + (1 - w) * lg["rtg"], "drtg": w * r["drtg"] + (1 - w) * lg["rtg"]}
    return {"season": "2025-26", "built_utc": iso(datetime.now(timezone.utc)), "lg": lg, "games": len(boxes),
            "teams": teams}, n, fail


def ratings(state, prior):
    cur, lg_cur = team_ratings(state["box"], FORM_N)
    lg = prior.get("lg") or lg_cur
    if not lg:
        return None
    if lg_cur and state["box"] and len(state["box"]) >= 200:   # this season's D1 means once there is enough data
        lg = lg_cur
    pt_ = prior.get("teams") or {}
    out = {"_lg": lg}
    for team in set(cur) | set(pt_):
        base = pt_.get(team) or {"pace": lg["pace"], "ortg": lg["rtg"], "drtg": lg["rtg"]}
        c = cur.get(team)
        if c:
            w = c["gp"] / (c["gp"] + K)
            out[team] = {"gp": c["gp"], "prior": team in pt_, "pace": w * c["pace"] + (1 - w) * base["pace"],
                         "ortg": w * c["ortg"] + (1 - w) * base["ortg"], "drtg": w * c["drtg"] + (1 - w) * base["drtg"]}
        else:
            out[team] = {"gp": 0, "prior": team in pt_, "pace": base["pace"], "ortg": base["ortg"], "drtg": base["drtg"]}
    return out


def number(r, home, away):
    if not r or home not in r or away not in r:
        return None
    lg = r["_lg"]["rtg"]
    pace = (r[home]["pace"] + r[away]["pace"]) / 2
    a = pace * (r[away]["ortg"] + r[home]["drtg"] - lg) / 100
    h = pace * (r[home]["ortg"] + r[away]["drtg"] - lg) / 100
    return round(a + h, 1)


def main():
    now = datetime.now(timezone.utc)
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        state = json.load(open(OUT))
    except Exception:
        state = {}
    state.setdefault("v", 1)
    state.setdefault("box", {})
    state.setdefault("games", {})
    try:
        prior = json.load(open(PRIOR))
    except Exception:
        prior = {}
    prior, pn, pf = build_prior(prior)
    json.dump(prior, open(PRIOR, "w"))
    today = now.astimezone(ET).date()
    new, n, fail = collect(max(SEASON_FROM, today - timedelta(days=4)), today, set(state["box"]))
    state["box"].update(new)
    r = ratings(state, prior)
    frozen = late = nonum = 0
    for off in range(0, AHEAD_DAYS + 1):
        day = today + timedelta(days=off)
        try:
            sched = scoreboard(day)
        except Exception:
            continue
        for g in sched:
            if g["id"] in state["games"] or g["state"] != "pre":
                continue
            tip = pt(g["start"])
            if not tip or tip <= now:
                continue
            num = number(r, g["home"], g["away"])
            tip_day = tip.astimezone(ET).date()
            deadline = datetime.combine(tip_day - timedelta(days=1), datetime.min.time(), ET) + timedelta(hours=6)
            rec = {"home": g["home"], "away": g["away"], "start": g["start"], "neutral": g["neutral"],
                   "frozen_utc": iso(now), "lead_min": round((tip - now).total_seconds() / 60),
                   "on_time": now <= deadline, "number": num}
            if num is None:
                rec["why"] = "no rating for a team"
                nonum += 1
            else:
                rec["gp"] = {"home": r[g["home"]]["gp"], "away": r[g["away"]]["gp"]}
                rec["prior"] = {"home": r[g["home"]]["prior"], "away": r[g["away"]]["prior"]}
            state["games"][g["id"]] = rec
            frozen += 1
            late += 0 if rec["on_time"] else 1
    # finals for frozen games (calibration later): read from the scoreboard of the tip day
    finals, boards = 0, {}
    for gid, rec in state["games"].items():
        if rec.get("final") is not None:
            continue
        tip = pt(rec.get("start"))
        if not tip or tip > now - timedelta(hours=3) or tip < now - timedelta(days=5):
            continue
        d = tip.astimezone(ET).date()
        try:
            if d not in boards:
                boards[d] = {g["id"]: g for g in scoreboard(d)}
            g = boards[d].get(gid)
            if g and g["completed"]:
                rec["final"] = float(g["hs"]) + float(g["as"])
                finals += 1
        except Exception:
            pass
    state["updated_utc"] = iso(now)
    state["summary"] = {"frozen": len(state["games"]), "with_number": sum(1 for g in state["games"].values() if g.get("number") is not None),
                        "on_time": sum(1 for g in state["games"].values() if g.get("on_time")),
                        "finals": sum(1 for g in state["games"].values() if g.get("final") is not None),
                        "season_boxes": len(state["box"]), "prior_teams": len(prior.get("teams") or {})}
    json.dump(state, open(OUT, "w"))
    print(f"NCAAB openers: prior games {prior.get('games', 0)} (this run scanned {pn}, box failures {pf}); "
          f"season boxes +{len(new)} of {n} (failures {fail}), total {len(state['box'])}; "
          f"froze {frozen} (late {late}, no number {nonum}); finals +{finals}; total frozen {len(state['games'])}")   # counts only


if __name__ == "__main__":
    main()
