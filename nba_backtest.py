#!/usr/bin/env python3
"""
NBA TOTALS MODEL - SEASON BACKTEST (Nov 2, 2026; Peter yes 12:17 ET). Labelled HYPOTHESIS: the forward paper
record stays the test of record.

No look-ahead: each game's number uses only ESPN box scores of games played on EARLIER ET dates.
Pinnacle from OddsPapi free history (one billable /fixtures call for the window). For every game, Pinnacle's main
total (largest limit, ticks under 24 h old) at four times: OPEN (first totals tick), T-6h (the live model's post
time), T-2h, and CLOSE (tip).

Per timing, a SIGHTING = |our number - Pinnacle's main total| >= threshold (3.0 registered; 2.0 / 4.0 shown).
Bet = Pinnacle's own price on that side at that line, at that time. Graded:
  CLV %       = Pinnacle no-vig close chance at that line x decimal price - 1 (vig included; the gate).
  Move pts    = close no-vig chance - no-vig chance at bet time (did the market move our way; vig excluded).
  W/L, units  at the bet price vs the final score (secondary).
Close at that line = Pinnacle's own market at that number at tip, else main close line moved by half-point values.
Variants (fixed in advance, not tuned): REG (last 10 games, shrink 10 = the live model), S5, S20, SEASON (all games,
shrink 10). Split: FIT = games up to BT_SPLIT, CHECK = after. Also: calibration (MAE vs final) and "does the line
move toward us" (share of games where the open-to-close move had the sign of our open gap).
Read-only: private email; the log prints counts only.
"""
import json
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import nba_totals_model as nm
import sharp_monitor as sm
import tracker_build as tb

