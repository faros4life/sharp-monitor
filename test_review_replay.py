#!/usr/bin/env python3
"""review_replay: the nested-record reader, the venue evidence and the completeness verdict.

No venue is contacted: the readers are injected. The point of these tests is the two defects the
first version had - reading flat where the records are nested, and calling a leg captured on the
registry's own word.
"""
import json
import review_replay as RR

P, F = [], []


def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


# ---------------------------------------------------------------- 1. nested enumeration
FLAT = {"key": "NBA|LAL @ BOS|total|UNDER", "order_id": "top-1", "status": "open"}
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
ok("venue proof cannot make missing odds into a COMPLETE budget",
   RR.completeness([{"key":"nba|lal @ bos|total|under", "order_id":"x",
                     "unit":200.0, "asked_stake":100.0, "american":None,
                     "venue_class":"OPEN"}], [], {RR.PROVEN:1})[0] == "INCOMPLETE")
ok("venue proof cannot make missing monetary stake into COMPLETE",
   RR.completeness([{"key":"nba|lal @ bos|total|under", "order_id":"x",
                     "unit":200.0, "asked_stake":None, "american":-110,
                     "venue_class":"OPEN"}], [], {RR.PROVEN:1})[0] == "INCOMPLETE")
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
                                       "unit": 300.0},
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
       [INC], "MIN @ SF",
       [dict(ilegs[0], recorded_terminal=True, venue_class="OPEN")])[2]))
ok("a leg with no venue proof is itself a discrepancy",
   any("no venue proof" in d.get("why", "") for d in RR.incident_exposure(
       [INC], "MIN @ SF", [dict(ilegs[0], evidence_class=RR.UNREADABLE)])[2]))
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
                        "asked_stake":220.0, "american":-110, "unit":200.0}}
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

# ------------------------------------------------- deltas on top of the Nov 23 04:30 corrections
# (a) a status that MEANS filled, with a zero quantity, must not be released as a zero fill
ok("a FILLED-meaning status with a zero quantity is a contradiction, not a released zero",
   RR.classify_generic({"status": "executed", "filled_qty": 0, "qty": 50})[0] == "UNKNOWN")
ok("and the reason names the contradiction",
   "contradiction" in RR.classify_generic({"status": "filled", "filled_qty": 0, "qty": 9})[1]["why"])
ok("a CANCELLED order with a read zero is still a real terminal zero",
   RR.classify_generic({"status": "canceled", "filled_qty": 0, "qty": 50})[0]
   == "TERMINAL ZERO FILL")
ok("a partial fill on an order since cancelled is still PARTIAL, not zero",
   RR.classify_generic({"status": "canceled", "filled_qty": 10, "qty": 50})[0]
   == "PARTIALLY FILLED")
import ast as _ast, inspect as _inspect
ok("no ternary in the classifier has identical branches",
   not any(_ast.unparse(n.body) == _ast.unparse(n.orelse) for n in _ast.walk(_ast.parse(
       _inspect.getsource(RR.classify_generic))) if isinstance(n, _ast.IfExp)))

# (b) the incident figure must equal what the guard would charge
import review_unit_reservation as _R
_CK = "nfl|min @ sf|total|under"
_mk = lambda f, oid, vc="OPEN": {
    "key": _CK, "registry_key": "rule|NFL|MIN @ SF|total|UNDER", "field": f, "order_id": oid,
    "book": "novig", "status": "open", "asked_stake": 220.0, "american": -110, "unit": 200.0,
    "venue_class": vc, "evidence_class": RR.PROVEN}
_rows = [{"key": "rule|NFL|MIN @ SF|total|UNDER"}]
_same = [_mk("live_order", "same-1"), _mk("live_rest", "same-1")]
_u = RR.incident_exposure(_rows, "MIN @ SF", _same)[1]
_guard = round(1.0 - _R.remaining_mixed(
    [dict(l, status="open", filled_stake=None) for l in _same], _CK), 3)
ok("one order recorded under two nested fields counts ONCE", _u == 1.0, str(_u))
ok("so the reported figure equals what the guard would actually charge", _u == _guard,
   f"{_u} vs {_guard}")
ok("two DISTINCT orders on one play still count twice",
   RR.incident_exposure(_rows, "MIN @ SF", [_mk("live_order", "a"), _mk("live_more", "b")])[1]
   == 2.0)
