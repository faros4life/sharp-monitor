"""Synthetic tests for reporting_ledger.py. No secrets, no network."""
import os, sys
os.environ.setdefault("TRACKER_PASSPHRASE", "synthetic-test-only")
import reporting_ledger as rl

fails = []
def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(label)

L = {"version": 1, "events": [], "head": {}}
reg = {"orders": [{"key": "rule|NBA|a+b|total|UNDER", "source": "rules", "et_day": "2026-11-12",
                   "live_order": {"order_id": "x"}},
                  {"key": "board|NBA|c+d|side|c", "source": "board", "et_day": "2026-11-11"}],
       "fills": {"o1": {"state": "FILLED", "play_key": "rule|NBA|a+b|total|UNDER", "ts": "2026-11-12T23:00:00Z"},
                 "o2": {"state": "RESTING", "play_key": "board|x", "ts": "2026-11-13T15:00:00Z"}},
       "intents": [], "venue_ids": {}}
tracker = {"t1": {"source": "bot", "result": "W", "settled": "2026-11-13T04:30:00Z",
                  "ingest_checked": "2026-11-12T23:10:00Z", "lane_src": "registry-order-id"},
           "t2": {"source": "Peter", "result": "L", "settled": "2026-11-13T04:30:00Z"},
           "t3": {"source": "bot", "ingest_checked": "2026-11-14T20:00:00Z"}}
clv = {"t1": {"clv": 0.012}, "t2": {"clv": -0.02}}

n1 = rl.snapshot(L, reg, tracker, clv, "2026-11-15T15:00:00Z")
e1 = len(L["events"])
check("first snapshot records every record once", e1 == 2 + 2 + 2 + 1, e1)
check("manual bets are never copied as bot rows", not any(e["id"] == "t2" for e in L["events"]))
n2 = rl.snapshot(L, reg, tracker, clv, "2026-11-15T16:00:00Z")
check("an unchanged re-run appends nothing", len(L["events"]) == e1)
reg["fills"]["o2"]["state"] = "FILLED"
rl.snapshot(L, reg, tracker, clv, "2026-11-15T17:00:00Z")
vers = [e for e in L["events"] if e["kind"] == "fill" and e["id"] == "o2"]
check("a change appends a new version and keeps the old one",
      len(vers) == 2 and vers[0]["data"]["state"] == "RESTING" and vers[1]["data"]["state"] == "FILLED")
# the registry later prunes: the ledger must keep it
reg["orders"] = []; reg["fills"] = {}
rl.snapshot(L, reg, tracker, clv, "2026-11-17T01:00:00Z")
check("records pruned from the registry stay in the ledger",
      any(e["kind"] == "order" and "rule|" in e["id"] for e in L["events"]))
cur = rl.latest(L)
check("latest() keeps the FIRST-seen time across versions",
      cur[("fill", "o2")][0] == "2026-11-15T15:00:00Z" and cur[("fill", "o2")][1]["state"] == "FILLED")

D = rl.daily(L)
check("orders before 12 Nov ET are excluded", "2026-11-11" not in D)
check("order counted on its execution day", D["2026-11-12"]["orders"] == 1 and D["2026-11-12"]["orders_lane_rules"] == 1)
check("fill counted on its ET day (23:00Z is 18:00 ET same day)", D["2026-11-12"]["fill_FILLED"] == 1)
check("settlement at 04:30Z counts on the PREVIOUS ET day", D["2026-11-12"]["bot_settled"] == 1, dict(D["2026-11-12"]))
check("graded and CLV-certified counted", D["2026-11-12"]["bot_graded"] == 1 and D["2026-11-12"]["bot_clv_certified"] == 1)
check("an open bot row is counted open, not settled", D["2026-11-14"]["bot_open"] == 1 and D["2026-11-14"]["bot_settled"] == 0)
check("Project 1 first-seen stamps counted per day", D["2026-11-12"]["p1_first_seen"] == 1 and D["2026-11-14"]["p1_first_seen"] == 1)

src = open("reporting_ledger.py").read()
check("no executor import", "import executor" not in src and "from executor" not in src)
check("no registry write path is called", not any(w in src for w in ("_commit(", "record_fill(", "claim_", "_put(")))
check("no OddsPapi key referenced", "ODDSPAPI" not in src)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails)); sys.exit(1)
print("test_reporting_ledger: all passed")


# ---- lane counts from the stored row's verified fields, never a key prefix (Peter, 16 Nov)
def _lane_counts():
    L = {"version": 1, "events": [], "head": {}}
    now = "2026-11-13T12:00:00Z"
    rl.observe(L, "order", "o1", {"key": "NBA|A @ B|total|OVER", "source": "board", "et_day": "2026-11-13",
                                  "live_order": {"order_id": "c1", "status": "placed"}}, now)
    rl.observe(L, "order", "o2", {"key": "NBA|C @ D|total|UNDER", "source": "r1", "et_day": "2026-11-13",
                                  "live_order": {"order_id": "c2", "status": "placed"}}, now)
    rl.observe(L, "order", "o3", {"key": "NBA|E @ F|total|UNDER", "source": "muse", "et_day": "2026-11-13"}, now)
    rl.observe(L, "fill", "c1", {"state": "FILLED", "ts": now, "play_key": "NBA|A @ B|total|OVER"}, now)
    rl.observe(L, "fill", "c2", {"state": "PARTIAL", "ts": now, "play_key": "NBA|C @ D|total|UNDER"}, now)
    rl.observe(L, "fill", "zz", {"state": "FILLED", "ts": now, "play_key": "board|NBA|X"}, now)
    return rl.daily(L)["2026-11-13"]


D_ = _lane_counts()
assert D_["orders_lane_board"] == 1 and D_["orders_lane_r1"] == 1 and D_["orders_lane_?"] == 1, dict(D_)
assert D_["fill_lane_board"] == 1 and D_["fill_lane_r1"] == 1, dict(D_)
assert D_["fill_lane_?"] == 1, dict(D_)          # a fill with no matching order id is '?', even with a lane-prefixed play_key
print("lane counts from verified fields: ok")
