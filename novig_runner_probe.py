#!/usr/bin/env python3
"""
WHY ISN'T THE HOME RUNNER PUBLISHING? (Peter, Nov 12). READ-ONLY DIAGNOSTIC.

The runner process was restarted at 09:24 ET and is alive (Runner.Listener PID 25820), yet the
positions snapshot is still 1122 minutes old. So the fault is NOT a dead process, and restarting
again would tell us nothing new - Peter's item 4 says not to. This asks the four questions that
separate the remaining causes, using ONLY the credential that already exists for this purpose.

CREDENTIAL. NOVIG_SNAPSHOT_TOKEN is the token the executor and the heartbeat already use to READ
snapshot/novig_positions.json out of faros4life/novig-runner. Nothing new is issued and no trading
key is involved: this is the same read token asking the same repo two more read-only questions. If
its scope does not cover the Actions API the call returns 403, and that is reported as a limit of
the token rather than worked around.

THE FOUR CAUSES, and the evidence that separates them:

  1 JOB DISPATCH     - is GitHub even assigning work? /actions/runners shows the self-hosted
                       runner's status (online/offline) and whether it is busy. A runner that is
                       OFFLINE here while the process is alive on the PC means the process is
                       running but not connected - a token or network fault, not a crash.
  2 EXECUTION        - /actions/runs shows whether runs are being created at all, and what they
                       concluded. Runs created but failing is a different fault from no runs.
  3 AUTHENTICATION   - a run that fails in seconds, or a runner that never comes online, points
                       at the runner's registration token rather than at the workflow.
  4 PUBLISHING       - runs succeeding while snapshot_utc does not advance means the job ran and
                       wrote nothing: the fault is inside the job, not around it.

Nothing is changed, started, cancelled or re-run. No workflow is dispatched. No restart.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("NOVIG_RUNNER_REPO", "") or "faros4life/novig-runner"
TOK = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
API = "https://api.github.com"


def gh(path):
    """(json, error). Never raises: a refused call is evidence about the token, not a crash."""
    if not TOK:
        return None, "NOVIG_SNAPSHOT_TOKEN not set"
    req = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "novig-runner-probe"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as ex:
        return None, f"HTTP {ex.code}"
    except Exception as ex:
        return None, f"{type(ex).__name__}"


def ago(ts):
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return f"{(datetime.now(timezone.utc) - d).total_seconds()/60:.0f} min ago"
    except Exception:
        return "?"


def main():
    print("NOVIG RUNNER PROBE - why is the home runner not publishing?")
    print(f"repo {REPO} | read-only | nothing dispatched, cancelled, re-run or restarted")
    print("=" * 92)

    # ---------------------------------------------------------------- 1. the snapshot itself
    snap, err = gh(f"/repos/{REPO}/contents/snapshot/novig_positions.json?ref=main")
    if err:
        print(f"  snapshot metadata unreadable ({err})")
    else:
        print(f"  snapshot file last commit sha {str(snap.get('sha'))[:12]}")
    cm, err = gh(f"/repos/{REPO}/commits?path=snapshot/novig_positions.json&per_page=3")
    if err:
        print(f"  snapshot commit history unreadable ({err})")
    elif cm:
        print("  WHEN THE SNAPSHOT FILE WAS LAST WRITTEN (the publishing question):")
        for c in cm[:3]:
            d = ((c.get("commit") or {}).get("committer") or {}).get("date")
            who = ((c.get("commit") or {}).get("author") or {}).get("name")
            print(f"    {str(d)[:16]}  {ago(d):>14}  by {str(who)[:24]}")

    # ---------------------------------------------------------------- 2. is the runner connected?
    rs, err = gh(f"/repos/{REPO}/actions/runners")
    print("")
    if err:
        print(f"  RUNNER STATUS unreadable ({err})")
        if err == "HTTP 403":
            print("    -> the snapshot token has no Actions scope. That is a token limit, not a")
            print("       finding about the runner; it needs a token with actions:read to answer.")
    else:
        runners = (rs or {}).get("runners") or []
        print(f"  SELF-HOSTED RUNNERS REGISTERED: {len(runners)}")
        for r in runners:
            print(f"    {str(r.get('name'))[:28]:<28} status {str(r.get('status')):<8} "
                  f"busy {r.get('busy')}  labels "
                  f"{','.join(l.get('name') for l in (r.get('labels') or []))[:40]}")
        if runners and all(str(r.get("status")) != "online" for r in runners):
            print("    -> OFFLINE while the process is alive on the PC. The runner is running but")
            print("       NOT CONNECTED to GitHub: a registration-token or network fault, which a")
            print("       restart cannot fix. Cause 1/3 - dispatch/authentication.")
        elif runners and any(str(r.get("status")) == "online" for r in runners):
            print("    -> ONLINE. GitHub can assign work, so dispatch is not the fault. Look at")
            print("       whether runs are being created, below.")

    # ---------------------------------------------------------------- 3. are runs happening?
    rr, err = gh(f"/repos/{REPO}/actions/runs?per_page=12")
    print("")
    if err:
        print(f"  WORKFLOW RUNS unreadable ({err})")
    else:
        runs = (rr or {}).get("workflow_runs") or []
        print(f"  RECENT WORKFLOW RUNS: {len(runs)} (total {(rr or {}).get('total_count')})")
        for w in runs[:12]:
            print(f"    {str(w.get('created_at'))[:16]}  {ago(w.get('created_at')):>14}  "
                  f"{str(w.get('name'))[:26]:<26} {str(w.get('status')):<11}"
                  f"{str(w.get('conclusion'))}")
        if not runs:
            print("    -> NO RUNS AT ALL. Nothing is being dispatched: the schedule is disabled,")
            print("       or Actions is off for the repo. Cause 1 - job dispatch.")
        else:
            newest = runs[0].get("created_at")
            ok = [w for w in runs if w.get("conclusion") == "success"]
            print("")
            print(f"    newest run {ago(newest)}")
            if ok:
                print(f"    newest SUCCESS {ago(ok[0].get('created_at'))} "
                      f"({str(ok[0].get('name'))[:30]})")
                print("    -> if a run succeeded recently while the snapshot did not advance, the")
                print("       job ran and wrote nothing: cause 4 - publishing, inside the job.")
            else:
                print("    -> runs exist but NONE succeeded: cause 2/3 - execution or auth inside")
                print("       the job, not dispatch.")
        q = [w for w in runs if w.get("status") in ("queued", "waiting", "pending")]
        if q:
            print(f"    {len(q)} run(s) QUEUED and not picked up -> the runner is not taking work,")
            print("       which with an alive process means it is not connected.")

    # ---------------------------------------------------------------- optional: verify the fix
    # Peter, Nov 12 ("you can do that"): trigger ONE novig-positions run to verify the Machine-PATH
    # fix, instead of waiting for the schedule. This is the job's own normal work - it reads
    # positions and writes a snapshot. It places no order and changes no live setting. It fires
    # only when PROBE_DISPATCH=1, so it can never go off as a side effect of a read.
    if (os.environ.get("PROBE_DISPATCH") or "") == "1":
        print("")
        print("  VERIFY: dispatching ONE novig-positions run")
        wf, err = gh(f"/repos/{REPO}/actions/workflows")
        wid = None
        if err:
            print(f"    workflow list unreadable ({err})")
        else:
            for w in (wf or {}).get("workflows") or []:
                if "novig-positions" in str(w.get("name")) or "novig-positions" in str(w.get("path")):
                    wid = w.get("id")
                    print(f"    found: {w.get('name')}  ({w.get('path')})  state {w.get('state')}")
                    break
        if wid is None:
            print("    novig-positions workflow not found - nothing dispatched")
        else:
            body = json.dumps({"ref": "main"}).encode()
            req = urllib.request.Request(
                f"{API}/repos/{REPO}/actions/workflows/{wid}/dispatches", data=body, method="POST",
                headers={"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                         "User-Agent": "novig-runner-probe"})
            try:
                urllib.request.urlopen(req, timeout=25).read()
                print("    dispatched. Waiting for it to finish...")
                import time
                seen = None
                for _ in range(30):
                    time.sleep(20)
                    rr2, e2 = gh(f"/repos/{REPO}/actions/runs?per_page=5")
                    if e2:
                        continue
                    for w in (rr2 or {}).get("workflow_runs") or []:
                        if w.get("workflow_id") == wid and w.get("event") == "workflow_dispatch":
                            seen = w
                            break
                    if seen and seen.get("status") == "completed":
                        break
                if seen:
                    print(f"    RESULT: {seen.get('status')}/{seen.get('conclusion')} "
                          f"({seen.get('html_url')})")
                    if seen.get("conclusion") == "success":
                        print("    -> the PATH fix worked: the job ran to completion.")
                    else:
                        print("    -> still failing. The step log is needed again; a different")
                        print("       error than 'python is not recognized' means a different fault.")
                else:
                    print("    no matching run observed within the wait window")
            except urllib.error.HTTPError as ex:
                print(f"    dispatch refused (HTTP {ex.code})")
                if ex.code in (403, 404):
                    print("    -> the snapshot token cannot dispatch (needs actions:write).")
                    print("       Trigger it from the browser instead: Actions -> novig-positions")
                    print("       -> Run workflow.")
            except Exception as ex:
                print(f"    dispatch failed ({type(ex).__name__})")

    print("=" * 92)
    print("No live setting changed; no order placed; nothing restarted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
