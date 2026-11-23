#!/usr/bin/env python3
"""REVIEW ONLY, READ-ONLY. The two private-data tasks blocking draft PR #10, run inside Actions.

WHY THIS EXISTS. Two preconditions for the shared unit ledger need data nobody can hand to a chat
session: the MIN @ SF reconciliation, and proof that the backfill list of already-outstanding
orders is complete. Both need the registry token and the venue read keys, which live in Actions and
nowhere else - so this runs there, as a dispatch-only workflow, and neither the secrets nor the
records ever leave that run. It does NOT read the tracker, so it is not given TRACKER_PASSPHRASE. The public Actions log gets COUNTS ONLY; the detail goes to the
private Bets inbox, the same split every other reporter in this repo uses.

IT PLACES NOTHING AND CANCELS NOTHING. It reads the registry, the runner's venue snapshots and each
venue's own order-read endpoint, and emails what it found. No order path is imported, no setting is
read or written, and it never touches EXEC_UNIT_LEDGER.

INVENTED RECORDS ARE THE FAILURE MODE HERE, so: every figure below is read or it is reported
MISSING. There is no fallback, no estimate and no sample value. A row it cannot parse is counted in
an "unreadable" bucket and named in the private mail, never dropped and never guessed.

TWO DEFECTS THE FIRST VERSION OF THIS FILE HAD (Nov 23). Both are CLAUDE.md's opening rule - when a
measurement returns nothing, the measurement is the first suspect:

  1. It read the order id off the TOP LEVEL of a registry row. The order records are NESTED, under
     live_order, live_rest and live_more - as registry._rid() has always descended, and as
     kalshi_reconcile.py enumerates. A row's top-level order_id is empty, so the outstanding count
     would have come back near zero and the natural explanation - "there is nothing outstanding" -
     would have been the reader, not the world. The enumerator below is the proven one, including
     its normalisation of live_more as a LIST while the other two are single dicts.
  2. It called a leg "outstanding" from the registry's own status alone and never asked a venue.
     A registry status is what we believed when we wrote it; the venue holds what actually happened.
     Evidence now comes from the venue for every leg, and a leg with no venue evidence is NOT
     counted as captured - it blocks the COMPLETE verdict by design.
"""
import csv
import io
import json
import re
import os
import sys
from datetime import datetime, timezone

LEDGER_STATES_OPEN = ("open", "placed", "partially_filled", "submitted", "resting", "working")
LEDGER_STATES_TERMINAL = ("filled", "settled", "canceled", "cancelled", "expired", "void", "refused")

NESTED_FIELDS = ("live_order", "live_rest", "live_more")

# Evidence classes. PROVEN means a venue answered about THIS order id. The rest block activation.
PROVEN, NO_RECORD, UNREADABLE, NO_READER = ("PROVEN", "NO VENUE RECORD", "VENUE UNREADABLE",
                                            "NO READER FOR VENUE")


def _rows():
    """Registry order rows, or None if the store cannot be read. None is NEVER an empty list."""
    try:
        import registry
        return registry.rows()
    except Exception as ex:
        print(f"registry unreadable ({type(ex).__name__})", flush=True)
        return None


def legs_from(row):
    """Every nested order record in one registry row, tagged with the field it came from.

    live_more is a LIST of order records while live_order and live_rest are single dicts.
    Normalising here rather than assuming: the first version of kalshi_reconcile.py assumed all
    three were dicts and died on .get() against the list, and this file's first version skipped
    them altogether.
    """
    out = []
    for field in NESTED_FIELDS:
        v = row.get(field)
        for o in (v if isinstance(v, list) else [v]):
            if isinstance(o, dict) and (o.get("order_id") or o.get("client_id")):
                out.append((field, o))
    return out


def canonical_registry_key(raw):
    """Map a stored lane-prefixed key to EXACTLY the live guard's play identity.

    Invalid/unknown formats are not allowed into an activation backfill. The original
    value is retained separately for private audit; never silently guess a market.
    """
    import review_integration as ri
    try:
        return ri.key_from_registry(raw)      # the ONE identity function; nothing rebuilt here
    except Exception:
        raise ValueError("unrecognised or incomplete source play key")


# Lane units, per Peter (Nov 23): $300 for Lane 1, $200 for R1, Board and NCS. These mirror
# executor.LIVE_UNIT / R1_UNIT / BOARD_UNIT / NCS_UNIT and a test asserts they still agree;
# executor itself is not imported, to keep the order paths out of this script's reachable set.
LANE_UNIT = {"lane1": 300.0, "r1": 200.0, "board": 200.0, "ncs": 200.0}
# The two places a row states its lane: the play-key prefix and the row's source.
PREFIX_LANE = {"rule": "lane1", "rules": "lane1", "board": "board", "r1": "r1", "ncs": "ncs"}
SOURCE_LANE = {"rules": "lane1", "board": "board", "r1": "r1", "ncs": "ncs"}


