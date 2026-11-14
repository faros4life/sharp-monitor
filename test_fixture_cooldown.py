#!/usr/bin/env python3
"""
STAGE 4 REGRESSION (Peter, Nov 13 2026): one extra fixture refresh per league per evening, and
not one more.

The Nov 12 failure: three selections sat unscored reading "no fixture yet - no fresh lookup this
run (6 h cooldown), retry not counted" while NBA's newest cached fixture started an hour before
the games in question and the league had been fetched two hours earlier. The cooldown refused the
only call that could have resolved them.

Cost control is the thing under test as much as the fix: the allowance must be consumed only when
a call actually bills, must be once per league per ET DAY, and must never fire when nothing is
pending past the cache. No network: api() and bill() are stubbed and the calls are counted.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_ledger as cl   # noqa: E402

BAD = []
NOW = datetime(2026, 11, 13, 23, 30, 0, tzinfo=timezone.utc)   # 18:30 ET on Nov 13


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


class Harness:
    """Stubs every billable path so a call is counted, never made."""

    def __init__(self, fixtures=None, can_bill=True):
        self.calls = []
        self.billed = 0
        self.fixtures = fixtures if fixtures is not None else [
            {"fixtureId": "new1", "startTime": "2026-11-14T01:00:00Z",
             "participant1Name": "Dallas Mavericks", "participant2Name": "Minnesota Timberwolves"}]
        self.can_bill = can_bill
        self._saved = {}

    def __enter__(self):
        for n in ("api", "bill", "can_bill", "tournament"):
            self._saved[n] = getattr(cl, n)
        cl.api = lambda path, billable, **kw: (self.calls.append((path, kw)) or self.fixtures)
        cl.bill = lambda st, now, n=1: self.__setattr__("billed", self.billed + n)
        cl.can_bill = lambda st, now, n=1: self.can_bill
        cl.tournament = lambda st, now, lg: 132
        cl.FX_LOG.clear()
        return self

    def __exit__(self, *a):
        for n, v in self._saved.items():
            setattr(cl, n, v)


def state(last_fetch_hours_ago=2.0, extra_day=None, newest="2026-11-13T00:00:00Z"):
    st = {"bets": {}, "fixtures": {}, "fx_last": {}}
    if last_fetch_hours_ago is not None:
        st["fx_last"]["NBA"] = cl.iso(NOW - timedelta(hours=last_fetch_hours_ago))
    if extra_day:
        st["fx_extra"] = {"NBA": extra_day}
    if newest:
        st["fixtures"]["old1"] = {"lg": "NBA", "start": newest,
                                 "p1": "Boston Celtics BOS", "p2": "New York Knicks NYK"}
    return st


def lo_hi():
    return (NOW - timedelta(days=2)).astimezone(cl.ET), (NOW + timedelta(days=1)).astimezone(cl.ET)


def main():
    lo, hi = lo_hi()

    print("1. inside the cooldown with nothing past the cache: NO call (unchanged behaviour)")
    with Harness() as h:
        st = state(last_fetch_hours_ago=2.0)
        ok = cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=False)
        check("no fresh lookup", ok is False)
        check("no billable call", h.calls == [], h.calls)
        check("log says cooldown", any("6h cooldown" in x for x in cl.FX_LOG), cl.FX_LOG)

    print("2. inside the cooldown WITH a game past the cache: exactly one extra call")
    with Harness() as h:
        st = state(last_fetch_hours_ago=2.0)
        ok = cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True)
        check("fresh lookup happened", ok is True)
        check("exactly one /fixtures call", [c[0] for c in h.calls] == ["/fixtures"], h.calls)
        check("it billed once", h.billed == 1, h.billed)
        check("allowance recorded for today", st["fx_extra"]["NBA"] == "2026-11-13", st.get("fx_extra"))
        check("log marks it EXTRA", any("EXTRA" in x for x in cl.FX_LOG), cl.FX_LOG)
        check("the new fixture was stored", "new1" in st["fixtures"], list(st["fixtures"]))
        check("the already-downloaded fixture is kept", "old1" in st["fixtures"], list(st["fixtures"]))

    print("3. the allowance is spent: a second attempt the same day makes NO call")
    with Harness() as h:
        st = state(last_fetch_hours_ago=2.0, extra_day="2026-11-13")
        ok = cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True)
        check("refused", ok is False)
        check("no call", h.calls == [], h.calls)
        check("log says the extra is spent", any("spent" in x for x in cl.FX_LOG), cl.FX_LOG)

    print("4. yesterday's allowance does not block today")
    with Harness() as h:
        st = state(last_fetch_hours_ago=2.0, extra_day="2026-11-12")
        check("today's extra is allowed", cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True) is True)
        check("one call", len(h.calls) == 1, h.calls)

    print("5. the allowance is NOT consumed when the credit gate would refuse")
    with Harness(can_bill=False) as h:
        st = state(last_fetch_hours_ago=2.0)
        check("no lookup", cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True) is False)
        check("no call", h.calls == [], h.calls)
        check("allowance untouched", "NBA" not in (st.get("fx_extra") or {}), st.get("fx_extra"))
        check("log names the gate", any("credit gate" in x for x in cl.FX_LOG), cl.FX_LOG)

    print("6. outside the cooldown nothing changes and no allowance is used")
    with Harness() as h:
        st = state(last_fetch_hours_ago=9.0)
        check("normal lookup", cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True) is True)
        check("one call", len(h.calls) == 1, h.calls)
        check("allowance untouched", "NBA" not in (st.get("fx_extra") or {}), st.get("fx_extra"))
        check("log does not say EXTRA", not any("EXTRA" in x for x in cl.FX_LOG), cl.FX_LOG)

    print("7. a league never fetched is not treated as cooled down")
    with Harness() as h:
        st = state(last_fetch_hours_ago=None)
        check("first fetch proceeds", cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=False) is True)
        check("one call", len(h.calls) == 1, h.calls)

    print("8. a failed call does not pretend to have refreshed")
    with Harness() as h:
        h.fixtures = {"_error": 500, "_body": "boom"}
        st = state(last_fetch_hours_ago=2.0)
        check("returns False on an API error", cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True) is False)
        check("but the call is logged as billed", any("1 billable" in x for x in cl.FX_LOG), cl.FX_LOG)
        check("cache unchanged by a failed call", "new1" not in st["fixtures"], list(st["fixtures"]))

    print("9. FX_LOG records every decision, so usage is always visible")
    with Harness():
        cl.FX_LOG.clear()
        st = state(last_fetch_hours_ago=2.0)
        cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=False)
        cl.refresh_fixtures(st, NOW, "NBA", lo, hi, allow_extra=True)
        check("two decisions, two lines", len(cl.FX_LOG) == 2, cl.FX_LOG)

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all Stage 4 fixture-cooldown checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
