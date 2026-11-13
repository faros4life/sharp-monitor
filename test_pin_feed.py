#!/usr/bin/env python3
"""Guards for the odds_screen Pinnacle feed in nba_totals_model (Nov 13, 2026). Offline, no API."""
import json, os, sys, tempfile
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nba_totals_model as M

FAIL = []
def ck(n, got, want):
    if got != want: FAIL.append(f"{n}: got {got!r}, want {want!r}")

def feed(age_s=0, game_age_s=0, over=(224.0, -105), under=(224.0, -107), dup=False, lg="NBA"):
    now = datetime.now(timezone.utc).timestamp()
    g = {"away": "A Team", "home": "B Team", "lg": lg, "start": "2026-11-14T00:00:00Z",
         "upd": now - game_age_s, "books": {"pinnacle": {"t": {"Over": list(over), "Under": list(under)}}}}
    games = [g, dict(g)] if dup else [g]
    return {"updated_utc": datetime.fromtimestamp(now - age_s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "games": games}

def run(doc):
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd)
    json.dump(doc, open(p, "w"))
    old = M.ODDS_SCREEN; M.ODDS_SCREEN = p
    try: return M.pin_lines()
    finally: M.ODDS_SCREEN = old; os.unlink(p)

ck("fresh quote is served", len(run(feed())), 1)
r = run(feed())[frozenset(("A Team", "B Team"))]
ck("line preserved", r["line"], 224.0)
ck("AMERICAN odds preserved, not converted", (r["over"], r["under"]), (-105, -107))

ck("stale FILE serves nothing", run(feed(age_s=M.MAX_REF_AGE_S + 60)), {})
ck("stale GAME is dropped", len(run(feed(game_age_s=M.MAX_REF_AGE_S + 60))), 0)
ck("Over/Under on different numbers is not one line",
   len(run(feed(over=(224.0, -105), under=(225.0, -107)))), 0)
ck("duplicate team pair is dropped, never guessed", len(run(feed(dup=True))), 0)
ck("non-NBA rows ignored", len(run(feed(lg="NFL"))), 0)
ck("missing file yields no reference, not a crash", run({"games": []}), {})

# downstream maths must be untouched: a no-vig pair still sums to 1
p = run(feed())[frozenset(("A Team", "B Team"))]
tot = M.close_prob("Over", p["line"], p) + M.close_prob("Under", p["line"], p)
ck("close_prob still sums to 1", round(tot, 6), 1.0)

print(f"test_pin_feed: {'FAIL' if FAIL else 'PASS'}")
for f in FAIL: print("  " + f)
sys.exit(1 if FAIL else 0)
