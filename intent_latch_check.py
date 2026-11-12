#!/usr/bin/env python3
"""ARE THE OUTSTANDING INTENTS STILL LATCHING LIVE ORDERS? (Peter, Nov 12). READ-ONLY.

Peter asked to verify the outstanding intents. The public Actions log prints counts only, so the
executor's own log cannot answer it, and the run email is too large to read for one line. This
answers it directly by calling the PRODUCTION functions rather than reimplementing their logic, so
it cannot disagree with what the executor actually does:

    _account_rows()        routes each registry row to _intents or _confirmed
    intent_cleared()       Peter's manual, subject-only INTENT CLEARED authorization
    subject_hits(VOID)     the bot's own void, for an order never transmitted
    _bot_orders_finish()   builds INTENT["open"] - non-empty means live orders refuse

Reads only. No order placed, amended or cancelled; no registry write; no email sent; no live
setting touched. It reports the latch, it never clears one.
"""
import os
import sys

os.environ.setdefault("EXEC_LIVE", "off")

import executor as ex
import registry


def main():
    print("INTENT LATCH CHECK - do any write-ahead intents still refuse live orders?")
    print("READ-ONLY: production functions, nothing written, nothing cleared")
    print("=" * 92)

    if not registry.enabled():
        print("  REGISTRY_TOKEN not set - CANNOT VERIFY (the executor would read Gmail instead)")
        return 1
    d = registry.load()
    if d is None:
        print("  registry unreadable - CANNOT VERIFY")
        return 1
    rows = d.get("orders") or []
    print(f"  {len(rows)} registry order row(s)")

    ids, seen, _int, _conf = {}, set(), {}, {}
    try:
        ex._account_rows(rows, {}, ids, seen, _int, _conf)
    except Exception as e:
        print(f"  (_account_rows raised {type(e).__name__}: {str(e)[:70]} - accounting only)")
    print(f"  routed: {len(_int)} intent row(s), {len(_conf)} confirmed/voided row(s)")

    if not _int:
        print()
        print("  NO open intents at all -> nothing is latching. Live orders are not blocked by this.")
        print("=" * 92)
        return 0

    # Ask Gmail the same two questions the executor asks, in the same way.
    try:
        M = ex.imap_open()
    except BaseException as e:          # gmail() raises SystemExit when credentials are absent
        print(f"  Gmail unreachable ({type(e).__name__}) - the executor would FAIL CLOSED and keep")
        print("  refusing. Treat every intent below as still latching.")
        for k in _int:
            print(f"    {k}  UNKNOWN - cannot confirm a clearance")
        return 1
    try:
        senders = ex.authorized_senders()
        print(f"  authorized sender(s) for a clearance: {', '.join(senders)}")
        print()
        still = []
        for k, row in sorted(_int.items()):
            lo = row.get("live_order") or {}
            try:
                cleared = ex.intent_cleared(M, k)
            except Exception as e:
                cleared = f"ERROR {type(e).__name__}"
            try:
                voided = bool(ex.subject_hits(M, k, ex.INTENT_VOID_PREFIX, senders=senders))
            except Exception as e:
                voided = f"ERROR {type(e).__name__}"
            latching = not (cleared is True or voided is True)
            if latching:
                still.append(k)
            print(f"    {k[:38]:<38} INTENT CLEARED={cleared!r}  VOID={voided!r}")
            print(f"        {str(row.get('key') or '')[:76]}")
            print(f"        book={lo.get('book')}  asked={lo.get('asked_stake')}  "
                  f"-> {'STILL LATCHING' if latching else 'RESOLVED, not latching'}")
        print()
        print(f"  {len(still)} of {len(_int)} intent(s) still latching.")
        if still:
            print("  While any remain, live_guards() refuses EVERY further live order, on every venue.")
            print("  Each clears only with an email whose SUBJECT begins: INTENT CLEARED <client_id>")
        else:
            print("  Live orders are no longer blocked by a write-ahead intent.")
            print("  NOTE: a resolved intent does NOT re-open its own play - the play key stays in")
            print("  LIVEKEYS as duplicate protection, which is correct and separate from the latch.")
    finally:
        try:
            ex.imap_close(M)
        except Exception:
            pass
    # ---------------------------------------------------------------- why 0 would go live?
    # Peter: "separate qualification failures, Novig submission holds, and unresolved-intent
    # blocks." Those three produce the SAME number in the subject line, so the number cannot tell
    # them apart. The executor's own run email carries the per-play detail, so it is read here by
    # IMAP and only the TALLY is printed - never the plays, prices or stakes.
    print()
    print("WHY '0 WOULD GO LIVE'? - the three causes, separated")
    print("=" * 92)
    try:
        M = ex.imap_open()
    except BaseException as e:
        print(f"  Gmail unreachable ({type(e).__name__}) - cannot read the run email")
        print("=" * 92)
        return 0
    try:
        import email as _email
        import re
        M.select('"[Gmail]/All Mail"')
        typ, data = M.uid("SEARCH", "X-GM-RAW", '"subject:\\"Bets LIVE:\\" newer_than:1d"')
        uids = (data[0].split() if data and data[0] else [])
        if not uids:
            print("  no recent run email found - CANNOT VERIFY the breakdown")
        else:
            typ, md = M.uid("FETCH", uids[-1], "(BODY.PEEK[])")
            raw = b"".join(x[1] for x in md if isinstance(x, tuple))
            msg = _email.message_from_bytes(raw)
            body = ""
            for part in (msg.walk() if msg.is_multipart() else [msg]):
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode("utf-8", "replace")
            subj = str(msg.get("Subject") or "")
            print(f"  run email: {subj[:88]}")
            # Count the stated reasons. Each pattern is the executor's own wording, so a zero here
            # means that cause did not fire - not that the parse failed. A parse that finds NOTHING
            # at all is reported as unverified rather than as three zeros.
            # The executor's OWN go=False wording, taken from the r["live"]["why"] strings at
            # executor.py:4397-4447, so each count is the real reason and not a guess.
            pats = {
                "PRICE: no live book has the alert number or better":
                    r"no live book has the alert number or better",
                "DUPLICATE: play already has an order/intent today (LIVEKEYS)":
                    r"already submitted or resting|already sent a live order|duplicate",
                "LANE CAP: play cap or daily risk reached":
                    r"play cap|daily risk|daily stop",
                "LANE 2 is dry-run only":
                    r"Lane 2 is dry-run only",
                "INTENT LATCH: unresolved write-ahead intent":
                    r"INTENT CLEARED [0-9a-f]{12,}|unresolved intent",
                "NOVIG HOLD: EXEC_NOVIG_SUBMIT off":
                    r"EXEC_NOVIG_SUBMIT is not on",
                "NOVIG HOLD: no dispatch credential":
                    r"NOVIG_DISPATCH_TOKEN",
                "ORDER REFUSED notices":
                    r"ORDER REFUSED",
                "HELD (positions unreadable)":
                    r"\bHELD\b",
            }
            hits = {k: len(re.findall(v, body, re.I)) for k, v in pats.items()}
            if not any(hits.values()):
                print("  the run email matched none of the executor's own reason strings -")
                print("  CANNOT VERIFY the breakdown from it; do not read these as three zeros")
            else:
                for k, n in hits.items():
                    print(f"    {n:>4}  {k}")
            m = re.search(r"(\d+)\s+would go live", subj)
            sk = re.search(r"(\d+)\s+skipped", subj)
            wb = re.search(r"(\d+)\s+would bet", subj)
            print()
            print(f"  subject says: would_go_live={m.group(1) if m else '?'}  "
                  f"would_bet={wb.group(1) if wb else '?'}  skipped={sk.group(1) if sk else '?'}")
            print("  qualification failures are the 'skipped' count; a play that qualifies but")
            print("  cannot be submitted appears in 'would bet' without reaching 'would go live'.")
    except Exception as e:
        print(f"  run-email breakdown unavailable ({type(e).__name__}: {str(e)[:70]})")
    finally:
        try:
            ex.imap_close(M)
        except Exception:
            pass

    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
