#!/usr/bin/env python3
"""
NOVIG SNAPSHOT HEARTBEAT (Peter, Nov 11, item 3). READ-ONLY. No bet, no order, no rule change.

WHAT IT CATCHES THAT THE WINDOWS SIDE CANNOT. The home PC's runner is now a Scheduled Task with
999 restarts, so a DEAD process restarts itself. Nothing on that machine notices a runner that is
alive and silently not reporting - a wedged job, a revoked token, a network that is up but cannot
reach GitHub. From the cloud the symptom is identical and visible: snapshot_utc stops advancing.

WHAT IT READS. The same snapshot the executor reads, by the same route - SNAP_URL with
NOVIG_SNAPSHOT_TOKEN - so a read that fails here is a read that would fail for the executor. No
Novig API call is made and no position data is printed.

THE BAR. STALE_MIN defaults to 35 minutes: the executor's own SNAP_MAX_MIN is 15 and the runner
is on a 5-minute schedule, so 35 is roughly two missed cycles past the point the executor begins
refusing to trade on it. Alerting at 15 would fire on ordinary jitter.

ALERTING, deliberately quiet. Peter, Oct 27: no new alert type unless it is actionable. This one is
- a stale snapshot means the executor is already holding plays. It pushes ONCE when the snapshot
goes stale and ONCE when it recovers, never on every run, by keeping a one-line state file on the
heartbeat branch. A push failure never fails the job: the point is to report, not to become another
thing that breaks.

FAIL-CLOSED STAYS WITH THE EXECUTOR. This script changes nothing about trading. novig_positions()
already returns None on a bad or stale read and the play is HELD, not placed. This only tells Peter
that it is happening.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

SNAP_URL = ("https://api.github.com/repos/faros4life/novig-runner/contents/"
            "snapshot/novig_positions.json?ref=main")
STATE_PATH = "heartbeat/novig_state.json"
STALE_MIN = float(os.environ.get("NOVIG_STALE_MIN", "") or "35")


def push(title, body):
    """Same ntfy topic as every other phone alert. Never raises: a failed push must not fail the run."""
    topic = (os.environ.get("NTFY_TOPIC") or "").strip()
    if not topic:
        print("no NTFY_TOPIC set - nothing pushed")
        return False
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
            headers={"Title": title.encode("ascii", "ignore").decode(),
                     "Priority": "high", "Tags": "warning"})
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception as ex:
        print(f"push failed: {type(ex).__name__}: {str(ex)[:60]}")
        return False


def read_snapshot():
    """(age_minutes, error). age is None when the snapshot cannot be read - never 0, which would
    read as 'perfectly fresh' and silence the alarm exactly when it matters most."""
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    if not tok:
        return None, "NOVIG_SNAPSHOT_TOKEN not set"
    try:
        req = urllib.request.Request(SNAP_URL, headers={
            "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.raw+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor-heartbeat"})
        with urllib.request.urlopen(req, timeout=20) as r:
            snap = json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:
        return None, f"HTTP {ex.code} reading the snapshot"
    except Exception as ex:
        return None, f"{type(ex).__name__} reading the snapshot"
    ts = snap.get("snapshot_utc")
    if not ts:
        return None, "snapshot carries no snapshot_utc"
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None, f"snapshot_utc unparseable ({str(ts)[:30]})"
    return (datetime.now(timezone.utc) - when).total_seconds() / 60.0, None


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(d):
    try:
        os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        return True
    except Exception as ex:
        print(f"state not written ({type(ex).__name__}) - the next run may repeat this alert")
        return False


def main():
    now = datetime.now(timezone.utc)
    age, err = read_snapshot()
    prev = load_state()
    was_bad = bool(prev.get("stale"))

    if err is not None:
        bad, why = True, err
        age_txt = "unknown"
    else:
        bad = age > STALE_MIN
        why = f"snapshot is {age:.0f} min old (limit {STALE_MIN:.0f})"
        age_txt = f"{age:.0f} min"

    # counts and minutes only - no positions, no dollars, nothing account-identifying
    print(f"novig heartbeat: age {age_txt}, stale={bad}, was_stale={was_bad}, limit {STALE_MIN:.0f} min")
    if err:
        print(f"  read problem: {err}")

    pushed = False
    if bad and not was_bad:
        pushed = push("NOVIG SNAPSHOT STALE",
                      f"The home runner's positions snapshot has stopped updating: {why}.\n"
                      f"The bot HOLDS plays rather than betting on a stale read, so nothing is at risk - "
                      f"but no Novig play can go live until it recovers.\n"
                      f"Check the PC is awake and the GitHub Actions Runner task is running.")
    elif was_bad and not bad:
        pushed = push("Novig snapshot recovered",
                      f"The positions snapshot is updating again ({age_txt} old). Novig plays can go live.")

    save_state({"stale": bad, "why": why, "checked_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "age_min": (None if age is None else round(age, 1)),
                "alerted": pushed or (was_bad and bad)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
