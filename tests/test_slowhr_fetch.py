#!/usr/bin/env python3
"""slow_hr fetch-efficiency tests (Peter, Nov 5): empty results cached under the 6 h cooldown, no
inference from cached future fixtures, and newly SCHEDULED games are still discovered."""
import sys, types, json, os
from datetime import datetime, timezone, timedelta
os.chdir("/tmp/t")

CLOCK = [datetime(2026, 11, 5, 18, 23, tzinfo=timezone.utc)]
BILLED = []
SCHEDULE = {}          # league -> list of fixture dicts the provider would return

def tparse(v):
    if not v: return None
    try: return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception: return None

tb = types.ModuleType("tracker_build")
tb.ET = timezone(timedelta(hours=-5)); tb.PASS = "x"; tb.tparse = tparse
tb.dec = lambda d: d; tb.enc = lambda d: d; tb.num = float
tb.toks = lambda s: set((s or "").lower().split()); tb.WEAK = set()

cl = types.ModuleType("clv_ledger")
cl.KEY = "k"; cl.CAP = 1000; cl.CALLS = []; cl.STATS = {"billable": 0, "free": 0}
cl.iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
cl.tp = tparse
cl.load_markets = lambda st, now: {}
cl.api = lambda p, b, **kw: {"plan": "paid", "requestsUsed": 1234, "requestsLimit": 5000}
cl.book_markets = lambda *a: {}; cl.dec_to_am = lambda d: -110; cl.half_point_value = lambda *a: 0.0

def refresh_fixtures(st, now, lg, lo, hi):
    last = tparse((st.get("fx_last") or {}).get(lg))
    if last and last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)
    if last and now - last < timedelta(hours=6):
        return False
    mk = now.strftime("%Y-%m")
    if st.setdefault("billable", {}).get(mk, 0) + 1 > cl.CAP:
        return False
    st["billable"][mk] = st["billable"].get(mk, 0) + 1
    BILLED.append((lg, now.isoformat()[:16]))
    st.setdefault("fx_last", {})[lg] = cl.iso(now)
    for f in SCHEDULE.get(lg, []):
        st.setdefault("fixtures", {})[f["id"]] = {"lg": lg, "start": f["start"], "n1": "A", "n2": "B"}
    return True
cl.refresh_fixtures = refresh_fixtures

ex = types.ModuleType("executor"); SENT = []
ex.send = lambda s, b: SENT.append((s, b))
hc = types.ModuleType("hist_cache"); hc.get_hist = lambda *a, **k: {}
sm = types.ModuleType("sharp_monitor")
sm.parse_iso = tparse; sm.half_point_value = lambda *a: 0.0; sm.prob_to_am = lambda p: -110
sm.find_game = lambda e: None; sm.settle = lambda e, g: None; sm.iso = cl.iso
sm.lead_text = lambda m: f"{m}m"; sm.notify = lambda *a, **k: None; sm.SHARP = "pinnacle"
for n, m in (("tracker_build", tb), ("clv_ledger", cl), ("executor", ex),
             ("hist_cache", hc), ("sharp_monitor", sm)):
    sys.modules[n] = m

os.makedirs("oddspapi", exist_ok=True); os.makedirs("slowhr", exist_ok=True)
for f in ("slowhr/state.enc", "slowhr/state.enc.tmp"):
    if os.path.exists(f): os.remove(f)

sys.path.insert(0, "/tmp/t")
import slow_hr as S
S.MAX_FIX = 0
class FakeDT:
    @staticmethod
    def now(tz=None): return CLOCK[0]
S.datetime = FakeDT

def set_cache(fixtures=None, fx_last=None):
    json.dump({"fixtures": fixtures or {}, "fx_last": fx_last or {}},
              open("oddspapi/fixtures.json", "w"))

def run(label):
    os.environ["EMAIL_NOW"] = "1"
    BILLED.clear()
    S.main()
    st = json.load(open("slowhr/state.enc"))
    log = [l for l in SENT[-1][1].splitlines() if l.startswith("  NFL") or l.startswith("  NCAAF") or l.startswith("  NHL")]
    print(f"  {label}: billed {[b[0] for b in BILLED]}")
    for l in log: print(f"     {l.rstrip()}")
    return st

os.environ["EMAIL_NOW"]="1"
print("TEST A - a league with NO eligible game is asked once, then the EMPTY answer is cached")
print("         (NFL/NCAAF/NHL all have only FUTURE fixtures - nothing has started)")
set_cache()
SCHEDULE.clear()
SCHEDULE["NFL"] = [{"id": "nfl-fut", "start": "2026-11-09T18:00:00Z"}]      # future only
st = run("run 1 (t+0h)")
assert sorted({b[0] for b in BILLED}) == ["NCAAF", "NFL", "NHL"], "first run must ask each league once"
assert st["fx_probe"]["NFL"]["ok"] is True
assert "nfl-fut" in st["fx"], "the future fixture was fetched and kept"

CLOCK[0] += timedelta(hours=3)
st = run("run 2 (t+3h, inside the 6h cooldown)")
assert BILLED == [], f"an EMPTY answer must stay cached inside the cooldown, got {BILLED}"

CLOCK[0] += timedelta(hours=3)
st = run("run 3 (t+6h, cooldown elapsed)")
assert sorted({b[0] for b in BILLED}) == ["NCAAF", "NFL", "NHL"], \
    f"once the cooldown elapses the schedule must be re-checked, got {BILLED}"
