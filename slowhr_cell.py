#!/usr/bin/env python3
"""
SLOW-HR DECISIVE CELL (Nov 6, 2026; Peter, rules fixed in advance). HYPOTHESIS ONLY - a historical verdict on ONE cell.
Nothing live changes: the scanner stays paper / information-only, flags stay manual, no thresholds move.

POPULATION: the registered SLOW-HR backtest population, unchanged - slow_hr.sightings + slowhr_backtest.enrich over every
finished NFL / NCAAF / NHL game, Pinnacle vs Hard Rock, from the shared history cache, games Oct 12 - Nov 2 (ET), not LATE
(the backtest's own headline basis).
CELL: Type P sightings x moneyline x underdog (enrich's side class) x EV >= +2% vs Pinnacle no-vig fair at the sighting
(slow_hr ev_pct: fair at the confirmation read vs Hard Rock's price - time-aligned).
RULES:
  - Dedupe on canonical event identity: event = league + ET date + both teams' names (from the fixture, order-free); a
    play = event + market + side, first sighting kept (one play counts once). Report raw sightings, n plays AND distinct
    games. The test is judged on DISTINCT GAMES.
  - Cutoff 100 distinct games. Below that the result is DIAGNOSTIC ONLY and the test stays open.
  - Pooled CLV <= 0 (Pinnacle no-vig close, % at Hard Rock's price) VETOES the cell outright, whatever the units say.
  - FIT <= Oct 22 < CHECK, reported separately with coverage (CLV-graded and result-graded shares).
  - Suspect-quote screen: the cell with AND without sightings at EV > +15%.
  - DATA CHECK: wins vs expected wins (sum of the close no-vig chance), z = (wins - expected) / sd, on each version.
Grading: flat 1u at the Hard Rock price, ESPN finals (finals.units). Private email; the log prints counts only.
"""
import json
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import finals as fin
import hist_cache as hc
import slow_hr as sh
import slowhr_backtest as bt
import tracker_build as tb

ET = tb.ET
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
LAST_DAY = os.environ.get("CELL_LAST_DAY", "") or "2026-11-02"      # registered population ends Nov 2 (ET)
FIT_END = os.environ.get("CELL_FIT_END", "") or "2026-10-22"        # FIT <= Oct 22 < CHECK
EV_MIN, EV_SUSPECT, MIN_GAMES = 2.0, 15.0, 100


def event_key(x):
    nm = x.get("game") or ""
    sides = [s.strip() for s in nm.split(" vs ")] if " vs " in nm else [nm]
    teams = tuple(sorted(" ".join(sorted(tb.toks(s))) for s in sides))
    return (x["league"], x["day"], teams)


def in_cell(x):
    return (x.get("kind") == "P" and x.get("type") == "moneyline" and x.get("sclass") == "dog"
            and x.get("ev_pct") is not None and x["ev_pct"] >= EV_MIN and not x.get("late"))


def dedupe(xs):
    first = {}
    for x in sorted(xs, key=lambda z: z["t_move"]):
        first.setdefault(event_key(x) + (x["type"], str(x["side"])), x)
    return list(first.values())


def summary(xs):
    n = len(xs)
    games = len({event_key(x) for x in xs})
    clv = [x["clv_pct"] for x in xs if x.get("clv_pct") is not None]
    res = [(x, fin.result(x)) for x in xs]
    g = [(x, r) for x, r in res if r in ("W", "L", "P")]
    u = sum(fin.units_wl(r, x["hr_price"]) or 0 for x, r in g)
    w, l_ = sum(1 for _, r in g if r == "W"), sum(1 for _, r in g if r == "L")
    s = (f"n {n} plays | {games} distinct games | {w}-{l_}" + (f"-{len(g) - w - l_}" if len(g) - w - l_ else "")
         + f" | {u:+.2f}u" + (f" ({u / len(g):+.3f}/play)" if g else ""))
    s += (f" | CLV {stt.mean(clv):+.2f}% beat close {sum(1 for v in clv if v > 0)}/{len(clv)}" if clv else " | CLV n/a")
    s += f" | coverage: CLV {len(clv)}/{n}, result {len(g)}/{n}" if n else ""
    return s, games, (stt.mean(clv) if clv else None), g


def data_check(g):
    wl = [(x, r) for x, r in g if r in ("W", "L") and x.get("close_fair") is not None]
    if not wl:
        return "graded 0"
    w = sum(1 for _, r in wl if r == "W")
    e = sum(x["close_fair"] for x, _ in wl)
    sd = sum(x["close_fair"] * (1 - x["close_fair"]) for x, _ in wl) ** 0.5 or 1
    eu = sum(x["close_fair"] * x["hr_price"] - 1 for x, _ in wl)
    au = sum((x["hr_price"] - 1) if r == "W" else -1.0 for x, r in wl)
    return f"graded {len(wl)} | wins {w} vs expected {e:.1f} (z {(w - e) / sd:+.2f}) | units {au:+.2f}u vs expected {eu:+.2f}u"


def verdict(games, clv):
    if clv is not None and clv <= 0:
        return "VETOED - pooled CLV <= 0"
    if games < MIN_GAMES:
        return f"DIAGNOSTIC ONLY - {games} distinct games < {MIN_GAMES}; test stays open"
    if clv is None:
        return "NO VERDICT - no CLV-graded plays"
    return f"{games} distinct games, pooled CLV > 0 - eligible for review (not an automatic pass)"


