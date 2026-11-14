"""Offline tests for Phase 1 forward-fill capture (P1-A lane by exact order id, P1-B write-once entry
provenance, P1-C identity at first observation). No network, no secrets, no live module touched."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import clv_basis as cb  # noqa: E402
import clv_ledger as cl  # noqa: E402
import registry as rg  # noqa: E402
import tracker_build as tb  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + ("" if cond else f"  [{detail}]"))


# ---- P1-A registry index
orders = [
    {"key": "board|NBA|A @ B|total|OVER", "live_order": {"order_id": "PX1", "client_id": "c1", "book": "prophetx"}},
    {"key": "rule|NFL|C @ D|side|C", "live_order": {"order_id": "PX2"}, "live_more": [{"order_id": "PX3"}]},
    {"key": "r1|NHL|E @ F|ml|E", "live_order": {"order_id": "intent-c9"}},
    {"key": "lane2|NBA|G @ H|total|UNDER", "live_rest": {"order_id": "PX4"}},
    {"key": "board|NBA|X @ Y|total|OVER", "live_order": {"order_id": "DUP"}},
    {"key": "r1|NBA|X @ Y|total|OVER", "live_order": {"order_id": "DUP"}},
    {"key": "manualthing|x", "live_order": {"order_id": "PX9"}},
    {"key": "board|NBA|Z|total|OVER", "live_order": {"order_id": "SAME"}},
    {"key": "board|NBA|Z|total|OVER", "live_order": {"order_id": "SAME"}},
]
idx = rg.order_lane_index(orders)
ck("A index: venue order id -> lane", rg.lane_of("PX1", idx) == ("board", orders[0]["key"]))
ck("A index: client id also resolves", rg.lane_of("c1", idx)[0] == "board")
ck("A index: executor prefix 'rule' maps to lane 'rules'", rg.lane_of("PX2", idx)[0] == "rules")
ck("A index: live_more and live_rest ids resolve", rg.lane_of("PX3", idx)[0] == "rules" and rg.lane_of("PX4", idx)[0] == "lane2")
ck("A index: 'intent-' placeholder is not a venue id", rg.lane_of("intent-c9", idx) is None)
ck("A index: id under two lanes is ambiguous -> None", rg.lane_of("DUP", idx) is None)
ck("A index: same id twice under one lane stays resolved", rg.lane_of("SAME", idx)[0] == "board")
ck("A index: unknown key prefix is never a lane", rg.lane_of("PX9", idx) is None)
ck("A index: absent / empty ref -> None", rg.lane_of("", idx) is None and rg.lane_of(None, idx) is None and rg.lane_of("PX1", {}) is None)
ck("A index: empty input", rg.order_lane_index(None) == {} and rg.order_lane_index([{}]) == {})

# ---- P1-A lane_src on rows
b = {"order_ref": "PX1", "source": "bot"}
ck("A row: exact order id -> registry-order-id", tb.assign_lane_src(b, idx, rg.lane_of) == "registry-order-id"
   and b["lane"] == "board" and b["strategy_key"] == orders[0]["key"])
b = {"order_ref": "PX2", "source": "bot", "lane": "board"}
tb.assign_lane_src(b, idx, rg.lane_of)
ck("A row: exact lane wins over fuzzy and the fuzzy one is kept beside it", b["lane"] == "rules" and b["lane_fuzzy"] == "board")
b = {"order_ref": "NOPE", "source": "bot", "lane": "r1"}
ck("A row: unresolved id keeps the fuzzy lane, labelled fuzzy", tb.assign_lane_src(b, idx, rg.lane_of) == "fuzzy-join" and b["lane"] == "r1")
b = {"source": "bot"}
ck("A row: no id, no lane -> none (never a guess)", tb.assign_lane_src(b, idx, rg.lane_of) == "none" and "lane" not in b)
b = {"source": "Peter"}
ck("A row: manual source with no lane -> manual-source, lane left unset", tb.assign_lane_src(b, idx, rg.lane_of) == "manual-source" and "lane" not in b)
b = {"order_ref": "DUP", "source": "bot"}
ck("A row: ambiguous id is not resolved", tb.assign_lane_src(b, idx, rg.lane_of) == "none")

# ---- P1-C identity at first observation
full = {"league": "NBA", "game": "A @ B", "game_start": "2026-11-20T00:00:00Z", "bet": "Over 220.5"}
ck("C complete row has no gaps", tb.ingest_missing(full) == [], str(tb.ingest_missing(full)))
ck("C missing league/start reported", tb.ingest_missing(dict(full, league=None, game_start="")) == ["league", "game_start"])
ck("C free bet text is not flagged (parse_bet cannot tell; close_for reports line problems)", tb.ingest_missing(dict(full, bet="something odd")) == [])
ck("C nothing at all", tb.ingest_missing({}) == ["league", "game", "game_start", "bet"])
r = dict(full, league=None)
tb.stamp_new_row(r, "T1")
first = list(r["ingest_missing_first"])
r["league"] = "NBA"
tb.stamp_new_row(r, "T2")
ck("C first observation is written once and never overwritten", r["ingest_missing_first"] == first == ["league"] and r["ingest_checked"] == "T1")
ck("C the row itself is kept (no drop, no field removed)", r["game"] == "A @ B" and r["bet"] == "Over 220.5")

# ---- P1-B entry provenance
ck("B eff_dec_src mirrors eff_dec: stake/to_pay", cl.eff_dec_src({"stake": 100, "to_pay": 190, "book": "Novig"})[:2] == (1.9, "stake_to_pay"))
ck("B eff_dec_src: Novig stake/to_pay is fee-inclusive", cl.eff_dec_src({"stake": 100, "to_pay": 190, "book": "Novig"})[2] == "fee_inclusive_cost_payout")
ck("B eff_dec_src: price_af branch", cl.eff_dec_src({"price_af": -110, "book": "Novig"})[1:] == ("price_af", "bot_fill_after_fee"))
d_px, s_px, f_px = cl.eff_dec_src({"price": 100, "book": "ProphetX"})
ck("B eff_dec_src: ProphetX price carries the 2% settlement fee", s_px == "price_px_fee" and f_px == "px_settle_2pct" and abs(d_px - 1.98) < 1e-9)
ck("B eff_dec_src: Kalshi fee is never defaulted", cl.eff_dec_src({"stake": 50, "to_pay": 100, "book": "Kalshi"})[2] == "kalshi_unresolved")
ck("B eff_dec_src: no price -> all None", cl.eff_dec_src({"book": "Novig"}) == (None, None, None))
for sn in ({"stake": 100, "to_pay": 190, "book": "Novig"}, {"price_af": -110}, {"price": 120, "book": "ProphetX"}, {"price": -105, "book": "Hard Rock"}, {}):
    ck(f"B eff_dec_src value == eff_dec for {sorted(sn)}", cl.eff_dec_src(sn)[0] == cl.eff_dec(sn))

now = datetime(2026, 11, 20, 3, 0, tzinfo=timezone.utc)
start = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
rec = {}
cl.stamp_entry(rec, {"stake": 100, "to_pay": 190, "book": "Novig"}, {"age_min": 3}, start, now)
ck("B first scoring stores entry provenance", rec["entry_dec"] == 1.9 and rec["entry_src"] == "stake_to_pay"
   and rec["basis_version"] == cb.BASIS_VERSION and rec["entry_scored_at"] and "entry_drift_bp" not in rec, str(rec))
ck("B quote_ts = start - age_min", rec["quote_ts"] == cl.iso(start - timedelta(minutes=3)))
cl.stamp_entry(rec, {"stake": 100, "to_pay": 192, "book": "Novig"}, {"age_min": 3}, start, now)
ck("B re-score with a different entry: original kept, drift exposed", rec["entry_dec"] == 1.9 and rec["entry_dec_now"] == 1.92
   and abs(rec["entry_drift_bp"] - 105.3) < 0.1, str(rec))
cl.stamp_entry(rec, {"stake": 100, "to_pay": 190, "book": "Novig"}, {"age_min": 3}, start, now)
ck("B drift clears when the entry returns to the original", rec["entry_dec"] == 1.9 and "entry_drift_bp" not in rec)
rec2 = {}
cl.stamp_entry(rec2, {"book": "Novig"}, {"age_min": 3}, start, now)
ck("B no entry price -> nothing written", rec2 == {})
rec3 = {}
cl.stamp_entry(rec3, {"price": -110, "book": "Hard Rock"}, {"age_min": None}, start, now)
ck("B missing age -> quote_ts None, not invented", rec3["quote_ts"] is None)

# ---- legacy rows are read unchanged
legacy = {"clv": 0.012, "close_p": 0.53, "how": "own line", "snap": {"stake": 100, "to_pay": 190}}
before = dict(legacy)
ck("L eff_dec unchanged on a legacy snap", cl.eff_dec(legacy["snap"]) == 1.9)
ck("L a legacy row without Phase 1 fields is untouched by reading", legacy == before and "entry_dec" not in legacy)

# ---- nothing execution-facing changed
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_t = open(os.path.join(root, "tracker_build.py")).read()
src_r = open(os.path.join(root, "registry.py")).read()
ck("X Phase 1 code adds no network call in registry helpers",
   "_call(" not in src_r.split("def order_lane_index")[1].split("def lane_of")[0])

print(f"{len(OK)} passed, {len(BAD)} failed")
for x in BAD:
    print("FAIL", x)
sys.exit(1 if BAD else 0)
