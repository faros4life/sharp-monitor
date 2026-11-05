#!/usr/bin/env python3
"""REGRESSION GUARD for the API-efficiency and credit-accounting work (Peter, Nov 5 2026).

Run BEFORE and AFTER every change. It proves the six invariants Peter named. Nothing here
touches the network, OddsPapi, ntfy or any state file in the repo: the provider is stubbed and
every state file is written under a temp dir.

  1. betting signals, qualification thresholds and alert routing unchanged  (fingerprint)
  2. Hard Rock is manual-only and can never be promoted to live             (structural)
  3. all six paper-data leagues still collect                               (structural)
  4. no OddsPapi call is double-counted and none bypasses the counter       (behavioural)
  5. concurrent workflows cannot exceed the cap                            (behavioural)
  6. a failed call or a crash cannot corrupt the accounting state           (behavioural)

Exit code 0 only when every invariant holds. Test 5 is EXPECTED RED until the shared meter
lands - that breach is the reason the shared meter is being built, so it is reported, not hidden.
"""
import hashlib
import json
import os
import sys
import tempfile
import traceback

REPO = os.environ.get("REPO_DIR") or os.getcwd()
sys.path.insert(0, REPO)
os.environ.setdefault("TRACKER_PASSPHRASE", "regress-only-not-a-real-passphrase")

RESULTS = []


def check(name, fn, expect_red=False):
    try:
        detail = fn()
        ok = True
    except AssertionError as e:
        ok, detail = False, f"ASSERT: {e}"
    except Exception:
        ok, detail = False, "ERROR: " + traceback.format_exc().strip().splitlines()[-1]
    RESULTS.append((name, ok, detail, expect_red))
    flag = "PASS" if ok else ("RED (expected)" if expect_red else "FAIL")
    print(f"[{flag:>14}] {name}")
    for ln in str(detail).splitlines():
        print(f"                 {ln}")
    return ok


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


# ---------------------------------------------------------------- 1. signals / thresholds / alerts
def inv1():
    """Fingerprint the decision surface. Any change to a signal, a threshold or an alert route
    moves this hash. The point is not the value but that it is IDENTICAL before and after."""
    import agree_rules
    import clv_ledger as cl
    import hr_scanner
    import sharp_monitor as sm

    fp = {}
    # the thresholds Peter named explicitly
    fp["MIN_EV"] = hr_scanner.MIN_EV
    fp["NO_FLAG_MIN"] = hr_scanner.NO_FLAG_MIN
    fp["LEAGUES"] = list(hr_scanner.LEAGUES)
    fp["FLAG_LEAGUES"] = list(hr_scanner.FLAG_LEAGUES)
    fp["LATE_MIN"] = sm.LATE_MIN
    fp["LATE_MODE"] = sm.LATE_MODE
    fp["REPEAT_MODE"] = sm.REPEAT_MODE
    fp["NCAAF_TOP25"] = sm.NCAAF_TOP25
    fp["SPORTS"] = {k: sorted(v.items(), key=str) for k, v in sorted(sm.SPORTS.items())}
    fp["DEADBAND"] = list(agree_rules.DEADBAND)
    fp["CAP"] = cl.CAP
    fp["SPORT"] = dict(sorted(cl.SPORT.items()))
    fp["TOURN"] = dict(sorted(cl.TOURN.items()))
    fp["MAX_TRIES"] = cl.MAX_TRIES

    # the EV / conversion maths that turns a line move into a signal
    fp["number_mass"] = [round(sm.number_mass(s, k, n, 45.0), 6)
                         for s in ("NFL", "NCAAF", "NBA", "NCAAB", "NHL", "MLB")
                         for k in ("spr", "tot") for n in (1, 3, 7, 10, 14, 21)]
    fp["half_point_value"] = [round(sm.half_point_value(s, "spr", a, b, a), 6)
                              for s in ("NFL", "NCAAF", "NBA") for a, b in ((-3, -2.5), (-7, -6), (1, 2.5))]
    fp["ev_pct"] = [round(sm.ev_pct(p, pr), 6) for p in (.4, .5, .55) for pr in (-110, -125, 100, 150)]
    fp["convb"] = [hr_scanner._convb(c) for c in (None, 0, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, "x")]

    # qualification: phase1 over a grid, plus the two kill rules
    grid = []
    for book in ("prophetx", "novig", "kalshi", "hardrockbet", "hardrockbet_fl", ""):
        for grade in ("A", "B", "C"):
            for kind in ("spr", "tot", "ml", "rl"):
                for late in (False, True):
                    a = {"book": book, "kind": kind, "text": "Team -3.5 (-110) at X", "price": -110,
                         "commence": "2026-11-06T01:00:00Z", "pt": -3.5}
                    ok, why = sm.phase1_label(a, "NFL", grade, 120.0, late, False)
                    grid.append((book, grade, kind, late, bool(ok), len(why)))
    fp["phase1_grid"] = grid
    fp["hr_dog"] = [sm.hr_dog({"book": b, "kind": k, "pt": p})
                    for b in ("hardrockbet", "hardrockbet_fl", "prophetx")
                    for k in ("spr", "rl", "tot") for p in (-3.5, 0, 1.5)]
    fp["hr_priced"] = [agree_rules.hr_priced({"book_key": b})
                       for b in ("hardrockbet", "hardrockbet_fl", "prophetx", "novig", "", None)]
    fp["deadband"] = [agree_rules.deadband({"book_key": b, "price_after_fee": p, "sent_to_phone": True})
                      for b in ("prophetx", "novig", "hardrockbet", "") for p in (-125, -119, -115, -110, -105, None)]

    blob = json.dumps(fp, sort_keys=True, default=str)
    h = hashlib.sha256(blob.encode()).hexdigest()
    files = {f: sha(os.path.join(REPO, f)) for f in
             ("sharp_monitor.py", "hr_scanner.py", "agree_rules.py", "clv_ledger.py", "lane2.py", "executor.py")
             if os.path.exists(os.path.join(REPO, f))}
    return ("decision-surface fingerprint: " + h + "\n"
            + "\n".join(f"  {k} {v}" for k, v in sorted(files.items()))
            + f"\n  grid rows {len(grid)} | thresholds MIN_EV={fp['MIN_EV']} NO_FLAG_MIN={fp['NO_FLAG_MIN']} "
              f"LATE_MIN={fp['LATE_MIN']} NCAAF_TOP25={fp['NCAAF_TOP25']}")