def population():
    now = datetime.now(timezone.utc)
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in bt.LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    have = {f.get("lg") for f in (st.get("fixtures") or {}).values()}
    if any(lg not in have for lg in bt.LEAGUES):   # same fallback as the registered backtest
        for path in ("exlag/state.enc", "slowhr/state.enc"):
            try:
                other = tb.dec(json.load(open(path)))
            except Exception:
                continue
            for fid, f in (other.get("fixtures") or {}).items():
                if f.get("lg") in bt.LEAGUES and f.get("lg") not in have and fid not in st.setdefault("fixtures", {}):
                    st["fixtures"][fid] = f
    todo = sorted((cl.tp(f["start"]), fid, f) for fid, f in (st.get("fixtures") or {}).items()
                  if f.get("lg") in bt.LEAGUES and cl.tp(f.get("start")) and FROM <= cl.tp(f["start"]) <= now - hc.FINAL_AFTER
                  and cl.tp(f["start"]).astimezone(ET).strftime("%Y-%m-%d") <= LAST_DAY)
    sh.FLOOR = FROM
    S, games, errs = [], 0, 0
    for s, fid, f in todo:
        h = hc.get_hist(fid, ["pinnacle", "hardrockbet"] + bt.EXB, s)
        if isinstance(h, dict) and h.get("_error"):
            errs += 1
            continue
        pin, hr = cl.book_markets(h, "pinnacle"), cl.book_markets(h, "hardrockbet")
        if not pin or not hr:
            continue
        games += 1
        for x in sh.sightings(fid, {"participant1Name": f.get("n1"), "participant2Name": f.get("n2")}, f["lg"], pin, hr, mkmap, s):
            x["day"] = s.astimezone(ET).strftime("%Y-%m-%d")
            if x.get("close_fair") is not None:
                x["clv_pct"] = round(100 * (x["close_fair"] * x["hr_price"] - 1), 2)
            try:
                bt.enrich(x, f["lg"], pin, hr, h, mkmap, s)
            except Exception:
                x.setdefault("sclass", None)
            S.append(x)
    return S, games, errs


def report(S, games_read, errs):
    raw = [x for x in S if in_cell(x)]
    full = dedupe(raw)
    clean = [x for x in full if x["ev_pct"] <= EV_SUSPECT]
    L = ["SLOW-HR DECISIVE CELL - HYPOTHESIS ONLY | historical verdict on one cell | nothing live changes",
         f"Population: registered SLOW-HR backtest, NFL/NCAAF/NHL, games {FROM.date()} to {LAST_DAY} ET, not LATE | "
         f"games read {games_read}, errors {errs}, sightings {len(S)}",
         f"Cell: Type P x moneyline x underdog x EV >= +{EV_MIN:g}% vs Pinnacle no-vig fair at the sighting | "
         f"raw sightings {len(raw)} -> {len(full)} plays after dedupe (event + market + side, first kept)",
         f"Rules: judged on distinct games, cutoff {MIN_GAMES}; pooled CLV <= 0 vetoes; FIT <= {FIT_END} < CHECK", ""]
    for name, xs in (("CELL (all quotes)", full), (f"CELL without EV > +{EV_SUSPECT:g}% (suspect-quote screen)", clean)):
        s, g_n, c, g = summary(xs)
        L += [f"{name}:", f"  pooled  {s}",
              f"  FIT     {summary([x for x in xs if x['day'] <= FIT_END])[0]}",
              f"  CHECK   {summary([x for x in xs if x['day'] > FIT_END])[0]}",
              f"  DATA CHECK  {data_check(g)}",
              f"  VERDICT  {verdict(g_n, c)}", ""]
    L.append(f"Removed by the suspect screen: {len(full) - len(clean)} plays: {summary([x for x in full if x['ev_pct'] > EV_SUSPECT])[0]}")
    L += ["", "PLAYS (dedupe kept, oldest first):"]
    for x in sorted(full, key=lambda z: z["t_move"]):
        r = fin.result(x)
        L.append(f"  {x['day']} {x['league']} {x['game']} | ML {x['team']} HR {x['hr_am']:+d} | EV {x['ev_pct']:+.1f}% | "
                 f"CLV {x['clv_pct']:+.2f}%" if x.get("clv_pct") is not None else
                 f"  {x['day']} {x['league']} {x['game']} | ML {x['team']} HR {x['hr_am']:+d} | EV {x['ev_pct']:+.1f}% | CLV n/a")
        L[-1] += f" | {r or 'ungraded'}"
    return L, len(raw), len(full), len({event_key(x) for x in full})


def main():
    if not cl.KEY:
        print("slow-hr cell: ODDSPAPI_KEY not set")
        return
    S, games_read, errs = population()
    L, n_raw, n, n_games = report(S, games_read, errs)
    ex.send("Bets SLOW-HR DECISIVE CELL (HYPOTHESIS)", "\n".join(L))
    print(f"slow-hr cell: games read {games_read}, cell sightings {n_raw}, plays {n}, distinct games {n_games}")   # counts only


if __name__ == "__main__":
    main()
