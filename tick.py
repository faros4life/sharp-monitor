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
    "liq-small-fwd.yml": 1440,   # Nov 6 (Peter): $25-50k NBA forward paper test - daily report, read-only
    "model-lab.yml": 1440,   # Nov 6 (Peter: "pull all history every night... find new trend or edge"): daily re-run on the
                             # updated cache. Read-only, hypothesis only, private email; free history calls for anything missing.
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
    # Nov 6 (Peter "fix everything that needs fixing"): the rest of the dispatcher-less set from the
    # same firing inventory. Each ran only on GitHub's cron, which this file already records as barely
    # firing, so each was delivering a few runs a day against hundreds claimed. Cadence only - none of
    # these changes what any script decides, and each matches that workflow's own cron.
    "signal-alerts.yml": 10,     # 12 of 431 (2.8%). Pushes the phone on two-signal confluence,
                                 # PREGAME: confirmed >=$100k new money on a side a sharp alert also
                                 # took. At ~4 runs a day a confluence is found hours late, past the
                                 # price and sometimes past tip - the one push path that is meant to
                                 # be actionable under Peter's "no alerts unless bot or actionable".
    # ev-sightings.yml REMOVED Nov 25, 2026. The study closed Nov 13 (Peter: "Approved. Disable
    # ev-sightings now.") and the workflow was disabled on GitHub, but it stayed in this table, so
    # tick tried to dispatch it every 10 minutes and GitHub refused every time. That pinned the log
    # at "errors 1" for twelve days and saturated the error channel: a real second failure would
    # have read as "errors 2" and gone unnoticed. Nothing was lost by the failures themselves - the
    # study was paper-only and collection was meant to stop. (The ev-sightings_2.yml duplicate the
    # old comment warned about no longer exists; its last run was Nov 12.)
    "balances-email.yml": 60,    # 11 of 72 (15.3%). Hourly by design; staleness of the balance and
                                 # open-exposure picture Muse reads. Reporting lag, not correctness.
    "ncaab-openers.yml": 30,     # 9 of 114 (10.5%). The freeze-lead measurement traced straight to
                                 # this: a game entering the window is only frozen at the next run, so
                                 # at ~4 runs a day the freeze lands hours late and 10 of 13
                                 # band-clearing disagreements were discarded as frozen-after-the-open.
                                 # AHEAD_DAYS=3 bought margin for exactly this; the cadence is the
                                 # other half of that fix.
    # Nov 6: plimit-level.yml has NO cron at all and was never registered, so the Item 56 P-limit
    # report only ever ran when someone dispatched it by hand - it last ran Nov 4 15:20 ET. That
    # silently stalled Peter's own check-in ("remind me when you have enough data", 50 graded H2
    # plays each side): the reminder fires, reads a stale email, and reschedules forever. 720 min
    # matches the twice-daily cadence the check-in expects. Paper, read-only, history-cache only.
    "plimit-level.yml": 720,
    # Nov 16 (Peter approved the scheduling fix): none of these three fired on GitHub's cron on 15 or 16 Nov,
    # and a workflow_run chain cannot fire off clv-ledger because tick starts it with GITHUB_TOKEN. All three
    # are reporting-only. The ledger is append-only (extra runs harmless; must run well inside the registry's
    # 4-day prune). p2-audit's gate keeps automatic Telegram reports to one per ET day; the dashboard's
    # committed marker keeps its email to one per ET day.
    "reporting-ledger.yml": 360,
}
# Nov 16 (Peter): DAILY jobs run once per reporting day at a fixed New York time. An interval job counts ANY run
# (a manual run restarted its 24 h clock and pushed the morning report later each time). A daily job counts only
# AUTOMATIC runs (schedule events, or dispatches by github-actions[bot] - this file), so manual runs never move it.
# America/New_York via zoneinfo, so the time holds through daylight-saving changes. If tick is down at the target
# time, the next tick that day still delivers (no lost day). At most MAX_DAILY_TRIES automatic attempts a day, so a
# job that keeps failing is not re-dispatched every 5 minutes.
DAILY_ET = {
    "clv-dashboard.yml": (4, 12),   # the dashboard's approved 04:12 ET slot; one email per ET day is its own marker
    "p2-audit.yml": (4, 52),        # the Project 2 Telegram report's approved 04:52 ET slot; its gate allows one a day
}
MAX_DAILY_TRIES = 3
BOT = "github-actions[bot]"
BUSY = {"queued", "in_progress", "waiting", "pending", "requested"}


