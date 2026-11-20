#!/usr/bin/env python3
"""Cross-venue committed risk before a resting bid (Peter, Nov 20, PRIORITY 1).

THE INCIDENT, reproduced exactly in section 1: New Mexico -7.5 taken on ProphetX for $110 at
9:11, then rested on Novig for the full unit at 9:12 and filled $237.60 - $347.60 against a $234
intended stake. Same game, side and line, two venues, two runs.

What these tests pin down is the rule, not the arithmetic of one case: a resting bid may only ever
rest the part of the intended stake that is not already committed somewhere else, and when the
committed figure cannot be established it must rest NOTHING.
"""
import sys

import executor as ex

fails = []


def check(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + (f"   [{extra}]" if extra else ""))
    if not cond:
        fails.append(label)


KEY = "NCAAF|New Mexico Lobos @ Wyoming Cowboys|side|New Mexico Lobos"


def row(key=KEY, order=None, rest=None, more=None):
    return {"key": key, "live_order": order, "live_rest": rest, "live_more": more or []}


def leg(status="placed", asked=None, filled=None, book="prophetx", cid="c1", oid="o1"):
    return {"status": status, "asked_stake": asked, "filled_stake": filled, "book": book,
            "client_id": cid, "order_id": oid}


# ==============================================================================================
print("\n1. THE INCIDENT: ProphetX $110 filled, then a Novig resting bid for the full unit")
px = row(order=leg(asked=110.00, filled=110.00, book="prophetx", cid="px-1", oid="PX1"))
committed, why = ex.committed_risk(KEY, rows_=[px])
check("the ProphetX fill is committed risk on this play", committed == 110.00 and why is None,
      f"{committed} why={why}")
INTENDED = 234.00
check("the remainder is the intended stake minus it, not the full unit",
      round(INTENDED - committed, 2) == 124.00, f"{INTENDED - committed}")
check("which is NOT what was rested on the day", round(INTENDED - committed, 2) != 237.60)

print("   and the venue does not matter - the key is lane-stripped and venue-free:")
nv = row(order=leg(asked=237.60, filled=237.60, book="novig", cid="nv-1", oid="NV1"))
both, why = ex.committed_risk(KEY, rows_=[px, nv])
check("both venues sum into one committed figure", both == 347.60 and why is None, f"{both}")
check("and that figure exceeds the intended stake, so nothing may be rested",
      round(INTENDED - both, 2) <= 0, f"remaining {round(INTENDED - both, 2)}")

print("   the lane prefix on the stored key must not hide a leg:")
laned = row(key="r1|" + KEY, order=leg(asked=110.00, filled=110.00, cid="px-2", oid="PX2"))
c, _ = ex.committed_risk(KEY, rows_=[laned])
check("a row stored under 'r1|<key>' still counts against the bare key", c == 110.00, f"{c}")

print("\n2. A DIFFERENT PLAY MUST NOT BE COUNTED")
other = row(key="NCAAF|Other @ Game|side|Other", order=leg(asked=300.0, filled=300.0, cid="x", oid="X"))
c, why = ex.committed_risk(KEY, rows_=[px, other])
check("only this play's legs are summed", c == 110.00 and why is None, f"{c}")

print("\n3. PARTIAL FILLS reserve the whole ask while the rest is still working")
part = row(order=leg(asked=234.00, filled=110.00, cid="p1", oid="P1"))
c, _ = ex.committed_risk(KEY, rows_=[part])
check("a partially filled order reserves its full ask, not just the filled part", c == 234.00,
      f"{c}")

print("\n4. UNKNOWN status: an unread fill reserves the ask, never zero")
unk = row(order=leg(status="placed", asked=237.60, filled=None, cid="u1", oid="U1"))
c, why = ex.committed_risk(KEY, rows_=[unk])
check("a placed order with no readable fill reserves its full ask", c == 237.60 and why is None,
      f"{c}")
check("it is NOT treated as zero", c != 0)

print("\n5. ORDERS THAT NEVER REACHED THE VENUE reserve nothing")
for st in ("refused", "void", "dry"):
    r = row(order=leg(status=st, asked=234.00, cid=f"n-{st}", oid=f"N{st}"))
    c, why = ex.committed_risk(KEY, rows_=[r])
    check(f"status '{st}' reserves nothing", c == 0.0 and why is None, f"{c}")

