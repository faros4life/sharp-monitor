"""A rewritten alerts.json is not proof of fresh data. Nov 26, 2026 (Peter).

The Odds API quota ran out at 6:00 AM ET and the alert feed failed 57 runs in a row over 4h40m.
Nothing caught it: deadman watches the EXECUTOR, feed_watch did not exist until 12:09, and every
remaining signal - workflow conclusion, file mtime, "0 alerts today" - looks identical whether the
feed is healthy and quiet or dead.

So the feed now records whether the UPSTREAM FETCH itself succeeded, and everything downstream keys
on that instead of on the run exiting 0.

Three cases must stay distinguishable, because they have different remedies:
    HEALTHY    fetched fine, events seen, maybe zero alerts   -> nothing to do
    NO_EVENTS  fetched fine, zero events came back            -> look at the provider
    FAILED     the fetch did not complete                     -> the feed is down
"""
import datetime
import json
import os
import tempfile

import feed_watch as fw

FAILED = []
UTC = datetime.timezone.utc


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


NOW = datetime.datetime(2026, 11, 26, 16, 0, tzinfo=UTC)


def run(n, concl="success", mins_ago=2):
    return [{"status": "completed", "conclusion": concl,
             "createdAt": iso(NOW - datetime.timedelta(minutes=mins_ago + i * 5)),
             "databaseId": 1000 + i} for i in range(n)]


GREEN = dict(feed=run(6), liq=run(6), exe=run(6), credits_left=4_000_000)


def ev(health):
    return fw.evaluate(NOW, GREEN["feed"], GREEN["liq"], GREEN["exe"],
                       GREEN["credits_left"], fw.QUOTA, None, health)


# --- the case that started this: green runs, fresh file, dead feed ----------------------------
stale = {"last_fetch_ok_utc": iso(NOW - datetime.timedelta(hours=4, minutes=40)),
         "written_utc": iso(NOW), "state": "FAILED", "fetch_ok": False, "events_seen": 0}
bad = ev(stale)
ok("a 4h40m-old upstream fetch is caught behind GREEN runs", "FEED_STALE" in bad, sorted(bad))
ok("the warning says how stale and admits the runs look fine",
   "280 min" in bad.get("FEED_STALE", "") and "green" in bad.get("FEED_STALE", ""), bad.get("FEED_STALE"))
ok("no run-based check fires here, which is the whole point",
   not any(k in bad for k in ("FEED_FAIL", "FEED_GAP")), sorted(bad))

# --- healthy and quiet must NOT alert ----------------------------------------------------------
quiet = {"last_fetch_ok_utc": iso(NOW - datetime.timedelta(minutes=3)), "written_utc": iso(NOW),
         "state": "HEALTHY", "fetch_ok": True, "events_seen": 112, "alerts_sent": 0}
bad = ev(quiet)
ok("a healthy feed with ZERO alerts raises nothing", bad == {}, sorted(bad))

# --- fetched fine but nothing came back: its own state, not silence ----------------------------
empty = dict(quiet, state="NO_EVENTS", events_seen=0)
bad = ev(empty)
ok("an empty successful fetch is reported", "FEED_EMPTY" in bad, sorted(bad))
ok("and is NOT confused with a quiet board", "not the same as a quiet board" in bad["FEED_EMPTY"])
ok("an empty fetch is not reported as stale", "FEED_STALE" not in bad, sorted(bad))

# --- quota exhaustion is stated, with the balance when we have it -------------------------------
out = dict(quiet, quota_exhausted=True, credits_remaining=0)
bad = ev(out)
ok("quota exhaustion is its own alert", "QUOTA_OUT" in bad, sorted(bad))
ok("it carries the remaining balance", "0 left" in bad["QUOTA_OUT"], bad["QUOTA_OUT"])
nob = dict(quiet, quota_exhausted=True, credits_remaining=None)
ok("and says so plainly when the balance is unavailable",
   "balance unavailable" in ev(nob)["QUOTA_OUT"])
ok("exhaustion outranks the NO_EVENTS note", "FEED_EMPTY" not in ev(dict(out, state="NO_EVENTS")))

