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
    wfs, err = gh(f"/repos/{REPO}/actions/workflows?per_page=100")
    if err:
        print(f"health: workflow list unreadable ({err}) - page not written")
        return 1

    rows = []
    for w in (wfs or {}).get("workflows") or []:
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
        auto = any(str(r.get("event")) in ("schedule", "workflow_run") for r in rl)
        starts = sorted([t for t in (ts(r.get("created_at")) for r in rl) if t], reverse=True)
        gaps = [(starts[i] - starts[i + 1]).total_seconds() / 60 for i in range(len(starts) - 1)]
        cadence = statistics.median(gaps) if gaps else None
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
            state, why = "STALE", f"last success {ok_txt}, its own cadence is ~{cadence:.0f}m"
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
        ("Bets Board publishing", ("board-page",)),
        ("Bets Board build",     ("bets-board",)),
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
    sysrows.append(("Novig submissions", "PAUSED",
                    "held by EXEC_NOVIG_SUBMIT; no dispatch credential is configured"))
    sysrows.append(("Phone alert delivery", "NOT CHECKED",
                    "this page cannot confirm your phone received anything"))

    order = {"FAIL": 0, "STALE": 1, "WARN": 2, "OK": 3, "ON DEMAND": 4}
    rows.sort(key=lambda r: (order[r["state"]], -r["ok_min"]))
    sched = [r for r in rows if r["state"] != "ON DEMAND"]
    bad = [r for r in sched if r["state"] in ("FAIL", "STALE")]
    headline = ("ALL RUNNING" if not bad and not [r for r in sched if r["state"] == "WARN"]
                else f"{len(bad)} NOT RUNNING" if bad else "RUNNING, WITH WARNINGS")
    hcls = "ok" if headline == "ALL RUNNING" else ("warn" if not bad else "bad")

    SDOT = {"OK": "ok", "WARN": "warn", "STALE": "bad", "FAIL": "bad",
            "UNKNOWN": "warn", "PAUSED": "warn", "NOT CHECKED": "warn", "ON DEMAND": "idle"}

    def tr(r):
        dot = {"OK": "ok", "WARN": "warn", "STALE": "bad", "FAIL": "bad",
               "ON DEMAND": "idle"}[r["state"]]
        run = '<span class=run>running</span>' if r["running"] else ""
        cad = f"~{r['cadence']:.0f}m" if r["cadence"] else "-"
        return (f"<tr><td><span class='dot {dot}'></span>{r['state']}</td>"
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
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;
vertical-align:1px}}
.dot.ok{{background:var(--ok)}}.dot.warn{{background:var(--warn)}}.dot.bad{{background:var(--bad)}}
.dot.idle{{background:var(--mut);opacity:.45}}
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
{''.join(f"<tr><td>{n}</td><td><span class='dot {SDOT.get(st,'warn')}'></span>{st}</td>"
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
