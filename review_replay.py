#!/usr/bin/env python3
"""REVIEW ONLY, READ-ONLY. The two private-data tasks blocking draft PR #10, run inside Actions.

WHY THIS EXISTS. Two preconditions for the shared unit ledger need data nobody can hand to a chat
session: the MIN @ SF reconciliation, and proof that the backfill list of already-outstanding
orders is complete. Both live behind TRACKER_PASSPHRASE and the venue keys. This script runs where
those secrets already are - a dispatch-only workflow - so the work happens without the secret or
the records ever leaving that run. The public Actions log gets COUNTS ONLY; the detail goes to the
private Bets inbox, the same split every other reporter in this repo uses.

IT PLACES NOTHING, CANCELS NOTHING, WRITES NOTHING. It opens the registry and the tracker read-only
and emails what it found. No order path is imported, no venue is contacted, no setting is read or
written, and it never touches EXEC_UNIT_LEDGER.

INVENTED RECORDS ARE THE FAILURE MODE HERE, so: every figure below is read or it is reported
MISSING. There is no fallback, no estimate and no sample value. A row it cannot parse is counted in
an "unreadable" bucket and named in the private mail, never dropped and never guessed.
"""
import json
import os
import sys
from datetime import datetime, timezone

LEDGER_STATES_OPEN = ("open", "placed", "partially_filled", "submitted", "resting", "working")
LEDGER_STATES_TERMINAL = ("filled", "settled", "canceled", "cancelled", "expired", "void", "refused")


def _rows():
    """Registry order rows, or None if the store cannot be read. None is NEVER an empty list."""
    try:
        import registry
        return registry.rows()
    except Exception as ex:
        print(f"registry unreadable ({type(ex).__name__})", flush=True)
        return None


def backfill_candidates(rows):
    """Every order that still carries exposure, in the leg shape backfill() expects.

    An order whose state cannot be read is NOT skipped - it goes to `unreadable`, because a row we
    cannot classify is exactly the row that must not quietly become zero exposure."""
    legs, unreadable, terminal = [], [], 0
    for r in rows or []:
        try:
            state = str(r.get("status") or r.get("state") or "").strip().lower()
            if state in LEDGER_STATES_TERMINAL and r.get("filled_stake") is not None:
                terminal += 1
                continue
            if state and state not in LEDGER_STATES_OPEN:
                unreadable.append({"why": f"unrecognised state {state!r}", "id": r.get("order_id")})
                continue
            key = r.get("play_key") or r.get("key")
            stake = r.get("asked_stake") if r.get("asked_stake") is not None else r.get("stake")
            price = r.get("american") if r.get("american") is not None else r.get("price")
            if not key or stake is None or price is None:
                unreadable.append({"why": "missing key, stake or price", "id": r.get("order_id")})
                continue
            legs.append({"key": str(key), "order_id": str(r.get("order_id") or r.get("client_id")),
                         "status": state or "open", "asked_stake": float(stake),
                         "american": float(price), "unit": r.get("unit")})
        except Exception as ex:
            unreadable.append({"why": type(ex).__name__, "id": r.get("order_id")})
    return legs, unreadable, terminal


def completeness(legs, unreadable):
    """Peter's precondition 2 in one line: is the backfill list provably complete?

    It is complete only if NOTHING was unreadable and every leg carries the unit its exposure is
    measured against. Anything else is INCOMPLETE - stated, not softened."""
    missing_unit = [l for l in legs if l.get("unit") in (None, "")]
    if unreadable:
        return "INCOMPLETE", f"{len(unreadable)} row(s) could not be classified"
    if missing_unit:
        return "INCOMPLETE", f"{len(missing_unit)} leg(s) carry no lane unit"
    if not legs:
        return "COMPLETE (empty)", "no outstanding exposure found - verify against the venues"
    return "COMPLETE", f"{len(legs)} outstanding leg(s), all classified and unit-bearing"


def min_at_sf(rows, needle):
    """The replay: every registry row matching the incident, verbatim, with nothing inferred.

    It reports what the records SAY. It does not decide whether the unit was exceeded - that is a
    reading of evidence for a person to make, and inventing the verdict here is precisely what the
    instruction forbids."""
    n = str(needle or "").strip().lower()
    if not n:
        return []
    out = []
    for r in rows or []:
        blob = json.dumps(r, default=str).lower()
        if n in blob:
            out.append(r)
    return out


def main(argv):
    needle = argv[1] if len(argv) > 1 else os.environ.get("REPLAY_MATCH", "")
    rows = _rows()
    if rows is None:
        print("REPLAY: registry unreadable - nothing reported, nothing inferred", flush=True)
        return 1
    legs, unreadable, terminal = backfill_candidates(rows)
    verdict, why = completeness(legs, unreadable)
    hits = min_at_sf(rows, needle)

    # PUBLIC LOG: counts only.
    print(f"REPLAY: registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
          f"unreadable {len(unreadable)}", flush=True)
    print(f"REPLAY: backfill completeness {verdict} - {why}", flush=True)
    print(f"REPLAY: incident rows matching the supplied term: {len(hits)}"
          if needle else "REPLAY: no incident term supplied; replay section skipped", flush=True)

    body = [f"PR #10 private reconciliation - {datetime.now(timezone.utc).isoformat()}", "",
            "READ-ONLY. Nothing was placed, cancelled or written. EXEC_UNIT_LEDGER untouched.", "",
            f"Backfill completeness: {verdict} - {why}",
            f"  registry rows {len(rows)} | outstanding {len(legs)} | terminal {terminal} | "
            f"unreadable {len(unreadable)}", ""]
    if unreadable:
        body += ["ROWS THAT COULD NOT BE CLASSIFIED (these block activation):"]
        body += [f"  {u}" for u in unreadable[:50]] + [""]
    body += ["BACKFILL LIST (feed verbatim to review_unit_reservation.backfill):",
             json.dumps(legs, indent=1, default=str)[:400000], ""]
    if needle:
        body += [f"MIN @ SF REPLAY - rows matching {needle!r}: {len(hits)}",
                 "Verbatim registry rows. No verdict is computed here; nothing is inferred.",
                 json.dumps(hits, indent=1, default=str)[:400000]]
    try:
        import smtplib
        from email.mime.text import MIMEText
        user = (os.environ.get("GMAIL_ADDRESS") or "").strip()
        pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
        to = (os.environ.get("EMAIL_TO") or "").strip() or user
        if not (user and pw):
            print("REPLAY: email not configured - detail NOT delivered", flush=True)
            return 1
        m = MIMEText("\n".join(body), "plain", "utf-8")
        m["Subject"] = f"Bets PR#10 private reconciliation - backfill {verdict}"
        m["From"], m["To"] = user, to
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
