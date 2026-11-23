#!/usr/bin/env python3
"""review_replay: the nested-record reader, the venue evidence and the completeness verdict.

No venue is contacted: the readers are injected. The point of these tests is the two defects the
first version had - reading flat where the records are nested, and calling a leg captured on the
registry's own word.
"""
import review_replay as RR

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


# ---------------------------------------------------------------- 1. nested enumeration
FLAT = {"key": "k1", "order_id": "top-1", "status": "open"}
NESTED = {"key": "k2",
          "live_order": {"order_id": "c1", "client_id": "c1", "book": "novig", "status": "open",
                         "asked_stake": 220.0, "american": -110, "unit": 200.0},
          "live_rest": {"order_id": "a2", "client_id": "c2", "book": "kalshi", "status": "open",
                        "asked_stake": 100.0, "american": 120, "unit": 200.0},
          "live_more": [{"order_id": "a3", "client_id": "c3", "book": "kalshi", "status": "filled"},
                        {"order_id": "a4", "client_id": "c4", "book": "polymarket_us",
                         "status": "open", "asked_stake": 50.0, "american": -105, "unit": 200.0}]}

ok("live_more is read as a LIST, not dict-accessed", len(RR.legs_from(NESTED)) == 4,
   str(len(RR.legs_from(NESTED))))
ok("all three nested fields are enumerated",
   {f for f, _ in RR.legs_from(NESTED)} == {"live_order", "live_rest", "live_more"})
ok("a row whose order records are only at the TOP level yields no legs", RR.legs_from(FLAT) == [])

legs, unreadable, terminal = RR.backfill_candidates([NESTED])
ok("the terminal nested leg is counted terminal, not outstanding", terminal == 1, str(terminal))
ok("three nested legs come back outstanding", len(legs) == 3, str(len(legs)))
ok("each outstanding leg carries the field it came from",
   all(l.get("field") in RR.NESTED_FIELDS for l in legs))

_l, _u, _t = RR.backfill_candidates([FLAT])
ok("a top-level-only row is reported UNREADABLE, never silently dropped",
   len(_u) == 1 and not _l and _t == 0, f"{len(_u)}/{len(_l)}/{_t}")
ok("and the reason names the row shape, so the two remedies stay apart",
   "no nested order record" in _u[0]["why"])

_l2, _u2, _ = RR.backfill_candidates([{"key": "k3", "live_order": {
    "order_id": "x", "book": "novig", "status": "weird_state"}}])
ok("an unknown recorded status is UNREADABLE, not assumed open or closed",
   not _l2 and len(_u2) == 1 and "weird_state" in _u2[0]["why"])


# ---------------------------------------------------------------- 2. venue evidence
def no_novig():
    return (None, None), "orders snapshot: no registry token"


def novig_ok():
    return ({"c1": {"client_id": "c1", "order_id": "v1", "status": "OPEN", "qty": 200,
                    "filled_qty": 0, "fill_read": True, "price": 55}}, {}), "ok"


def kalshi_ok(oid):
    return {"status": "resting", "filled_qty": 0, "qty": 83}, ""


def kalshi_dead(oid):
    return None, "status 503"


def pmus_ok(oid):
    return {"status": "OPEN", "cumQuantity": 0, "quantity": 48}, ""


def pmus_dead(oid):
    return None, "HTTPError"


base = [dict(l) for l in legs]
got, counts = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_ok,
                                pmus=pmus_ok)
ok("every leg is proven when all three venues answer", counts.get(RR.PROVEN) == 3, str(counts))

got, counts = RR.venue_evidence([dict(l) for l in base], novig=no_novig, kalshi=kalshi_ok,
                                pmus=pmus_ok)
ok("an unreadable Novig snapshot leaves that leg UNREADABLE, not zero-filled",
   counts.get(RR.UNREADABLE) == 1, str(counts))
ok("and the reason is carried through verbatim",
   any("no registry token" in str((l.get("evidence") or {}).get("why")) for l in got))

got, counts = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_dead,
                                pmus=pmus_dead)
ok("a venue that will not answer blocks both of its legs", counts.get(RR.UNREADABLE) == 2,
   str(counts))

got, counts = RR.venue_evidence(
    [{"key": "k", "book": "prophetx", "order_id": "p1", "unit": 200.0}],
    novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok)
ok("a book with no read-back path is NO READER, not quietly proven",
   counts.get(RR.NO_READER) == 1, str(counts))

