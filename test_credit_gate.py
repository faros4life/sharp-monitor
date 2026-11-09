#!/usr/bin/env python3
"""Tests for the shared OddsPapi credit gate. Stage 2 of Peter's staged deploy.

The headline test is CONCURRENCY, because that is the property he asked to see proved rather
than asserted. It is not a mock: it builds a real bare git repo, clones it twice as two
independent working copies standing in for two GitHub Actions runners, and has them race for a
budget deliberately too small for both. Then it checks the ledger that survived.

Run: python test_credit_gate.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

PASS, FAIL = [], []


def ck(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------- scaffolding
def build_repo():
    """A bare origin plus two clones: two runners that share a ref and nothing else."""
    root = tempfile.mkdtemp(prefix="gate-")
    origin = os.path.join(root, "origin.git")
    sh(root, "git", "init", "--bare", "-q", "-b", "main", origin)
    seed = os.path.join(root, "seed")
    sh(root, "git", "clone", "-q", origin, seed)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        sh(seed, "git", "config", k, v)
    os.makedirs(os.path.join(seed, "credits"), exist_ok=True)
    open(os.path.join(seed, "credits", ".keep"), "w").write("x")
    sh(seed, "git", "add", "-A")
    sh(seed, "git", "commit", "-qm", "seed")
    sh(seed, "git", "push", "-q", "origin", "HEAD:main")
    runners = []
    for n in ("a", "b"):
        p = os.path.join(root, f"runner-{n}")
        sh(root, "git", "clone", "-q", origin, p)
        for k, v in (("user.email", f"{n}@t"), ("user.name", n)):
            sh(p, "git", "config", k, v)
        runners.append(p)
    return root, runners


GATE = os.path.abspath("credit_gate.py")
LEDGER_REL = "credits/gate.json"

# A stub /account so no test ever touches the network or spends a credit. The gate reads usage
# through credits._pick, so the stub answers in the provider's real shape: counters under
# subscriptions[0] as request_count / request_limit.
STUB = '''
import sys, os, json, types
sys.path.insert(0, os.getcwd())   # -I implies -E, so PYTHONPATH is ignored
os.makedirs("credits", exist_ok=True)
m = types.ModuleType("credits")
m.account = lambda: {"subscriptions": [{"request_count": %(used)d, "request_limit": %(limit)d,
                                        "valid_from": "%(vf)s", "valid_until": "%(vu)s"}]}
def _pick(d, *names):
    def norm(x): return str(x).replace("_", "").lower()
    w = {norm(n) for n in names}
    subs = (d or {}).get("subscriptions")
    for sc in ((d or {}), (subs[0] if isinstance(subs, list) and subs else {})):
        for k, v in sc.items():
            if norm(k) in w and v is not None: return v
    return None
m._pick = _pick
m.period_key = lambda a, n: ("%(pk)s", "%(vf)s to %(vu)s", True)
sys.modules["credits"] = m
'''

WORKER = STUB + '''
import credit_gate as g
res = g.reserve(%(n)d, "%(purpose)s")
print(json.dumps({"got": bool(res), "shadow": bool(res and res.get("shadow")),
                  "token": (res or {}).get("token")}))
if res and not res.get("shadow"): g.confirm(res)
'''


def run_worker(cwd, n, purpose, used=0, limit=5000, enforce=True,
               vf="2026-11-03", vu="2026-12-03", pk="2026-11-03", extra_env=None):
    src = WORKER % {"used": used, "limit": limit, "vf": vf, "vu": vu, "pk": pk,
                    "n": n, "purpose": purpose}
    shutil.copy(GATE, os.path.join(cwd, "credit_gate.py"))
    shutil.copy("clv_ledger.py", os.path.join(cwd, "clv_ledger.py"))
    for dep in ("tracker_bits.py", "tb.py"):
        if os.path.exists(dep):
            shutil.copy(dep, os.path.join(cwd, dep))
    # AUTH_TTL=0 so each worker re-reads the stubbed /account. Without it a worker inherits the
    # previous one's cached authority figure and the test's own `used` value is ignored.
    env = dict(os.environ, ODDSPAPI_GATE="enforce" if enforce else "shadow",
               GATE_LEDGER=LEDGER_REL, GATE_AUTH_TTL_MIN="0", PYTHONPATH=cwd)
    env.update(extra_env or {})
    p = subprocess.run([sys.executable, "-I", "-c", src], cwd=cwd, env=env,
                       capture_output=True, text=True)
    out = [l for l in p.stdout.splitlines() if l.startswith("{")]
    return (json.loads(out[-1]) if out else {"got": None, "err": p.stderr[-400:]})


def ledger(cwd):
    """Read the ledger from the SHARED ref, which is the only version that matters."""
    sh(cwd, "git", "fetch", "-q", "origin", "main")
    p = sh(cwd, "git", "show", f"origin/main:{LEDGER_REL}")
    try:
        return json.loads(p.stdout)
    except Exception:
        return {}


# ---------------------------------------------------------------- 1. concurrency
def t_concurrency():
    print("\n1. CONCURRENCY - two real runners race for a budget too small for both")
    root, (a, b) = build_repo()
    # limit 5000, floor 500 -> usable 4500. Provider already used 4480, so room = 20.
    # Each runner asks for 15. Both can only succeed if they spend the same credits twice.
    with ThreadPoolExecutor(2) as ex:
        fa = ex.submit(run_worker, a, 15, "runner-a", used=4480)
        fb = ex.submit(run_worker, b, 15, "runner-b", used=4480)
        ra, rb = fa.result(), fb.result()
    won = [r for r in (ra, rb) if r.get("got")]
    ck("exactly one runner gets the credits", len(won) == 1,
       f"a={ra.get('got')} b={rb.get('got')}")
    L = ledger(a)
    total = sum(int(s.get("n", 0)) for s in L.get("spent") or []) \
        + sum(int(r.get("n", 0)) for r in L.get("reserved") or [])
    ck("the ledger never commits more than the room allowed", total <= 20, f"committed {total} of 20")
    ck("the loser is refused, not silently merged", len(L.get("refused") or []) >= 1,
       f"{len(L.get('refused') or [])} refusal(s) recorded")
    ck("both runners' work is on one ref", L.get("period") == "2026-11-03")
    shutil.rmtree(root, ignore_errors=True)


def t_stress():
    print("\n1b. CONCURRENCY STRESS - six runners, room for three")
    root = tempfile.mkdtemp(prefix="gate-s-")
    origin = os.path.join(root, "origin.git")
    sh(root, "git", "init", "--bare", "-q", "-b", "main", origin)
    seed = os.path.join(root, "seed")
    sh(root, "git", "clone", "-q", origin, seed)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        sh(seed, "git", "config", k, v)
    os.makedirs(os.path.join(seed, "credits"), exist_ok=True)
    open(os.path.join(seed, "credits", ".keep"), "w").write("x")
    sh(seed, "git", "add", "-A")
    sh(seed, "git", "commit", "-qm", "seed")
    sh(seed, "git", "push", "-q", "origin", "HEAD:main")
    runs = []
    for i in range(6):
        p = os.path.join(root, f"r{i}")
        sh(root, "git", "clone", "-q", origin, p)
        for k, v in (("user.email", f"r{i}@t"), ("user.name", f"r{i}")):
            sh(p, "git", "config", k, v)
        runs.append(p)
    # usable 4500; provider used 4450 -> room 50. Six runners each want 15: at most three fit.
    with ThreadPoolExecutor(6) as ex:
        res = [f.result() for f in [ex.submit(run_worker, p, 15, f"r{i}", 4450)
                                    for i, p in enumerate(runs)]]
    winners = sum(1 for r in res if r.get("got"))
    L = ledger(runs[0])
    total = sum(int(s.get("n", 0)) for s in L.get("spent") or []) \
        + sum(int(r.get("n", 0)) for r in L.get("reserved") or [])
    ck("no more than three of six runners win", winners <= 3, f"{winners} winners")
    ck("the committed total never exceeds the room", total <= 50, f"committed {total} of 50")
    ck("every winner is recorded on the shared ref", total == winners * 15,
       f"{winners} winners x15 = {winners * 15}, ledger says {total}")
    ck("the losers are refused rather than lost",
       len(L.get("refused") or []) >= 6 - winners,
       f"{len(L.get('refused') or [])} refusal(s) for {6 - winners} loser(s)")
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 2. the cap refuses
def t_cap():
    print("\n2. CAP REFUSAL - the 500-credit reserve is untouchable")
    root, (a, _) = build_repo()
    r = run_worker(a, 1, "at-the-floor", used=4500)       # usable exactly exhausted
    ck("a request at the floor is refused", not r.get("got"), f"got={r.get('got')}")
    r2 = run_worker(a, 400, "into-the-reserve", used=4200)  # 300 room, asks 400
    ck("a request that would dip into the reserve is refused", not r2.get("got"))
    r3 = run_worker(a, 200, "within-budget", used=4200)
    ck("a request inside the budget is granted", bool(r3.get("got")))
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 3. fail closed
def t_fail_closed():
    print("\n3. FAIL CLOSED - no authority means no spending")
    root, (a, _) = build_repo()
    shutil.copy(GATE, os.path.join(a, "credit_gate.py"))
    shutil.copy("clv_ledger.py", os.path.join(a, "clv_ledger.py"))
    env = dict(os.environ, ODDSPAPI_GATE="enforce", GATE_LEDGER=LEDGER_REL, PYTHONPATH=a)

    # provider outage: /account raises
    src = ('import sys, os, types, json\nsys.path.insert(0, os.getcwd())\n'
           'os.makedirs("credits", exist_ok=True)\nm = types.ModuleType("credits")\n'
           'def boom(): raise OSError("provider unreachable")\n'
           'm.account = boom\nm._pick = lambda d, *n: None\n'
           'm.period_key = lambda a, n: ("2026-11-03", "l", True)\n'
           'sys.modules["credits"] = m\n'
           'import credit_gate as g\nprint(json.dumps({"got": bool(g.reserve(1, "outage"))}))\n')
    p = subprocess.run([sys.executable, "-I", "-c", src], cwd=a, env=env,
                       capture_output=True, text=True)
    got = json.loads([l for l in p.stdout.splitlines() if l.startswith("{")][-1])["got"]
    ck("a provider outage refuses every paid call", not got)

    # an unreadable SHARED ledger. The working copy is not the authority any more - the gate reads
    # the blob out of origin/main - so the corruption has to be pushed to be meaningful.
    sh(a, "git", "fetch", "-q", "origin", "main")
    sh(a, "git", "reset", "-q", "--hard", "origin/main")   # earlier workers moved the ref
    os.makedirs(os.path.join(a, "credits"), exist_ok=True)
    open(os.path.join(a, LEDGER_REL), "w").write("{ this is not json")
    sh(a, "git", "add", "-f", LEDGER_REL)
    sh(a, "git", "commit", "-qm", "corrupt")
    sh(a, "git", "push", "-q", "origin", "HEAD:main")
    r = run_worker(a, 1, "corrupt-ledger")
    ck("an unreadable shared ledger refuses every paid call", not r.get("got"))

    # a MISSING ledger must still bootstrap, or enforcement deadlocks on its own absence
    sh(a, "git", "fetch", "-q", "origin", "main")
    sh(a, "git", "reset", "-q", "--hard", "origin/main")
    sh(a, "git", "rm", "-q", LEDGER_REL)
    sh(a, "git", "commit", "-qm", "remove")
    sh(a, "git", "push", "-q", "origin", "HEAD:main")
    r = run_worker(a, 1, "bootstrap", used=0)
    ck("a missing ledger bootstraps instead of deadlocking", bool(r.get("got")))
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 4. free endpoints
def t_free():
    print("\n4. FREE ENDPOINTS - never gated, even with the budget exhausted")
    sys.path.insert(0, os.getcwd())
    import credit_gate as g
    # ISOLATE FIRST. reserve() on a paid path records a refusal and PUSHES it, and an earlier
    # version of this test ran that in the live checkout - it put nine junk ledger commits on the
    # real repo's main, one per run. Detach the remote and the ledger path before calling anything
    # that can write. Every test that touches reserve() must do this or use a sandbox clone.
    g._fetch = lambda: False
    g.LEDGER = os.path.join(tempfile.mkdtemp(prefix="gate-free-"), "gate.json")
    # the gate is a leaf module (clv_ledger pulls executor and its credentials), so it carries its
    # own copy of the period rule. That copy must not drift from the one the ledger bills on.
    import clv_ledger as cl
    tops = [l.split()[1].split(".")[0] for l in open("credit_gate.py").read().splitlines()
            if (l.startswith("import ") or l.startswith("from ")) and len(l.split()) > 1]
    local = {f[:-3] for f in os.listdir(".") if f.endswith(".py")}
    ck("the gate imports no project module at module scope",
       not (set(tops) & local), f"top-level imports: {sorted(set(tops))}")
    days = [datetime(2026, m, d, 12, tzinfo=timezone.utc)
            for m in (1, 2, 3, 11, 12) for d in (1, 2, 3, 4, 15, 28)]
    ck("the gate's month_key matches clv_ledger.month_key on every boundary day",
       all(g.month_key(x) == cl.month_key(x) for x in days))
    ck("/account bypasses the gate", g.reserve(1, "x", path="/account").get("free") is True)
    ck("/historical-odds bypasses the gate",
       g.reserve(1, "x", path="/historical-odds").get("free") is True)
    ck("a paid path does NOT bypass", not (g.reserve(0, "x", path="/odds-by-tournaments") or {}).get("free"))
    ck("is_free agrees with the billing rule",
       g.is_free("/account?x=1") and g.is_free("/historical-odds/nba")
       and not g.is_free("/fixtures") and not g.is_free("/markets")
       and not g.is_free("/tournaments") and not g.is_free("/odds-by-tournaments"))


# ---------------------------------------------------------------- 5. no double count
def t_reconcile():
    print("\n5. RECONCILIATION - a call counted by the provider is not counted twice")
    sys.path.insert(0, os.getcwd())
    import credit_gate as g
    # These exercise the arithmetic, not the transport, so detach the shared ref and let the gate
    # read its working copy (base=None, the local-only path).
    g._fetch = lambda: False
    g.LEDGER = os.path.join(tempfile.mkdtemp(prefix="gate-logic-"), "gate.json")
    now = datetime.now(timezone.utc)
    # /account read at T. One spend before T (provider already has it), one after (it does not).
    d = {"period": "2026-11-03",
         "authority": {"used": 1000, "limit": 5000, "as_of": g._iso(now),
                       "period": "2026-11-03"},
         "spent": [{"token": "old", "n": 7, "at": g._iso(now - timedelta(minutes=5))},
                   {"token": "new", "n": 3, "at": g._iso(now + timedelta(seconds=30))}],
         "reserved": [{"token": "open", "n": 2, "at": g._iso(now),
                       "expires": g._iso(now + timedelta(minutes=9))}]}
    json.dump(d, open(g.LEDGER, "w"))
    d2, ok, _ = g._read(now)
    ck("the pre-authority spend is dropped (already inside provider_used)",
       [s["token"] for s in d2["spent"]] == ["new"])
    ck("used = provider + post-authority spends + open reservations",
       g.used(d2, now) == 1000 + 3 + 2, f"got {g.used(d2, now)}")
    ck("room subtracts the 500 reserve", g.room(d2, now) == 4500 - 1005,
       f"got {g.room(d2, now)}")

    # an expired reservation is reclaimed, not leaked forever
    d["reserved"] = [{"token": "dead", "n": 900, "at": g._iso(now - timedelta(hours=2)),
                      "expires": g._iso(now - timedelta(hours=1))}]
    json.dump(d, open(g.LEDGER, "w"))
    d3, _, _ = g._read(now)
    ck("a crashed run's reservation expires and is reclaimed", not d3["reserved"],
       "a crash leaks one reservation for TTL minutes, never the budget")

    # rollover opens a fresh budget on the provider's own boundary
    d["period"] = "2026-10-03"
    d["authority"]["period"] = "2026-12-03"
    d["spent"] = [{"token": "last", "n": 4000, "at": g._iso(now)}]
    json.dump(d, open(g.LEDGER, "w"))
    d4, ok4, _ = g._read(now)
    ck("period rollover opens a fresh budget", ok4 and not d4["spent"] and d4["period"] == "2026-12-03")
    os.remove(g.LEDGER)


# ---------------------------------------------------------------- 6. shadow mode
def t_shadow():
    print("\n6. SHADOW MODE - stage 3 observes, never blocks")
    root, (a, _) = build_repo()
    r = run_worker(a, 9999, "way-over-budget", used=4490, enforce=False)
    ck("shadow mode grants a token it would have refused", bool(r.get("got")) and r.get("shadow"))
    L = ledger(a)
    ck("shadow mode records the refusal it would have made", len(L.get("refused") or []) >= 1,
       (L.get("refused") or [{}])[-1].get("why", ""))
    ck("shadow mode records no spend", not (L.get("spent") or []),
       "a shadow token is never confirmed, so it cannot pollute the reconciliation")
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 7. idempotent confirm
def t_idempotent():
    print("\n7. RETRIES - confirming twice counts once")
    root, (a, _) = build_repo()
    shutil.copy(GATE, os.path.join(a, "credit_gate.py"))
    shutil.copy("clv_ledger.py", os.path.join(a, "clv_ledger.py"))
    src = (STUB % {"used": 100, "limit": 5000, "vf": "2026-11-03", "vu": "2026-12-03",
                   "pk": "2026-11-03"}) + '''
import credit_gate as g
r = g.reserve(5, "retried")
g.confirm(r); g.confirm(r); g.confirm(r)        # an HTTP retry loop calling confirm each pass
d, _, _ = g._read(g._now())
print(json.dumps({"spent": sum(int(s["n"]) for s in d.get("spent") or []),
                  "open": sum(int(x["n"]) for x in d.get("reserved") or [])}))
'''
    env = dict(os.environ, ODDSPAPI_GATE="enforce", GATE_LEDGER=LEDGER_REL, PYTHONPATH=a)
    p = subprocess.run([sys.executable, "-I", "-c", src], cwd=a, env=env,
                       capture_output=True, text=True)
    o = [l for l in p.stdout.splitlines() if l.startswith("{")]
    d = json.loads(o[-1]) if o else {"spent": -1, "open": -1}
    ck("three confirms of one token count 5, not 15", d["spent"] == 5, f"spent={d['spent']}")
    ck("confirm clears the reservation so it isn't double-held", d["open"] == 0)
    shutil.rmtree(root, ignore_errors=True)


def t_wiring():
    print("\n8. WIRING - the gate sits on the one paid chokepoint")
    sys.path.insert(0, os.getcwd())
    import credit_gate as g
    import clv_ledger as cl

    calls = []
    real_take, real_api = g.take, cl._api
    cl._api = lambda path, b, k, p: calls.append(path) or {"stub": True}
    try:
        # a refusal must stop the request before it is made
        g.take = lambda n=1, purpose="api", path=None: False
        try:
            cl.api("/odds-by-tournaments", True, tournamentIds="1")
            ck("a refused paid call raises instead of spending", False, "no exception raised")
        except cl.GateRefused:
            ck("a refused paid call raises instead of spending", True)
        ck("a refused paid call never reaches the network", not calls, f"calls={calls}")

        # free endpoints must not be gated even when the gate refuses everything
        calls.clear()
        cl.api("/account", False)
        ck("/account is not gated", calls == ["/account"], f"calls={calls}")

        # and a grant lets the call through
        calls.clear()
        g.take = lambda n=1, purpose="api", path=None: True
        cl.api("/fixtures", True)
        ck("a granted paid call proceeds", calls == ["/fixtures"], f"calls={calls}")

        # ENFORCEMENT MUST BE THE DEFAULT. Setting it per workflow would make one missed env block
        # a silent hole in the cap, so an unset ODDSPAPI_GATE has to mean "on".
        p = subprocess.run([sys.executable, "-c",
                            "import credit_gate as g; print(g.MODE, g.ENFORCE)"],
                           cwd=os.getcwd(), capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if k != "ODDSPAPI_GATE"})
        ck("the gate enforces by default, with no env var set",
           p.stdout.strip() == "enforce True", p.stdout.strip() or p.stderr[-200:])

        # A refusal must not abort a job's FREE work. The seven contents: read research jobs cannot
        # reserve under enforcement, so every paid call is refused - by design - and they still have
        # free historical research to finish.
        g.take = lambda n=1, purpose="api", path=None: False
        st = {"billable": {}}
        now = datetime.now(timezone.utc)
        try:
            got = cl.refresh_fixtures(st, now, "NBA", now, now)
            ck("a refused /fixtures degrades instead of raising", got is False, f"returned {got}")
        except cl.GateRefused:
            ck("a refused /fixtures degrades instead of raising", False, "it raised")
        try:
            m = cl.load_markets({"billable": {}}, now)
            ck("a refused /markets falls back to the cached list", isinstance(m, dict))
        except cl.GateRefused:
            ck("a refused /markets falls back to the cached list", False, "it raised")

        # every paid endpoint we actually use is covered by the one chokepoint
        src = open("clv_ledger.py").read()
        ck("the gate is checked in api(), before the request is built",
           "cg.take(1, purpose=path.lstrip" in src and src.index("cg.take") < src.index("def _api"))
    finally:
        g.take, cl._api = real_take, real_api


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("CREDIT GATE TESTS - no network, no credits spent (/account is stubbed throughout)")
    for t in (t_concurrency, t_stress, t_cap, t_fail_closed, t_free, t_reconcile, t_shadow, t_idempotent, t_wiring):
        try:
            t()
        except Exception as e:
            FAIL.append(t.__name__)
            print(f"  FAIL  {t.__name__} raised {type(e).__name__}: {e}")
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    sys.exit(1 if FAIL else 0)