def lane_unit(row, order=None):
    """(lane, unit, why). The unit comes from LANE METADATA or not at all.

    The first run (Nov 23) refused 46 legs for "no lane unit" because this script read a `unit`
    field off the order record, and the registry's projection of an order never writes one. The
    world was fine; the reader was wrong.

    NOTHING IS DEFAULTED. executor.unit_for() treats every lane it does not name as Lane 1, which is
    right for sizing a new order and wrong for certifying old exposure. Here an unnamed lane, a
    source this table does not know ("muse", "lane2", blank) or a prefix that disagrees with the
    source returns no unit, and the leg stays INCOMPLETE until a person rules on it.
    """
    key = str((row or {}).get("key") or (row or {}).get("play_key") or "")
    parts = key.split("|")
    by_prefix = PREFIX_LANE.get(parts[0].strip().lower()) if len(parts) == 5 else None
    src = str((row or {}).get("source") or "").strip().lower()
    by_source = SOURCE_LANE.get(src)
    if by_prefix and by_source and by_prefix != by_source:
        return None, None, "lane conflict: key prefix and source disagree"
    lane = by_prefix or by_source
    if not lane:
        if len(parts) == 5 and not by_prefix:
            return None, None, "lane unknown: unrecognised key prefix"
        return None, None, ("lane unknown: source not a live lane" if src
                            else "lane unknown: no prefix and no source")
    unit = LANE_UNIT[lane]
    stored = _num((order or {}).get("unit"))
    if stored is not None and abs(stored - unit) > 0.005:
        return lane, None, "unit conflict: stored unit disagrees with the lane"
    return lane, unit, ""


def american_of(o):
    """The order's American price, or None. The registry projection stores it as `limit`; older
    shapes used american / shown. A value that is not American odds (|x| < 100) is not guessed at."""
    for k in ("american", "shown", "limit"):
        v = _num((o or {}).get(k))
        if v is not None:
            return v if abs(v) >= 100 else None
    return None


def backfill_candidates(rows):
    """(legs, unreadable, terminal) from the NESTED order records of every registry row.

    A leg is outstanding when its recorded status is not terminal. That is a candidate list only -
    the venue decides, in venue_evidence() below.
    """
    legs, unreadable, terminal = [], [], 0
    for r in rows or []:
        key = r.get("key") or r.get("play_key") or ""
        found = legs_from(r)
        # The normal ledger uses lane-stripped, line-blind identity. A source key
        # that does not resolve to that format must block activation, not start a
        # different and therefore falsely empty exposure budget.
        try:
            canon = canonical_registry_key(key)
        except Exception:
            unreadable.append({"key": str(key), "why": "source play key cannot be canonicalised"})
            continue
        if not found:
            # A row with no nested order record at all. Named, never dropped: it is either a row
            # shape this reader does not know or a row that never reached a venue, and the two
            # have opposite remedies.
            unreadable.append({"key": str(key), "why": "row carries no nested order record",
                               "fields_present": sorted(k for k in r if k in NESTED_FIELDS)})
            continue
        for field, o in found:
            lane, unit, unit_why = lane_unit(r, o)
            st = str(o.get("status") or "").strip().lower()
            if st in LEDGER_STATES_TERMINAL:
                terminal += 1
            elif st and st not in LEDGER_STATES_OPEN:
                unreadable.append({"key": str(key), "field": field,
                                   "order_id": str(o.get("order_id") or o.get("client_id")),
                                   "why": f"unknown recorded status {st!r}"})
                continue
            # EVERY leg is verified, FILLED ONES INCLUDED. The first version stopped at the
            # recorded status and skipped terminal legs, so a filled order - the one kind that
            # certainly moved money - was never checked against a venue at all. A recorded
            # "filled" is still only what we believed when we wrote it.
            legs.append({"key": canon, "source_key": str(key), "field": field,
                         "recorded_terminal": st in LEDGER_STATES_TERMINAL,
                         "order_id": str(o.get("order_id") or o.get("client_id") or ""),
                         "client_id": str(o.get("client_id") or "") or None,
                         "book": str(o.get("book") or "").strip().lower() or None,
                         "status": st or None,
                         "asked_stake": o.get("asked_stake", o.get("risk")),
                         "filled_stake": o.get("filled_stake"),
                         "american": american_of(o),
                         "lane": lane, "unit": unit, "unit_why": unit_why or None,
                         "day": str(r.get("et_day") or r.get("decided_utc") or "")[:10] or None,
                         "fields": sorted(k for k in o if isinstance(k, str)),
                         "terminal_verified": o.get("terminal_verified")})
    return legs, unreadable, terminal