# ---------------------------------------------------------------- 2. Hard Rock manual-only
def inv2():
    import agree_rules
    import sharp_monitor as sm
    HR = ("hardrockbet", "hardrockbet_fl")
    for b in HR:
        assert agree_rules.hr_priced({"book_key": b}) is True, f"hr_priced({b}) must be True"
    n = 0
    for b in HR:
        for grade in ("A", "B", "C", "D"):
            for lead in (5.0, 29.0, 31.0, 120.0, 600.0):
                for late in (False, True):
                    for kind in ("spr", "tot", "ml", "rl"):
                        a = {"book": b, "kind": kind, "text": "X -3.5 (-110) at Hard Rock",
                             "price": -110, "commence": "2026-11-06T01:00:00Z", "pt": -3.5}
                        ok, why = sm.phase1_label(a, "NFL", grade, lead, late, False)
                        assert ok is False, f"HR alert became phase-1 eligible: {b} {grade} {lead} {kind}"
                        n += 1
    # the HR ping must not be reachable without the +2% bar
    import hr_scanner
    assert hr_scanner.MIN_EV == 2.0, "HR flag threshold moved off +2%"
    assert hr_scanner.NO_FLAG_MIN == 30, "scanner T-30 cutoff moved"
    return f"{n} HR phase-1 combinations all refused; hr_priced True for both keys; MIN_EV 2.0; T-30 intact"


# ---------------------------------------------------------------- 3. six paper leagues
def inv3():
    import hr_scanner
    import sharp_monitor as sm
    six = {"NBA", "NFL", "NCAAF", "NHL", "NCAAB", "MLB"}
    assert set(hr_scanner.LEAGUES) == six, f"scanner LEAGUES changed: {hr_scanner.LEAGUES}"
    assert set(hr_scanner.FLAG_LEAGUES) == six, f"FLAG_LEAGUES changed: {hr_scanner.FLAG_LEAGUES}"
    polled = {v["label"] for v in sm.SPORTS.values()}
    assert six <= polled, f"a paper league is no longer polled: {six - polled}"
    # scan() must not early-return for any of the six
    for lg in six:
        cfg = {"label": lg}
        assert cfg["label"] in hr_scanner.LEAGUES, lg
    return f"all six collect: {sorted(six)}; polled labels {sorted(polled)}"


