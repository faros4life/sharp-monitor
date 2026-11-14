#!/usr/bin/env python3
"""clv_liqbot_compare: the published figure is never overwritten, and the verdict cannot promote.

Peter, Nov 14: "Add a clearly labelled reconciled LIQ-BOT comparison alongside the original
+23.81u alert-price result. Do not overwrite the published result." The protection has to be
structural, so it is tested here: the module must not open SCORECARD.md or REGISTRY.md for
writing, and the frozen numbers it quotes must be constants, not recomputed.
"""
import clv_liqbot_compare as lb

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


src = open("clv_liqbot_compare.py").read()

print("1. the published files are never written")
for f in ("SCORECARD.md", "REGISTRY.md"):
    check(f"{f} is not opened for writing",
          f'open("{f}", "w")' not in src and f"open('{f}', 'w')" not in src)
import re
writes = re.findall(r'open\(\s*([^,]+?)\s*,\s*["\']w["\']\s*\)', src)
check("every write target is OUT or a path under audit/",
      writes and all(w == "OUT" or w.strip('"\'').startswith("audit/") for w in writes), writes)
check("both the report and its json are written", 'open(OUT, "w")' in src
      and 'open("audit/liqbot_reconciled.json", "w")' in src)
check("OUT lives under audit/", lb.OUT.startswith("audit/"), lb.OUT)

print("2. the frozen figures are constants, quoted not recomputed")
check("registry 9 published n is 151", lb.PUBLISHED["registry9"]["n"] == 151)
check("registry 9 published units are +23.81u", lb.PUBLISHED["registry9"]["units"] == 23.81)
check("the board's published figures are kept too",
      lb.PUBLISHED["board"]["n"] == 2665 and lb.PUBLISHED["board"]["units"] == -29.04)
check("the published basis is labelled NOT executable",
      "NOT executable" in lb.PUBLISHED["registry9"]["basis"])

print("3. selection and unit math are imported, not re-implemented")
check("the registry-9 selector comes from nba_totals_master",
      "ntm.lead_min" in src and "ntm.nba_totals" in src)
check("the unit arithmetic comes from nba_totals_master", "ntm.units_of" in src)
check("the CLV formula comes from clv_basis via the audit waterfall", "oa.classify" in src)

print("4. a mean is never reported without a bound")
c = lb.ci([0.01, 0.02, -0.03, 0.00, 0.015])
check("ci returns an interval for n>=2", c is not None and c[0] < c[1], c)
check("ci refuses n<2", lb.ci([0.01]) is None and lb.ci([]) is None)

print("5. the verdict cannot reach POTENTIAL PASS - this population has no fills")
v = [{"row": {"result": "W", "price": 0.5, "alerted_utc": f"2026-11-{i + 1:02d}T00:00:00Z"},
      "clv": 0.05} for i in range(40)]
out = lb.verdict(v[:20], v[20:], v, [x["row"] for x in v])
check("even an all-positive, well-covered sample is not promoted", "POTENTIAL PASS is unreachable" in out, out[:120])
check("and it says why", "ACTUAL FILLS" in out)
check("a uniformly positive sample is not called a FAIL either", "CLEAR FAIL" not in out, out[:90])

print("6. a negative, well-covered CLV CI reads as CLEAR FAIL on the basis")
v = [{"row": {"result": "L", "price": 0.5, "alerted_utc": f"2026-11-{i + 1:02d}T00:00:00Z"},
      "clv": -0.03 - (i % 3) * 0.001} for i in range(40)]
out = lb.verdict(v[:20], v[20:], v, [x["row"] for x in v])
check("negative CI excluding zero -> CLEAR FAIL", "CLEAR FAIL" in out, out[:120])

print("7. thin coverage never produces a verdict stronger than CONTINUE")
v = [{"row": {"result": "L", "price": 0.5, "alerted_utc": f"2026-11-{i + 1:02d}T00:00:00Z"},
      "clv": -0.03} for i in range(10)]
out = lb.verdict(v[:5], v[5:], v, [x["row"] for x in v] * 10)   # 10% coverage
check("10% coverage -> CONTINUE TESTING, not CLEAR FAIL",
      "CONTINUE TESTING" in out and "CLEAR FAIL" not in out, out[:140])
check("both coverage denominators are named", "of all rows" in out and "PRICEABLE" in out, out[-200:])

print("8. no verified rows at all -> INSUFFICIENT EVIDENCE, no direction claimed")
out = lb.verdict([], [], [], [{"result": "W"}])
check("INSUFFICIENT EVIDENCE", "INSUFFICIENT EVIDENCE" in out, out[:90])
check("no sign is implied", "negative" not in out.lower() and "positive" not in out.lower(), out)

print("9. block() runs end to end on a synthetic population")
# Why this exists: the module shipped with a NameError in block()'s return dict (a renamed
# variable), which every helper-level test above passed straight over. It only surfaced in
# Actions, after the recovery step had already run. A report that cannot be exercised locally
# gets exercised in production instead.
import clv_obs_audit as oa_

_rows = [{"result": "W" if i % 3 else "L", "price": 0.5, "book": "kalshi", "league": "NBA",
          "market": "total", "side": "UNDER", "line": 220.5, "lead_min": 300,
          "alerted_utc": f"2026-11-{i % 28 + 1:02d}T00:00:00Z",
          "start": f"2026-11-{i % 28 + 1:02d}T05:00:00Z",
          "game": "Alpha Antelopes @ Beta Bobcats"} for i in range(12)]

_orig = oa_.classify
try:
    # half verified with a real CLV, half not: exercises both the covered and uncovered paths
    def _fake(x, src, *a, **k):
        if (x.get("line") or 0) and int(str(x.get("alerted_utc"))[8:10]) % 2 == 0:
            return "VERIFIED_PINNACLE", {"p": 0.52, "entry": 1.94, "clv": 0.0088,
                                        "how": "own line", "fid": "f1"}
        return "MISSING_HISTORY", "fixture f1 has no cached Pinnacle history"
    oa_.classify = _fake
    before = len(lb.L)
    out = lb.block("synthetic", _rows, lb.PUBLISHED["registry9"], {}, {}, {}, {},
                   "synthetic population")
    body = "\n".join(lb.L[before:])
    check("block returns a summary dict", isinstance(out, dict) and "n_verified" in out, out)
    check("it reports both halves", "| H1 |" in body and "| H2 |" in body)
    check("the frozen published figure is printed unchanged", "+23.81u" in body)
    check("units are labelled after fees in the halves table", "units (after fees)" in body)
    check("the entry-price-did-not-move note is present",
          "does NOT differ between the last two columns" in body)
    check("a population that does not match the frozen one is flagged first",
          "Population difference" in body, body[-500:])
    check("and an unexplained drop is not explained away",
          "NOT explained here" in body or "logged and graded since" in body, body[-500:])
finally:
    oa_.classify = _orig

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_liqbot_compare: all passed")
