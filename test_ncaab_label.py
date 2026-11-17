#!/usr/bin/env python3
"""Nov 17: a CACHE_ONLY_FX row whose fixture list IS cached is UNMATCHED, not "waiting for the daily lookup"."""
import report_sections as rs


def t_classes_differ():
    waiting = "NCAAB fixture not in any cached store; waiting for the capped daily NCAAB lookup (1 paid call per ET day) - retry not counted"
    unmatched = "no OddsPapi fixture matched (NCAAB list for this date is already cached)"
    assert rs.clv_reason_class(waiting) == "fixture not yet fetched"
    assert rs.clv_reason_class(unmatched) == "fixture unmatched"
    assert rs.clv_reason_class("no fixture in any cache matches this league and date") == "fixture unmatched"


def t_branch_uses_this_rows_start():
    s = open("clv_ledger.py").read()
    i = s.index("elif lg in CACHE_ONLY_FX:")
    blk = s[i:i + 1400]
    assert 'day_listed(lg, tp(s.get("game_start")), st)' in blk      # never the stale gs from the earlier loop
    assert "day_listed(lg, gs, st)" not in blk
    assert 'rec["tries"] = rec.get("tries", 0) + 1' in blk           # a cached-list miss now counts toward done
    assert 'rec["done"] = True' in blk
    assert "waiting for the capped daily" in blk                     # the genuine not-yet-fetched case is kept


for f in (t_classes_differ, t_branch_uses_this_rows_start):
    f()
print("ncaab label tests: OK")
