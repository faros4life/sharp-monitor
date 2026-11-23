#!/usr/bin/env python3
"""Offline review of the single-shot CAS registry writer. Never contacts GitHub or venues."""
import base64
import json
import registry

checks = []
old_call, old_enabled = registry._call, registry.enabled
calls = []
status = [200]
try:
    registry.enabled = lambda: True
    def fake_call(method, url, body=None, timeout=20):
        calls.append((method, url, body))
        return status[0], {}
    registry._call = fake_call
    sample = {"orders": [{"id": "existing"}], "unit_reservations": {"legs": [{"id": "x"}]}}
    checks.append(("successful conditional PUT", registry._put_with_sha(sample, "sha-1") is True))
    checks.append(("one and only one PUT", len(calls) == 1 and calls[-1][0] == "PUT"))
    checks.append(("SHA carried unchanged", calls[-1][2]["sha"] == "sha-1"))
    checks.append(("unrelated registry data preserved", json.loads(base64.b64decode(calls[-1][2]["content"])) == sample))
    calls.clear()
    status[0] = 409
    checks.append(("lost CAS returns False", registry._put_with_sha(sample, "stale") is False))
    checks.append(("lost CAS does NOT retry", len(calls) == 1))
    calls.clear()
    status[0] = 422
    checks.append(("validation conflict returns False", registry._put_with_sha(sample, "bad-sha") is False))
    checks.append(("validation conflict does NOT retry", len(calls) == 1))
    calls.clear()
    checks.append(("missing SHA refuses with zero PUTs", registry._put_with_sha(sample, None) is False and len(calls) == 0))
    checks.append(("invalid payload refuses with zero PUTs", registry._put_with_sha([], "sha-1") is False and len(calls) == 0))
    registry.enabled = lambda: False
    checks.append(("missing credentials refuse with zero PUTs", registry._put_with_sha(sample, "sha-1") is False and len(calls) == 0))
    registry.enabled = lambda: True
    registry._call = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("offline read/write failure"))
    checks.append(("network exception refuses", registry._put_with_sha(sample, "sha-1") is False))
finally:
    registry._call, registry.enabled = old_call, old_enabled

for name, good in checks:
    print(("PASS " if good else "FAIL ") + name)
print(f"{sum(good for _, good in checks)} passed, {sum(not good for _, good in checks)} failed")
if not all(good for _, good in checks):
    raise SystemExit(1)
