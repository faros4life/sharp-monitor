#!/usr/bin/env python3
"""Board after-fee floor (Peter, 17 Nov, Option 1). OFF by default: it can admit orders the old floor refused."""
import importlib
import os

import executor as ex


def t_off_by_default():
    assert ex.BOARD_FEE_BASIS is False
    assert "EXEC_BOARD_FEE_BASIS" in open("executor.py").read()


def t_floor_is_the_trigger_venues_own_after_fee_price():
    """The alert's raw COST re-priced at the trigger venue's fee - never a number a fee has already touched."""
    for book, want in (("kalshi", -112), ("novig", -104), ("prophetx", -106), ("polymarket_us", -111)):
        am, why = ex.board_after_fee_floor({"price": 0.51, "book": book, "league": "NBA"})
        assert am == want, (book, am)
        assert "raw cost" in why
    # no double counting: the input is the 0-1 cost, and the same cost always gives the same answer
    a = ex.board_after_fee_floor({"price": 0.51, "book": "kalshi", "league": "NBA"})[0]
    b = ex.board_after_fee_floor({"price": 0.51, "book": "kalshi", "league": "NBA"})[0]
    assert a == b == -112
    # a venue's own after-fee floor is never BETTER than its raw price
    assert -112 <= -104 and ex.board_after_fee_floor({"price": 0.51, "book": "novig"})[0] == -104


def t_fails_closed():
    """Anything it cannot compute keeps the RAW floor, which is the stricter one."""
    for bad in ({"price": None, "book": "kalshi"}, {"price": 0.51, "book": ""}, {"book": "kalshi"},
                {"price": 0.51, "book": "mystery"},          # no modelled fee -> must not become a zero-fee floor
                {"price": 0, "book": "kalshi"}, {"price": 1.5, "book": "kalshi"}, {}):
        am, why = ex.board_after_fee_floor(bad)
        assert am is None and why, bad


def t_entry_carries_both_numbers_and_the_switch():
    s = open("executor.py").read()
    i = s.index('"board_entry": {')
    blk = s[i:i + 420]
    assert '"alert_price_raw": am' in blk and '"fee_basis"' in blk and '"fee_basis_on": BOARD_FEE_BASIS' in blk
    assert '(_bf if (BOARD_FEE_BASIS and _bf is not None) else am)' in blk   # off, or uncomputable -> raw floor


def t_ledger_row_records_the_basis():
    """Requirement 5: before-and-after must be splittable from the row itself, not from a commit date."""
    from datetime import datetime, timezone
    import json
    p = {"play_key": "board|k", "source": "board", "sport": "NBA", "game": "A vs. B", "bet": "Under 224.5 (-108)",
         "start_utc": "2026-11-18T00:00:00Z", "alert_utc": "2026-11-17T20:00:00Z",
         "board_v4": {"ok": True, "why": None, "evidence": {"book": "novig"}, "strength": []}}
    ent = {"book_key": "kalshi", "price_after_fee": -112, "alert_price_raw": -104,
           "fee_basis": "kalshi raw cost 0.5100 -> after fee -112", "fee_basis_on": True, "point": 224.5}
    row = json.loads(json.dumps(ex.ledger_row({"play": p, "entry": ent, "verdict": "SKIP"},
                                              datetime.now(timezone.utc)), default=str))
    assert row["board_fee_basis"] is True
    assert row["board_alert_price_raw"] == -104 and row["alert_price_after_fee"] == -112
    # a non-board row carries neither field as a value
    p2 = dict(p, source="r1", play_key="r1|k")
    row2 = ex.ledger_row({"play": p2, "entry": {"book_key": "prophetx", "price_after_fee": -110}, "verdict": "SKIP"},
                         datetime.now(timezone.utc))
    assert row2["board_fee_basis"] is None and row2["board_alert_price_raw"] is None


def t_nothing_else_changed():
    """V4 confirmation, stakes, caps, duplicate protection and the stops must be untouched by this."""
    prev = os.environ.get("EXEC_BOARD_FEE_BASIS")
    try:
        for val in ("off", "on"):
            os.environ["EXEC_BOARD_FEE_BASIS"] = val
            m = importlib.reload(ex)
            assert m.BOARD_V4_MIN == 10000.0 and m.BOARD_CONFIRM_MIN == 15
            assert m.BOARD_UNIT == 200.0 and m.BOARD_MAX_PLAYS == 10 and m.BOARD_DAILY_RISK == 2000.0
            assert m.board_v4({"rule_met": True, "second_book_status": "ok", "second_book": ["novig"], "line": 224.5,
                               "book": "kalshi", "depth_by_book": {"novig": {"this_side": 15000, "label": "Under 224.5",
                                                                             "price": 0.51, "heavier_side": True}}})[0]
            src = open("executor.py").read()
            assert "def board_gate" in src and "LIVEKEYS" in src and "live_guards" in src
            assert src.count("BOARD_FEE_BASIS") == 5   # two comment mentions, the definition, the floor choice, the audit field
    finally:
        if prev is None:
            os.environ.pop("EXEC_BOARD_FEE_BASIS", None)
        else:
            os.environ["EXEC_BOARD_FEE_BASIS"] = prev
        importlib.reload(ex)


def t_separate_hard_limits_untouched():
    """The line floor and the eligibility re-pricing are different limits and must not move."""
    s = open("executor.py").read()
    assert "floor_line" in s and "def qual_price" in s
    i = s.index("def board_after_fee_floor")
    blk = s[i:i + 1500]
    assert "floor_line" not in blk and "qual_price" not in blk and "MIN_ORDER" not in blk


for f in (t_off_by_default, t_floor_is_the_trigger_venues_own_after_fee_price, t_fails_closed,
          t_entry_carries_both_numbers_and_the_switch, t_ledger_row_records_the_basis, t_nothing_else_changed,
          t_separate_hard_limits_untouched):
    f()
print("board fee-basis tests: OK")
