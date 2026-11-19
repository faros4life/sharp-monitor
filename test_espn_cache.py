#!/usr/bin/env python3
"""ESPN scoreboard reuse (Peter, Nov 19): "cache only verified complete historical scoreboards.
Incomplete or failed responses must remain eligible for retries."

The waste being removed: espn_fill swept up to 50 dates x 8 league jobs = ~400 ESPN reads EVERY run,
re-reading the same settled historical dates, and a row beyond the 50-date cap never burned a try, so
it queued forever. The fix caches the OUTCOME, not the payload - a 50-date slate would add megabytes
to a state file that is already 1.3 MB and is committed on every run.

The failure this file exists to prevent is the silent one: a date wrongly marked settled is never read
again for that row, so the row can never resolve and nothing says so. Hence the negative assertions -
a failed read, a partial slate, a live game, today's date, or a date empty across every league must
all leave the date OPEN.
"""
from datetime import datetime, timedelta, timezone

import tracker_build as tb
import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


ET = tb.ET
NOW = datetime.now(ET)
PAST = (NOW - timedelta(days=4)).replace(hour=12, minute=0, second=0, microsecond=0)
TODAY = NOW.replace(hour=12, minute=0, second=0, microsecond=0)
FUTURE = (NOW + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)


def ev(gid, state="post", completed=True, home="Boston Celtics", away="Miami Heat", start=None):
    return {"id": gid, "date": start or PAST.astimezone(timezone.utc).isoformat(),
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": "101", "team": {"displayName": home, "shortDisplayName": home.split()[-1],
                                                              "name": home.split()[-1], "location": home.split()[0],
                                                              "abbreviation": home[:3].upper()}},
                {"homeAway": "away", "score": "99", "team": {"displayName": away, "shortDisplayName": away.split()[-1],
                                                             "name": away.split()[-1], "location": away.split()[0],
                                                             "abbreviation": away[:3].upper()}}]}],
            "status": {"period": 4, "displayClock": "0:00", "type": {"state": state, "completed": completed,
                                                                     "shortDetail": "Final", "detail": "Final"}}}


# ------------------------------------------------------------------ 1. terminal / verified predicates
ok("a completed game is terminal", tb._espn_terminal(ev("1")))
ok("a postponed game is terminal (state post, completed false)", tb._espn_terminal(ev("1", "post", False)))
ok("an in-progress game is NOT terminal", not tb._espn_terminal(ev("1", "in", False)))
ok("a scheduled game is NOT terminal", not tb._espn_terminal(ev("1", "pre", False)))
ok("a game with no status at all is NOT terminal", not tb._espn_terminal({"id": "1"}))

ok("a failed read (None) is never verified", not tb.espn_verified(None, PAST, NOW))
ok("a non-dict response is never verified", not tb.espn_verified([ev("1")], PAST, NOW))
ok("a response with no 'events' key is never verified", not tb.espn_verified({"leagues": []}, PAST, NOW))
ok("a response whose 'events' is not a list is never verified", not tb.espn_verified({"events": {}}, PAST, NOW))
ok("a past date with every game final IS verified", tb.espn_verified({"events": [ev("1"), ev("2")]}, PAST, NOW))
ok("one live game on an otherwise final past slate blocks it",
   not tb.espn_verified({"events": [ev("1"), ev("2", "in", False)]}, PAST, NOW))
ok("one unplayed game on a past slate blocks it",
   not tb.espn_verified({"events": [ev("1"), ev("2", "pre", False)]}, PAST, NOW))
ok("a postponed game does NOT block an otherwise final past slate",
   tb.espn_verified({"events": [ev("1"), ev("2", "post", False)]}, PAST, NOW))
ok("TODAY is never verified however final it looks", not tb.espn_verified({"events": [ev("1")]}, TODAY, NOW))
ok("a future date is never verified", not tb.espn_verified({"events": [ev("1")]}, FUTURE, NOW))
ok("the past/today boundary is the ET CALENDAR DAY, not 24h",
   tb.espn_verified({"events": []}, (NOW - timedelta(days=1)).replace(hour=23), NOW)
   and not tb.espn_verified({"events": []}, NOW.replace(hour=0, minute=1), NOW))
ok("emptiness is NOT judged by espn_verified (the caller judges it)",
   tb.espn_verified({"events": []}, PAST, NOW))


