#!/usr/bin/env python3
"""READ-ONLY probe of the Novig home-runner path. Places nothing, dispatches nothing.

Peter, Nov 12: "Verify the Novig dispatch credential, home-runner connection and result-reading
path. No real orders."

WHAT IT CHECKS
  1. NOVIG_DISPATCH_TOKEN present. It has NO fallback: without it novig_place() refuses with "no
     dispatch credential for the home runner", so an absent token is an activation blocker.
  2. The dispatch token can SEE the runner workflow - a GET on the workflow, never a POST to its
     dispatches endpoint. This proves reachability and authorisation without creating a run.
  3. The result-reading path: novig_results() against snapshot/novig_orders.json with the
     read-only NOVIG_SNAPSHOT_TOKEN. None means unreadable (fail-closed), [] means no rows yet.
  4. Reconciliation input: how many runner result rows exist, how many carry a venue order id, and
     how many are still unresolved. "No unknown submissions" cannot be concluded from zero intents,
     so this reports the rows themselves.

WHAT IT NEVER DOES: no POST to any dispatches endpoint, no order, no cancel, no write of any kind.
EXEC_NOVIG_SUBMIT is irrelevant here because nothing is submitted either way.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import book_live as bl

ok_all = True


def say(label, ok, detail=""):
    global ok_all
    ok_all = ok_all and ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" - {detail}" if detail else ""))


print("NOVIG HOME-RUNNER PROBE (read-only; nothing is dispatched or placed)")

tok = (os.environ.get("NOVIG_DISPATCH_TOKEN") or "").strip()
say("NOVIG_DISPATCH_TOKEN present", bool(tok),
    "absent -> novig_place() refuses: 'no dispatch credential for the home runner'" if not tok else "")

snap = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
say("NOVIG_SNAPSHOT_TOKEN present", bool(snap))

# 2. Reachability WITHOUT dispatching: a GET on the workflow the executor would POST to.
repo = getattr(bl, "NV_REPO", None)
say("the runner repo is configured in book_live", bool(repo), str(repo or ""))
if tok and repo:
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor"})
        with urllib.request.urlopen(req, timeout=20) as r:
            wfs = (json.loads(r.read().decode()) or {}).get("workflows") or []
        names = [w.get("path", "").rsplit("/", 1)[-1] for w in wfs]
        say("the dispatch credential can reach the runner repo", True, f"{len(wfs)} workflow(s)")
        say("the novig-live-order workflow exists",
            any("novig-live-order" in n for n in names), ", ".join(names[:6]))
    except urllib.error.HTTPError as ex:
        say("the dispatch credential can reach the runner repo", False,
            f"HTTP {ex.code} - {'token lacks access' if ex.code in (401, 403, 404) else 'see code'}")
    except Exception as ex:
        say("the dispatch credential can reach the runner repo", False, str(ex)[:70])

# 2b. POSITIONS SNAPSHOT FRESHNESS. This is the file that held every lane when it went stale: a
# stale read makes novig_positions() return None, the venue counts as blind, and no live order goes
# out on ANY venue. SNAP_MAX_MIN is the executor's own gate, which is tighter than the 35-minute
# alert, so the executor starts holding plays well before the warning arrives.
try:
    import executor as _ex
    _snap, _age = _ex._snap_read(snap)
    print(f"    positions snapshot_utc     : {_snap.get('snapshot_utc')}")
    print(f"    age                        : {_age:.1f} min   (executor gate SNAP_MAX_MIN = {_ex.SNAP_MAX_MIN})")
    say("the positions snapshot is FRESH by the executor's own gate", _age <= _ex.SNAP_MAX_MIN,
        f"{_age:.1f} min > {_ex.SNAP_MAX_MIN} min - every lane holds while this is true"
        if _age > _ex.SNAP_MAX_MIN else "")
    say("the snapshot reports itself ok", bool(_snap.get("ok", True)))
except Exception as ex:
    say("the positions snapshot is readable", False,
        f"{str(ex)[:70]} - unreadable means blind, never 'no positions'")

# 3 + 4. The result-reading path and what it currently holds.
rows = None
try:
    rows = bl.novig_results()
except Exception as ex:
    say("novig_results() did not raise", False, str(ex)[:70])

if rows is None:
    say("the result file is readable", False,
        "novig_results() returned None = UNREADABLE (fail-closed; never read as 'no orders')")
else:
    say("the result file is readable", True, f"{len(rows)} runner result row(s)")
    # Nov 12, corrected: the runner's rows carry order_id, which put_venue_ids() maps
    # client_id -> order_id. The first version of this probe looked for "venue_order_id" - the name
    # the EXECUTOR's own record uses - and reported 33 unresolved rows that were nothing of the
    # kind. Checking both, and the client_id that attribution actually joins on.
    with_id = [r for r in rows if isinstance(r, dict) and (r.get("order_id") or r.get("venue_order_id"))]
    no_id = [r for r in rows if isinstance(r, dict) and not (r.get("order_id") or r.get("venue_order_id"))]
    no_cid = [r for r in rows if isinstance(r, dict) and not r.get("client_id")]
    print(f"    rows WITHOUT a client_id   : {len(no_cid)}  (attribution joins on client_id)")
    if rows and isinstance(rows[-1], dict):
        print(f"    fields on the newest row   : {sorted(rows[-1].keys())}")
    print(f"    rows with a venue order id : {len(with_id)}")
    print(f"    rows WITHOUT one           : {len(no_id)}")
    st = {}
    for r in rows:
        if isinstance(r, dict):
            st[str(r.get("status") or "?")] = st.get(str(r.get("status") or "?"), 0) + 1
    print(f"    statuses                   : {st or '(none)'}")
    # A row the venue never ACCEPTED has no venue order id and should not: "refused" and
    # "rejected" never reached Novig. Flagging those as unreconciled collapsed two states with
    # opposite meanings - the first reading of this probe reported 33 unresolved rows and then 2,
    # and both numbers were the measurement, not the data.
    NEVER_SENT = ("refused", "rejected")
    unexplained = [r for r in no_id if str(r.get("status") or "").lower() not in NEVER_SENT]
    say("every ACCEPTED runner row carries a venue order id", not unexplained,
        f"{len(unexplained)} unexplained - reconcile before activation" if unexplained
        else f"{len(no_id)} without one, all {NEVER_SENT} (never reached the venue)")
    say("every runner row carries a client_id (joinable to our claim)", not no_cid,
        f"{len(no_cid)} unjoinable" if no_cid else "")

print()
print("ACTIVATION READINESS (this probe only):", "PASS" if ok_all else "FAIL")
print("Nothing was dispatched, placed, cancelled or written.")
sys.exit(0)   # a diagnostic never fails the workflow
