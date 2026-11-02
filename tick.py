#!/usr/bin/env python3
"""
TICK (Nov 2, 2026). GitHub's own cron barely fires in this repo (nba-model last ran 14:26Z, x2-tag once, slow-hr never),
so sharp-monitor - which cron-job.org starts every 5 minutes - calls this to start the paper / measurement jobs that are
due. A job is due when its last run (any trigger) started at least its interval ago and none is queued or running.
Read-only jobs and paper lanes only: nothing here places, sizes or changes a bet. The log prints counts only.
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
