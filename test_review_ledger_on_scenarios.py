#!/usr/bin/env python3
"""The resting path under the PRODUCTION ledger configuration, EXEC_UNIT_LEDGER=on (Peter, Nov 27).

WHY THIS FILE EXISTS. Every other test of rest_bid runs with the shared unit ledger OFF.
test_rest_lane_caps says so in its own docstring: "It deliberately does NOT enable
EXEC_UNIT_LEDGER: doing so engages review_unit_exposure, which raises without a real ledger." That
exemption hid a blocker. With the ledger ON - which dogs_gate REQUIRES, so it is not optional for
DOGS - rest_bid handed the ledger lv.get("risk") and lv.get("shown"), and on the rest-only path
r["live"] carries neither. ExposureUnknown("stake") escaped rest_bid as an exception: a SKIP
"error: stake" row and a STOP-worthy push instead of a refusal, with the |rest claim left held so
the NEXT run refused too. DOGS resting could not work at all.

So this file does not stub the ledger - it RUNS it, against an in-memory registry blob with the
real compare-and-swap, the real intent sweep and the real reservation arithmetic. Only the venue,
the notifiers and the claim store are stubs. The six scenarios are Peter's own list.
"""
import copy
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ["EXEC_UNIT_LEDGER"] = "on"          # BEFORE executor is imported: the flag is read live

import registry as rg

BLOB = {"data": {"orders": []}, "sha": "s0", "n": 0}


def _fetch():
    return (copy.deepcopy(BLOB["data"]), BLOB["sha"])


def _put_with_sha(data, sha):
    if sha != BLOB["sha"]:                     # a real lost compare-and-swap, not a stub that agrees
        return False
    BLOB["data"], BLOB["n"] = copy.deepcopy(data), BLOB["n"] + 1
    BLOB["sha"] = f"s{BLOB['n']}"
    return True


rg._fetch, rg._put_with_sha = _fetch, _put_with_sha

import executor as ex
import review_store_registry as _rs
import review_unit_reservation as _R

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


FAR = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
LADDER = {"status": "ok", "exact_line": True, "line": None, "alert_line": None,
          "outcome_id": "OC1", "buy_levels": [{"price": 0.50, "size": 100000}]}
SUB, REL, CLAIMS = {}, [], {}


def reset(lane="dogs", lane_risk=0.0, lane_keys=(), place_result=None, rows=()):
    """One isolated scenario: a freshly seeded ledger, an empty lane, stubbed venue and claims."""
    BLOB["data"], BLOB["sha"], BLOB["n"] = {"orders": list(rows)}, "s0", 0
    _R.backfill(_rs.RegistryStore(rg), [], "test seed: no pre-existing orders")
    SUB.clear()
    REL[:] = []
    CLAIMS.clear()
    for l in ex.LANE_RUN:
        ex.LANE_RUN[l] = {"risk": 0.0, "keys": set()}
    st = {"board": ex.BOARD, "r1": ex.R1, "ncs": ex.NCS, "dogs": ex.DOGS}[lane]
    st.clear()
    st.update({"known": True, "keys": set(lane_keys), "risk": float(lane_risk)})
    ex.registry.enabled = lambda: True
    ex.registry.rows = lambda: list(rows)
    ex.registry.submission_held = lambda k: None
    ex.registry.claim_submission = lambda k, c: (CLAIMS.__setitem__(k, c) or True)
    ex.registry.release_submission = lambda k, c: (REL.append(k) or CLAIMS.pop(k, None) or True)
    ex.committed_risk = lambda k: (0.0, None)
    ex.live_guards = lambda: (True, "")
    ex.journal_latch_why = lambda: None
    ex.dogs_kill_state = lambda: {"blocked": False, "why": "ok"}
    ex.rest_pre_alert = lambda *a, **k: None
    ex.px_live.LIVE = True
    ex.REST_BOOKS = ("novig",)
    ex.reread_book = lambda b, ln, rv: dict(LADDER)
    ex.novig_grid_floor = lambda ps, lv: 0.50
    ex.gmail = lambda: ("u", "p", "t")
    for n in ("send", "push", "tg_push"):
        setattr(ex, n, lambda *a, **k: None)

    def place(oid, cost, qty, label, ms, key):
        SUB["dollars"] = round(qty / 100.0 * cost, 2)
        return place_result or {"status": "placed", "order_id": "N1", "book": "novig",
                                "asked_stake": SUB["dollars"]}
    ex.book_live.novig_place = place


def legs():
    return list(((BLOB["data"].get("unit_reservations") or {}).get("legs")) or [])


def reserved():
    """Dollars the LEDGER believes are reserved - read from the blob, not from our own arithmetic."""
    tot = 0.0
    for lg in legs():
        if str(lg.get("state") or "") in ("refused", "void", "dry"):
            continue
        for f in ("stake", "risk", "asked_stake", "amount"):
            if lg.get(f) is not None:
                try:
                    tot += float(lg[f])
                except (TypeError, ValueError):
                    pass
                break
    return round(tot, 2)


