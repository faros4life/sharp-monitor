#!/usr/bin/env python3
"""
P1 BACKTEST (Nov 3, 2026; Peter 12:05 "but you can backtest"). PAPER / MEASUREMENT ONLY - reads history, touches no bet.
The phase-1 LIVE rule (agree_rules.phase1 without Muse AGREE + never Hard Rock-priced + retail deadband, the same as
sharp_monitor.phase1_label), applied to every alerts.json alert from Oct 12 (OddsPapi history window), graded on
Pinnacle's no-vig close (TRUE close, price-based) at two prices: the alert after-fee price, and the best after-fee
EXCHANGE price (ProphetX / Novig / Kalshi / Polymarket US) at the alert line +5 min (the bot's realistic fill; none =
not gettable). Quotes implying > +15% vs the close are dropped as misreads (counted).  Question: does phase-1 TOTALS beat the close in both halves, and do phase-1 spreads lose?
Standard bucket list on each. Private email; the log prints counts only.
"""
import os
import statistics as stt
from datetime import datetime, timedelta, timezone
import json

import buckets as bkt
import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
FIT_END = "2026-10-24"   # median alert day of the Oct 12+ window (stated)
CACHE_ONLY = (os.environ.get("PLEVEL_CACHE_ONLY") or "1") == "1"   # default: the history we already hold, no downloads


def pin_limit_at(b, f, pm, mkmap, when, lg):
    """(raw limit, 'own line' | 'main line') of Pinnacle's last tick at/before `when` (within 60 min) for the held side."""
    pz = cl.parsed(b)
    if not pz:
        return None, None
    sid = cl.SPORT[lg]

    def lim(mid, oid):
        m = (pm.get(str(mid)) or {}).get("outcomes", {}).get(oid) or {}
        lt = cl.last_tick((m.get("players") or {}).get("0"), when)
        if not lt or (when - lt[0]) > timedelta(minutes=60):
            return None
        return tb.num(lt[1].get("limit"))
    if pz[0] == "ml":
        side = cl.which_team(f, pz[1])
        if not side:
            return None, None
        if pz[3]:
            side = "2" if side == "1" else "1"
        mid = cl.ML_MARKET[sid]
        oid = {v: k for k, v in mkmap.get(mid, [0, 0, 0, {}])[3].items()}.get(side)
        v = lim(mid, oid) if oid else None
        return (v, "own line") if v else (None, None)
    typ = "spreads" if pz[0] == "spread" else "totals"
    if typ == "totals":
        want, name = pz[2], ("Over" if pz[1] == "OVER" else "Under")
    else:
        side = cl.which_team(f, pz[1])
        if not side:
            return None, None
        if pz[3]:
            side = "2" if side == "1" else "1"
        want, name = (pz[2] if side == "1" else -pz[2]), side
    main = None
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        oid = {v: k for k, v in outs.items()}.get(name)
        v = lim(mid, oid) if oid else None
        if not v:
            continue
        if abs(hcap - want) < 1e-9:
            return v, "own line"
        if main is None or v > main:
            main = v
    return (main, "main line") if main else (None, None)


