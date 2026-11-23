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
o2 = [{"key": "board|NBA|A|total|OVER", "live_order": {"order_id": "Q1", "book": "prophetx"}},
      {"key": "board|NBA|B|total|UNDER", "live_order": {"order_id": "Q1", "book": "prophetx"}}]
ck("A R2: same id, same lane, two strategies -> None", rg.lane_of("Q1", rg.order_lane_index(o2)) is None)
o3 = [{"key": "board|NBA|A|total|OVER", "live_order": {"order_id": "Q2", "book": "ProphetX"}},
      {"key": "r1|NBA|B|total|UNDER", "live_order": {"order_id": "Q2", "book": "novig"}}]
i3 = rg.order_lane_index(o3)
ck("A R2: cross-venue id collision resolves per venue", rg.lane_of("Q2", i3, "ProphetX") == ("board", o3[0]["key"])
   and rg.lane_of("Q2", i3, "Novig")[0] == "r1")
ck("A R2: cross-venue collision with no venue given -> None", rg.lane_of("Q2", i3) is None)
ck("A R2: venue mismatch -> None (never a cross-venue join)", rg.lane_of("Q2", i3, "Kalshi") is None)
o4 = [{"key": "board|NBA|A|total|OVER", "live_order": {"order_id": "Q3"}}]
ck("A R2: a claim with no recorded venue still resolves", rg.lane_of("Q3", rg.order_lane_index(o4), "ProphetX")[0] == "board")
ck("A index: same id twice under one lane stays resolved", rg.lane_of("SAME", idx)[0] == "board")
ck("A index: unknown key prefix is never a lane", rg.lane_of("PX9", idx) is None)
ck("A index: absent / empty ref -> None", rg.lane_of("", idx) is None and rg.lane_of(None, idx) is None and rg.lane_of("PX1", {}) is None)
ck("A index: empty input", rg.order_lane_index(None) == {} and rg.order_lane_index([{}]) == {})

# ---- lane from the registry row's SOURCE (executor.ledger_row stores key = derive_key(play), no lane prefix)
real = [{"key": "NBA|A @ B|total|OVER", "source": "board", "live_order": {"order_id": "S1", "book": "prophetx"}},
        {"key": "NFL|C @ D|side|C", "source": "r1", "live_order": {"order_id": "S2", "book": "prophetx"}},
        {"key": "NBA|E @ F|total|UNDER", "source": "rules", "live_order": {"order_id": "S3", "book": "prophetx"}},
        {"key": "NBA|G @ H|total|UNDER", "source": "muse", "live_order": {"order_id": "S4", "book": "prophetx"}},
        {"key": "board|NBA|I @ J|total|OVER", "source": "r1", "live_order": {"order_id": "S5", "book": "prophetx"}},
        {"key": "r1|NBA|K @ L|total|OVER", "source": "", "live_order": {"order_id": "S6", "book": "prophetx"}}]
ri = rg.order_lane_index(real)
ck("A source: board / r1 / rules resolve from the row's source field", rg.lane_of("S1", ri, "ProphetX")[0] == "board"
   and rg.lane_of("S2", ri, "ProphetX")[0] == "r1" and rg.lane_of("S3", ri, "ProphetX")[0] == "rules")
ck("A source: unknown legacy source is NOT defaulted to a lane", rg.lane_of("S4", ri, "ProphetX") is None)
ck("A source: key prefix and source that disagree prove nothing", rg.lane_of("S5", ri, "ProphetX") is None)
ck("A source: key prefix alone still works", rg.lane_of("S6", ri, "ProphetX")[0] == "r1")
ck("A source: row_lane is case-insensitive on source", rg.row_lane({"key": "x", "source": "Board"}) == "board")

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

# ---- tracker KEY_LANE from the registry row (not executor.lane_of)
tb.KEY_LANE.clear(); tb.KEY_LANE_CONFLICT.clear()
ck("K board source -> BOARD V4 (executor.lane_of would have raised on live=True)",
   tb.key_lane_put({"key": "NBA|A @ B|total|OVER", "source": "board", "live": True}) == "BOARD V4")
ck("K r1 / rules", tb.key_lane_put({"key": "NFL|C @ D|side|C", "source": "r1", "live": False}) == "R1"
   and tb.key_lane_put({"key": "NBA|E @ F|total|UNDER", "source": "rules", "live": True}) == "LANE 1")