_NOSRC = object()      # a sentinel, because `src or lane` and `lane if src is None else src` both
# make "no source at all" unreachable - and that is precisely the case scenario 5 is about. My own
# first version used None for it, so the play silently carried source="dogs" and was correctly
# placed; three assertions then failed for a fault in the harness, not the code.


def play(lane="dogs", key=None, src=_NOSRC, price=140):
    k = key or f"{lane}|NBA|A @ B|side|A"
    return {"source": lane if src is _NOSRC else src, "play_key": k, "sport": "NBA",
            "game": "A @ B", "bet": "A ML (+140)", "start_utc": FAR}


def bid(p, live=None, price=140):
    r = {"play": p, "books": {"novig": dict(LADDER)}, "verdict": "WOULD PLACE", "reason": None,
         "entry": {"price_after_fee": price, "line": None},
         "reval": {"al": {"bet": p["bet"]}, "mtype": "ml", "side": "A", "price": price,
                   "teams": ["A", "B"], "line": None},
         "live": live or {"go": False, "lane": p.get("source"),
                          "why": ["no live book has the alert number or better"]}}
    try:
        return ex.rest_bid(r), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


ok("the ledger is genuinely enforced in this file", ex._unit_ledger_mode() == "on")

# --- SCENARIO 1: rest-only execution ----------------------------------------------------------
print("\n1. REST-ONLY EXECUTION (no take was priced, so lv has no risk/shown/unit)")
reset()
res, exc = bid(play())
ok("rest-only does not raise - the ExposureUnknown blocker is gone", exc is None, exc)
ok("...and the bid is actually placed", (res or {}).get("status") == "placed", str(res)[:90])
ok("...at the DOGS unit, $300", SUB.get("dollars") == 300.0, SUB.get("dollars"))
ok("...and the ledger reserved that real stake, not a guess", reserved() == 300.0,
   f"{reserved()} legs={len(legs())}")

# --- SCENARIO 2: empty FOK, then rest ---------------------------------------------------------
print("\n2. EMPTY FILL-OR-KILL FOLLOWED BY RESTING")
reset()
_lv = {"go": True, "lane": "dogs", "risk": 300.0, "shown": 140, "unit": 300.0,
       "order": {"status": "placed", "fills_read": True, "filled_stake": 0, "asked_stake": 300.0}}
ok("rest_wanted says rest the FULL unit on an empty FOK",
   ex.rest_wanted({"play": play(), "books": {}, "verdict": "WOULD PLACE", "live": dict(_lv)}) is True)
res, exc = bid(play(), live=dict(_lv))
ok("the resting bid goes out", exc is None and (res or {}).get("status") == "placed", exc or str(res)[:80])
ok("...for the whole unit, nothing having filled", SUB.get("dollars") == 300.0, SUB.get("dollars"))

# --- SCENARIO 3: partial fill, then rest the permitted remainder -------------------------------
print("\n3. PARTIAL FILL FOLLOWED BY RESTING THE PERMITTED REMAINDER")
reset()
_lvp = {"go": True, "lane": "dogs", "risk": 300.0, "shown": 140, "unit": 300.0,
        "order": {"status": "placed", "fills_read": True, "filled_stake": 110.0,
                  "asked_stake": 300.0}}
_rw = {"play": play(), "books": {}, "verdict": "WOULD PLACE", "live": dict(_lvp)}
ok("rest_wanted rests only the unfilled part", ex.rest_wanted(_rw) is True
   and _rw["live"]["rest_risk"] == 190.0, _rw["live"].get("rest_risk"))
reset()
res, exc = bid(play(), live=dict(_lvp, rest_risk=190.0))
ok("the remainder is what goes out", exc is None and SUB.get("dollars") == 190.0,
   exc or SUB.get("dollars"))
ok("take + rest never exceeds the $300 unit", 110.0 + (SUB.get("dollars") or 0) <= 300.0 + 1e-9,
   110.0 + (SUB.get("dollars") or 0))
ok("...and the ledger reserved the remainder, not a second full unit", reserved() == 190.0, reserved())

# --- SCENARIO 4: multiple submissions approaching the daily risk and play limits ---------------
print("\n4. MULTIPLE SUBMISSIONS APPROACHING THE DAILY RISK AND PLAY LIMITS (item 2)")
reset(lane="board", lane_risk=ex.BOARD_DAILY_RISK - 450.0)
_placed, _why = 0.0, ""
for i in range(5):
    reset_rows = None
    p_i = play("board", key=f"board|NBA|G{i} @ H{i}|side|A")
    SUB.clear()
    res, exc = bid(p_i)
    if (res or {}).get("status") == "placed":
        _placed += SUB.get("dollars") or 0.0
        ex.lane_commit_run("board", p_i["play_key"], SUB.get("dollars") or 0.0)
    else:
        _why = str((res or {}).get("reason") or exc)
        break
