#!/usr/bin/env python3
"""The PMUS_FEE_MODEL variable must actually REACH the runners that price Polymarket US.

Why this file exists: the model switch was built, tested under both models and committed, and
PMUS_FEE_MODEL was passed by NO workflow. Setting the repo variable would have changed nothing while
both Peter and I believed the schedule was active - a no-op that looks like success, which CLAUDE.md
names as the worst failure available ("Check the caller, not just the list"). Code consistency and
deployment are different claims and the regression suite only ever tested the first one.

It also pins the FORWARD / HISTORICAL split, which is deliberate:

  WIRED (follow the variable)     executor-dry-run, sharp-monitor, bets-board, board-page,
                                  ncaab-openers, pmus-slugs - these price decisions and displays
                                  going forward.
  NOT WIRED (stay on legacy)      clv-ledger, test-clv-stale, last50-report, exchange-lag,
                                  ev-sightings, x2-backtest - these report on fills and sightings
                                  already measured at 0.06. Floating them would restate history,
                                  which Peter prohibited ("Preserve historical executed prices and
                                  old-model reporting").

A workflow moving between those lists should fail here and be an explicit decision, not a side effect.
"""
import os

import yaml

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


WF = ".github/workflows"
# workflow -> the scripts it runs that resolve a Polymarket US coefficient
WIRED = {"executor-dry-run": ["executor.py"],
         "sharp-monitor": ["sharp_monitor.py"],
         "bets-board": ["board_build.py", "tracker_build.py"],
         "board-page": ["board_build.py"],
         "ncaab-openers": ["ncaab_grade.py"],
         "pmus-slugs": ["pmus_slugs.py"]}
PINNED = ["clv-ledger", "test-clv-stale", "last50-report", "exchange-lag", "ev-sightings", "x2-backtest"]


def runs_with_env(path, script):
    """(step_found, env_reaches_it) for the step that runs `script`."""
    d = yaml.safe_load(open(path))
    found = reaches = False
    for j in (d.get("jobs") or {}).values():
        jenv = "PMUS_FEE_MODEL" in (j.get("env") or {})
        for st in (j.get("steps") or []):
            run = st.get("run") or ""
            if f"python -u {script}" in run or f"python {script}" in run:
                found = True
                if jenv or "PMUS_FEE_MODEL" in (st.get("env") or {}):
                    reaches = True
    return found, reaches


for wf, scripts in WIRED.items():
    p = f"{WF}/{wf}.yml"
    ok(f"{wf}.yml exists", os.path.exists(p))
    if not os.path.exists(p):
        continue
    for sc in scripts:
        found, reaches = runs_with_env(p, sc)
        ok(f"{wf}.yml still runs {sc}", found)
        ok(f"{wf}.yml passes PMUS_FEE_MODEL to the step running {sc}", reaches)
    s = open(p).read()
    ok(f"{wf}.yml defaults the variable to legacy, not schedule",
       "vars.PMUS_FEE_MODEL || 'legacy'" in s,
       "a default of 'schedule' would activate on deploy instead of on Peter's switch")

for wf in PINNED:
    p = f"{WF}/{wf}.yml"
    if not os.path.exists(p):
        ok(f"{wf}.yml exists", False)
        continue
    ok(f"{wf}.yml is deliberately NOT wired (reports on the basis it measured)",
       "PMUS_FEE_MODEL" not in open(p).read())

# The code default must agree with the workflow default, or the two disagree about what "unset" means.
import pmus_fee as pf  # noqa: E402

ok("the code default is legacy too",
   (os.environ.get("PMUS_FEE_MODEL", "") or "legacy").strip().lower()
   == ("schedule" if os.environ.get("PMUS_FEE_MODEL", "").strip().lower() == "schedule" else "legacy"))
ok("an unrecognised value falls back to legacy, never schedule",
   pf.coef(model="typo")[0] == pf.LEGACY_TAKER,
   "anything that is not exactly 'schedule' must keep the preserved basis")
ok("only the exact string 'schedule' activates", pf.coef(model="schedule")[0] == 0.095)
ok("'Schedule' with a capital does not silently fail to activate via MODEL normalisation",
   "strip().lower()" in open("pmus_fee.py").read())

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
