#!/usr/bin/env python3
"""The fixture export must carry identity and close evidence - and no money.

Muse matches events by ID because team-name matching is where the misses happen (St Bonaventure).
So fixture_id and game_start are the point of the file, and the raw two-sided prices plus tick
ages are what let a V1-vs-snapshot gap be attributed rather than guessed at.
"""
import fixture_export as fe

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


rec = {"fixture": "fx123", "our_line": -6.5, "main_line": -7.5, "how": "own line", "age_min": 4,
       "clv": -0.0085, "clv_v2": None, "v2_unsupported": "no_mass_row: NCAAB spread 12",
       "alt_px": [1.8065, 2.04], "main_px": [1.9, 1.95], "ts_ages": [4.0, 4.2, 4.1, 4.4],
       "snap": {"game": "Robert Morris Colonials @ Toledo Rockets", "league": "NCAAB",
                "book": "Hard Rock", "bet": "Toledo Rockets -6.5 (-115)",
                "teams": [{"name": "Robert Morris Colonials"}, {"name": "Toledo Rockets"}],
                "placed": "2026-11-19T17:57:00Z", "settled": "2026-11-20T03:40:00Z",
                "stake": 230.0, "to_pay": 430.0, "profit": 200.0}}
r = fe.row("k", rec, {"fx123": {"id": "1a7893819f5b", "start": "2026-11-20T00:00:00Z"}})

ok("the fixture id is exported", r["fixture_id"] == "fx123")
ok("the OddsPapi event id is exported for ID-based matching", r["odds_api_event_id"] == "1a7893819f5b")
ok("the authoritative start comes from the fixture store", r["game_start"] == "2026-11-20T00:00:00Z")
ok("teams are listed for a fallback match", r["teams"] == ["Robert Morris Colonials", "Toledo Rockets"])
ok("the raw two-sided prices are exported, held side first", r["alt_px_decimal"] == [1.8065, 2.04])
ok("the main-line pair is exported too", r["main_px_decimal"] == [1.9, 1.95])
ok("the four tick ages are exported", r["tick_ages_min_before_start"] == [4.0, 4.2, 4.1, 4.4])
ok("CLV is a percentage, V1 and V2 separately", r["clv_v1_pct"] == -0.85 and r["clv_v2_pct"] is None)
ok("an unsupported V2 carries its reason", r["v2_unsupported"].startswith("no_mass_row"))

for m in ("stake", "to_pay", "profit", "payout", "balance", "pnl", "cost"):
    ok(f"NO MONEY: '{m}' is absent from the export", m not in r)
ok("no money value leaks under any key",
   not any(v in (230.0, 430.0, 200.0) for v in r.values() if isinstance(v, float)), r)

st = {"bets": {"a": rec, "b": {"snap": {}, "why": "no OddsPapi fixture matched"}},
      "fixtures": {"fx123": {"id": "1a7893819f5b", "start": "2026-11-20T00:00:00Z"}}}
b = fe.build(st)
ok("every ledger row is exported, scored or not", b["rows"] == 2)
ok("coverage counters are reported", b["with_fixture_id"] == 1 and b["with_raw_two_sided_prices"] == 1
   and b["with_tick_ages"] == 1, b)
ok("an unscored row keeps its reason instead of being dropped",
   b["data"][1]["not_scored_reason"] == "no OddsPapi fixture matched")
ok("the file states that matching is by id, not team name", "not on team name" in b["note"])

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
import sys as _sys
_sys.exit(1 if FAILED else 0)
