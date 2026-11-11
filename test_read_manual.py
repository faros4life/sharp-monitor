"""Nov 11: read_manual() cost 202.0s - 50.7% of the run, the largest item in PERF - to read about
eight one-line notes.

CAUSE, not a guess: gsearch() does query.replace('"', ''), stripping the phrase quotes off
'subject:"Bets manual" newer_than:3d'. Gmail then read it as "subject contains Bets" AND "the
message contains manual anywhere", which matches every Bets LIVE:/signal:/watchdog: email of the
last three days - the run emails themselves say "MANUAL ONLY" and "manual bets" - and each was
then fetched whole, 38KB ledgers included.

Now an IMAP SUBJECT + SINCE search with a header prefix re-check, the pattern bot_orders() already
uses because IMAP SUBJECT is a substring match (reading dry-run mail as live was a real bug on
Oct 27).

What these tests pin: the broad X-GM-RAW search is gone, the window is bounded, a message whose
subject merely CONTAINS the phrase is rejected, and - the part that protects money - Peter's notes
still produce the duplicate/conflict holds that stop the bot betting a game he placed by hand.
"""
import email as _email
import executor as ex

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


def msg(subject, body):
    return (f"From: pgoranites@gmail.com\r\nTo: pgoranites+bets@gmail.com\r\n"
            f"Subject: {subject}\r\nDate: Wed, 11 Nov 2026 10:16:10 -0500\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n").encode()


MANUAL_LINE = ('MANUAL: {"sport": "NBA", "game": "Los Angeles Lakers @ Milwaukee Bucks", '
               '"bet": "Under 230.5 (-116)", "book": "ProphetX"}')

# A 38KB run email that mentions the word "manual" - exactly what the old query dragged in.
BIG_RUN_EMAIL = msg("Bets LIVE: 0 placed, 1 would go live",
                    "Hard Rock remains MANUAL ONLY - never auto-bet.\n" + ("x" * 38000))


class FakeIMAP:
    def __init__(self, corpus):
        self.corpus = corpus          # uid -> raw bytes
        self.searches = []
        self.fetched = []

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            self.searches.append(a)
            if a[0] == "X-GM-RAW":
                # The old path. Present only so the test can prove it is NOT used any more.
                return "OK", [b" ".join(self.corpus)]
            # IMAP SUBJECT is a substring match, modelled faithfully. Args arrive as
            # (None, "SUBJECT", '"Bets manual"', "SINCE", date), so the phrase follows the keyword.
            want = ""
            for i, x in enumerate(a):
                if x == "SUBJECT" and i + 1 < len(a):
                    want = str(a[i + 1]).strip('"')
                    break
            hits = []
            for u, raw in self.corpus.items():
                subj = _email.message_from_bytes(raw).get("Subject") or ""
                if want.lower() in subj.lower():
                    hits.append(u)
            return "OK", [b" ".join(u.encode() for u in hits)]
        u = a[0] if isinstance(a[0], str) else a[0].decode()
        self.fetched.append(u)
        return "OK", [(b"h", self.corpus[u])]


CORPUS = {
    "1": msg("Bets manual", MANUAL_LINE),
    "2": BIG_RUN_EMAIL,                                  # must NOT be fetched
    "3": msg("Bets signal: NBA UNDER lane", "nothing about manual bets here"),
    "4": msg("Re: Bets manual note from someone else", MANUAL_LINE.replace("Lakers", "Celtics")),
}

ex.MANUAL_HELD.clear()
M = FakeIMAP(CORPUS)
ex.read_manual(M)

# ---------------------------------------------------------------- the broad search is gone
assert all(s[0] != "X-GM-RAW" for s in M.searches), \
    f"read_manual still uses the quote-stripping X-GM-RAW path: {M.searches}"
ck("exactly one search", len(M.searches), 1)
ck("it is an IMAP SUBJECT search", M.searches[0][1], "SUBJECT")
assert "SINCE" in M.searches[0], f"the search must be date-bounded: {M.searches[0]}"
CHECKS.append(("the search is bounded by SINCE", True, True))

# ---------------------------------------------------------------- the 38KB run email is untouched
assert "2" not in M.fetched, "the big run email was fetched again - that was the 202 seconds"
assert "3" not in M.fetched, "an unrelated Bets email was fetched"
CHECKS.append(("no run email or ledger is fetched", M.fetched, M.fetched))

# ---------------------------------------------------------------- substring match is re-checked
# uid 4's subject CONTAINS "Bets manual" but does not START with it, so its note must be ignored.
keys = set(ex.MANUAL_HELD)
celtics = ex.derive_key({"sport": "NBA", "game": "Los Angeles Celtics @ Milwaukee Bucks",
                         "bet": "Under 230.5 (-116)"})
assert not any("Celtics" in k for k in keys), \
    f"a subject that merely contains the phrase was trusted: {keys}"
CHECKS.append(("a non-prefix subject is rejected", True, True))

# ---------------------------------------------------------------- the money guard still works
lakers = {"sport": "NBA", "game": "Los Angeles Lakers @ Milwaukee Bucks",
          "bet": "Under 230.5 (-119)"}
dk = ex.derive_key(lakers)
ck("Peter's manual bet still registers a duplicate hold", ex.MANUAL_HELD.get(dk), "duplicate")
ck("and the opposite side is held as a conflict",
   ex.MANUAL_HELD.get(ex.opposite_key(lakers)), "conflict")
# The price in the note (-116) differs from the bot's play (-119) and must not matter: derive_key
# is sport|game|market|side, with no price and no line.
ck("the hold ignores the price difference",
   ex.MANUAL_HELD.get(ex.derive_key(dict(lakers, bet="Under 231.5 (-130)"))), "duplicate")

# ---------------------------------------------------------------- degenerate cases
ex.MANUAL_HELD.clear()
ex.read_manual(FakeIMAP({}))
ck("no notes -> no holds", dict(ex.MANUAL_HELD), {})

ex.MANUAL_HELD.clear()
ex.read_manual(FakeIMAP({"1": msg("Bets manual", "MANUAL: {not json at all}")}))
ck("an unreadable MANUAL line holds nothing", dict(ex.MANUAL_HELD), {})

ex.MANUAL_HELD.clear()
ex.read_manual(FakeIMAP({"1": msg("Bets manual", "just a note, no MANUAL line")}))
ck("a note with no MANUAL line holds nothing", dict(ex.MANUAL_HELD), {})

print(f"PASS  test_read_manual.py  {len(CHECKS)} checks")
