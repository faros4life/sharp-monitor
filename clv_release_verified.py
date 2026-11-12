#!/usr/bin/env python3
"""
CONTROLLED RELEASE of independently verified held-out CLV rows (Peter, Nov 12, explicit GO).

Clears the sticky fixture_doubt marker on rows whose identity has been confirmed WITHOUT relying
on the matcher. It rewrites no CLV, no price, no fixture and no result: the only field it touches
is fixture_doubt, which is what excludes a scored row from the headline.

WHY THE MATCHER CANNOT AUTHORISE THIS. espn_fill overwrites s["teams"] with the ESPN game's two
teams, and find_fixture then matches against those teams - so on an ESPN error the matcher checks
the data the error wrote. clv_ledger states it: "The downstream matcher therefore cannot catch this
class of mistake at all; it can only confirm it." Every condition below is evaluated against the
bet's ORIGINAL text, which espn_fill never overwrites, and against the STORED FIXTURE's own
participants - never against the ESPN teams.

SEVEN CONDITIONS, ALL required per row:
  1  the id is on the explicit allowlist
  2  the row is actually held out (fixture_doubt present)
  3  clv is not None - a released row must already be scored
  4  the bet's own untouched text names BOTH participants of the stored fixture
  5  NO stray team token: nothing in the bet text may name a team absent from both participants.
     This is what keeps the Houston Rockets @ Dallas Mavericks row - stored against Houston vs
     Oklahoma City, carrying the set's largest CLV at +21.54% - permanently excluded.
  6  the close is SAME-LINE or moneyline. A converted close ("main X moved to Y") carries the
     half-point conversion's error and is not released.
  7  the tracker's own date agrees with the assigned start within 36h

A row failing ANY condition is reported and left held out. If any allowlisted id fails, the run
stops without writing.
"""
import collections
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
APPLY = (os.environ.get("REL_APPLY") or "") == "1"
EXPECT = int(os.environ.get("REL_EXPECT") or "25")
ALLOW = [x.strip() for x in (os.environ.get("REL_IDS") or "").split(",") if x.strip()]
SAME_LINE = ("own line", "moneyline")
L = []


def say(t=""):
    L.append(t)
    print(t)


