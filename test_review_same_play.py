#!/usr/bin/env python3
"""ONE PLAY, WHATEVER THE FEED CALLS IT (Peter, Nov 23 2026). Offline.

The shared unit ledger keyed a play on the game text. The main feed (Lane 1, Board) writes
"Dallas Mavericks @ Utah Jazz"; the liquidity feed DOGS reads writes "Dallas vs Utah". Same side, same game, two
budgets. These tests pin the matcher that closes it, on three levels:
  1. names     - which two names are one team, and which are NOT (Kansas / Kansas State)
  2. real data - on today's feeds: no two different games are ever joined, every DOGS row finds its main-feed twin
  3. money     - through the real reservation code: a DOGS order on a play Board already holds is refused, partial
                 fills add up across spellings, another day is another game, unknown fails closed, and the home
                 runner (no matcher) still claims exactly the reservation the cloud made
"""
import collections
import copy
import itertools
import json
import os
import sys

os.environ["EXEC_UNIT_LEDGER"] = "on"

import executor as ex                     # noqa: E402
import liquidity_monitor as lm            # noqa: E402
import review_integration as ri           # noqa: E402
import review_unit_reservation as res     # noqa: E402

FAILED, RAN = [], []
HERE = os.path.dirname(os.path.abspath(__file__))


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


K = lambda lg, g, m, s: ri.key_from_registry(f"{lg}|{g}|{m}|{s}")   # noqa: E731

# --- 1. names ------------------------------------------------------------------------------------
SAME = [("dallas", "dallas mavericks", "NBA"), ("los angeles l", "los angeles lakers", "NBA"),
        ("los angeles c", "los angeles clippers", "NBA"), ("hawks", "atlanta", "NBA"),
        ("carolina: spread", "carolina hurricanes", "NHL"), ("ohio st.", "ohio state buckeyes", "NCAAF"),
        ("nc state", "n.c. state wolfpack", "NCAAF"), ("north carolina state", "nc state wolfpack", "NCAAF"),
        ("east carolina", "east carolina pirates", "NCAAF"), ("army", "army black knights", "NCAAF")]
DIFF = [("kansas", "kansas state", "NCAAF"), ("texas", "texas a&m", "NCAAF"), ("texas", "texas tech", "NCAAF"),
        ("miami", "miami (oh)", "NCAAF"), ("carolina", "east carolina", "NCAAF"), ("lakers", "los angeles clippers", "NBA"),
        ("los angeles l", "los angeles clippers", "NBA"), ("florida", "florida state", "NCAAF"),
        ("georgia southern", "georgia tech yellow jackets", "NCAAF"), ("", "dallas", "NBA")]
ok("names for one team are read as one team", all(ex._ledger_team_eq(a, b, lg) for a, b, lg in SAME),
   [(a, b) for a, b, lg in SAME if not ex._ledger_team_eq(a, b, lg)])
ok("a qualifier makes a DIFFERENT team (lm.toks drops 'state'; this does not)",
   not any(ex._ledger_team_eq(a, b, lg) for a, b, lg in DIFF), [(a, b) for a, b, lg in DIFF if ex._ledger_team_eq(a, b, lg)])
ok("symmetric", all(ex._ledger_team_eq(a, b, lg) == ex._ledger_team_eq(b, a, lg) for a, b, lg in SAME + DIFF))

A, B = K("NBA", "Dallas Mavericks @ Utah Jazz", "side", "Utah Jazz"), K("NBA", "Dallas vs Utah: Spread", "side", "Utah")
ok("same game, same side, two feeds: ONE play", ex._ledger_same_play(A, B) and ex._ledger_same_play(B, A))
ok("the other side is NOT the same play", not ex._ledger_same_play(A, K("NBA", "Dallas vs Utah", "side", "Dallas")))
ok("another market is not the same play", not ex._ledger_same_play(A, K("NBA", "Dallas vs Utah", "total", "OVER")))
ok("another sport is not the same play", not ex._ledger_same_play(A, K("NHL", "Dallas vs Utah", "side", "Utah")))
ok("totals: over is over across feeds, never under",
   ex._ledger_same_play(K("NBA", "Dallas Mavericks @ Utah Jazz", "total", "OVER"), K("NBA", "Utah vs Dallas", "total", "OVER"))
   and not ex._ledger_same_play(K("NBA", "Dallas Mavericks @ Utah Jazz", "total", "OVER"), K("NBA", "Utah vs Dallas", "total", "UNDER")))
