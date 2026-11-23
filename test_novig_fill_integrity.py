"""Novig fill-status integrity, CLOUD side (Peter, PRIORITY 1, 19 Nov 2026).

The incident: "[BOARD V4] NOVIG NO FILL: NBA Golden State vs Memphis ... nothing traded" went out
for an order that had MATCHED $203.50, and LAC/SA matched $215.80 the same day. Neither was
verified by our fill reader; 0 of 29 Novig placements since 12 Nov carry a fill read, so the false
no-fill was the ORDINARY path.

The root cause is upstream of this repo. novig_live_order.py HERE is a mirror that nothing
executes: the self-hosted Windows runner checks out faros4life/novig-runner and runs ITS copy
(novig-live-order.yml). The fabricated zero, and the writer-side tests for it, therefore live in
that repo - novig-runner/test_fill_integrity.py drives the real settle(), fills_for() and place().

This file tests the half that runs in the cloud: that nothing here turns an unread fill into a
confirmed zero, in the classifier, the exposure calculation, or the Telegram head and body. The
RUNNER_* records below are the contract between the two repos - the exact shapes the patched runner
emits - so if that contract ever changes, these tests are what notices.
"""
import ast
import inspect
import itertools
import textwrap
from datetime import datetime, timedelta, timezone

import executor as ex
import liquidity_monitor as lm
import novig_reconcile as nvr

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


NOW = datetime.now(timezone.utc)
PLACED = (NOW - timedelta(minutes=40)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---- THE RUNNER CONTRACT (proven by novig-runner/test_fill_integrity.py) -------------------
# unread: both venue reads failed. filled_qty is None, fill_read False, and the reason is named.
RUNNER_UNREAD = {"client_id": "gsmem-1", "order_id": "NV-GSMEM", "qty": 20553, "price": 0.50,
                 "tif": "FOK", "placed_utc": PLACED, "status": "UNKNOWN",
                 "label": "NBA Golden State vs Memphis | Under 225.5",
                 "play_key": "NBA|Golden State vs Memphis: Total Points|total|UNDER",
                 "filled_qty": None, "fill_read": False, "fill_read_src": None,
                 "fill_read_why": "order read failed (HTTP 401); fills read failed (HTTP 500)"}
# proven zero: the ORDER OBJECT reported qty == remaining. The only thing that can prove a zero,
# because Novig's fills pagination and completeness are not established.
RUNNER_ZERO = dict(RUNNER_UNREAD, status="CANCELED", filled_qty=0, fill_read=True,
                   fill_read_src="order object", fill_read_why=None)
# positive: a real read.
RUNNER_FILLED = dict(RUNNER_UNREAD, status="FILLED", filled_qty=20553, fill_read=True,
                     fill_read_src="order object + fills list", fill_read_why=None,
                     filled_cost=203.50)
# a pre-flag row, written before fill_read existed: a bare 0 that nothing can vouch for.
RUNNER_LEGACY = {k: v for k, v in dict(RUNNER_ZERO, filled_qty=0).items()
                 if k not in ("fill_read", "fill_read_src", "fill_read_why")}
LACSA_UNREAD = dict(RUNNER_UNREAD, client_id="lacsa-1", order_id="NV-LACSA", qty=21580,
                    play_key="NBA|Los Angeles C vs San Antonio: Total Points|total|UNDER",
                    label="NBA Los Angeles C vs San Antonio | Under 226.5")

print("1. the cloud reads the runner contract correctly")
check("an unread fill is UNKNOWN here", ex.fq_read(RUNNER_UNREAD) == (False, 0))
check("and its zero is not proven", ex.fq_zero_proven(RUNNER_UNREAD) is False)
check("a proven zero is known AND proven",
      ex.fq_read(RUNNER_ZERO) == (True, 0) and ex.fq_zero_proven(RUNNER_ZERO) is True)
check("a positive fill is known", ex.fq_read(RUNNER_FILLED) == (True, 20553))
check("a pre-flag bare zero is NOT proven", ex.fq_zero_proven(RUNNER_LEGACY) is False)
check("fq_read never raises on an unreadable value", ex.fq_read({"filled_qty": "n/a"}) == (False, 0))

print("\n6. READER - the classifier never releases an unread fill")
by = {"gsmem-1": dict(RUNNER_UNREAD, status="CANCELED")}
cls, evd = nvr.classify({"order_id": "gsmem-1", "asked_stake": 205.53, "resting": False}, by, {})
check("a terminal status with an unread quantity is UNKNOWN, not TERMINAL",
      cls == nvr.UNKNOWN, cls)
check("the evidence says why", "not read" in str(evd.get("why", "")), evd.get("why"))
check("exposure keeps the whole commitment",
      nvr.exposure_for({"asked_stake": 205.53, "filled_stake": 0.0}, cls, evd) == 205.53,
      nvr.exposure_for({"asked_stake": 205.53, "filled_stake": 0.0}, cls, evd))

by_proven = {"c": {"client_id": "c", "status": "CANCELED", "qty": 20553, "price": 0.50,
                   "filled_qty": 0, "fill_read": True}}
cls2, ev2 = nvr.classify({"order_id": "c", "asked_stake": 205.53}, by_proven, {})
check("a PROVEN zero on a terminal status still releases", cls2 == nvr.TERMINAL, cls2)
check("and it counts nothing", nvr.exposure_for({"asked_stake": 205.53}, cls2, ev2) == 0.0)

by_legacy = {"c": {"client_id": "c", "status": "CANCELED", "qty": 20553, "price": 0.50,
                   "filled_qty": 0}}                      # pre-flag row: 0 with no proof
cls3, ev3 = nvr.classify({"order_id": "c", "asked_stake": 205.53}, by_legacy, {})
check("a pre-flag zero is NOT released", cls3 == nvr.UNKNOWN, cls3)

print("\n6b. REFUSED proves its own zero - it was never submitted")
for st_ in ("REFUSED",):
    by_np = {"c": {"client_id": "c", "status": st_, "qty": 20553, "price": 0.50,
                   "filled_qty": None, "fill_read": False}}
    c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, by_np, {})
    check(f"{st_} with an UNREAD fill still releases (it was never placed)", c_ == nvr.TERMINAL, c_)
    check(f"{st_} counts nothing", nvr.exposure_for({"asked_stake": 205.53}, c_, e_) == 0.0)
