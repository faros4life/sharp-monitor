import ast
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_audit_core as c  # noqa: E402

R = lambda **k: {"result": "W", "stake": 100, "profit": 90, "game": "g", "bet": "b", "book": "ProphetX", **k}
IDX = {"A": [("prophetx", "K1", "R1")], "B": [("prophetx", "K1", "R1")], "C": [("prophetx", "K2", "PHASE 1")],
       "X": [("prophetx", "K3", "R1"), ("prophetx", "K4", "PHASE 1")], "N": [("novig", "K9", "BOARD V3")]}
run = lambda rows: c.build(rows, IDX)


def t_finite_only():
    assert c.verified_money(R())
    for bad in (None, 0, -5, float("inf"), float("-inf"), float("nan"), True, "x"):
        assert not c.verified_money(R(stake=bad)), bad
    for bad in (None, float("inf"), float("nan"), True):
        assert not c.verified_money(R(profit=bad)), bad
    assert not c.verified_money(R(result=None)) and not c.verified_money(R(result="X"))


def t_roi_is_dollars_not_rate_sum():
    a = c._agg([R(), R(stake=10, profit=-10, result="L")])
    assert a["risked"] == 110 and a["net"] == 80 and a["roi_pct"] == round(80 / 110 * 100, 2)


def t_unverified_visible_not_zeroed():
    a = c._agg([R(), R(stake=None), R(profit=float("inf"))])
    assert a["settled"] == 3 and a["verified_money"] == 1 and a["unverified_money"] == 2 and a["risked"] == 100


def t_halves_cut_before_money_exclusion():
    rows = [R(game_start=f"2026-11-0{i}", stake=None if i == 1 else 100) for i in range(1, 5)]
    r = c.bucket_report(c.consolidate([(x, "B", None) for x in rows])["B"])
    assert r["H1"]["settled"] == 2 and r["H2"]["settled"] == 2 and r["H1"]["unverified_money"] == 1


def t_no_time_excluded_and_counted():
    ps = c.consolidate([(R(game_start="2026-11-01"), "B", None), (R(), "B", None)])["B"]
    r = c.bucket_report(ps); assert r["settled_no_time"] == 1 and r["H1"]["settled"] + r["H2"]["settled"] == 1


def t_time_basis_reported_and_mixed_flagged():
    ps = c.consolidate([(R(game_start="2026-11-01"), "B", None), (R(placed="2026-11-02"), "B", None)])["B"]
    r = c.bucket_report(ps); assert r["time_basis_used"] == {"game_start": 1, "placed": 1} and r["MIXED_TIME_BASIS"]
    assert not any("fill" in k for k in r)


def t_merge_only_on_one_verified_claim():
    rep = run([R(order_ref="A", lane_src="registry-order-id", lane="R1"), R(order_ref="B", lane_src="registry-order-id", lane="R1")])
    b = rep["buckets"]["EXACT:R1"]; assert b["all"]["settled"] == 1 and b["multi_row_plays"] == 1
    assert b["all"]["risked"] == 200 and b["all"]["net"] == 180


def t_unkeyed_rows_never_merge():   # Novig-style: no order id, identical game/bet/book
    rep = run([R(book="Novig", lane="PHASE 1"), R(book="Novig", lane="PHASE 1")])
    b = rep["buckets"]["FUZZY:PHASE 1"]; assert b["all"]["settled"] == 2 and b["possible_split_flagged_NOT_MERGED"] == 1


def t_different_claims_never_merge():
    rep = run([R(order_ref="A"), R(order_ref="C")])
    assert rep["buckets"]["EXACT:R1"]["all"]["settled"] == 1 and rep["buckets"]["EXACT:PHASE 1"]["all"]["settled"] == 1


