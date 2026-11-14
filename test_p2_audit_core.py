import math
import p2_audit_core as c

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
    assert c.resolve(R(order_ref="N", book="ProphetX"), IDX)[0] == "ref_not_in_registry"
    assert c.resolve(R(order_ref="N", book="Novig"), IDX) == ("exact", "BOARD V3", "K9")


def t_lane_conflict_reported_registry_wins():
    rep = run([R(order_ref="A", lane_src="registry-order-id", lane="PHASE 1")])
    assert rep["join"]["lane_conflict"] == 1 and rep["lane_conflicts"][0]["registry_lane"] == "R1"
    assert "EXACT:R1" in rep["buckets"] and "EXACT:PHASE 1" not in rep["buckets"]


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


for n, f in list(globals().items()):
    if n.startswith("t_"):
        f(); print("ok", n)