# superseded 19 Nov: REJECTED used to release here too. It no longer does without proof - see 6c.
by_np_f = {"c": {"client_id": "c", "status": "REFUSED", "qty": 20553, "price": 0.50,
                 "filled_qty": 500, "fill_read": True}}
c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, by_np_f, {})
check("but a REFUSED row showing a positive fill is NOT released", c_ != nvr.TERMINAL, c_)
for st_ in ("CANCELED", "EXPIRED"):
    by_c = {"c": {"client_id": "c", "status": st_, "qty": 20553, "price": 0.50,
                  "filled_qty": None, "fill_read": False}}
    c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, by_c, {})
    check(f"{st_} with an unread fill is NOT released - it may have filled first",
          c_ == nvr.UNKNOWN, c_)

print("\n6c. REJECTED needs a proven zero; REFUSED does not (Peter, 19 Nov)")
# REFUSED is pre-submission by construction in BOTH repos - traced: every book_live.novig_place
# refusal returns before its dispatch POST, and the runner's "refused" is its initial status.
for fr in (True, False, None):
    row = {"client_id": "c", "status": "REFUSED", "qty": 20553, "price": 0.50, "filled_qty": 0}
    if fr is not None:
        row["fill_read"] = fr
    c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, {"c": row}, {})
    check(f"REFUSED releases with fill_read={fr}", c_ == nvr.TERMINAL, c_)
# REJECTED can come from an ambiguous HTTP code. The runner DEPLOYED today writes it for ANY
# non-2xx, including a 5xx or a transport failure, and a 409 can mean an earlier attempt landed.
rej_proven = {"client_id": "c", "status": "REJECTED", "qty": 20553, "price": 0.50,
              "filled_qty": 0, "fill_read": True, "fill_read_src": "not submitted"}
