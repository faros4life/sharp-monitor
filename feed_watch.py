#!/usr/bin/env python3
"""FEED WATCH - independent heartbeat for live-feed integrity (Peter, Nov 26 2026: "Implement feed-failure, quota and
outage warnings immediately. Use an independent heartbeat so warnings work even when the feed itself fails. Include
recovery notifications.")

Why: The Odds API quota ran out at 6:00 AM ET on Nov 26 and the alert feed failed 57 runs in a row over 4 h 40 min
with no warning to anyone. A failing feed cannot report its own failure, so this job watches from outside: it runs on
its own schedule AND after every liquidity-monitor run (a separate feed), reads GitHub's run history, and alerts
Telegram + ntfy through executor.tg_push.

Checks (active hours 9 AM - midnight ET for gaps; failures and quota always):
  FEED_FAIL      latest sharp-monitor run failed (2+ in a row)    cause QUOTA when its log shows HTTP 401/429
  FEED_GAP       no successful sharp-monitor run for GAP_FEED_MIN
  LIQ_GAP        no successful liquidity-monitor run for GAP_LIQ_MIN (Dogs' feed)
  EXEC_GAP       no completed executor run for GAP_EXEC_MIN
  QUOTA_50/70/80 The Odds API credits used crossed 50 / 70 / 80 % of ODDS_QUOTA (credits_left from odds_screen.json)
Each condition alerts ONCE when it starts and sends a RECOVERED message when it clears. State: feed_watch_state.json in
the Actions cache. TEST=1 sends one test warning and one test recovery through both channels and reports delivery.
Log: counts only.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

REPO = os.environ.get("GITHUB_REPOSITORY") or "faros4life/sharp-monitor"
STATE = os.environ.get("FW_STATE") or "fw_state/feed_watch_state.json"
GAP_FEED_MIN = int(os.environ.get("GAP_FEED_MIN") or "15")
GAP_LIQ_MIN = int(os.environ.get("GAP_LIQ_MIN") or "25")
GAP_EXEC_MIN = int(os.environ.get("GAP_EXEC_MIN") or "25")
QUOTA = int(os.environ.get("ODDS_QUOTA") or "5000000")
ET_OFF = timedelta(hours=-5)


def tp(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None


def runs(wf, n=6):
    out = subprocess.run(["gh", "run", "list", "-R", REPO, "-w", wf, "-L", str(n), "--json",
                          "databaseId,createdAt,updatedAt,status,conclusion"], capture_output=True, text=True,
                         timeout=60)
    if out.returncode:
        raise RuntimeError(f"gh run list {wf} failed")
    return json.loads(out.stdout or "[]")


def log_has(run_id, needles):
    out = subprocess.run(["gh", "run", "view", "-R", REPO, str(run_id), "--log-failed"], capture_output=True,
                         text=True, timeout=90)
    t = out.stdout or ""
    return any(n in t for n in needles)


def active(now):
    return 9 <= (now + ET_OFF).hour <= 23


def evaluate(now, feed, liq, exe, credits_left, quota=QUOTA, quota_cause=None, health=None):
    """{condition: detail} currently TRUE. Pure given its inputs (run lists newest first).

    `health` is sharp_monitor's feed_health block out of alerts.json. Nov 26: every check below it
    reads RUN CONCLUSIONS, which caught the Nov 26 outage only because those runs honestly failed. A
    run that exits 0 having fetched nothing is invisible to all of them, and that is the case Peter
    named first - a rewritten alerts.json is not proof of fresh data. FEED_STALE reads the last
    successful UPSTREAM fetch instead, so it fires behind a green run and a freshly written file."""
    bad = {}
    if health is not None:
        last = tp(health["last_fetch_ok_utc"]) if health.get("last_fetch_ok_utc") else None
        if last is None:
            bad["FEED_STALE"] = "the feed has never recorded a successful upstream fetch"
        elif (now - last) > timedelta(minutes=GAP_FEED_MIN):
            bad["FEED_STALE"] = (f"last SUCCESSFUL upstream fetch was "
                                 f"{round((now - last).total_seconds() / 60)} min ago "
                                 f"(state {health.get('state')}) - runs may still be green")
        if health.get("quota_exhausted"):
            cl = health.get("credits_remaining")
            bad["QUOTA_OUT"] = ("The Odds API credits exhausted - the feed has stopped fetching"
                                + (f" ({cl:,} left)" if isinstance(cl, (int, float)) else " (balance unavailable)"))
        elif health.get("state") == "PARTIAL":
            bad["FEED_PARTIAL"] = ("upstream fetch stopped short - "
                                   + (health.get("reason") or "not all due sports were fetched"))
        elif health.get("state") == "NO_EVENTS":
            bad["FEED_EMPTY"] = ("upstream fetch succeeded but returned NO events - "
                                 "not the same as a quiet board with nothing qualifying")
    done = [r for r in feed if r.get("status") == "completed"]
    fails = 0
    for r in done:
        if r.get("conclusion") == "failure":
            fails += 1
        else:
            break
    if fails >= 2:
        bad["FEED_FAIL"] = f"alert feed failed {fails} runs in a row" + (
            " - The Odds API refused the key (quota or key: HTTP 401/429)" if quota_cause else "")
    ok = [tp(r["createdAt"]) for r in done if r.get("conclusion") == "success"]
    if active(now):
        if not ok or (now - max(ok)) > timedelta(minutes=GAP_FEED_MIN):
            mins = round((now - max(ok)).total_seconds() / 60) if ok else None
            bad["FEED_GAP"] = f"no successful alert-feed run for {mins} min"
        lok = [tp(r["createdAt"]) for r in liq if r.get("conclusion") == "success"]
        if not lok or (now - max(lok)) > timedelta(minutes=GAP_LIQ_MIN):
            bad["LIQ_GAP"] = (f"no successful liquidity-feed run for "
                              f"{round((now - max(lok)).total_seconds() / 60) if lok else '?'} min (Dogs' feed)")
        eok = [tp(r["createdAt"]) for r in exe if r.get("status") == "completed"]
        if not eok or (now - max(eok)) > timedelta(minutes=GAP_EXEC_MIN):
            bad["EXEC_GAP"] = (f"no completed executor run for "
                               f"{round((now - max(eok)).total_seconds() / 60) if eok else '?'} min")
    if isinstance(credits_left, (int, float)) and quota:
        used = 1 - credits_left / quota
        for lvl in (80, 70, 50):
            if used >= lvl / 100:
                bad[f"QUOTA_{lvl}"] = (f"The Odds API: {100 * used:.0f}% of the monthly quota used "
                                       f"({credits_left:,.0f} credits left of {quota:,})")
                break
    return bad


def transitions(prev, now_bad):
    """(started, cleared): conditions to alert and to report as recovered."""
    started = {k: v for k, v in now_bad.items() if k not in prev}
    cleared = [k for k in prev if k not in now_bad]
    # A quota LEVEL stepping up (50 -> 70) is not a recovery of the lower level. Nov 26: this used to
    # int() the suffix of anything starting with QUOTA_, so the new QUOTA_OUT condition crashed the
    # whole monitor on its first transition - a watchdog that dies on an unexpected key is worse than
    # one that misses, so only numeric levels are laddered and every other key passes through.
    def _lvl(k):
        tail = k.split("_", 1)[1] if "_" in k else ""
        return int(tail) if tail.isdigit() else None
    levels = [v for v in (_lvl(k) for k in now_bad if k.startswith("QUOTA_")) if v is not None]
    hi = max(levels or [0])
    cleared = [k for k in cleared
               if not (k.startswith("QUOTA_") and (_lvl(k) is not None) and _lvl(k) < hi)]
    return started, cleared


def send(title, text):
    import executor as ex
    ex.tg_push(title, text)
    return dict(ex.NOTIFY)


def main():
    now = datetime.now(timezone.utc)
    if (os.environ.get("TEST") or "").strip() == "1":
        a = send("FEED WATCH TEST - warning", "TEST: feed-watch warning path. No real problem - this is a test.")
        b = send("FEED WATCH TEST - recovered", "TEST: feed-watch recovery path. No real problem - this is a test.")
        print(f"TEST sent: delivery counts {b}")
        return 0
    try:
        prev = json.load(open(STATE))
    except (OSError, ValueError):
        prev = {}
    try:
        feed, liq, exe = runs("sharp-monitor.yml", 6), runs("liquidity-monitor.yml", 4), runs("executor-dry-run.yml", 4)
    except Exception as e:
        send("FEED WATCH: cannot read GitHub run history", f"feed-watch could not read run history ({type(e).__name__})."
             " Feed health is UNKNOWN until this clears.")
        print("run history unreadable - warned")
        return 1
    cause = None
    last = next((r for r in feed if r.get("status") == "completed"), None)
    if last and last.get("conclusion") == "failure":
        try:
            cause = log_has(last["databaseId"], ("HTTP Error 401", "HTTP Error 429"))
        except Exception:
            cause = None
    try:
        credits_left = (json.load(open("odds_screen.json")) or {}).get("credits_left")
    except (OSError, ValueError):
        credits_left = None
    try:   # Nov 26: the feed's own account of whether the UPSTREAM fetch worked
        health = (json.load(open("alerts.json")) or {}).get("feed_health")
    except (OSError, ValueError):
        health = None
    if health is None:
        print("feed_health missing from alerts.json - staleness cannot be checked this run")
    bad = evaluate(now, feed, liq, exe, credits_left, QUOTA, cause, health)
    started, cleared = transitions(prev, bad)
    for k, v in started.items():
        send(f"FEED WARNING: {k}", f"FEED WARNING ({k}): {v}.\nChecked {(now + ET_OFF):%-I:%M %p} ET by the "
             f"independent feed watch.")
    for k in cleared:
        send(f"FEED RECOVERED: {k}", f"RECOVERED ({k}): back to normal as of {(now + ET_OFF):%-I:%M %p} ET "
             f"(was: {prev[k]}).")
    os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
    json.dump(bad, open(STATE, "w"))
    print(f"feed watch: open conditions {sorted(bad)} | new {len(started)} | recovered {len(cleared)} | "
          f"credits_left known {credits_left is not None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
