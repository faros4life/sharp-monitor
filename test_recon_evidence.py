#!/usr/bin/env python3
"""Tests for the durable-evidence layer in novig_venue_recon (Nov 13, 2026).

These assert BEHAVIOUR, not docstrings. The bug this guards against is an evidence entry reaching
a row it was never meant to cover - above all the Louisiana play, where two attempts never ran and
a third filled. Stamping "never executed" on the one that filled would be a false all-clear on a
live-money row, so the precedence rules are tested directly.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import novig_venue_recon as R

FAIL = []


def ck(name, got, want):
    if got != want:
        FAIL.append(f"{name}: got {got!r}, want {want!r}")


def row(cid="", oid="", key="", intent=False):
    return {"cid": cid, "oid": oid, "key": key, "when": "", "asked": None,
            "intent": intent, "status": ""}


ev, dnt, note = R.evidence()
ck("evidence file loads", bool(ev), True)
ck("do_not_touch recorded", len(dnt) >= 1, True)

LA = "NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"

# --- the precedence that matters most -------------------------------------------------------
# The confirmed Louisiana attempt HAS a runner record. The play-key entry demands there be none,
# so it must not reach it. (The live venue match in main() is a second, earlier guard.)
hit = R.evidence_for(ev, row(cid="9876e410d17d45fd", key="r1|" + LA), at_runner=True)
ck("confirmed Louisiana attempt is not stamped", hit, None)

# The two that never ran have no runner record and are matched by client id.
for cid in ("fee2daffea274108", "e238da09866a4efd"):
    h = R.evidence_for(ev, row(cid=cid, key="r1|" + LA), at_runner=False)
    ck(f"{cid} matched", bool(h), True)
    ck(f"{cid} kind", h and h.get("kind"), "proven_pre_execution")
    ck(f"{cid} ruled out", bool(h and h["verdict"].startswith("RULED OUT")), True)

# Their bare-key twins carry no client id and must still be covered, by play key.
h = R.evidence_for(ev, row(cid="", key=LA), at_runner=False)
ck("bare-key twin matched by play key", h and h.get("kind"), "proven_pre_execution")

# A client id match must win even if a runner record exists, so an exact id is never shadowed.
h = R.evidence_for(ev, row(cid="fee2daffea274108", key=LA), at_runner=True)
ck("client id match beats the no-record condition", bool(h), True)

# --- the two cancelled orders, matched on venue order id ------------------------------------
for oid in ("01a1cb84-4a5c-7113-8e00-8986dce6e13a", "01a1cb85-4239-7e33-bc75-9be59bf54f57"):
    h = R.evidence_for(ev, row(oid=oid), at_runner=True)
    ck(f"{oid[:12]} matched", bool(h), True)
    ck(f"{oid[:12]} kind", h and h.get("kind"), "terminal_at_venue")

# --- intents stay blocked --------------------------------------------------------------------
for cid in ("060d16319d5b40ec", "e2fa1ea2ed3c4d7d"):
    h = R.evidence_for(ev, row(cid=cid, intent=True), at_runner=False)
    ck(f"{cid} matched", bool(h), True)
    ck(f"{cid} kind", h and h.get("kind"), "no_dispatch_evidence")
    # The whole point: an absence-of-evidence argument must NOT read as ruled out.
    ck(f"{cid} stays unresolved", bool(h and h["verdict"].startswith("UNRESOLVED")), True)

# --- regression: an id must match whichever field it lands in ---------------------------------
# The first live run missed both cancelled orders because the registry carried their CLIENT id in
# the field the order id usually occupies, and the lookup was pinned to one field each way.
for u in ("6c5b19ad-d05a-423d-aeed-fbd37f212dec", "f35c5788-adec-4346-87cf-945bbeaf33d6"):
    ck(f"client uuid {u[:8]} in the oid field matches",
       bool(R.evidence_for(ev, row(oid=u), at_runner=True)), True)
    ck(f"client uuid {u[:8]} in the cid field matches",
       bool(R.evidence_for(ev, row(cid=u), at_runner=True)), True)
# and the venue order id must still match from either field
ck("order id in the cid field matches",
   bool(R.evidence_for(ev, row(cid="01a1cb84-4a5c-7113-8e00-8986dce6e13a"), at_runner=True)), True)

# --- an unrelated row is never stamped -------------------------------------------------------
ck("unrelated row untouched",
   R.evidence_for(ev, row(cid="deadbeefdeadbeef", key="NBA|Lakers vs Suns|total|OVER"), at_runner=False),
   None)

# --- no entry may release anything -----------------------------------------------------------
d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "novig_recon_evidence.json")))
for e in d["entries"]:
    for k in ("release", "clear", "unblock", "resume", "cancel"):
        ck(f"entry {e['id']} has no {k} field", k in e, False)
    ck(f"entry {e['id']} states its source", bool(e.get("source")), True)
    ck(f"entry {e['id']} states its kind", e.get("kind") in
       ("proven_pre_execution", "terminal_at_venue", "no_dispatch_evidence"), True)

# --- the module itself must stay read-only ---------------------------------------------------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "novig_venue_recon.py")).read()
import re
ck("no non-GET github calls", set(re.findall(r'_gh\(\s*["\'](\w+)', src)), {"GET"})
ck("no registry writes", bool(re.search(r'registry\.(save|write|claim_|release_|void)', src)), False)
ck("no file writes", bool(re.search(r'open\([^)]*["\'][wa]', src)), False)

# --- the live resting order is listed as untouchable, not as an unresolved row ----------------
ck("resting order recorded in do_not_touch",
   any(o.get("order_id") == "01a1d53a-e54f-7b23-b492-94e6b58d3a62" for o in dnt), True)

print(f"test_recon_evidence: {'FAIL' if FAIL else 'PASS'}")
for f in FAIL:
    print("  " + f)
sys.exit(1 if FAIL else 0)
