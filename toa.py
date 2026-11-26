#!/usr/bin/env python3
"""THE ODDS API HISTORICAL PINNACLE CLOSES - one shared store (Peter, Nov 26 2026).

WHY. 3,223 graded observations were rejected MISSING_HISTORY and 506 FIXTURE_OR_IDENTITY: OddsPapi history is free but
its fixture lookups bill, and that budget is spent until Dec 4. The Odds API's historical endpoint needs no fixture id:
one call returns every game of a sport at a 5-minute snapshot, Pinnacle included. The plan is 5M credits a month.

ONE STORE, READ BY EVERYONE. Snapshots are gzip files under toa_hist/<sport>/, kept in the Actions cache (private to this
repo, never committed - provider data is not republished). Only toa_recover.py fetches; every reader is cache-only.

THE SAME CERTIFICATION RULES, NOTHING LOOSER:
  - exact line only ("own line"); a moneyline counts as its own line. No half-point conversion, no estimate.
  - two-sided Pinnacle quote at the SAME snapshot, de-vigged with clv_ledger.novig_p.
  - the snapshot is at or BEFORE the listed start and no more than SNAP_MAX_MIN before it (a 5-minute cadence),
    and each quote's last change is within clv_ledger.FRESH_MIN of the start - the ledger's own freshness rule.
  - a game that cannot be matched to exactly one event is refused, never guessed (fixture_match.ordered_match).
"""
import glob
import gzip
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

DIR = os.environ.get("TOA_DIR", "") or "toa_hist"
API = "https://api.the-odds-api.com/v4"
SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba",
         "NCAAB": "basketball_ncaab", "NHL": "icehockey_nhl", "MLB": "baseball_mlb", "WNBA": "basketball_wnba"}
FEATURED = "h2h,spreads,totals"
ALTS = "alternate_spreads,alternate_totals"
SNAP_MAX_MIN = 10          # the snapshot used as the close must be within 10 minutes before the start
METER = {"calls": 0, "credits": 0, "empty": 0}
SRC = "theoddsapi"


def _iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _path(sport, name):
    return os.path.join(DIR, sport, name + ".json.gz")


def _save(sport, name, data):
    os.makedirs(os.path.join(DIR, sport), exist_ok=True)
    with gzip.open(_path(sport, name), "wt") as fh:
        json.dump(data, fh, separators=(",", ":"))


def _load(p):
    try:
        with gzip.open(p, "rt") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- fetch (toa_recover.py only)
def _get(path, params):
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        raise RuntimeError("ODDS_API_KEY not set")
    url = f"{API}{path}?{urllib.parse.urlencode(dict(params, apiKey=key))}"
    with urllib.request.urlopen(url, timeout=40) as r:
        body = json.loads(r.read().decode())
        last = r.headers.get("x-requests-last")
        METER["calls"] += 1
        try:
            METER["credits"] += int(float(last or 0))
        except ValueError:
            pass
        METER["remaining"] = r.headers.get("x-requests-remaining")
        return body


def snap_name(when):
    return "f_" + _iso(when).replace(":", "")


def have_snap(sport, when):
    return os.path.exists(_path(sport, snap_name(when)))


def fetch_snapshot(sport, when):
    """Featured Pinnacle markets for every game of `sport` at the snapshot at or before `when`. Cached forever."""
    if have_snap(sport, when):
        return _load(_path(sport, snap_name(when)))
    d = _get(f"/historical/sports/{sport}/odds", {"date": _iso(when), "bookmakers": "pinnacle",
                                                  "markets": FEATURED, "oddsFormat": "decimal"})
    if not (d or {}).get("data"):
        METER["empty"] += 1
    _save(sport, snap_name(when), d or {})
    return d


def alt_name(eid, when):
    return f"a_{eid}_" + _iso(when).replace(":", "")


def fetch_alts(sport, eid, when):
    """Pinnacle alternate spreads/totals for one event at the snapshot at or before `when`. Cached forever."""
    p = _path(sport, alt_name(eid, when))
    if os.path.exists(p):
        return _load(p)
    d = _get(f"/historical/sports/{sport}/events/{eid}/odds",
             {"date": _iso(when), "bookmakers": "pinnacle", "markets": ALTS, "oddsFormat": "decimal"})
    _save(sport, alt_name(eid, when), d or {})
    return d


# ---------------------------------------------------------------- read side (cache-only)
_FX = {}


def fixtures(lg):
    """{'toa:<event id>': {'lg','start','p1','p2'}} for every event in the stored snapshots of this league."""
    sport = SPORT.get(lg)
    if not sport:
        return {}
    if lg in _FX:
        return _FX[lg]
    out = {}
    for p in glob.glob(os.path.join(DIR, sport, "f_*.json.gz")):
        for ev in (_load(p) or {}).get("data") or []:
            if ev.get("id") and ev.get("home_team") and ev.get("away_team"):
                out["toa:" + ev["id"]] = {"lg": lg, "start": ev.get("commence_time"),
                                          "p1": ev["home_team"], "p2": ev["away_team"]}
    _FX[lg] = out
    return out


