"""A venue REFUSAL must release the leg. Nov 27, 2026.

A Novig fill-or-kill on Buffalo -7.5 +104 was refused at 14:16:35Z, 35 seconds after submission -
no money reached the venue. The leg still held its full $300 ask, because:

  1. "refused" was not in TERMINAL_ROW, so reconcile_outcomes classified the row still_live and
     never reached the fill check at all; and
  2. even if it had, the row's zero was marked unread, and the Nov 19 rule holds an unread zero.

That rule is right for a fill FIELD that may never have been read. A refusal is not an unread
field - it is the venue answering, and a fill-or-kill cannot partially fill, so nothing matched by
definition. review_unit_reservation.IGNORED already carries "refused" and scores such a leg at 0.0,
so this makes the sweep agree with the rest of the ledger rather than inventing a new rule.

What must NOT change: an unread zero on any other terminal status still holds the full ask."""
import review_intents as ri
import review_unit_reservation as R

FAILED = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


KEY = "ncaaf|buf@akr|side|buf"   # canonicalised: lane stripped, lowercased


class Store:
    def __init__(self, legs):
        self.state = {"seeded": True, "legs": legs}
        self.version = 1

    def read(self):
        return (self.state, self.version)

    def write(self, new, v):
        self.state, self.version = new, self.version + 1
        return True


def leg(**kw):
    d = {"key": KEY, "leg_id": "L1", "status": "open", "asked_stake": 300.0, "american": 104,
         "unit": 300.0, "order_id": "OID1", "actor": "sharp-monitor:dogs:novig", "venue_order_id": "OID1"}
    d.update(kw)
    return d


def row(**kw):
    """A registry row carries its orders NESTED (live_order / live_rest / live_more), which is the
    shape backfill_candidates reads - a flat dict produces no candidates at all."""
    o = {"order_id": "OID1", "book": "novig", "status": "refused", "filled_stake": 0.0,
         "fill_read": False, "client_id": "cid1", "asked_stake": 300.0, "american": 104, "limit": 104}
    o.update(kw)
    return {"key": "dogs|NCAAF|BUF@AKR|side|BUF", "lane": "dogs", "live_order": o}


ok("'refused' is a terminal row status", "refused" in ri.TERMINAL_ROW)
ok("a refusal is declared proof of zero", "refused" in ri.REFUSAL_PROVES_ZERO)
ok("the reservation module already scores a refused leg at zero", "refused" in R.IGNORED)

# --- the Buffalo case: a refused FOK must free the unit -------------------------------------------
st = Store([leg()])
c = ri.reconcile_outcomes(st, [row()])
ok("a refused row is no longer counted still_live", c["still_live"] == 0, c)
ok("it is not parked as an unread zero", c["unread_zero_held"] == 0, c)
ok("the leg is released at zero", c["released_zero_fill"] == 1, c)
free = R.remaining_mixed(st.state["legs"], KEY)
ok("the play's full unit is available again", abs(free - R.BUDGET) < 1e-9, free)

# --- what must NOT change --------------------------------------------------------------------------
st2 = Store([leg()])
c2 = ri.reconcile_outcomes(st2, [row(status="cancelled", filled_stake=0.0, fill_read=False)])
ok("an UNREAD zero on a cancelled row still holds the ask", c2["unread_zero_held"] == 1, c2)
ok("and it releases nothing", c2["released_zero_fill"] == 0, c2)
ok("the unit stays held", R.remaining_mixed(st2.state["legs"], KEY) < R.BUDGET)

st3 = Store([leg()])
c3 = ri.reconcile_outcomes(st3, [row(status="cancelled", filled_stake=0.0, fill_read=True)])
ok("a READ zero still releases, as before", c3["released_zero_fill"] == 1, c3)

# a refusal that somehow carries a positive fill is a contradiction: reduce to the fill, never free it
# A refusal that carries a POSITIVE fill is a contradiction - the venue cannot both reject an order
# and match it. record_outcome refuses to release on it ("release to 'refused' with a non-zero fill
# - fail closed") and the leg keeps its FULL hold. That is stricter than reducing to the fill, and
# it is the right direction: a record that disagrees with itself must not free capacity.
st4 = Store([leg()])
c4 = ri.reconcile_outcomes(st4, [row(filled_stake=120.0, fill_read=True)])
ok("a refusal carrying a positive fill releases NOTHING", c4["released_zero_fill"] == 0, c4)
ok("the contradiction is counted as a refused release", c4["refused"] == 1, c4)
ok("and the leg keeps its FULL hold", abs(R.remaining_mixed(st4.state["legs"], KEY)) < 1e-9,
   R.remaining_mixed(st4.state["legs"], KEY))

# an open row is untouched
st5 = Store([leg()])
c5 = ri.reconcile_outcomes(st5, [row(status="open")])
ok("an OPEN row is still left alone", c5["still_live"] == 1, c5)

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
