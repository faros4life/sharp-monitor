#!/usr/bin/env python3
"""Board V4 gate (Peter, 17 Nov 2026): offline tests. No network, no orders."""
import copy
import os
from datetime import datetime, timedelta, timezone

os.environ.pop("EXEC_BOARD_V4", None)
import executor as ex

GOOD = {"book": "kalshi", "league": "NBA", "market": "total", "side": "UNDER", "line": 224.5, "rule_met": True,
        "second_book": ["novig"], "second_book_status": "ok", "alerted_utc": "2026-11-17T15:00:00Z",
        "depth_by_book": {"kalshi": {"this_side": 40000}, "novig": {"this_side": 15000, "label": "Under 224.5",
                                                                  "price": 0.51, "heavier_side": True}}}


def mut(**kw):
    x = copy.deepcopy(GOOD)
    for k, v in kw.items():
        if k == "nv":
            x["depth_by_book"]["novig"].update(v)
        else:
            x[k] = v
    return x


def t_gate():
    assert ex.BOARD_V4 is False                                   # off by default
    ok, why, ev = ex.board_v4(GOOD)
    assert ok and why is None and ev["book"] == "novig" and ev["line"] == 224.5 and ev["trigger"] == "kalshi"
    bad = [mut(rule_met=False), mut(rule_met="true"), mut(rule_met=None), mut(second_book_status="none_10k"),
           mut(second_book=[]), mut(second_book="novig"), mut(depth_by_book=None), mut(line=None),
           mut(second_book=["kalshi"]),                            # the trigger book cannot confirm itself
           mut(second_book=["mystery"]),                           # unknown book
           mut(nv={"this_side": 9999}),                            # under $10k
           mut(nv={"heavier_side": False}), mut(nv={"heavier_side": None}),
           mut(nv={"label": "Under 225.5"}),                       # partial match: different line
           mut(nv={"label": "Under"}),                             # no line in the evidence
           mut(nv={"price": None}), mut(nv={"price": 0}), mut(nv={"this_side": None}),
           mut(book=None), None, {}]
    for x in bad:
        ok, why, ev = ex.board_v4(x)
        assert ok is False and why and ev is None, x
    # a second, valid book rescues a failing first one; Polymarket Global may confirm
    x = mut(second_book=["mystery", "polymarket"])
    x["depth_by_book"]["polymarket"] = {"this_side": 20000, "label": "Under 224.5", "price": 0.5, "heavier_side": True}
    assert ex.board_v4(x)[0] and ex.board_v4(x)[2]["book"] == "polymarket"


def t_plays_same_key():
    """V4 never creates a second play: one row per signal, key identical with the gate on or off."""
    import board_build as bb
    now = datetime(2026, 11, 17, 16, 0, tzinfo=timezone.utc)
    def row(x):
        return {"at": now - timedelta(minutes=20), "tag": "PLAY", "status": "still there", "x": x}
    base = dict(GOOD, game="Raptors vs. 76ers", start_utc="2026-11-18T00:00:00Z", price_american=-108)
    rows = [row(base), row(dict(base, game="Lakers vs. Bucks", rule_met=False, second_book=[], second_book_status="no_match"))]
    orig, origv = bb.build, ex.BOARD_V4
    bb.build = lambda upcoming=True: (None, rows, None)
    try:
        out = {}
        for v in (False, True):
            ex.BOARD_V4 = v
            out[v] = ex.board_plays(now)
    finally:
        bb.build, ex.BOARD_V4 = orig, origv
    assert [p["play_key"] for p in out[False]] == [p["play_key"] for p in out[True]] and len(out[True]) == 2
    assert all(p["play_key"].startswith("board|") for p in out[True])
    assert [p["board_v4"]["ok"] for p in out[True]] == [True, False] and out[True][1]["board_v4"]["why"]