got, counts = RR.venue_evidence([{"key": "k", "book": "novig", "unit": 200.0}],
                                novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok)
ok("a leg with no identifier is NO VENUE RECORD", counts.get(RR.NO_RECORD) == 1, str(counts))

got, counts = RR.venue_evidence(
    [{"key": "k", "book": "novig", "client_id": "not-in-snapshot", "unit": 200.0,
      "asked_stake": 100.0, "american": -110, "status": "open"}],
    novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok)
ok("a Novig id absent from the snapshot is NOT proof of zero fills",
   counts.get(RR.NO_RECORD) == 1, str(counts))


# ---------------------------------------------------------------- 3. completeness is bounded
ok("no venue evidence at all reads UNPROVEN, never COMPLETE",
   RR.completeness(base, [], None)[0] == "UNPROVEN")
ok("an unclassifiable row blocks the verdict",
   RR.completeness(base, [{"why": "x"}], {RR.PROVEN: 3})[0] == "INCOMPLETE")
ok("a leg with no lane unit blocks the verdict",
   RR.completeness([{"unit": None}], [], {RR.PROVEN: 1})[0] == "INCOMPLETE")
ok("one unproven leg among many blocks the verdict",
   RR.completeness(base, [], {RR.PROVEN: 2, RR.UNREADABLE: 1})[0] == "INCOMPLETE")
v, why = RR.completeness(base, [], {RR.PROVEN: 3})
ok("COMPLETE only with a unit and venue evidence on every leg", v == "COMPLETE", f"{v}: {why}")
ok("and the COMPLETE wording says what was actually checked", "against its venue" in why)
ok("an empty outstanding list is COMPLETE and says so",
   RR.completeness([], [], {})[1].startswith("no outstanding legs"))


# ---------------------------------------------------------------- 4. the replay is honest about itself
ok("the replay matches NESTED order ids, which is the only place they appear",
   len(RR.min_at_sf([NESTED], "a4")) == 1)
ok("a Novig leg is looked up by the registry's order_id, which IS Novig's client id",
   RR.venue_evidence([{"key": "k", "book": "novig", "order_id": "c1", "unit": 200.0,
                       "asked_stake": 110.0, "american": -110, "status": "open"}],
                     novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok)[1].get(RR.PROVEN) == 1)
ok("a Kalshi leg is looked up by its VENUE order id, not a client id",
   RR.venue_evidence([{"key": "k", "book": "kalshi", "order_id": "a2", "client_id": "c2",
                       "unit": 200.0}], novig=novig_ok,
                     kalshi=lambda o: (({"status": "resting"}, "") if o == "a2"
                                       else (None, "wrong id")), pmus=pmus_ok
                     )[1].get(RR.PROVEN) == 1)
ok("an empty needle replays nothing rather than everything", RR.min_at_sf([NESTED], "") == [])
src = open("review_replay.py", encoding="utf-8").read()
ok("the mail says plainly that the replay is a registry search, not a venue reconciliation",
   "not a venue-side reconciliation" in src)


# ---------------------------------------------------------------- 5. delivery cannot be half-valid
import csv as _csv
import io as _io

proven, _ = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_ok,
                              pmus=pmus_ok)
text = RR._csv(proven)
parsed = list(_csv.DictReader(_io.StringIO(text)))
ok("the backfill list is delivered as parseable CSV", len(parsed) == 3, str(len(parsed)))
ok("with the evidence class on every row",
   all(r["evidence_class"] == RR.PROVEN for r in parsed))
ok("the body does NOT carry the truncated JSON list that broke clv_report",
   "BACKFILL LIST" not in src and "pr10_backfill_legs.csv" in src)
ok("the public log prints counts only - no key, id or dollar figure",
   all(s not in src.split("def main")[1].split("body = [")[0]
       for s in ("asked_stake", "order_id", "leg['key']")))


# ---------------------------------------------------------------- 6. still read-only
for forbidden in ("px_live.place", "book_live.kalshi_place", "book_live.novig_place",
                  "book_live.pmus_place", "pmus_cancel", "_put_with_sha", "put_order"):
    ok(f"review_replay never calls {forbidden}", forbidden not in src)
ok("and never reads or writes the ledger flag", "EXEC_UNIT_LEDGER" not in src.replace(
    "it never touches EXEC_UNIT_LEDGER", "").replace("EXEC_UNIT_LEDGER untouched", ""))

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
