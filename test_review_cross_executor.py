#!/usr/bin/env python3
"""REVIEW ONLY. Both executors, one play, one unit.

The cloud executor (ProphetX directly, and the dispatcher of every Novig order) and the Novig runner
must agree on three things or the budget is not shared: the play's IDENTITY, who holds the
RESERVATION, and the UNIT LIMIT. These tests drive the shared modules exactly as each side calls
them. No venue, no network, no real registry.

Peter, Nov 23: cover duplicate retries, simultaneous orders and unknown fill outcomes.
"""
import executor as ex
import review_integration as ri
import review_replay as RR
import review_unit_exposure as X
import review_unit_reservation as R

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception as e:                      # the wrong refusal is still a failure of the test
        return f"{type(e).__name__}: {e}"
    return False


class Store:
    """In-memory store with compare-and-swap, the contract RegistryStore presents."""

    def __init__(self, seeded=True, readable=True):
        self.state = {"legs": []}
        if seeded:
            self.state["seeded"] = True
        self.version, self.readable = 1, readable

    def read(self):
        return (None, None) if not self.readable else (
            {**self.state, "legs": [dict(l) for l in self.state["legs"]]}, self.version)

    def write(self, state, version):
        if version != self.version:
            return False
        self.state, self.version = dict(state), self.version + 1
        return True


class Stale:
    """A second runner that read the store BEFORE the first one wrote - the simultaneous case."""

    def __init__(self, real):
        self.real, self.snap = real, real.read()

    def read(self):
        return self.snap

    def write(self, state, version):
        return self.real.write(state, version)


# ------------------------------------------------------------------ 1. ONE identity
PLAYS = {
    "total": {"sport": "NBA", "game": "Los Angeles Lakers @ Boston Celtics",
              "bet": "Under 225.5 (-110)"},
    "spread": {"sport": "NCAAF", "game": "New Mexico Lobos @ Wyoming Cowboys",
               "bet": "New Mexico Lobos -7.5 (-110)"},
    "moneyline": {"sport": "NBA", "game": "Los Angeles Lakers @ Boston Celtics",
                  "bet": "Boston Celtics ML (-150)"},
}
for name, p in PLAYS.items():
    dk = ex.derive_key(p)
    cloud = ri.key_from_registry(dk)                     # what _unit_ledger_guard reserves under
    runner = ri.key_from_registry(dk)                    # the runner is handed derive_key as IN_KEY
    stored = RR.canonical_registry_key("r1|" + dk)       # what the backfill seeds under
    ok(f"{name}: cloud guard, Novig runner and backfill agree on the identity",
       cloud == runner == stored and bool(cloud), f"{cloud} / {runner} / {stored}")
ok("a spread is keyed as market 'side', not defaulted to 'total'",
   ri.key_from_registry(ex.derive_key(PLAYS["spread"])).split("|")[2] == "side")
_src = open("executor.py", encoding="utf-8").read()
_guard = _src.split("def _unit_ledger_guard(")[1].split("\ndef ")[0]
ok("the cloud guard builds its key through key_from_registry(derive_key(p))",
   "ri.key_from_registry(derive_key(p)" in _guard and "ri.play_key(" not in _guard)
adj = [dict(PLAYS["total"], bet=b) for b in ("Under 225.5 (-110)", "Under 226.5 (-108)",
                                              "Under 224.5 (-115)")]
ok("ADJACENT LINES on one side are one identity for both executors",
   len({ri.key_from_registry(ex.derive_key(p)) for p in adj}) == 1)
ok("the opposite side is a different identity",
   ri.key_from_registry(ex.derive_key(dict(PLAYS["total"], bet="Over 225.5 (-110)")))
   != ri.key_from_registry(ex.derive_key(PLAYS["total"])))
ok("every lane prefix collapses to the same identity",
   len({ri.key_from_registry(pre + ex.derive_key(PLAYS["total"]))
        for pre in ("", "rule|", "board|", "r1|", "ncs|", "newlane|")}) == 1)
for bad in ("", "a|b", "a|b|c|d|e|f", "NBA||total|under", None):
    ok(f"a malformed key {bad!r} raises rather than inventing an identity",
       raises(lambda b=bad: ri.key_from_registry(b), X.ExposureUnknown) is True)

# ------------------------------------------------------------------ 2. the handshake
KEY = ri.key_from_registry(ex.derive_key(PLAYS["total"]))
U = 200.0
NOVIG = ri.actor_for("sharp-monitor", "live_order_other", "novig")
PX = ri.actor_for("sharp-monitor", "live_order", "prophetx")
ok("a reservation with no venue cannot be made at all",
   raises(lambda: ri.actor_for("sharp-monitor", "live_order", ""), X.ExposureUnknown) is True)


