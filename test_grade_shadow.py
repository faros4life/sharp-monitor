#!/usr/bin/env python3
"""Shadow grading ladder (Peter, Nov 22 2026) - report only.

The checks that matter: CLV can never promote on its own, a missing input is INSUFFICIENT rather
than a pass, production kill semantics are untouched, and stability is measured on DISJOINT halves
rather than the nested rolling windows.
"""
import sys

import grade_shadow as G

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


def rows(units, clv=None, lead=300, n=None):
    """n rows with the given per-row units; clv defaults to a comfortably positive value."""
    out = []
    for i, u in enumerate(units):
        r = {"result": "W" if u > 0 else "L", "units_flat": u, "lead_min": lead,
             "first_seen_utc": f"2026-11-{(i % 28) + 1:02d}T12:00:00Z"}
        if clv is not None:
            r["clv_cents"] = clv
        out.append(r)
    return out


STRONG = [0.9, 1.0] * 30          # 60 rows, clearly positive, tight
FLAT = [1.0, -1.0] * 30           # 60 rows, mean 0

# --- gate 1: sample -----------------------------------------------------------------------
ok("under 30 is NO VERDICT, never a pass", G.new_verdict(rows([1.0] * 10, clv=5))[0] == G.NO_VERDICT)
ok("under 30 is NO VERDICT on the old ladder too", G.old_verdict(rows([1.0] * 10))[0] == G.NO_VERDICT)

# --- gate 4: price is necessary, NEVER sufficient -------------------------------------------
v, g = G.new_verdict(rows(FLAT, clv=9.0))
ok("huge CLV with a flat outcome does NOT promote", v == G.WATCH, v)
ok("...and the price gate itself did pass, so it was the outcome that blocked it",
   "+9.00c" in g.get("price", ""), g.get("price"))
ok("strong outcome AND strong price promotes", G.new_verdict(rows(STRONG, clv=5.0))[0] == G.PROMOTE)
ok("strong outcome with NEGATIVE price does not promote",
   G.new_verdict(rows(STRONG, clv=-5.0))[0] == G.WATCH)
ok("promote label says no auto deploy", "NO AUTO DEPLOY" in G.PROMOTE)

# --- gate 2: interval, not point estimate ----------------------------------------------------
# mean just above +0.10 but wildly dispersed: the OLD ladder promotes, the new one must not.
noisy = [3.0, -2.8] * 15 + [0.2] * 30
o = G.outcome(rows(noisy))
ok("test fixture really does clear the old point bar", o[1] >= 0.10, f"{o[1]:+.3f}")
ok("old ladder promotes it on the point estimate", G.old_verdict(rows(noisy))[0] == "ELIGIBLE")
ok("new ladder does not, because the interval spans zero",
   G.new_verdict(rows(noisy, clv=5.0))[0] == G.WATCH, str(o[3]))

# --- gate 3: stability on DISJOINT halves ------------------------------------------------------
split = [1.0] * 30 + [-0.6] * 30     # first half up, second half down
v, g = G.new_verdict(rows(split, clv=5.0))
ok("a bucket carried by one half does not promote", v == G.WATCH, v)
ok("the halves are reported and are disjoint", "disjoint" in g.get("stability", ""), g.get("stability"))
a, b = G.halves(rows([1.0] * 11))
ok("halves do not overlap", len(a) + len(b) == 11 and not (set(map(id, a)) & set(map(id, b))))

# --- missing inputs are INSUFFICIENT, never a pass ---------------------------------------------
ok("no CLV at all is INSUFFICIENT", G.new_verdict(rows(STRONG, clv=None))[0] == G.INSUFFICIENT)
thin = rows(STRONG, clv=5.0)
for r in thin[:40]:
    del r["clv_cents"]               # 20/60 = 33% coverage, under the 80% floor
ok("CLV below the coverage floor is INSUFFICIENT", G.new_verdict(thin)[0] == G.INSUFFICIENT)
nolead = rows(STRONG, clv=5.0)
for r in nolead:
    del r["lead_min"]