c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, {"c": rej_proven}, {})
check("REJECTED with a PROVEN zero releases", c_ == nvr.TERMINAL, c_)
rej_legacy = {k: v for k, v in rej_proven.items() if k not in ("fill_read", "fill_read_src")}
c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53}, {"c": rej_legacy}, {})
check("REJECTED with an UNPROVEN zero does NOT release", c_ == nvr.UNKNOWN, c_)
check("and its exposure stays reserved in full",
      nvr.exposure_for({"asked_stake": 205.53, "filled_stake": 0.0}, c_, e_) == 205.53)
c_, e_ = nvr.classify({"order_id": "c", "asked_stake": 205.53},
                      {"c": dict(rej_legacy, filled_qty=None)}, {})
check("REJECTED with an unread quantity does NOT release", c_ == nvr.UNKNOWN, c_)

print("\n7. READER - the head for every state")
def row(**kw):
    return dict({"qty": 20553, "price": 0.50, "status": "?", "tif": "FOK"}, **kw)


cases = [
    ("unread fill, terminal status", row(status="CANCELED", filled_qty=None, fill_read=False),
     "NOVIG STATUS UNKNOWN - VERIFY"),
    ("unread fill, no status", row(status="", filled_qty=None, fill_read=False),
     "NOVIG STATUS UNKNOWN - VERIFY"),
    ("pre-flag zero, terminal status", row(status="CANCELED", filled_qty=0),
     "NOVIG STATUS UNKNOWN - VERIFY"),
    ("PROVEN zero, terminal status", row(status="CANCELED", filled_qty=0, fill_read=True),
     "NOVIG NO FILL"),
    ("proven zero, OPEN", row(status="OPEN", filled_qty=0, fill_read=True, tif="GTT"),
     "NOVIG RESTING (nothing filled yet)"),
    ("unread fill, OPEN", row(status="OPEN", filled_qty=None, fill_read=False, tif="GTT"),
     "NOVIG RESTING - MATCHED QUANTITY NOT CONFIRMED"),
    ("partial", row(status="OPEN", filled_qty=15000, fill_read=True), "NOVIG PARTIAL FILL"),
    ("full", row(status="FILLED", filled_qty=20553, fill_read=True), "NOVIG FILLED"),
    ("refused", row(status="REFUSED", filled_qty=0, fill_read=True), "NOVIG REFUSED"),
    ("rejected", row(status="REJECTED", filled_qty=0, fill_read=True), "NOVIG REJECTED"),
]
for nm, x, want in cases:
    got = ex.novig_head(x)
    check(f"{nm} -> {want}", got == want, f"got {got}")

print("\n8. READER - an unknown fill can NEVER produce a no-fill head")
import itertools
bad = []
for st in ("", "?", "CANCELED", "CANCELLED", "EXPIRED", "OPEN", "PENDING", "SENT", "UNKNOWN",
           "FILLED", "REFUSED", "REJECTED", "WEIRD"):
    for fv, fr in itertools.product([None, "", "n/a", "oops"], [False, None]):
        x = row(status=st, filled_qty=fv)
        if fr is not None:
            x["fill_read"] = fr
        h = ex.novig_head(x)
        if h in ("NOVIG NO FILL", "NOVIG FILLED", "NOVIG PARTIAL FILL",
                 "NOVIG RESTING (nothing filled yet)"):
            bad.append((st, fv, fr, h))
check("no unreadable quantity reaches a head that claims a fill outcome", not bad, bad[:4])

