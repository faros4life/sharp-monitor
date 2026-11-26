"""The Odds API close: exact line only, same snapshot, at the close, fresh, de-vigged. Offline."""
import os
import tempfile

D = tempfile.mkdtemp()
os.environ["TOA_DIR"] = D
import clv_ledger as cl
import fixture_match as fxm
import toa

FAILED = []


def ok(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


START = "2026-11-20T00:10:00Z"
EV = {"id": "e1", "commence_time": START, "home_team": "Denver Nuggets", "away_team": "Dallas Mavericks",
      "bookmakers": [{"key": "pinnacle", "markets": [
          {"key": "h2h", "last_update": "2026-11-20T00:05:00Z",
           "outcomes": [{"name": "Denver Nuggets", "price": 1.5}, {"name": "Dallas Mavericks", "price": 2.7}]},
          {"key": "spreads", "last_update": "2026-11-20T00:05:00Z",
           "outcomes": [{"name": "Denver Nuggets", "price": 1.91, "point": -5.5},
                        {"name": "Dallas Mavericks", "price": 1.95, "point": 5.5}]},
          {"key": "totals", "last_update": "2026-11-20T00:05:00Z",
           "outcomes": [{"name": "Over", "price": 1.93, "point": 233.5},
                        {"name": "Under", "price": 1.93, "point": 233.5}]}]}]}
toa._save("basketball_nba", "f_pre", {"timestamp": "2026-11-20T00:05:00Z", "data": [EV]})
# an IN-PLAY snapshot after the start with a different total - must never be read
live = dict(EV, bookmakers=[{"key": "pinnacle", "markets": [
    {"key": "totals", "last_update": "2026-11-20T00:20:00Z",
     "outcomes": [{"name": "Over", "price": 1.5, "point": 240.5}, {"name": "Under", "price": 2.6, "point": 240.5}]}]}])
toa._save("basketball_nba", "f_live", {"timestamp": "2026-11-20T00:20:00Z", "data": [live]})
toa.reset_cache()

fx = toa.fixtures("NBA")
ok("store exposes the event as a fixture", fx.get("toa:e1", {}).get("p1") == "Denver Nuggets")


def go(bet, game="Dallas Mavericks @ Denver Nuggets"):
    snap = {"bet": bet, "league": "NBA", "game": game, "game_start": START}
    fid, _ = fxm.ordered_match(snap, fx, cl.tp)
    if not fid:
        return None, "no match"
    return toa.close(snap, fx[fid], fid, "NBA", cl.parsed, fxm.resolve_side, cl.which_team, cl.novig_p, cl.FRESH_MIN)


c, w = go("Under 233.5 (-110)")
ok("total at Pinnacle's own line is certified", c and c["how"] == "own line" and abs(c["p"] - 0.5) < 1e-9)
ok("the in-play snapshot is ignored", c and c["snap_ts"] == "2026-11-20T00:05:00Z")
c, w = go("Under 234.5 (-110)")
ok("a different total is REFUSED, never converted", c is None and "exact line" in w)
c, w = go("Dallas Mavericks +5.5 (-105)")
ok("spread at the exact line, away side", c and c["how"] == "own line" and abs(c["p"] - cl.novig_p(1.95, 1.91)) < 1e-9)
c, w = go("Denver Nuggets -5.5 (-110)")
ok("spread at the exact line, home side", c and abs(c["p"] - cl.novig_p(1.91, 1.95)) < 1e-9)
c, w = go("Denver Nuggets -6.5 (-110)")
ok("a different spread is refused", c is None)
c, w = go("Dallas Mavericks ML (+170)")
ok("moneyline counts as its own line", c and c["how"] == "moneyline" and abs(c["p"] - cl.novig_p(2.7, 1.5)) < 1e-9)

# a close snapshot more than 10 minutes before the start is not the close
D2 = tempfile.mkdtemp()
toa.DIR = D2
toa._save("basketball_nba", "f_old", {"timestamp": "2026-11-19T23:50:00Z", "data": [EV]})
toa.reset_cache()
fx = toa.fixtures("NBA")
c, w = go("Under 233.5 (-110)")
ok("a snapshot 20 minutes before the start is refused", c is None and "not at the close" in w)

# no store at all: the shared waterfall keeps its original rejection
import clv_obs_audit as oa
toa.DIR = os.path.join(D, "missing")
toa.reset_cache()
ok("no store -> no fallback", oa._toa_verified({"bet": "Under 233.5", "league": "NBA", "game_start": START}, "NBA", 1.9)
   is None)
ok("budget is checked before each call", "spend_ok(FEAT_COST)" in open("toa_recover.py").read())

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