ET = tb.ET
NOW = datetime.now(timezone.utc)
LO = os.environ.get("BT_FROM", "") or "2026-10-21"   # Muse 12:19 registration: Oct 21 to present
HI = os.environ.get("BT_TO", "") or (NOW.astimezone(ET).date() - timedelta(days=1)).isoformat()
_nd = (datetime.fromisoformat(HI) - datetime.fromisoformat(LO)).days + 1
SPLIT = os.environ.get("BT_SPLIT", "") or (datetime.fromisoformat(LO) + timedelta(days=_nd // 2 - 1)).date().isoformat()   # FIT = first half by date
THRESH = (2.0, 3.0, 4.0)
VARIANTS = {"REG": (10, 10.0), "S5": (10, 5.0), "S20": (10, 20.0), "SEASON": (999, 10.0)}
TIMES = ("OPEN", "T-6h", "T-2h")
FRESH = timedelta(hours=24)


def etd(s):
    return nm.pt(s).astimezone(ET).date().isoformat()


def ratings_asof(boxes, day, n_form, shrink):
    """nba_totals_model.ratings() using only games on ET dates before the game day."""
    games = sorted(((g, v) for g, v in boxes.items() if etd(v["start"]) < day), key=lambda kv: kv[1]["start"])
    by = {}
    for _, g in games:
        for team, v in g["teams"].items():
            by.setdefault(team, []).append(v)
    allg = [v for vs in by.values() for v in vs]
    if len(allg) < 10:
        return None
    lg_pace = stt.mean(v["poss"] for v in allg)
    lg_rtg = 100 * sum(v["pts"] for v in allg) / sum(v["poss"] for v in allg)
    out = {"_lg": {"pace": lg_pace, "rtg": lg_rtg}}
    for team, vs in by.items():
        last = vs[-n_form:]
        gp = len(last)
        w = gp / (gp + shrink)
        o = 100 * sum(v["pts"] for v in last) / sum(v["poss"] for v in last)
        d = 100 * sum(v["opp"] for v in last) / sum(v["poss"] for v in last)
        out[team] = {"gp": gp, "pace": w * stt.mean(v["poss"] for v in last) + (1 - w) * lg_pace,
                     "ortg": w * o + (1 - w) * lg_rtg, "drtg": w * d + (1 - w) * lg_rtg}
    return out


def number(r, home, away):
    """Live model's number; a team with no games yet sits at league average."""
    lg = r["_lg"]
    z = {"gp": 0, "pace": lg["pace"], "ortg": lg["rtg"], "drtg": lg["rtg"]}
    h, a = r.get(home, z), r.get(away, z)
    pace = (h["pace"] + a["pace"]) / 2
    return round(pace * (a["ortg"] + h["drtg"] - lg["rtg"]) / 100 + pace * (h["ortg"] + a["drtg"] - lg["rtg"]) / 100, 1), min(h["gp"], a["gp"])


def totals_at(pm, mkmap, when):
    """[(line, over_dec, under_dec, p_over_novig, limit)] fresh Pinnacle totals at that time."""
    out = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != 11 or t != "totals" or mid not in pm:
            continue
        nmo = {v: k for k, v in outs.items()}
        tw = cl.two_way(pm, mid, when)
        o, u = nmo.get("Over"), nmo.get("Under")
        if o not in tw or u not in tw or when - min(tw[o][1], tw[u][1]) > FRESH:
            continue
        out.append((hcap, tw[o][0], tw[u][0], cl.novig_p(tw[o][0], tw[u][0]), min(tw[o][2], tw[u][2])))
    return out


def main_line(c):
    return max(c, key=lambda x: (x[4], -abs(x[3] - 0.5))) if c else None


def p_at(cands, line, side):
    """No-vig chance for the side at that line: own market, else main line moved by half-point values."""
    ex_ = next((x for x in cands if abs(x[0] - line) < 1e-9), None)
    if ex_:
        p = ex_[3]
    else:
        m = main_line(cands)
        if not m or abs(m[0] - line) > 6:
            return None
        p = m[3] if side == "Over" else 1 - m[3]
        v = sm.half_point_value("NBA", "tot", m[0], line, m[0])
        better = (line < m[0]) if side == "Over" else (line > m[0])
        return min(max(p + (v if better else -v), .01), .99)
    return p if side == "Over" else 1 - p


def first_tick(pm, mkmap):
    ts = []
    for mid, (s, t, _, _) in mkmap.items():
        if s == 11 and t == "totals" and mid in pm:
            for o in (pm[mid].get("outcomes") or {}).values():
                for x in (o.get("players") or {}).get("0") or []:
                    c = cl.tp(x.get("createdAt"))
                    if c:
                        ts.append(c)
    return min(ts) if ts else None


def match(fx, g):
    s = nm.pt(g["start"])
    words = tb.toks(g["home"]) | tb.toks(g["away"])
    for fid, f in fx.items():
        fs = cl.tp(f.get("start"))
        if f.get("lg") == "NBA" and fs and abs((fs - s).total_seconds()) <= 3 * 3600 \
                and tb.toks(f["p1"]) & words and tb.toks(f["p2"]) & words:
            return fid
    return None


def main():
    if not cl.KEY:
        print("NBA backtest: ODDSPAPI_KEY not set")
        return
    # 1. ESPN: every completed game from the season start to HI
    boxes, games = {}, []
    day = datetime.fromisoformat("2026-10-20").date()
    while day.isoformat() <= HI:
        try:
            for g in nm.scoreboard(day):
                if g["completed"] and g["hs"] is not None:
                    b = nm.box(g["id"])
                    if b:
                        boxes[g["id"]] = {"start": g["start"], "teams": b}
                    if LO <= etd(g["start"]) <= HI:
                        g["final"] = float(g["hs"]) + float(g["as"])
                        games.append(g)
        except Exception:
            pass
        day += timedelta(days=1)
    # 2. OddsPapi fixtures (1 billable) + Pinnacle history per game (free)
    st = {"billable": {}}
    mkmap = cl.load_markets(st, NOW)
    cl.refresh_fixtures(st, NOW, "NBA", datetime.fromisoformat(LO) - timedelta(days=1), datetime.fromisoformat(HI) + timedelta(days=2))
    fx = st.get("fixtures") or {}
    rows, why = [], {}
    for g in sorted(games, key=lambda g: g["start"]):
        fid = match(fx, g)
        if not fid:
            why["no OddsPapi fixture"] = why.get("no OddsPapi fixture", 0) + 1
            continue
        h = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
        if isinstance(h, dict) and h.get("_error"):
            why[f"history {h['_error']}"] = why.get(f"history {h['_error']}", 0) + 1
            continue
        pm = cl.book_markets(h, "pinnacle")
        s0 = nm.pt(g["start"])
        close = totals_at(pm, mkmap, s0)
        if not main_line(close):
            why["no Pinnacle totals close"] = why.get("no Pinnacle totals close", 0) + 1
            continue
        ft = first_tick(pm, mkmap)
        at = {"OPEN": min(ft + timedelta(minutes=1), s0) if ft else None, "T-6h": s0 - timedelta(hours=6), "T-2h": s0 - timedelta(hours=2)}
        snap = {}
        for k, t in at.items():
            c = totals_at(pm, mkmap, t) if t else []
            m = main_line(c)
            if m:
                snap[k] = {"line": m[0], "over": m[1], "under": m[2], "p_over": m[3], "lead_h": round((s0 - t).total_seconds() / 3600, 1), "c": c}
        row = {"id": g["id"], "day": etd(g["start"]), "game": f"{g['away']} @ {g['home']}", "final": g["final"],
               "close": main_line(close)[0], "snap": snap, "num": {}, "gp": None}
        for v, (n, sh) in VARIANTS.items():
            r = ratings_asof(boxes, row["day"], n, sh)
            if r:
                row["num"][v], gp = number(r, g["home"], g["away"])
                row["gp"] = gp if v == "REG" else row["gp"]
        if not row["num"]:
            why["no prior games (opening days)"] = why.get("no prior games (opening days)", 0) + 1
            continue
        # sightings per variant / timing / threshold
        row["sig"] = {}
        for v, num in row["num"].items():
            for k, sn in snap.items():
                gap = num - sn["line"]
                side = "Over" if gap > 0 else "Under"
                dec = sn["over"] if side == "Over" else sn["under"]
                pc = p_at(close, sn["line"], side)
                pt0 = sn["p_over"] if side == "Over" else 1 - sn["p_over"]
                d = (g["final"] - sn["line"]) * (1 if side == "Over" else -1)
                res = "P" if abs(d) < 1e-9 else ("W" if d > 0 else "L")
                row["sig"][f"{v}|{k}"] = {"gap": round(gap, 1), "side": side, "line": sn["line"], "dec": dec,
                                          "clv": None if pc is None else round(100 * (pc * dec - 1), 2),
                                          "move": None if pc is None else round(100 * (pc - pt0), 2),
                                          "res": res, "u": 0.0 if res == "P" else (dec - 1 if res == "W" else -1.0)}
        for sn in snap.values():
            sn.pop("c", None)
        rows.append(row)
    report(rows, why, len(games))
    print(f"NBA backtest: games {len(games)}, graded {len(rows)}, calls {len(cl.CALLS)}")   # counts only


def stats(S):
    if not S:
        return "n 0"
    c = [s["clv"] for s in S if s["clv"] is not None]
    mv = [s["move"] for s in S if s["move"] is not None]
    w, l = sum(s["res"] == "W" for s in S), sum(s["res"] == "L" for s in S)
    u = sum(s["u"] for s in S)
    out = f"n {len(S)}"
    if c:
        out += f" | CLV {stt.mean(c):+.2f}% beat-close {sum(x > 0 for x in c)}/{len(c)} | move {stt.mean(mv):+.2f} pts"
    return out + f" | {w}-{l} {u:+.2f}u ({u / len(S):+.3f}/bet)"


def report(rows, why, n_games):
    L = [f"NBA TOTALS MODEL - SEASON BACKTEST (HYPOTHESIS) | games {LO} to {HI} ET | FIT <= {SPLIT} < CHECK",
         "No look-ahead: numbers use only box scores from earlier dates. Bet = Pinnacle's own price at that time and line.",
         "CLV % = Pinnacle no-vig close at that line x decimal - 1 (vig included). move = close no-vig minus no-vig at bet time (pts).",
         "", f"Games {n_games}; graded {len(rows)}; not graded: " + (", ".join(f"{v} x {k}" for k, v in why.items()) or "none")]
    # calibration
    for k in ("OPEN", "T-6h", "T-2h"):
        g = [r for r in rows if k in r["snap"] and "REG" in r["num"]]
        if g:
            L.append(f"MAE vs final ({k}, n {len(g)}): ours REG {stt.mean(abs(r['num']['REG'] - r['final']) for r in g):.2f} | "
                     f"Pinnacle {stt.mean(abs(r['snap'][k]['line'] - r['final']) for r in g):.2f} | Pinnacle close "
                     f"{stt.mean(abs(r['close'] - r['final']) for r in g):.2f}")
    # does the market move toward us (all games, REG, open gap sign vs open->close move)
    g = [r for r in rows if "OPEN" in r["snap"] and "REG" in r["num"] and abs(r["close"] - r["snap"]["OPEN"]["line"]) > 1e-9]
    if g:
        hit = sum((r["num"]["REG"] - r["snap"]["OPEN"]["line"]) * (r["close"] - r["snap"]["OPEN"]["line"]) > 0 for r in g)
        L.append(f"Line moved open->close toward our number: {hit}/{len(g)} games that moved ({100 * hit / len(g):.0f}%; 50% = no signal)")
        for lo_, hi_ in ((0, 2), (2, 4), (4, 99)):
            s = [r for r in g if lo_ <= abs(r["num"]["REG"] - r["snap"]["OPEN"]["line"]) < hi_]
            if s:
                h2 = sum((r["num"]["REG"] - r["snap"]["OPEN"]["line"]) * (r["close"] - r["snap"]["OPEN"]["line"]) > 0 for r in s)
                L.append(f"  open gap {lo_}-{hi_ if hi_ < 99 else '+'}: toward us {h2}/{len(s)}")
    for v in VARIANTS:
        L += ["", f"VARIANT {v} (last {VARIANTS[v][0] if VARIANTS[v][0] < 999 else 'all'} games, shrink {VARIANTS[v][1]:g})"]
        for k in TIMES:
            for th in THRESH:
                S = [r["sig"][f"{v}|{k}"] for r in rows if f"{v}|{k}" in r.get("sig", {}) and abs(r["sig"][f"{v}|{k}"]["gap"]) >= th]
                F = [r["sig"][f"{v}|{k}"] for r in rows if r["day"] <= SPLIT and f"{v}|{k}" in r.get("sig", {}) and abs(r["sig"][f"{v}|{k}"]["gap"]) >= th]
                C = [r["sig"][f"{v}|{k}"] for r in rows if r["day"] > SPLIT and f"{v}|{k}" in r.get("sig", {}) and abs(r["sig"][f"{v}|{k}"]["gap"]) >= th]
                L.append(f"  {k:<5} gap>={th:g}: {stats(S)}")
                if v == "REG" and th == 3.0:
                    L.append(f"      FIT {stats(F)}")
                    L.append(f"      CHECK {stats(C)}")
                if v == "REG" and th == 3.0:
                    for sd in ("Over", "Under"):
                        L.append(f"      {sd}s {stats([s for s in S if s['side'] == sd])}")
    # registered bar (Muse 12:19): >= 100 games AND avg CLV > 0 AND beat-close >= 53%, holding in BOTH halves
    L += ["", "REGISTERED BAR (REG, gap >= 3.0): >= 100 games graded, avg CLV > 0 and beat-close >= 53% in FIT and in CHECK"]
    for k in TIMES:
        ok = len(rows) >= 100
        parts = []
        for lab, sel in (("FIT", lambda r: r["day"] <= SPLIT), ("CHECK", lambda r: r["day"] > SPLIT)):
            c = [r["sig"][f"REG|{k}"]["clv"] for r in rows if sel(r) and f"REG|{k}" in r.get("sig", {})
                 and abs(r["sig"][f"REG|{k}"]["gap"]) >= 3.0 and r["sig"][f"REG|{k}"]["clv"] is not None]
            good = bool(c) and stt.mean(c) > 0 and sum(x > 0 for x in c) / len(c) >= 0.53
            ok = ok and good
            parts.append(f"{lab} n {len(c)} {'pass' if good else 'fail'}")
        L.append(f"  {k:<5}: {'MEETS BAR' if ok else 'does not meet bar'} (games {len(rows)}; " + "; ".join(parts) + ")")
    L += ["", "REG T-6h SIGHTINGS (gap >= 3.0):"]
    for r in rows:
        s = r.get("sig", {}).get("REG|T-6h")
        if s and abs(s["gap"]) >= 3.0:
            L.append(f"  {r['day']} {r['game']} | ours {r['num']['REG']} vs Pin {s['line']:g} (open {r['snap'].get('OPEN', {}).get('line', '-')}, close {r['close']:g}) "
                     f"| {s['side']} {cl.dec_to_am(s['dec']):+d} | CLV {s['clv'] if s['clv'] is not None else '-'}% | final {r['final']:g} {s['res']}")
    L += ["", "Calls: " + f"{len(cl.CALLS)} total; billable {cl.STATS['billable']}"]
    ex.send("Bets NBA MODEL BACKTEST (HYPOTHESIS)", "\n".join(L))


if __name__ == "__main__":
    main()
