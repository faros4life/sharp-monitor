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
NESTED = {"key": "board|NBA|LAL @ BOS|total|UNDER",
          "live_order": {"order_id": "c1", "client_id": "c1", "book": "novig", "status": "open",
                         "asked_stake": 220.0, "american": -110, "unit": 200.0},
          "live_rest": {"order_id": "a2", "client_id": "c2", "book": "kalshi", "status": "open",
                        "asked_stake": 100.0, "american": 120, "unit": 200.0},
          "live_more": [{"order_id": "a3", "client_id": "c3", "book": "kalshi",
                         "status": "filled", "asked_stake": 90.0, "american": -110,
                         "unit": 200.0},
                        {"order_id": "a4", "client_id": "c4", "book": "polymarket_us",
                         "status": "open", "asked_stake": 50.0, "american": -105, "unit": 200.0}]}

ok("live_more is read as a LIST, not dict-accessed", len(RR.legs_from(NESTED)) == 4,
   str(len(RR.legs_from(NESTED))))
ok("all three nested fields are enumerated",
   {f for f, _ in RR.legs_from(NESTED)} == {"live_order", "live_rest", "live_more"})
ok("a row whose order records are only at the TOP level yields no legs", RR.legs_from(FLAT) == [])

legs, unreadable, terminal = RR.backfill_candidates([NESTED])
ok("the terminal nested leg is still COUNTED terminal", terminal == 1, str(terminal))
ok("but it is NOT skipped: a filled order is verified like any other",
   len(legs) == 4 and sum(1 for l in legs if l["recorded_terminal"]) == 1, str(len(legs)))
ok("each outstanding leg carries the field it came from",
   all(l.get("field") in RR.NESTED_FIELDS for l in legs))

_l, _u, _t = RR.backfill_candidates([FLAT])
ok("a top-level-only row is reported UNREADABLE, never silently dropped",
   len(_u) == 1 and not _l and _t == 0, f"{len(_u)}/{len(_l)}/{_t}")
ok("and the reason names the row shape, so the two remedies stay apart",
   "no nested order record" in _u[0]["why"])

