#!/usr/bin/env python3
"""ODDSPAPI CREDIT METER - STAGE 1: measurement and reconciliation ONLY (Peter, Nov 5 2026).

Peter approved Stage 1 and held the spending gate pending a concurrency-safe design. So this module
DOES NOT GATE ANYTHING. It cannot refuse a call, cannot change a cooldown, and is not imported by any
script that places bets or sends alerts. Running it changes no betting signal, threshold or alert.

WHY IT EXISTS
Twenty-five scripts can spend an OddsPapi credit. Six keep their own monthly counter in their own
state file and the other nineteen keep none, yet all six counters are compared against the same
CLV_MONTH_CAP - so the cap bounds no total and no local figure is the real usage. Peter's dashboard
on Nov 5 read 449 of 5,000 used while the CLV ledger's own counter read 32.

WHAT IT REPORTS
  * the provider's own usage, which is the only authoritative number. /account is a FREE call
    (OddsPapi bills everything except /account and /historical-odds), so this costs no credits.
  * the position against our INTERNAL safety cap, which Peter is deliberately keeping at 1,000 and
    NOT raising to the plan's 5,000.
  * the sum of every local counter it can read, and the DRIFT between that sum and the provider's
    figure. Drift is the measurement this stage exists to produce: it is the credits being spent by
    scripts that count nothing.

PERIOD BOUNDARY - the thing the local counters get wrong
Every local counter keys on the calendar month ("%Y-%m"). Peter's account period runs Nov 3 to
Dec 3, so the provider's usage resets on the 3rd while every local counter resets on the 1st. Two
days of spend therefore land in the wrong bucket every month, in both directions. This module keys
on the provider's period when /account reports one and says so plainly when it has to fall back.

READ-ONLY
Nothing here writes to any state file, any cache or the repo. It reads the local counters and never
modifies them, so a failure in this module cannot corrupt accounting state belonging to anything else.
"""
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import tracker_build as tb

# Internal safety cap. Deliberately NOT the plan's 5,000 (Peter, Nov 5: "Keep our existing
# 1,000-credit internal safety cap for now. Do not automatically increase it to 5,000.")
INTERNAL_CAP = int(os.environ.get("ODDSPAPI_MONTH_CAP", "") or os.environ.get("CLV_MONTH_CAP", "") or "1000")

# Every state file that holds a st["billable"] counter, and the script that owns it. Read-only.
# A path that does not exist, or will not decrypt, is reported as unreadable rather than as zero -
# the difference matters, because zero would understate usage and hide the drift this exists to find.
COUNTERS = [
    ("clv_ledger.py", "clv/state.enc", "enc"),
    ("plimit_logger.py", "plimit/state.enc", "enc"),
    ("slow_hr.py", "slowhr/state.enc", "enc"),
    ("exchange_lag.py", "exlag/state.enc", "enc"),
    ("x2_tag.py", "x2/limits.json", "json"),
    ("ncaab_grade.py", "ncaab/openers.enc", "enc"),
]

# Scripts that can reach a billable call but keep NO persistent counter, so their spend appears in no
# local total. Fourteen pass a throwaway {"billable": {}} to the biller; five have no counter at all.
# Listed so the report names what the drift is made of instead of leaving it anonymous.
UNCOUNTED = [
    "executor.py", "close_vs_close_test.py", "fill_audit.py", "hcache_fill.py", "lane2.py",
    "liq_history_test.py", "model_lab.py", "nba_backtest.py", "nba_backtest2.py", "p1_backtest.py",
    "plimit_level.py", "plimit_probe.py", "sent_export.py", "slowhr_backtest.py",
    "small_book_surge_test.py", "x2_backtest.py", "hist_probe.py",
    "kalshi_demo_order_test.py", "kalshi_live_order_test.py", "kalshi_no_order_test.py",
]


def account():
    """The provider's own usage. /account is free, so this spends nothing. Returns {} when it cannot
    be read - never a zero, which would read as 'nothing used'."""
    try:
        d = cl.api("/account", False)
    except Exception as ex:
        return {"_error": f"call failed: {str(ex)[:80]}"}
    if not isinstance(d, dict) or d.get("_error"):
        return {"_error": str((d or {}).get("_error") or f"unexpected shape: {type(d).__name__}")[:120]}
    return d


