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

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_cross_venue_rest: all passed")
