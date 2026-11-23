import ast
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_audit_core as c  # noqa: E402

R = lambda **k: {"result": "W", "stake": 100, "profit": 90, "game": "g", "bet": "b", "book": "ProphetX", **k}
IDX = {"A": [("prophetx", "K1", "R1")], "B": [("prophetx", "K1", "R1")], "C": [("prophetx", "K2", "LANE 1")],
       "X": [("prophetx", "K3", "R1"), ("prophetx", "K4", "LANE 1")], "N": [("novig", "K9", "BOARD V4")]}
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
    rep = run([R(book="Novig", lane="LANE 1"), R(book="Novig", lane="LANE 1")])
    b = rep["buckets"]["FUZZY:LANE 1"]; assert b["all"]["settled"] == 2 and b["possible_split_flagged_NOT_MERGED"] == 1


def t_different_claims_never_merge():
    rep = run([R(order_ref="A"), R(order_ref="C")])
    assert rep["buckets"]["EXACT:R1"]["all"]["settled"] == 1 and rep["buckets"]["EXACT:LANE 1"]["all"]["settled"] == 1


def t_ambiguous_and_missing_claims():
    rep = run([R(order_ref="X"), R(order_ref="ZZZ"), R()])
    assert rep["join"] == {"ambiguous_claims:different_lanes": 1, "ref_not_in_registry": 1, "no_order_ref": 1}
    assert set(rep["buckets"]) == {"UNATTRIBUTED(ambiguous_claims)", "UNATTRIBUTED(ref_not_in_registry)", "UNATTRIBUTED(no_order_ref)"}


def t_venue_scoped():   # same order id under another venue is not a claim for this row
    assert c.resolve(R(order_ref="N", book="ProphetX"), IDX)[0] == "venue_unmatched"
    assert c.resolve(R(order_ref="N", book="Novig"), IDX) == ("exact", "BOARD V4", "K9")


def t_lane_conflict_reported_and_quarantined():
    rep = run([R(order_ref="A", lane_src="registry-order-id", lane="LANE 1")])
    assert rep["join"]["lane_conflict"] == 1 and rep["lane_conflicts"][0]["registry_lane"] == "R1"
    assert "CONFLICT(registry=R1)" in rep["buckets"] and "EXACT:R1" not in rep["buckets"] and "EXACT:LANE 1" not in rep["buckets"]


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
        rep = run([R(order_ref="A", lane_src=src, lane="BOARD V4")])
        assert rep["join"] == {"lane_conflict": 1}, (src, rep["join"])
    rep = run([R(order_ref="A", lane="R1", lane_fuzzy="board")])
    assert rep["join"] == {"lane_conflict": 1} and rep["lane_conflicts"][0]["tracker_lanes"] == ["BOARD V4", "R1"]


def t_bug3_conflicts_not_merged_or_counted_exact():
    rep = run([R(order_ref="A", lane="board"), R(order_ref="B", lane="board"), R(order_ref="A")])
    assert rep["join"] == {"lane_conflict": 2, "exact": 1}
    assert rep["buckets"]["CONFLICT(registry=R1)"]["all"]["settled"] == 2          # two plays, not merged
    assert rep["buckets"]["EXACT:R1"]["all"]["settled"] == 1 and rep["buckets"]["EXACT:R1"]["all"]["risked"] == 100


def t_lane_spelling_variants_not_conflicts():
    for v in ("r1", "R1", " r 1 "):
        assert run([R(order_ref="A", lane=v)])["join"] == {"exact": 1}, v
    assert c.build([R(order_ref="C", lane="rules")], IDX)["join"] == {"exact": 1}         # rules == LANE 1


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
    assert set(_re.findall(r"secrets\.([A-Z_]+)", wf)) == {"TRACKER_PASSPHRASE", "REGISTRY_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
                                                           "NOVIG_READ_KEY_ID", "NOVIG_READ_KEY_PEM", "NOVIG_TRADE_KEY_ID",
                                                           "PROPHETX_ACCESS_KEY", "PROPHETX_SECRET_KEY",
                                                           "NOVIG_READ_TOKEN"}   # Nov 17 Option A: read-only, novig-runner only
    for bad in ("NOVIG_TRADE_KEY_PEM", "PX_TRADE", "PROPHETX_TRADE", "GMAIL", "ODDSPAPI", "KALSHI", "PMUS"):
        assert bad not in wf, bad
    assert "contents: read" in wf and "upload-artifact" not in wf and "actions/cache" not in wf and "git push" not in wf and "git commit" not in wf


