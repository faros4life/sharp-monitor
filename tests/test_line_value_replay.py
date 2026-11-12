"""Nov 12, 2026: the replay reports coverage honestly and finds changes only where every input exists.
  1. a real-shaped legacy ledger row is UNREPLAYABLE with the missing inputs named (never reconstructed)
  2. a shadow play WITHOUT a reference is counted 'no reference', never valued
  3. a shadow play WITH a two-sided reference (built by the real lvsh.build) is replayed and its changes carry reasons
  4. the LEDGER block is read with rfind + raw_decode, so a duplicated marker earlier in the text cannot win
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value as lv  # noqa: E402
import line_value_replay as rp  # noqa: E402
import line_value_shadow as lvsh  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


ROW = {"key": "NBA|A @ B|total|UNDER", "source": "rules", "verdict": "WOULD PLACE", "alert_utc": "2026-11-12T12:15:17Z",
       "alert_line": 214.5, "alert_price_after_fee": -111,
       "venues_considered": [{"book": "novig", "after_fee": -111, "line": 214.5, "thr": -113},
                             {"book": "novig", "after_fee": -100, "line": 213.5, "thr": -101}]}
txt = "noise LEDGER (machine-readable) earlier\n[]\nLEDGER (machine-readable, rows)\n" + json.dumps([ROW])
r = rp.report([txt])
ck("rfind reads the LAST ledger block", r["ledger_rows_examined"] == 1)
ck("legacy row: 0 exact under either calc", r["legacy_exact"] == 0 and r["new_calc_exact"] == 0)
for need in ("independent_reference", "exact_hp", "complete_prefilter_ladder", "rejected_candidates"):
    ck(f"legacy row names missing input {need}", r["unreplayable_inputs"][need] == 1)
ck("no changes are claimed from a legacy row", not r["would_reject"] and not r["would_admit"])

# NFL spread, alert -2.5 candidate -3.5? build both a no-reference play and a referenced play through the REAL build()
ctx = dict(play_key="k", source="rules", sport="NFL", mtype="spread", side=0, alert_line=-2.5, alert_af=-110,
           tol_cents=2, tol_books=["novig"], hp=0.02, hp_src="HP_FALLBACK", floor=None, now_utc="2026-11-12T12:00:00Z")
notes = [dict(book="novig", line=-3.5, am_after_fee=-104, legacy="qualified", hb=1, c_eq_q=0.5, thr=-105),
         dict(book="novig", line=-2.5, am_after_fee=-110, legacy="qualified", hb=0, c_eq_q=0.5, thr=-112)]
worse = lambda am, c: am - c if am < 0 else am - c  # placeholder, replaced below if executor helper exists
try:
    import executor as ex
    worse = ex.cents_worse if hasattr(ex, "cents_worse") else worse
except Exception:
    pass
noref = lvsh.build(ctx, [dict(book="novig", line=-2.5, am_after_fee=-110)], notes, worse)
from datetime import datetime, timedelta, timezone
_now = datetime(2026, 11, 12, 12, 0, 30, tzinfo=timezone.utc)
pin = {"market": {"outcomes": [{"name": "A", "point": -2.5, "price": -110}, {"name": "B", "point": 2.5, "price": -110}],
                  "last_update": "2026-11-12T12:00:00Z"}, "mine": "A", "book": "pinnacle",
       "read_utc": "2026-11-12T12:00:10Z", "commence_utc": "2026-11-12T18:00:00Z"}
ref = lvsh.build(dict(ctx, pin=pin, now_dt=_now, start_utc="2026-11-12T18:00:00Z"), [dict(book="novig", line=-2.5, am_after_fee=-110)],
                 notes, worse)
ck("no-reference play has no reference", noref["reference"] is None)
ck("referenced play carries the reference timestamp", (ref["reference"] or {}).get("ts") == "2026-11-12T12:00:00Z", str(ref.get("reference")))
sh_txt = "LINEVALUE (machine-readable)\n" + json.dumps({"plays": [noref, ref], "rechecks": []})
r2 = rp.report([sh_txt])
ck("shadow: 2 plays, 1 with reference", r2["shadow_plays"] == 2 and r2["shadow_with_reference"] == 1)
ck("shadow candidates partition exactly", r2["shadow_candidates"] == r2["shadow_supported"] + r2["shadow_unsupported"] + r2["shadow_no_reference"])
ck("no-reference candidates are counted, not valued", r2["shadow_no_reference"] == 2)
for x in r2["would_reject"] + r2["would_admit"]:
    ck("every change carries a reason", bool(x.get("why")))
ck("render runs", "DECISIONS THAT CHANGE" in rp.render(r2))
# ledger rows that carry the capture (new design: no separate email)
row_ok = dict(ROW, lvs_capture="ok", lvs=ref, lvs_rechecks=[{"play_key": "k"}])
row_bad = dict(ROW, key="NBA|C @ D|total|OVER", lvs_capture="error: KeyError: x")
r3 = rp.report(["LEDGER (machine-readable, rows)\n" + json.dumps([row_ok, row_bad, ROW])])
ck("ledger-embedded play is replayed", r3["shadow_plays"] == 1 and r3["shadow_with_reference"] == 1, str(r3["shadow_plays"]))
ck("capture statuses are counted by name", r3["capture_status"]["ok"] == 1 and r3["capture_status"]["error"] == 1
   and r3["capture_status"]["absent (row predates capture)"] == 1, str(dict(r3["capture_status"])))
ck("recorded inputs are not called missing when capture ok", r3["unreplayable_inputs"]["exact_hp"] == 2, str(dict(r3["unreplayable_inputs"])))
ck("rechecks ride along", r3["rechecks_recorded"] == 1, "")
ck("gap wording says evaluated, never 'none' for an evaluated gap", "EVALUATED on 3 rows" in rp.render(r3), "")
gap = dict(ROW, key="NCAAF|X @ Y|total|OVER", alert_line=60.5, source="rules",
           venues_considered=[{"book": "novig", "after_fee": -115, "line": 59.5, "thr": -118}])
ok_ = dict(ROW, key="NCAAF|X @ Y|total|OVER", alert_line=55.5, source="rules", venues_considered=[{"book": "novig", "after_fee": -115, "line": 54.5}])
board = dict(gap, key="NCAAF|Z @ W|total|OVER", source="board")
r4 = rp.report(["LEDGER (machine-readable, rows)\n" + json.dumps([gap, ok_, board])])
ck("Lane 1 NCAAF 58-68 gap counted separately (board lane excluded)", r4["lane1_examined"] == 2 and r4["lane1_ncaaf_total_gap_58_68"] == 1, str((r4["lane1_examined"], r4["lane1_ncaaf_total_gap_58_68"])))
ck("...and shown as a percentage of Lane 1", "(50.0% of Lane 1)" in rp.render(r4))
# per-fill detail: -130 fills first, hp recovered only from a recorded off-line threshold
real = json.loads(open("/tmp/real/ledger_nov12_0738.txt").read().split("latency = decision time minus first alert time)\n", 1)[1]) if os.path.exists("/tmp/real/ledger_nov12_0738.txt") else []
f130 = dict(ROW, key="NBA|A @ B|total|UNDER", alert_line=214.5, alert_price_after_fee=-111, fill_book="novig", fill_line=213.5, fill_price_after_fee=-130,
            venues_considered=[{"book": "novig", "after_fee": -130, "line": 213.5, "thr": -128, "tolerance_cents": 2}])
d = rp.fill_detail(f130)
ck("-130 fill: flagged, replacement max from prob points (half point under: 1.1576 pts), verdict given with reason",
   d["is_minus_130"] and d["method"] == "prob_points" and d["repl_verdict"] in ("would_accept", "would_reject") and "allowance" in d["repl_reason"], str(d))
ck("-130 fill: old hp recovered from the off-line threshold with its rounding error", d["old_hp"] is not None and d["old_hp_err"] > 0, str(d))
nohp = dict(f130, venues_considered=[{"book": "novig", "after_fee": -130, "line": 214.5, "thr": -113}])
ck("no off-line candidate -> hp marked unrecoverable, not guessed", rp.fill_detail(nohp)["old_hp"] is None and "no off-line" in rp.fill_detail(nohp)["old_hp_note"])
nfl = dict(f130, key="NFL|A @ B|spread|", alert_line=-3.5, fill_line=-2.5)
ck("NFL fill without a reference is unresolved/no_reference", rp.fill_detail(nfl)["repl_verdict"] == "unresolved" and "no_reference" in rp.fill_detail(nfl)["repl_reason"])
fc = rp.fill_counts([d, rp.fill_detail(nfl)])
ck("fill counts separate -130 verdicts", fc["fills_at_-130"] == 2 and fc["verdict:unresolved"] == 1)
ck("detail carries no stake or balance field", not any(k in d for k in ("risk", "stake", "balance", "units")))
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