def cloud_dispatch(store, leg, stake, actor, key=KEY, unit=U, american=-110):
    """What the cloud executor does before any venue call: reserve, then authorize (single use)."""
    g = R.reserve(store, key, leg, stake, american, unit, actor)
    return R.authorize(store, g, stake)


st = Store()
cloud_dispatch(st, "novig-leg-1", 220.0, NOVIG)
ok("the runner claims the reservation the cloud made for Novig",
   R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1") == "novig-leg-1")
ok("DUPLICATE RETRY: the same dispatch replayed is refused",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1"),
          R.ReservationRefused) is True)
ok("a different client id cannot reuse that reservation either",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-2"),
          R.ReservationRefused) is True)
ok("UNKNOWN FILL: a claimed order with no outcome still holds the play's full unit",
   R.available(st, KEY) == 0.0, str(R.available(st, KEY)))
ok("so the cloud cannot place the same side on ProphetX while Novig is unresolved",
   raises(lambda: cloud_dispatch(st, "px-leg-1", 220.0, PX), R.ReservationRefused) is True)
ok("nor an ADJACENT line of it",
   raises(lambda: R.reserve(st, ri.key_from_registry(ex.derive_key(adj[1])), "px-leg-2", 220.0,
                            -108, U, PX), R.ReservationRefused) is True)
R.record_outcome(st, KEY, "novig-leg-1", "canceled", None, False, None)
ok("an UNVERIFIED cancel releases nothing", R.available(st, KEY) == 0.0, str(R.available(st, KEY)))

st = Store()
cloud_dispatch(st, "novig-leg-1", 220.0, NOVIG)
a, b = Stale(st), Stale(st)                       # two runner jobs that both read before either wrote
first = R.claim_dispatched(a, KEY, 110.0, "novig", "cid-a")
ok("SIMULTANEOUS: the first runner wins the claim", first == "novig-leg-1")
ok("SIMULTANEOUS: the second loses the compare-and-swap and is refused, not retried",
   raises(lambda: R.claim_dispatched(b, KEY, 110.0, "novig", "cid-b"),
          R.ReservationRefused) is True)
class Busy(Store):
    """The registry's ordinary bookkeeping commits land between a runner's read and its write."""
    def __init__(self):
        super().__init__(); self.bumps = 2
    def write(self, state, version):
        if self.bumps:
            self.bumps -= 1; self.version += 1      # someone else's unrelated commit moved the sha
            return False
        return super().write(state, version)
_bz = Busy(); _bz.bumps = 0
cloud_dispatch(_bz, "novig-leg-1", 220.0, NOVIG); _bz.bumps = 2
ok("an UNRELATED registry commit does not cost the order: the claim re-reads and re-decides",
   R.claim_dispatched(_bz, KEY, 110.0, "novig", "cid-z") == "novig-leg-1")
_bz.bumps = 5
ok("but it gives up, refused, rather than looping",
   raises(lambda: R.claim_dispatched(_bz, KEY, 110.0, "novig", "cid-y"),
          R.ReservationRefused) is True)
ok("and exactly one claim is on record",
   [l.get("claimed_by") for l in st.state["legs"]] == ["cid-a"])

st = Store()
x, y = Stale(st), Stale(st)                       # the two EXECUTORS racing for one play
R.reserve(x, KEY, "px-leg", 220.0, -110, U, PX)
ok("SIMULTANEOUS EXECUTORS: ProphetX and Novig cannot both reserve the same unit",
   raises(lambda: R.reserve(y, KEY, "novig-leg", 220.0, -110, U, NOVIG, attempts=1),
          R.ReservationRefused) is True and len(st.state["legs"]) == 1)

st = Store()
ok("NO RESERVATION: a Novig order dispatched with nothing reserved is refused",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1"),
          R.ReservationRefused) is True)
cloud_dispatch(st, "px-leg-1", 220.0, PX)
ok("THE MIN @ SF SHAPE: a Novig order cannot ride a ProphetX reservation on the same play",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1"),
          R.ReservationRefused) is True)

st = Store()
R.reserve(st, KEY, "novig-leg-1", 220.0, -110, U, NOVIG)
ok("a reservation the cloud has not yet dispatched cannot be claimed",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1"),
          R.ReservationRefused) is True)

st = Store()
cloud_dispatch(st, "novig-leg-1", 110.0, NOVIG)
ok("a runner order LARGER than the reservation is refused, not trimmed",
   raises(lambda: R.claim_dispatched(st, KEY, 150.0, "novig", "cid-1"),
          R.ReservationRefused) is True)
