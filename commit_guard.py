#!/usr/bin/env python3
"""Did these paths change MEANINGFULLY, or only in volatile fields?

Exit 0 = commit it. Exit 1 = only volatile fields differ, leave main alone.

WHY THIS EXISTS (Nov 13). bets-board was committing to main ~1320 times a day while saying
nothing. Its existing "git diff --cached --quiet && break" guard could never fire, because three
fields differ on every single run no matter what:

    lanes/lanes.json     "mins_to_start": 714 -> 713      (a countdown)
                         "snapshot_utc": ...13:05:56Z     (a timestamp)
    board/calls.json     "updated": ...13:06:19Z          (a timestamp)
    tracker/index.html   let BLOB={"s":...,"i":...}       (ciphertext: a random salt and IV are
                                                           drawn per run, so identical content
                                                           encrypts to a different blob)

A 228-line diff of lanes.json turned out to be 115 countdown lines and 115 timestamps. That churn
is what drove commits to main from ~33/hour to 50-74/hour, which starved sharp-monitor's push and
froze the alert feed for nine hours. Suppressing it removes the contention at its source without
touching a single trigger.

The heartbeat is the safety valve: if the paths have not been committed for COMMIT_HEARTBEAT_MIN
minutes, commit regardless, so a countdown on main is never staler than that. The default 10
matches bets-board's own designed cadence, so the published page is no less fresh than it was
designed to be - only the 5x over-committing stops.

Read-only with respect to secrets: it compares plaintext JSON and skips the ciphertext line. It
never decrypts anything and never touches TRACKER_PASSPHRASE.
"""
import json
import os
import subprocess
import sys
import time

# Fields that change every run by construction and carry no decision content on their own.
VOLATILE = {"snapshot_utc", "mins_to_start", "updated", "as_of", "generated_utc", "built_utc"}
HEARTBEAT_MIN = float(os.environ.get("COMMIT_HEARTBEAT_MIN", "") or "10")
# Line prefixes whose payload is randomised per run even when the content is identical.
CIPHER_PREFIXES = ("let BLOB=",)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def _head_text(path):
    r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def norm(path, text):
    """Comparable form: volatile JSON fields removed, ciphertext lines dropped."""
    if text is None:
        return None
    if path.endswith(".json"):
        try:
            return json.dumps(strip(json.loads(text)), sort_keys=True)
        except Exception:
            return text          # unparseable: compare raw rather than guess
    return "\n".join(l for l in text.splitlines()
                     if not l.lstrip().startswith(CIPHER_PREFIXES))


def _files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for dp, _, names in os.walk(p):
                if ".git" in dp.split(os.sep):
                    continue
                for n in sorted(names):
                    yield os.path.join(dp, n)


def main(paths):
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--"] + list(paths),
                       capture_output=True, text=True)
    try:
        age_min = (time.time() - int(r.stdout.strip())) / 60.0
    except Exception:
        age_min = float("inf")   # no history for these paths: treat as due
    if age_min >= HEARTBEAT_MIN:
        print(f"commit guard: last commit {age_min:.0f}m ago (heartbeat {HEARTBEAT_MIN:g}m) - committing")
        return 0

    seen = set()
    for f in _files(paths):
        seen.add(f)
        try:
            cur = norm(f, open(f, errors="replace").read())
        except Exception:
            return 0             # unreadable: never suppress on uncertainty
        if cur != norm(f, _head_text(f)):
            print(f"commit guard: {f} changed meaningfully - committing")
            return 0
    # A file present in HEAD but gone from the tree is a real change too.
    tracked = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD", "--"] + list(paths),
                             capture_output=True, text=True).stdout.split()
    for f in tracked:
        if f not in seen:
            print(f"commit guard: {f} was removed - committing")
            return 0

    print(f"commit guard: only volatile fields differ (last commit {age_min:.0f}m ago) - skipping")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["."]))
