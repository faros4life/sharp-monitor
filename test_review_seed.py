#!/usr/bin/env python3
"""REVIEW ONLY. The ledger seed: conservative, all-or-nothing, dry by default, once only."""
import os

import review_replay as RR
import review_seed as S
import review_unit_reservation as R

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


class Store:
    def __init__(self):
        self.state, self.version = {"legs": []}, 1

    def read(self):
        return ({**self.state, "legs": [dict(l) for l in self.state["legs"]]}, self.version)

    def write(self, state, version):
        if version != self.version:
            return False
        self.state, self.version = dict(state), self.version + 1
        return True


K = "nba|lal @ bos|total|under"


def leg(oid, book="novig", vc="OPEN", ec=None, ask=220.0, am=-110, unit=200.0, key=K, lane="r1"):
    return {"key": key, "order_id": oid, "book": book, "field": "live_order", "asked_stake": ask,
            "american": am, "unit": unit, "lane": lane, "venue_class": vc,
            "evidence_class": ec or RR.PROVEN}


seed, sm, why = S.build([leg("a"), leg("b", "prophetx", "FILLED", key="nfl|min @ sf|total|under",
                                   unit=300.0, ask=330.0, lane="lane1")], [])
ok("open and FILLED orders are both seeded", why is None and sm["retained"] == 2, f"{why} {sm}")
ok("every seeded leg is held at its FULL asked stake as an open commitment",
   all(l["status"] == "open" and l["asked_stake"] in (220.0, 330.0) for l in seed))
seed, sm, why = S.build([leg("a", vc="TERMINAL ZERO FILL")], [])
ok("only a venue-PROVEN zero fill is left out", why is None and sm["retained"] == 0
   and sm["proven_zero"] == 1)
seed, sm, why = S.build([leg("a", vc="TERMINAL ZERO FILL", ec=RR.NO_RECORD)], [])
ok("a terminal zero WITHOUT venue proof is seeded in full", sm["retained"] == 1)
seed, sm, why = S.build([leg("a", vc="UNKNOWN", ec=RR.NO_RECORD)], [])
ok("an order whose fill was never read is seeded in full and counted as unproven",
   why is None and sm["retained"] == 1 and sm["unproven_retained_in_full"] == 1)
for label, bad in (("no lane unit", leg("a", unit=None)), ("no price", leg("a", am=None)),
                   ("no stake", leg("a", ask=None)), ("no order id", leg("")),
                   ("no venue", leg("a", book=""))):
    seed, sm, why = S.build([leg("ok"), bad], [])
    ok(f"one standing order with {label} REFUSES THE WHOLE SEED", seed == [] and bool(why), str(why))
seed, sm, why = S.build([leg("a")], [{"why": "no canonical identity"}])
ok("a row that could not be keyed refuses the whole seed", seed == [] and "could not be keyed" in why)
seed, sm, why = S.build([leg("same"), dict(leg("same"), field="live_rest")], [])
ok("one order recorded under two fields is seeded ONCE", sm["retained"] == 1)
seed, sm, why = S.build([leg("a"), leg("b", "prophetx")], [])
ok("a play already over one unit is reported, and still seeded",
   sm["plays"] == 1 and sm["plays_at_or_over_one_unit"] == 1 and sm["retained"] == 2)

seed, sm, why = S.build([leg("dup-1", "novig", ask=110.0), leg("dup-1", "prophetx", ask=110.0)], [])
ok("the SAME order id on two venues is two orders, not one", sm["retained"] == 2, str(sm))
_st = Store(); R.backfill(_st, seed, "dup test")
ok("and the ledger charges BOTH: two half units leave no capacity",
   R.available(_st, K) == 0.0, str(R.available(_st, K)))
ok("the venue's own order id is kept alongside for audit",
   {l["venue_order_id"] for l in seed} == {"dup-1"} and len({l["order_id"] for l in seed}) == 2)

st = Store()
seed, _, _ = S.build([leg("a")], [])
try:
    R.available(st, K)
    blocked = False
except Exception:
    blocked = True