def t_ambiguous_and_missing_claims():
    rep = run([R(order_ref="X"), R(order_ref="ZZZ"), R()])
    assert rep["join"] == {"ambiguous_claims": 1, "ref_not_in_registry": 1, "no_order_ref": 1}
    assert set(rep["buckets"]) == {"UNATTRIBUTED(ambiguous_claims)", "UNATTRIBUTED(ref_not_in_registry)", "UNATTRIBUTED(no_order_ref)"}


def t_venue_scoped():   # same order id under another venue is not a claim for this row
    assert c.resolve(R(order_ref="N", book="ProphetX"), IDX)[0] == "venue_unmatched"
    assert c.resolve(R(order_ref="N", book="Novig"), IDX) == ("exact", "BOARD V3", "K9")


def t_lane_conflict_reported_and_quarantined():
    rep = run([R(order_ref="A", lane_src="registry-order-id", lane="PHASE 1")])
    assert rep["join"]["lane_conflict"] == 1 and rep["lane_conflicts"][0]["registry_lane"] == "R1"
    assert "CONFLICT(registry=R1)" in rep["buckets"] and "EXACT:R1" not in rep["buckets"] and "EXACT:PHASE 1" not in rep["buckets"]


def t_claim_without_lane_proves_nothing():
    assert c.resolve(R(order_ref="Q"), {"Q": [("prophetx", "K", None)]})[0] == "ambiguous_claims"


def t_buckets_never_mix():
    rep = run([R(order_ref="A"), R(lane="R1"), R()])
    assert set(rep["buckets"]) == {"EXACT:R1", "FUZZY:R1", "UNATTRIBUTED(no_order_ref)"}


def t_mixed_results_same_claim_not_guessed():
    rep = run([R(order_ref="A"), R(order_ref="B", result="L", profit=-100)])
    b = rep["buckets"]["EXACT:R1"]; assert b["mixed_result_plays"] == 1 and b["all"]["settled"] == 0 and b["open_or_ambiguous"] == 1


def t_open_row_keeps_play_open():
    rep = run([R(order_ref="A"), R(order_ref="B", result=None, profit=None)])
    b = rep["buckets"]["EXACT:R1"]; assert b["open_or_ambiguous"] == 1 and b["all"]["settled"] == 0


def t_group_money_needs_every_row_finite():
    rep = run([R(order_ref="A"), R(order_ref="B", stake=float("nan"))])
    b = rep["buckets"]["EXACT:R1"]; assert b["all"]["settled"] == 1 and b["all"]["verified_money"] == 0


def t_roi_split_by_book_and_units_unavailable():
    r = c.bucket_report(c.consolidate([(R(book="Novig"), "B", None), (R(book="ProphetX", stake=50, profit=-50, result="L"), "B", None)])["B"])
    assert set(r["all"]["by_book"]) == {"Novig", "ProphetX"} and r["units"].startswith("UNAVAILABLE")


# ---- bug 1: a missing venue is never a wildcard
def t_bug1_missing_venue_not_exact():
    idx = {"M": [("", "K1", "R1")], "V": [("prophetx", "K2", "R1")]}
    assert c.resolve(R(order_ref="M", book="ProphetX"), idx)[0] == "venue_unmatched"      # empty claim venue
    assert c.resolve(R(order_ref="V", book=None), idx)[0] == "venue_unmatched"            # empty row venue
    assert c.resolve(R(order_ref="V", book="Prophet X"), idx) == ("exact", "R1", "K2")      # equal after normalisation
    assert c.build([R(order_ref="M")], idx)["join"] == {"venue_unmatched": 1}


# ---- bug 2: one invalid component stake cannot be laundered by a sum
def t_bug2_invalid_component_stake_not_laundered():
    rep = run([R(order_ref="A", stake=100, profit=90), R(order_ref="B", stake=-50, profit=10)])
    b = rep["buckets"]["EXACT:R1"]
    assert b["all"]["settled"] == 1 and b["all"]["verified_money"] == 0 and b["all"]["risked"] == 0
    rep0 = run([R(order_ref="A"), R(order_ref="B", stake=0)])
    assert rep0["buckets"]["EXACT:R1"]["all"]["verified_money"] == 0