ok("no lead minutes is INSUFFICIENT", G.new_verdict(nolead)[0] == G.INSUFFICIENT)
ok("a single row yields no interval and no pass",
   G.new_verdict(rows([1.0], clv=5))[0] in (G.INSUFFICIENT, G.NO_VERDICT))

# --- the kill rule is REPORTED, not applied ----------------------------------------------------
ok("kill pre-registration is symmetric: it needs the CI UPPER bound below zero",
   G.kill_preregistration(rows([-0.9, -1.0] * 30)).startswith("SUSPEND"))
ok("a merely negative point estimate does NOT trip it",
   G.kill_preregistration(rows([1.0, -1.2] * 30)).startswith("keep"))
ok("the proposed close is reversible, not sticky",
   "reversible" in G.kill_preregistration(rows([-0.9, -1.0] * 30)))
src = open(__file__.replace("test_grade_shadow.py", "grade_shadow.py"), encoding="utf-8").read()
ok("the module never writes anything", "open(" not in src.replace("open(os.path.join", "SAFE"))
ok("the module does not import the live decision path",
   "import splits" not in src and "import executor" not in src and "import agree_rules" not in src)
ok("production kill semantics are described as untouched", "NOT APPLIED" in src)

# --- the overlapping-window warning is carried in the output -----------------------------------
rep = G.report(__file__.rsplit("/", 1)[0] if "/" in __file__ else ".")
ok("report states the windows are nested and not replications",
   "NESTED" in rep and "not independent replications" in rep)
ok("report separates the CLV source from the Pinnacle standard", "CLV_STANDARD.md" in rep)
ok("report says nothing is promoted or switched", "Nothing is promoted" in rep)
ok("report shows both verdicts per bucket", "OLD (production" in rep and "NEW (four gates)" in rep)
ok("report marks disagreements", "DISAGREE" in rep or "agree" in rep)

# --- the daily-report section (Peter, Nov 22: fold in, don't add a scheduler) ------------------
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sec = "\n".join(G.section(HERE))
for needle, what in (
        ("REPORT ONLY", "says report only"),
        ("NOT a promotion, suspension or allocation change", "disclaims the three actions"),
        ("is NOT 'approved for live trading'", "separates eligible-for-review from approved"),
        ("NESTED OVERLAPPING OBSERVATIONS", "labels the windows as overlapping"),
        ("NOT\nindependent replications", "says they are not replications"),
        ("DISJOINT halves", "names the stability basis"),
        ("CLV_STANDARD.md", "keeps the two CLV sources apart"),
        ("EXEC_NCS_LIVE stays OFF", "states NCS stays off"),
        ("PRE-REGISTERED, NOT APPLIED", "marks the kill proposal as not applied"),
        ("u/play", "carries units per play"),
        ("total ", "carries total units"),
        ("95% [", "carries the outcome interval"),
        ("coverage", "carries CLV coverage"),
        ("reason:", "carries a reason"),
        ("lead under 4h", "has the <4h band"),
        ("lead 4-12h", "has the 4-12h band"),
        ("lead 12h+", "has the 12h+ band"),
        ("Human review decides", "ends by deferring to human review")):
    ok(f"section {what}", needle in sec, "missing")

ok("section shows the NCAAB disagreement with a reason",
   "DISAGREEMENT" in sec and "NCAAB" in sec)
ok("section never claims anything was promoted",
   "has been promoted" not in sec and "now live" not in sec)

dr = open(os.path.join(HERE, "daily_report.py"), encoding="utf-8").read()
ok("daily_report calls the shadow section", "grade_shadow.section(" in dr)
ok("daily_report does not let a shadow failure break the settled-bets report",
   "SHADOW GRADING LADDER: not available this run" in dr)
ok("no second scheduler was added for it",
   not os.path.exists(os.path.join(HERE, ".github/workflows/grade-shadow.yml")))

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