ok("before the seed, the guard refuses every read", blocked is True)
R.backfill(st, seed, "test seed")
ok("after the seed, a play with an existing unit has NO capacity", R.available(st, K) == 0.0)
ok("and an untouched play has its full unit", R.available(st, "nba|x @ y|total|over") == 1.0)
try:
    R.claim_dispatched(st, K, 100.0, "novig", "cid-new")
    claimed = True
except R.ReservationRefused:
    claimed = False
ok("a NEW Novig order cannot claim a backfilled Novig position", claimed is False)
try:
    R.backfill(st, seed, "again")
    twice = True
except R.ReservationRefused:
    twice = False
ok("the seed cannot be written twice", twice is False)

src = open("review_seed.py", encoding="utf-8").read()
ok("the write is behind an exact confirmation word", 'CONFIRM = "SEED"' in src
   and '!= CONFIRM' in src and src.index("!= CONFIRM") < src.index("R.backfill("))
import re as _re
ok("review_seed never calls a venue order function",
   not _re.search(r"(?<![.\w])(place|kalshi_place|novig_place|pmus_place)\(|px_live\.place", src))
for banned in ("cancel", "EXEC_UNIT_LEDGER\"", "os.environ[\"EXEC", "_commit(", "sendmail"):
    ok(f"review_seed never uses {banned}", banned not in src.replace("places nothing and cancels nothing", "").replace("Places nothing, cancels nothing", ""))
import yaml
d = yaml.safe_load(open(".github/workflows/pr10-seed.yml"))
on = d.get("on") or d[True]
ok("the seed workflow is dispatch-only with read-only repo permissions",
   list(on.keys()) == ["workflow_dispatch"] and d["permissions"] == {"contents": "read"})
ok("its confirm input defaults to empty, so a bare dispatch is a dry run",
   on["workflow_dispatch"]["inputs"]["confirm"]["default"] == "")
ok("and it neither reads nor sets the guard flag",
   "EXEC_UNIT_LEDGER" not in d["jobs"]["run"]["steps"][-1]["env"])

ok("the sweep write is behind its own exact word", 'SWEEP = "SWEEP"' in src
   and "write=(confirm == SWEEP)" in src)
ok("the seed write is read back before it is called written",
   src.index("R.backfill(") < src.index("read-back") and "CONFIRMED" in src)
ok("no time cutoff is used anywhere in the cutover", "cutoff" not in src.lower())

# ------------------------------------------------- one-off repair of a stuck never-submitted leg
import review_unit_reservation as _R
_st = Store(); _st.state["seeded"] = True
_st.state["legs"] = [
    {"key": K, "leg_id": "a", "order_id": "a", "status": "open", "asked_stake": 220.0,
     "american": -110, "unit": 200.0, "actor": "sharp-monitor:live_order:novig",
     "intent_cid": "cid-void", "recorded_only": True},
    {"key": K, "leg_id": "b", "order_id": "b", "status": "open", "asked_stake": 220.0,
     "american": -110, "unit": 200.0, "actor": "sharp-monitor:live_order:novig",
     "intent_cid": "cid-live"}]
_rows = [{"client_id": "cid-void", "voided": True,
          "live_order": {"order_id": "intent-cid-void", "book": "novig", "client_id": "cid-void"}},
         {"client_id": "cid-live",
          "live_order": {"order_id": "venue-9", "book": "novig", "client_id": "cid-live"}}]
_c, _w = S.stuck_never_submitted(_st, _rows)
ok("the repair finds only the leg whose rows prove it was never submitted", _c == ["cid-void"], str(_c))
_R.release_never_submitted(_st, "cid-void", "one-off repair", rows=_rows)
ok("releasing it frees its unit and keeps the leg",
   len(_st.state["legs"]) == 2 and _st.state["legs"][0]["status"] == "void")
ok("the confirmed order's leg is untouched", _st.state["legs"][1]["status"] == "open")
ok("and a second pass finds nothing", S.stuck_never_submitted(_st, _rows)[0] == [])
ok("the repair is behind its own exact word", 'RELEASE = "RELEASE"' in src
   and "confirm == RELEASE" in src)

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
