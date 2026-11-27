#!/usr/bin/env python3
"""Refusal writeback: release exposure only on proof, and only once.

Peter, 27 Nov: "require exact order identity, fill_read=True, zero filled quantity and authoritative
confirmation of no submission before releasing exposure. Make the release idempotent. Unknown or
contradictory records must remain reserved."

Each of those five is a separate section below, and every HOLD case is asserted to HOLD rather than
merely "not release", so a future change that turned a HOLD into a NO_MATCH (which releases nothing but
also reports nothing) would fail here.
"""
import novig_writeback as W

OK = {"client_id": "c1", "fill_read": True, "filled_qty": 0, "filled_cost": 0,
      "fill_read_src": "not submitted", "fill_read_why": "refused by the hard limits",
      "status": "refused", "error": "inputs outside the hard limits"}


def rows(cid="c1", field="live_order", **leg):
    base = {"status": "placed", "client_id": cid, "asked_stake": 299.88, "filled_stake": None}
    base.update(leg)
    if field == "live_more":
        return [{"key": "dogs|K", "live_more": [base]}]
    return [{"key": "dogs|K", field: base}]


def d(rec, rws):
    return W.classify(rec, W.legs_by_cid(rws))


def check(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    return bool(cond)


def main():
    ok = True

    # ---- 0. the happy path: the real Dogs incident
    dec, why = d(OK, rows())
    ok &= check("a proven pre-submission refusal RELEASES", dec == W.RELEASE, (dec, why))
    for field in ("live_order", "live_rest", "live_more"):
        ok &= check(f"  and it is found on a {field} leg", d(OK, rows(field=field))[0] == W.RELEASE)

    # ---- 1. EXACT ORDER IDENTITY
    for bad in (None, "", "   "):
        ok &= check(f"no client_id ({bad!r}) HOLDs", d({**OK, "client_id": bad}, rows())[0] == W.HOLD)
    ok &= check("an unknown client_id is NO_MATCH, not a release",
                d({**OK, "client_id": "nope"}, rows())[0] == W.NO_MATCH)
    two = [{"key": "a", "live_order": {"client_id": "c1", "status": "placed", "filled_stake": None}},
           {"key": "b", "live_rest": {"client_id": "c1", "status": "placed", "filled_stake": None}}]
    dec, why = d(OK, two)
    ok &= check("one client_id on TWO legs HOLDs (ambiguous identity)", dec == W.HOLD, (dec, why))
    ok &= check("  and says it is ambiguous", "ambiguous" in why)

    # ---- 2. fill_read MUST BE True, by identity not truthiness
    for v in (False, None, 1, "true", "True", 0):
        dec = d({**OK, "fill_read": v}, rows())[0]
        ok &= check(f"fill_read={v!r} HOLDs", dec == W.HOLD, dec)

    # ---- 3. ZERO FILLED QUANTITY
    for q in (None, "", "abc", float("nan")):
        dec, why = d({**OK, "filled_qty": q}, rows())
        ok &= check(f"filled_qty={q!r} HOLDs (unknown is never zero)", dec == W.HOLD)
        # the REASON matters as much as the decision: Peter's rule is that unknown stays reserved AND
        # is reported as unknown. Saying "something filled" about an unread quantity is a different
        # claim, and one the record cannot support.
        ok &= check(f"  and it is reported as unreadable, not as a fill",
                    "missing or unreadable" in why, why)
    for q in (1, 0.5, 100, -1):
        ok &= check(f"filled_qty={q} HOLDs (something filled)",
                    d({**OK, "filled_qty": q}, rows())[0] == W.HOLD)
    dec, why = d({**OK, "filled_cost": 12.5}, rows())
    ok &= check("zero qty but non-zero cost HOLDs (contradictory)", dec == W.HOLD, (dec, why))

    # ---- 4. AUTHORITATIVE CONFIRMATION OF NO SUBMISSION
    for src in (None, "", "venue read", "fills list", "refused", "not_submitted", "unknown"):
        dec, why = d({**OK, "fill_read_src": src}, rows())
        ok &= check(f"fill_read_src={src!r} HOLDs", dec == W.HOLD, (dec, why))
    ok &= check("  the exact marker is accepted, case-insensitively",
                d({**OK, "fill_read_src": "NOT SUBMITTED"}, rows())[0] == W.RELEASE)
    dec, why = d({**OK, "order_id": "ord-9"}, rows())
    ok &= check("'not submitted' WITH a venue order_id HOLDs (contradictory)", dec == W.HOLD, (dec, why))

    # ---- 5. THE REGISTRY MUST NOT ALREADY DISAGREE
    dec, why = d(OK, rows(filled_stake=150.0))
    ok &= check("registry shows $150 filled but snapshot says unsubmitted -> HOLD", dec == W.HOLD, (dec, why))
    ok &= check("registry filled_stake unreadable -> HOLD",
                d(OK, rows(filled_stake="abc"))[0] == W.HOLD)

    # ---- 6. IDEMPOTENT
    r = rows()
    dec, _ = d(OK, r)
    ok &= check("first pass releases", dec == W.RELEASE)
    leg = r[0]["live_order"]
    W.apply_to_leg(leg, OK)
    ok &= check("after apply, the leg carries a proven zero", leg["filled_stake"] == 0.0
                and leg["fill_read"] is True and leg["writeback"] == W.DONE_MARK)
    ok &= check("second pass is DONE, not a second release", d(OK, r)[0] == W.DONE)
    ok &= check("  and the reason says so", "already" in d(OK, r)[1])
    r2 = rows(filled_stake=0.0, fill_read=True)
    ok &= check("a leg already carrying a proven zero is DONE even without the mark",
                d(OK, r2)[0] == W.DONE)

    # ---- 7. plan(): the duplicate in one snapshot acts once, and HOLDs are reported not dropped
    rel, other = W.plan([OK, OK], rows())
    ok &= check("a duplicate record in one snapshot releases once", len(rel) == 1, len(rel))
    ok &= check("  and the duplicate is reported", W.DONE in other)
    rel, other = W.plan([{**OK, "fill_read": False}], rows())
    ok &= check("a HOLD releases nothing", rel == [])
    ok &= check("a HOLD is reported with its reason", other.get(W.HOLD) and "UNKNOWN" in other[W.HOLD][0])
    rel, other = W.plan([], rows())
    ok &= check("an empty snapshot releases nothing", rel == [] and other == {})
    rel, other = W.plan(None, None)
    ok &= check("None inputs release nothing", rel == [] and other == {})

    # ---- 8. a leg with no client_id is not indexable, so it can never be released by accident
    nocid = [{"key": "x", "live_order": {"status": "placed", "order_id": "o1", "filled_stake": None}}]
    ok &= check("a leg with only an order_id is not released", d(OK, nocid)[0] == W.NO_MATCH)

    print("\nALL PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