def _shape(d):
    """Field NAMES ONLY. Never values.

    Nov 5: an earlier version printed short values with a redaction test, and /account returned
    api_key=<a UUID>. The test required a value to be almost entirely alphanumeric, so the UUID's
    hyphens defeated it and the live key was printed into Peter's private email. No value from this
    endpoint is worth printing: the field names alone are what pinning the usage field needs, so
    values are now never emitted and no redaction rule has to be trusted.
    """
    out = []
    for k, v in sorted((d or {}).items()):
        if isinstance(v, dict):
            out.append(f"{k}{{{','.join(sorted(v))}}}")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(f"{k}[0]{{{','.join(sorted(v[0]))}}}")
        elif isinstance(v, list):
            out.append(f"{k}[{len(v)}]")
        else:
            out.append(f"{k}:{type(v).__name__}")
    return out


def _pick(d, *names):
    """Look for a field at the top level AND inside subscriptions[0].

    The first run showed /account carries no usage field at the top level - the plan and its counters
    sit under subscriptions[0] - so a top-level-only search reported '? of ?' and the whole point of
    the reconciliation was lost. Names are matched case-insensitively and ignoring underscores, since
    the provider uses snake_case inside subscriptions where the docs use camelCase.
    """
    def norm(x):
        return str(x).replace("_", "").lower()
    wanted = {norm(n) for n in names}
    subs = (d or {}).get("subscriptions")
    for scope in ((d or {}), (subs[0] if isinstance(subs, list) and subs and isinstance(subs[0], dict) else {})):
        for k, v in scope.items():
            if norm(k) in wanted and v is not None:
                return v
    return None


def period_key(acct, now):
    """(key, label, authoritative). The provider's billing period when it reports one, else the
    calendar month with authoritative=False so the report can say the boundary is a guess."""
    start = _pick(acct, "valid_from", "periodStart", "currentPeriodStart")
    end = _pick(acct, "valid_until", "periodEnd", "currentPeriodEnd")
    if start:
        s = tb.tparse(start)
        e = tb.tparse(end) if end else None
        if s is not None:
            return (s.strftime("%Y-%m-%d"),
                    f"{s:%Y-%m-%d} to {e:%Y-%m-%d}" if e else f"from {s:%Y-%m-%d}", True)
    return now.strftime("%Y-%m"), f"calendar month {now:%Y-%m}", False


def local_counters(now):
    """[(script, path, month_to_date, note)] read from each owner's own state. Never writes."""
    out = []
    mk = now.strftime("%Y-%m")
    for script, path, kind in COUNTERS:
        if not os.path.exists(path):
            out.append((script, path, None, "no state file yet"))
            continue
        try:
            raw = json.load(open(path))
            st = tb.dec(raw) if kind == "enc" else raw
            b = (st or {}).get("billable") or {}
            out.append((script, path, b.get(mk, 0), f"keys {sorted(b)[-3:]}" if b else "counter empty"))
        except Exception as ex:
            out.append((script, path, None, f"unreadable ({str(ex)[:50]})"))
    return out