# --- PARTIAL: some sports fetched, the rest never attempted (Peter, Nov 26) ---------------------
# The credit-reserve break stops the poll mid-loop with fetch_ok already True. Before this was
# fixed, one sport of four published HEALTHY and pinged Healthchecks.
part = dict(quiet, state="PARTIAL", sports_due=4, sports_polled=1,
            reason="only 1 of 4 due sports were fetched this run")
bad = ev(part)
ok("a partial poll is reported", "FEED_PARTIAL" in bad, sorted(bad))
ok("it says how short it fell", "1 of 4" in bad["FEED_PARTIAL"], bad["FEED_PARTIAL"])
ok("a partial poll is NOT reported as healthy-and-quiet", "FEED_EMPTY" not in bad)

# and the state itself must never compute as HEALTHY when the poll stopped short
import importlib
import sharp_monitor as _sm
src_sm = open("sharp_monitor.py", encoding="utf-8").read()
ok("PARTIAL outranks HEALTHY in the state ladder",
   src_sm.index('"PARTIAL" if (_short or FEED["quota_exhausted"])') < src_sm.index('else "HEALTHY")'))
ok("quota exhaustion forces a non-HEALTHY state", 'FEED["quota_exhausted"])' in src_sm)
ok("the feed counts sports DUE as well as polled", '"sports_due"' in src_sm)
ok("a sport skipped on its own interval is not counted as due",
   src_sm.index("if time.time() - last < interval * 60:") < src_sm.index('FEED["sports_due"] += 1'))

# the ping gates on HEALTHY only, so PARTIAL cannot conceal a short poll
wf_src = open(os.path.join(".github", "workflows", "sharp-monitor.yml"), encoding="utf-8").read()
ok("PARTIAL cannot ping Healthchecks", '"$STATE" != "HEALTHY"' in wf_src)

# --- never fetched at all ----------------------------------------------------------------------
ok("a feed that never fetched is caught", "FEED_STALE" in ev({"last_fetch_ok_utc": None, "state": "FAILED"}))

# --- recovery clears it -------------------------------------------------------------------------
started, cleared = fw.transitions({"FEED_STALE": "...", "QUOTA_OUT": "..."}, ev(quiet))
ok("recovery clears FEED_STALE", "FEED_STALE" in cleared, cleared)
ok("recovery clears QUOTA_OUT", "QUOTA_OUT" in cleared, cleared)
ok("and raises nothing new", started == {}, started)

# --- missing health block must not crash the monitor --------------------------------------------
try:
    ok("a missing feed_health block is survivable", ev(None) == {} or True)
except Exception as e:
    ok("a missing feed_health block is survivable", False, repr(e))

# --- the feed actually writes the block, and only advances it on a real fetch --------------------
import sharp_monitor as sm
ok("sharp_monitor carries a FEED health record", isinstance(sm.FEED, dict))
ok("fetch_ok starts False, so silence is never mistaken for success", sm.FEED["fetch_ok"] is False)
for k in ("sports_polled", "events_seen", "alerts_sent", "credits_remaining", "quota_exhausted"):
    ok(f"FEED tracks {k}", k in sm.FEED)
src = open("sharp_monitor.py", encoding="utf-8").read()
ok("fetch_ok is set only after the odds call returns",
   src.index('FEED["fetch_ok"] = True') > src.index('events, rem = http_get(f"/sports/{key}/odds"'))
ok("the health block is published inside alerts.json", '"feed_health": health' in src)
ok("last_fetch_ok_utc carries forward when the fetch failed",
   'prev.get("last_fetch_ok_utc")' in src)
ok("quota exhaustion is recorded where the reserve stops the poll",
   'FEED["quota_exhausted"] = True' in src)

# --- the Healthchecks ping is gated on the fetch, not on the job exiting 0 ------------------------
wf = open(os.path.join(".github", "workflows", "sharp-monitor.yml"), encoding="utf-8").read()
ok("the ping reads feed_health.state", "feed_health" in wf and "STATE" in wf)
ok("the ping goes only on HEALTHY", '"$STATE" != "HEALTHY"' in wf)
ok("FAILED and NO_EVENTS are left to time the check out", "no ping: upstream fetch not healthy" in wf)

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)
