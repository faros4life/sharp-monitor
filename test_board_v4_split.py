#!/usr/bin/env python3
"""Board V4's two forward comparisons (Peter, 17 Nov, O19). Reporting only - it reads settled fills and changes
nothing. Pure: no ledger, no network."""
import last50_report as r


def row(key, res, am, clv, books, basis):
    return {"ts": "2026-11-17", "key": key, "res": res, "am": am, "clv": clv, "books": books, "fee_basis": basis}


def t_splits_by_basis():
    rows = [row("a", "W", -110, 1.5, ["novig"], False), row("b", "W", -110, 1.5, ["novig"], None),
            row("c", "L", -112, -2.0, ["kalshi"], True)]
    out = "\n".join(r.board_v4_split(rows))
    assert "BEFORE the fee correction          n   2" in out      # False AND None are both "before"
    assert "AFTER the fee correction           n   1" in out


def t_splits_by_venue():
    rows = [row("a", "W", -110, 1.0, ["novig"], True), row("b", "W", -110, 1.0, ["prophetx", "novig"], True),
            row("c", "L", -112, -2.0, ["kalshi"], True), row("d", "L", -111, -1.0, ["novig", "kalshi"], True),
            row("e", "W", -105, None, [], True)]
    out = "\n".join(r.board_v4_split(rows))
    assert "filled Novig / ProphetX only       n   2" in out
    assert "any Kalshi / Polymarket US leg    n   2" in out or "any Kalshi / Polymarket US leg     n   2" in out
    assert "fill venue not recorded            n   1" in out      # a split-venue play counts to the marginal group
    assert "polymarket.us" in open("last50_report.py").read()     # both spellings of the venue key


def t_unsettled_and_missing_clv():
    rows = [row("a", "W", -110, 2.0, ["novig"], True), row("b", None, -110, None, ["novig"], True),
            row("c", "L", -110, None, ["novig"], True)]
    out = "\n".join(r.board_v4_split(rows))
    assert "n   2" in out                                          # the unsettled fill is not counted
    assert "on 1/2" in out                                         # coverage shown; the missing close is NOT a zero
    assert "+2.00%" in out


def t_empty_and_warning():
    out = "\n".join(r.board_v4_split([]))
    assert "no fills yet" in out and "BOARD V4 SPLIT" in out
    assert "does not say" in out and "whether those bets are profitable" in out
    assert "\n".join(r.board_v4_split(None)).count("no fills yet") >= 2


def t_reporting_only():
    s = open("last50_report.py").read()
    assert "board_v4_split(live_rows(acct" in s and s.count("def board_v4_split") == 1
    for name in ("EXEC_BOARD", "BOARD_V4_MIN", "board_after_fee_floor"):
        assert name not in s
    # the ledger exposes what the split needs, and only as added fields
    L = open("live_ledger.py").read()
    assert '"books": sorted(' in L and '"fee_basis": p.get("fee_basis")' in L
    assert 'p["fee_basis"] = bool(o["board_fee_basis"])' in L


for f in (t_splits_by_basis, t_splits_by_venue, t_unsettled_and_missing_clv, t_empty_and_warning, t_reporting_only):
    f()
print("board v4 split tests: OK")
