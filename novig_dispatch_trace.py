#!/usr/bin/env python3
"""WHAT SUBMITTED THE LOUISIANA NOVIG ORDER? (Peter, Nov 12). READ-ONLY. NOTHING DISPATCHED.

The 11:57 recon showed a real filled Novig order while book_live.novig_place() refuses every
submission (EXEC_NOVIG_SUBMIT is not even passed to executor-dry-run.yml), so some other path
reached the home runner. This traces that one order back to the run that placed it.

Read-only by construction: every call below is a GET. No workflow is dispatched, cancelled or
re-run, no order is placed, amended or cancelled, and no live setting is touched. The credential
is NOVIG_SNAPSHOT_TOKEN, which the Nov 12 audit measured as admin on the runner repo - that is the
finding being acted on, not a licence to use it for anything but reads.

Three questions, in order:
  1 WHICH RUN       - novig-live-order runs in the window, with event and actor. A workflow_dispatch
                      names the identity that sent it, which is what "what submitted it" means.
  2 WHICH COMMIT    - snapshot/novig_orders.json commit history. The runner appends its result row
                      and commits, so the commit that carries this order pins the run by time.
  3 WHICH CHECKOUT  - whether that run checks out sharp-monitor. novig_live_order.py lives in the
                      PUBLIC repo, so if the runner executes this repo's copy, the runner-side
                      authorization guard Peter asked for can be added here. If it runs its own
                      private copy, it cannot, and that has to be said plainly rather than assumed.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO

REPO = os.environ.get("NOVIG_RUNNER_REPO") or "faros4life/novig-runner"
TOK = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
API = "https://api.github.com"
# The order the 11:57 recon reported as FILLED. Overridable so the same trace answers the next one.
CID = os.environ.get("TRACE_CLIENT_ID") or "adade61d-8fb6-4f2b-980e-6a7ca126af22"
OID = os.environ.get("TRACE_ORDER_ID") or "01a1d042-e4b5-7423-a0bf-785747f314f6"
OUTCOME = os.environ.get("TRACE_OUTCOME_ID") or "01a1b942-e9c6-7b61-ab02-9d851a12e54e"
DAYS = int(os.environ.get("TRACE_DAYS") or "3")


def gh(path, raw=False):
    """(payload, error). Never raises: a refused call is evidence about the token, not a crash."""
    if not TOK:
        return None, "NOVIG_SNAPSHOT_TOKEN not set"
    req = urllib.request.Request(API + path if path.startswith("/") else path, headers={
        "Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "novig-dispatch-trace"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read()
            return (b if raw else (json.loads(b.decode()) if b else {})), None
    except urllib.error.HTTPError as ex:
        return None, f"HTTP {ex.code}"
    except Exception as ex:
        return None, f"{type(ex).__name__}"


def main():
    print("NOVIG DISPATCH TRACE - what submitted the Louisiana order?")
    print(f"repo {REPO} | READ-ONLY (GET only) | nothing dispatched, cancelled, re-run or placed")
    print(f"tracing client_id {CID}")
    print("=" * 96)
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------ 1. the runs
    print()
    print(f"1. novig-live-order RUNS since {since}")
    print("-" * 96)
    runs, err = gh(f"/repos/{REPO}/actions/runs?per_page=100&created=%3E{since}")
    hits = []
    if err:
        print(f"  runs unreadable ({err}) - CANNOT VERIFY which run placed it")
    else:
        allr = (runs or {}).get("workflow_runs") or []
        print(f"  {len(allr)} run(s) of any workflow in the window")
        for r in allr:
            nm = str(r.get("name") or "")
            if "live-order" not in nm.lower():
                continue
            hits.append(r)
            print(f"  {r.get('id')}  {nm}  event={r.get('event')}  "
                  f"{r.get('status')}/{r.get('conclusion')}  {r.get('created_at')}")
            print(f"      actor={(r.get('actor') or {}).get('login')}  "
                  f"triggering_actor={(r.get('triggering_actor') or {}).get('login')}")
        if not hits:
            print("  NO novig-live-order run in the window. Then this order was not placed by the")
            print("  runner workflow in this period - it came from somewhere else entirely.")
        # Every workflow that exists here, so a second order path cannot hide behind a name.
        print()
        print("  workflows present in the runner repo:")
        wf, e2 = gh(f"/repos/{REPO}/actions/workflows")
        if e2:
            print(f"    unreadable ({e2})")
        else:
            for w in (wf or {}).get("workflows") or []:
                print(f"    {w.get('name'):<28} {w.get('path'):<44} {w.get('state')}")

    # ------------------------------------------------------------------ 2. the commit
    print()
    print("2. snapshot/novig_orders.json COMMITS (the runner commits its own result row)")
    print("-" * 96)
    cm, err = gh(f"/repos/{REPO}/commits?path=snapshot/novig_orders.json&per_page=20&since={since}")
    if err:
        print(f"  commits unreadable ({err})")
    else:
        for c in cm or []:
            d = ((c.get("commit") or {}).get("committer") or {}).get("date")
            msg = str((c.get("commit") or {}).get("message") or "").splitlines()[0]
            who = (c.get("author") or {}).get("login") or ((c.get("commit") or {}).get("author") or {}).get("name")
            print(f"  {d}  {str(msg)[:52]:<52} by {who}")

    # ------------------------------------------------------------------ 3. the checkout
    print()
    print("3. DOES THE RUNNER EXECUTE THIS REPO'S novig_live_order.py?")
    print("-" * 96)
    print("  (decides whether the runner-side authorization guard can be added in sharp-monitor)")
    target = None
    for r in hits:
        if str(r.get("conclusion")) == "success":
            target = r
            break
    target = target or (hits[0] if hits else None)
    if not target:
        print("  no run to inspect")
    else:
        print(f"  inspecting run {target.get('id')} ({target.get('created_at')})")
        blob, err = gh(f"/repos/{REPO}/actions/runs/{target['id']}/logs", raw=True)
        if err:
            print(f"  logs unreadable ({err})")
        else:
            try:
                txt = []
                with zipfile.ZipFile(BytesIO(blob)) as z:
                    for n in z.namelist()[:40]:
                        try:
                            txt.append(z.read(n).decode("utf-8", "replace"))
                        except Exception:
                            pass
                body = "\n".join(txt)
                for label, pat in (("checks out sharp-monitor", r"sharp-monitor"),
                                   ("runs novig_live_order", r"novig_live_order"),
                                   ("this order's outcome_id", re.escape(OUTCOME)),
                                   ("this order's client_id", re.escape(CID)),
                                   ("this order's order_id", re.escape(OID))):
                    print(f"    {label:<28} {'FOUND' if re.search(pat, body) else 'not in log'}")
                for ln in body.splitlines():
                    s = ln.strip()
                    if re.search(r"IN_(OUTCOME|PRICE|QTY|TIF|TTL|CLIENT|KEY|LABEL)\s*:", s) \
                            or "Novig order:" in s or "repository: " in s:
                        print(f"    | {s[:110]}")
            except Exception as ex:
                print(f"  log archive unreadable ({type(ex).__name__})")

    print()
    print("=" * 96)
    print("READ-ONLY: no workflow dispatched, no order placed, no live setting changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