# ---- counts-only diagnosis of ambiguous order ids
def t_ambiguity_kinds():
    assert c.ambiguity_kind({("K1", "R1"), ("K2", "LANE 1")}) == "different_lanes"
    assert c.ambiguity_kind({("NBA|A|total|OVER", "board"), ("board|NBA|A|total|OVER", "board")}) == "same_lane_prefix_variant"
    assert c.ambiguity_kind({("NBA|A|total|OVER", "board"), ("NBA|B|total|OVER", "BOARD V4")}) == "same_lane_different_keys"
    idx = {"Z": [("prophetx", "NBA|A|total|OVER", "board"), ("prophetx", "board|NBA|A|total|OVER", "board")]}
    rep = c.build([R(order_ref="Z")], idx)
    assert rep["join"] == {"ambiguous_claims:same_lane_prefix_variant": 1} and "UNATTRIBUTED(ambiguous_claims)" in rep["buckets"]


def t_same_order_twice_in_one_row_is_not_ambiguous():
    idx = {"Y": [("prophetx", "K", "r1"), ("prophetx", "K", "r1")]}      # live_order and live_more carry the same id
    assert c.resolve(R(order_ref="Y"), idx) == ("exact", "r1", "K")


def t_time_diag_counts():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 14, 23, 15, tzinfo=timezone.utc)
    ps = [R(game_start="2026-11-15T00:30:00Z", settled="2026-11-14T00:00:00Z"), R(game_start="2026-11-13T19:00:00-05:00"), R(placed="junk")]
    d = c.time_diag(ps, now)
    assert d["game_start"] == {"present": 2, "unparseable": 0, "after_run": 1, "midnight_utc": 1}, d["game_start"]
    assert d["settled"]["midnight_utc"] == 1 and d["placed"]["unparseable"] == 1


# ---- venue links (Novig fill clientId -> nv|market|outcome; ProphetX trade order_id -> px|trade id)
NVX = {"c1": [("novig", "K1", "board")], "c2": [("novig", "K2", "board")], "c3": [("novig", "K3", "r1")],
       "c4": [("novig", "K4", "board"), ("novig", "K5", "r1")], "P9": [("prophetx", "K9", "rules")]}
F = lambda m, o, cid, oid=None: {"marketId": m, "outcomeId": o, "clientId": cid, "orderId": oid}
NV = lambda tid, **k: R(id=tid, book="Novig", **k)


def t_link_index_keys_are_the_tracker_keys():
    li = c.link_index([F("M", "O", "c1", "v1"), F("M", "O", "c2"), F(None, "O", "c9"), {"x": 1}],
                      [{"id": 77, "order_id": "P9"}, {"id": None, "order_id": "P8"}])
    assert set(li) - {"_incomplete"} == {"nv|M|O", "px|77"} and li["nv|M|O"][0] == frozenset({"c1", "v1"}) and li["px|77"] == [frozenset({"P9"})]


def t_link_position_one_lane_is_exact():
    li = c.link_index([F("M", "O", "c1"), F("M", "O", "c2")], [])
    rep = c.build([NV("nv|M|O")], NVX, links=li)
    assert rep["join"].get("exact") == 1 and rep["join"].get("exact_via_venue_link") == 1 and "EXACT:BOARD V4" in rep["buckets"]


def t_link_position_two_lanes_is_not_exact():
    li = c.link_index([F("M", "O", "c1"), F("M", "O", "c3")], [])
    rep = c.build([NV("nv|M|O")], NVX, links=li)
    assert rep["join"].get("link:link_position_multi_lane") == 1 and not any(b.startswith("EXACT") for b in rep["buckets"])