# ------------------------------------------------------------------ 2. espn_games completeness reporting
def run_games(responder, days=(PAST,), **kw):
    calls = []

    def fake(url):
        calls.append(url)
        return responder(url)
    real, tb._espn_get = tb._espn_get, fake
    try:
        comp = set()
        games = tb.espn_games(list(days), complete=comp, **kw)
    finally:
        tb._espn_get = real
    return games, comp, calls


_all_final = lambda url: {"events": [ev("nhl1" if "hockey" in url else "g1")]}
games, comp, calls = run_games(_all_final)
ok("a full sweep is one read per league, plus the extra NCAAB division-I read", len(calls) == 8, len(calls))
ok("a past date verified in every league is reported complete", comp == {PAST.strftime("%Y%m%d")}, comp)

games, comp, _ = run_games(lambda url: None)
ok("a date whose every read FAILED is not complete", comp == set())
ok("a date whose every read failed yields no games", games == [])

games, comp, _ = run_games(lambda url: None if "hockey" in url else _all_final(url))
ok("ONE failed league read leaves the whole date open", comp == set(), comp)
ok("the other leagues' games are still returned", len(games) > 0)

games, comp, _ = run_games(lambda url: {"events": [ev("g1", "in", False)]} if "nhl" in url else _all_final(url))
ok("one league still playing leaves the whole date open", comp == set(), comp)

games, comp, _ = run_games(lambda url: {"events": []})
ok("a date EMPTY across every league is not complete (that is what a glitch looks like)", comp == set(), comp)

games, comp, _ = run_games(lambda url: _all_final(url) if "hockey" in url else {"events": []})
ok("a date with games in one league only IS complete", comp == {PAST.strftime("%Y%m%d")}, comp)

games, comp, _ = run_games(_all_final, days=(TODAY,))
ok("today is never reported complete even when every read is final", comp == set(), comp)

games, comp, calls = run_games(_all_final, days=(PAST, PAST - timedelta(days=1)))
ok("two dates are two sweeps", len(calls) == 16, len(calls))
ok("both past dates are reported complete", len(comp) == 2, comp)

games, comp, calls = run_games(_all_final, leagues=("NFL", "NHL"))
ok("a league-filtered sweep reads only those leagues", len(calls) == 2, len(calls))
ok("a league-filtered sweep reports NO date complete - the other leagues were never read",
   comp == set(), comp)

# dedupe across the NCAAB double read, unchanged by this work
games, comp, _ = run_games(lambda url: {"events": [ev("same")]})
ok("one game id per league survives however many feeds carry it",
   len([g for g in games if g["league"] == "NCAAB"]) == 1,
   [g["league"] for g in games])
ok("every league still contributes its own row", len(games) == len(tb.LEAGUES))
ok("an event with no id is never dropped by the dedupe",
   len(run_games(lambda url: {"events": [dict(ev("x"), id=None), dict(ev("y"), id=None)]}, days=(PAST,))[0]) == 16)


# ------------------------------------------------------------------ 3. espn_fill reuse
def row(key, t0, **extra):
    r = {"snap": {"game": "Miami Heat at Boston Celtics", "bet": "Boston Celtics -3.5",
                  "settled": t0.astimezone(timezone.utc).isoformat()}, "first_seen": t0.astimezone(timezone.utc).isoformat()}
    r.update(extra)
    return key, r


def run_fill(bets, matcher=None, complete_dates=None, fail=False):
    """Returns (state, dates actually read, log lines)."""
    st = {"bets": dict(bets)}
    read = []

    def fake_games(days, leagues=None, complete=None):
        read.extend(d.strftime("%Y%m%d") for d in days)
        if complete is not None and not fail:
            complete.update(complete_dates if complete_dates is not None
                            else {d.strftime("%Y%m%d") for d in days})
        return [{"league": "NBA", "id": "g1", "start": PAST.isoformat(), "final": True,
                 "teams": [{"home": True, "full": "Boston Celtics"}, {"home": False, "full": "Miami Heat"}]}]

    real_g, real_m = tb.espn_games, tb.match_game
    log0 = len(cl.LG_LOG)
    tb.espn_games = fake_games
    tb.match_game = matcher or (lambda *a, **k: None)
    try:
        cl.espn_fill(st, NOW)
    finally:
        tb.espn_games, tb.match_game = real_g, real_m
    return st, read, cl.LG_LOG[log0:]