# ---- bug 3: any differing lane / lane_fuzzy is a conflict, whatever lane_src says
def t_bug3_conflict_any_lane_src():
    for src in (None, "fuzzy-join", "manual-source", "none", "registry-order-id"):
        rep = run([R(order_ref="A", lane_src=src, lane="BOARD V3")])
        assert rep["join"] == {"lane_conflict": 1}, (src, rep["join"])
    rep = run([R(order_ref="A", lane="R1", lane_fuzzy="board")])
    assert rep["join"] == {"lane_conflict": 1} and rep["lane_conflicts"][0]["tracker_lanes"] == ["BOARD V3", "R1"]


def t_bug3_conflicts_not_merged_or_counted_exact():
    rep = run([R(order_ref="A", lane="board"), R(order_ref="B", lane="board"), R(order_ref="A")])
    assert rep["join"] == {"lane_conflict": 2, "exact": 1}
    assert rep["buckets"]["CONFLICT(registry=R1)"]["all"]["settled"] == 2          # two plays, not merged
    assert rep["buckets"]["EXACT:R1"]["all"]["settled"] == 1 and rep["buckets"]["EXACT:R1"]["all"]["risked"] == 100


def t_lane_spelling_variants_not_conflicts():
    for v in ("r1", "R1", " r 1 "):
        assert run([R(order_ref="A", lane=v)])["join"] == {"exact": 1}, v
    assert c.build([R(order_ref="C", lane="rules")], IDX)["join"] == {"exact": 1}         # rules == PHASE 1


def t_unknown_lane_spelling_is_a_conflict_not_a_match():
    assert run([R(order_ref="A", lane="Lane X")])["join"] == {"lane_conflict": 1}


# ---- time is parsed to UTC, never sorted as text
def t_utc_ordering_across_offsets():
    a = R(game_start="2026-11-02T01:00:00+00:00", profit=1)       # later in UTC
    b = R(game_start="2026-11-01T22:00:00-05:00", profit=2)       # = 2026-11-02T03:00Z: latest
    z = R(game_start="2026-11-01T23:00:00Z", profit=3)            # earliest
    ps = c.consolidate([(x, "B", None) for x in (a, b, z)])["B"]
    r = c.bucket_report(ps)
    assert r["H1"]["net"] == 3 and r["H2"]["net"] == 3, (r["H1"], r["H2"])   # H1=[z], H2=[a, b] -> 1 + 2
    assert r["game_start_range"][0].startswith("2026-11-01T23:00")


def t_unparseable_time_is_no_time():
    ps = c.consolidate([(R(game_start="soon"), "B", None), (R(game_start="2026-11-01"), "B", None)])["B"]
    assert c.bucket_report(ps)["settled_no_time"] == 1


# ---- the runner: no executor import; lane names match executor without importing it
def t_runner_has_no_executor_import():
    src = open(os.path.join(HERE, "p2_audit.py")).read()
    assert "import executor" not in src and "from executor" not in src and " ex." not in src


def t_lane_names_match_executor():
    exsrc = open(os.path.join(HERE, "executor.py")).read()
    line = next(l for l in exsrc.splitlines() if l.startswith("LANE_NAME = "))
    names = ast.literal_eval(line.split("=", 1)[1].strip())
    for k, v in names.items():
        assert c.canon_lane(k) == v, (k, v)


def t_registry_lane_from_source():
    import registry as reg
    assert reg.row_lane({"key": "NBA|A @ B|total|OVER", "source": "board"}) == "board"
    assert reg.row_lane({"key": "NBA|A @ B|total|OVER", "source": "muse"}) is None
    assert reg.row_lane({"key": "board|NBA|x", "source": "r1"}) is None