ok("a number in the team name survives the key's number stripping (76ers)",
   ex._ledger_same_play(K("NBA", "Philadelphia vs Detroit: Spread", "side", "Philadelphia"),
                        K("NBA", "Philadelphia 76ers @ Detroit Pistons", "side", "Philadelphia 76ers")))
ok("home-and-home on consecutive nights is two games",
   not ex._ledger_same_play(K("NHL", "Colorado Avalanche @ Dallas Stars", "total", "OVER"),
                            K("NHL", "Dallas Stars @ Colorado Avalanche", "total", "OVER")))
ok("a malformed key matches nothing", not ex._ledger_same_play("nba|x", A) and not ex._ledger_same_play(None, A))

# --- 2. real data ---------------------------------------------------------------------------------
MAIN = [x for x in (json.load(open(os.path.join(HERE, "alerts.json"))).get("alerts") or []) if x.get("game") and x.get("start_utc")]
LIQ = [x for x in json.load(open(os.path.join(HERE, "liquidity", "alerts.json")))["alerts"] if isinstance(x, dict)]
byday = collections.defaultdict(set)
for x in MAIN:
    byday[(str(x.get("sport")).upper(), str(x["start_utc"])[:10])].add(str(x["game"]))
pairs = false_match = 0
for (lg, _day), games in byday.items():
    for g1, g2 in itertools.combinations(sorted(games), 2):
        pairs += 1
        false_match += ex._ledger_same_play(K(lg, g1, "total", "OVER"), K(lg, g2, "total", "OVER"))
ok(f"no two DIFFERENT games on one day are ever joined ({pairs} real pairs)", pairs > 5000 and false_match == 0, false_match)
n = hit = other = 0
for x in LIQ:
    if not (ex.dogs_qualifies(x) and ex.dogs_bet(x)):
        continue
    lg, g, day = str(x.get("league")).upper(), str(x["game"]), str(x.get("start_utc"))[:10]
    ta = lm.split_teams(g)
    for gg in byday.get((lg, day), ()):
        tb = lm.split_teams(gg)
        if not tb or not all(any(lm.toks(p, lg) & lm.toks(q, lg) for q in tb) for p in ta):
            continue
        i = [j for j in (0, 1) if lm.toks(str(x["side"]), lg) & lm.toks(tb[j], lg)]
        if len(i) != 1:
            continue
        n += 1
        kd = K(lg, g, "side", str(x["side"]))
        hit += ex._ledger_same_play(kd, K(lg, gg, "side", tb[i[0]]))
        other += ex._ledger_same_play(kd, K(lg, gg, "side", tb[1 - i[0]]))
        break
ok(f"every DOGS row with a main-feed twin that day is matched to it ({n} rows)", n >= 60 and hit == n, f"{hit}/{n}")
ok("...and never to the other side of that game", other == 0, other)


# --- 3. money: through the real reservation code ----------------------------------------------------
class Mem:
    def __init__(self, legs=None, seeded=True):
        self.st, self.v = {"legs": copy.deepcopy(legs or []), "seeded": seeded, "seed_note": "test"}, 1

    def read(self):
        return copy.deepcopy(self.st), self.v

    def write(self, st, v):
        if v != self.v:
            return False
        self.st, self.v = copy.deepcopy(st), self.v + 1
        return True


def leg(key, stake, american, unit, actor="sharp-monitor:live_order:prophetx", **kw):
    return dict({"key": key, "leg_id": "L|" + key, "order_id": "L|" + key, "status": "open", "asked_stake": stake,
                 "american": american, "unit": unit, "actor": actor, "dispatched": True}, **kw)


