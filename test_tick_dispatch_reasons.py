"""tick must say WHICH workflow failed and WHY, not just how many. Nov 25, 2026.

`tick: errors 1` ran on every cycle for twelve days. The cause was ev-sightings, a paper study
Peter closed on Nov 13 and disabled on GitHub, left sitting in JOBS so tick tried to dispatch it
every ten minutes and GitHub refused every time. Nothing was lost by those failures - the study
was meant to stop - but the error channel was saturated: a real second failure would have read as
`errors 2` and nobody would have looked, because the line always had a number in it.

Two states with opposite remedies in one counter. A disabled workflow should be taken OUT of the
table; a failing one should be FIXED. These checks pin the split and the reason."""
import tick

# The dispatch table as it must stand after ev-sightings was retired (Nov 25). Pinned by name so
# that dropping any OTHER workflow - the failure mode this whole change is about - fails loudly
# instead of quietly reducing what gets dispatched.
EXPECTED_AFTER = {
    "nba-model.yml", "x2-tag.yml", "clv-ledger.yml", "slow-hr.yml", "plimit-logger.yml",
    "exchange-lag.yml", "hcache-fill.yml", "liq-small-fwd.yml", "model-lab.yml",
    "liquidity-monitor.yml", "deadman.yml", "signal-alerts.yml", "balances-email.yml",
    "ncaab-openers.yml", "plimit-level.yml", "reporting-ledger.yml", "clv-dashboard.yml",
    "p2-audit.yml",
}

FAILED = []
CALLS = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


def fake_gh(rc, out="", err=""):
    def g(*args):
        CALLS.append(args)
        return rc, out, err
    return g


# --- the closed study is out of the dispatch table ---------------------------------------------
ok("ev-sightings is no longer dispatched", "ev-sightings.yml" not in tick.JOBS)
ok("it is not in the daily table either", "ev-sightings.yml" not in tick.DAILY_ET)
ok("the rest of the table is intact", len(tick.JOBS) + len(tick.DAILY_ET) == 18,
   len(tick.JOBS) + len(tick.DAILY_ET))

# --- every OTHER scheduled workflow is unaffected and still dispatchable ------------------------
import os
import yaml
for wf in list(tick.JOBS) + list(tick.DAILY_ET):
    p = os.path.join(".github/workflows", wf)
    ok(f"{wf}: still present", os.path.exists(p))
    y = yaml.safe_load(open(p))
    on = y.get("on", y.get(True))                 # YAML 1.1 reads a bare `on:` as True
    ok(f"{wf}: still has workflow_dispatch", isinstance(on, dict) and "workflow_dispatch" in on)
ok("every remaining entry has a cadence", all(isinstance(v, int) and v > 0 for v in tick.JOBS.values()))
ok("ev-sightings is the ONLY entry removed",
   set(tick.JOBS) | set(tick.DAILY_ET) == EXPECTED_AFTER, sorted(set(tick.JOBS) | set(tick.DAILY_ET)))

# --- gh() hands back stderr, which is where the reason lives -----------------------------------
import inspect
ok("gh returns stderr", "r.stderr" in inspect.getsource(tick.gh))
ok("no caller unpacks the old two-value return",
   not [l for l in inspect.getsource(tick).splitlines()
        if "= gh(" in l and "def gh" not in l and l.count(",") < 2])

# --- a disabled workflow is its own state, not an error ----------------------------------------
orig = tick.gh
try:
    tick.gh = fake_gh(1, err="HTTP 403: Workflow does not have 'workflow_dispatch' trigger / "
                             "the workflow is disabled and cannot be dispatched")
    ok("a disabled workflow reports 'disabled'", tick.dispatch("x.yml") == "disabled")

    tick.gh = fake_gh(0)
    ok("a good dispatch reports 'started'", tick.dispatch("x.yml") == "started")

    tick.gh = fake_gh(1, err="HTTP 404: Not Found")
    r = tick.dispatch("x.yml")
    ok("a real failure is neither 'started' nor 'disabled'", r not in ("started", "disabled"), r)
    ok("a real failure carries the reason", "404" in r, r)

    # the reason must survive even when gh says nothing at all
    tick.gh = fake_gh(7, err="")
    r = tick.dispatch("x.yml")
    ok("a silent failure still reports its rc", "7" in r, r)

    # a multi-line error reports its last line, not a wall of text
    tick.gh = fake_gh(1, err="line one\nline two\nHTTP 422: unprocessable")
    r = tick.dispatch("x.yml")
    ok("a multi-line error is trimmed to the useful line", r.startswith("HTTP 422"), r)
    ok("the reason is length-bounded", len(tick.dispatch("x.yml")) <= 140)
finally:
    tick.gh = orig

# --- the three states are reported separately, and failures are NAMED ---------------------------
src = inspect.getsource(tick.main)
ok("started, disabled and errors are counted apart",
   "started {started}, disabled {len(disabled)}, errors {len(failed)}" in src)
ok("each failing workflow is named with its reason", "DISPATCH FAILED {wf}" in src)
ok("each disabled workflow is named, with what to do about it",
   "DISABLED, not dispatched" in src and "take it out of JOBS" in src)
ok("exceptions carry their type instead of being swallowed",
   "type(ex).__name__" in src and "except Exception:\n            failed" not in src)
ok("a failed run-list is distinguished from a failed dispatch", "run list failed" in src)

# --- the log stays counts-only: names and gh's own text, nothing financial ----------------------
for bad in ("$", "stake", "profit", "balance", "units"):
    ok(f"log line carries no {bad!r}", bad not in src)

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
