#!/usr/bin/env python3
"""THE TEST RUNNER (Nov 12, 2026). Runs every test file and EXITS NON-ZERO if any of them fails.

Written because the ad-hoc shell loop used until now hid a failing file: `for t in ...; do python3 $t; done` reports the
exit status of the LAST command only, so a red file in the middle of the list passed unnoticed (it did, once).

Each test file in this repo is a script that exits 1 on failure, so the runner's rule is simply: any non-zero exit, any
timeout, or any crash is a FAILURE, and the runner's own exit code is 1 if a single file failed. No allowlist and no
"known failures" bucket - a red file is red.

Usage:
    python3 run_tests.py                 # every test file
    python3 run_tests.py line_value      # only files whose name contains this substring
    python3 run_tests.py --list          # list what would run
Env: TEST_TIMEOUT (seconds per file, default 300).
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = int(os.environ.get("TEST_TIMEOUT") or 300)
COUNT = re.compile(r"(\d+)\s*(?:passed|pass)\D+(\d+)\s*(?:failed|fail)|PASS\s+(\d+)\s+FAIL\s+(\d+)")


def files(pat=None):
    out = []
    for d in (os.path.join(ROOT, "tests"), ROOT):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.startswith("test_") and f.endswith(".py") and (pat is None or pat in f):
                p = os.path.join(d, f)
                if p not in out:
                    out.append(p)
    return out


def counts(text):
    """(passed, failed) as the file itself reported them, or (None, None)."""
    for m in COUNT.finditer(text or ""):
        g = [x for x in m.groups() if x is not None]
        if len(g) == 2:
            return int(g[0]), int(g[1])
    return None, None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fs = files(args[0] if args else None)
    if "--list" in sys.argv:
        print("\n".join(os.path.relpath(f, ROOT) for f in fs))
        return 0
    if not fs:
        print("run_tests: no test files matched - treating that as a FAILURE (a silent empty run is how a suite dies)")
        return 1
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    failed, assertions = [], [0, 0]
    print(f"run_tests: {len(fs)} file(s), {TIMEOUT}s each\n")
    t0 = time.time()
    for f in fs:
        rel = os.path.relpath(f, ROOT)
        s = time.time()
        try:
            r = subprocess.run([sys.executable, f], cwd=ROOT, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            out, rc = (r.stdout or "") + (r.stderr or ""), r.returncode
        except subprocess.TimeoutExpired:
            out, rc = f"TIMEOUT after {TIMEOUT}s", 124
        except Exception as ex:
            out, rc = f"RUNNER ERROR: {type(ex).__name__}: {ex}", 125
        p, fl = counts(out)
        if p is not None:
            assertions[0] += p
            assertions[1] += fl
        tag = "ok  " if rc == 0 else "FAIL"
        print(f"  {tag} {rel:<44} rc={rc:<4} {('' if p is None else f'{p} passed, {fl} failed')}  {time.time() - s:.1f}s")
        if rc != 0:
            failed.append((rel, rc, out.strip().splitlines()[-12:]))
    print(f"\nfiles: {len(fs) - len(failed)} ok, {len(failed)} FAILED   "
          f"assertions: {assertions[0]} passed, {assertions[1]} failed   ({time.time() - t0:.0f}s)")
    for rel, rc, tail in failed:
        print(f"\n--- {rel} (rc={rc})")
        for line in tail:
            print(f"    {line}")
    if failed:
        print(f"\nrun_tests: FAILING - {len(failed)} file(s): " + ", ".join(r for r, _, _ in failed))
        return 1
    print("run_tests: all files passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
