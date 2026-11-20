#!/usr/bin/env python3
"""Pull Muse's private transfer for a day into local files the daily report already reads.

Peter, Nov 20: use the private route that EXISTS - faros4life/novig-runner,
muse_transfers/<day>.json - with the REGISTRY_TOKEN secret the other workflows already use.
No new repository, no new credential.

Nothing private is written into this public repo: the files land in the runner's working
directory for the length of the run and are never committed. Monetary fields (stake, profit) are
dropped on the way in - the report computes units from the tracker's own records.
"""
import json
import os
import sys
import urllib.request

REPO = "faros4life/novig-runner"
PATH = "muse_transfers"
DROP = ("stake", "profit", "profit_site", "payout", "to_pay")


def fetch(day, token):
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}/{day}.json"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw",
        "User-Agent": "sharp-monitor-daily-report"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def scrub(rec):
    return {k: v for k, v in rec.items() if k not in DROP}


def main(argv):
    day = argv[1]
    token = os.environ.get("REGISTRY_TOKEN") or ""
    if not token:
        print("transfer: REGISTRY_TOKEN not set - no private transfer read", flush=True)
        return 0                      # never fatal: the report still runs on certified records
    try:
        d = fetch(day, token)
    except Exception as e:
        print(f"transfer: NOT read ({type(e).__name__}) - report continues without it", flush=True)
        return 0
    snaps = [scrub(s) for s in (d.get("pinnacle_snapshots") or [])]
    # extra_events are METADATA ONLY - authoritative game dates for bets already in the tracker.
    # They are never turned into bets; they only supply a game date the tracker lacks.
    events = [scrub(b) for b in (d.get("manual_bets") or [])] + \
             [dict(scrub(b), metadata_only=True) for b in (d.get("extra_events") or [])]
    os.makedirs("snapshots", exist_ok=True)
    os.makedirs("events", exist_ok=True)
    json.dump(snaps, open(f"snapshots/{day}.json", "w"))
    json.dump(events, open(f"events/{day}.json", "w"))
    print(f"transfer: {len(snaps)} snapshot(s), {len(events)} event record(s) "
          f"({len(d.get('extra_events') or [])} metadata-only) for {day}"
          f" (monetary fields dropped)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
