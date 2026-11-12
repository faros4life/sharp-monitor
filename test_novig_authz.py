#!/usr/bin/env python3
"""Novig order authorization cannot be reached by any path (Peter, Nov 12). OFFLINE. NO ORDERS.

The audit found that NOVIG_SNAPSHOT_TOKEN - documented twice in executor-dry-run.yml as
"read-only" - actually reports {admin, maintain, push, triage, pull} on the runner repo, and sat in
ten workflows of a public repo, nine of which only read one snapshot file. Each therefore carried a
live-order dispatch capability. novig-dispatch-check.yml made that concrete by POSTing runner
inputs itself, skipping novig_place() and every check inside it.

This proves the close, in-process, without any network call: read and dispatch credentials are
separate, dispatch has no fallback to the read credential, novig_place() fails closed when the
narrow credential is absent, and no workflow or module reaches the runner except through
novig_place(). The urlopen used by the real dispatch is replaced with a tripwire that FAILS the
test if it is ever reached, so a regression cannot pass quietly.
"""
import glob
import inspect
import os
import re
import sys
import urllib.request

import book_live as b

OK, BAD = [], []


def ck(name, got, want):
    (OK if got == want else BAD).append(name)
    print(("  ok   " if got == want else "  FAIL ") + f"{name}: got {got!r} want {want!r}")


# Any real HTTP from here is itself the defect.
REACHED = []
urllib.request.urlopen = lambda *a, **k: (REACHED.append(getattr(a[0], "full_url", a[0])),
                                          (_ for _ in ()).throw(AssertionError("network reached")))[1]

print("1. the two credentials are separate, and dispatch has NO fallback")
print("=" * 78)
for k in ("NOVIG_READ_TOKEN", "NOVIG_SNAPSHOT_TOKEN", "NOVIG_DISPATCH_TOKEN"):
    os.environ.pop(k, None)
os.environ["NOVIG_SNAPSHOT_TOKEN"] = "broad-token"
ck("read falls back to the broad token during migration", b._read_token(), "broad-token")
ck("the broad token is NOT a dispatch credential", b._dispatch_token(), "")
os.environ["NOVIG_READ_TOKEN"] = "narrow-read"
ck("the narrow read token is preferred once present", b._read_token(), "narrow-read")
ck("a read token is still never a dispatch credential", b._dispatch_token(), "")
os.environ["NOVIG_DISPATCH_TOKEN"] = "narrow-dispatch"
ck("the dispatch credential is its own secret", b._dispatch_token(), "narrow-dispatch")
ck("reads do not silently use the dispatch credential", b._read_token(), "narrow-read")
src = inspect.getsource(b._dispatch_token)
ck("_dispatch_token names no other secret", "SNAPSHOT" not in src and "READ_TOKEN" not in src, True)

print()
print("2. novig_place() fails closed, and reaches no network while it does")
print("=" * 78)
os.environ.pop("NOVIG_DISPATCH_TOKEN", None)
b.NOVIG_SUBMIT = True          # lift ONLY the submit hold, to test the layer underneath it
# preflight() reads live positions and the STOP switch, so offline it refuses first and would hide
# the credential check behind it. Stubbed to PASS so the dispatch-credential layer is the one
# actually exercised here - the point is that it refuses even when everything above it agrees.
_real_preflight = b.preflight
b.preflight = lambda book, risk: (True, "")
REACHED.clear()
res = b.novig_place("00000000-0000-0000-0000-000000000000", 0.54, 100, "test", None, "TEST")
ck("refused with no dispatch credential", res.get("status"), "refused")
ck("the reason names the narrow credential", "NOVIG_DISPATCH_TOKEN" in str(res.get("reason")), True)
ck("nothing was sent to the runner", bool(res.get("sent_to_runner")), False)
ck("no network was reached", REACHED, [])

b.preflight = _real_preflight
b.NOVIG_SUBMIT = False         # the normal state: the submit hold refuses first
REACHED.clear()
res = b.novig_place("00000000-0000-0000-0000-000000000000", 0.54, 100, "test", None, "TEST")
ck("refused by the submit hold when off", res.get("status"), "refused")
ck("the hold is the stated reason", "EXEC_NOVIG_SUBMIT" in str(res.get("reason")), True)
ck("still no network", REACHED, [])
ck("no order id on a refusal", res.get("order_id"), None)

print()
print("3. the submit hold is the FIRST branch, so nothing runs ahead of it")
print("=" * 78)
psrc = inspect.getsource(b.novig_place)
body = psrc.split('"""', 2)[-1]
i_hold, i_pre = body.find("if not NOVIG_SUBMIT"), body.find("preflight(")
i_disp = body.find("_dispatch_token()")
i_post = body.find("_gh(")
ck("the hold precedes preflight", 0 <= i_hold < i_pre, True)
ck("the hold precedes the dispatch-credential check", 0 <= i_hold < i_disp, True)
ck("every check precedes the POST", max(i_hold, i_pre, i_disp) < i_post, True)

print()
print("4. NO path reaches the runner except through novig_place()")
print("=" * 78)
pat = re.compile(r"actions/workflows/[^\s\"']*/dispatches|NV_WORKFLOW")
offenders = []
for f in sorted(glob.glob("*.py") + glob.glob(".github/workflows/*.yml")):
    if f.endswith("book_live.py") or f.endswith("test_novig_authz.py"):
        continue
    t = open(f).read()
    if pat.search(t) and "novig_place" not in t:
        offenders.append(f)
ck("no module or workflow builds its own runner dispatch", offenders, [])
chk = open(".github/workflows/novig-dispatch-check.yml").read()
ck("the dispatch-check goes through novig_place", "novig_place(" in chk, True)
ck("the dispatch-check no longer POSTs a dispatch itself", "/dispatches" in chk, False)
ck("the dispatch-check pins the submit hold off", 'EXEC_NOVIG_SUBMIT: "off"' in chk, True)
ck("the dispatch-check binds no dispatch credential in env",
   bool(re.search(r"^\s*NOVIG_DISPATCH_TOKEN:", chk, re.M)), False)
ck("the dispatch-check asserts the refusal", 'status") == "refused"' in chk, True)

print()
print("5. the credential migration is staged everywhere the broad token appears")
print("=" * 78)
missing = [f.split("/")[-1] for f in sorted(glob.glob(".github/workflows/*.yml"))
           if "NOVIG_SNAPSHOT_TOKEN:" in open(f).read() and "NOVIG_READ_TOKEN:" not in open(f).read()]
ck("every workflow holding the broad token also offers the narrow one", missing, [])
disp = [f.split("/")[-1] for f in sorted(glob.glob(".github/workflows/*.yml"))
        if re.search(r"^\s*NOVIG_DISPATCH_TOKEN:", open(f).read(), re.M)]
ck("no workflow yet carries a dispatch credential", disp, [])

print()
print("=" * 78)
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for x in BAD:
    print("  FAILED: " + x)
sys.exit(1 if BAD else 0)
