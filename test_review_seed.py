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
ok("open and FILLED orders are both seeded", why is None and sm["seeded"] == 2, f"{why} {sm}")
ok("every seeded leg is held at its FULL asked stake as an open commitment",
   all(l["status"] == "open" and l["asked_stake"] in (220.0, 330.0) for l in seed))
seed, sm, why = S.build([leg("a", vc="TERMINAL ZERO FILL")], [])
ok("only a venue-PROVEN zero fill is left out", why is None and sm["seeded"] == 0
   and sm["skipped_proven_zero"] == 1)
seed, sm, why = S.build([leg("a", vc="TERMINAL ZERO FILL", ec=RR.NO_RECORD)], [])
ok("a terminal zero WITHOUT venue proof is seeded in full", sm["seeded"] == 1)
seed, sm, why = S.build([leg("a", vc="UNKNOWN", ec=RR.NO_RECORD)], [])
ok("an order whose fill was never read is seeded in full and counted as unproven",
   why is None and sm["seeded"] == 1 and sm["unproven_seeded_in_full"] == 1)
for label, bad in (("no lane unit", leg("a", unit=None)), ("no price", leg("a", am=None)),
                   ("no stake", leg("a", ask=None)), ("no order id", leg("")),
                   ("no venue", leg("a", book=""))):
    seed, sm, why = S.build([leg("ok"), bad], [])
    ok(f"one standing order with {label} REFUSES THE WHOLE SEED", seed == [] and bool(why), str(why))
seed, sm, why = S.build([leg("a")], [{"why": "no canonical identity"}])
ok("a row that could not be keyed refuses the whole seed", seed == [] and "could not be keyed" in why)
seed, sm, why = S.build([leg("same"), dict(leg("same"), field="live_rest")], [])
ok("one order recorded under two fields is seeded ONCE", sm["seeded"] == 1)
seed, sm, why = S.build([leg("a"), leg("b", "prophetx")], [])
ok("a play already over one unit is reported, and still seeded",
   sm["plays"] == 1 and sm["plays_at_or_over_one_unit"] == 1 and sm["seeded"] == 2)

seed, sm, why = S.build([leg("dup-1", "novig", ask=110.0), leg("dup-1", "prophetx", ask=110.0)], [])
ok("the SAME order id on two venues is two orders, not one", sm["seeded"] == 2, str(sm))
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

# ------------------------------------------------- catch-up: the seed-to-recording gap
CUT = "2026-11-23T11:00:00Z"


def dated(oid, when, **kw):
    l = leg(oid, **kw)
    l["decided_utc"] = when
    return l


st = Store()
seed0, _, _ = S.build([dated("old-1", "2026-11-22T20:00:00Z")], [])
R.backfill(st, seed0, "seed")
inv, _, _ = S.build([dated("old-1", "2026-11-22T20:00:00Z"),
                     dated("gap-1", "2026-11-23T10:40:00Z", book="prophetx", ask=110.0,
                           key="nba|x @ y|side|x"),
                     dated("gap-2", "2026-11-23T10:55:00Z", vc="UNKNOWN", ec=RR.NO_RECORD,
                           key="nba|x @ y|side|x", ask=110.0),
                     dated("late-1", "2026-11-23T11:05:00Z", key="nba|p @ q|total|over")], [])
c = S.catch_up(st, inv, CUT, write=False)
ok("catch-up dry run counts the gap and writes nothing",
   c["added"] == 2 and c["already_in_ledger"] == 1 and c["after_cutoff_skipped"] == 1
   and len(st.state["legs"]) == 1, str(c))
ok("before the catch-up, a play with a gap order still reads a full unit free - the hole",
   R.available(st, "nba|x @ y|side|x") == 1.0)
c = S.catch_up(st, inv, CUT, write=True)
ok("the catch-up writes exactly the gap orders", c["added"] == 2 and len(st.state["legs"]) == 3)
ok("an order placed during the transition now counts toward the one-unit limit",
   R.available(st, "nba|x @ y|side|x") == 0.0, str(R.available(st, "nba|x @ y|side|x")))
ok("including one whose fill status has not come back - held at its full asked stake",
   any(l["order_id"] == "novig|gap-2" and l["status"] == "open" and l["asked_stake"] == 110.0
       for l in st.state["legs"]))
ok("an order placed AFTER recording began is left to the executor's own record",
   R.available(st, "nba|p @ q|total|over") == 1.0)
c = S.catch_up(st, inv, CUT, write=True)
ok("running the catch-up again adds nothing", c["added"] == 0 and len(st.state["legs"]) == 3)
und, _, _ = S.build([leg("undated-1", key="nba|u @ v|total|over")], [])
c = S.catch_up(st, und, CUT, write=True)
ok("an order with NO timestamp is added (over-count is the safe side) and reported",
   c["added"] == 1 and c["added_undated"] == 1)
try:
    S.catch_up(Store(), inv, CUT, write=True)
    unseeded = True
except Exception:
    unseeded = False
ok("catch-up refuses an unseeded ledger", unseeded is False)
for bad in ("", "yesterday", None):
    try:
        S.catch_up(st, inv, bad, write=True)
        r = True
    except Exception:
        r = False
    ok(f"catch-up refuses without a readable cutoff ({bad!r})", r is False)
try:
    R.claim_dispatched(st, "nba|x @ y|side|x", 50.0, "novig", "new-cid")
    c2 = True
except R.ReservationRefused:
    c2 = False
ok("a new Novig order cannot claim a caught-up position", c2 is False)
ok("the catch-up write is behind its own exact word", 'CATCHUP = "CATCHUP"' in src
   and "write=(confirm == CATCHUP)" in src)

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
