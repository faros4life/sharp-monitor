#!/usr/bin/env python3
"""REVIEW ONLY, READ-ONLY. The two private-data tasks blocking draft PR #10, run inside Actions.

WHY THIS EXISTS. Two preconditions for the shared unit ledger need data nobody can hand to a chat
session: the MIN @ SF reconciliation, and proof that the backfill list of already-outstanding
orders is complete. Both live behind TRACKER_PASSPHRASE and the venue keys. This script runs where
those secrets already are - a dispatch-only workflow - so the work happens without the secret or
the records ever leaving that run. The public Actions log gets COUNTS ONLY; the detail goes to the
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


def backfill_candidates(rows):
    """(legs, unreadable, terminal) from the NESTED order records of every registry row.

    A leg is outstanding when its recorded status is not terminal. That is a candidate list only -
    the venue decides, in venue_evidence() below.
    """
    legs, unreadable, terminal = [], [], 0
    for r in rows or []:
        key = r.get("key") or r.get("play_key") or ""
        found = legs_from(r)
        if not found:
            # A row with no nested order record at all. Named, never dropped: it is either a row
            # shape this reader does not know or a row that never reached a venue, and the two
            # have opposite remedies.
            unreadable.append({"key": str(key), "why": "row carries no nested order record",
                               "fields_present": sorted(k for k in r if k in NESTED_FIELDS)})
            continue
        for field, o in found:
            st = str(o.get("status") or "").strip().lower()
            if st in LEDGER_STATES_TERMINAL:
                terminal += 1
                continue
            if st and st not in LEDGER_STATES_OPEN:
                unreadable.append({"key": str(key), "field": field,
                                   "order_id": str(o.get("order_id") or o.get("client_id")),
                                   "why": f"unknown recorded status {st!r}"})
                continue
            legs.append({"key": str(key), "field": field,
                         "order_id": str(o.get("order_id") or o.get("client_id") or ""),
                         "client_id": str(o.get("client_id") or "") or None,
                         "book": str(o.get("book") or "").strip().lower() or None,
                         "status": st or None,
                         "asked_stake": o.get("asked_stake", o.get("risk")),
                         "filled_stake": o.get("filled_stake"),
                         "american": o.get("american", o.get("shown")),
                         "unit": o.get("unit"),
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


def venue_evidence(legs, novig=None, kalshi=None, pmus=None):
    """Attach venue evidence to each outstanding leg. Returns (legs, summary_by_class).

    The readers are injectable so the tests exercise this against fakes and never a live venue.
    A leg whose venue cannot be read keeps its FULL recorded exposure and is reported as blocking:
    an unread venue must never be able to release a dollar, which is novig_reconcile's own rule and
    is the reason this does not fall back to the registry's status.
    """
    if novig is None:
        novig = _novig_index
    if kalshi is None:
        kalshi = _kalshi_order
    if pmus is None:
        pmus = _pmus_order
    (by_cid, fills), nv_why = novig()
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
                leg["evidence_class"] = PROVEN
                leg["evidence"] = {"venue_status": o.get("status"),
                                   "filled": o.get("filled_qty", o.get("cumQuantity")),
                                   "qty": o.get("qty", o.get("quantity"))}
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
    if unreadable:
        return "INCOMPLETE", f"{len(unreadable)} row(s) could not be classified"
    missing_unit = [l for l in legs if l.get("unit") in (None, "")]
    if missing_unit:
        return "INCOMPLETE", (f"{len(missing_unit)} leg(s) carry no lane unit, so their share of "
                              f"the budget cannot be computed")
    if counts is None:
        return "UNPROVEN", "no venue evidence was gathered - the registry's own status is not proof"
    unproven = {k: v for k, v in counts.items() if k != PROVEN and v}
    if unproven:
        return "INCOMPLETE", "; ".join(f"{v} leg(s) {k.lower()}" for k, v in sorted(unproven.items()))
    if not legs:
        return "COMPLETE", "no outstanding legs: nothing to backfill"
    return "COMPLETE", f"{len(legs)} outstanding leg(s), each confirmed against its venue"


def min_at_sf(rows, needle):
    """The replay: every registry row matching the incident, verbatim, with nothing inferred.

    Matches the NESTED records as well as the row, because an order id only ever appears nested.
    """
    want = str(needle or "").strip().lower()
    if not want:
        return []
    hits = []
    for r in rows or []:
        blob = json.dumps(r, default=str).lower()
        if want in blob:
            hits.append(r)
    return hits


def _csv(legs):
    """The backfill list as CSV. CLAUDE.md: an email body truncates SILENTLY and clv_report shipped
    unparseable half-JSON for months that way. A CSV attachment cannot be half-valid."""
    cols = ["key", "field", "order_id", "client_id", "book", "status", "asked_stake",
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
    rows = _rows()
    if rows is None:
        print("REPLAY: registry unreadable - nothing reported, nothing inferred", flush=True)
        return 1
    legs, unreadable, terminal = backfill_candidates(rows)
    legs, counts = venue_evidence(legs)
    verdict, why = completeness(legs, unreadable, counts)
    hits = min_at_sf(rows, needle)

    # PUBLIC LOG: counts only. No key, no dollar figure, no order id.
    print(f"REPLAY: registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
          f"unreadable {len(unreadable)}", flush=True)
    print("REPLAY: venue evidence " + (", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                                       or "none gathered"), flush=True)
    print(f"REPLAY: backfill completeness {verdict} - {why}", flush=True)
    print(f"REPLAY: incident rows matching the supplied term: {len(hits)}"
          if needle else "REPLAY: no incident term supplied; replay section skipped", flush=True)

    body = [f"PR #10 private reconciliation - {datetime.now(timezone.utc).isoformat()}", "",
            "READ-ONLY. Nothing was placed or cancelled. EXEC_UNIT_LEDGER untouched.", "",
            f"Backfill completeness: {verdict} - {why}",
            f"  registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
            f"unreadable {len(unreadable)}",
            "  venue evidence: " + (", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                                    or "none gathered"), "",
            "The backfill list is the CSV attachment, not this body: an email body truncates",
            "silently and a half-written list is worse than none.", ""]
    if unreadable:
        body += ["ROWS THAT COULD NOT BE CLASSIFIED (these block activation):"]
        body += [f"  {json.dumps(u, default=str)}" for u in unreadable[:50]] + [""]
    if needle:
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