def t_lane_name_follows_the_live_rule():
    """Peter, 17 Nov: a notification that says BOARD V3 while V4 is deciding names a rule that did not place the bet.
    The label follows the switch; the lane KEY, caps and accounting do not change."""
    import importlib
    import os
    r = {"live": {"lane": "board"}, "play": {"source": "board"}}
    r1 = {"live": {"lane": "r1"}, "play": {"source": "r1"}}
    prev = os.environ.get("EXEC_BOARD_V4")
    try:
        for val, want in (("off", "[BOARD V3] "), ("on", "[BOARD V4] ")):
            os.environ["EXEC_BOARD_V4"] = val
            m = importlib.reload(ex)
            assert m.lane_tag(r) == want, (val, m.lane_tag(r))
            assert m.lane_tag(r1) == "[R1] "                                  # other lanes unaffected
            # LANE_NAME stays the canonical map other modules check; only the message changes
            # Nov 22: NCS (NCAAB spreads) joined the map. Kept as an EXACT comparison on purpose -
            # a lane that appears here without being wired everywhere else is the failure this guards.
            assert m.LANE_NAME == {"board": "BOARD V3", "r1": "R1", "lane2": "LANE 2",
                                   "rules": "PHASE 1", "ncs": "NCS"}
            assert m.BOARD_UNIT == 200.0 and "board|" in m.LANE_PREFIXES      # unit and play-key prefix untouched
    finally:
        if prev is None:
            os.environ.pop("EXEC_BOARD_V4", None)
        else:
            os.environ["EXEC_BOARD_V4"] = prev
        importlib.reload(ex)


def t_wiring():
    s = open("executor.py").read()
    i = s.index('elif p.get("source") == "board":')
    j = s.index('elif p.get("source") == "r1":', i)
    blk = s[i:j]
    g = blk.index('if BOARD_V4 and (p.get("board_v4") or {}).get("ok") is not True:')
    assert g < blk.index('r["live"] = {"go": True')          # the gate is decided before any go
    assert blk.count('r["live"] = {"go": True') == 1 and "if not why and" in blk
    assert 'EXEC_BOARD_V4: ${{ vars.EXEC_BOARD_V4 || \'off\' }}' in open(".github/workflows/executor-dry-run.yml").read()
    for name in ("BOARD_UNIT = 200.0", "BOARD_CONFIRM_MIN = 15"):
        assert name in s


def t_strength_logging_only():
    import json
    from datetime import datetime as dt, timezone as tz
    x = mut(norm_by_book={"novig": {"normal": 8000}, "kalshi": {"normal": 90000}}, second_book_fresh=True)
    r = ex.board_v4_strength(x)
    assert len(r) == 1 and r[0] == {"book": "novig", "league": "NBA", "market": "total", "confirming": True, "size": 15000,
                                    "normal": 8000, "ratio": 1.88, "money": "NEW", "pass_1x": True, "pass_2x": False}
    assert ex.board_v4_strength(mut(second_book_fresh=False))[0]["money"] == "RESTING"
    assert ex.board_v4_strength(mut())[0]["money"] == "UNKNOWN"                     # freshness not recorded
    y = mut(second_book=["novig", "prophetx"], second_book_fresh=True)             # two books, one flag: do not infer NEW
    y["depth_by_book"]["prophetx"] = {"this_side": 12000, "label": "Under 224.5", "price": 0.5, "heavier_side": True}
    assert {v["money"] for v in ex.board_v4_strength(y)} == {"UNKNOWN"}
    z = ex.board_v4_strength(mut())[0]                                              # no normal: ratio and gates unknown
    assert z["normal"] is None and z["ratio"] is None and z["pass_1x"] is None and z["pass_2x"] is None
    w = ex.board_v4_strength(mut(rule_met=False, second_book=[], second_book_status="none_10k", nv={"this_side": 4000}))
    assert w[0]["confirming"] is False and w[0]["size"] == 4000 and w[0]["money"] == "UNKNOWN"   # rejected signals log too
    assert ex.board_v4_strength(None) == [] and ex.board_v4_strength({"depth_by_book": "x"}) == []
    # the gate ignores strength: identical decision with or without normals / freshness
    assert ex.board_v4(x)[:2] == ex.board_v4(GOOD)[:2] and ex.board_v4(mut(nv={"this_side": 9999}, norm_by_book={"novig": {"normal": 1}}))[0] is False
    src = open("executor.py").read()
    assert src.count("board_v4_strength(") == 2                                    # defined once, called once (in board_plays)
    # persists on the ledger row and survives JSON
    p = {"play_key": "board|k", "source": "board", "sport": "NBA", "game": "A vs. B", "bet": "Under 224.5 (-108)",
         "start_utc": "2026-11-18T00:00:00Z", "alert_utc": "2026-11-17T15:00:00Z",
         "board_v4": dict(zip(("ok", "why", "evidence"), ex.board_v4(x)), strength=r)}
    lr = json.loads(json.dumps(ex.ledger_row({"play": p, "entry": {}, "verdict": "SKIP"}, dt.now(tz.utc)), default=str))
    assert lr["board_v4"]["strength"] == r and lr["board_v4"]["ok"] is True and lr["board_v4_gate"] is False


for f in (t_gate, t_plays_same_key, t_lane_name_follows_the_live_rule, t_wiring, t_strength_logging_only):
    f()
print("board v4 tests: OK")
