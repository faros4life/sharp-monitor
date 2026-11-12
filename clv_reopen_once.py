#!/usr/bin/env python3
"""
ONE-TIME CLV RECOVERY for rows retired by the pre-fix fixture matcher (Peter, Nov 12, explicit GO).

WHAT HAPPENED. find_fixture built its match words with `or` instead of `|`, so a row whose teams
list held one side could never match the second side. 27 rows failed that way eight times each and
were retired with done=True at tries=8. The matcher is fixed (9a7bfb898) and now resolves all 27 to
a unique fixture - but the pending loop checks done BEFORE anything else, so the fix cannot reach
them. The ledger run after the fix reported scored 109 (+0) with 0 calls: the queue was empty.

They were retired for a reason that no longer exists. This reopens exactly those rows, once.

WHAT THIS IS NOT. It does not change MAX_TRIES or the retirement logic (Peter item 4) - this is a
separate one-time script, and clv_ledger is untouched. It does not reset tries. Leaving tries at 8
is what makes this ONE controlled attempt rather than an unlimited retry cycle (item 5): the next
genuine failure increments to 9, clears MAX_TRIES again, and the row retires itself through the
existing guard. The guard does the work; nothing here weakens it.

THE FIVE CONDITIONS (item 3), ALL required, per row:
  1  the id is on the explicit allowlist
  2  clv is None                       - there is no score to overwrite
  3  done is True and tries == 8       - retired, and retired by exhaustion rather than terminally
  4  why is exactly the fixture-matching failure - so a terminally excluded row ("placed after
     start (in-play): not scored", "not comparable", "far from", "league not covered") can never
     be resurrected, whatever the allowlist says
  5  the corrected matcher resolves exactly ONE fixture for it now

A row failing ANY condition is reported and left alone. If any allowlisted id fails, the run stops
without writing (item 7's "stop if any of the 27 fail").

AUDIT (item 2). Before any change, every affected row's id, done, tries, why and clv are written to
clv/reopen_audit_<utc>.json and printed. The encrypted state itself is already versioned in git, so
the prior state is recoverable by commit as well; that commit sha is recorded in the audit file.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import tracker_build as tb

APPLY = (os.environ.get("REOPEN_APPLY") or "") == "1"
EXPECT = int(os.environ.get("REOPEN_EXPECT") or "27")
ALLOW = [x.strip() for x in (os.environ.get("REOPEN_IDS") or "").split(",") if x.strip()]
WHY_OK = "no OddsPapi fixture matched"
TRIES_OK = 8
L = []


def say(t=""):
    L.append(t)
    print(t)


def main():
    now = datetime.now(timezone.utc)
    say("ONE-TIME CLV RECOVERY - reopen rows retired by the pre-fix matcher")
    say(f"generated {now:%Y-%m-%d %H:%M}Z | mode: {'APPLY' if APPLY else 'DRY RUN'}")
    say("Does not change MAX_TRIES or the retirement logic. Does not reset tries.")
    say("Never overwrites a CLV score, a terminal exclusion or a verified historical result.")
    say("=" * 100)

    try:
        raw = json.load(open(cl.STATE))
        st = cl.tb.dec(raw)
    except Exception as e:
        say(f"  CLV state unreadable ({type(e).__name__}) - nothing done")
        return 1
    bets = st.get("bets") or {}
    fxst = {"fixtures": st.get("fixtures") or {}, "fx_last": st.get("fx_last") or {}}
    say(f"  ledger rows {len(bets)} | fixtures {len(fxst['fixtures'])}")

    # ---------------------------------------------------------------- candidates
    # Derived by the SAME five conditions whether or not an allowlist was supplied. With an
    # allowlist, only those ids are considered and every one of them must qualify.
    pool = ALLOW or list(bets)
    if ALLOW:
        say(f"  explicit allowlist supplied: {len(ALLOW)} id(s)")
    else:
        say("  no allowlist supplied - deriving candidates (DRY RUN only; apply requires the list)")

    eligible, rejected = [], []
    for k in pool:
        rec = bets.get(k)
        if rec is None:
            rejected.append((k, "not in the ledger"))
            continue
        s = rec.get("snap") or {}
        if rec.get("clv") is not None:
            rejected.append((k, f"already scored (clv {rec.get('clv')}) - never overwritten"))
            continue
        if not rec.get("done"):
            rejected.append((k, "not retired (done is not True) - nothing to reopen"))
            continue
        if rec.get("tries") != TRIES_OK:
            rejected.append((k, f"tries={rec.get('tries')}, not {TRIES_OK} - not exhaustion-retired"))
            continue
        if str(rec.get("why") or "") != WHY_OK:
            rejected.append((k, f"why is {str(rec.get('why'))[:46]!r} - not the matcher failure"))
            continue
        fid = cl.find_fixture(fxst, s)
        if not fid:
            rejected.append((k, "corrected matcher still finds no unique fixture"))
            continue
        f = fxst["fixtures"].get(fid) or {}
        eligible.append((k, rec, fid, f))

    say("")
    say(f"  ELIGIBLE   {len(eligible)}")
    say(f"  REJECTED   {len(rejected)}")
    for k, rec, fid, f in eligible:
        s = rec.get("snap") or {}
        say(f"    {k[:36]:<36} {str(s.get('league')):<6} {str(s.get('game'))[:34]:<34}")
        say(f"        -> {str(f.get('p1'))[:30]} v {str(f.get('p2'))[:30]}")
    if rejected:
        say("")
        say("  rejected, left untouched:")
        for k, why in rejected[:30]:
            say(f"    {k[:36]:<36} {why}")

    # ---------------------------------------------------------------- gate
    if ALLOW and rejected:
        say("")
        say(f"  STOP: {len(rejected)} allowlisted id(s) failed eligibility. Nothing written.")
        say("  Peter's instruction: stop if any of the 27 fail the checks.")
        return 2
    if ALLOW and len(eligible) != EXPECT:
        say("")
        say(f"  STOP: {len(eligible)} eligible, expected {EXPECT}. Nothing written.")
        return 2

    if not APPLY:
        say("")
        say("=" * 100)
        say("  DRY RUN - nothing written, no state changed, no credit spent.")
        say("  The ids above are the allowlist to pass back as REOPEN_IDS for the apply run.")
        say("=" * 100)
        say("")
        say("REOPEN_IDS=" + ",".join(k for k, _, _, _ in eligible))
        _mail(f"Bets CLV REOPEN dry run ({len(eligible)} eligible)")
        print(f"clv reopen: DRY RUN, eligible {len(eligible)}, rejected {len(rejected)}")
        return 0

    # ---------------------------------------------------------------- audit, then apply
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except Exception:
        sha = ""
    audit = {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "reason": "one-time reopen of rows retired by the pre-fix fixture matcher (9a7bfb898)",
             "state_commit_before": sha, "max_tries_unchanged": cl.MAX_TRIES,
             "tries_preserved": True, "rows": []}
    for k, rec, fid, f in eligible:
        audit["rows"].append({"id": k, "done_before": rec.get("done"),
                              "tries_before": rec.get("tries"), "why_before": rec.get("why"),
                              "clv_before": rec.get("clv"), "fixture_now": fid,
                              "fixture_p1": f.get("p1"), "fixture_p2": f.get("p2")})
    path = f"clv/reopen_audit_{now:%Y%m%dT%H%M%S}Z.json"
    os.makedirs("clv", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(audit, fh, indent=1, sort_keys=True)
    say("")
    say(f"  AUDIT written: {path} ({len(audit['rows'])} row(s)), state commit before = {sha[:12]}")

    changed = 0
    for k, rec, fid, f in eligible:
        # ONE controlled attempt: clear done, KEEP tries at 8. The next genuine failure increments
        # to 9, clears MAX_TRIES and retires the row again through the existing guard - so this
        # cannot become an unlimited retry cycle.
        rec["done"] = False
        rec["why"] = "reopened once: retired by the pre-fix matcher, which now resolves it"
        rec["reopened_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        changed += 1
    say(f"  reopened {changed} row(s): done=False, tries LEFT AT {TRIES_OK}, no clv touched")

    with open(cl.STATE, "w") as fh:
        json.dump(tb.enc(st), fh)
    say(f"  state written: {cl.STATE}")
    say("=" * 100)
    _mail(f"Bets CLV REOPEN applied ({changed} rows)")
    print(f"clv reopen: APPLIED, reopened {changed}, audit {path}")
    return 0


def _mail(subject):
    try:
        import executor as ex
        ex.send(subject, "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")


if __name__ == "__main__":
    sys.exit(main())
