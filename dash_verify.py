#!/usr/bin/env python3
"""Verify the PUBLISHED dashboard: prompt-only markup, real decryption, P/L semantics.

Runs inside Actions, where TRACKER_PASSPHRASE lives. It prints booleans and counts ONLY - never
the passphrase, never a figure from the payload. Peter, 14 Nov: "Verify dashboard deployment,
passphrase prompt and successful decryption using safe checks. Do not expose the passphrase or
plaintext performance data."

Decrypting with the real secret is the only check that proves the page a browser receives is both
opaque without the passphrase and readable with it. Asserting the blob merely "looks encrypted" is
what the earlier guard did, and it passed while a plaintext copy of the same numbers sat next to
the page.
"""
import json
import re
import sys

import tracker_build as tb

PAGE = "dash/index.html"
bad = []


def ck(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"  {extra}" if extra and not cond else ""))
    if not cond:
        bad.append(label)


h = open(PAGE).read()
m = re.search(r"let BLOB=(\{.*?\});", h, re.S)
ck("the page carries a blob", bool(m))
blob = json.loads(m.group(1)) if m else {}

print("A. without the passphrase the page is a prompt and nothing else")
body = re.sub(r"<script.*?</script>", "", h, flags=re.S)
ck("markup is prompt-sized", len(body) < 4000, f"{len(body)} bytes")
ck("markup has a passphrase field", 'type="password"' in body)
ck("markup carries no figure, no lane name, no league",
   not re.search(r"(PHASE 1|BOARD V3|LIQ-BOT|NBA|NCAAF|NHL|NFL|[+-]\d+\.\d+%)", body))
ck("no dollar sign anywhere in the file", "$" not in h)
ck("the page is noindex", 'content="noindex"' in h)

print("B. with the passphrase it decrypts - the real secret, counts only")
try:
    view = tb.dec(blob)
    ok = True
except Exception as e:
    view, ok = None, False
    ck("decryption", False, type(e).__name__)
if ok:
    ck("decryption succeeds with the repo secret", True)
    B = (view or {}).get("bands") or {}
    for b in ("A_status", "B_lanes", "C_qualification", "D_triggers", "E_change", "F_research"):
        ck(f"band {b} present after decryption", b in B)
    ck("the approved cutoff label is the one in the payload",
       view.get("cutoff_label") == "Price-First Execution Change - Nov 11, 11:31 AM ET")
    ck("payload is non-trivial", (view.get("selections_total") or 0) > 0,
       str(view.get("selections_total")))

    print("C. units are realized P/L, exposure is separate, missing P/L stays UNAVAILABLE")
    lanes = (B.get("B_lanes") or {}).get("lanes") or []
    checked = 0
    for L in lanes:
        for per in ("today", "cumulative", "post_change", "pre_change", "h1", "h2"):
            blk = L.get(per) or {}
            if not blk.get("n"):
                continue
            checked += 1
            if blk.get("units") is None:
                ck(f"{L['name']}/{per}: missing P/L is UNAVAILABLE with a reason, not zero",
                   bool(blk.get("units_why")) and "not zero" in str(blk.get("units_why")),
                   str(blk.get("units_why"))[:40])
            else:
                # P/L and exposure must be DIFFERENT quantities: exposure is never negative.
                ck(f"{L['name']}/{per}: exposure is reported separately",
                   blk.get("risked_u") is not None)
                ck(f"{L['name']}/{per}: exposure is non-negative", (blk.get("risked_u") or 0) >= 0)
    ck("at least one populated block was checked", checked > 0, str(checked))
    print("D. exceptions keep unattributed history, nothing inferred")
    bl = B.get("B_lanes") or {}
    ck("unassigned selections are reported as a count", isinstance(bl.get("unassigned_n"), int))
    ck("the registry window bounding attribution is stated", bool(bl.get("window_note")))
    ck("no lane is claimed without a registry join", "provably" in str(bl.get("note", "")))

print()
print("DASHBOARD VERIFIED" if not bad else f"{len(bad)} FAILURE(S): {bad}")
sys.exit(1 if bad else 0)