# ----------------------------------------------------------------- venue evidence, read-only
def _novig_index():
    """((by_client_id, fills_by_client_id), why) - the runner's snapshots, through the existing
    module. Not a second parser: novig_reconcile already fails closed on an unread fill."""
    try:
        import novig_reconcile as nr
        return nr.load_venue()
    except Exception as ex:
        return (None, None), f"novig_reconcile unavailable: {type(ex).__name__}"


def _kalshi_order(oid):
    """GET /portfolio/orders/{id}, the same read kalshi_reconcile and kalshi_expiry_probe use."""
    import book_live
    st, d = book_live._k_call("GET", f"/portfolio/orders/{oid}")
    if st != 200 or not isinstance(d, dict):
        return None, f"status {st}"
    return (d.get("order") or {}), ""


def _pmus_order(oid):
    """Read the order BACK. CLAUDE.md: acceptance is never proof on this venue. Two paths, because
    the id-only route is the one that has moved before."""
    import book_live
    last = ""
    for path in (f"/v1/order/{oid}", f"/v1/orders/{oid}"):
        try:
            _, r = book_live._pm_call("GET", path)
            o = (r.get("order") or {}) if isinstance(r, dict) else {}
            if o:
                return o, ""
        except Exception as ex:
            last = f"{type(ex).__name__}"
    return None, last or "no order body returned"


def _px_trades():
    """(trades_by_order_id, why). ProphetX fill evidence is its TRADE list - px_live.trades() reads
    /v4/mm/get_trades and _mine() already matches on order_id. Read-only; no order path is used."""
    try:
        import px_live
        # trades() does NOT authenticate itself, and an unauthenticated GET returns 401 - which
        # would make ProphetX permanently UNREADABLE and the verdict permanently INCOMPLETE. login()
        # is a CREDENTIAL EXCHANGE (POST /auth/login), the only POST anywhere in this script. It is
        # not an order path: no strike, price, stake or order id is sent. Stated plainly rather than
        # claiming this script makes no POST at all.
        if not px_live.login():
            return None, "ProphetX credentials absent or refused - no fill evidence"
        tr = px_live.trades()
        if not isinstance(tr, list):
            return None, "trade list unreadable"
        by = {}
        for t in tr:
            if isinstance(t, dict) and t.get("order_id") is not None:
                by.setdefault(str(t["order_id"]), []).append(t)
        return by, f"ok ({len(by)} order id(s) with trades)"
    except Exception as ex:
        return None, f"px_live unavailable: {type(ex).__name__}"


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


OPEN_WORDS = ("open", "resting", "working", "pending", "new", "accepted")
# Terminal words split by what they IMPLY about the fill. "canceled" with a read zero is a real
# zero. "filled" or "executed" with a zero is a CONTRADICTION between two fields - a fill we failed
# to read - and the remedies are opposite. Lumped together, the second was released as zero
# exposure, which is the remaining route to undercounting a filled order.
ZERO_WORDS = ("canceled", "cancelled", "expired", "rejected", "closed", "done")
FILLED_WORDS = ("filled", "executed", "settled", "matched", "complete")


def classify_generic(o):
    """(class, evidence) for a Kalshi or Polymarket US order body, in novig_reconcile's vocabulary.

    The Nov 19 Novig lesson applies verbatim here: an UNREAD quantity must not become a confident
    zero. A missing or unparseable filled quantity is UNKNOWN, which keeps the leg's full
    commitment, never TERMINAL, which would release it.
    """
    import novig_reconcile as nr
    st = str(o.get("status") or "").strip().lower()
    fq = _num(o.get("filled_qty"))
    if fq is None:
        fq = _num(o.get("cumQuantity"))
    qty = _num(o.get("qty"))
    if qty is None:
        qty = _num(o.get("quantity"))
    ev = {"venue_status": o.get("status") or None, "filled": fq, "qty": qty}
    if fq is None:
        ev["why"] = "venue returned no filled quantity - an unread fill is not a zero"
        return nr.UNKNOWN, ev
    if qty is not None and fq > 0:
        if fq >= qty:
            return nr.FILLED, ev
        return nr.PARTIAL, ev     # resting or since-terminal: a real quantity filled either way
    if fq > 0:
        return nr.PARTIAL, ev
    if any(w in st for w in OPEN_WORDS):
        return nr.OPEN, ev
    if any(w in st for w in FILLED_WORDS):
        ev["why"] = (f"venue status {st!r} means filled but the quantity read as zero - "
                     f"contradiction, so the full commitment is kept")
        return nr.UNKNOWN, ev
    if any(w in st for w in ZERO_WORDS):
        return nr.TERMINAL, ev
    ev["why"] = f"venue status {st!r} is not one this reader knows"
    return nr.UNKNOWN, ev