print("\n9. CHAIN - the two regression cases end to end")
for nm, w, matched in (("GS/MEM Under 225.5", RUNNER_UNREAD, 203.50),
                       ("LAC/SA Under 226.5", LACSA_UNREAD, 215.80)):
    cid = w["client_id"]
    head = ex.novig_head(dict(w, status="CANCELED"))
    cls, evd = nvr.classify({"order_id": cid, "asked_stake": matched, "resting": False},
                            {cid: dict(w, status="CANCELED")}, {})
    expo = nvr.exposure_for({"asked_stake": matched, "filled_stake": 0.0}, cls, evd)
    print(f"   {nm}: filled_qty={w['filled_qty']} head={head!r} class={cls} exposure=${expo:,.2f}")
    check(f"{nm}: never says NO FILL", head != "NOVIG NO FILL", head)
    check(f"{nm}: says STATUS UNKNOWN", head == "NOVIG STATUS UNKNOWN - VERIFY", head)
    check(f"{nm}: exposure is NOT released", expo == matched, expo)
    check(f"{nm}: the venue class is UNKNOWN", cls == nvr.UNKNOWN, cls)
    check(f"{nm}: and the id resolved, so the verdict is about the FILL",
          "not read" in str(evd.get("why", "")), evd.get("why"))

print("\n10. CHAIN - an expired resting bid with an unreadable fill is reported, not silenced")
srcf = textwrap.dedent(inspect.getsource(ex.novig_reports))
fn = next(n for n in ast.walk(ast.parse(srcf))
          if isinstance(n, ast.FunctionDef) and n.name == "_expire")
ns = {"datetime": datetime, "timezone": timezone, "timedelta": timedelta, "lm": lm,
      "fq_read": ex.fq_read}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<_expire>", "exec"), ns)
_expire = ns["_expire"]

gtt = {"tif": "GTT", "ttl_ms": 30 * 60 * 1000, "placed_utc": PLACED, "qty": 20553, "price": 0.50,
       "client_id": "rest-1", "status": "OPEN"}
e_unread = _expire(dict(gtt, filled_qty=None, fill_read=False, fill_read_why="fills read failed (HTTP 500)"))
check("it is marked unresolved", e_unread.get("_unresolved") is True)
check("status becomes UNKNOWN, not EXPIRED", e_unread.get("status") == "UNKNOWN", e_unread.get("status"))
check("the head asks for a check", ex.novig_head(e_unread) == "NOVIG STATUS UNKNOWN - VERIFY",
      ex.novig_head(e_unread))
check("the note says the quantity could not be read and this is not a no-fill",
      "could NOT" in e_unread["_exp_note"] and "NOT confirmed unfilled" in e_unread["_exp_note"],
      e_unread.get("_exp_note"))
check("it is NOT skipped by the not-final guard",
      bool(e_unread.get("_unresolved")), "the guard exempts _unresolved rows")

e_proven = _expire(dict(gtt, filled_qty=0, fill_read=True))
check("a PROVEN zero past expiry still reports EXPIRED", e_proven.get("status") == "EXPIRED",
      e_proven.get("status"))
check("and reads as a no-fill", ex.novig_head(e_proven) == "NOVIG NO FILL", ex.novig_head(e_proven))
e_filled = _expire(dict(gtt, filled_qty=20553, fill_read=True))
check("a filled bid past expiry is left alone", e_filled.get("status") == "OPEN"
      and ex.novig_head(e_filled) == "NOVIG FILLED", ex.novig_head(e_filled))

print("\n11. non-submission - the contract the runner guarantees")
NOT_SUBMITTED = dict(RUNNER_UNREAD, status="rejected", filled_qty=0, fill_read=True,
                     fill_read_src="not submitted",
                     fill_read_why="venue rejected the request (HTTP 400) - nothing was submitted")
check("a not-submitted order is a PROVEN zero, so the stop counts no phantom risk",
      ex.fq_zero_proven(NOT_SUBMITTED) is True)
c_, e_ = nvr.classify({"order_id": "gsmem-1", "asked_stake": 205.53},
                      {"gsmem-1": NOT_SUBMITTED}, {})
check("and it releases", c_ == nvr.TERMINAL, c_)
check("the head names the refusal", ex.novig_head(NOT_SUBMITTED) == "NOVIG REJECTED")

