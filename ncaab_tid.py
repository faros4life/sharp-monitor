#!/usr/bin/env python3
"""NCAAB TOURNAMENT IDENTIFICATION - one-off (Peter, Nov 16 16:10).

Exactly ONE billable /tournaments?sportId=11 call through the shared credit gate. It SELECTS
NOTHING: it prints every basketball tournament whose name or category could be US college
(id, name, category and the other metadata fields), so the Division I men's id can be verified
by a person from authoritative metadata. Writes no state. Never calls /fixtures.
Upcoming-fixture counts are deliberately NOT printed, so they cannot drive the choice.
"""
import sys

import clv_ledger as cl

WORDS = ("ncaa", "college", "ncaab", "division", "cbb")


def candidates(ts):
    out = []
    for t in ts if isinstance(ts, list) else []:
        blob = " ".join(str(t.get(k) or "") for k in ("tournamentName", "tournamentSlug", "categoryName",
                                                       "categorySlug")).lower()
        if any(w in blob for w in WORDS) or "usa" in str(t.get("categorySlug") or "").lower():
            out.append(t)
    return out


def main():
    try:
        ts = cl.api("/tournaments", True, sportId=11)
    except cl.GateRefused as e:
        print(f"REFUSED by the credit gate, no call made: {e}")
        return 1
    if cl.STATS["billable"] != 1:
        print(f"ABORT: expected exactly one billable call, saw {cl.STATS['billable']}")
        return 1
    if isinstance(ts, dict) and ts.get("_error"):
        print(f"OddsPapi error {ts['_error']}: {str(ts.get('_body'))[:150]}")
        return 1
    keys = sorted({k for t in (ts if isinstance(ts, list) else []) for k in t})
    print(f"basketball tournaments returned: {len(ts) if isinstance(ts, list) else 0}; fields: {keys}")
    hide = {"upcomingFixtures", "futureFixtures", "liveFixtures"}
    for t in candidates(ts):
        print("CANDIDATE " + " | ".join(f"{k}={t.get(k)}" for k in sorted(t) if k not in hide))
    print("NO SELECTION MADE - verify Division I men's from the metadata above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
