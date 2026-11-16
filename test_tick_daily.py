"""Simulated tests for tick.py daily jobs (no network). These prove the RULE, not that a run happened."""
import sys
from datetime import datetime, timezone
import tick
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
D = tick.daily_due
U = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
man_ok = {"event": "workflow_dispatch", "actor": "faros4life", "status": "completed", "conclusion": "success"}
auto_ok = {"event": "workflow_dispatch", "actor": "github-actions[bot]", "status": "completed", "conclusion": "success"}
auto_bad = dict(auto_ok, conclusion="failure")
# 16 Nov 2026 is EST (UTC-5): 04:52 ET = 09:52Z
check("before 04:52 ET -> not due", D(4, 52, U("2026-11-16T09:51:00"), []) is False)
check("at 04:52 ET with no runs -> due", D(4, 52, U("2026-11-16T09:52:00"), []) is True)
check("MANUAL runs today never block or postpone it", D(4, 52, U("2026-11-16T10:00:00"), [man_ok] * 14) is True)
check("an automatic success today -> not due again (one a day)", D(4, 52, U("2026-11-16T15:00:00"), [auto_ok]) is False)
check("a schedule-event success counts as automatic", D(4, 52, U("2026-11-16T15:00:00"), [dict(auto_ok, event="schedule", actor="x")]) is False)
check("a run in progress -> wait", D(4, 52, U("2026-11-16T10:00:00"), [dict(man_ok, status="in_progress", conclusion=None)]) is False)
check("a failed automatic run is retried", D(4, 52, U("2026-11-16T10:00:00"), [auto_bad]) is True)
check("but at most 3 automatic attempts a day", D(4, 52, U("2026-11-16T12:00:00"), [auto_bad] * 3) is False)
check("tick down at 04:52, back at 14:00 -> still delivers that day", D(4, 52, U("2026-11-16T19:00:00"), []) is True)
# daylight saving: 1 Jul 2026 is EDT (UTC-4): 04:52 ET = 08:52Z
check("summer: 08:51Z (04:51 EDT) -> not due", D(4, 52, U("2026-07-01T08:51:00"), []) is False)
check("summer: 08:52Z (04:52 EDT) -> due", D(4, 52, U("2026-07-01T08:52:00"), []) is True)
# DST end day 1 Nov 2026 (clocks back at 02:00): 04:52 EST = 09:52Z
check("DST change day keeps 04:52 local", D(4, 52, U("2026-11-01T09:51:00"), []) is False and D(4, 52, U("2026-11-01T09:52:00"), []) is True)
check("the report and dashboard are daily jobs, not interval jobs",
      "p2-audit.yml" in tick.DAILY_ET and "clv-dashboard.yml" in tick.DAILY_ET and
      "p2-audit.yml" not in tick.JOBS and "clv-dashboard.yml" not in tick.JOBS)
import yaml
for f in ("p2-audit", "clv-dashboard"):
    on = yaml.safe_load(open(f".github/workflows/{f}.yml"))[True]
    check(f"{f}: tick is its only scheduler (no cron, no workflow_run)", "schedule" not in on and "workflow_run" not in on, list(on))
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_tick_daily: all passed (simulated - proves the rule, not a delivered run)")