_l2, _u2, _ = RR.backfill_candidates([{"key": "r1|NBA|LAL @ BOS|total|UNDER", "live_order": {
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
    # a3 is the recorded-filled leg; the venue agrees it is executed and fully filled
    if oid == "a3":
        return {"status": "executed", "filled_qty": 90, "qty": 90}, ""
    return {"status": "resting", "filled_qty": 0, "qty": 83}, ""


def kalshi_dead(oid):
    return None, "status 503"


def pmus_ok(oid):
    return {"status": "OPEN", "cumQuantity": 0, "quantity": 48}, ""


def pmus_dead(oid):
    return None, "HTTPError"


def px_ok():
    return {"px-1": [{"order_id": "px-1", "stake": 1}]}, "ok (1 order id with trades)"


def px_dead():
    return None, "px_live unavailable: KeyError"


base = [dict(l) for l in legs]
got, counts = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_ok,
                                pmus=pmus_ok, px=px_ok)
ok("every leg is proven when the venues answer", counts.get(RR.PROVEN) == 4, str(counts))
ok("the recorded-filled leg is proven FILLED by the venue, not taken on our word",
   any(l["order_id"] == "a3" and l.get("venue_class") == "FILLED" for l in got),
   str([(l["order_id"], l.get("venue_class")) for l in got]))

got, counts = RR.venue_evidence([dict(l) for l in base], novig=no_novig, kalshi=kalshi_ok,
                                pmus=pmus_ok, px=px_ok)
ok("an unreadable Novig snapshot leaves that leg UNREADABLE, not zero-filled",
   counts.get(RR.UNREADABLE) == 1, str(counts))
ok("and the reason is carried through verbatim",
   any("no registry token" in str((l.get("evidence") or {}).get("why")) for l in got))

got, counts = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_dead,
                                pmus=pmus_dead, px=px_ok)
ok("a venue that will not answer blocks every one of its legs",
   counts.get(RR.UNREADABLE) == 3, str(counts))

got, counts = RR.venue_evidence(
    [{"key": "k", "book": "hardrock", "order_id": "p1", "unit": 200.0}],
    novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
ok("a book with no read-back path is NO READER, not quietly proven",
   counts.get(RR.NO_READER) == 1, str(counts))

# ProphetX: trades ARE the fill evidence, and absence of one proves nothing
_g, _c = RR.venue_evidence([{"key": "k", "book": "prophetx", "order_id": "px-1", "unit": 300.0}],
                           novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
ok("a ProphetX order with a trade record is PROVEN filled", _c.get(RR.PROVEN) == 1, str(_c))
_g, _c = RR.venue_evidence([{"key": "k", "book": "prophetx", "order_id": "px-9", "unit": 300.0}],
                           novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
ok("a ProphetX order with NO trade is NO VENUE RECORD, never a proven zero",
   _c.get(RR.NO_RECORD) == 1, str(_c))
_g, _c = RR.venue_evidence([{"key": "k", "book": "prophetx", "order_id": "px-1", "unit": 300.0}],
                           novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_dead)
ok("an unreadable ProphetX trade list is UNREADABLE, never zero exposure",
   _c.get(RR.UNREADABLE) == 1, str(_c))

# the shared classifier: the Nov 19 Novig lesson, applied to the other venues
ok("a venue body with NO filled quantity is UNKNOWN, not a zero fill",
   RR.classify_generic({"status": "canceled"})[0] == "UNKNOWN")
ok("a cancelled order with a READ zero is terminal",
   RR.classify_generic({"status": "canceled", "filled_qty": 0, "qty": 50})[0]
   == "TERMINAL ZERO FILL")
ok("a partial fill is PARTIAL, not FILLED",
   RR.classify_generic({"status": "resting", "filled_qty": 10, "qty": 50})[0]
   == "PARTIALLY FILLED")
ok("a venue status this reader does not know is UNKNOWN",
   RR.classify_generic({"status": "quantum", "filled_qty": 0, "qty": 5})[0] == "UNKNOWN")

got, counts = RR.venue_evidence([{"key": "k", "book": "novig", "unit": 200.0}],
                                novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
ok("a leg with no identifier is NO VENUE RECORD", counts.get(RR.NO_RECORD) == 1, str(counts))

got, counts = RR.venue_evidence(
    [{"key": "k", "book": "novig", "client_id": "not-in-snapshot", "unit": 200.0,
      "asked_stake": 100.0, "american": -110, "status": "open"}],
    novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
ok("a Novig id absent from the snapshot is NOT proof of zero fills",
   counts.get(RR.NO_RECORD) == 1, str(counts))


# ---------------------------------------------------------------- 3. completeness is bounded
ok("no venue evidence at all reads UNPROVEN, never COMPLETE",
   RR.completeness(base, [], None)[0] == "UNPROVEN")
ok("an unclassifiable row blocks the verdict",
   RR.completeness(base, [{"why": "x"}], {RR.PROVEN: 4})[0] == "INCOMPLETE")
ok("a venue-PROVEN terminal leg needs no unit, so settled history cannot hold the verdict hostage",
   RR.completeness([{"unit": None, "venue_class": "TERMINAL ZERO FILL"}], [],
                   {RR.PROVEN: 1})[0] == "COMPLETE")
ok("a leg with no lane unit blocks the verdict",
   RR.completeness([{"unit": None}], [], {RR.PROVEN: 1})[0] == "INCOMPLETE")
ok("one unproven leg among many blocks the verdict",
   RR.completeness(base, [], {RR.PROVEN: 3, RR.UNREADABLE: 1})[0] == "INCOMPLETE")
ok("and an unreadable venue is reported as such, never as zero exposure",
   "venue unreadable" in RR.completeness(base, [], {RR.UNREADABLE: 1})[1].lower(),
   RR.completeness(base, [], {RR.UNREADABLE: 1})[1])
_std = [dict(l, unit=200.0) for l in base]
v, why = RR.completeness(_std, [], {RR.PROVEN: 4})
ok("COMPLETE only with a unit and venue evidence on every leg", v == "COMPLETE", f"{v}: {why}")
ok("and the COMPLETE wording says what was actually checked, and how much still stands",
   "against their venue" in why and "still standing" in why, why)
ok("an empty leg list is COMPLETE and says so",
   RR.completeness([], [], {})[1].startswith("no order records at all"))


# ---------------------------------------------------------------- 4. the replay is honest about itself
ok("the replay matches NESTED order ids, which is the only place they appear",
   len(RR.min_at_sf([NESTED], "a4")) == 1)
ok("a Novig leg is looked up by the registry's order_id, which IS Novig's client id",
   RR.venue_evidence([{"key": "k", "book": "novig", "order_id": "c1", "unit": 200.0,
                       "asked_stake": 110.0, "american": -110, "status": "open"}],
                     novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok,
                     px=px_ok)[1].get(RR.PROVEN) == 1)
ok("a Kalshi leg is looked up by its VENUE order id, not a client id",
   RR.venue_evidence([{"key": "k", "book": "kalshi", "order_id": "a2", "client_id": "c2",
                       "unit": 200.0}], novig=novig_ok,
                     kalshi=lambda o: (({"status": "resting", "filled_qty": 0, "qty": 9}, "")
                                       if o == "a2" else (None, "wrong id")), pmus=pmus_ok,
                     px=px_ok)[1].get(RR.PROVEN) == 1)
ok("an empty needle replays nothing rather than everything", RR.min_at_sf([NESTED], "") == [])
src = open("review_replay.py", encoding="utf-8").read()
ok("the mail says plainly that the replay is a registry search, not a venue reconciliation",
   "not a venue-side reconciliation" in src)


# ---------------------------------------------------------------- 5. delivery cannot be half-valid
import csv as _csv
import io as _io

proven, _ = RR.venue_evidence([dict(l) for l in base], novig=novig_ok, kalshi=kalshi_ok,
                              pmus=pmus_ok, px=px_ok)
text = RR._csv(proven)
parsed = list(_csv.DictReader(_io.StringIO(text)))
ok("the backfill list is delivered as parseable CSV", len(parsed) == 4, str(len(parsed)))
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

# ---------------------------------------------------------------- 7. the incident report
INC = {"key": "rule|NFL|MIN @ SF|total|UNDER", "live_order": {"order_id": "c1", "client_id": "c1", "book": "novig",
                                       "status": "open", "asked_stake": 110.0, "american": -110,
                                       "unit": 200.0},
       "live_more": [{"order_id": "px-1", "book": "prophetx", "status": "filled",
                      "asked_stake": 300.0, "american": -110, "unit": 300.0}]}
ilegs, _iu, _it = RR.backfill_candidates([INC])
ilegs, _ic = RR.venue_evidence(ilegs, novig=novig_ok, kalshi=kalshi_ok, pmus=pmus_ok, px=px_ok)
rep, units, disc = RR.incident_exposure([INC], "MIN @ SF", ilegs)
ok("the incident report covers BOTH venues' legs", len(rep) == 2, str(len(rep)))
ok("Novig and ProphetX are both named", {r["book"] for r in rep} == {"novig", "prophetx"})
ok("combined exposure is reported in UNITS", isinstance(units, float), str(units))
ok("and it uses the reservation protocol's own per-leg fraction, so the two cannot drift",
   "leg_fraction" in open("review_replay.py", encoding="utf-8").read())
ok("a registry-terminal leg the venue still shows live is flagged as a discrepancy",
   any("still shows it live" in d.get("why", "") for d in RR.incident_exposure(
       [INC], "MIN@SF",
       [dict(ilegs[0], recorded_terminal=True, venue_class="OPEN")])[2]))
ok("a leg with no venue proof is itself a discrepancy",
   any("no venue proof" in d.get("why", "") for d in RR.incident_exposure(
       [INC], "MIN@SF", [dict(ilegs[0], evidence_class=RR.UNREADABLE)])[2]))
ok("an unreadable unit makes combined exposure NOT COMPUTABLE rather than a guess",
   RR.incident_exposure([INC], "MIN @ SF",
                        [dict(ilegs[0], unit=None)])[1] is None)
ok("no needle means no incident report at all", RR.incident_exposure([INC], "", ilegs) == ([], None, []))
log_part = src.split("# PUBLIC LOG")[1].split("body = [")[0]
ok("the public log carries UNITS, never a dollar figure",
   "unit(s)" in log_part and "asked_stake" not in log_part and "filled_usd" not in log_part)
ok("the mail says a clean discrepancy list is not a claim that none exists",
   "not a claim that none exists" in src)
ok("ProphetX auth failure yields NO evidence, never an assumed zero",
   "no fill evidence" in src and "credentials absent or refused" in src)
ok("the only POST is the ProphetX credential exchange, and it is documented as such",
   "the only POST anywhere in this script" in src)
ok("it does not claim a secret it never reads", "TRACKER_PASSPHRASE" not in src.replace(
   "it is not given TRACKER_PASSPHRASE", ""))
ok("and nothing here touches the pause, stop or bot-order registry controls",
   not any(x in src for x in ("auto_pause(", "stop_state(", "set_bot_orders(", "add_bot_order(")))



# ---------------------------------------------------------------- 8. key normalization and terminal-fill regressions
ok("lane prefixes map to the exact same canonical budget",
   RR.canonical_registry_key("r1|NBA|LAL @ BOS|total|UNDER")
   == RR.canonical_registry_key("board|NBA|LAL @ BOS|total|UNDER"))
ok("alternate total prices and lines do not create separate budgets",
   RR.canonical_registry_key("NBA|LAL @ BOS|total|UNDER")
   == RR.canonical_registry_key("r1|NBA|LAL @ BOS|total|UNDER"))
ok("invalid source keys fail rather than creating a separate budget",
   len(RR.backfill_candidates([{"key":"unknown", "live_order":{
       "order_id":"x", "book":"novig", "status":"open", "asked_stake":100,
       "american":-110, "unit":200}}])[1]) == 1)
_probe = {"key":"r1|NFL|MIN @ SF|total|UNDER",
          "live_order":{"order_id":"px-filled", "book":"prophetx", "status":"filled",
                        "asked_stake":330.0, "american":-110, "unit":300.0}}
_probe_legs, _probe_bad, _ = RR.backfill_candidates([_probe])
ok("a lane-tagged filled order is exported with the shared canonical key",
   len(_probe_legs) == 1 and _probe_legs[0]["key"] ==
   RR.canonical_registry_key("NFL|MIN @ SF|total|UNDER"))
_probe_proven = [dict(_probe_legs[0], evidence_class=RR.PROVEN,
                      venue_class="FILLED", evidence={"trade_records":1})]
_pr, _units, _d = RR.incident_exposure([_probe], "MIN @ SF", _probe_proven)
ok("confirmed FILLED terminal order still consumes capacity",
   len(_pr) == 1 and abs(_units - 1.0) < 1e-9, str(_units))
_probe_zero = [dict(_probe_legs[0], evidence_class=RR.PROVEN,
                    venue_class="TERMINAL ZERO FILL", evidence={"filled":0})]
_pr, _zero_units, _d = RR.incident_exposure([_probe], "MIN @ SF", _probe_zero)
ok("only proven zero-fill terminal releases capacity",
   _zero_units == 0.0, str(_zero_units))
_pr, _uncertain, _d = RR.incident_exposure([_probe], "MIN @ SF",
  [dict(_probe_legs[0], evidence_class=RR.NO_RECORD, venue_class="UNKNOWN")])
ok("unverified venue record yields NOT COMPUTABLE instead of falsely zero",
   _uncertain is None, str(_uncertain))

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
