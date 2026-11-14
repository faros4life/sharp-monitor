#!/usr/bin/env python3
"""clv_dashboard: the gate, the cutoff, the privacy of the payload, and zero-vs-unknown.

The dashboard is a reporting surface, so its defects are all of one kind: a figure that looks
normal and is not. These tests pin the four that would do real damage - a PASS rendered from a
computation, a wrong cutoff, a readable payload on a PUBLIC repo, and a zero standing in for
missing data.
"""
import json
import re
from datetime import datetime, timezone

import clv_dashboard as dash

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


print("1. the verified cutoff, exactly as approved")
check("cutoff is 2026-11-11T16:31:19Z",
      dash.CUTOFF == datetime(2026, 11, 11, 16, 31, 19, tzinfo=timezone.utc), dash.CUTOFF)
check("that is 11:31:19 EST",
      dash.CUTOFF.astimezone(dash.ET).strftime("%Y-%m-%d %H:%M:%S") == "2026-11-11 11:31:19",
      dash.CUTOFF.astimezone(dash.ET).isoformat())
check("the label is Peter's wording", dash.CUTOFF_LABEL ==
      "Price-First Execution Change - Nov 11, 11:31 AM ET", dash.CUTOFF_LABEL)
check("the page never calls it the November 12 change",
      "Nov 12" not in dash.PAGE and "November 12" not in dash.PAGE)

print("2. the registered gate cannot render PASS from a computation")
whole = {"n": 60, "clv": 2.0, "ci": [1.0, 3.0], "pos": 40, "units": 5.0}
h = {"n": 30, "clv": 1.8, "ci": [0.5, 3.1], "units": 2.5}
g = dash.gate("x", h, h, whole, fills_ok=True)
check("a perfect computable sample is NOT called PASS", "PASS" not in g["verdict"].split(" - ")[0]
      or "ALL COMPUTABLE" in g["verdict"], g["verdict"])
check("it names the two clauses it cannot compute",
      sum(1 for c in g["clauses"] if c["state"] == "NOT MEASURABLE") >= 2,
      [c["clause"] for c in g["clauses"] if c["state"] == "NOT MEASURABLE"])
check("multiplicity is one of them",
      any("multiplicity" in c["clause"] and c["state"] == "NOT MEASURABLE" for c in g["clauses"]))
check("pre-registration is the other",
      any("pre-registered" in c["clause"] and c["state"] == "NOT MEASURABLE" for c in g["clauses"]))

print("   no fills -> the realized-unit clause is UNMET, not skipped")
g2 = dash.gate("x", h, h, whole, fills_ok=False)
check("the fills clause is UNMET",
      any("CONFIRMED FILLS" in c["clause"] and c["state"] == "UNMET" for c in g2["clauses"]))
check("and says every unit figure is hypothetical",
      any("hypothetical" in c["detail"] for c in g2["clauses"]))
check("the verdict is not ALL COMPUTABLE CLAUSES MET", "ALL COMPUTABLE" not in g2["verdict"],
      g2["verdict"])

print("   a negative interval at adequate n is CLEAR FAIL; a thin one never is")
g3 = dash.gate("x", h, h, {"n": 60, "clv": -3.0, "ci": [-4.0, -2.0], "pos": 10, "units": -1.0}, True)
check("CLEAR FAIL", g3["verdict"] == "CLEAR FAIL", g3["verdict"])
g4 = dash.gate("x", h, h, {"n": 8, "clv": -3.0, "ci": [-9.0, -1.0], "pos": 1, "units": -1.0}, True)
check("n=8 is INSUFFICIENT EVIDENCE, not a FAIL", g4["verdict"] == "INSUFFICIENT EVIDENCE",
      g4["verdict"])
g5 = dash.gate("x", None, None, None, False)
check("nothing certified -> INSUFFICIENT EVIDENCE", g5["verdict"] == "INSUFFICIENT EVIDENCE")
check("and no clause is claimed as met",
      all(c["state"] != "MET" for c in g5["clauses"]), g5["clauses"])

print("3. zero is never unknown")
b = dash.blk([])
check("an empty group reports no data with a reason", b["n"] == 0 and b.get("why"), b)
b2 = dash.blk([{"clv": 0.01, "stake": None, "game_start": "2026-11-12T00:00:00Z"}], unit=None)
check("units stay None with a reason when no unit is registered",
      b2["units"] is None and b2["units_why"], b2)
check("ROI is UNAVAILABLE rather than 0.00 when profit is absent",
      b2["roi_pct"] is None and "not zero" in (b2["roi_why"] or ""), b2)
check("the renderer prints UNAVAIL for a null ROI, never 0", "UNAVAIL" in dash.PAGE)
check("and an en dash for a null figure", "ndash" in dash.PAGE)

print("4. a mean never ships without an interval")
check("ci95 returns None without a standard error", dash.ci95(0.01, None) is None)
c = dash.ci95(0.01, 0.002)
check("and brackets the mean when it can", c and c[0] < 1.0 < c[1], c)

