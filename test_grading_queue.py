#!/usr/bin/env python3
"""Grading queue order (Peter, Nov 19): "Process new fills first... Move historical recovery into
small, bounded batches that cannot block today's grading."

The defect: st["bets"] iterates in FIRST-SEEN order, so pend handed the OLDEST rows to the scorer
first. Each distinct (fixture, book) costs a free history call at ~8 s and the run is capped at
MAX_HIST=60 of them, so the Nov 18 recovery of 353 newly-scorable old rows could consume every call
before a fill placed tonight was reached. The run finishes on time and still does not grade today.
That is starvation, and it is a different fault from the runtime, with a different fix.

What must stay true: no row is dropped, deferral is not failure, and the backlog ROTATES so the tail
is reached rather than the same head being retried forever.
"""
from datetime import datetime, timedelta, timezone

import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


NOW = datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc)


def row(key, age_days, tries=None, last_try=None, field="game_start"):
    snap = {field: (NOW - timedelta(days=age_days)).isoformat()}
    rec = {"snap": snap}
    if tries is not None:
        rec["tries"] = tries
    if last_try is not None:
        rec["last_try"] = (NOW - timedelta(days=last_try)).isoformat()
    return (key, rec)


def keys(q):
    return [k for k, _ in q]


# ------------------------------------------------------------------ 1. new before backlog
pend = [row("old1", 30), row("old2", 20), row("new1", 0.2), row("old3", 10), row("new2", 1)]
q, line = cl.grading_queue(pend, NOW)
ok("today's fills come before every backlog row",
   keys(q)[:2] == ["new1", "new2"], keys(q))
ok("newest of the new fills is served first", keys(q)[0] == "new1", keys(q))
ok("no row is dropped when the backlog fits in the batch", len(q) == 5, len(q))
ok("the log line reports new, backlog, served and deferred",
   all(w in line for w in ("2 new", "3 backlog", "3 served", "0 deferred")), line)

# the original order is the bug: oldest first
ok("the pre-fix order would have served the oldest row first", keys(pend)[0] == "old1")

# ------------------------------------------------------------------ 2. backlog is bounded
many = [row(f"old{i}", 10 + i) for i in range(cl.BACKLOG_MAX + 25)] + [row("newA", 0.5)]
q, line = cl.grading_queue(many, NOW)
ok("the backlog is capped at BACKLOG_MAX per run", len(q) == cl.BACKLOG_MAX + 1, len(q))
ok("the new fill is still first even against a huge backlog", keys(q)[0] == "newA", keys(q)[:2])
ok("the deferred remainder is counted, not discarded", "25 deferred" in line, line)

# a big day of new fills never loses one to the cap
busy = [row(f"n{i}", 0.1 + i / 100) for i in range(80)] + [row("o1", 40)]
q, _ = cl.grading_queue(busy, NOW)
ok("the cap never truncates NEW fills - only historical recovery is bounded",
   len([k for k in keys(q) if k.startswith("n")]) == 80, len(q))

# ------------------------------------------------------------------ 3. the backlog rotates
mix = [row("tried3", 10, tries=3), row("tried0", 11, tries=0), row("tried1", 12, tries=1)]
q, _ = cl.grading_queue(mix, NOW)
ok("least-tried backlog rows are served first, not the oldest",
   keys(q) == ["tried0", "tried1", "tried3"], keys(q))

same = [row("recent", 10, tries=2, last_try=0), row("stale", 11, tries=2, last_try=9),
        row("middle", 12, tries=2, last_try=4)]
q, _ = cl.grading_queue(same, NOW)
ok("at equal tries the least-recently-tried is served first",
   keys(q) == ["stale", "middle", "recent"], keys(q))

ok("a backlog row never tried outranks one tried today",
   keys(cl.grading_queue([row("done_today", 10, tries=0, last_try=0), row("never", 11)], NOW)[0])
   == ["never", "done_today"])

# rotation actually drains: simulate runs, stamping last_try/tries on whatever is served
pool = [row(f"b{i}", 10 + i) for i in range(cl.BACKLOG_MAX * 3)]
seen, clock = set(), NOW
for _ in range(3):
    served, _ = cl.grading_queue(pool, clock)
    for k, rec in served:
        seen.add(k)
        rec["tries"] = rec.get("tries", 0) + 1
        rec["last_try"] = clock.isoformat()
    clock += timedelta(hours=2)
ok("three runs reach the whole backlog - the tail is not stranded",
   len(seen) == len(pool), f"{len(seen)} of {len(pool)}")

# ------------------------------------------------------------------ 4. fallbacks and edges
ok("a row with no game_start falls back to placed",
   keys(cl.grading_queue([row("old", 30), row("byplaced", 0.3, field="placed")], NOW)[0])[0] == "byplaced")
ok("a row with no usable date is treated as backlog, never as today's fill",
   keys(cl.grading_queue([({}, {"snap": {}}) and ("nodate", {"snap": {}}), row("newz", 0.1)], NOW)[0])[0] == "newz")
ok("an empty queue is handled", cl.grading_queue([], NOW)[0] == [])
ok("the boundary is BACKLOG_AFTER_DAYS, exclusive on the old side",
   keys(cl.grading_queue([row("justold", cl.BACKLOG_AFTER_DAYS + 0.1),
                          row("justnew", cl.BACKLOG_AFTER_DAYS - 0.1)], NOW)[0])[0] == "justnew")

# ------------------------------------------------------------------ 5. what it must NOT do
src = open("clv_ledger.py").read()
fn = src[src.index("def grading_queue("):src.index("# ---", src.index("def grading_queue("))]
ok("the queue never marks a row done", '"done"' not in fn and "'done'" not in fn)
ok("the queue never writes a clv value", '"clv"' not in fn)
ok("the queue never estimates or substitutes a close", "close" not in fn.split('"""')[2])
ok("deferral is reversible - the function only returns, it does not mutate the store",
   ".pop(" not in fn and "del " not in fn)

ok("CLV is still written at exactly one place in the ledger",
   src.count('rec["clv"] = ') == 1, src.count('rec["clv"] = '))
ok("that one place requires a real close and a real price",
   "if c and d:" in src)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
