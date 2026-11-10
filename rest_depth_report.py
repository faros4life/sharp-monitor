#!/usr/bin/env python3
"""
RESTING-DEPTH MEASUREMENT (Nov 10). Read-only, 0 OddsPapi credits, MANUAL DISPATCH ONLY.

THE ONE QUESTION IT ANSWERS: how often do BOTH Novig and Kalshi lack the exact alert line, so a
third resting venue would have been the only way to rest at all?

WHY IT EXISTS. Peter asked whether to add Polymarket US to REST_BOOKS as a third venue. The maker
case died with the PDI test - participateDontInitiate is dropped by the venue, so Polymarket is a
taker there at -116.8 on a -110 screen, the worst of the three. That leaves exactly one argument
for adding it: DEPTH, on the plays where neither of the first two can rest. Against that sits a
real asymmetry - Polymarket is the only venue whose expiry does not work, so every bid needs an
active cancel and a failed cancel leaves money resting all day.

Nobody knew the frequency. Claude and Muse independently landed on the same conclusion - leave the
chain at Novig, Kalshi - and both said the flip should never happen on a read when it can happen
on a measurement. This is the measurement.

NOT A NEW SCAN OR LENS, and deliberately not scheduled: a one-off diagnostic for a pending
decision, run by hand, registering nothing. The idea freeze stands.

HOW. The executor already records the answer and nobody had read it. Every run's email carries a
LEDGER row per play, and rest_bid writes its refusal into live_rest.reason - including, per book,
"<Book>: no exact-line market". Gmail is the registry here as it is for bot_orders(), so this
reads the executor's own emails rather than re-deriving anything or spending a credit.
"""
import collections
import email
import email.header
import json
import os
import sys

import executor as ex

DAYS = int(os.environ.get("DEPTH_DAYS", "") or "7")
SUBJECTS = ('"Bets dry run:"', '"Bets LIVE:"')


def say(s):
    print(s, flush=True)


def ledger_rows(M, subject, since):
    """Every LEDGER row from the executor's own emails with this subject prefix."""
    rows, mails = [], 0
    typ, data = M.uid("SEARCH", None, "SUBJECT", subject, "SINCE", since)
    if typ != "OK":
        return rows, 0
    want = subject.strip('"')
    for uid in (data[0].split() if data and data[0] else []):
        typ, d = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not d or not d[0]:
            continue
        raw = d[0][1]
        # IMAP SUBJECT is a SUBSTRING match - the Oct 27 bug that read dry-run mail as live. The
        # real header is re-checked before the body is trusted.
        subj = str(email.header.make_header(email.header.decode_header(
            email.message_from_bytes(raw).get("Subject") or "")))
        if not subj.startswith(want):
            continue
        txt = ex.body_text(raw)
        # Extracted exactly the way executor.bot_orders() already does it (rfind the header, then
        # raw_decode from the first bracket). My first draft used a line-anchored regex, which is
        # a second way of doing a solved thing - and would have broken the moment the ledger JSON
        # wrapped or something else in the body looked like a list on its own line.
        i = txt.rfind("LEDGER (machine-readable")
        if i < 0:
            continue
        try:
            parsed, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
        except Exception:
            continue
        rows.extend(parsed)
        mails += 1
    return rows, mails


def main():
    since = (__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
             - __import__("datetime").timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say(f"RESTING-DEPTH MEASUREMENT | last {DAYS} days | read-only, 0 credits")
    say("Question: how often did BOTH Novig and Kalshi lack the exact alert line?\n")

    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in SUBJECTS:
            r, n = ledger_rows(M, s, since)
            rows.extend(r)
            mails += n
    finally:
        ex.imap_close(M)
    say(f"read {mails} executor email(s), {len(rows)} ledger row(s)")

    # One row per play KEY, newest wins: the executor re-reports a play every run until it is
    # decided, so counting raw rows would weight a long-lived play dozens of times and the
    # frequency would be meaningless.
    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if k:
            seen[k] = r
    say(f"{len(seen)} distinct play(s) after de-duplicating by key\n")

    attempted = [r for r in seen.values() if (r.get("live_rest") or {}).get("status")]
    placed = [r for r in attempted if (r.get("live_rest") or {}).get("status") == "placed"]
    refused = [r for r in attempted if (r.get("live_rest") or {}).get("status") == "refused"]

    say(f"resting ATTEMPTED on {len(attempted)} play(s): {len(placed)} placed, {len(refused)} refused")
    if not attempted:
        say("\nNo resting attempts in the window - nothing to measure. Widen DEPTH_DAYS.")
        return

    # The question: among refusals, how many were BOTH books lacking the exact line - the only
    # case a third venue could have rescued? A refusal for any other reason (under the minimum,
    # a guard, an ambiguous market) would not have been helped by adding Polymarket.
    both, one_only, other = 0, 0, collections.Counter()
    for r in refused:
        why = ((r.get("live_rest") or {}).get("reason") or "")
        nov = "Novig: no exact-line market" in why
        kal = "Kalshi: no exact-line market" in why
        if nov and kal:
            both += 1
        elif nov or kal:
            one_only += 1
        else:
            other[why[:70] or "(no reason recorded)"] += 1

    say("")
    say("=" * 78)
    say("WOULD A THIRD RESTING VENUE HAVE HELPED?")
    say("=" * 78)
    say(f"  both books lacked the exact line   {both:4}   <- only these could a 3rd venue rescue")
    say(f"  only one book lacked it            {one_only:4}   (the other could already rest)")
    say(f"  refused for some other reason      {sum(other.values()):4}   (a 3rd venue changes nothing)")
    for k, n in other.most_common(6):
        say(f"        {n:3}  {k}")

    pct = 100.0 * both / max(len(attempted), 1)
    say("")
    say(f"So {both} of {len(attempted)} resting attempts ({pct:.1f}%) are the case that argues for a "
        f"third venue.")
    say("")
    # The threshold is stated, not implied, so the decision does not drift to whoever reads it.
    if both == 0:
        say("VERDICT: zero. Adding Polymarket US to REST_BOOKS would have changed NOTHING in this")
        say("  window, while adding the one venue whose expiry does not work and whose bids need an")
        say("  active cancel. Leave the chain at (novig, kalshi).")
    elif pct < 5:
        say("VERDICT: marginal. A third venue would have rescued under 5% of attempts - not worth")
        say("  taking on the only venue where a failed cancel leaves a bid resting all day.")
        say("  Leave the chain at (novig, kalshi).")
    else:
        say(f"VERDICT: {pct:.1f}% is material. Worth Peter weighing the depth gain against the")
        say("  cancel risk - note that Polymarket would be entering as a TAKER (-116.8 at a -110")
        say("  screen, worst of the three), so it only helps where resting is otherwise impossible,")
        say("  never where it is merely cheaper.")
    say("")
    say("Counts only. No prices, stakes, balances or order ids in this output.")


if __name__ == "__main__":
    sys.exit(main())