_IDX = {}


def _index(sport):
    """{event id: [(snapshot_ts, pinnacle markets)]} over every stored file of a sport. Built once per process."""
    if sport in _IDX:
        return _IDX[sport]
    idx = {}
    for p in glob.glob(os.path.join(DIR, sport, "*.json.gz")):
        d = _load(p) or {}
        ts = _tp(d.get("timestamp"))
        data = d.get("data")
        evs = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        for ev in evs:
            for bk in ev.get("bookmakers") or []:
                if bk.get("key") == "pinnacle" and ts and ev.get("id"):
                    idx.setdefault(ev["id"], []).append((ts, bk.get("markets") or []))
    _IDX[sport] = idx
    return idx


def reset_cache():
    _FX.clear()
    _IDX.clear()


def _quotes(lg, eid, start):
    """[(snapshot_ts, pinnacle markets list)] for this event, featured and alternates, at snapshots <= start."""
    return [r for r in _index(SPORT[lg]).get(eid, []) if r[0] <= start]


def _pair(mkts, keys, held, other):
    """(held_price, other_price, oldest last_update) where both outcomes sit in ONE market of `keys`, or None."""
    for m in mkts:
        if m.get("key") not in keys:
            continue
        oc = m.get("outcomes") or []
        a = next((o for o in oc if held(o)), None)
        b = next((o for o in oc if other(o)), None)
        if a and b and a.get("price") and b.get("price"):
            return float(a["price"]), float(b["price"]), _tp(m.get("last_update"))
    return None


def close(snap, f, fid, lg, parsed, resolve_side, which_team, novig_p, fresh_min):
    """({'p','how','age_min','src','snap_ts'}, None) or (None, why). Exact line only; same rules as the ledger."""
    start = _tp(f.get("start"))
    if not start:
        return None, "toa: event has no start time"
    pz = parsed(snap)
    if not pz:
        return None, "toa: bet text not parsed"
    quotes = _quotes(lg, fid.split(":", 1)[1], start)
    if not quotes:
        return None, "toa: no stored Pinnacle snapshot at or before the start"
    last_ts = max(q[0] for q in quotes)
    if (start - last_ts) > timedelta(minutes=SNAP_MAX_MIN):
        return None, "toa: latest stored snapshot is not at the close"
    mkts = [m for ts, ms in quotes if ts == last_ts for m in ms]
    if pz[0] == "total":
        want, over = float(pz[2]), str(pz[1]).upper() == "OVER"
        nm, on = ("Over", "Under") if over else ("Under", "Over")
        r = _pair(mkts, ("totals", "alternate_totals"),
                  lambda o: o.get("name") == nm and abs(float(o.get("point", 1e9)) - want) < 1e-9,
                  lambda o: o.get("name") == on and abs(float(o.get("point", 1e9)) - want) < 1e-9)
        how = "own line"
    else:
        side, why = resolve_side(f, pz[1], lg, which_team)
        if not side:
            return None, f"toa: {why}"
        if pz[0] == "ml":
            if len(pz) > 3 and pz[3]:
                side = "2" if side == "1" else "1"
            mine, theirs = (f["p1"], f["p2"]) if side == "1" else (f["p2"], f["p1"])
            r = _pair(mkts, ("h2h",), lambda o: o.get("name") == mine, lambda o: o.get("name") == theirs)
            how = "moneyline"
        else:
            want = float(pz[2])
            if pz[3]:
                side, want = ("2" if side == "1" else "1"), -want
            mine, theirs = (f["p1"], f["p2"]) if side == "1" else (f["p2"], f["p1"])
            r = _pair(mkts, ("spreads", "alternate_spreads"),
                      lambda o: o.get("name") == mine and abs(float(o.get("point", 1e9)) - want) < 1e-9,
                      lambda o: o.get("name") == theirs and abs(float(o.get("point", 1e9)) + want) < 1e-9)
            how = "own line"
    if not r:
        return None, "toa: Pinnacle had no two-sided quote at this exact line at the close"
    a, b, lu = r
    age = (start - lu).total_seconds() / 60 if lu else None
    if age is None or age > fresh_min or age < -1:
        return None, "toa: quote outside the freshness rule"
    return {"p": novig_p(a, b), "how": how, "age_min": round(max(age, 0)), "src": SRC,
            "snap_ts": _iso(last_ts)}, None


def report():
    """Counts only - credits by this process, for the per-workflow meter."""
    return (f"ODDS API (The Odds API) this run [{os.environ.get('GITHUB_WORKFLOW', 'local')}]: "
            f"calls {METER['calls']}, credits {METER['credits']}, empty {METER['empty']}, "
            f"remaining {METER.get('remaining')}")