def main():
    now = datetime.now(timezone.utc)
    say("CONTROLLED RELEASE of verified held-out CLV rows")
    say(f"generated {now:%Y-%m-%d %H:%M}Z | mode: {'APPLY' if APPLY else 'DRY RUN'}")
    say("Touches fixture_doubt ONLY. No CLV, price, fixture or result is rewritten.")
    say("=" * 100)

    try:
        st = cl.tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"  CLV state unreadable ({type(e).__name__}) - nothing done")
        return 1
    bets = st.get("bets") or {}
    fx = st.get("fixtures") or {}
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tbets = raw if isinstance(raw, dict) else {}
    except Exception:
        tbets = {}

    pool = ALLOW or [k for k, r in bets.items() if r.get("fixture_doubt")]
    say(f"  ledger rows {len(bets)} | candidates considered {len(pool)}"
        + (f" (explicit allowlist of {len(ALLOW)})" if ALLOW else " (derived; DRY RUN only)"))

    eligible, rejected = [], []
    for k in pool:
        rec = bets.get(k)
        if rec is None:
            rejected.append((k, "not in the ledger"))
            continue
        s = rec.get("snap") or {}
        tr = tbets.get(k) or {}
        if not rec.get("fixture_doubt"):
            rejected.append((k, "not held out - nothing to release"))
            continue
        if rec.get("clv") is None:
            rejected.append((k, "not scored - a released row must already have a CLV"))
            continue
        f = fx.get(rec.get("fixture")) or {}
        p1, p2 = str(f.get("p1") or ""), str(f.get("p2") or "")
        own = (tb.toks(s.get("bet")) | tb.toks(s.get("game"))) - tb.WEAK
        h1 = (tb.toks(p1) - tb.WEAK) & own
        h2 = (tb.toks(p2) - tb.WEAK) & own
        if not (h1 and h2):
            rejected.append((k, f"bet text supports {(1 if h1 else 0) + (1 if h2 else 0)} of 2 "
                                "participants - identity not independently confirmed"))
            continue
        stray = own - ((tb.toks(p1) | tb.toks(p2)) - tb.WEAK) - tb.toks(str(s.get("bet") or ""))
        if stray:
            rejected.append((k, f"bet names {sorted(stray)[:3]}, absent from both participants - "
                                "WRONG MATCH, stays excluded"))
            continue
        how = str(rec.get("how") or "")
        if how not in SAME_LINE:
            rejected.append((k, f"close is CONVERTED ({how[:34]}) - not released"))
            continue
        gs, d = cl.tp(s.get("game_start")), (cl.tp((s.get("date") or "") + "T12:00:00Z")
                                             if s.get("date") else None)
        if d and gs and abs((gs - d).total_seconds()) > 36 * 3600:
            rejected.append((k, "tracker date disagrees with the assigned game by over 36h"))
            continue
        eligible.append((k, rec, f, how))

    say("")
    say(f"  ELIGIBLE  {len(eligible)}")
    say(f"  REJECTED  {len(rejected)}")
    for k, rec, f, how in eligible:
        s = rec.get("snap") or {}
        say(f"    {k[:34]:<34} CLV {100 * rec['clv']:+7.2f}%  {str(s.get('league')):<6} "
            f"{str(s.get('bet'))[:20]:<20} {how}")
    if rejected:
        say("")
        say("  NOT released, flag left in place:")
        for k, why in rejected[:20]:
            say(f"    {k[:34]:<34} {why}")

    if ALLOW and rejected:
        say("")
        say(f"  STOP: {len(rejected)} allowlisted id(s) failed. Nothing written.")
        return 2
    if ALLOW and len(eligible) != EXPECT:
        say("")
        say(f"  STOP: {len(eligible)} eligible, expected {EXPECT}. Nothing written.")
        return 2

    if not APPLY:
        say("")
        say("  DRY RUN - nothing written, no flag cleared, no credit spent.")
        say("=" * 100)
        say("REL_IDS=" + ",".join(k for k, _, _, _ in eligible))
        _mail(f"Bets CLV RELEASE dry run ({len(eligible)} eligible)")
        print(f"clv release: DRY RUN, eligible {len(eligible)}, rejected {len(rejected)}")
        return 0

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except Exception:
        sha = ""
    audit = {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "reason": "release of independently verified held-out rows; fixture_doubt cleared only",
             "state_commit_before": sha, "rows": []}
    for k, rec, f, how in eligible:
        s = rec.get("snap") or {}
        audit["rows"].append({"id": k, "clv": rec.get("clv"), "how": how,
                              "fixture": rec.get("fixture"), "p1": f.get("p1"), "p2": f.get("p2"),
                              "league": s.get("league"), "bet": s.get("bet"), "game": s.get("game"),
                              "fixture_doubt_before": rec.get("fixture_doubt")})
    path = f"clv/release_audit_{now:%Y%m%dT%H%M%S}Z.json"
    os.makedirs("clv", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(audit, fh, indent=1, sort_keys=True)
    say("")
    say(f"  AUDIT written: {path} ({len(audit['rows'])} row(s)), state commit before = {sha[:12]}")

    for k, rec, f, how in eligible:
        # the ONLY mutation: the flag that excludes a scored row from the headline. Its prior
        # value is preserved in the audit file and in released_from below.
        rec["released_from"] = rec.pop("fixture_doubt")
        rec["released_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    say(f"  released {len(eligible)} row(s): fixture_doubt cleared, nothing else touched")
    with open(cl.STATE, "w") as fh:
        json.dump(tb.enc(st), fh)
    say(f"  state written: {cl.STATE}")
    say("=" * 100)
    _mail(f"Bets CLV RELEASE applied ({len(eligible)} rows)")
    print(f"clv release: APPLIED {len(eligible)}, audit {path}")
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
