#!/usr/bin/env python3
"""
Dead-man alert (Oct 30, 2026; Muse via Peter). With sharp pushes muted, a dead executor looks like a quiet day.
Every 15 min, 8 AM - midnight ET: if the executor (executor-dry-run.yml) hasn't STARTED a run in 45+ minutes, or its
last 3 finished runs all failed, push Peter (ntfy + Telegram), at most about once an hour per problem.
Reads only GitHub's run list (GITHUB_TOKEN, actions:read). Nothing financial anywhere.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REPO = os.environ.get("GITHUB_REPOSITORY", "faros4life/sharp-monitor")
WF = "executor-dry-run.yml"
GAP_MIN = int(os.environ.get("DEADMAN_GAP_MIN") or "45")


def gh(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                               "Accept": "application/vnd.github+json", "User-Agent": "sharp-monitor"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def alert(title, body):
    topic = (os.environ.get("NTFY_TOPIC") or "").strip()
    if topic:
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
                                   headers={"Title": title, "Priority": "high", "Tags": "skull"}), timeout=15).read()
        except Exception:
            print("ntfy failed")
    tok, chat = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip(), (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if tok and chat:
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                   data=json.dumps({"chat_id": chat, "text": f"{title}\n{body}"}).encode(), method="POST",
                                   headers={"Content-Type": "application/json"}), timeout=15).read()
        except Exception:
            print("telegram failed")


def main():
    now = datetime.now(timezone.utc)
    et = now.astimezone(ET)
    if et.hour < 8:
        print("outside 8 AM - midnight ET: no check")
        return
    runs = gh(f"https://api.github.com/repos/{REPO}/actions/workflows/{WF}/runs?per_page=10").get("workflow_runs") or []
    if not runs:
        alert("EXECUTOR DOWN?", "No executor runs found at all. Check GitHub Actions.")
        return
    last_start = max(t(r["created_at"]) for r in runs)
    gap = (now - last_start).total_seconds() / 60
    done = [r for r in runs if r.get("status") == "completed"][:3]
    print(f"last executor start {gap:.0f} min ago; last 3 finished: {[r.get('conclusion') for r in done]}")
    if gap >= GAP_MIN and (gap - GAP_MIN) % 60 < 15:   # first at 45 min, then about hourly while it stays down
        alert("EXECUTOR DOWN?", f"No executor run in {gap:.0f} min (last start {last_start.astimezone(ET).strftime('%I:%M %p ET')}). "
              "Live bets can't go out. Check GitHub Actions / cron-job.org.")
    elif len(done) == 3 and all(r.get("conclusion") == "failure" for r in done) \
            and (now - t(done[0]["updated_at"])).total_seconds() < 15 * 60 and et.minute < 15:
        alert("EXECUTOR FAILING", "The executor's last 3 runs all failed. Live bets can't go out. Check GitHub Actions.")


if __name__ == "__main__":
    main()