def venue_evidence(legs, novig=None, kalshi=None, pmus=None, px=None):
    """Attach venue evidence to each outstanding leg. Returns (legs, summary_by_class).

    The readers are injectable so the tests exercise this against fakes and never a live venue.
    A leg whose venue cannot be read keeps its FULL recorded exposure and is reported as blocking:
    an unread venue must never be able to release a dollar, which is novig_reconcile's own rule and
    is the reason this does not fall back to the registry's status.
    """
    import novig_reconcile as nr
    if novig is None:
        novig = _novig_index
    if kalshi is None:
        kalshi = _kalshi_order
    if pmus is None:
        pmus = _pmus_order
    if px is None:
        px = _px_trades
    (by_cid, fills), nv_why = novig()
    px_by, px_why = px()
    counts = {}
    for leg in legs:
        book = (leg.get("book") or "").lower()
        # THE ID MEANS DIFFERENT THINGS PER VENUE, and assuming one convention is how this went
        # wrong first time. novig_reconcile's own rule: the registry's order_id IS Novig's CLIENT
        # id, and it normalises that itself - so a Novig leg is handed over untouched. Kalshi's
        # order_id is a VENUE order id, which is what /portfolio/orders/{id} takes, and
        # kalshi_reconcile looks it up exactly that way.
        oid = leg.get("order_id") or leg.get("client_id")
        if not oid:
            leg["evidence_class"], leg["evidence"] = NO_RECORD, {"why": "leg carries no identifier"}
        elif book == "novig":
            if by_cid is None:
                leg["evidence_class"], leg["evidence"] = UNREADABLE, {"why": nv_why}
            else:
                import novig_reconcile as nr
                cls, ev = nr.classify(leg, by_cid, fills)
                leg["evidence_class"] = PROVEN if cls != nr.UNKNOWN else NO_RECORD
                leg["venue_class"], leg["evidence"] = cls, ev
        elif book in ("kalshi", "polymarket_us"):
            o, why = (kalshi(oid) if book == "kalshi" else pmus(oid))
            if not o:
                leg["evidence_class"], leg["evidence"] = UNREADABLE, {"why": why}
            else:
                cls, ev = classify_generic(o)
                leg["evidence_class"] = PROVEN if cls != nr.UNKNOWN else NO_RECORD
                leg["venue_class"], leg["evidence"] = cls, ev
        elif book == "prophetx":
            if px_by is None:
                leg["evidence_class"], leg["evidence"] = UNREADABLE, {"why": px_why}
            else:
                tr = px_by.get(str(oid)) or []
                if tr:
                    leg["evidence_class"], leg["venue_class"] = PROVEN, nr.FILLED
                    leg["evidence"] = {"trade_records": len(tr), "source": "px get_trades"}
                else:
                    # No trade for this order id. ProphetX's trade list is FILLS, so absence is not
                    # proof the order never filled - it may predate the window the venue returns.
                    leg["evidence_class"], leg["venue_class"] = NO_RECORD, nr.UNKNOWN
                    leg["evidence"] = {"why": "no ProphetX trade for this order id - absence of a "
                                              "fill record is not proof of zero fills"}
        else:
            leg["evidence_class"] = NO_READER
            leg["evidence"] = {"why": f"no read-back path for book {book or 'unknown'!r}"}
        counts[leg["evidence_class"]] = counts.get(leg["evidence_class"], 0) + 1
    return legs, counts