ok("a FILLED leg still contributes its share",
   RR.incident_exposure(_rows, "MIN @ SF", [_mk("live_order", "a", "FILLED")])[1] == 1.0)
ok("the incident needle is matched against the real key, so it cannot silently match nothing",
   len(RR.incident_exposure(_rows, "MIN @ SF", [_mk("live_order", "a")])[0]) == 1)

# ------------------------------------------------- Nov 23 run 1: units, ambiguity, the search
import re as _re
_ex = open("executor.py", encoding="utf-8").read()
def _const(name):
    return float(_re.search(rf"^{name} = ([0-9.]+)", _ex, _re.M).group(1))
ok("the lane units mirror executor's constants exactly",
   RR.LANE_UNIT == {"lane1": _const("LIVE_UNIT"), "r1": _const("R1_UNIT"),
                    "board": _const("BOARD_UNIT"), "ncs": _const("NCS_UNIT"),
                    "dogs": _const("DOGS_UNIT"),
                    "all3": _const("ALL3_UNIT")}, str(RR.LANE_UNIT))
# Nov 28: ALL-3 added at $200 ("to win 200", Peter). The label below was already stale - DOGS has
# been $300 since 25 Nov while it still said $100 - so it now states the units it actually asserts.
ok("Lane 1 and DOGS are $300; R1, Board, NCS and ALL-3 are $200",
   RR.LANE_UNIT == {"lane1": 300.0, "r1": 200.0, "board": 200.0, "ncs": 200.0, "dogs": 300.0,
                    "all3": 200.0})
_K = "NFL|MIN @ SF|total|UNDER"
for _row, _want in (({"key": "rule|" + _K}, ("lane1", 300.0)),
                    ({"key": _K, "source": "rules"}, ("lane1", 300.0)),
                    ({"key": "r1|" + _K}, ("r1", 200.0)),
                    ({"key": "board|" + _K, "source": "board"}, ("board", 200.0)),
                    ({"key": _K, "source": "ncs"}, ("ncs", 200.0))):
    ok(f"unit derived from lane metadata: {_row}", RR.lane_unit(_row)[:2] == _want,
       str(RR.lane_unit(_row)))
for _row, _why in (({"key": _K}, "no prefix and no source"),
                   ({"key": _K, "source": "muse"}, "not a live lane"),
                   ({"key": "lane2|" + _K}, "unrecognised key prefix"),
                   ({"key": "zzz|" + _K}, "unrecognised key prefix"),
                   ({"key": "r1|" + _K, "source": "board"}, "lane conflict")):
    _l, _u, _w = RR.lane_unit(_row)
    ok(f"NO unit and no default for {_row}", _u is None and _why in _w, f"{_u} / {_w}")
ok("a stored unit that disagrees with the lane is a conflict, not a tie-break",
   RR.lane_unit({"key": "r1|" + _K}, {"unit": 300.0})[1:] ==
   (None, "unit conflict: stored unit disagrees with the lane"))
ok("a stored unit alone, with no lane, grants nothing",
   RR.lane_unit({"key": _K}, {"unit": 300.0})[1] is None)
ok("the registry projection's `limit` is read as the American price",
   RR.american_of({"limit": -110}) == -110 and RR.american_of({"limit": 0.52}) is None)

# the run-1 shape: an order record with NO unit field, as the registry really stores it
_real = lambda key, src=None, oid="o1": dict(
    {"key": key, "decided_utc": "2026-11-22T20:00:00Z",
     "live_order": {"order_id": oid, "book": "kalshi", "status": "placed",
                    "asked_stake": 220.0, "limit": -110, "filled_stake": 220.0}},
    **({"source": src} if src else {}))
_kal = lambda oid: ({"status": "executed", "filled_qty": 9, "qty": 9}, "")
def _run(rows):
    lg, un, _ = RR.backfill_candidates(rows)
    lg, ct = RR.venue_evidence(lg, novig=novig_ok, kalshi=_kal, pmus=pmus_ok, px=px_ok)
    return lg, RR.completeness(lg, un, ct)
_lg, (_v, _w) = _run([_real("r1|" + _K)])
ok("a record with no unit field gets its unit from the lane and can be COMPLETE",
   _v == "COMPLETE" and _lg[0]["unit"] == 200.0 and _lg[0]["american"] == -110, f"{_v}: {_w}")
