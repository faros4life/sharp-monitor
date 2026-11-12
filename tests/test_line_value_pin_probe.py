"""Nov 12: the Pinnacle probe is bounded (one read per league, capped), order-free, and reports usage."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value_pin_probe as pp  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


src = open(pp.__file__).read()
mods = {n.names[0].name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import)} | {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
ck("imports no order/execution/mail code", not (mods & {"executor", "px_live", "book_live", "smtplib", "registry"}), str(mods))
ck("one read per league and a hard cap", src.count("pin_read(") == 2 and "[:MAX_LEAGUES]" in src and "PROBE_MAX_LEAGUES" in src)
ck("records and prints the Odds API quota headers", "x-requests-remaining" in src and "Pinnacle calls this run" in src)
ck("uses the shared convert() and the shared reference builder", "lv.convert(" in src and "lvr.pinnacle_reference(" in src)
wf = open(os.path.join(os.path.dirname(pp.__file__), ".github/workflows/line-value-pin-probe.yml")).read()
ck("workflow is dispatch-only with contents:read, no schedule, no order secrets",
   "workflow_dispatch" in wf and "schedule" not in wf and "contents: read" in wf and "PMUS" not in wf and "NOVIG" not in wf and "EMAIL_TO" not in wf)
# offline: no key -> no read, no crash
os.environ.pop("ODDS_API_KEY", None)
ck("no key -> reads nothing and returns cleanly", pp.main() == 0 and not pp.USAGE)
# the reference failure reasons come from line_value_ref, not from the probe
ck("the probe never invents a reference", "Reference(" not in src)
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