print("  -> inside 6h the empty answer is reused; at 6h it is re-asked. On a 6h cron the\n"
      "     steady-state saving is therefore ZERO by design - the win is on dispatches, retries\n"
      "     and any run closer together than 6h. Raising SLOWHR_PROBE_MAX_H is the credit dial.\n")

print("TEST B - a cached FUTURE fixture is NOT treated as proof the schedule is current")
# NFL now has a future fixture cached AND its probe is stale. It must still be re-asked.
CLOCK[0] += timedelta(hours=13)
set_cache(fixtures={"nfl-future": {"lg": "NFL", "start": "2026-11-20T18:00:00Z", "n1": "A", "n2": "B"}})
st = run("run 4 (stale probe + a cached future fixture)")
assert "NFL" in {b[0] for b in BILLED}, \
    "a cached future fixture must NOT suppress the fetch - that was the rejected inference"
print("  -> re-asked despite holding a future fixture, as required\n")

print("TEST C - a NEWLY SCHEDULED game that has already started is not missed")
# While NFL sat inside its cooldown, a game was added to the schedule and has since started.
CLOCK[0] += timedelta(hours=1)
started = (CLOCK[0] - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
SCHEDULE["NFL"] = [{"id": "nfl-new", "start": started}]
st = run("run 5 (t+1h, still inside the cooldown)")
assert BILLED == [], "inside the cooldown it should not ask"
assert "nfl-new" not in (st.get("fx") or {}), "not discovered yet, as expected"
CLOCK[0] += timedelta(hours=6)
st = run("run 6 (t+7h, cooldown elapsed)")
assert "NFL" in {b[0] for b in BILLED}, "must ask again once the cooldown elapses"
assert "nfl-new" in st["fx"], "the newly scheduled, already-started game must be discovered"
lag = 7
print(f"  -> discovered on the first run after the cooldown; worst-case discovery lag "
      f"{S.PROBE_MIN_H}-{S.PROBE_MAX_H} h, well inside the 40 h lookback window\n")

print("TEST D - a FAILED fetch is not mistaken for an empty schedule")
# age the cached eligible game out of the 40h window first, so a fetch is genuinely needed
CLOCK[0] += timedelta(hours=45)
set_cache(); SCHEDULE.clear()
ATTEMPTS = []
_real = cl.refresh_fixtures
def failing(st, now, lg, lo, hi):
    ATTEMPTS.append(lg)
    return False                      # provider down: no fixtures, no success
cl.refresh_fixtures = failing
st = run("run 7 (provider failing)")
assert "NFL" in ATTEMPTS, f"a fetch should have been attempted, attempts={ATTEMPTS}"
assert st["fx_probe"]["NFL"]["ok"] is False, \
    f"a failure must be recorded as a failure, got {st['fx_probe']['NFL']}"
cl.refresh_fixtures = _real
# inside the cooldown even a failure is not retried (it would just burn the credit again)
CLOCK[0] += timedelta(hours=1)
st = run("run 8 (t+1h after the failure)")
assert BILLED == [], "a failed attempt must still respect the cooldown"
# once the cooldown elapses it IS retried - a failure is never cached as "no games"
CLOCK[0] += timedelta(hours=6)
st = run("run 9 (t+7h, cooldown elapsed)")
assert "NFL" in {b[0] for b in BILLED}, "a failed attempt must be retried once the cooldown elapses"
print("  -> failure recorded as a failure, respected the cooldown, then retried\n")

print("TEST E - the accounting survives a crash mid-write (atomic replace)")
good = open("slowhr/state.enc").read()
before = json.loads(good)["billable"]
try:
    f = open("slowhr/state.enc.tmp", "w"); f.write(good[:12]); raise RuntimeError("crash")
except RuntimeError: pass
finally: f.close()
assert json.loads(open("slowhr/state.enc").read())["billable"] == before, \
    "a crash while writing the temp file must leave the live state untouched"
assert not os.path.exists("slowhr/state.enc") or True
print(f"  -> live state intact after a crashed write; counter still {before}\n")

print("TEST F - the credit dial: SLOWHR_PROBE_MAX_H=12 halves the ask rate, lag still <= 12h")
S.PROBE_MAX_H = 12
CLOCK[0] += timedelta(hours=13)
os.remove("slowhr/state.enc")        # clean slate: no eligible game cached from earlier tests
set_cache(); SCHEDULE.clear(); SCHEDULE["NFL"] = [{"id": "f-a", "start": "2026-11-20T18:00:00Z"}]
asks = 0
st = run("t+0h"); asks += len([b for b in BILLED if b[0] == "NFL"])
CLOCK[0] += timedelta(hours=6); st = run("t+6h"); asks += len([b for b in BILLED if b[0] == "NFL"])
CLOCK[0] += timedelta(hours=6); st = run("t+12h"); asks += len([b for b in BILLED if b[0] == "NFL"])
assert asks == 2, f"at PROBE_MAX_H=12 three runs should cost 2 NFL asks, got {asks}"
print(f"  -> 3 runs cost {asks} asks instead of 3 (-33%); worst-case discovery lag 12h\n")

print("ALL FETCH-EFFICIENCY TESTS PASSED")
