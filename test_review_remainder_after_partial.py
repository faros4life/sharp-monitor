"""Nov 25, 2026 (Packers/Rams Under 44.5): ProphetX filled part of the unit; the remainder to Novig
was refused twice - the play's submission claim was read as "another run", and the shared ledger
still held the ProphetX leg at its FULL asked stake (0u free). Both are fixed narrowly; this file
replays the case and pins what must still refuse."""
import executor as ex
import review_unit_reservation as R
import review_store_registry as RS

FAILED = []


def ok(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


class Store:
    def __init__(self, state):
        self.state, self.v = state, 1

    def read(self):
        return (self.state, self.v)

    def write(self, new, version):
        if version != self.v:
            return False
        self.state, self.v = new, self.v + 1
        return True


KEY = "nfl|green bay packers @ los angeles rams|total|under"
LEG = {"key": KEY, "leg_id": "live_order|L1", "status": "open", "asked_stake": 345.0,
       "american": -115, "unit": 300.0, "actor": "sharp-monitor:live_order:prophetx",
       "dispatched": True, "order_id": "live_order|L1"}


class G:
    key, leg_id = KEY, "live_order|L1"


def run(lv, first):
    store = Store({R.SEEDED: True, "legs": [dict(LEG)]})
    RS.RegistryStore = lambda _reg, key=None, s=store: s
    ex.LOG.clear()
    done = ex._remainder_settle_first(lv, first)
    return done, store


FIRST = {"status": "placed", "fills_read": True, "filled_stake": 140.0, "asked_stake": 345.0,
         "order_id": "partner_422f"}

before = R.remaining_mixed([dict(LEG)], KEY)
ok(f"before: the partly filled ProphetX leg holds the whole unit ({before:.2f}u free)", before < 1e-9)

done, st = run({"book": "prophetx", "_ledger_grant": G()}, FIRST)
leg = st.state["legs"][0]
free = R.remaining_mixed(st.state["legs"], KEY)
ok("a READ ProphetX fill settles the leg", done and leg.get("terminal_verified") is True)
ok("the leg is held at the fill, 140 of 345", leg.get("filled_stake") == 140.0 and leg.get("status") == "filled")
ok(f"the unfilled part is free for the remainder ({free:.2f}u)", 0.55 < free < 0.65)
ok("the remainder cannot exceed what is free: one unit in total",
   abs(R.leg_fraction(leg) + free - 1.0) < 1e-6)

d2, s2 = run({"book": "prophetx", "_ledger_grant": G()}, dict(FIRST, fills_read=False))
ok("an UNREAD fill settles nothing - full hold kept", not d2 and s2.state["legs"][0]["status"] == "open")
d3, s3 = run({"book": "novig", "_ledger_grant": G()}, FIRST)
ok("a non-ProphetX first leg is never settled here", not d3 and s3.state["legs"][0]["status"] == "open")
d4, s4 = run({"book": "prophetx"}, FIRST)
ok("ledger off (no grant) changes nothing", not d4)
d5, s5 = run({"book": "prophetx", "_ledger_grant": G()}, dict(FIRST, filled_stake=None))
ok("no fill amount settles nothing", not d5)

# the remainder is trimmed to what the ledger has free at the NEXT venue's price
cap = R.maximum_stake(free, -113, 300.0)
ok(f"today's remainder (205 at -113) did not fit; the cap is {cap:.2f}", cap < 205.0 and cap > 195.0)
ok("a stake at the cap reserves (fits exactly)", R.fraction(int(cap * 100) / 100.0, -113, 300.0) <= free + 1e-9)

src = open("executor.py", encoding="utf-8").read()
ok("the remainder claims under the FIRST order's cid",
   'claim_submission(_ckey, (r.get("live") or {}).get("_claim_cid") or cid)' in src)
ok("the carried claim is set before the loop and cleared after it",
   'lv["_claim_cid"] = lv.get("client_id")' in src and 'lv.pop("_claim_cid", None)' in src)
ok("the ProphetX grant is kept for the settle", 'lv["_ledger_grant"] = _led' in src)
ok("the remainder is trimmed by the ledger cap before dispatch", "_cap = _remainder_cap(lv, c)" in src)

import registry as REG
calls = []
def fake_commit(merge):
    merge(DB)
    return True
DB = {"submissions": {"nfl|gb@lar|total|under": {"cid": "first"}}}
REG._commit = fake_commit
ok("the first order's cid re-claims its own key (remainder allowed)", REG.claim_submission("nfl|gb@lar|total|under", "first"))
ok("any other cid still loses the key (duplicate still blocked)", not REG.claim_submission("nfl|gb@lar|total|under", "other"))

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
