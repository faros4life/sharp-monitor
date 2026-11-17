#!/usr/bin/env python3
"""Alert-history integrity (Peter, 17 Nov 2026). The regressions are the real incident, two processes writing at
once, and a restart. Offline: no network, no repo state."""
import json
import os
import tempfile

import liq_history as lh

HOU = {"key": 'kalshi|{"market_ticker": "KXNBATOTAL-26NOV16HOUMIA-233"}', "alerted_utc": "2026-11-16T16:20:14Z",
       "league": "NBA", "market": "total", "side": "UNDER", "line": 232.5, "price_american": -108, "result": None}
BATCH = [{"key": f"kalshi|b{i}", "alerted_utc": "2026-11-16T15:45:44Z", "league": "NBA"} for i in range(5)]
OLDER = [{"key": f"kalshi|o{i}", "alerted_utc": "2026-11-16T14:55:54Z", "league": "NBA"} for i in range(2)]


def t_houston_miami_cannot_be_deleted():
    """The exact 16 Nov incident: a run publishes 6 alerts, a run on older state republishes without them."""
    with tempfile.TemporaryDirectory() as d:
        run_a = OLDER + BATCH + [HOU]                    # the 16:21:11 export
        run_b = OLDER                                    # the 16:22:46 export, from older state
        assert lh.record(d, run_a) == (8, 8)
        added, total = lh.record(d, run_b)
        assert (added, total) == (0, 8)                  # nothing added, nothing LOST
        store = lh.read(os.path.join(d, lh.HIST))
        assert lh.aid(HOU) in store                      # the alert the board froze a call on survives
        assert store[lh.aid(HOU)]["line"] == 232.5 and store[lh.aid(HOU)]["side"] == "UNDER"
        assert store[lh.aid(HOU)]["alerted_utc"] == "2026-11-16T16:20:14Z"   # original identity and timestamp


def t_simultaneous_writes_commute():
    """Two processes, either order, same result - and neither can drop the other's rows."""
    a = {lh.aid(x): x for x in BATCH + [HOU]}
    b = {lh.aid(x): x for x in OLDER + BATCH}
    assert lh.merge(a, b) == lh.merge(b, a)
    assert len(lh.merge(a, b)) == 8
    assert lh.merge(a, b, a) == lh.merge(a, b)           # idempotent: re-running changes nothing


def t_first_publication_wins():
    """A later pass never rewrites an original record."""
    first = dict(HOU)
    later = dict(HOU, line=999.5, side="OVER", result="W")
    m = lh.merge({lh.aid(first): first}, {lh.aid(later): later})
    assert m[lh.aid(HOU)]["line"] == 232.5 and m[lh.aid(HOU)]["side"] == "UNDER"


def t_restart_and_corruption():
    """A half-written final line (killed mid-write) must not cost the rest of the history."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, lh.HIST)
        lh.record(d, BATCH + [HOU])
        with open(p, "a") as fh:
            fh.write('{"key": "truncated", "alerted_')     # a kill mid-append
        store = lh.read(p)
        assert len(store) == 6 and lh.aid(HOU) in store
        assert lh.record(d, [HOU])[1] == 6                 # and the file is usable again, no duplicate
        assert lh.read(os.path.join(d, "nothing.jsonl")) == {}   # a missing file is empty, never fatal


def t_history_is_not_an_execution_feed():
    """Nothing that selects or places a bet may read the history."""
    for f in ("executor.py", "board_build.py", "agree_rules.py", "lanes.py", "book_live.py"):
        if os.path.exists(f):
            src = open(f).read()
            assert "history.jsonl" not in src and "liq_history" not in src, f
    mon = open("liquidity_monitor.py").read()
    assert mon.index("import liq_history") > mon.index("def main")      # recording only, inside main
    assert "lh.record(OUT_DIR, alerts)" in mon


def t_commit_steps_merge_not_replace():
    for wf, d in ((".github/workflows/liquidity-monitor.yml", "liquidity"),
                  (".github/workflows/liquidity-extra.yml", "liquidity-extra")):
        s = open(wf).read()
        assert f"python liq_history.py {d}/history.jsonl" in s
        assert s.index(f'cp -r "$RUNNER_TEMP/out/{d}" .') < s.index("python liq_history.py")   # merge AFTER the replace
        assert s.index("python liq_history.py") < s.index(f"git add -A {d}")                   # and BEFORE staging


def t_backfill_recovered_the_incident():
    """The committed history must still contain the alert that vanished from the live export."""
    store = lh.read("liquidity/history.jsonl")
    assert len(store) > 2000
    hit = [k for k in store if "HOUMIA-233" in k]
    assert len(hit) == 1, hit
    import board_build as bb
    live = {lh.aid(x) for x in bb.load()}
    assert hit[0] not in live                                  # gone from the live feeds, kept in history
    assert not (live - (store | lh.read("liquidity-extra/history.jsonl").keys()))   # history is a superset


for f in (t_houston_miami_cannot_be_deleted, t_simultaneous_writes_commute, t_first_publication_wins,
          t_restart_and_corruption, t_history_is_not_an_execution_feed, t_commit_steps_merge_not_replace,
          t_backfill_recovered_the_incident):
    f()
print("liq history tests: OK")