ok("the daily risk cap now BINDS within one run", "daily risk limit" in _why, _why[:80] or "never refused")
ok(f"...after admitting no more than the ${450.0:,.0f} of headroom", _placed <= 450.0 + 1e-9, _placed)
reset(lane="board", lane_risk=0.0, lane_keys={f"k{i}" for i in range(ex.BOARD_MAX_PLAYS)})
res, exc = bid(play("board", key="board|NBA|Z @ Y|side|Z"))
ok("the play maximum binds on a resting bid",
   (res or {}).get("status") == "refused" and "play cap" in str((res or {}).get("reason")),
   str(res)[:80] or exc)
# item 3: two legs of ONE play are one slot, but both lots of money
reset(lane="dogs")
ex.lane_commit_run("dogs", "dogs|NBA|A @ B|side|A", 110.0)      # take leg, lane-prefixed
ex.lane_commit_run("dogs", "NBA|A @ B|side|A", 190.0)           # rest leg, unprefixed
_r, _n, _u = ex.lane_counts("dogs", ex.DOGS, "NBA|A @ B|side|A")
ok("item 3: two legs of one play consume ONE play slot", _u == 1 and _n == 1, (_u, _n))
ok("item 3: ...while their combined exposure is fully counted", _r == 300.0, _r)
_r2, _n2, _u2 = ex.lane_counts("dogs", ex.DOGS, "NBA|C @ D|side|C")
ok("item 3: a different play is a second slot", _n2 == 2, _n2)

# --- SCENARIO 5: missing or contradictory lane attribution -------------------------------------
print("\n5. MISSING OR CONTRADICTORY LANE ATTRIBUTION")
reset()
res, exc = bid(play("dogs", key="NBA|A @ B|side|A", src=None))
ok("a play with NO lane evidence at all is refused, not defaulted",
   (res or {}).get("status") == "refused" and "lane could not be proven" in str((res or {}).get("reason")),
   str(res)[:100] or exc)
reset()
res, exc = bid(play("dogs", key="board|NBA|A @ B|side|A", src="dogs"))
ok("a key prefix that CONTRADICTS the source is refused",
   (res or {}).get("status") == "refused" and "lane could not be proven" in str((res or {}).get("reason")),
   str(res)[:100] or exc)
ok("...and nothing was submitted on either", SUB.get("dollars") is None, SUB.get("dollars"))
reset()
res, exc = bid(play("dogs", key="dogs|NBA|A @ B|side|A", src="dogs"))
ok("agreeing key and source proceed normally", (res or {}).get("status") == "placed", str(res)[:80])

# --- SCENARIO 6: failed submissions and reservation recovery -----------------------------------
print("\n6. FAILED SUBMISSIONS AND RESERVATION RECOVERY")
reset(place_result={"status": "error", "reason": "venue 500"})
res, exc = bid(play())
_r_after = reserved()
ok("a venue error does not raise out of rest_bid", exc is None, exc)
ok("UNKNOWN exposure stays RESERVED after a failed submission - the venue may hold the order",
   _r_after > 0, f"reserved={_r_after} status={(res or {}).get('status')}")
reset()
res, exc = bid(play("dogs", key="NBA|A @ B|side|A", src=None))   # refused BEFORE any venue contact
ok("a refusal decided before any venue contact releases its claim (provably zero exposure)",
   REL and REL[-1].endswith("|rest"), REL[-1:] )
ok("...and reserves nothing", reserved() == 0.0, reserved())

# --- PRESERVED, as instructed ------------------------------------------------------------------
print("\nPRESERVED")
ok("DOGS unit is $300 per play", ex.DOGS_UNIT == 300.0 and ex.unit_for("dogs") == 300.0)
ok("DOGS eight-play maximum", ex.DOGS_MAX_PLAYS == 8)
ok("DOGS $2,400 daily risk comes from the workflow variable",
   "EXEC_DOGS_DAILY_RISK" in open(".github/workflows/executor-dry-run.yml", encoding="utf-8").read())
ok("the global daily stop is $3,000", ex.px_live.DAILY_STOP == 3000.0, ex.px_live.DAILY_STOP)
ok("MAX_COST in this repo's Novig mirror is $415",
   "MAX_COST = 415.0" in open("novig_live_order.py", encoding="utf-8").read())
ok("MANUAL_HELD still blocks a play in every live lane",
   open("executor.py", encoding="utf-8").read().count("in MANUAL_HELD") >= 4)
ok("duplicate protection: the resting claim is a separate |rest key",
   '_pkey + "|rest"' in open("executor.py", encoding="utf-8").read())
ok("T-30 expiry unchanged", ex.REST_BEFORE_MIN == 30)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