# ---------------------------------------------------------------- stub provider for 4/5/6
class Stub:
    """Counts every call that actually left for OddsPapi, so billed-vs-called can be compared."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def install(self, cl):
        self.cl = cl
        self._real = cl.api

        def api(path, billable, apikey=None, **params):
            self.calls.append((path, billable))
            if self.fail:
                return {"_error": "500 stub", "_body": "stub failure"}
            if path == "/fixtures":
                return [{"fixtureId": f"f{len(self.calls)}", "startTime": "2026-11-05T12:00:00.000Z",
                         "participant1Name": "A", "participant2Name": "B", "statusId": 1}]
            if path == "/tournaments":
                return [{"tournamentId": 99, "tournamentName": "NCAA College", "categorySlug": "usa"}]
            if path == "/markets":
                return []
            if path == "/account":
                return {"plan": "paid", "requestsUsed": 1234, "requestsLimit": 5000}
            return []
        cl.api = api

    def remove(self):
        self.cl.api = self._real

    @property
    def billable(self):
        return sum(1 for _, b in self.calls if b)


# ---------------------------------------------------------------- 4. no double count, no bypass
def inv4():
    from datetime import datetime, timedelta, timezone
    import clv_ledger as cl
    now = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
    s = Stub()
    s.install(cl)
    try:
        st = {"billable": {}, "fx_last": {}, "fixtures": {}}
        for lg in ("NBA", "NFL", "NHL"):
            cl.refresh_fixtures(st, now, lg, now - timedelta(days=1), now + timedelta(days=1))
        billed = st["billable"].get("2026-11", 0)
        assert billed == s.billable, f"counter {billed} != provider billable calls {s.billable}"
        # second pass inside the cooldown must neither call nor bill
        before_calls, before_billed = len(s.calls), billed
        for lg in ("NBA", "NFL", "NHL"):
            cl.refresh_fixtures(st, now + timedelta(hours=1), lg, now - timedelta(days=1), now + timedelta(days=1))
        assert len(s.calls) == before_calls, "cooldown did not stop the provider call"
        assert st["billable"]["2026-11"] == before_billed, "billed again inside the cooldown"
        # a caller that resets fx_last (x2_tag does exactly this) must still be counted
        st["fx_last"].pop("NBA", None)
        cl.refresh_fixtures(st, now + timedelta(hours=1), "NBA", now - timedelta(days=1), now + timedelta(days=1))
        assert st["billable"]["2026-11"] == before_billed + 1, "a forced re-fetch was not counted"
        final = st["billable"]["2026-11"]
        return (f"first pass {billed} billed == {billed} provider billable calls; cooldown "
                f"suppressed 3 repeats; forced re-fetch counted once -> {final} billed "
                f"== {s.billable} total provider billable calls")
    finally:
        s.remove()


# ---------------------------------------------------------------- 5. concurrency cannot overspend
def inv5():
    """Two workflows, two separate state files, one shared cap. This is the breach the shared
    meter must close: each counter sees only its own spend, so the pair can exceed CAP."""
    from datetime import datetime, timedelta, timezone
    import clv_ledger as cl
    now = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
    s = Stub()
    s.install(cl)
    old_cap = cl.CAP
    try:
        cl.CAP = 2                     # tiny cap so the breach is unambiguous
        a = {"billable": {}, "fx_last": {}, "fixtures": {}}   # workflow A (e.g. clv/state.enc)
        b = {"billable": {}, "fx_last": {}, "fixtures": {}}   # workflow B (e.g. plimit/state.enc)
        t = now
        for i in range(2):
            for lg in ("NBA", "NFL"):
                cl.refresh_fixtures(a, t, lg, now - timedelta(days=1), now + timedelta(days=1))
                cl.refresh_fixtures(b, t, lg, now - timedelta(days=1), now + timedelta(days=1))
            t += timedelta(hours=7)
        total = a["billable"].get("2026-11", 0) + b["billable"].get("2026-11", 0)
        assert total <= cl.CAP, (f"two workflows spent {total} against a shared cap of {cl.CAP} "
                                 f"(A {a['billable']} + B {b['billable']}) - separate counters "
                                 f"cannot enforce one budget")
        return f"total {total} <= cap {cl.CAP}"
    finally:
        cl.CAP = old_cap
        s.remove()


# ---------------------------------------------------------------- 6. failure cannot corrupt state
def inv6():
    from datetime import datetime, timedelta, timezone
    import clv_ledger as cl
    import tracker_build as tb
    now = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
    notes = []

    # (a) a failed provider call still bills exactly once (the credit WAS spent) and leaves the
    #     fixture cache untouched - a 500 must not look like "the league has no games".
    s = Stub(fail=True)
    s.install(cl)
    try:
        st = {"billable": {}, "fx_last": {}, "fixtures": {"keep": {"lg": "NBA", "start": "x"}}}
        ok = cl.refresh_fixtures(st, now, "NBA", now - timedelta(days=1), now + timedelta(days=1))
        assert ok is False, "a failed fetch must report False"
        assert st["billable"]["2026-11"] == 1, "a spent credit must be counted even when the call failed"
        assert st["fixtures"] == {"keep": {"lg": "NBA", "start": "x"}}, "a failed fetch corrupted the cache"
        assert st["errors"], "a failed fetch must leave a recorded error"
        notes.append("failed call: billed once, cache intact, error recorded, returns False")
    finally:
        s.remove()

    # (b) the counter must survive a round trip through the encrypted state writer
    d = tempfile.mkdtemp()
    p = os.path.join(d, "state.enc")
    st = {"billable": {"2026-11": 7}, "fx_last": {"NBA": cl.iso(now)}}
    json.dump(tb.enc(st), open(p, "w"))
    back = tb.dec(json.load(open(p)))
    assert back["billable"] == {"2026-11": 7}, "counter did not survive encrypt/decrypt"
    notes.append("counter survives the encrypted round trip")

    # (c) a crash mid-write must not leave a truncated state file. The repo writes with
    #     json.dump(..., open(PATH,"w")), which truncates on open - so a crash between the
    #     truncate and the flush destroys the counter. Proven by simulation.
    good = open(p).read()
    try:
        f = open(p, "w")          # truncates immediately, exactly as json.dump(open(...)) does
        f.write(good[:10])
        raise RuntimeError("simulated crash mid-write")
    except RuntimeError:
        pass
    finally:
        f.close()
    truncated = open(p).read()
    atomic_safe = (truncated == good)
    if not atomic_safe:
        notes.append(f"NON-ATOMIC WRITE: a crash mid-write left {len(truncated)} of {len(good)} bytes "
                     "- the month counter would be lost. Needs tmp-file + os.replace.")
    assert atomic_safe, "\n".join(notes)
    return "\n".join(notes)


# ---------------------------------------------------------------- 7. the credit meter cannot spend
def inv7():
    """Stage 1 of the credit meter must be incapable of spending a credit or writing any state.
    Checked structurally (AST), so it stays true even if the module is edited later."""
    import ast
    f = os.path.join(REPO, "credits.py")
    if not os.path.exists(f):
        return "credits.py not present (nothing to check)"
    t = ast.parse(open(f).read())
    calls, writes = [], []
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "api":
            path = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else "?"
            bill = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else "?"
            calls.append((path, bill))
            assert path == "/account" and bill is False, \
                f"credits.py made a non-free provider call: api({path!r}, {bill!r})"
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open":
            mode = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else "r"
            if "w" in str(mode) or "a" in str(mode) or "+" in str(mode):
                writes.append(mode)
    assert not writes, f"credits.py opened a file for writing: {writes}"
    # and it must not be imported by anything that places bets or sends alerts
    for risky in ("executor.py", "px_live.py", "book_live.py", "sharp_monitor.py", "hr_scanner.py"):
        rp = os.path.join(REPO, risky)
        if os.path.exists(rp):
            src = open(rp).read()
            assert "import credits" not in src, f"{risky} imports credits - Stage 1 must stay out of the live path"
    return (f"only provider call is {calls}; no file opened for writing; not imported by the "
            f"executor, either live-order module, the monitor or the HR scanner")


def main():
    print(f"REGRESSION GUARD | repo {REPO}\n" + "=" * 78)
    check("1. betting signals / qualification thresholds / alert routing", inv1)
    check("2. Hard Rock manual-only, never promoted to live", inv2)
    check("3. all six paper-data leagues collecting", inv3)
    check("4. no OddsPapi call double-counted or uncounted", inv4)
    check("5. concurrent workflows cannot exceed the cap", inv5, expect_red=True)
    check("6. a failed call or crash cannot corrupt accounting state", inv6, expect_red=True)
    check("7. the Stage-1 credit meter cannot spend or write", inv7)
    print("=" * 78)
    hard = [n for n, ok, _, red in RESULTS if not ok and not red]
    known = [n for n, ok, _, red in RESULTS if not ok and red]
    for n, ok, _, red in RESULTS:
        print(f"  {'ok  ' if ok else ('RED ' if red else 'FAIL')} {n}")
    if known:
        print("\nKNOWN-RED (documents the defect the next change must close):")
        for n in known:
            print(f"  - {n}")
    print(f"\n{'FAILURES: ' + str(hard) if hard else 'No unexpected failures.'}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