print("   the incident's own refused leg is one of these:")
inc = [px, row(order=leg(status="refused", asked=234.00, book="novig", cid="nv-ref", oid="NVR"))]
c, _ = ex.committed_risk(KEY, rows_=inc)
check("ProphetX $110 + a refused Novig attempt = $110 committed", c == 110.00, f"{c}")
check("so the resting bid should have been $124.00, not $237.60",
      round(INTENDED - c, 2) == 124.00)

print("\n6. ONE ORDER IS COUNTED ONCE across the intent row and the confirmed row")
intent = row(order=leg(asked=110.00, filled=None, cid="same", oid="SAME"))
confirmed = row(order=leg(asked=110.00, filled=110.00, cid="same", oid="SAME"))
c, _ = ex.committed_risk(KEY, rows_=[intent, confirmed])
check("the same client id is not double counted", c == 110.00, f"{c}")
diff = row(order=leg(asked=110.00, filled=110.00, cid="other-cid", oid="OTHER"))
c, _ = ex.committed_risk(KEY, rows_=[confirmed, diff])
check("two genuinely different orders both count", c == 220.00, f"{c}")

print("\n6b. THE REAL STORED SHAPE carries order_id and NO client_id")
# executor's registry projection writes only status/reason/book/order_id/asked_stake/limit/
# filled_stake/avg_price (or expires_utc). It has no client_id at all - the daily stop's
# "money identity is the CLIENT ID" holds for Gmail-parsed rows, not for these. So the order id
# is what actually dedupes stored rows, and these cases use that shape exactly.
def stored(book="prophetx", oid="O1", asked=None, filled=None, status="placed", expires=None):
    d = {"status": status, "reason": None, "book": book, "order_id": oid,
         "asked_stake": asked, "limit": -117, "filled_stake": filled, "avg_price": None}
    if expires:
        d["expires_utc"] = expires
    return d

s1 = row(order=stored(oid="PX9", asked=110.00, filled=110.00))
c, why = ex.committed_risk(KEY, rows_=[s1])
check("a stored leg with no client_id is still counted", c == 110.00 and why is None, f"{c} {why}")
dup = row(order=stored(oid="PX9", asked=110.00, filled=None))
c, _ = ex.committed_risk(KEY, rows_=[s1, dup])
check("the same order id across two rows counts ONCE", c == 110.00, f"{c}")
two = row(order=stored(oid="PX9", asked=110.00, filled=110.00),
          rest=stored(book="novig", oid="NV9", asked=238.00, filled=237.60,
                      expires="2026-11-21T01:30:00Z"))
c, _ = ex.committed_risk(KEY, rows_=[two])
check("two different order ids in the real shape both count", c == 348.00, f"{c}")
check("which is the incident's combined exposure, from production-shaped records",
      c > 234.00)

print("\n6c. ONE ORDER KEEPS ITS MAXIMUM, whatever order the records arrive in")
# Nov 20 (Peter, PR #9 review): a `seen` set let the FIRST record of an order win, so an intent
# row recording a smaller amount ahead of the confirmed row would UNDERCOUNT exposure - the
# direction that places money. Every record of one order is now grouped and the group keeps its
# maximum, and grouping is by any SHARED identity because the two id fields do not co-occur.
small = row(order=leg(asked=110.00, filled=None, cid="k1", oid="K1"))
large = row(order=leg(asked=238.00, filled=237.60, cid="k1", oid="K1"))
c_fwd, _ = ex.committed_risk(KEY, rows_=[small, large])
c_rev, _ = ex.committed_risk(KEY, rows_=[large, small])
check("the larger record wins when it arrives second", c_fwd == 238.00, f"{c_fwd}")
check("REVERSED record order gives the identical answer", c_rev == c_fwd, f"{c_rev} vs {c_fwd}")
check("and it is NOT the first record's smaller figure", c_fwd != 110.00)

print("   differing FILLED amounts for one order:")
f1 = row(order=leg(asked=238.00, filled=100.00, cid="k2", oid="K2"))
f2 = row(order=leg(asked=238.00, filled=237.60, cid="k2", oid="K2"))
c, _ = ex.committed_risk(KEY, rows_=[f2, f1])
check("the maximum exposure is retained, not the last seen", c == 238.00, f"{c}")
o1 = row(order=leg(asked=None, filled=100.00, cid="k3", oid="K3"))
o2 = row(order=leg(asked=None, filled=237.60, cid="k3", oid="K3"))
c, _ = ex.committed_risk(KEY, rows_=[o1, o2])
check("with no ask recorded, the larger fill wins", c == 237.60, f"{c}")

print("   MIXED identities: the same order seen under different id fields:")
by_cid = row(order={"status": "placed", "client_id": "mix-1", "asked_stake": 110.00,
                    "filled_stake": 110.00, "book": "prophetx"})
