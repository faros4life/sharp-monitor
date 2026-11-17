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


for f in (t_gate, t_plays_same_key, t_wiring):
    f()
print("board v4 tests: OK")