def t_link_one_unregistered_fill_fails_the_position():
    li = c.link_index([F("M", "O", "c1"), F("M", "O", "manual-xyz")], [])
    assert c.resolve_link(NV("nv|M|O"), li, NVX)[0] == "link_order_not_in_registry"


def t_link_ambiguous_order_fails():
    li = c.link_index([F("M", "O", "c4")], [])
    assert c.resolve_link(NV("nv|M|O"), li, NVX)[0] == "link_order_ambiguous"


def t_link_is_venue_scoped():
    li = c.link_index([F("M", "O", "P9")], [])                    # a ProphetX id used as a Novig client id
    assert c.resolve_link(NV("nv|M|O"), li, NVX)[0] == "link_order_not_in_registry"
    li2 = c.link_index([], [{"id": 5, "order_id": "P9"}])
    assert c.resolve_link(R(id="px|5", book="ProphetX"), li2, NVX) == ("exact_link", "LANE 1", "K9")


def t_link_rows_never_merge_and_conflict_still_applies():
    li = c.link_index([F("M", "O", "c1"), F("M", "Q", "c2")], [])
    rep = c.build([NV("nv|M|O"), NV("nv|M|Q"), NV("nv|M|O", lane="R1")], NVX, links=li)
    assert rep["buckets"]["EXACT:BOARD V4"]["all"]["settled"] == 2 and rep["join"]["lane_conflict"] == 1


def t_order_ref_path_unchanged_by_links():
    li = c.link_index([F("M", "O", "c1")], [])
    assert c.build([R(order_ref="A")], IDX, links=li)["join"] == {"exact": 1}


def t_no_link_stays_unattributed():
    rep = c.build([NV("nv|Z|Z")], NVX, links={})
    assert rep["join"] == {"no_order_ref": 1, "link:no_venue_link": 1} and "UNATTRIBUTED(no_order_ref)" in rep["buckets"]


def t_runner_venue_reads_are_read_only():
    src = open(os.path.join(HERE, "p2_audit.py")).read()
    body = src[src.index("def read_novig_fills"):src.index("def send_private")]
    paths = set(__import__("re").findall(r'"(/v[0-9][^"]*)"', body))
    # 16 Nov: + ProphetX matching detail (documented read; resolves orders the 100-row get_trades cap hides)
    assert paths == {"/v3/portfolio/fills", "/v4/mm/get_trades", "/v2/mm/get_wager_matching_detail?"}, paths   # px_login's POST /auth/login lives in book_check
    # every px_call in the readers is a GET: one argument, no request body
    assert all(",".join(m.split(",")[1:]).strip() == "" for m in __import__("re").findall(r"px_call\(([^()]*(?:\([^()]*\))?[^()]*)\)", body)), "px_call with a body"
    for bad in ("place", "cancel", "order(", "/orders", "trade_key", "TRADE_KEY_PEM", "px_live", "book_live", "executor"):
        assert bad not in body, bad
    assert "nv.ready()" in body          # Novig refuses to run unless the key is confirmed read-only


# ---- completeness: a possibly-truncated venue read never yields EXACT
def t_px_cap_or_paging_marker_is_incomplete():
    assert c.px_trades_complete([{}] * 99) and not c.px_trades_complete([{}] * 100) and not c.px_trades_complete([{}] * 250)
    for k in ("next", "cursor", "next_cursor", "has_more", "pagination", "Offset"):
        assert not c.px_trades_complete([{}] * 3, ["trades", k]), k
    assert c.px_trades_complete([{}] * 3, ["trades", "status"])


