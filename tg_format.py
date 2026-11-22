#!/usr/bin/env python3
"""Uniform Telegram message decoration: a colour symbol and a bold header on EVERY message.

Peter, Nov 22 2026: "Can you make telegram more bold or have this color symbols... All the time
not just a few." Today only some messages (the HR1 alerts) carry bold and a symbol; fill lines,
[R1] status notices and NEW POSITIONS summaries arrive plain.

    RED     status unknown / verify / conflict / failure
    YELLOW  manual action for Peter (HR1 alerts already carry it - kept, not doubled)
    GREEN   fill confirmed / matched / placed
    BLUE    positions and balance summaries, and anything else

FORMATTING ONLY. Nothing here reads or changes what is sent, selection, sizing, placement or
routing. The decorator is a pure function of the message text.

THE SAFETY PROPERTY THAT MATTERS: a formatting failure must never cost a notification. Telegram
answers 400 (and {"ok": false}) for malformed HTML, so a stray '<' in a message would otherwise
silently suppress an alert. Every sender therefore sends `html` first and falls back to `plain`
on any refusal - `plain` carries the symbol but no markup and cannot be rejected for entities.
That is why decorate() returns BOTH forms rather than one string.
"""

RED, YELLOW, GREEN, BLUE = "\U0001F534", "\U0001F7E1", "\U0001F7E2", "\U0001F535"
SYMBOLS = (RED, YELLOW, GREEN, BLUE, "\U0001F7E0", "⚪", "⚫")

# Checked in this order. RED first on purpose: a problem inside an otherwise ordinary message is
# the thing Peter must not scroll past. HR1 alerts already start with their own symbol, so
# already_marked() returns them untouched before any of this runs.
_RED = ("unknown", "verify", "conflict", "failed", "failure", "refused", "error", "mismatch",
        "not configured", "no live feed", "stale", "timeout", "discrepanc")
_YELLOW = ("hr1", "manual", "action needed", "action required", "your move", "please ")
_GREEN = ("filled", "fill confirmed", "matched", "placed", "confirmed", " fill ", "fills")
_BLUE = ("positions", "balance", "summary", "recap", "ledger")


def esc(t):
    """HTML-escape for Telegram parse_mode=HTML. Ampersand first or it double-escapes."""
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def already_marked(text):
    """True when the message already opens with a colour symbol - HR1's existing yellow, say."""
    return str(text).lstrip()[:1] in SYMBOLS


def classify(text):
    """Pick the symbol from the message body. A wrong symbol is cosmetic; it never gates a send."""
    t = " " + str(text).lower() + " "
    for words, sym in ((_RED, RED), (_YELLOW, YELLOW), (_GREEN, GREEN), (_BLUE, BLUE)):
        if any(w in t for w in words):
            return sym
    return BLUE          # default: informational. Never GREEN - that would read as a confirmed fill.


def decorate(text, body_is_html=False):
    """Return (html, plain) for one message.

    html  - symbol + <b>first line</b> + the rest, sent with parse_mode=HTML.
    plain - symbol + the original text, byte-for-byte after the symbol. The fallback.

    body_is_html=True means the CALLER already built HTML (sharp_monitor and liquidity_monitor
    have callers that pass html=True). Its markup is left completely alone - we only prefix the
    symbol - because escaping it here would print tags at Peter instead of bolding.
    """
    s = str(text)
    if already_marked(s):
        return s, s                      # idempotent: never stack a second symbol on HR1
    sym = classify(s)
    if body_is_html:
        return f"{sym} {s}", f"{sym} {s}"
    head, sep, rest = s.partition("\n")
    html = f"{sym} <b>{esc(head)}</b>" + (f"\n{esc(rest)}" if sep else "")
    return html, f"{sym} {s}"