by_oid = row(order={"status": "placed", "order_id": "MIX1", "asked_stake": 238.00,
                    "filled_stake": 237.60, "book": "prophetx"})
bridge = row(order={"status": "placed", "client_id": "mix-1", "order_id": "MIX1",
                    "asked_stake": 238.00, "filled_stake": 237.60, "book": "prophetx"})
c_nobridge, _ = ex.committed_risk(KEY, rows_=[by_cid, by_oid])
check("with nothing linking them they are two orders (cannot be known otherwise)",
      c_nobridge == 348.00, f"{c_nobridge}")
c_bridge, _ = ex.committed_risk(KEY, rows_=[by_cid, by_oid, bridge])
check("a record carrying BOTH ids merges them into one order", c_bridge == 238.00, f"{c_bridge}")
c_bridge_rev, _ = ex.committed_risk(KEY, rows_=[bridge, by_oid, by_cid])
check("and the merge is order-independent", c_bridge_rev == c_bridge,
      f"{c_bridge_rev} vs {c_bridge}")

print("   MISSING identity still fails closed, in any position:")
anon = row(order=leg(status="placed", asked=110.0, cid="", oid=""))
for label, rows_ in (("first", [anon, large]), ("last", [large, anon])):
    c, why = ex.committed_risk(KEY, rows_=rows_)
    check(f"an unidentifiable leg {label} refuses", c is None and why, str(why)[:44])

print("   three records of one order, shuffled:")
import itertools
trio = [row(order=leg(asked=110.0, filled=None, cid="t1", oid="T1")),
        row(order=leg(asked=238.0, filled=120.0, cid="t1", oid="T1")),
        row(order=leg(asked=238.0, filled=237.6, cid="t1", oid="T1"))]
vals = {ex.committed_risk(KEY, rows_=list(p))[0] for p in itertools.permutations(trio)}
check("every ordering gives the same maximum", vals == {238.00}, str(vals))

print("\n7. RESTING LEGS AND live_more COUNT TOO")
r = row(rest=leg(asked=238.00, filled=237.60, book="novig", cid="r1", oid="R1"))
c, _ = ex.committed_risk(KEY, rows_=[r])
check("a live_rest leg counts", c == 238.00, f"{c}")
r = row(more=[leg(asked=50.0, filled=50.0, cid="m1", oid="M1"),
              leg(asked=60.0, filled=60.0, cid="m2", oid="M2")])
c, _ = ex.committed_risk(KEY, rows_=[r])
check("live_more legs count", c == 110.00, f"{c}")

print("\n8. FAIL CLOSED when the state is missing, stale or contradictory")
c, why = ex.committed_risk(KEY, rows_=None if False else [row(order=leg(asked=None, filled=None,
                                                                        cid="z", oid="Z"))])
check("a leg with no stake at all refuses", c is None and why, str(why)[:46])
c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked="not-a-number", cid="y", oid="Y"))])
check("an unreadable stake refuses", c is None and why, str(why)[:46])
c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked=110.0, cid="", oid=""))])
check("a placed leg with no identity refuses rather than risk double counting",
      c is None and why, str(why)[:46])


class Boom:
    def __call__(self, *a, **k):
        raise RuntimeError("store down")


_real_rows = ex.registry.rows
try:
    ex.registry.rows = Boom()
    c, why = ex.committed_risk(KEY)
    check("an unreadable store refuses", c is None and why, str(why)[:46])
finally:
    ex.registry.rows = _real_rows

check("a refusal never returns a number the caller could size against",
      ex.committed_risk(KEY, rows_=[row(order=leg(asked=None, cid="q", oid="Q"))])[0] is None)

print("\n9. THE CALLER REFUSES RATHER THAN SIZING AGAINST AN UNKNOWN")
import ast
src = open("executor.py").read()
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "rest_bid")
body = ast.dump(fn)
check("rest_bid calls committed_risk", "committed_risk" in body)
check("and releases its claim when it refuses on that path",
      src.count("release_submission(_rkey, REST_CID)") >= 2,
      f"{src.count('release_submission(_rkey, REST_CID)')} release call(s)")
i_claim = src.index("claim_submission(_rkey, REST_CID)")
i_comm = src.index("_committed, _cwhy = committed_risk(_pkey)")
i_alert = src.index("rest_pre_alert(r, risk, expire, REST_BOOKS)")
check("the remainder is computed AFTER the claim is held (two runs cannot both reserve it)",
      i_claim < i_comm, f"claim@{i_claim} committed@{i_comm}")
