#!/usr/bin/env python3
"""
TICK (Nov 2, 2026). GitHub's own cron barely fires in this repo (nba-model last ran 14:26Z, x2-tag once, slow-hr never),
so sharp-monitor - which cron-job.org starts every 5 minutes - calls this to start the paper / measurement jobs that are
due. A job is due when its last run (any trigger) started at least its interval ago and none is queued or running.
Read-only jobs, paper lanes, and (since Nov 5) the deadman monitor: nothing here places, sizes or changes a bet.
The deadman is the one entry that can push a notification - it reports that execution looks dead, which is the
whole point of it, and it still touches no bet. The log prints counts only.
"""
import json
import subprocess
from datetime import datetime, timedelta, timezone

JOBS = {   # workflow file: minimum minutes between runs (matches each workflow's own cron)
    "nba-model.yml": 20,
    "x2-tag.yml": 30,
    "clv-ledger.yml": 120,
    "slow-hr.yml": 360,
    "plimit-logger.yml": 1440,
    "exchange-lag.yml": 1440,
    "hcache-fill.yml": 1440,   # Peter 15:24: keep downloading history so models run from disk
    "liquidity-monitor.yml": 5,   # Peter Nov 3 10:27 "yes": exchange scan every ~5 min (cron-job.org still starts :00/:10)
    # Nov 5: the firing inventory found deadman delivering 11 runs against 288 claimed (3.8%) - it
    # was never registered here, so it ran only on the cron that barely fires. Two consequences,
    # both silent: it cannot see a 45-minute executor outage while checking every 5-8 h, and its
    # alert condition "(gap - 45) % 60 < 15" is a 15-minute-wide window that ASSUMES a 15-minute
    # cadence - at 5-8 h intervals it is false about three times in four even with the executor
    # down, so the watcher could check during an outage and still say nothing. Restoring the
    # cadence restores the alert rule as written; the rule itself is untouched.
    # deadman.py returns before 8 AM ET, so overnight dispatches cost one no-op run each.
    "deadman.yml": 15,
}
BUSY = {"queued", "in_progress", "waiting", "pending", "requested"}


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=40)
    return r.returncode, r.stdout


def main():
    now = datetime.now(timezone.utc)
    started = skipped = 0
    for wf, mins in JOBS.items():
        try:
            rc, out = gh("run", "list", "--workflow", wf, "--limit", "1", "--json", "createdAt,status")
            if rc != 0:
                skipped += 1
                continue
            runs = json.loads(out or "[]")
            if runs and runs[0].get("status") in BUSY:
                continue
            last = datetime.fromisoformat(runs[0]["createdAt"].replace("Z", "+00:00")) if runs else None
            if last is None or now - last >= timedelta(minutes=mins - 2):
                rc, _ = gh("workflow", "run", wf, "--ref", "main")
                started += rc == 0
                skipped += rc != 0
        except Exception:
            skipped += 1
    print(f"tick: started {started}, errors {skipped}")   # counts only


if __name__ == "__main__":
    main()