def p1(a):
    import agree_rules as ar
    ok, why = ar.phase1(a, True)
    why = [w for w in why if w != "no Muse AGREE"]
    return bool(ok or not why) and ar.hr_priced(a) is False and ar.deadband(a) is False


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("plimit level: ODDSPAPI_KEY not set")
        return
    A = [a for a in (json.load(open("alerts.json")).get("alerts") or [])
         if a.get("sport") in LEAGUES and a.get("kind") in ("spr", "tot", "ml") and a.get("result") in ("W", "L", "P")
         and a.get("pricing_bettable") is not False and cl.tp(a.get("alert_utc")) and cl.tp(a["alert_utc"]) >= FROM]
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    R, miss = [], {"no fixture": 0, "not in cache": 0, "history error": 0, "no close": 0}
    for a in A:
        lg, t0 = a["sport"], cl.tp(a["alert_utc"])
        b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc"), "book": a.get("book")}
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if CACHE_ONLY and not all(os.path.exists(hc._path(fid, x)) for x in ("pinnacle",) + EXCH):
            miss["not in cache"] += 1
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), start)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            continue
        pin = cl.book_markets(h, "pinnacle")
        c, _ = cl.close_for(b, f, pin, mkmap, start, lg)
        if not c:
            miss["no close"] += 1
            continue
        limit, how = pin_limit_at(b, f, pin, mkmap, t0, lg)
        w5 = min(t0 + timedelta(minutes=5), start)
        best = None
        for slug in EXCH:
            bk = cl.book_markets(h, slug)
            x = cl.novig_at(b, f, bk, mkmap, w5, lg) if bk else None
            if x:
                v = el.eff(slug, x[0])
                if c["p"] * v - 1 > 0.15:   # quote implies > +15% vs Pinnacle's close: misread / crossed book, not a fill
                    miss["suspect quote dropped"] = miss.get("suspect quote dropped", 0) + 1
                    continue
                best = v if best is None or v > best else best
        want = cl.am_to_dec(a.get("price_after_fee") or a.get("price"))
        res = a["result"]
        units = (lambda d: (d - 1) if res == "W" else (-1.0 if res == "L" else 0.0))
        kind = {"tot": "totals", "spr": "spreads", "ml": "moneyline"}[a["kind"]]
        bet = str(a.get("bet") or "")
        sc = (("under" if bet.upper().startswith("UNDER") else "over") if kind == "totals" else
              (("dog" if (a.get("point") or 0) > 0 else "fav") if kind == "spreads" else
               ("dog" if (a.get("price") or 0) > 0 else "fav")))
        lead = (start - t0).total_seconds() / 60 if start else a.get("minutes_before_start")
        R.append({"p1": p1(a), "book": a.get("book"), "lg": lg, "mk": kind, "sc": sc, "sent": bool(a.get("sent_to_phone")), "day": t0.astimezone(ET).strftime("%Y-%m-%d"),
                  "lead": lead, "late": lead is not None and lead < 30, "am": a.get("price_after_fee"), "edge": a.get("edge_pct"),
                  "limit": limit, "lim_how": how, "gettable": best is not None,
                  "clv_g": round(100 * (c["p"] * best - 1), 2) if best else None, "u_g": units(best) if best else None,
                  "clv_a": round(100 * (c["p"] * want - 1), 2), "u_a": units(want)})
    days = sorted({r["day"] for r in R})
    mid = days[(len(days) - 1) // 2] if days else FIT_END

    def st_(xs, basis="g"):
        g = [x for x in xs if x[f"clv_{basis}"] is not None]
        if not g:
            return f"n {len(xs)} | graded 0"
        cv = [x[f"clv_{basis}"] for x in g]
        u = sum(x[f"u_{basis}"] for x in g)
        w = sum(x[f"u_{basis}"] > 0 for x in g)
        l_ = sum(x[f"u_{basis}"] < 0 for x in g)
        return (f"n {len(xs)} | graded {len(g)} {w}-{l_} {u:+.2f}u | CLV {stt.mean(cv):+.2f}% beat {sum(v > 0 for v in cv)}/{len(cv)} "
                f"({100 * sum(v > 0 for v in cv) / len(cv):.0f}%)")

    def block(name, xs):
        a, b = [r for r in xs if r["day"] <= mid], [r for r in xs if r["day"] > mid]
        return [f"{name}:", f"   at +5 min exchange price: {st_(xs)}", f"      H1 {st_(a)}", f"      H2 {st_(b)}",
                f"   at alert price:           {st_(xs, 'a')}", f"      H1 {st_(a, 'a')}", f"      H2 {st_(b, 'a')}"]
    P = [r for r in R if r["p1"] and r["sent"] and not r["late"]]
    L = [f"P1 BACKTEST - PHASE-1 LIVE RULE ON HISTORY (paper) | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         f"Alerts Oct 12+ in scope {len(A)}, read {len(R)}. Not read: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v),
         f"H1 <= {mid} < H2 (median alert day). LATE (final 30 min) excluded from the judged lines. TRUE close (Pinnacle no-vig, price).",
         f"Phase-1 qualifying: {len(P)} (gettable at +5 min: {sum(r['gettable'] for r in P)}).", ""]
    L += block("PHASE-1 ALL", P) + [""]
    L += block("PHASE-1 TOTALS (candidate rule)", [r for r in P if r["mk"] == "totals"]) + [""]
    L += block("PHASE-1 SPREADS (control)", [r for r in P if r["mk"] == "spreads"]) + [""]
    L += ["BY LEAGUE x MARKET (phase-1, +5 min price):"]
    for lg in LEAGUES:
        for mk in ("totals", "spreads"):
            xs = [r for r in P if r["lg"] == lg and r["mk"] == mk]
            if xs:
                L.append(f"   {lg} {mk}: {st_(xs)}")
    L += ["", "NON-PHASE-1 SENT (reference, +5 min price): " + st_([r for r in R if r["sent"] and not r["p1"] and not r["late"]])]

    def recs(xs, basis):
        return [{"day": r["day"], "clv": r[f"clv_{basis}"], "lg": r["lg"], "mk": r["mk"], "sc": r["sc"], "lead": r["lead"],
                 "late": r["late"], "edge": r["edge"], "am": r["am"], "pin_limit": r["limit"]} for r in xs if r[f"clv_{basis}"] is not None]
    PA = [r for r in R if r["p1"] and r["sent"]]
    L += [""] + bkt.section("PHASE-1 alerts at the +5-min exchange price (CLV % TRUE close)", recs(PA, "g"), "%")
    L += [""] + bkt.section("PHASE-1 alerts at the alert price (CLV % TRUE close)", recs(PA, "a"), "%")
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} (billable {cl.STATS['billable']}).")
    ex.send("Bets P1 BACKTEST (phase-1 LIVE rule on history, paper)", "\n".join(L))
    print(f"p1 backtest: scope {len(A)}, read {len(R)}, phase-1 {len(P)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
