#!/usr/bin/env python3
"""
P LIMIT + 2X TAG for the live Bets Board (Nov 2, 2026; Muse 11:35 rulings: P only, OddsJam scale; Peter: "add P limit and
a live P limit to the board").

For every board row today (NBA / NFL / NHL / NCAAF), read Pinnacle's limit for the row's market and side from OddsPapi's
free history: at the row's alert time, and now (the latest tick). Limits are shown on OddsJam's scale (OddsPapi x 4/3,
the Nov 2 identity check). 2X PASS = bet-side exchange money (our monitor's depth: Novig + ProphetX + Kalshi) >= 2x the
P limit at the alert, with 2 of those 3 at >= $5k and >= $25k total (3x in playoffs; none now). A row with no Pinnacle
limit is NO LIMIT DATA (B is not used: Muse 11:35). Measurement / display only: nothing here changes a call or a bet.

Writes x2/limits.json (public market data, like the board itself) and oddspapi/fixtures.json (a shared fixture cache so
other jobs need fewer billable calls). Billable: /fixtures per league at most every 8 h, and only when a row's game is
missing from the cache. The log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
OUT = "x2/limits.json"
CACHE = "oddspapi/fixtures.json"
OJ = 4 / 3
EXCH = ("novig", "prophetx", "kalshi")

# Nov 23 (Peter, via VALUE LAB). Every 2X backtest so far used a DEPTH-ONLY proxy - clauses 2 and 3
# without the Pinnacle multiple - which fires on 73% of resulted plays. That is a different trigger
# from the one this file computes. So the TRUE verdict and the limit it used are now persisted per
# row, with each clause separately, so the multiple can be re-derived and audited rather than the
# flag being trusted on its own.
#
# A SIDECAR, NOT THE FEED. liquidity_monitor rewrites liquidity/alerts.json in full on every run,
# so a second writer would race it and lose. x2/limits.json is keyed by "<key>|<alerted_utc>",
# which joins back to the alert, and the Pinnacle limit is reconstructed AS OF the alert's print
# time over /historical-odds - a FREE path - so nothing billable enters the alerting path.
FORWARD_FROM = (os.environ.get("X2_FORWARD_FROM") or "2026-11-23").strip()[:10]
# Deliberate, bounded backfill. 0 = today only, the behaviour before this change. A backfill needs
# fixtures outside the normal now-1d..now+3d window, and /fixtures BILLS (only /account and
# /historical-odds are free), so this is opt-in per run and never the default.
BACKFILL_DAYS = max(0, int(os.environ.get("X2_BACKFILL_DAYS") or "0"))
# Nov 23: a single 30-day backfill was KILLED by the 25-minute timeout - "Terminate orphan process:
# pid (python)", CLAUDE.md's decisive tell for a kill mid-work rather than a dropped queue run. It
# saved nothing. The schedule fires every 30 minutes, so raising the timeout only collides with the
# next firing; the work has to get smaller instead. So a backfill is a bounded SLICE, run as many
# times as it takes: the window is [now - DAYS, now - END_DAYS], and a row that already carries a
# verdict is skipped, so repeat dispatches make progress instead of redoing the same work.
BACKFILL_END_DAYS = max(0, int(os.environ.get("X2_BACKFILL_END_DAYS") or "0"))


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def depth(x, b):
    d = (x.get("depth_by_book") or {}).get(b) or {}
    v = d.get("this_side_all_levels") if d.get("this_side_all_levels") is not None else d.get("this_side")
    return float(v or 0)


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("x2 tag: ODDSPAPI_KEY not set")
        return
    day0 = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    day1 = None
    if BACKFILL_DAYS:
        day0 -= timedelta(days=BACKFILL_DAYS)
        if BACKFILL_END_DAYS:
            day1 = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0) \
                   - timedelta(days=BACKFILL_END_DAYS)
    a = load("liquidity/alerts.json", [])
    a = a if isinstance(a, list) else a.get("alerts") or []
    rows = [x for x in a if x.get("league") in cl.SPORT and x.get("market") in ("moneyline", "spread", "total")
            and (tb.tparse(x.get("alerted_utc")) or now) >= day0
            and (day1 is None or (tb.tparse(x.get("alerted_utc")) or now) < day1)]
    done = (load(OUT, {"rows": {}}).get("rows") or {})
    if BACKFILL_DAYS:
        before = len(rows)
        rows = [x for x in rows
                if done.get(f"{x.get('key')}|{x.get('alerted_utc')}", {}).get("x2_pass") is None]
        print(f"x2 tag: backfill slice {BACKFILL_DAYS}d..{BACKFILL_END_DAYS}d | "
              f"{before} row(s) in the window, {before - len(rows)} already have a verdict, "
              f"{len(rows)} to do")
    cache = load(CACHE, {"fixtures": {}, "fx_last": {}})
    st = {"fixtures": cache.get("fixtures") or {}, "fx_last": cache.get("fx_last") or {}, "billable": {}}
    out = load(OUT, {"rows": {}})
    prev = out.get("rows") or {}
    mkmap = cl.load_markets(st, now)
    need = {}
    for x in rows:
        b = {"league": x["league"], "game": x.get("game"), "teams": [{"name": n} for n in x.get("teams") or []], "game_start": x.get("start_utc")}
        if not cl.find_fixture(st, b):
            need.setdefault(x["league"], True)
    for lg in need:
        last = tb.tparse(st["fx_last"].get(lg))
        # The 8h guard keeps the ordinary half-hourly run cheap. A BACKFILL must ignore it: the
        # cached window is now-1d..now+3d, so a league refreshed within 8h would skip the fetch
        # entirely and the wider window would never be loaded. That is what left the first 30-day
        # run at 11% limit coverage - 2,838 of 3,202 rows found no fixture.
        if last and now - last < timedelta(hours=8) and not BACKFILL_DAYS:
            continue
        st["fx_last"].pop(lg, None)
        cl.refresh_fixtures(st, now, lg, (now - timedelta(days=1 + BACKFILL_DAYS)).astimezone(ET),
                            (now + timedelta(days=3)).astimezone(ET))
    t_fix = (datetime.now(timezone.utc) - now).total_seconds()
    hist, res = {}, {}
    for x in rows:
        k = f"{x.get('key')}|{x.get('alerted_utc')}"
        b = {"league": x["league"], "game": x.get("game"), "teams": [{"name": n} for n in x.get("teams") or []], "game_start": x.get("start_utc")}
        fid = cl.find_fixture(st, b)
        rec = dict(prev.get(k) or {})
        # BASIS FIRST. It describes WHEN the alert printed, which is known before any lookup, and
        # stamping it after the fixture `continue`s left 2,838 of 3,202 rows with none - so a
        # reader counting forward vs backfill silently under-counted both.
        rec["basis"] = ("forward" if str(x.get("alerted_utc") or "")[:10] >= FORWARD_FROM
                        else "backfill")
        dep = {e: depth(x, e) for e in EXCH}
        tot = sum(dep.values())
        rec.update(liq=round(tot), two5k=sum(1 for v in dep.values() if v >= 5000) >= 2)
        if not fid:
            rec.setdefault("note", "NO LIMIT DATA (game not found)")
            res[k] = rec
            continue
        if fid not in hist:
            hist[fid] = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
        h = hist[fid]
        if isinstance(h, dict) and h.get("_error"):
            res[k] = rec
            continue
        import x2_backtest as xb
        pm = cl.book_markets(h, "pinnacle")
        f = st["fixtures"][fid]
        if rec.get("p_alert") is None:
            lim, how, _ = xb.limit_at(x, f, pm, mkmap, tb.tparse(x.get("alerted_utc")))
            if lim is not None:
                rec.update(p_alert=round(lim * OJ), how=how)
        st0 = tb.tparse(x.get("start_utc"))
        lim2, how2, _ = xb.limit_at(x, f, pm, mkmap, min(now, st0) if st0 else now)
        if lim2 is not None:
            rec.update(p_now=round(lim2 * OJ), p_now_utc=cl.iso(now))
        if rec.get("p_alert"):
            rec.pop("note", None)
            # The three clauses, each on the record. The flag alone cannot be audited; these can.
            c_mult = tot >= 2 * rec["p_alert"]
            c_two5k = bool(rec["two5k"])
            c_total = tot >= 25000
            ok = c_mult and c_two5k and c_total
            rec.update(x2=bool(ok), x2_pass=bool(ok), p_limit=rec["p_alert"],
                       c_mult=bool(c_mult), c_two5k=c_two5k, c_total=bool(c_total),
                       mult=round(tot / rec["p_alert"], 3) if rec["p_alert"] else None,
                       exch_total=round(tot))
            if ok and not rec.get("x2_first_utc"):
                rec["x2_first_utc"] = cl.iso(now)
        else:
            # No limit means NO VERDICT - never a False, which would read as "tested and failed".
            for f in ("x2", "x2_pass", "p_limit", "c_mult", "mult"):
                rec.pop(f, None)
            rec.update(note="NO LIMIT DATA", c_two5k=bool(rec["two5k"]),
                       c_total=tot >= 25000, exch_total=round(tot))
        res[k] = rec
    os.makedirs("x2", exist_ok=True)
    os.makedirs("oddspapi", exist_ok=True)
    # A row that HAS a verdict is evidence and is kept; the 3-day prune is for rows still being
    # followed. Without this a backfilled row would be dropped by the next ordinary run.
    keep = {k: v for k, v in prev.items()
            if k not in res and (v.get("x2_pass") is not None
                                 or (v.get("p_now_utc") or "") >= cl.iso(now - timedelta(days=3)))}
    keep.update(res)
    json.dump({"updated": cl.iso(now), "scale": "OddsJam (OddsPapi x 4/3)", "rows": keep}, open(OUT, "w"), separators=(",", ":"))
    cut = cl.iso(now - timedelta(days=5))
    json.dump({"fixtures": {k: v for k, v in st["fixtures"].items() if (v.get("start") or "") >= cut}, "fx_last": st["fx_last"],
               "note": "OddsPapi fixture ids (public)"}, open(CACHE, "w"), separators=(",", ":"))
    fwd = [v for v in res.values() if v.get("basis") == "forward"]
    bak = [v for v in res.values() if v.get("basis") == "backfill"]
    print(f"x2 tag: rows {len(rows)}, with P limit {sum(1 for v in res.values() if v.get('p_alert'))}, "
          f"TRUE 2X {sum(1 for v in res.values() if v.get('x2_pass'))}, calls {len(cl.CALLS)}")
    print(f"x2 tag: forward {len(fwd)} (true 2X {sum(1 for v in fwd if v.get('x2_pass'))}), "
          f"backfill {len(bak)} (true 2X {sum(1 for v in bak if v.get('x2_pass'))}) - "
          f"backfill is BACKTEST data and must not pool into the forward count")
    el = (datetime.now(timezone.utc) - now).total_seconds()
    print(f"x2 tag: elapsed {el:.0f}s (fixtures {t_fix:.0f}s, rows {el - t_fix:.0f}s) - the 30-day "
          f"run was killed at the 25-minute timeout, so slices are sized against this")
    cov = sum(1 for v in res.values() if v.get("p_limit"))
    print(f"x2 tag: limit coverage {cov}/{len(res)} rows "
          f"({(100.0 * cov / len(res)) if res else 0:.0f}%) - rows with no Pinnacle limit carry NO "
          f"verdict and cannot judge a cell")
    loose = sum(1 for v in res.values() if v.get("c_two5k") and v.get("c_total"))
    print(f"x2 tag: depth-only proxy would pass {loose}, the multiple clause holds on "
          f"{sum(1 for v in res.values() if v.get('c_mult'))} - the gap is why the two differ")


if __name__ == "__main__":
    main()
