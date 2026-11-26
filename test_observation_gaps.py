"""The Thanksgiving blind window must be excluded from research rates and KEPT in uptime.

Peter, Nov 26 2026. The trap this guards is quiet: an hour the feed never watched looks exactly
like an hour with no qualifying plays, so every opportunity rate silently reads low while the
denominator looks healthy."""
from datetime import datetime, timedelta, timezone

import observation_gaps as og

FAILED = []
UTC = timezone.utc


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


# --- the outage is on the record, with its real bounds ------------------------------------------
ok("exactly one gap is recorded", len(og.GAPS) == 1, len(og.GAPS))
a, b, what, why = og.GAPS[0]
ok("it starts at 11:00Z (6:00 AM ET)", a == "2026-11-26T11:00:00Z", a)
ok("it ends at 15:40Z (10:40 AM ET)", b == "2026-11-26T15:40:00Z", b)
ok("the window is 4h40m", (og._t(b) - og._t(a)) == timedelta(hours=4, minutes=40))
ok("the cause is named", "quota" in what.lower())
ok("why it cannot be recovered is stated", "never fetched" in why and "cannot be reconstructed" in why)

# --- membership ---------------------------------------------------------------------------------
ok("a timestamp inside is blind", og.in_gap("2026-11-26T13:00:00Z"))
ok("the start is inside", og.in_gap("2026-11-26T11:00:00Z"))
ok("the end is OUTSIDE (half-open)", not og.in_gap("2026-11-26T15:40:00Z"))
ok("a minute before is outside", not og.in_gap("2026-11-26T10:59:00Z"))
ok("the recovery minute is outside", not og.in_gap("2026-11-26T15:41:00Z"))
ok("another day is outside", not og.in_gap("2026-11-25T13:00:00Z"))
ok("None is not blind", not og.in_gap(None))
ok("a naive datetime is read as UTC", og.in_gap(datetime(2026, 11, 26, 13, 0)))
ok("an aware datetime works", og.in_gap(datetime(2026, 11, 26, 13, 0, tzinfo=UTC)))

# --- the honest denominator ----------------------------------------------------------------------
day = ("2026-11-26T00:00:00Z", "2026-11-27T00:00:00Z")
ok("a full day is 1440 minutes of wall time", (og._t(day[1]) - og._t(day[0])).total_seconds() / 60 == 1440)
ok("but only 1160 were observed", og.observed_minutes(*day) == 1160.0, og.observed_minutes(*day))
ok("a window entirely inside the gap observed nothing",
   og.observed_minutes("2026-11-26T12:00:00Z", "2026-11-26T13:00:00Z") == 0.0)
ok("a window entirely outside is untouched",
   og.observed_minutes("2026-11-25T00:00:00Z", "2026-11-25T01:00:00Z") == 60.0)
ok("a window overlapping the start is clipped",
   og.observed_minutes("2026-11-26T10:30:00Z", "2026-11-26T11:30:00Z") == 30.0)
ok("a window overlapping the end is clipped",
   og.observed_minutes("2026-11-26T15:10:00Z", "2026-11-26T16:10:00Z") == 30.0)
ok("a backwards window is 0, not negative",
   og.observed_minutes("2026-11-26T13:00:00Z", "2026-11-26T12:00:00Z") == 0.0)

# overlapping gaps must not be double-counted out of the denominator
two = [("2026-11-26T11:00:00Z", "2026-11-26T13:00:00Z", "x", "y"),
       ("2026-11-26T12:00:00Z", "2026-11-26T14:00:00Z", "x", "y")]
ok("overlapping gaps are merged, not subtracted twice",
   og.observed_minutes("2026-11-26T11:00:00Z", "2026-11-26T14:00:00Z", two) == 0.0,
   og.observed_minutes("2026-11-26T11:00:00Z", "2026-11-26T14:00:00Z", two))

# --- uptime KEEPS the gap: observed_minutes is opt-in, never applied by default -------------------
src = open("observation_gaps.py", encoding="utf-8").read()
ok("research-vs-uptime distinction is documented", "UPTIME" in src and "RESEARCH" in src)
ok("the module states the gap is unobserved, not observed-and-empty",
   "never as observed-and-empty" in src)
ok("nothing here mutates alerts or results", "alerts.json" not in src and "result" not in src.lower().split("RESEARCH")[0])

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
