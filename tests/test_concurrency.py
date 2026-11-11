"""Two overlapping executor runs cannot submit duplicate orders or exceed risk limits.

The load-bearing protection is the workflow concurrency group, not the code: two runs that
overlapped would each read the registry before either placed, so both could pass the same limit
checks. GitHub's concurrency group makes the overlap impossible - at most one run in the group
executes, and with cancel-in-progress: false a newer run WAITS rather than killing the one in
flight (which is also why a half-finished order pass is never cut short).

These tests pin that configuration so a future edit cannot quietly remove it, and confirm no
other workflow can reach the order code.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
WF = os.path.join(ROOT, ".github/workflows")

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


def text(f):
    with open(os.path.join(WF, f)) as fh:
        return fh.read()


ex_wf = [f for f in sorted(os.listdir(WF)) if f.endswith(".yml") and "executor.py" in text(f)]
ck("the executor-running workflows are known", set(ex_wf) == {"executor-dry-run.yml", "pmus-slugs.yml"},
   str(ex_wf))

# ---------------------------------------------------------------- the real executor
e = text("executor-dry-run.yml")
ck("executor-dry-run declares a concurrency group", re.search(r"^concurrency:", e, re.M) is not None)
ck("  the group is 'executor'", re.search(r"^\s*group:\s*executor\s*$", e, re.M) is not None)
ck("  cancel-in-progress is FALSE (never kill a half-finished order pass)",
   re.search(r"^\s*cancel-in-progress:\s*false\s*$", e, re.M) is not None)
ck("  it is NOT true (a newer run must never cancel one that may hold an order)",
   re.search(r"cancel-in-progress:\s*true", e) is None)
ck("executor-dry-run actually runs the executor", re.search(r"python\s+-u\s+executor\.py", e) is not None)
ck("executor-dry-run reads the real EXEC_LIVE variable",
   "EXEC_LIVE: ${{ vars.EXEC_LIVE }}" in e)
ck("executor-dry-run reads the real EXEC_BOARD_LIVE variable, defaulting off",
   "vars.EXEC_BOARD_LIVE || 'off'" in e)
ck("its timeout exceeds a single pass (passes run 6-15 min)",
   (m := re.search(r"timeout-minutes:\s*(\d+)", e)) and int(m.group(1)) >= 30, m.group(1) if m else "none")

# ---------------------------------------------------------------- the other mention is a comment
p = text("pmus-slugs.yml")
ck("pmus-slugs only MENTIONS executor.py in a comment",
   all(l.lstrip().startswith("#") for l in p.splitlines() if "executor.py" in l))
ck("pmus-slugs does not run the executor", re.search(r"python\s+-u\s+executor\.py", p) is None)
ck("pmus-slugs is given no EXEC_LIVE, so its code could not place anyway", "EXEC_LIVE" not in p)

# ---------------------------------------------------------------- nothing else can reach order code
order_mods = ("px_live.py", "book_live.py")
for f in sorted(os.listdir(WF)):
    if not f.endswith(".yml"):
        continue
    t = text(f)
    runs_order = any(re.search(r"python\s+-u\s+" + re.escape(m), t) for m in order_mods)
    ck(f"{f} does not run an order module directly", not runs_order)
    if f == "executor-dry-run.yml":
        continue
    if "EXEC_LIVE: ${{ vars.EXEC_LIVE }}" in t:
        ck(f"{f} passes the live switch but is not the executor - must have a concurrency group",
           re.search(r"^concurrency:", t, re.M) is not None, f)

# live-switch-check hardcodes EXEC_LIVE on; it must stay order-free
s = text("live-switch-check.yml")
ck("live-switch-check hardcodes EXEC_LIVE on for itself only", 'EXEC_LIVE: "on"' in s)
ck("  and runs only the brake check, never the executor",
   re.search(r"python\s+-u\s+live_switch_check\.py", s) is not None
   and re.search(r"python\s+-u\s+executor\.py", s) is None)
ck("  and is manual-dispatch only (no schedule that could collide)",
   "workflow_dispatch" in s and not re.search(r"^\s*schedule:", s, re.M))
with open(os.path.join(ROOT, "live_switch_check.py")) as fh:
    lsc = fh.read()
# Judge CALL NODES, not prose: the file's own docstring says "place() / submit_order are never
# called", which a substring check reads as a call.
import ast as _ast  # noqa: E402

_called = set()
for _n in _ast.walk(_ast.parse(lsc)):
    if isinstance(_n, _ast.Call):
        _f = _n.func
        _called.add(_f.attr if isinstance(_f, _ast.Attribute) else getattr(_f, "id", ""))
ck("  and its script contains no order CALL",
   not ({"place", "submit_order", "kalshi_place", "pmus_place", "novig_place"} & _called),
   str(sorted(_called)))

# ---------------------------------------------------------------- what the code does on top
import executor as ex  # noqa: E402
import inspect  # noqa: E402

ck("the registry is loaded before any order (serialises exposure within a run)",
   inspect.getsource(ex.live_order).index("live_guards()")
   < inspect.getsource(ex.live_order).index("journal_intent("))
ck("an unknown registry refuses (so a run that cannot read exposure places nothing)",
   "fail closed" in inspect.getsource(ex.live_guards))
ck("board exposure unknown refuses", ex.board_gate(100.0, "k")[0] is False)
ck("the write-ahead row is readable by the NEXT run before this run confirms an order",
   "INTENT_SUBJECT_PREFIX" in inspect.getsource(ex.intent_readable))
ck("limits are re-derived from the registry each run, not carried in memory",
   'BOARD = {"risk": 0.0' in inspect.getsource(ex) or 'BOARD["risk"]' in inspect.getsource(ex.bot_orders))

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
