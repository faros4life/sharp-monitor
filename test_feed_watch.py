"""Feed watch: replays the Nov 26 outage and checks warnings, recovery and quota levels. Offline."""
from datetime import datetime, timedelta, timezone
import feed_watch as fw

FAILED = []


def ok(n, c):
    print(("PASS  " if c else "FAIL  ") + n)
    if not c:
        FAILED.append(n)


def r(mins_ago, concl, now, status="completed"):
    t = (now - timedelta(minutes=mins_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"createdAt": t, "updatedAt": t, "status": status, "conclusion": concl}


NOW = datetime(2026, 11, 26, 13, 0, tzinfo=timezone.utc)   # 8:00 AM ET... use 10 AM ET for active hours
NOW = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
liq = [r(3, "success", NOW)]
exe = [r(4, "success", NOW)]
# Nov 26: every alert-feed run failing with 401
outage = [r(m, "failure", NOW) for m in (0, 5, 10, 15, 20, 25)]
bad = fw.evaluate(NOW, outage, liq, exe, 72, 100000, True)
ok("outage: feed failure raised, with the quota cause", "FEED_FAIL" in bad and "401/429" in bad["FEED_FAIL"])
ok("outage: feed gap raised too", "FEED_GAP" in bad)
ok("outage: quota 80% raised (72 left of 100,000)", "QUOTA_80" in bad)
st, cl = fw.transitions({}, bad)
ok("first sight alerts every condition once", set(st) == set(bad) and not cl)
st2, cl2 = fw.transitions(bad, bad)
ok("an ongoing condition does not alert again", not st2 and not cl2)
healthy = [r(m, "success", NOW) for m in (0, 5, 10)]
good = fw.evaluate(NOW, healthy, liq, exe, 4_999_000, 5_000_000, None)
st3, cl3 = fw.transitions(bad, good)
ok("recovery: every condition clears with a RECOVERED notice", not good and set(cl3) == set(bad))
ok("one failed run alone is not an alarm", "FEED_FAIL" not in fw.evaluate(NOW, [r(0, "failure", NOW)] + healthy,
                                                                          liq, exe, None))
ok("liquidity feed gap is caught", "LIQ_GAP" in fw.evaluate(NOW, healthy, [r(40, "success", NOW)], exe, None))
ok("executor gap is caught", "EXEC_GAP" in fw.evaluate(NOW, healthy, liq, [r(40, "success", NOW)], None))
night = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)   # 4 AM ET
ok("no gap alarms overnight", not fw.evaluate(night, [r(120, "success", night)], [r(120, "success", night)],
                                               [r(120, "success", night)], None))
q50 = fw.evaluate(NOW, healthy, liq, exe, 2_400_000, 5_000_000)
q70 = fw.evaluate(NOW, healthy, liq, exe, 1_400_000, 5_000_000)
ok("quota 50% then 70%", "QUOTA_50" in q50 and "QUOTA_70" in q70)
s4, c4 = fw.transitions(q50, q70)
ok("stepping 50 -> 70 alerts 70 and is NOT a false recovery of 50", "QUOTA_70" in s4 and not c4)
print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