for _label, _rows in (("no lane metadata", [_real(_K)]),
                      ("an unknown source", [_real(_K, "muse")]),
                      ("conflicting lanes", [_real("r1|" + _K, "board")]),
                      ("one ambiguous leg among good ones",
                       [_real("r1|" + _K, oid="a"), _real(_K, oid="b")])):
    _lg, (_v, _w) = _run(_rows)
    ok(f"historical exposure with {_label} cannot be marked COMPLETE", _v == "INCOMPLETE",
       f"{_v}: {_w}")
ok("and the verdict says WHY the unit is missing, by reason and count",
   "lane unknown" in _run([_real(_K)])[1][1], _run([_real(_K)])[1][1])
_lg, (_v, _w) = _run([{"key": "r1|" + _K, "live_order": {
    "order_id": "p", "book": "kalshi", "status": "placed", "asked_stake": 220.0}}])
ok("a leg with a unit but no readable price is still INCOMPLETE", _v == "INCOMPLETE", _w)

# diagnostics: counts and reasons only
_dl, _du, _ = RR.backfill_candidates([_real("r1|" + _K, oid="SECRET-ID-1"), _real(_K, oid="b")])
_dl, _ = RR.venue_evidence(_dl, novig=novig_ok, kalshi=lambda o: (None, "status 503 SECRET"),
                           pmus=pmus_ok, px=px_ok)
_dg = RR.diagnostics(_dl)
ok("diagnostics split the unproven legs by book, class and reason", len(_dg["unproven"]) >= 1
   and all(k.startswith("kalshi / ") for k in _dg["unproven"]), str(_dg["unproven"]))
ok("and carry no order id, key or raw venue text", "SECRET" not in json.dumps(_dg)
   and "MIN @ SF" not in json.dumps(_dg), json.dumps(_dg)[:200])
ok("a reason outside the fixed vocabulary is coded 'other', never echoed",
   RR.reason_code({"evidence": {"why": "weird SECRET-ID text"}}) == "other (see private mail)")
ok("field NAMES are reported, never values", set(_dg["fields"]) >= {"asked_stake", "limit"})

# the incident search no longer hangs on one literal string
_al = RR.parse_aliases("Minnesota|Vikings|MIN;San Francisco|49ers|SF")
ok("aliases parse into one group per team", len(_al) == 2 and "49ers" in _al[1])
ok("full team names match where the literal term does not",
   RR.matches_incident({"game": "Minnesota Vikings @ San Francisco 49ers"}, "MIN @ SF", _al))
ok("reversed order and another separator still match",
   RR.matches_incident({"label": "49ers vs Vikings"}, "MIN @ SF", _al))
ok("one team alone does not match", not RR.matches_incident({"g": "Vikings @ Bears"}, "MIN @ SF", _al))
ok("a short code only matches as a whole word",
   not RR.matches_incident({"note": "minimum stake sfx"}, "", RR.parse_aliases("MIN;SF")))
_vs = RR.venue_side_search("MIN @ SF", _al, "2026-11-22",
    novig=lambda: (({"c9": {"client_id": "c9", "label": "Vikings at 49ers",
                             "placed_utc": "2026-11-22T21:00:00Z"}}, {}), "ok"),
    px=lambda: ({"p9": [{"order_id": "p9", "event": "Minnesota Vikings v San Francisco 49ers",
                         "created": "2026-11-22T20:10:00Z"}]}, "ok"))
ok("venue-side search finds an incident order the registry never recorded",
   len(_vs["novig"]["matching"]) == 1 and len(_vs["prophetx"]["matching"]) == 1)
ok("and counts that day's venue records", _vs["novig"]["on_date"] == 1 and _vs["prophetx"]["on_date"] == 1)
ok("venues with no history read are reported NOT SEARCHED, not clean",
   _vs["kalshi"]["readable"] is False and _vs["polymarket_us"]["readable"] is False)
_vd = RR.venue_side_search("MIN @ SF", _al, "2026-11-22",
                           novig=lambda: ((None, None), "snapshot unreadable"), px=px_dead)
ok("an unreadable venue is NOT SEARCHED, never zero records",
   _vd["novig"]["readable"] is False and _vd["prophetx"]["readable"] is False)
ok("zero matched legs is printed as NOT FOUND, never as 0 units",
   "not evidence of zero exposure" in src and "NOT FOUND" in src)
_mainlog = src.split("# PUBLIC LOG")[1].split("body = [")[0]
ok("the public log still prints no id, key or amount",
   not any(x in _mainlog for x in ("l['key']", "order_id\"]", "asked_stake\"]", "json.dumps(")))

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
