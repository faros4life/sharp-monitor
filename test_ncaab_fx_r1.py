#!/usr/bin/env python3
"""ncaab_fx_r1: offline tests. No network, no state needed."""
import json
import ncaab_fx_r1 as m


def t_targets():
    A = [{"sport": "NCAAB", "book_key": "prophetx", "top25": False, "kind": "spr", "bet": "Duke -6.5",
          "price_after_fee": -110, "late": False, "confirmed_by": ["BetOnline"], "result": "W",
          "alert_utc": "2026-11-10T18:00:00Z", "start_utc": "2026-11-11T00:00:00Z", "game": "A vs B"},
         {"sport": "NCAAB", "book_key": "prophetx", "top25": False, "kind": "spr", "bet": "X -2",
          "price_after_fee": -110, "late": False, "result": "L",
          "alert_utc": "2026-11-09T18:00:00Z", "start_utc": "2026-11-10T00:00:00Z", "game": "C vs D"},
         {"sport": "NBA", "book_key": "prophetx", "top25": False, "kind": "spr", "bet": "Y -2", "result": "W",
          "price_after_fee": -110, "late": False, "alert_utc": "2026-11-09T18:00:00Z", "start_utc": "2026-11-10T00:00:00Z"}]
    rej = {f"sharp|{A[0]['alert_utc']}|{A[0]['game']}|{A[0]['bet']}|prophetx": "FIXTURE_OR_IDENTITY: no unique fixture: no fixture in any cache matches",
           f"sharp|{A[1]['alert_utc']}|{A[1]['game']}|{A[1]['bet']}|prophetx": "MISSING_HISTORY: fixture id1 has no cached Pinnacle history"}
    out = m.targets(A, rej)
    assert len(out) == 1 and out[0][0]["game"] == "A vs B"      # only the missing-fixture-list reason
    assert m.targets(A, {}) == []                               # nothing rejected that way -> no call
    assert m.window(out) == ("2026-11-11", "2026-11-11")


def t_window_is_one_range():
    rows = [({"start_utc": "2026-11-11T00:00:00Z"}, {}), ({"start_utc": "2026-11-03T00:00:00Z"}, {}),
            ({"start_utc": "2026-11-09T00:00:00Z"}, {})]
    assert m.window(rows) == ("2026-11-03", "2026-11-11")       # ONE call spans every date, not one per day
    assert m.window([]) == (None, None)


def t_fixtures_from():
    fx = m.fixtures_from([{"fixtureId": "id9", "startTime": "2026-11-11T00:00:00Z", "statusId": 3,
                           "participant1Name": "Duke", "participant2Name": "UNC", "tournamentId": 648,
                           "tournamentName": "NCAA"}, {"noId": 1}])
    assert set(fx) == {"id9"} and fx["id9"][1] == 648 and fx["id9"][0]["lg"] == "NCAAB"
    assert fx["id9"][0]["n1"] == "Duke" and "Duke" in fx["id9"][0]["p1"]


def t_guards():
    s = open("ncaab_fx_r1.py").read()
    assert 'store.get(TAG)' in s and "already ran - no call made" in s        # cannot repeat
    assert 'cl.can_bill(st, now, 1)' in s and "GateRefused" in s             # credit gate before any call
    assert s.count('cl.api("/fixtures", True') == 1                          # exactly one paid endpoint call
    assert 'cl.STATS["billable"] > BILL_CAP' in s                            # hard cap checked after
    assert 'hc.get_hist(fid, ["pinnacle"], start)' in s                      # history via the FREE path
    assert s.count("json.dump(") == 1 and 'open(OUT, "w")' in s              # the fixture store is the only write
    assert s.count("cl.STATE") == 1 and "tb.dec(json.load(open(cl.STATE)))" in s   # ledger state is READ, never written
    wf = open(".github/workflows/ncaab-fx-r1.yml").read()
    assert "ODDSPAPI_KEY" in wf and "ODDSPAPI_FREE_KEY" in wf
    assert "paper_clv_certify.py" in wf                                      # re-certify in the same run
    assert "oddspapi/fixtures_ncaab.json" in wf and "paper/clv_certified.json" in wf


for f in (t_targets, t_window_is_one_range, t_fixtures_from, t_guards):
    f()
print("ncaab_fx_r1 tests: OK")
