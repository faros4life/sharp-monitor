#!/usr/bin/env python3
"""LIVE HEALTH PAGE (Peter, Nov 12: "i want to see it at alltimes is everything running").

Writes site/health/index.html, published by board-page.yml alongside the board. Reads only the
repo's OWN Actions history through GITHUB_TOKEN (actions: read). No venue calls, no Gmail, no
registry, no orders - so it can never be the thing that breaks a betting run.

WHAT IT DECIDES, and why that is not obvious. "Is it running" cannot be read off the newest run:
this repo cancels queued runs by design (concurrency with cancel-in-progress: false), so a wall of
"cancelled" is normal and tells you nothing. What matters is whether each workflow has SUCCEEDED
recently relative to its own cadence. So for every workflow it measures the median gap between
recent runs, and flags one whose last SUCCESS is older than three of its own gaps. That is what
caught bets-board sitting 20 hours stale while its runs looked busy.

PUBLIC PAGE DISCIPLINE. This repo is public and this page is published, so it carries workflow
names, statuses and timestamps only. No stakes, balances, prices, bets, lane switch states or
venue credentials - nothing that is either financial or strategy-revealing. Counts and clock
readings, nothing else.
"""
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("GITHUB_REPOSITORY") or "faros4life/sharp-monitor"
TOK = (os.environ.get("GITHUB_TOKEN") or "").strip()
API = "https://api.github.com"
OUT = os.environ.get("HEALTH_OUT") or "site/health"
STALE_FACTOR = 3        # a workflow is stale when its last success is older than 3 of its own gaps
FLOOR_MIN = 25          # ...but never flag a workflow whose own cadence is slower than this
LOOKBACK = 30           # runs per workflow to measure cadence from
STALE_PAGE_MIN = 25     # the page calls ITSELF stale past this, in the browser


def gh(path):
    req = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "health-build"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode() or "{}"), None
    except urllib.error.HTTPError as ex:
        return None, f"HTTP {ex.code}"
    except Exception as ex:
        return None, type(ex).__name__


