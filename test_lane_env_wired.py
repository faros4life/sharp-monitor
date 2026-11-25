"""Every lane knob the executor reads from the environment must actually be PASSED to the job.

Nov 25, 2026. Peter set the repo variable EXEC_DOGS_DAILY_RISK to 2400. The workflow never passed
it, so the job read an unset variable and fell back to the code default of 800 - the cap stayed
where it was while the settings page said otherwise. A no-op that looks like success.

This is the second time: the Nov 11 note in executor-dry-run.yml records EXEC_BOARD_DAILY_RISK and
EXEC_DAILY_STOP having the same problem. Catching it by hand twice is enough, so it is a test now.

The rule asserted here: for every `os.environ.get("EXEC_...")` the executor reads for a lane's unit,
cap, play limit or risk limit, the workflow that places orders must pass that name - and its YAML
default must equal the code default, or the same knob means two different things depending on
whether the variable happens to be set."""
import re

import yaml

FAILED = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


SRC = open("executor.py", encoding="utf-8").read()
WF = ".github/workflows/executor-dry-run.yml"
RAW = open(WF, encoding="utf-8").read()
Y = yaml.safe_load(RAW)
ENV = {}
for j in Y["jobs"].values():
    for st in j["steps"]:
        ENV.update(st.get("env") or {})

# Every EXEC_* read with a literal fallback, as `os.environ.get("NAME", "") or "DEFAULT"`.
READS = dict(re.findall(r'os\.environ\.get\(\s*"(EXEC_[A-Z0-9_]+)"\s*,\s*""\s*\)\s*or\s*"([^"]+)"', SRC))
ok("the executor reads some EXEC_ knobs with defaults", len(READS) >= 4, len(READS))

# The risk/cap knobs are the ones where a silent fallback costs money or opportunity.
MONEY = {k: v for k, v in READS.items()
         if any(w in k for w in ("DAILY_RISK", "MAX_PLAYS", "DAILY_STOP", "UNIT"))}
ok("found the lane risk/cap knobs", len(MONEY) >= 4, sorted(MONEY))

for name, code_default in sorted(MONEY.items()):
    passed = name in ENV
    ok(f"{name}: passed to the job that places orders", passed)
    if not passed:
        continue
    expr = str(ENV[name])
    m = re.search(r"\|\|\s*'([^']*)'", expr)
    if m:   # the usual shape: read the repo variable, fall back to a default
        ok(f"{name}: workflow default {m.group(1)!r} matches the code default {code_default!r}",
           m.group(1).strip() == code_default.strip())
        ok(f"{name}: reads the repo variable, not a hardcoded value", "vars." + name in expr, expr)
    else:   # a deliberate literal (EXEC_UNIT): still must agree with the code default
        ok(f"{name}: literal {expr!r} matches the code default {code_default!r}",
           expr.strip() == code_default.strip(), expr)

# The two that were missing today, named explicitly so a future edit cannot quietly drop them.
for name in ("EXEC_DOGS_DAILY_RISK", "EXEC_NCS_DAILY_RISK", "EXEC_DOGS_LIVE"):
    ok(f"{name} is wired (missing on Nov 25)", name in ENV)

# Dogs is a $300 unit in code; the workflow comment must not still say $100.
ok("executor's DOGS_UNIT is 300", "DOGS_UNIT = 300.0" in SRC)
ok("the workflow comment no longer calls it a $100 unit",
   "Own $100 unit" not in RAW)

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