# ---- the public log line prints counts and bucket names only
def t_runner_prints_counts_only():
    src = open(os.path.join(HERE, "p2_audit.py")).read()
    prints = [l for l in src.splitlines() if "print(" in l or l.strip().startswith(("f\"", "\""))]
    joined = "\n".join(prints)
    for bad in ("risked", "net", "roi", "profit", "stake", "game", "bet"):
        assert bad not in joined.replace("verified money", ""), bad


# ---- private delivery (offline: urlopen is replaced; nothing leaves the machine)
def t_render_aggregates_only():
    rows = [R(order_ref="A", game="SECRETGAME @ XYZ", bet="Over 999.5", game_start="2026-11-02T00:00:00Z"),
            R(lane="R1", game="OTHERGAME", bet="Lakers -3.5", game_start="2026-11-03T00:00:00Z")]
    text, csvr = c.render(run(rows))
    for leak in ("SECRETGAME", "XYZ", "999.5", "OTHERGAME", "Lakers"):
        assert leak not in text and leak not in str(csvr), leak
    assert "EXACT:R1" in text and "FUZZY:R1" in text and "UNAVAILABLE" in text
    assert all(set(r) <= set(c.CSV_FIELDS) for r in csvr) and {r["segment"] for r in csvr} >= {"all", "H1", "H2", "last50"}


def _runner():
    import importlib
    sys.modules.pop("p2_audit", None)
    return importlib.import_module("p2_audit")   # import must not run the audit (main is guarded)


def t_runner_import_runs_nothing():
    m = _runner()
    assert hasattr(m, "main") and hasattr(m, "send_private")


def t_send_private_without_secrets_is_loud_not_silent():
    import contextlib
    m, out = _runner(), io.StringIO()
    os.environ.pop("TELEGRAM_BOT_TOKEN", None); os.environ.pop("TELEGRAM_CHAT_ID", None)
    with contextlib.redirect_stdout(out):
        ok = m.send_private("x", [])
    assert ok is False and "NOT delivered" in out.getvalue()


def t_send_private_public_log_carries_no_figures_or_token():
    import contextlib, urllib.request
    m, out, sent = _runner(), io.StringIO(), []

    class Resp:
        def read(self):
            return b"{}"
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=0: (sent.append(req.data), Resp())[1]
    os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"] = "TOKEN123", "CHAT9"
    try:
        text, csvr = c.render(run([R(order_ref="A", game_start="2026-11-02T00:00:00Z")]))
        with contextlib.redirect_stdout(out):
            ok = m.send_private(text, csvr)
        urllib.request.urlopen = lambda req, timeout=0: (_ for _ in ()).throw(OSError("TOKEN123 secret detail"))
        with contextlib.redirect_stdout(out):
            bad = m.send_private(text, csvr)
    finally:
        urllib.request.urlopen = orig
        os.environ.pop("TELEGRAM_BOT_TOKEN", None); os.environ.pop("TELEGRAM_CHAT_ID", None)
    log = out.getvalue()
    assert ok is True and bad is False and len(sent) == 2                        # one message + the CSV document
    assert b"p2_lane_audit.csv" in sent[1] and b"risked" in sent[1]              # the figures go to Telegram...
    for leak in ("TOKEN123", "CHAT9", "risked", "net", "+90", "secret detail"):  # ...and never to the public log
        assert leak not in log, (leak, log)
    assert "telegram delivered: 1 message(s) + CSV" in log and "telegram send failed (OSError)" in log


def t_workflow_secrets_are_exactly_the_needed_four():
    import re as _re
    wf = open(os.path.join(HERE, ".github", "workflows", "p2-audit.yml")).read()
    assert set(_re.findall(r"secrets\.([A-Z_]+)", wf)) == {"TRACKER_PASSPHRASE", "REGISTRY_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}
    assert "contents: read" in wf and "upload-artifact" not in wf and "actions/cache" not in wf and "git push" not in wf and "git commit" not in wf


_n = 0
for n, f in list(globals().items()):
    if n.startswith("t_"):
        f(); print("ok", n); _n += 1
print(f"{_n} checks passed")