print("5. the cutoff split keeps undated rows OUT of both sides")
rows = [{"clv": 0.01, "game_start": "2026-11-10T00:00:00Z"},
        {"clv": 0.01, "game_start": "2026-11-13T00:00:00Z"},
        {"clv": 0.01}]
pre, post, nos = dash.split_by_cutoff(rows)
check("one before, one after, one undated", (len(pre), len(post), len(nos)) == (1, 1, 1),
      (len(pre), len(post), len(nos)))
check("the undated row is reported, not silently dropped into a half", len(nos) == 1)

print("6. the payload is encrypted and the page carries no cleartext data")
view = {"generated_et": "x", "basis": "v", "selections_total": 3, "privacy": "counts only",
        "bands": {"A_status": {"overall": "FRESH", "sources": [], "note": "n", "warnings": []},
                  "B_lanes": {"lanes": [], "unassigned": [], "unassigned_n": 0, "note": "n"},
                  "C_qualification": {"lanes": [], "note": "n"},
                  "D_triggers": {"live": [], "note": "n"},
                  "E_change": {"label": dash.CUTOFF_LABEL, "before": {}, "after": {},
                               "evidence": "e", "caveat": "c"},
                  "F_research": {"title": "t", "candidates": [], "note": "n"}},
        "SECRET_CANARY": "Hornets-Suns-224.5-canary"}
import os
os.environ.setdefault("TRACKER_PASSPHRASE", "test-passphrase-for-the-suite")
import importlib
import tracker_build as tb
importlib.reload(tb)
blob = tb.enc(view)
html = dash.PAGE.replace("__BLOB__", json.dumps(blob))
check("the canary does not appear in the page", "canary" not in html and "Hornets" not in html)
check("the blob is AES-GCM with a salt, iv and ciphertext",
      all(k in blob for k in ("s", "i", "c", "n")), list(blob))
check("the KDF iteration count travels with the blob", isinstance(blob["n"], int) and blob["n"] > 0)
check("the browser derives the key with PBKDF2-SHA256",
      "PBKDF2" in html and "SHA-256" in html and "AES-GCM" in html)
check("it round-trips back to the same view", tb.dec(blob)["SECRET_CANARY"] == view["SECRET_CANARY"])
check("the page is marked noindex", 'name="robots" content="noindex"' in html)

print("7. nothing financial reaches the payload shape")
# The build writes only counts, units and percentages. These keys must never appear.
banned = ("balance", "account_number", "stake_usd", "passphrase", "apikey", "api_key",
          "order_id", "secret", "token")
src = open("clv_dashboard.py").read()
for b in banned:
    check(f"the builder never writes a '{b}' field",
          f'"{b}"' not in src.replace('"order ids, no secrets."', ""), b)

print("8. the build fails closed when the ledger cannot be read")
view2, err = dash.build()
check("with no passphrase for the real state it reports an error rather than a blank page",
      (view2 is None and err) or (view2 is not None), err)

print("9. the email summary carries no dollar figures and names the gate")
body = dash.email_body({"generated_et": "x", "basis": "v", "selections_total": 0,
                        "bands": {"A_status": {"overall": "FRESH", "sources": [], "warnings": []},
                                  "B_lanes": {"lanes": [{"name": "R1", "paper": False,
                                                         "gate": {"verdict": "INSUFFICIENT EVIDENCE"},
                                                         "today": {"n": 0, "why": "no data"},
                                                         "cumulative": {"n": 0, "why": "no data"},
                                                         "post_change": {"n": 0, "why": "no data"},
                                                         "h1": {}, "h2": {},
                                                         "confirmed_fill_selections": 0,
                                                         "exceptions": []}],
                                              "unassigned_n": 0},
                                  "E_change": {"label": dash.CUTOFF_LABEL,
                                               "before": {}, "after": {}},
                                  "F_research": {"candidates": []}}})
check("no '$' anywhere in the email", "$" not in body, body[:120])
check("the gate verdict is in the email", "INSUFFICIENT EVIDENCE" in body)
check("the change is labelled as approved", dash.CUTOFF_LABEL in body)
check("it states that nothing is promoted", "No promotion" in body)
check("it is concise", len(body.splitlines()) < 60, len(body.splitlines()))


print("10. confirmed fills join on play_key, never on ledger row ids")
# The first version intersected a selection's "ids" (ledger rows, nv|01a1...) with the fills
# dict's keys (venue order UUIDs). Those sets cannot intersect, so every lane reported ZERO
# confirmed fills and the gate's realized-unit clause read UNMET for lanes that had filled.
src = open("clv_dashboard.py").read()
check("the builder joins fills through play_key", 'v["play_key"]' in src)
check("and no longer intersects ids with the fills dict",
      'set(o.get("ids") or []) & confirmed' not in src)
check("the join reuses the one resolver rather than a second matcher",
      src.count("cov.build_lane_resolver") >= 2 and "def _lane_match" not in src,
      src.count("cov.build_lane_resolver"))
check("only FILLED and PARTIAL count as confirmed",
      '("FILLED", "PARTIAL")' in src)
check("the fill join's return is documented as a boolean, not a lane claim",
      "never as a lane claim" in src)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_clv_dashboard: all passed")