print("\n12. PROVENANCE - a zero names the read it came from (priority 1)")
check("the contract carries a source for a proven zero", RUNNER_ZERO["fill_read_src"] == "order object")
check("an unread fill carries none", RUNNER_UNREAD["fill_read_src"] is None)
check("the NO FILL message states the evidence",
      "read from the {x['fill_read_src']}" in inspect.getsource(ex.novig_reports))
check("and an unread quantity is called out in the body",
      "MATCHED QUANTITY NOT READ" in inspect.getsource(ex.novig_reports))

print("\n13. UNKNOWN IS REPORTABLE - no silent disappearance (priority 2)")
young = {"status": "UNKNOWN", "qty": 20553, "filled_qty": None, "fill_read": False,
         "placed_utc": (NOW - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}
stale = dict(young, placed_utc=(NOW - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"))
check("a row 1 minute old is still settling - not reported", ex.stale_unknown(young) is False)
check("a row 30 minutes old is an unresolved event - reported", ex.stale_unknown(stale) is True)
check("an unresolved expiry is reported whatever its age",
      ex.stale_unknown(dict(young, _unresolved=True)) is True)
check("an unparseable timestamp reports rather than drops",
      ex.stale_unknown({"status": "UNKNOWN", "filled_qty": None, "fill_read": False,
                        "placed_utc": "not a date"}) is True)
check("a row whose fill WAS read is not in this path",
      ex.stale_unknown({"filled_qty": 0, "fill_read": True}) is False)
check("a FILLED status with an unread amount is also reported once stale",
      ex.stale_unknown(dict(stale, status="FILLED")) is True)

# _final gates the WHOLE report: extract the real one and prove an all-unknown day still reports.
fin = next(n for n in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(ex.novig_reports))))
           if isinstance(n, ast.FunctionDef) and n.name == "_final")
ns2 = {"fq_read": ex.fq_read, "stale_unknown": ex.stale_unknown}
exec(compile(ast.Module(body=[fin], type_ignores=[]), "<_final>", "exec"), ns2)
_final = ns2["_final"]
check("a young unknown row does not trigger the report", _final(young) is False)
check("a stale unknown row DOES", _final(stale) is True)
check("so a day where EVERY row is unknown is no longer silent", any(_final(x) for x in [stale]))
check("and the head it gets asks for a check",
      ex.novig_head(stale) == "NOVIG STATUS UNKNOWN - VERIFY", ex.novig_head(stale))

print("\n14. ONE PLAY ID across trigger, order and delayed fill (priority 3)")
LANEKEY = "board|NBA|Golden State vs Memphis: Total Points|total|UNDER"
BASE = ex.lane_strip(LANEKEY)
_re, _rr = ex.registry.enabled, ex.registry.rows
try:
    ex.registry.enabled = lambda: True
    ex.registry.rows = lambda: [{"key": LANEKEY}]
    names, keys = ex.lane_lookup([BASE], with_keys=True)
    plain = ex.lane_lookup([BASE])
finally:
    ex.registry.enabled, ex.registry.rows = _re, _rr
check("lane_lookup still resolves the lane name", names.get(BASE) == "BOARD V4", names)
check("the one-argument contract other callers rely on is unchanged",
      isinstance(plain, dict) and plain.get(BASE) == "BOARD V4", type(plain).__name__)
check("and now also returns the FULL lane-prefixed key", keys.get(BASE) == LANEKEY, keys)
live_id = ex.play_id({"play_key": LANEKEY})
check("the delayed id equals the id the trigger and order stages use",
      ex.pid(keys[BASE]) == live_id, f"{ex.pid(keys[BASE])} vs {live_id}")
check("hashing the runner's UNPREFIXED key would NOT have matched (why this was needed)",
      ex.pid(BASE) != live_id)
check("the delayed message carries the id", 'msg += f"\\nID: {pid(_fullkey)' in
      inspect.getsource(ex.novig_reports))
check("an unresolved lane says so instead of inventing an id",
      "unavailable (lane not resolved)" in inspect.getsource(ex.novig_reports))

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_novig_fill_integrity: all passed")