def attempt(store, key, stake, american, unit, book="kalshi", lid="new", path="live_order"):
    try:
        return ri.guard_or_refuse(store, key, lid, stake, american, unit, ri.actor_for("sharp-monitor", path, book))
    except Exception as e:   # the refusal IS the result under test
        return e


DAY = "2026-11-24T00:30:00Z"
BOARD = K("NBA", "Dallas Mavericks @ Utah Jazz", "side", "Utah Jazz")
DOGS = ri.key_from_registry("dogs|NBA|Dallas vs Utah: Spread|side|Utah")
ROWS = [{"key": "NBA|Dallas Mavericks @ Utah Jazz|side|Utah Jazz", "start_utc": DAY}]
PLAY = {"start_utc": "2026-11-24T00:35:00Z", "source": "dogs"}          # the liquidity feed's start, minutes off
try:
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(None)
    g = attempt(S, DOGS, 100, 120, 100.0)
    ok("THE DEFECT, pinned: with no matcher the DOGS order gets its own unit on a play Board already holds",
       isinstance(g, res.Grant), g)
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(ex._unit_ledger_matcher(PLAY, ROWS))
    g = attempt(S, DOGS, 100, 120, 100.0)
    ok("THE FIX: the same DOGS order is refused - Board already holds the unit", isinstance(g, res.ReservationRefused), g)
    ok("...and nothing was written for it", len(S.st["legs"]) == 1)
    g = attempt(S, ri.key_from_registry("dogs|NBA|Dallas vs Utah|side|Dallas"), 100, 120, 100.0)
    ok("the OTHER side is a different budget here (first-side-stays is the executor's rule, not the ledger's)", isinstance(g, res.Grant), g)

    # the reverse order: DOGS first, then Lane 1 / Board on the main feed's spelling
    S = Mem([leg(DOGS, 100, 120, 100.0, actor="sharp-monitor:live_order:kalshi")])
    res.set_play_matcher(ex._unit_ledger_matcher({"start_utc": DAY}, [{"key": "NBA|Dallas vs Utah: Spread|side|Utah", "start_utc": DAY}]))
    ok("DOGS filled first: a Board order on the same side is refused", isinstance(attempt(S, BOARD, 300, 120, 300.0), res.ReservationRefused))

    # partial fills add up ACROSS spellings, each at its own unit
    S = Mem([leg(DOGS, 50, 120, 100.0, actor="sharp-monitor:live_order:kalshi")])                 # half of DOGS' $100 unit
    res.set_play_matcher(ex._unit_ledger_matcher({"start_utc": DAY}, [{"key": "NBA|Dallas vs Utah: Spread|side|Utah", "start_utc": DAY}]))
    ok("half a unit used by DOGS: a FULL Board unit is refused", isinstance(attempt(S, BOARD, 300, 120, 300.0, lid="b1"), res.ReservationRefused))
    ok("...half a Board unit fits", isinstance(attempt(S, BOARD, 150, 120, 300.0, lid="b2"), res.Grant))
    ok("...and then nothing more on either spelling",
       isinstance(attempt(S, BOARD, 30, 120, 300.0, lid="b3"), res.ReservationRefused)
       and isinstance(attempt(S, DOGS, 10, 120, 100.0, lid="d3", book="novig", path="rest_bid"), res.ReservationRefused))

    # another day is another game
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(ex._unit_ledger_matcher({"start_utc": "2026-11-29T00:30:00Z"}, ROWS))
    ok("the same two teams five days later is a new play", isinstance(attempt(S, DOGS, 100, 120, 100.0), res.Grant))
    res.set_play_matcher(ex._unit_ledger_matcher({"start_utc": "2026-11-29T00:30:00Z"}, ROWS))
    ok("...but the EXACT same key always counts, whatever the day says (as it always did)",
       isinstance(attempt(Mem([leg(BOARD, 300, 120, 300.0)]), BOARD, 300, 120, 300.0, lid="again"), res.ReservationRefused))

    # the day cannot be read: fail closed
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(ex._unit_ledger_matcher(PLAY, []))
    ok("an old leg with no day at all is COUNTED (unknown is exposure)", isinstance(attempt(S, DOGS, 100, 120, 100.0), res.ReservationRefused))
    S = Mem([leg(BOARD, 300, 120, 300.0, placed_utc="2026-11-23T20:00:00Z")])
    ok("a leg outside the registry window is dated by when it was placed: the day before the game counts",
       isinstance(attempt(S, DOGS, 100, 120, 100.0), res.ReservationRefused))
    S = Mem([leg(BOARD, 300, 120, 300.0, placed_utc="2026-11-10T20:00:00Z")])
    ok("...and one placed two weeks earlier is an older game", isinstance(attempt(S, DOGS, 100, 120, 100.0), res.Grant))
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(ex._unit_ledger_matcher({"start_utc": None}, ROWS))
    ok("a play with no start time matches on teams alone", isinstance(attempt(S, DOGS, 100, 120, 100.0), res.ReservationRefused))

    def _boom(_leg, _key):
        raise RuntimeError("team tables unreadable")
    S = Mem([leg(BOARD, 300, 120, 300.0)])
    res.set_play_matcher(_boom)
    g = attempt(S, DOGS, 100, 120, 100.0)
    ok("a matcher that fails is never read as 'no match': no grant, nothing written",
       not isinstance(g, res.Grant) and len(S.st["legs"]) == 1, g)

    # both executors: the cloud reserves under ITS spelling, the runner (no matcher) claims exactly that
    S = Mem([])
    res.set_play_matcher(ex._unit_ledger_matcher(PLAY, []))
    g = attempt(S, DOGS, 100, 120, 100.0, book="novig", lid="live_order_other|x", path="live_order_other")
    ri.authorized_stake(S, g, 100)
    res.set_play_matcher(None)                                   # the home runner installs none
    runner_key = ri.key_from_registry("NBA|Dallas vs Utah: Spread|side|Utah")      # IN_KEY = derive_key, no lane prefix
    ok("the runner's key for the dispatched order is the cloud's key (lane prefix dropped)", runner_key == DOGS)
    ok("runner claims the cloud's reservation", res.claim_dispatched(S, runner_key, 100, "novig", "cid-1") == "live_order_other|x")
    try:
        res.claim_dispatched(S, runner_key, 100, "novig", "cid-2")
        dup = False
    except res.ReservationRefused:
        dup = True
    ok("a duplicate dispatch is refused at the runner", dup)
    res.set_play_matcher(ex._unit_ledger_matcher(PLAY, []))
    ok("and the cloud then refuses Board on the main feed's spelling of that play",
       isinstance(attempt(S, BOARD, 300, 120, 300.0, lid="board"), res.ReservationRefused))
finally:
    res.set_play_matcher(None)

# --- 4. wiring ---------------------------------------------------------------------------------------
SRC = open(os.path.join(HERE, "executor.py")).read()
G = SRC.split("def _unit_ledger_guard(")[1].split("\ndef live_order(")[0]
ok("the enforcing guard installs the matcher BEFORE it reserves",
   "set_play_matcher(_unit_ledger_matcher(p, _rows))" in G
   and G.index("set_play_matcher(") < G.index("ri.guard_or_refuse(store, key"))
ok("...and refuses when the order rows it needs cannot be read", "order rows unreadable - cannot match this play across feeds" in G)
RS = open(os.path.join(HERE, "review_unit_reservation.py")).read()
ok("the budget is read through the matcher in both places it is summed",
   "if same_play(l, key)]" in RS and "if not same_play(leg, key):" in RS)
ok("an exact key match never consults the matcher", RS.split("def same_play(")[1].split("def _legs(")[0].index('leg.get("key") == key')
   < RS.split("def same_play(")[1].split("def _legs(")[0].index('_MATCH["fn"]'))

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