def report(now=None):
    """The reconciliation, as text lines. Counts only - no dollars, no stakes, no account ids."""
    now = now or datetime.now(timezone.utc)
    acct = account()
    key, plabel, auth = period_key(acct, now)
    # Field names confirmed from the live response on 2026-11-05: the counters live under
    # subscriptions[0] as request_count / request_limit, with the billing window as
    # valid_from / valid_until. Earlier guesses ("requestsUsed", "requestsLimit") missed on the
    # singular/plural of "request", which is why two runs reported "? of ?".
    used = _pick(acct, "request_count", "requestsUsed", "used")
    limit = _pick(acct, "request_limit", "requestsLimit", "limit")
    plan = _pick(acct, "plan", "planName", "tier")

    L = [f"ODDSPAPI CREDIT RECONCILIATION | {now:%Y-%m-%d %H:%M} UTC",
         "",
         "Stage 1: measurement only. This report gates nothing and changed no betting signal,",
         "threshold, alert or execution path. /account is a free call, so this costs no credits.",
         "",
         "=" * 70, "PROVIDER (authoritative)", "=" * 70]
    if acct.get("_error"):
        L += [f"  /account unreadable: {acct['_error']}",
              "  No authoritative figure this run. The local sums below are a FLOOR, not the total."]
    elif used is None:
        L += ["  /account answered but reported no usage field under any name this code knows.",
              "  Field NAMES and types only - no value from this endpoint is ever printed:",
              "    " + ", ".join(_shape(acct) or ["(empty response)"]),
              "  Until a usage field is identified the reconciliation below has no authoritative",
              "  total, and the local sums are a FLOOR. Peter's dashboard is the figure to use."]
    else:
        L += [f"  plan: {plan if plan is not None else '?'}",
              f"  period: {plabel}" + ("" if auth else "   <-- GUESSED: the provider did not report a"
                                       " period, so this falls back to the calendar month"),
              f"  used: {used if used is not None else '?'} of {limit if limit is not None else '?'}"]
        if isinstance(used, (int, float)) and isinstance(limit, (int, float)) and limit:
            L.append(f"  remaining on the plan: {limit - used:,.0f} ({100.0 * used / limit:.1f}% used)")
        if isinstance(used, (int, float)):
            L += [f"  against our INTERNAL safety cap of {INTERNAL_CAP}: {used:,.0f} used, "
                  f"{INTERNAL_CAP - used:,.0f} left" if used <= INTERNAL_CAP else
                  f"  *** INTERNAL CAP EXCEEDED: {used:,.0f} used against a cap of {INTERNAL_CAP} ***"]

    L += ["", "=" * 70, "LOCAL COUNTERS (each script's own, calendar-month keyed)", "=" * 70]
    rows = local_counters(now)
    s = 0
    unread = []
    for script, path, v, note in rows:
        if v is None:
            unread.append(script)
            L.append(f"  {script:<20} {'-':>6}  {path}  ({note})")
        else:
            s += v
            L.append(f"  {script:<20} {v:>6}  {path}  ({note})")
    L.append(f"  {'SUM':<20} {s:>6}" + (f"   ({len(unread)} unreadable: {', '.join(unread)})" if unread else ""))

    L += ["", "=" * 70, "DRIFT - what the local counters cannot see", "=" * 70]
    if isinstance(used, (int, float)):
        L += [f"  provider {used:,.0f} - local sum {s} = {used - s:+,.0f}",
              "  That gap is spend by scripts that keep no counter, plus the period-boundary",
              "  mismatch (local counters reset on the 1st; the plan period does not)."]
    else:
        L.append("  not computable without the provider figure")
    L += ["",
          f"  {len(UNCOUNTED)} scripts can spend and keep NO persistent counter:",
          "    " + ", ".join(UNCOUNTED[:9]),
          "    " + ", ".join(UNCOUNTED[9:]),
          "",
          "  Six independent counters are each compared against the same cap, so the cap bounds no",
          "  total. Closing that needs the shared meter, which is Stage 2 and awaits Peter's",
          "  approval of a concurrency-safe design.",
          "",
          "Nothing was written. No counter, cache, cooldown or betting rule was modified."]
    return L


def main():
    lines = report()
    body = "\n".join(lines)
    try:
        import executor as ex
        ex.send("Bets ODDSPAPI CREDITS (reconciliation)", body)
    except Exception as e:
        print(f"email skipped: {str(e)[:80]}", file=sys.stderr)
    # the public Actions log gets counts only, never the body
    acct = account()
    u = _pick(acct, "requestsUsed", "used")
    print(f"credits: provider used {u if u is not None else '?'}, internal cap {INTERNAL_CAP}, "
          f"local counters read {sum(1 for _, _, v, _ in local_counters(datetime.now(timezone.utc)) if v is not None)}"
          f"/{len(COUNTERS)}")


if __name__ == "__main__":
    main()
