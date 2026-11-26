#!/usr/bin/env python3
"""UNRECOVERABLE OBSERVATION GAPS - periods where the feed was not watching.

Peter, Nov 26 2026: "Clearly mark the missing Thanksgiving morning data as an unrecoverable
observation gap. Exclude that period from opportunity-frequency and feed-availability research
where appropriate, but retain it in operational uptime reporting."

The distinction is the whole point, and it cuts both ways:

  RESEARCH            "how often does a qualifying play appear?" must EXCLUDE these windows.
                      Counting a blind hour as an hour with no opportunities biases every rate
                      downward, and silently - the denominator looks fine.

  UPTIME / OPERATIONS "was the system working?" must KEEP them. A gap is exactly the failure
                      that reporting exists to surface; excluding it would flatter the record.

These rows are NOT recoverable. The upstream fetch never happened, so no amount of backfill
reconstructs what would have alerted: the odds at those moments were never requested and the
provider's historical endpoints do not answer "what would my alert rule have fired on". Treat the
window as unobserved, never as observed-and-empty.
"""
from datetime import datetime, timezone

# (start_utc, end_utc, what, why it is unrecoverable)
GAPS = [
    ("2026-11-26T11:00:00Z", "2026-11-26T15:40:00Z",
     "alert feed (The Odds API) down - credit quota exhausted",
     "57 consecutive sharp-monitor failures over 4h40m, 6:00-10:40 AM ET Thanksgiving. The odds "
     "were never fetched, so the alerts that would have fired were never computed and cannot be "
     "reconstructed. Morning NCAAB and the early NFL slate fell inside it."),
]


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def in_gap(when, gaps=None):
    """True when `when` (aware datetime or ISO string) falls inside a known blind window."""
    if when is None:
        return False
    w = _t(when) if isinstance(when, str) else when
    if w.tzinfo is None:
        w = w.replace(tzinfo=timezone.utc)
    return any(_t(a) <= w < _t(b) for a, b, _, _ in (gaps or GAPS))


def observed_minutes(start, end, gaps=None):
    """Minutes in [start, end) the feed was actually WATCHING - the honest denominator for any
    per-hour or per-day opportunity rate. Overlapping gaps are merged so none is counted twice."""
    s, e = (_t(start) if isinstance(start, str) else start), (_t(end) if isinstance(end, str) else end)
    if e <= s:
        return 0.0
    spans = sorted(((max(s, _t(a)), min(e, _t(b))) for a, b, _, _ in (gaps or GAPS)), key=lambda x: x[0])
    blind, last = 0.0, s
    for a, b in spans:
        if b <= a:
            continue
        a = max(a, last)
        if b > a:
            blind += (b - a).total_seconds() / 60
            last = b
    return round((e - s).total_seconds() / 60 - blind, 3)


def describe():
    return [f"{a} -> {b}  {what}" for a, b, what, _ in GAPS]


if __name__ == "__main__":
    for line in describe():
        print(line)
    print(f"\n{len(GAPS)} recorded gap(s); research excludes them, uptime reporting keeps them.")
