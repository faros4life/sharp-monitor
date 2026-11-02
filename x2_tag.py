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
    a = load("liquidity/alerts.json", [])
    a = a if isinstance(a, list) else a.get("alerts") or []
    rows = [x for x in a if x.get("league") in cl.SPORT and x.get("market") in ("moneyline", "spread", "total")
            and (tb.tparse(x.get("alerted_utc")) or now) >= day0]
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
        if last and now - last < timedelta(hours=8):
            continue
        st["fx_last"].pop(lg, None)
        cl.refresh_fixtures(st, now, lg, (now - timedelta(days=1)).astimezone(ET), (now + timedelta(days=3)).astimezone(ET))
    hist, res = {}, {}
    for x in rows:
        k = f"{x.get('key')}|{x.get('alerted_utc')}"
        b = {"league": x["league"], "game": x.get("game"), "teams": [{"name": n} for n in x.get("teams") or []], "game_start": x.get("start_utc")}
        fid = cl.find_fixture(st, b)
        rec = dict(prev.get(k) or {})
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
            ok = tot >= 2 * rec["p_alert"] and rec["two5k"] and tot >= 25000
            rec["x2"] = bool(ok)
            if ok and not rec.get("x2_first_utc"):
                rec["x2_first_utc"] = cl.iso(now)
        else:
            rec["note"] = "NO LIMIT DATA"
        res[k] = rec
    os.makedirs("x2", exist_ok=True)
    os.makedirs("oddspapi", exist_ok=True)
    keep = {k: v for k, v in prev.items() if k not in res and (v.get("p_now_utc") or "") >= cl.iso(now - timedelta(days=3))}
    keep.update(res)
    json.dump({"updated": cl.iso(now), "scale": "OddsJam (OddsPapi x 4/3)", "rows": keep}, open(OUT, "w"), separators=(",", ":"))
    cut = cl.iso(now - timedelta(days=5))
    json.dump({"fixtures": {k: v for k, v in st["fixtures"].items() if (v.get("start") or "") >= cut}, "fx_last": st["fx_last"],
               "note": "OddsPapi fixture ids (public)"}, open(CACHE, "w"), separators=(",", ":"))
    print(f"x2 tag: rows {len(rows)}, with P limit {sum(1 for v in res.values() if v.get('p_alert'))}, "
          f"2X {sum(1 for v in res.values() if v.get('x2'))}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