def gh(*args):
    """Returns (rc, stdout, stderr). stderr used to be discarded, which is the whole reason a
    dispatch failure could only ever be counted and never explained (Nov 25, 2026)."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=40)
    return r.returncode, r.stdout, r.stderr


def is_automatic(run):
    return run.get("event") == "schedule" or (run.get("event") == "workflow_dispatch" and run.get("actor") == BOT)


def daily_due(hh, mm, now_utc, runs):
    """Pure. runs: this workflow's runs created on today's New York date: {event, actor, status, conclusion}."""
    from zoneinfo import ZoneInfo
    now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    if (now_et.hour, now_et.minute) < (hh, mm):
        return False
    if any(r.get("status") in BUSY for r in runs):
        return False
    auto = [r for r in runs if is_automatic(r)]
    if any(r.get("conclusion") == "success" for r in auto):
        return False
    return len(auto) < MAX_DAILY_TRIES


def today_runs(wf, now_utc):
    """This workflow's runs since New York midnight, via the API (it carries the triggering actor)."""
    from zoneinfo import ZoneInfo
    et = now_utc.astimezone(ZoneInfo("America/New_York"))
    midnight = et.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    rc, out, _ = gh("api", f"repos/{{owner}}/{{repo}}/actions/workflows/{wf}/runs?created=>="
                 f"{midnight.strftime('%Y-%m-%dT%H:%M:%SZ')}&per_page=100",
                 "--jq", "[.workflow_runs[] | {event, actor: .triggering_actor.login, status, conclusion}]")
    if rc != 0:
        raise RuntimeError("runs unreadable")
    return json.loads(out or "[]")


def dispatch(wf):
    """Dispatch one workflow. Returns "started", "disabled", or a short reason it failed.

    Nov 25, 2026: this used to be `started += rc == 0; skipped += rc != 0`, with every exception
    swallowed by a bare `except Exception: skipped += 1` and stderr discarded by gh(). A workflow
    that is DELIBERATELY disabled and one that is genuinely failing produced the same number, and
    the reason was gone. Two states with opposite remedies in one counter - a disabled workflow
    should be taken OUT of the table, a failing one should be FIXED."""
    rc, _, err = gh("workflow", "run", wf, "--ref", "main")
    if rc == 0:
        return "started"
    text = (err or "").strip()
    if "disabled" in text.lower():
        return "disabled"
    return (text.splitlines()[-1][:140] if text else f"rc={rc}, no stderr")


def main():
    now = datetime.now(timezone.utc)
    started, disabled, failed = 0, [], {}
    for wf, mins in JOBS.items():
        try:
            rc, out, err = gh("run", "list", "--workflow", wf, "--limit", "1", "--json", "createdAt,status")
            if rc != 0:
                failed[wf] = f"run list failed: {(err or '').strip().splitlines()[-1][:120] if err else rc}"
                continue
            runs = json.loads(out or "[]")
            if runs and runs[0].get("status") in BUSY:
                continue
            last = datetime.fromisoformat(runs[0]["createdAt"].replace("Z", "+00:00")) if runs else None
            if last is None or now - last >= timedelta(minutes=mins - 2):
                r = dispatch(wf)
                started += r == "started"
                if r == "disabled":
                    disabled.append(wf)
                elif r != "started":
                    failed[wf] = r
        except Exception as ex:
            failed[wf] = f"{type(ex).__name__}: {str(ex)[:100]}"
    for wf, (hh, mm) in DAILY_ET.items():
        try:
            if daily_due(hh, mm, now, today_runs(wf, now)):
                r = dispatch(wf)
                started += r == "started"
                if r == "disabled":
                    disabled.append(wf)
                elif r != "started":
                    failed[wf] = r
        except Exception as ex:
            failed[wf] = f"{type(ex).__name__}: {str(ex)[:100]}"
    # Counts only - workflow filenames and gh's own error text, never anything financial.
    print(f"tick: started {started}, disabled {len(disabled)}, errors {len(failed)}")
    for wf in sorted(disabled):
        print(f"tick: DISABLED, not dispatched (take it out of JOBS if the study is closed): {wf}")
    for wf in sorted(failed):
        print(f"tick: DISPATCH FAILED {wf}: {failed[wf]}")


if __name__ == "__main__":
    main()