def completeness(legs, unreadable, counts=None):
    """(verdict, why). COMPLETE requires VENUE EVIDENCE for every outstanding leg.

    Bounded, not asserted. The old version called the list COMPLETE when every leg merely carried a
    unit - which proves the reader parsed the row, not that the exposure is real or still open.
    """
    import novig_reconcile as nr
    if unreadable:
        return "INCOMPLETE", f"{len(unreadable)} row(s) could not be classified"
    # A lane unit is needed wherever exposure could exist. A PROVEN zero-fill terminal
    # contributes nothing, but FILLED is a settled liability and still counts.
    standing = [l for l in legs if l.get("venue_class") != nr.TERMINAL]
    missing_unit = [l for l in standing if l.get("unit") in (None, "")]
    if missing_unit:
        why = {}
        for l in missing_unit:
            k = l.get("unit_why") or "no lane unit"
            why[k] = why.get(k, 0) + 1
        return "INCOMPLETE", (f"{len(missing_unit)} leg(s) with standing exposure have no lane "
                              f"unit (" + "; ".join(f"{v} {k}" for k, v in sorted(why.items()))
                              + ")")
    # The venue can prove an order exists while our registry still lacks enough
    # economic fields to value it. A COMPLETE flag must not be based on unit alone.
    try:
        import review_unit_reservation as reservation
        for leg in standing:
            reservation.leg_fraction({
                "status": "open",   # conservatively hold the full asked exposure
                "order_id": leg.get("order_id") or leg.get("client_id"),
                "asked_stake": leg.get("asked_stake"),
                "american": leg.get("american"),
                "unit": leg.get("unit"),
            })
    except Exception:
        return "INCOMPLETE", "standing exposure has invalid/missing identity, amount, price or unit"
    if counts is None:
        return "UNPROVEN", "no venue evidence was gathered - the registry's own status is not proof"
    unproven = {k: v for k, v in counts.items() if k != PROVEN and v}
    if unproven:
        return "INCOMPLETE", "; ".join(f"{v} leg(s) {k.lower()}" for k, v in sorted(unproven.items()))
    if not legs:
        return "COMPLETE", "no order records at all: nothing to backfill"
    return "COMPLETE", (f"{len(legs)} leg(s) confirmed against their venue "
                        f"({len(standing)} with exposure still standing)")


REASON_CODES = (
    ("leg carries no identifier", "no identifier on the leg"),
    ("no venue record for this client id", "id absent from the Novig snapshot"),
    ("fill quantity not read", "Novig fill quantity unread"),
    ("zero that no read confirms", "Novig terminal zero unconfirmed"),
    ("no ProphetX trade", "no ProphetX trade record"),
    ("venue returned no filled quantity", "venue returned no filled quantity"),
    ("means filled but the quantity read as zero", "filled status with zero quantity"),
    ("is not one this reader knows", "venue status unknown to the reader"),
    ("no read-back path", "no reader for this book"),
)


def reason_code(leg):
    """A FIXED-VOCABULARY reason for a leg without venue proof. The raw text can carry an order id
    or a venue message, so the public log only ever prints one of these codes."""
    why = str((leg.get("evidence") or {}).get("why") or "")
    for needle, code in REASON_CODES:
        if needle in why:
            return code
    return "other (see private mail)"


def diagnostics(legs):
    """Counts and reasons only - safe for a public log. No id, key, price or amount.

    Peter, Nov 23: identify the unproven legs' venue, missing evidence and reason WITHOUT a Gmail
    read. This is that: (book, evidence class, reason) -> count, the lane split, and which
    economic fields are absent - by NAME, never value, as px_live.trade_fields() does.
    """
    out = {"unproven": {}, "lane": {}, "unit": {}, "missing": {}, "fields": {}}
    for l in legs:
        if l.get("evidence_class") != PROVEN:
            k = f"{l.get('book') or 'unknown book'} / {l.get('evidence_class')} / {reason_code(l)}"
            out["unproven"][k] = out["unproven"].get(k, 0) + 1
        ln = l.get("lane") or "unknown"
        out["lane"][ln] = out["lane"].get(ln, 0) + 1
        if l.get("unit") is None:
            k = l.get("unit_why") or "no lane unit"
            out["unit"][k] = out["unit"].get(k, 0) + 1
        for f in ("asked_stake", "american", "order_id", "book"):
            if l.get(f) in (None, ""):
                out["missing"][f] = out["missing"].get(f, 0) + 1
        for f in l.get("fields") or []:
            out["fields"][f] = out["fields"].get(f, 0) + 1
    return out


def parse_aliases(text):
    """"Minnesota|Vikings;San Francisco|49ers" -> [["minnesota","vikings"],["san francisco","49ers"]].
    One group per team; a record matches when EVERY group has at least one whole-word hit."""
    groups = []
    for g in str(text or "").split(";"):
        names = [n.strip().lower() for n in g.split("|") if n.strip()]
        if names:
            groups.append(names)
    return groups