def t_incomplete_venue_fails_closed():
    fills = [F("M", "O", "c1")]
    trades = [{"id": 5, "order_id": "P9"}]
    li = c.link_index(fills, trades, {"nv": False, "px": True})
    assert c.resolve_link(NV("nv|M|O"), li, NVX)[0] == "link_source_incomplete"
    assert c.resolve_link(R(id="px|5", book="ProphetX"), li, NVX)[0] == "exact_link"
    li2 = c.link_index(fills, trades, {"nv": True, "px": False})
    assert c.resolve_link(R(id="px|5", book="ProphetX"), li2, NVX)[0] == "link_source_incomplete"
    rep = c.build([NV("nv|M|O")], NVX, links=li)
    assert not any(b.startswith("EXACT") for b in rep["buckets"]) and rep["join"].get("link:link_source_incomplete") == 1


def t_novig_page_cap_marks_truncated():
    import types
    m = _runner()
    calls = []
    fake = types.SimpleNamespace(ready=lambda: True, _S={"id": "K"},
                                 get=lambda path, prm: (calls.append(prm), {"w": {"items": [{"fillId": len(calls)}], "next": "cur"}})[1])
    sys.modules["novig_signed"] = fake
    try:
        os.environ.pop("NOVIG_TRADE_KEY_ID", None)
        fills, note, ok = m.read_novig_fills()
    finally:
        sys.modules.pop("novig_signed", None)
    assert ok is False and "TRUNCATED" in note and len(calls) == 40 and len(fills) == 40
    fake2 = types.SimpleNamespace(ready=lambda: True, _S={"id": "K"}, get=lambda path, prm: {"w": {"items": [{"fillId": 1}], "next": None}})
    sys.modules["novig_signed"] = fake2
    try:
        assert m.read_novig_fills()[2] is True
    finally:
        sys.modules.pop("novig_signed", None)


# ---- RULED (Peter's 13 Nov table) - never EXACT, multi-lane -> UNATTRIBUTED
TOKS = lambda t: set(__import__("re").findall(r"[a-z]+", str(t).lower()))
TRG = {"Lane 1": [("11-01", {"boston"}, {"orlando"})], "R1": [("11-11", {"utah"}, {"denver"})],
       "Bets Board v4": [("11-11", {"utah"}, {"denver"}), ("11-20", {"late"}, {"game"})]}
RG = lambda **k: R(order_ref=None, **k)


def t_ruled_matches_date_window_and_both_teams():
    assert c.ruled_lane(RG(game="Boston Celtics @ Orlando Magic", game_start="2026-11-02T00:30:00Z"), TRG, TOKS) == ("LANE 1", None)
    assert c.ruled_lane(RG(game="Boston Celtics @ Miami Heat", game_start="2026-11-01T23:00:00Z"), TRG, TOKS) == (None, None)
    assert c.ruled_lane(RG(game="Boston @ Orlando", game_start="2026-11-05T00:00:00Z"), TRG, TOKS) == (None, None)


def t_ruled_two_lanes_is_unattributed():
    assert c.ruled_lane(RG(game="Utah Jazz @ Denver Nuggets", game_start="2026-11-11T02:00:00Z"), TRG, TOKS) == (None, "ruled_multi_lane")
    rep = c.build([RG(game="Utah @ Denver", game_start="2026-11-11T02:00:00Z")], IDX, ruled=(TRG, TOKS))
    assert set(rep["buckets"]) == {"UNATTRIBUTED(ruled_multi_lane)"}


def t_ruled_window_is_oct31_to_nov12_only():
    assert c.ruled_lane(RG(game="Late @ Game", game_start="2026-11-20T00:00:00Z"), TRG, TOKS) == (None, None)


def t_ruled_never_exact_and_exact_wins():
    rep = c.build([RG(game="Boston @ Orlando", game_start="2026-11-01T23:00:00Z"),
                   R(order_ref="A", game="Boston @ Orlando", game_start="2026-11-01T23:00:00Z")], IDX, ruled=(TRG, TOKS))
    assert "RULED:LANE 1" in rep["buckets"] and "EXACT:R1" in rep["buckets"]
    assert not any(b.startswith("EXACT:PHASE") for b in rep["buckets"])
    assert c.units_for("RULED:LANE 1", ["2026-11-10T00:00:00+00:00", "x"], 300) is None      # no units on RULED