check("and BEFORE the pre-alert, so the announced number is the final one",
      i_comm < i_alert, f"committed@{i_comm} alert@{i_alert}")
check("the existing rest_risk trim is still applied",
      'r["live"]["rest_risk"]' in src)
check("duplicate protection is untouched", "submission_held(_pkey)" in src)

# ==============================================================================================
print("\n10. INTEGRATION: the amount that actually reaches the venue")
# Drives the real rest_bid() and captures the stake handed to book_live.novig_place(), because
# committed_risk() arithmetic being right is not the same as the submitted order being right.
# Nov 20: Peter's review caught exactly this gap - the first patch subtracted committed risk from
# the ALREADY-trimmed rest_risk, so intended $234 with $110 filled would have rested $14, not $124.
import types
from datetime import datetime, timedelta, timezone

SUBMITTED = {}


def _run_rest_bid(rows, rest_risk=None, unit_price=-117):
    """Call the production rest_bid() with the venue stubbed; return (result, submitted_cost)."""
    SUBMITTED.clear()
    start = datetime.now(timezone.utc) + timedelta(hours=6)
    play = {"sport": "NCAAF", "game": "New Mexico Lobos @ Wyoming Cowboys",
            "bet": "New Mexico Lobos -7.5 (-117)", "play_key": "r1|" + KEY,
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")}
    live = {"lane": "r1", "client_id": "this-run"}
    if rest_risk is not None:
        live["rest_risk"] = rest_risk
    r = {"play": play, "entry": {"price_after_fee": unit_price}, "live": live,
         "books": {"novig": {"status": "ok", "exact_line": True, "line": -7.5, "alert_line": -7.5,
                             "outcome_id": "OC1",
                             "buy_levels": [{"price": 0.50, "size": 100000}]}}}

    reg = types.SimpleNamespace(
        enabled=lambda: True,
        rows=lambda: rows,
        submission_held=lambda k: None,
        claim_submission=lambda k, c: True,
        release_submission=lambda k, c: True)

    def fake_novig_place(outcome_id, cost, qty, label, ms, key):
        SUBMITTED["cost"] = cost
        SUBMITTED["qty"] = qty
        SUBMITTED["dollars"] = round(qty / 100.0 * cost, 2)
        return {"status": "placed", "order_id": "NEW1", "book": "novig", "asked_stake": SUBMITTED["dollars"]}

    # executor.gmail() raises SystemExit when credentials are absent, and the resting path
    # notifies after a placement - stub the notifiers so this exercises SIZING, nothing else.
    saved = (ex.registry, ex.REST_BOOKS, ex.book_live.novig_place, ex.live_guards,
             ex.rest_pre_alert, ex.journal_latch_why, ex.novig_grid_floor,
             ex.gmail, ex.send, ex.push, ex.tg_push)
    try:
        ex.gmail = lambda: ("u", "p", "t")
        ex.send = lambda *a, **k: None
        ex.push = lambda *a, **k: None
        ex.tg_push = lambda *a, **k: None
        ex.registry = reg
        ex.REST_BOOKS = ("novig",)
        ex.book_live.novig_place = fake_novig_place
        ex.live_guards = lambda: (True, "")
        ex.rest_pre_alert = lambda *a, **k: None
        ex.journal_latch_why = lambda: None
        ex.novig_grid_floor = lambda p_star, levels: 0.50
        res = ex.rest_bid(r)
    finally:
        (ex.registry, ex.REST_BOOKS, ex.book_live.novig_place, ex.live_guards,
         ex.rest_pre_alert, ex.journal_latch_why, ex.novig_grid_floor,
         ex.gmail, ex.send, ex.push, ex.tg_push) = saved
    return res, SUBMITTED.get("dollars")


_unit, _ = ex.live_stake(-117, ex.unit_for("r1"))
print(f"   intended unit at -117 = ${_unit:,.2f}")

print("   a) the incident: $110 filled on ProphetX, no rest_risk on this run (the refused leg)")
res, got = _run_rest_bid([px])
check("an order was submitted", res and res.get("status") == "placed", str(res)[:50])
check(f"it rests intended - committed, not the full unit", got == round(_unit - 110.00, 2),
      f"submitted ${got} vs expected ${round(_unit - 110.00, 2)}")
check("and NOT the full unit that caused the incident", got != _unit)

print("   b) THE DOUBLE-SUBTRACTION Peter caught: rest_risk set AND committed risk present")
res, got = _run_rest_bid([px], rest_risk=round(_unit - 110.00, 2))
check("the same amount is rested, not the fill subtracted twice",
      got == round(_unit - 110.00, 2),
      f"submitted ${got}; double-subtracted would be ${round(_unit - 220.00, 2)}")
check("the two constraints combine as a ceiling, not a second subtraction",
      got != round(_unit - 220.00, 2))

print("   c) rest_risk tighter than the cross-venue allowance still wins")
res, got = _run_rest_bid([px], rest_risk=40.00)
check("the smaller of the two ceilings is used", got == 40.00, f"submitted ${got}")

print("   d) nothing committed: the full unit rests, exactly as before this change")
res, got = _run_rest_bid([])
check("unchanged behaviour when nothing is committed", got == round(_unit, 2), f"${got}")

print("   e) already at or above the intended stake: NOTHING is submitted")
big = row(order=leg(asked=400.00, filled=400.00, cid="b1", oid="B1"))
res, got = _run_rest_bid([big])
check("refused", res.get("status") == "refused", str(res.get("reason"))[:54])
check("and no order reached the venue", got is None and not SUBMITTED)

print("   f) FAIL CLOSED on an unresolved/unidentifiable outstanding order")
bad = row(order=leg(status="placed", asked=110.0, cid="", oid=""))
res, got = _run_rest_bid([bad])
check("refused rather than sized against an unknown", res.get("status") == "refused",
      str(res.get("reason"))[:54])
check("and nothing was submitted", got is None and not SUBMITTED)

print("   g) FAIL CLOSED on an UNKNOWN fill: the ask is reserved, not treated as zero")
unknown = row(order=leg(status="placed", asked=100.00, filled=None, cid="u9", oid="U9"))
res, got = _run_rest_bid([unknown])
check("the unread order reserves its ask, so only the remainder rests",
      got == round(_unit - 100.00, 2), f"submitted ${got}")
check("it was not treated as a zero fill", got != round(_unit, 2))

print("\n11. NUMERICAL SAFETY: nothing non-finite or negative may reach a venue")
# Nov 20 (Peter): float() happily parses "nan" and "inf". NaN is the dangerous one - every
# comparison with it is False, so a NaN exposure slips past a "remaining <= 0" guard and arrives
# at the venue as a quantity. These assert on what reaches novig_place, not just on the return.
import math as _math

print("   a) committed_risk rejects them at the source:")
for label, val in (("NaN asked", float("nan")), ("+inf asked", float("inf")),
                   ("-inf asked", float("-inf")), ("negative asked", -110.0)):
    c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked=val, cid="n1", oid="N1"))])
    check(f"{label} refuses", c is None and bool(why), str(why)[:46])