t0 = NOW - timedelta(days=4)
want = sorted(d.strftime("%Y%m%d") for d in cl._espn_days(t0))

st, read, log = run_fill([row("a", t0)])
ok("an unmatched row on a settled date is closed out for those dates",
   st["bets"]["a"].get("espn_done") == want, st["bets"]["a"].get("espn_done"))
ok("an unmatched row still burns a try", st["bets"]["a"]["espn_tries"] == 1)
ok("the row's own two dates are what gets read", sorted(set(read)) == want, read)

st2, read2, log2 = run_fill([row("a", t0, espn_done=want)])
ok("a row whose every date is settled triggers NO read at all", read2 == [], read2)
ok("...and is reported as skipped", "skipped as already checked" in (log2[-1] if log2 else ""), log2)
ok("...and does not burn another try", "espn_tries" not in st2["bets"]["a"])

st3, read3, _ = run_fill([row("a", t0, espn_done=[want[0]])])
ok("a row with ONE date settled reads only the other one", read3 == [want[1]], read3)
ok("...and ends up with both recorded",
   st3["bets"]["a"]["espn_done"] == want, st3["bets"]["a"]["espn_done"])

st4, _, _ = run_fill([row("a", t0)], complete_dates=set())
ok("an INCOMPLETE date is never marked done - the row stays eligible for retry",
   "espn_done" not in st4["bets"]["a"])
ok("...and still burns a try, so a hopeless row still ages out", st4["bets"]["a"]["espn_tries"] == 1)

st5, _, _ = run_fill([row("a", t0)], complete_dates={want[0]})
ok("only the dates that were actually settled are recorded",
   st5["bets"]["a"]["espn_done"] == [want[0]], st5["bets"]["a"].get("espn_done"))

hit = lambda *a, **k: {"league": "NBA", "start": PAST.isoformat(),
                       "teams": [{"home": True, "full": "Boston Celtics"}, {"home": False, "full": "Miami Heat"}]}
st6, _, _ = run_fill([row("a", t0)], matcher=hit)
ok("a MATCHED row is filled", st6["bets"]["a"]["snap"].get("espn_filled") is True)
ok("a matched row is not marked done (it no longer qualifies anyway)", "espn_done" not in st6["bets"]["a"])
ok("a matched row burns no try", "espn_tries" not in st6["bets"]["a"])
ok("a matched row takes league, start and both teams from ESPN",
   st6["bets"]["a"]["snap"]["game_start"] == PAST.isoformat()
   and [t["name"] for t in st6["bets"]["a"]["snap"]["teams"]] == ["Miami Heat", "Boston Celtics"])

st7, read7, _ = run_fill([row("a", t0), row("b", NOW - timedelta(days=60))])
ok("a row older than the 45-day window is not attempted", "espn_tries" not in st7["bets"]["b"])
st8, _, _ = run_fill([row("a", t0, espn_tries=6)])
ok("a row at the try ceiling is not attempted", read8 := True and st8["bets"]["a"]["espn_tries"] == 6)
st9, _, _ = run_fill([row("a", t0, snap_filled=True)] and [("a", {"snap": {"game_start": PAST.isoformat()}})])
ok("a row that already has a game_start is not attempted", "espn_tries" not in st9["bets"]["a"])

# the whole point, end to end: run twice, second run costs nothing
st10 = {"bets": dict([row("a", t0)])}
reads = []


def _fake(days, leagues=None, complete=None):
    reads.append(len(days))
    if complete is not None:
        complete.update(d.strftime("%Y%m%d") for d in days)
    return []


_g, _m = tb.espn_games, tb.match_game
tb.espn_games, tb.match_game = _fake, (lambda *a, **k: None)
try:
    cl.espn_fill(st10, NOW)
    cl.espn_fill(st10, NOW)
finally:
    tb.espn_games, tb.match_game = _g, _m
ok("the second run re-reads nothing for a row already checked against settled dates",
   reads == [2], reads)

# ------------------------------------------------------------------ 4. no payload is persisted
_src = open("clv_ledger.py").read()
_fill = _src[_src.index("def espn_fill("):_src.index("# ----", _src.index("def espn_fill("))]
ok("espn_fill stores only date strings, never scoreboard payloads",
   "espn_done" in _fill and "events" not in _fill)
ok("the completeness set is passed to espn_games, not reconstructed locally",
   "complete=complete" in _fill)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