def matches_incident(obj, needle="", aliases=None):
    """True when a record names the incident - by the literal term, or by every alias group.

    The first run searched one literal string, "MIN @ SF", found nothing and printed "0 unit(s)".
    A venue or a lane may spell the game with full names, a different separator or the teams in
    the other order, so a literal miss proves nothing about exposure."""
    blob = json.dumps(obj, default=str).lower()
    want = str(needle or "").strip().lower()
    if want and want in blob:
        return True
    groups = aliases or []
    return bool(groups) and all(
        any(re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", blob) for n in g)
        for g in groups)


def venue_side_search(needle, aliases, date, novig=None, px=None):
    """Counts of VENUE-SIDE records naming the incident or dated that day, found without going
    through the registry at all - so an order the registry never recorded can still surface.

    Novig: the runner's order snapshot. ProphetX: the trade list. Kalshi and Polymarket US have no
    history read in this repo (only a per-order read by id), which is reported as a limit rather
    than passed off as a clean result."""
    out = {}
    (by_cid, _f), nv_why = (novig or _novig_index)()
    if by_cid is None:
        out["novig"] = {"readable": False, "why": nv_why}
    else:
        recs = list(by_cid.values())
        out["novig"] = {"readable": True, "records": len(recs),
                        "on_date": sum(1 for r in recs if date and date in json.dumps(r, default=str)),
                        "matching": [r for r in recs if matches_incident(r, needle, aliases)]}
    px_by, px_why = (px or _px_trades)()
    if px_by is None:
        out["prophetx"] = {"readable": False, "why": px_why}
    else:
        recs = [t for v in px_by.values() for t in v]
        out["prophetx"] = {"readable": True, "records": len(recs),
                           "on_date": sum(1 for r in recs if date and date in json.dumps(r, default=str)),
                           "matching": [r for r in recs if matches_incident(r, needle, aliases)],
                           "field_names": sorted({k for r in recs[:40] for k in r})}
    for b in ("kalshi", "polymarket_us"):
        out[b] = {"readable": False, "why": "no history read exists for this venue - by-id only"}
    return out


def min_at_sf(rows, needle, aliases=None, date=None):
    """The replay: every registry row matching the incident, verbatim, with nothing inferred.

    Matches the NESTED records as well as the row, because an order id only ever appears nested.
    """
    want = str(needle or "").strip().lower()
    if not want and not aliases:
        return []
    return [r for r in rows or [] if matches_incident(r, want, aliases)]


def incident_exposure(rows, needle, legs, aliases=None, date=None):
    """(report, units, discrepancies) for the incident: what each venue holds, and where it
    disagrees with the registry.

    Peter, Nov 23: report the ACTUAL Novig and ProphetX fills, the discrepancies and the combined
    unit exposure. Combined exposure is in UNITS, never dollars, so this is safe to summarise in
    chat; the dollar figures stay in the private mail and never reach a log.

    A discrepancy is recorded, never reconciled away: where the registry and the venue disagree the
    row says so and BOTH figures are kept. CLAUDE.md - two states with opposite remedies must not
    be collapsed into one message.
    """
    import novig_reconcile as nr
    want = str(needle or "").strip().lower()
    if not want and not aliases:
        return [], None, []
    hit_keys = set()
    for row in min_at_sf(rows, want, aliases):
        try:
            hit_keys.add(canonical_registry_key(row.get("key") or row.get("play_key")))
        except Exception:
            # The row is already reported as unreadable by backfill_candidates.
            # Never force an invalid source key to match a valid reservation.
            pass
    mine = [l for l in legs if str(l.get("key") or "") in hit_keys and hit_keys]
    report, disc = [], []
    by_order, units_unknown = {}, 0
    for l in mine:
        vc = l.get("venue_class")
        rec_term = bool(l.get("recorded_terminal"))
        ev = l.get("evidence") or {}
        report.append({"book": l.get("book"), "field": l.get("field"),
                       "order_id": l.get("order_id"), "recorded_status": l.get("status"),
                       "venue_class": vc, "evidence_class": l.get("evidence_class"),
                       "asked_stake": l.get("asked_stake"), "filled_stake": l.get("filled_stake"),
                       "venue_filled": ev.get("filled_usd", ev.get("filled")),
                       "unit": l.get("unit"), "american": l.get("american")})
        # the registry said terminal, the venue says it is still live - or the reverse
        if rec_term and vc in (nr.OPEN, nr.PARTIAL):
            disc.append({"order_id": l.get("order_id"), "book": l.get("book"),
                         "why": "registry recorded this terminal; the venue still shows it live",
                         "registry": l.get("status"), "venue": vc})
        if (not rec_term) and vc == nr.TERMINAL:
            disc.append({"order_id": l.get("order_id"), "book": l.get("book"),
                         "why": "registry recorded this live; the venue shows it terminal",
                         "registry": l.get("status"), "venue": vc})
        if l.get("evidence_class") != PROVEN:
            disc.append({"order_id": l.get("order_id"), "book": l.get("book"),
                         "why": f"no venue proof: {l.get('evidence_class')}",
                         "detail": ev.get("why")})
        # combined UNIT exposure: the same per-leg fraction the reservation protocol uses, so the
        # number here and the number the guard would enforce cannot drift apart.
        # Only a PROVEN zero-fill terminal outcome can release the entire ask.
        # A venue-confirmed FILLED order remains committed even when the registry
        # calls it terminal. Open/partial/unknown retains the whole asked stake.
        # This is a conservative RESERVATION number, not realized P&L.
        if vc == nr.TERMINAL and l.get("evidence_class") == PROVEN:
            continue
        if l.get("evidence_class") != PROVEN:
            units_unknown += 1
            continue
        try:
            import review_unit_reservation as R
            f = R.leg_fraction({"status": "open", "order_id": l.get("order_id") or "x",
                                "asked_stake": l.get("asked_stake"),
                                "american": l.get("american"), "unit": l.get("unit")})
        except Exception:
            units_unknown += 1
            continue
        # remaining_mixed() takes the MAX per order id and then sums. A flat sum here reported one
        # order recorded under two nested fields at 2.0 units where the guard would charge 1.0 -
        # so the comment above ("cannot drift apart") was not true of the code beneath it.
        oid = str(l.get("order_id") or l.get("client_id") or id(l))
        bucket = by_order.setdefault(str(l.get("key") or ""), {})
        bucket[oid] = max(f, bucket.get(oid, 0.0))
    units = sum(v for b in by_order.values() for v in b.values())
    return report, (None if units_unknown else round(units, 3)), disc


def _csv(legs):
    """Evidence-review CSV, NOT a directly executable activation backfill. A complete
    evidence report still needs identity dedupe, verified fill amounts and explicit
    migration approval before it may be used to seed the live ledger.

    CLAUDE.md: an email body truncates SILENTLY and clv_report shipped
    unparseable half-JSON for months that way. A CSV attachment cannot be half-valid."""
    cols = ["key", "source_key", "field", "order_id", "client_id", "book", "status", "asked_stake",
            "filled_stake", "american", "unit", "terminal_verified", "evidence_class",
            "venue_class", "evidence"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for l in legs:
        row = dict(l)
        if isinstance(row.get("evidence"), dict):
            row["evidence"] = json.dumps(row["evidence"], default=str)
        w.writerow(row)
    return buf.getvalue()


def main(argv):
    needle = argv[1] if len(argv) > 1 else os.environ.get("REPLAY_MATCH", "")
    aliases = parse_aliases(os.environ.get("REPLAY_ALIASES", ""))
    date = (os.environ.get("REPLAY_DATE") or "").strip()[:10]
    rows = _rows()
    if rows is None:
        print("REPLAY: registry unreadable - nothing reported, nothing inferred", flush=True)
        return 1
    legs, unreadable, terminal = backfill_candidates(rows)
    legs, counts = venue_evidence(legs)
    verdict, why = completeness(legs, unreadable, counts)
    hits = min_at_sf(rows, needle, aliases)
    inc, inc_units, inc_disc = incident_exposure(rows, needle, legs, aliases)
    diag = diagnostics(legs)
    on_date = [l for l in legs if date and l.get("day") == date]
    vside = venue_side_search(needle, aliases, date) if (needle or aliases) else {}

    # PUBLIC LOG: counts only. No key, no dollar figure, no order id.
    print(f"REPLAY: registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
          f"unreadable {len(unreadable)}", flush=True)
    print("REPLAY: venue evidence " + (", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                                       or "none gathered"), flush=True)
    print(f"REPLAY: backfill completeness {verdict} - {why}", flush=True)
    _fmt = lambda d: "; ".join(f"{v} x {k}" for k, v in sorted(d.items())) or "none"
    print("REPLAY: unproven legs by book / class / reason: " + _fmt(diag["unproven"]), flush=True)
    print("REPLAY: legs by lane: " + _fmt(diag["lane"]), flush=True)
    print("REPLAY: legs with no unit, by reason: " + _fmt(diag["unit"]), flush=True)
    print("REPLAY: legs missing an economic field (names only): " + _fmt(diag["missing"]),
          flush=True)
    print("REPLAY: order-record field names seen (names only): "
          + ", ".join(sorted(diag["fields"])), flush=True)
    if needle or aliases:
        print(f"REPLAY: incident - registry rows matching the term or aliases: {len(hits)} | "
              f"legs {len(inc)} | discrepancies {len(inc_disc)} | alias groups {len(aliases)}",
              flush=True)
        if date:
            print(f"REPLAY: incident - registry legs dated {date}: {len(on_date)}", flush=True)
        for b in sorted(vside):
            v = vside[b]
            print(f"REPLAY: incident - venue-side {b}: " + (
                f"{v['records']} record(s) read, {v['on_date']} on the date, "
                f"{len(v['matching'])} naming the incident" if v.get("readable")
                else f"NOT SEARCHED ({v.get('why')})"), flush=True)
        if "field_names" in (vside.get("prophetx") or {}):
            print("REPLAY: incident - ProphetX trade field names (names only): "
                  + ", ".join(vside["prophetx"]["field_names"]), flush=True)
        # UNITS ONLY in the log. Dollars go to the private mail, per CLAUDE.md.
        if not inc:
            # Zero matched legs is NOT zero exposure, and must never be printed as "0 unit(s)".
            print("REPLAY: incident combined exposure NOT FOUND - no registry leg matched, which "
                  "is not evidence of zero exposure", flush=True)
        else:
            print("REPLAY: incident combined exposure " + (f"{inc_units} unit(s)" if inc_units
                  is not None else "NOT COMPUTABLE - a leg lacks venue proof, a unit or a price"),
                  flush=True)
    else:
        print("REPLAY: no incident term supplied; replay section skipped", flush=True)

    body = [f"PR #10 private reconciliation - {datetime.now(timezone.utc).isoformat()}", "",
            "READ-ONLY. Nothing was placed or cancelled. EXEC_UNIT_LEDGER untouched.", "",
            f"Backfill completeness: {verdict} - {why}",
            f"  registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
            f"unreadable {len(unreadable)}",
            "  venue evidence: " + (", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                                    or "none gathered"), "",
            "CSV contains reconciliation CANDIDATES, not an activation-ready backfill.",
            "Do not seed the production ledger directly from this attachment: order/client",
            "identity dedupe, independently verified monetary fills, and complete venue",
            "coverage require separate reconciliation and approval.", ""]
    if unreadable:
        body += ["ROWS THAT COULD NOT BE CLASSIFIED (these block activation):"]
        body += [f"  {json.dumps(u, default=str)}" for u in unreadable[:50]] + [""]
    if needle or aliases:
        body += ["VENUE-SIDE RECORDS NAMING THE INCIDENT (found without the registry):",
                 json.dumps({b: v.get("matching") for b, v in vside.items() if v.get("readable")},
                            indent=1, default=str)[:100000], ""]
        body += [f"INCIDENT EXPOSURE - {len(inc)} leg(s) across the matching rows",
                 f"  combined exposure: " + (f"{inc_units} unit(s)" if inc_units is not None
                                             else "NOT COMPUTABLE"),
                 "  per-leg detail (registry figure AND venue figure, both kept):",
                 json.dumps(inc, indent=1, default=str)[:100000], ""]
        if inc_disc:
            body += [f"DISCREPANCIES - {len(inc_disc)}. Recorded, not reconciled away:"]
            body += [f"  {json.dumps(d, default=str)}" for d in inc_disc[:50]] + [""]
        else:
            body += ["DISCREPANCIES: none found between the registry and the venues for these "
                     "legs. That is not a claim that none exists - only legs with venue proof "
                     "could be compared.", ""]
        body += [f"MIN @ SF REPLAY - rows matching {needle!r}: {len(hits)}",
                 "Verbatim registry rows. No verdict is computed here; nothing is inferred.",
                 "This is a REGISTRY-RECORD search. It is not a venue-side reconciliation of that",
                 "incident: it shows what we recorded, which is the thing under suspicion.",
                 json.dumps(hits, indent=1, default=str)[:200000]]
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        user = (os.environ.get("GMAIL_ADDRESS") or "").strip()
        pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
        to = (os.environ.get("EMAIL_TO") or "").strip() or user
        if not (user and pw):
            print("REPLAY: email not configured - detail NOT delivered", flush=True)
            return 1
        m = MIMEMultipart()
        m["Subject"] = f"Bets PR#10 private reconciliation - backfill {verdict}"
        m["From"], m["To"] = user, to
        m.attach(MIMEText("\n".join(body), "plain", "utf-8"))
        att = MIMEApplication(_csv(legs).encode("utf-8"), _subtype="csv")
        att.add_header("Content-Disposition", "attachment", filename="pr10_backfill_legs.csv")
        m.attach(att)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=120) as sv:
            sv.login(user, pw)
            sv.sendmail(user, [to], m.as_string())
        print("REPLAY: emailed", flush=True)
    except Exception as ex:
        print(f"REPLAY: email failed ({type(ex).__name__})", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