ok("an order under another play's key finds nothing to claim",
   raises(lambda: R.claim_dispatched(st, ri.key_from_registry(ex.derive_key(PLAYS["spread"])),
                                     50.0, "novig", "cid-1"), R.ReservationRefused) is True)

st = Store()
cloud_dispatch(st, "novig-leg-1", 220.0, NOVIG)
R.record_outcome(st, KEY, "novig-leg-1", "canceled", 0.0, True, "venue read: cancelled, zero fill")
ok("a reservation the venue has proven closed cannot be claimed",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1"),
          R.ReservationRefused) is True)

# ------------------------------------------------------------------ 3. fail closed
ok("an UNSEEDED ledger refuses the claim - old exposure has not been counted yet",
   raises(lambda: R.claim_dispatched(Store(seeded=False), KEY, 110.0, "novig", "c"),
          Exception) is True)
ok("an UNREADABLE store refuses the claim",
   raises(lambda: R.claim_dispatched(Store(readable=False), KEY, 110.0, "novig", "c"),
          X.ExposureUnknown) is True)
st = Store()
cloud_dispatch(st, "novig-leg-1", 220.0, NOVIG)
for bad_stake in (0, -5, float("nan")):
    ok(f"an unreadable stake ({bad_stake}) refuses the claim",
       raises(lambda s=bad_stake: R.claim_dispatched(st, KEY, s, "novig", "c"),
              X.ExposureUnknown) is True)
ok("a claim with no claimant or venue is refused",
   raises(lambda: R.claim_dispatched(st, KEY, 110.0, "novig", ""), X.ExposureUnknown) is True
   and raises(lambda: R.claim_dispatched(st, KEY, 110.0, "", "c"), X.ExposureUnknown) is True)
ok("none of those refusals consumed the reservation",
   R.claim_dispatched(st, KEY, 110.0, "novig", "cid-1") == "novig-leg-1")

# ------------------------------------------------------------------ 4. one unit limit across lanes
st = Store()
cloud_dispatch(st, "px-lane1", 165.0, PX, unit=300.0)            # half a Lane 1 unit at -110
ok("half a Lane 1 unit on ProphetX leaves half a unit for the play",
   abs(R.available(st, KEY) - 0.5) < 1e-9, str(R.available(st, KEY)))
ok("an R1 order on Novig for a full R1 unit is then refused: one play, one unit",
   raises(lambda: R.reserve(st, KEY, "nv-r1", 220.0, -110, 200.0, NOVIG),
          R.ReservationRefused) is True)
cloud_dispatch(st, "nv-r1-half", 110.0, NOVIG, unit=200.0)
ok("but half an R1 unit fits, each leg measured at its OWN lane unit",
   R.available(st, KEY) == 0.0 and R.claim_dispatched(st, KEY, 110.0, "novig", "c") == "nv-r1-half")

# ------------------------------------------------------------------ 5. the two repos cannot drift
import hashlib
for line in open("review_shared.sha256", encoding="utf-8").read().split("\n"):
    if line.strip():
        want, name = line.split()
        have = hashlib.sha256(open(name, "rb").read()).hexdigest()
        ok(f"{name} is byte-identical to the manifest both repositories carry", have == want,
           "edit made here without regenerating review_shared.sha256 and re-syncing the runner")

import yaml
_wf = yaml.safe_load(open(".github/workflows/executor-dry-run.yml"))
_envs = [st.get("env") or {} for j in _wf["jobs"].values() for st in j["steps"]]
ok("the executor workflow passes the EXEC_UNIT_LEDGER variable to the job that places orders",
   any(e.get("EXEC_UNIT_LEDGER") == "${{ vars.EXEC_UNIT_LEDGER }}" and "EXEC_LIVE" in e for e in _envs))
ok("and that same job has the registry token the ledger needs",
   any("EXEC_UNIT_LEDGER" in e and "REGISTRY_TOKEN" in e for e in _envs))

# ------------------------------------------------------------------ 6. the record-only stage
import os
import registry as _registry
import review_store_registry as _rs


class _FakeReg:
    def __init__(self, seeded=True):
        self.data, self.n = {"unit_reservations": {"legs": [], **({"seeded": True} if seeded else {})}}, 1
    def _fetch(self):
        import copy
        return copy.deepcopy(self.data), f"s{self.n}"
    def _put_with_sha(self, merged, sha):
        if sha != f"s{self.n}":
            return False
        self.data, self.n = dict(merged), self.n + 1
        return True