for label, val in (("NaN filled", float("nan")), ("inf filled", float("inf")),
                   ("negative filled", -5.0)):
    c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked=110.0, filled=val,
                                                          cid="n2", oid="N2"))])
    check(f"{label} refuses", c is None and bool(why), str(why)[:46])
c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked="nan", cid="n3", oid="N3"))])
check("the STRING 'nan' refuses too (float() parses it)", c is None and bool(why), str(why)[:46])
c, why = ex.committed_risk(KEY, rows_=[row(order=leg(asked="inf", cid="n4", oid="N4"))])
check("the string 'inf' refuses too", c is None and bool(why), str(why)[:46])
check("a normal stake is still accepted",
      ex.committed_risk(KEY, rows_=[row(order=leg(asked=110.0, cid="ok", oid="OK"))])[0] == 110.0)

print("   b) INTEGRATION: no venue call is made for any of them")
for label, val in (("NaN", float("nan")), ("inf", float("inf")), ("negative", -110.0)):
    res, got = _run_rest_bid([row(order=leg(asked=val, cid=f"i-{label}", oid=f"I{label}"))])
    check(f"{label} stake: refused", res.get("status") == "refused", str(res.get("reason"))[:48])
    check(f"{label} stake: novig_place was NEVER called", got is None and not SUBMITTED)

print("   c) a NaN arriving as rest_risk cannot reach the venue either")
res, got = _run_rest_bid([], rest_risk=float("nan"))
check("refused before dispatch", res.get("status") == "refused", str(res.get("reason"))[:48])
check("and nothing was submitted", got is None and not SUBMITTED)

print("   d) whatever is submitted on the good path is finite and positive")
res, got = _run_rest_bid([px])
check("the incident's remainder is a finite positive number",
      got is not None and _math.isfinite(got) and got > 0, f"${got}")
check("and it is still exactly $124.00 - the calculation is unchanged", got == 124.00, f"${got}")

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_cross_venue_rest: all passed")