ck("K unknown legacy source labels nothing (no LANE 1 default)", tb.key_lane_put({"key": "NBA|G @ H|total|OVER", "source": "muse"}) is None
   and "NBA|G @ H|total|OVER" not in tb.KEY_LANE)
tb.key_lane_put({"key": "NBA|A @ B|total|OVER", "source": "r1"})
ck("K one key under two lanes -> conflict, unlabelled", "NBA|A @ B|total|OVER" not in tb.KEY_LANE and "NBA|A @ B|total|OVER" in tb.KEY_LANE_CONFLICT)
ck("K a conflicted key stays conflicted", tb.key_lane_put({"key": "NBA|A @ B|total|OVER", "source": "board"}) is None)
_bm = tb.bot_match
tb.bot_match = lambda b, keys: next(iter(keys)) in b["_m"]
try:
    ck("K row matching one lane's keys -> that lane", tb.bot_row_lane({"_m": {"NFL|C @ D|side|C"}}) == "R1")
    ck("K row matching two lanes -> None", tb.bot_row_lane({"_m": {"NFL|C @ D|side|C", "NBA|E @ F|total|UNDER"}}) is None)
    ck("K row matching a conflicted key -> None", tb.bot_row_lane({"_m": {"NBA|A @ B|total|OVER"}}) is None)
    ck("K row matching nothing -> None", tb.bot_row_lane({"_m": set()}) is None)
finally:
    tb.bot_match = _bm
    tb.KEY_LANE.clear(); tb.KEY_LANE_CONFLICT.clear()
src_tb = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracker_build.py")).read()
ck("K tracker no longer labels lanes with executor.lane_of", "ex.lane_of(" not in src_tb)

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
NV = lambda pay: {"stake": 100, "to_pay": pay, "book": "Novig"}
rec = {}
st0 = cl.stamp_entry(rec, NV(190), {"age_min": 3}, start, now)
ck("B first scoring stores entry provenance", st0 == "ok" and rec["entry_dec"] == 1.9 and rec["entry_src"] == "stake_to_pay"
   and rec["basis_version"] == cb.BASIS_VERSION and rec["entry_scored_at"] == cl.iso(now) and "entry_drift_bp" not in rec, str(rec))
ck("B quote time is labelled DERIVED, never observed", rec["quote_ts_derived"] == cl.iso(start - timedelta(minutes=3))
   and rec["quote_ts_basis"].startswith("derived") and "quote_ts" not in rec)
later = now + timedelta(hours=2)
cl.stamp_entry(rec, NV(192), {"age_min": 3}, start, later)
ck("B re-score with a different entry: original kept, drift exposed", rec["entry_dec"] == 1.9 and rec["entry_dec_now"] == 1.92
   and abs(rec["entry_drift_bp"] - 105.3) < 0.1 and rec["entry_prov_status"] == "ok_drift", str(rec))
ck("B entry_scored_at is the FIRST scoring, not rewritten", rec["entry_scored_at"] == cl.iso(now))
cl.stamp_entry(rec, NV(190), {"age_min": 3}, start, later + timedelta(hours=1))
ck("B R3: return to original clears CURRENT drift only", rec["entry_dec"] == 1.9 and "entry_drift_bp" not in rec and "entry_dec_now" not in rec)
ck("B R3: sticky drift evidence survives the return", rec["entry_drift_count"] == 1 and rec["entry_drift_first_seen"] == cl.iso(later)
   and abs(rec["entry_drift_max_bp"] - 105.3) < 0.1, str(rec))
cl.stamp_entry(rec, NV(188), {"age_min": 3}, start, later + timedelta(hours=2))
ck("B R3: repeat drift counts again, keeps first-seen and the max |drift|", rec["entry_drift_count"] == 2
   and rec["entry_drift_first_seen"] == cl.iso(later) and abs(rec["entry_drift_max_bp"] - 105.3) < 0.1)
