#!/usr/bin/env python3
"""R1's 25-fill checkpoint, registered by Peter on 17 Nov 2026. Reporting only: it states a verdict, changes nothing."""
import last50_report as r


def rows(n, res, clv, am=-110, key=None):
    return [{"ts": f"2026-11-{10 + i:02d}", "key": key or f"k{i}", "res": res, "clv": clv, "am": am} for i in range(n)]


def t_before_target():
    out = r.r1_checkpoint(rows(8, "W", 2.0))
    assert "8/25" in out and "to go, no decision before then" in out
    assert "VERDICT" not in out                                   # no verdict is stated early
    assert "0/25" in r.r1_checkpoint([]) and "0/25" in r.r1_checkpoint(None)


def t_unique_and_settled():
    dup = rows(3, "W", 1.0, key="same")                            # one selection alerted three times
    assert "1/25" in r.r1_checkpoint(dup)
    mixed = rows(2, "W", 1.0) + [{"ts": "2026-11-20", "key": "pend", "res": None, "clv": None, "am": -110}]
    assert "2/25" in r.r1_checkpoint(mixed)                        # unsettled fills do not count


def t_registered_verdicts():
    assert "PAUSE FOR REVIEW" in r.r1_checkpoint(rows(25, "L", -1.0))
    assert "INCONCLUSIVE" in r.r1_checkpoint(rows(25, "L", 2.0))   # CLV positive, units negative -> Peter decides
    assert "do NOT extend" in r.r1_checkpoint(rows(25, "L", 2.0))
    assert "CONTINUE" in r.r1_checkpoint(rows(25, "W", 2.0))
    assert "CONTINUE" in r.r1_checkpoint(rows(25, "W", -1.0))      # units positive is enough to keep running
    assert "NO CERTIFIED CLV" in r.r1_checkpoint(rows(25, "L", None))


def t_missing_clv_is_not_zero():
    """A fill with no certified close must not be averaged in as 0.00%."""
    mix = rows(12, "W", 2.0) + [dict(x, key=f"n{i}", clv=None) for i, x in enumerate(rows(13, "W", None))]
    out = r.r1_checkpoint(mix)
    assert "+2.00% on 12" in out and "25/25" in out


def t_wired_and_inert():
    s = open("last50_report.py").read()
    assert "R1_CHECK_N = 25" in s and 'r1_checkpoint(live_rows(acct, "R1"))' in s
    assert s.count("def r1_checkpoint") == 1
    # the checkpoint must not touch R1's rule, sizing or limits
    for name in ("R1_UNIT", "R1_DAILY_RISK", "R1_MAX_PLAYS", "EXEC_R1_LIVE"):
        assert name not in s
    a = open("agree_rules.py").read()
    assert "r1_checkpoint" not in a and "R1_CHECK" not in a
    assert "checkpoint" not in open("executor.py").read().lower()


for f in (t_before_target, t_unique_and_settled, t_registered_verdicts, t_missing_clv_is_not_zero, t_wired_and_inert):
    f()
print("r1 checkpoint tests: OK")
