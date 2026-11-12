#!/usr/bin/env python3
"""READ-ONLY historical audit of the executor ledgers for the line-value replay (Nov 12, 2026).

Reads Gmail over IMAP (mailbox opened readonly), keeps only emails whose real Subject STARTS WITH the executor's
own prefixes (IMAP SUBJECT search is a substring match), and hands the bodies to line_value_replay. It prints
COUNTS ONLY: no game, line, price, stake, balance or key. It imports no execution code, sends no email, and
writes nothing. Detail stays in the private mailbox.

Env: GMAIL_ADDRESS, GMAIL_APP_PASSWORD, AUDIT_DAYS (default 14).
"""
import email
import email.header
import imaplib
import os
import sys
from datetime import datetime, timedelta, timezone

import line_value_replay as rp

PREFIXES = ("Bets LIVE:", "Bets dry run:")


def body_text(raw):
    msg = email.message_from_bytes(raw)
    for p in (msg.walk() if msg.is_multipart() else [msg]):
        if p.get_content_type() == "text/plain":
            return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="ignore")
    return ""


def subject(raw):
    return str(email.header.make_header(email.header.decode_header(email.message_from_bytes(raw).get("Subject") or "")))


def fetch_texts(days):
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
    M.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    texts, seen, skipped = [], 0, 0
    for pre in ("Bets LIVE:", "Bets dry run:"):
        typ, data = M.uid("SEARCH", None, "SUBJECT", f'"{pre}"', "SINCE", since)
        if typ != "OK":
            raise SystemExit("search failed")
        for uid in (data[0].split() if data and data[0] else []):
            typ, d = M.uid("FETCH", uid, "(BODY.PEEK[])")   # PEEK: never changes a flag
            if typ != "OK" or not d or not d[0]:
                skipped += 1
                continue
            raw = d[0][1]
            if not subject(raw).startswith(PREFIXES):
                continue
            seen += 1
            texts.append(body_text(raw))
    try:
        M.logout()
    except Exception:
        pass
    return texts, seen, skipped


def main():
    days = int(os.environ.get("AUDIT_DAYS") or 14)
    texts, seen, skipped = fetch_texts(days)
    with_ledger = sum(1 for t in texts if rp.MARK in t)
    print(f"emails read: {seen} (window {days}d), with a ledger block: {with_ledger}, fetch failures: {skipped}")
    print(rp.render(rp.report(texts), detail=False))
    det = rp.fill_details(texts)
    print("  fills: " + ", ".join(f"{k} {v}" for k, v in sorted(rp.fill_counts(det).items())))   # counts only in the log
    os.makedirs("summary", exist_ok=True)
    import csv
    with open("summary/line_value_audit_fills.csv", "w", newline="") as fh:   # lines and prices, never stakes or balances
        w = csv.DictWriter(fh, fieldnames=list(det[0]) if det else ["key"])
        w.writeheader()
        w.writerows(sorted(det, key=lambda d: (not d["is_minus_130"], d["alert_utc"] or "")))


if __name__ == "__main__":
    sys.exit(main())