cl.stamp_entry(rec, NV(196), {"age_min": 3}, start, later + timedelta(hours=3))
ck("B R3: max |drift| grows when a larger drift is seen", rec["entry_drift_count"] == 3 and rec["entry_drift_max_bp"] > 300)
rec2 = {}
ck("B R1: no entry price -> explicit status, nothing else written", cl.stamp_entry(rec2, {"book": "Novig"}, {"age_min": 3}, start, now)
   == "no_entry_price" and rec2 == {"entry_prov_status": "no_entry_price"})
rec3 = {}
cl.stamp_entry(rec3, {"price": -110, "book": "Hard Rock"}, {"age_min": None}, start, now)
ck("B missing age -> no quote time, labelled unavailable", rec3["quote_ts_derived"] is None and rec3["quote_ts_basis"].startswith("unavailable"))

# R1 through the real call site: an exception inside stamp_entry must leave a durable status and a count
src_l = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clv_ledger.py")).read()
site = src_l[src_l.index("PROV[stamp_entry("):src_l.index("PROV[\"failed\"] += 1")]
ck("B R1: call site records failure status (not a bare pass)", 'rec["entry_prov_status"] = f"failed: {type(_pe).__name__}"' in site
   and "pass" not in site)
_orig = cl.eff_dec_src
cl.eff_dec_src = lambda s_: (_ for _ in ()).throw(KeyError("boom"))
rec4, P = {}, cl.PROV.copy()
try:
    try:
        cl.PROV[cl.stamp_entry(rec4, NV(190), {"age_min": 3}, start, now)] += 1
    except Exception as _pe:
        rec4["entry_prov_status"] = f"failed: {type(_pe).__name__}"
        cl.PROV["failed"] += 1
finally:
    cl.eff_dec_src = _orig
ck("B R1: injected exception -> 'failed: KeyError' status and a counted failure, no private text",
   rec4 == {"entry_prov_status": "failed: KeyError"} and cl.PROV["failed"] == P["failed"] + 1)

# ---- R4 the actual ledger snap-copy path
legacy_snap = {"book": "ProphetX", "game": "A @ B"}
ck("R4 legacy tracker row (no lane_src) copies nothing", cl.copy_phase1(dict(legacy_snap), {"lane": "board", "order_ref": "X"}, "T")
   == "legacy")
ls = dict(legacy_snap)
cl.copy_phase1(ls, {"lane": "board", "order_ref": "X"}, "T")
ck("R4 legacy snap left byte-identical", ls == legacy_snap)
sn = {}
ck("R4 first Phase 1 copy", cl.copy_phase1(sn, {"lane_src": "fuzzy-join", "lane": "r1", "order_ref": "X"}, "T1") == "first"
   and sn["lane"] == "r1" and sn["lane_src"] == "fuzzy-join")
ck("R4 sideways change is NOT written", cl.copy_phase1(sn, {"lane_src": "fuzzy-join", "lane": "board"}, "T2") == "kept" and sn["lane"] == "r1")
ck("R4 downgrade is NOT written", cl.copy_phase1(sn, {"lane_src": "none"}, "T3") == "kept" and sn["lane_src"] == "fuzzy-join")
ck("R4 upgrade to exact is written WITH an audit entry",
   cl.copy_phase1(sn, {"lane_src": "registry-order-id", "lane": "board", "strategy_key": "board|k", "order_ref": "X"}, "T4") == "upgraded"
   and sn["lane"] == "board" and sn["lane_history"][0]["from"]["lane"] == "r1" and sn["lane_history"][0]["at"] == "T4")
ck("R4 an exact lane is never replaced", cl.copy_phase1(sn, {"lane_src": "registry-order-id", "lane": "r1"}, "T5") == "kept"
   and sn["lane"] == "board" and len(sn["lane_history"]) == 1)
s5 = {"ingest_missing_first": ["league"]}
cl.copy_phase1(s5, {"lane_src": "none", "ingest_missing_first": [], "ingest_checked": "T"}, "T")
ck("R4 ingest first-observation is never overwritten", s5["ingest_missing_first"] == ["league"] and s5["ingest_checked"] == "T")
src_main = src_l[src_l.index("# 1) capture"):src_l.index("# 1b)")]
ck("R4 the ledger capture loop calls copy_phase1 and copies no Phase 1 field directly",
   "copy_phase1(snap, b" in src_main and not any(f'"{f}"' in src_main for f in ("order_ref", "lane_src", "strategy_key")))

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