def t_ruled_beats_fuzzy_and_disagreement_is_counted():
    rep = c.build([RG(game="Boston @ Orlando", game_start="2026-11-01T23:00:00Z", lane="R1")], IDX, ruled=(TRG, TOKS))
    assert "RULED:LANE 1" in rep["buckets"] and rep["join"].get("ruled_vs_tracker_text_disagree") == 1


def t_no_ruled_table_means_old_behaviour():
    assert set(c.build([RG(lane="R1")], IDX)["buckets"]) == {"FUZZY:R1"}


# ---- EXACT claims from live registry + durable ledger, deduplicated by immutable id
def _o(oid, src, key="NBA|A|total|OVER", book="novig", cid=None):
    return {"key": key, "source": src, "live_order": {"status": "placed", "order_id": oid, "client_id": cid, "book": book}}


def t_index_dedups_by_id_across_sources():
    import registry as reg
    live = [_o("c1", "board"), _o("c2", "r1")]
    led = [_o("c1", "board"), _o("c3", "rules")]
    idx, st = c.index_from_sources([("registry", live), ("ledger", led)], reg.row_lane, reg._venue)
    assert idx["c1"] == [("novig", "NBA|A|total|OVER", "board")]          # same claim in both sources = ONE claim
    assert st["ids_in_registry+ledger"] == 1 and st["ids_in_registry"] == 1 and st["ids_in_ledger"] == 1
    assert "ids_cross_source_conflict" not in st


def t_index_cross_source_conflict_is_kept_and_ambiguous():
    import registry as reg
    idx, st = c.index_from_sources([("registry", [_o("c1", "board")]), ("ledger", [_o("c1", "r1")])], reg.row_lane, reg._venue)
    assert st["ids_cross_source_conflict"] == 1 and len(idx["c1"]) == 2
    assert c.resolve(R(order_ref="c1", book="Novig"), idx)[0].startswith("ambiguous_claims")


def t_index_lane_from_source_not_key_prefix():
    import registry as reg
    idx, st = c.index_from_sources([("registry", [_o("c9", "muse", key="board|NBA|A|total|OVER"),
                                                   _o("c8", "muse")])], reg.row_lane, reg._venue)
    assert idx["c9"][0][2] == "board" and "c8" not in idx and st["rows_no_provable_lane"] == 1


def t_index_client_id_also_indexed():
    import registry as reg
    idx, _ = c.index_from_sources([("ledger", [_o("v77", "r1", cid="c77")])], reg.row_lane, reg._venue)
    assert set(idx) == {"v77", "c77"}


# ---- Section F: every row from 12 Nov is classified exactly once
def t_section_f_exactly_once_over_mixed_classes():
    rows = [R(id="1", order_ref="A", game_start="2026-11-12T23:00:00Z"),
            RG(id="2", game="Boston @ Orlando", game_start="2026-11-01T23:00:00Z"),
            RG(id="3", lane="R1", game_start="2026-11-13T23:00:00Z"),
            RG(id="4", game_start="2026-11-13T23:00:00Z", result=None, profit=None)]
    rep = c.build(rows, IDX, ruled=(TRG, TOKS))
    eo = rep["exactly_once"]
    assert eo["ok"] and eo["rows"] == 4 and set(rep["row_bucket"].values()) == {"EXACT:R1", "RULED:LANE 1", "FUZZY:R1",
                                                                                  "UNATTRIBUTED(no_order_ref)"}



def t_fills_without_tracker_row():
    li = c.link_index([F("M", "O", "c1"), F("M", "Q", "zz")], [{"id": 5, "order_id": "P9"}])
    assert c.fills_without_tracker_row(li, NVX, {"nv|M|O"}) == {"px": 1}      # nv|M|Q is not our order; px|5 has no row
    assert c.fills_without_tracker_row(li, NVX, {"nv|M|O", "px|5"}) == {}

_n = 0
for n, f in list(globals().items()):
    if n.startswith("t_"):
        f(); print("ok", n); _n += 1
print(f"{_n} checks passed")