def _with(reg, mode, fn):
    keep = (_registry._fetch, _registry._put_with_sha, os.environ.get("EXEC_UNIT_LEDGER"))
    _registry._fetch, _registry._put_with_sha = reg._fetch, reg._put_with_sha
    os.environ["EXEC_UNIT_LEDGER"] = mode
    try:
        return fn()
    finally:
        _registry._fetch, _registry._put_with_sha = keep[0], keep[1]
        if keep[2] is None:
            os.environ.pop("EXEC_UNIT_LEDGER", None)
        else:
            os.environ["EXEC_UNIT_LEDGER"] = keep[2]


def _r(bet, risk=220.0, shown=-110, unit=200.0, book="prophetx", line=225.5):
    return {"live": {"risk": risk, "shown": shown, "unit": unit, "book": book, "line": line},
            "play": dict(PLAYS["total"], bet=bet)}


for _m, _want in (("off", "off"), ("", "off"), ("ON", "on"), ("record", "record"),
                  ("Record ", "record"), ("true", "off"), ("recording", "off"), ("1", "off")):
    os.environ["EXEC_UNIT_LEDGER"] = _m
    ok(f"mode {_m!r} is read as {_want} - a typo never switches anything on",
       ex._unit_ledger_mode() == _want, ex._unit_ledger_mode())
os.environ.pop("EXEC_UNIT_LEDGER", None)

reg = _FakeReg()
g = _with(reg, "record", lambda: ex._unit_ledger_guard(_r("Under 225.5 (-110)"), "live_order", "prophetx"))
ok("RECORD: the guard returns nothing to consume and raises nothing", g is None)
ok("RECORD: the order is in the ledger at its full asked stake, as an open commitment",
   [(l["asked_stake"], l["status"], l.get("recorded_only")) for l in
    reg.data["unit_reservations"]["legs"]] == [(220.0, "open", True)])
ok("RECORD: consume passes the stake through untouched",
   _with(reg, "record", lambda: ex._unit_ledger_consume(None, 220.0)) == 220.0)
_with(reg, "record", lambda: ex._unit_ledger_guard(_r("Under 226.5 (-108)", shown=-108, line=226.5),
                                                  "live_order", "prophetx"))
ok("RECORD: a second order on an ADJACENT line is NOT refused - nothing is, in this stage",
   len(reg.data["unit_reservations"]["legs"]) == 2)
ok("RECORD: and both are on record under the one play identity",
   len({l["key"] for l in reg.data["unit_reservations"]["legs"]}) == 1)
_with(reg, "record", lambda: ex._unit_ledger_guard(_r("Under 225.5 (-110)"), "live_order", "prophetx"))
ok("RECORD: the same order replayed is recorded once", len(reg.data["unit_reservations"]["legs"]) == 2)
_store = _rs.RegistryStore(reg)
ok("so when enforcement starts, the play recorded during the transition has no unit left",
   R.available(_store, KEY) == 0.0)
ok("ENFORCE after RECORD: a further order on that play is refused",
   raises(lambda: _with(reg, "on", lambda: ex._unit_ledger_guard(
       _r("Under 224.5 (-112)", shown=-112, line=224.5), "live_order", "prophetx")),
       R.ReservationRefused) is True)
ok("ENFORCE after RECORD: a Novig order cannot claim a ProphetX order recorded in transition",
   raises(lambda: R.claim_dispatched(_store, KEY, 100.0, "novig", "c"), R.ReservationRefused) is True)

for _label, _reg, _play in (("an unseeded ledger", _FakeReg(seeded=False), _r("Under 225.5 (-110)")),
                            ("a play with no identity", _FakeReg(),
                             {"live": {"risk": 1.0, "shown": -110, "book": "prophetx"}, "play": {}}),
                            ("an unreadable price", _FakeReg(), _r("Under 225.5 (-110)", shown=None))):
    try:
        _out = _with(_reg, "record", lambda p=_play: ex._unit_ledger_guard(p, "live_order", "prophetx"))
        _raised = False
    except Exception:
        _raised = True
    ok(f"RECORD never blocks an order, even with {_label}", _raised is False and _out is None)
    ok(f"and writes nothing it cannot validate ({_label})",
       not _reg.data["unit_reservations"]["legs"])
ok("OFF: the guard and consume do nothing and the registry is untouched",
   _with(_FakeReg(), "off", lambda: (ex._unit_ledger_guard(_r("Under 225.5 (-110)"), "live_order"),
                                     ex._unit_ledger_consume(None, 5.0))) == (None, 5.0))
ok("a failed record is reported as a COUNT-SAFE log line, with no id, key or amount",
   'print(f"unit ledger: RECORD FAILED ({type(ex).__name__}) - order proceeds unrecorded"' in _src)

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