def _novig_switch():
    """(submit_state, dispatch_present). Env first; otherwise read it off the executor's own log.

    board-page passes vars.EXEC_NOVIG_SUBMIT in, so the published page always has it. The PINNED
    PANEL does not: it is built by a session that cannot read the variables API (blocked through
    the proxy), which would leave the most important row on the board saying UNKNOWN exactly when
    Peter wants to know whether Novig is live.

    The executor echoes both values at the top of every run as '***' or blank - presence, never
    the value - so the newest completed run is an authoritative, already-public source.

    Returns sub=None when it could not be read, which the caller renders as UNKNOWN. That
    distinction is the whole point: an empty string would fall into the "off" branch and print
    PAUSED, asserting the switch is off on no evidence. That is the same failure this row already
    had once as a hardcoded PAUSED, and it is the direction that loses money quietly.
    """
    sub = (os.environ.get("EXEC_NOVIG_SUBMIT") or "").strip()
    disp = bool((os.environ.get("NOVIG_DISPATCH_TOKEN") or "").strip())
    if sub:
        return sub, disp
    # gh() takes a FULL api path - callers supply /repos/{REPO} themselves (API is the bare host).
    runs, err = gh(f"/repos/{REPO}/actions/workflows/executor-dry-run.yml/runs"
                   "?per_page=10&status=success")
    if err or not runs:
        return None, False
    for run in (runs.get("workflow_runs") or [])[:3]:
        jobs, err = gh(f"/repos/{REPO}/actions/runs/{run.get('id')}/jobs")
        if err or not jobs:
            continue
        jid = ((jobs.get("jobs") or [{}])[0] or {}).get("id")
        if not jid:
            continue
        req = urllib.request.Request(f"{API}/repos/{REPO}/actions/jobs/{jid}/logs", headers={
            "Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "health-build"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
        except Exception:
            continue
        m = re.search(r"EXEC_NOVIG_SUBMIT:\s*(\S*)", text)
        d = re.search(r"NOVIG_DISPATCH_TOKEN:\s*(\S*)", text)
        if m:
            print(f"health: Novig switch read from executor run {run.get('id')}", flush=True)
            return (m.group(1) or "").strip(), bool((d.group(1) if d else "").strip())
    return None, False


def _pretty_gap(m):
    """A gap in minutes, said the way a person would."""
    if m is None:
        return "?"
    if m < 90:
        return f" {m:.0f}m"
    if m < 60 * 36:
        return f" {m / 60:.0f}h"
    return f" {m / 1440:.0f}d"


def _cron_gap_min(path):
    """Minutes between firings, from the workflow's DECLARED cron. None when it has none.

    Nov 12, third correction. Cadence was measured from observed run GAPS, which is wrong for any
    workflow that does not run often: a weekly job with a burst of hand runs shows a tiny median
    gap, so the staleness test demanded a success within minutes and reported it late. That put
    three false alarms on this page at once - novig-weekly and pmus-activity are Monday-only and
    had run on their Monday, credits-report is daily and was mid-run.

    So the cadence comes from the schedule itself. Coarsest constrained field wins, which covers
    every shape this repo uses; several crons take the shortest. Unparseable -> None, and the
    caller then falls back to observed gaps rather than guessing.
    """
    try:
        text = open(str(path or ""), encoding="utf-8").read()
    except Exception:
        return None
    best = None
    for expr in re.findall(r"cron:\s*[\"']([^\"']+)[\"']", text):
        f = expr.split()
        if len(f) != 5:
            continue
        minute, hour, dom, mon, dow = f
        if "/" in minute:                       # */5, 3-59/15 -> that many minutes
            try:
                gap = int(minute.split("/")[1])
            except ValueError:
                continue
        elif "/" in hour:                       # fixed minute, every N hours
            try:
                gap = 60 * int(hour.split("/")[1])
            except ValueError:
                continue
        elif hour in ("*",) or "-" in hour or "," in hour:
            gap = 60                            # fixed minute, several hours -> hourly
        elif dow not in ("*", "?"):
            gap = 7 * 24 * 60                   # a named weekday -> weekly
        elif dom not in ("*", "?"):
            gap = 30 * 24 * 60                  # a named day of the month -> monthly
        else:
            gap = 24 * 60                       # fixed minute and hour -> daily
        best = gap if best is None else min(best, gap)
    return best


def _declares_auto(path):
    """True when the workflow's own `on:` block declares schedule or workflow_run.

    Read from the checkout, text-only: a real YAML parse is not worth a dependency here, and the
    question is only whether either key appears inside `on:` before the next top-level key.
    Unreadable file -> False, so an unknown workflow is reported ON DEMAND rather than judged on a
    guess.
    """
    try:
        lines = open(str(path or ""), encoding="utf-8").read().splitlines()
    except Exception:
        return False
    inside = False
    for ln in lines:
        if re.match(r"^on\s*:", ln):
            inside = True
            if re.search(r"\bschedule\b|\bworkflow_run\b", ln):
                return True
            continue
        if inside:
            if ln.strip() and not ln.startswith((" ", "\t", "#")):
                break            # next top-level key: the on: block has ended
            if re.match(r"^\s+(schedule|workflow_run)\s*:", ln):
                return True
    return False


def ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def ago(dt, now):
    if not dt:
        return "never", 10 ** 9
    m = (now - dt).total_seconds() / 60
    if m < 1:
        return "just now", m
    if m < 60:
        return f"{int(m)}m ago", m
    if m < 1440:
        return f"{m / 60:.1f}h ago", m
    return f"{m / 1440:.1f}d ago", m


def main():
    now = datetime.now(timezone.utc)
    if not TOK:
        print("health: no GITHUB_TOKEN - cannot read Actions history, page not written")
        return 1
    # Nov 12: the list is PAGINATED and this repo has 115 workflows. Reading one page of
    # 100 silently dropped the last 15 - signal-alerts among them - so the page reported
    # "Against Your Bet: no workflow of this name is active" when the workflow was simply
    # on page 2. A truncated list is the worst kind of wrong here: it reads as a finding.
    wf_all, page = [], 1
    while page <= 10:
        wfs, err = gh(f"/repos/{REPO}/actions/workflows?per_page=100&page={page}")
        if err:
            if page == 1:
                print(f"health: workflow list unreadable ({err}) - page not written")
                return 1
            print(f"health: workflow list truncated at page {page} ({err}) - FLAGGED")
            break
        got = (wfs or {}).get("workflows") or []
        wf_all += got
        total = int((wfs or {}).get("total_count") or 0)
        if len(got) < 100 or (total and len(wf_all) >= total):
            break
        page += 1
    print(f"health: {len(wf_all)} workflow(s) listed"
          f"{' of ' + str(total) if total else ''}")

    rows = []
    for w in wf_all:
        if str(w.get("state")) != "active":
            continue
        name = str(w.get("name") or "")
        runs, e2 = gh(f"/repos/{REPO}/actions/workflows/{w['id']}/runs?per_page={LOOKBACK}")
        rl = (runs or {}).get("workflow_runs") or [] if not e2 else []
        if not rl:
            continue
        # Nov 12 (first live run): the page reported "56 not running" out of 100 workflows, naming
        # px-sandbox-order-test, nba-backtest2, clv-reset, pmus-slugs and dozens of other
        # MANUAL-ONLY probes. They have no schedule, so "late" is meaningless for them, and a
        # headline of 56 NOT RUNNING is worse than no page - it buries the one workflow that
        # really is stale. Only a workflow that fires ON ITS OWN gets a cadence verdict; the rest
        # are reported as ON DEMAND and kept out of the headline entirely. Read off the runs'
        # own event field rather than parsing workflow files, so it stays true if a trigger
        # changes.
        # Nov 12, final: classify by what the workflow DECLARES, not by its run history.
        #
        # Two heuristics failed first. Testing the event alone labelled the executor and nearly
        # every live job ON DEMAND, because cron-job.org fires them and an external caller arrives
        # as workflow_dispatch. Adding "many runs, closely spaced" then swept in one-off probes -
        # nba-backtest2, hist-probe, pnl-pull - because a debugging burst also looks regular.
        # Run history simply cannot tell "automated but broken" from "manual and idle".
        #
        # The workflow file can. A `schedule:` or `workflow_run:` trigger in its own `on:` block
        # says it is meant to fire by itself, whether or not GitHub's timer is the thing firing it,
        # and that stays true while it is broken - which is exactly when the answer matters. The
        # repo is checked out in this job, so this is a free local read, not an API call.
        auto = _declares_auto(w.get("path"))
        starts = sorted([t for t in (ts(r.get("created_at")) for r in rl) if t], reverse=True)
        gaps = [(starts[i] - starts[i + 1]).total_seconds() / 60 for i in range(len(starts) - 1)]
        # Declared schedule first; observed gaps only when there is no cron to read.
        declared = _cron_gap_min(w.get("path"))
        observed = statistics.median(gaps) if gaps else None
        cadence = declared if declared is not None else observed
        succ = [ts(r.get("created_at")) for r in rl
                if r.get("status") == "completed" and r.get("conclusion") == "success"]
        succ = sorted([t for t in succ if t], reverse=True)
        last_ok = succ[0] if succ else None
        ok_txt, ok_min = ago(last_ok, now)
        newest = rl[0]
        running = any(r.get("status") in ("in_progress", "queued", "pending") for r in rl[:3])

        # The verdict. Deliberately NOT "is the newest run green": this repo drops queued runs on
        # purpose, so cancellations are routine and say nothing about health.
        limit = max(FLOOR_MIN, STALE_FACTOR * cadence) if cadence else None
        if not auto:
            state, why = "ON DEMAND", ("manual only" + (f", last success {ok_txt}" if last_ok else ", never succeeded"))
        elif last_ok is None:
            state, why = "FAIL", "no successful run in the last %d runs" % len(rl)
        elif limit and ok_min > limit:
            _src = "its schedule is every" if declared is not None else "its own cadence is ~"
            state, why = "STALE", f"last success {ok_txt}, {_src}{_pretty_gap(cadence)}"
        elif str(newest.get("conclusion")) == "failure":
            state, why = "WARN", "succeeding, but the most recent run FAILED"
        else:
            state, why = "OK", ""
        cancels = sum(1 for r in rl if r.get("conclusion") == "cancelled")
        rows.append({"name": name, "state": state, "why": why, "last_ok": ok_txt,
                     "ok_min": ok_min, "cadence": cadence, "running": running,
                     "cancel_pct": round(100 * cancels / len(rl)), "n": len(rl)})

    # Nov 12 (Muse's review, via Peter): "I want to be able to open Bets Board and see whether my
    # entire trading operation is healthy - not merely whether GitHub Actions is green." So the
    # workflows are rolled up into the systems Peter actually names. The worst member decides the
    # system's state; a system with no matching workflow says so rather than showing green.
    SYSTEMS = (
        ("Live executor",        ("executor",)),
        ("Against Your Bet",     ("signal-alerts",)),
        ("Fill reports",         ("fill-reports",)),
        # Nov 12: these two were both called "Bets Board", which read as though the board Peter
        # opens were stale whenever the tracker build was. They are different jobs: board-page
        # runs board_build.py and publishes the live board (every ~10m on workflow_run), while
        # bets-board builds the encrypted private tracker page that board-page then copies in.
        # A stale tracker build leaves the board itself current, so it is named for what it is.
        ("Bets Board (live)",    ("board-page",)),
        ("Private tracker build", ("bets-board",)),
        ("CLV ledger",           ("clv-ledger",)),
        ("Novig snapshot",       ("novig-snapshot-check", "novig-positions", "novig-heartbeat")),
        ("Liquidity feeds",      ("liquidity-monitor", "liquidity-extra")),
    )
    # ON DEMAND must be here too, or the systems rollup raises KeyError the moment a system's
    # members include a manual-only workflow. Ranked last: a manual probe never decides a system's
    # health, but it must not crash the page either.
    worst = {"FAIL": 0, "STALE": 1, "WARN": 2, "OK": 3, "ON DEMAND": 4}
    sysrows = []
    for label, pats in SYSTEMS:
        members = [r for r in rows if any(pt in r["name"].lower().replace(" ", "-") for pt in pats)]
        if not members:
            sysrows.append((label, "UNKNOWN", "no workflow of this name is active"))
            continue
        m = min(members, key=lambda r: worst[r["state"]])
        detail = m["why"] or f"last success {m['last_ok']}"
        if len(members) > 1:
            detail += f" ({m['name']})"
        sysrows.append((label, m["state"], detail))
    # Two things this page cannot establish, stated rather than coloured green.
    # Nov 12, 22:00Z: this row was HARDCODED to PAUSED, written when both holds were on. Peter
    # then turned EXEC_NOVIG_SUBMIT on, and a board reporting PAUSED while orders can actually
    # go out is a worse lie than the stale-board one - it is the direction that loses money
    # quietly. So it reads the switch, and says UNKNOWN rather than guessing when it is not
    # passed in. Switch state only: no stake, no limit, no dollars.
    _sub, _disp = _novig_switch()
    _unreadable = _sub is None          # None means COULD NOT READ, never "it is off"
    _sub = (_sub or "").strip().lower()
    if _sub in ("on", "1", "true", "yes"):
        sysrows.append(("Novig submissions", "OK" if _disp else "WARN",
                        "LIVE - EXEC_NOVIG_SUBMIT is on" + ("" if _disp
                         else "; but NO dispatch credential, so every order would refuse")))
    elif not _unreadable and _sub in ("off", "0", "false", "no", ""):
        sysrows.append(("Novig submissions", "PAUSED",
                        "held by EXEC_NOVIG_SUBMIT" + ("" if _disp
                         else "; no dispatch credential configured either")))
    elif _unreadable:
        sysrows.append(("Novig submissions", "UNKNOWN",
                        "could not read EXEC_NOVIG_SUBMIT - this is NOT a claim that it is off"))
    else:
        sysrows.append(("Novig submissions", "UNKNOWN",
                        f"EXEC_NOVIG_SUBMIT not readable from this job (saw {_sub!r})"))
    sysrows.append(("Phone alert delivery", "NOT CHECKED",
                    "this page cannot confirm your phone received anything"))

    # The side panel reads the same rows this page renders, so the two can never disagree.
    # Written as a sidecar of this build rather than rebuilt by a separate script: one source.
    try:
        os.makedirs("site/health", exist_ok=True)
        with open("site/health/rows.json", "w") as _f:
            json.dump({"at": int(datetime.now(timezone.utc).timestamp() * 1000),
                       "rows": [{"name": a, "state": b, "detail": c} for a, b, c in sysrows]},
                      _f, indent=1)
        print(f"health rows.json: {len(sysrows)} system row(s)", flush=True)
    except Exception as _ex:
        print(f"health rows.json: not written ({str(_ex)[:80]})", flush=True)

    order = {"FAIL": 0, "STALE": 1, "WARN": 2, "OK": 3, "ON DEMAND": 4}
    rows.sort(key=lambda r: (order[r["state"]], -r["ok_min"]))
    sched = [r for r in rows if r["state"] != "ON DEMAND"]
    bad = [r for r in sched if r["state"] in ("FAIL", "STALE")]
    headline = ("ALL RUNNING" if not bad and not [r for r in sched if r["state"] == "WARN"]
                else f"{len(bad)} NOT RUNNING" if bad else "RUNNING, WITH WARNINGS")
    hcls = "ok" if headline == "ALL RUNNING" else ("warn" if not bad else "bad")

    SDOT = {"OK": "ok", "WARN": "warn", "STALE": "bad", "FAIL": "bad",
            "UNKNOWN": "warn", "PAUSED": "warn", "NOT CHECKED": "warn", "ON DEMAND": "idle"}
    # Nov 12 (Peter): a mark per state rather than a coloured dot, so a row reads without
    # relying on colour - a tick is running, a cross is not - and the states that are
    # NEITHER get their own mark instead of being dressed up as one or the other.
    MARK = {"OK": "\u2713", "WARN": "!", "STALE": "\u2717", "FAIL": "\u2717",
            "UNKNOWN": "?", "PAUSED": "\u2016", "NOT CHECKED": "\u2013", "ON DEMAND": "\u2013"}

    def tr(r):
        dot = {"OK": "ok", "WARN": "warn", "STALE": "bad", "FAIL": "bad",
               "ON DEMAND": "idle"}[r["state"]]
        run = '<span class=run>running</span>' if r["running"] else ""
        cad = _pretty_gap(r["cadence"]).strip() if r["cadence"] else "-"
        return (f"<tr><td><span class='dot {dot}'>{MARK.get(r['state'], '?')}</span>{r['state']}</td>"
                f"<td>{r['name']}{run}</td><td class=r>{r['last_ok']}</td>"
                f"<td class='r muted'>{cad}</td><td class='r muted'>{r['cancel_pct']}%</td>"
                f"<td class=muted>{r['why']}</td></tr>")

    html = f"""<!doctype html>
<html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv=refresh content=120>
<title>Live Health</title>
<style>
:root{{--bg:#f7f7f8;--fg:#17181c;--mut:#6b6f76;--line:#e3e4e8;--card:#fff;
--ok:#1a7f45;--warn:#9a6b00;--bad:#b3261e;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#111215;--fg:#e8e9ec;
--mut:#9aa0a8;--line:#2a2c31;--card:#1a1b1f;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;
color-scheme:dark}}}}
:root[data-theme=dark]{{--bg:#111215;--fg:#e8e9ec;--mut:#9aa0a8;--line:#2a2c31;--card:#1a1b1f;
--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:900px;margin:0 auto;
padding-left:max(16px,env(safe-area-inset-left,0px));
padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px}}
h1{{font-size:15px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);
margin:0 0 4px;font-weight:600}}
.big{{font-size:26px;font-weight:650;margin:0 0 2px}}
.big.ok{{color:var(--ok)}}.big.warn{{color:var(--warn)}}.big.bad{{color:var(--bad)}}
.sub{{color:var(--mut);font-size:12px;margin-bottom:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th{{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
color:var(--mut);font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line);
white-space:nowrap}}
td{{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
.r{{text-align:right;white-space:nowrap}}.muted{{color:var(--mut)}}
.dot{{display:inline-block;width:1.1em;margin-right:6px;text-align:center;
font-weight:700;font-variant-numeric:normal}}
.dot.ok{{color:var(--ok)}}.dot.warn{{color:var(--warn)}}.dot.bad{{color:var(--bad)}}
.dot.idle{{color:var(--mut);opacity:.6}}
.run{{margin-left:8px;font-size:10px;color:var(--mut);border:1px solid var(--line);
border-radius:4px;padding:1px 5px}}
.note{{color:var(--mut);font-size:12px;margin-top:14px}}
</style></head><body data-generated="{now:%Y-%m-%dT%H:%M:%SZ}"><div class=wrap>
<h1>Live health</h1>
<p class="big {hcls}">{headline}</p>
<p class=sub>{len(sched)} scheduled &middot; {len(rows) - len(sched)} on demand &middot; generated {now:%Y-%m-%d %H:%M}Z &middot;
<span id=age>checking snapshot age</span></p>
<div class=card style="margin-bottom:16px"><table>
<tr><th>System</th><th>State</th><th>Detail</th></tr>
{''.join(f"<tr><td>{n}</td><td><span class='dot {SDOT.get(st,'warn')}'>{MARK.get(st,'?')}</span>{st}</td>"
         f"<td class=muted>{d}</td></tr>" for n, st, d in sysrows)}
</table></div>
<div class=card><table>
<tr><th>State</th><th>Workflow</th><th class=r>Last success</th><th class=r>Cadence</th>
<th class=r>Cancelled</th><th>Note</th></tr>
{''.join(tr(r) for r in rows) or '<tr><td colspan=6 class=muted>no workflow history readable</td></tr>'}
</table></div>
<p class=note id=stalebox hidden></p>
<p class=note>STALE means the last SUCCESS is older than {STALE_FACTOR}x that workflow's own
median run gap. Cancelled runs are normal here - queued runs are dropped on purpose - so a high
cancelled share is not itself a fault. Workflow status only: no stakes, balances, prices or
switch states appear on this page.</p>
</div>
<script>
// Nov 12 (Muse's review, via Peter): "a frozen health page could misleadingly keep displaying ALL
// RUNNING." A page that cannot report its OWN staleness is worse than no page, because it fails
// silently in exactly the situation it exists to detect - the publisher stopping. The generation
// time is baked in at build time and the age is computed HERE, in the viewer's browser, so a page
// served from cache or from a dead publisher still tells the truth. If the stamp will not parse,
// it says UNKNOWN rather than assuming the page is fresh.
(function () {{
  var MAXMIN = {STALE_PAGE_MIN};
  var el = document.getElementById('age'), box = document.getElementById('stalebox');
  var big = document.querySelector('.big');
  var gen = document.body.getAttribute('data-generated');
  var t = gen ? Date.parse(gen) : NaN;
  if (!gen || isNaN(t)) {{
    if (el) {{ el.textContent = 'snapshot age UNKNOWN'; }}
    if (big) {{ big.textContent = 'SNAPSHOT AGE UNKNOWN'; big.className = 'big warn'; }}
    return;
  }}
  function paint() {{
    var min = (Date.now() - t) / 60000;
    var txt = min < 1 ? 'snapshot just now'
            : min < 60 ? 'snapshot ' + Math.round(min) + 'm old'
            : min < 1440 ? 'snapshot ' + (min / 60).toFixed(1) + 'h old'
            : 'snapshot ' + (min / 1440).toFixed(1) + 'd old';
    if (el) el.textContent = txt;
    if (min > MAXMIN) {{
      if (big) {{
        big.textContent = 'HEALTH PAGE STALE';
        big.className = 'big bad';
      }}
      if (box) {{
        box.hidden = false;
        box.innerHTML = '<strong>This page stopped updating ' + txt.replace('snapshot ', '') +
          '.</strong> Everything below is a frozen snapshot from ' + gen +
          ' and may no longer be true. The publisher (board-page) is itself not running.';
      }}
    }}
  }}
  paint();
  setInterval(paint, 30000);
}})();
</script>
</body></html>"""

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(html)
    print(f"health page: {len(rows)} workflows, {len(bad)} not running "
          f"({', '.join(r['name'] for r in bad) or 'none'}); "
          f"{len(rows) - len(sched)} on demand, not judged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
