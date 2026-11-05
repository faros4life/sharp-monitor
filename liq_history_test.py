#!/usr/bin/env python3
"""
LIQUIDITY ALERTS vs THE DOWNLOADED HISTORY (Nov 4, 2026; Peter 9:22 "5 minutes after is too long ... bot will be faster
than that and we get price at alert or better"). PAPER / MEASUREMENT ONLY - reads history, touches no bet, no alert, no
board, no executor input.

Population: liquidity/alerts.json, NBA / NFL / NCAAF / NHL, moneyline / spread / total, graded W/L/P, not an artifact
or close_suspect, inside the history window (Oct 12+; liquidity alerts start Oct 22).
PRICE: every play is graded at the ALERT price (after the trigger exchange's fee) - the bot only bets that price or better.
GETTABLE: at least one exchange we can bet (ProphetX / Novig / Kalshi / Polymarket US) had that after-fee price OR BETTER
on its last quote at or before alert + GET_SEC seconds (default 60). Not gettable = counted, not graded in the judged rows.
CLV: Pinnacle's true no-vig close for the held side x the alert's after-fee price - 1 (percent), not the exchange's own close.
PINNACLE LIMIT: Pinnacle's raw max-stake limit on that side at the alert (last tick within 60 min), and vs its own value
2 hours earlier (rising = 1.5x+). Limits rise toward tip-off, so the lead split always goes with it.
JUDGED rule (proposed Nov 4): NBA totals, alerted 4h+ before tip. H1 <= FIT_END < H2. Everything else is descriptive.
Private email; the Actions log prints counts only.
"""
import json
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import plimit_level as pl
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
SLUG = {"kalshi": "kalshi", "polymarket": "polymarket.us", "novig": "novig.us", "prophetx": "prophetx"}
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
FIT_END = os.environ.get("LIQH_FIT_END", "") or "2026-10-28"
GET_SEC = int(os.environ.get("LIQH_GET_SEC", "") or "60")
CACHE_ONLY = (os.environ.get("LIQH_CACHE_ONLY") or "1") == "1"   # default: the history we already hold, no downloads
ALERTS = os.environ.get("LIQH_ALERTS", "") or "liquidity/alerts.json"


def units(res, dec):
    return (dec - 1) if res == "W" else (-1.0 if res == "L" else 0.0)


def bet_text(a):
    """Bet text the history tools parse, from the alert's own side and line (Polymarket labels like 'Over (237.5)' or
    'Team (+3.5)' don't parse; Kalshi 'NOT ...' wording is already resolved in side/line)."""
    sd, ln, mk = a.get("side"), a.get("line"), a.get("market")
    if mk == "total" and sd in ("OVER", "UNDER") and ln is not None:
        return f"{'Over' if sd == 'OVER' else 'Under'} {ln:g}"
    if mk == "spread" and sd and ln is not None:
        return f"{sd} {ln:+g}"
    if mk == "moneyline" and sd:
        return f"{sd} ML"
    return a.get("side_label")


def size_x(a):
    b, n = a.get("base_depth") or 0, a.get("new_money") or 0
    return (b + n) / b if b > 0 else None


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("liq history test: ODDSPAPI_KEY not set")
        return
    A = [a for a in (json.load(open(ALERTS)).get("alerts") or [])
         if a.get("league") in LEAGUES and a.get("market") in ("moneyline", "spread", "total")
         and a.get("result") in ("W", "L", "P") and not a.get("artifact") and not a.get("close_suspect")
         and cl.tp(a.get("alerted_utc")) and cl.tp(a["alerted_utc"]) >= FROM and a.get("price")]
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    R = []
    miss = {"no fixture": 0, "not in cache": 0, "history error": 0, "no Pinnacle close": 0}
    for a in A:
        lg, t0 = a["league"], cl.tp(a["alerted_utc"])
        game = (a.get("game") or "").split(":")[0]
        b = {"bet": bet_text(a), "league": lg, "game": game, "game_start": a.get("start_utc"), "book": a.get("book")}
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
            miss["no Pinnacle close"] += 1
            continue
        want = el.eff(SLUG.get(a.get("book"), a.get("book")), 1 / a["price"])   # alert price, after the trigger book's fee
        when = min(t0 + timedelta(seconds=GET_SEC), start)
        best, best_bk = None, None
        for slug in EXCH:
            bk = cl.book_markets(h, slug)
            x = cl.novig_at(b, f, bk, mkmap, when, lg) if bk else None
            if not x:
                continue
            v = el.eff(slug, x[0])
            if c["p"] * v - 1 > 0.15:   # same rule as P1 / exchange-lag: a quote > +15% vs the close is a misread
                miss["suspect quote dropped"] = miss.get("suspect quote dropped", 0) + 1
                continue
            if best is None or v > best:
                best, best_bk = v, slug
        lim, how = pl.pin_limit_at(b, f, pin, mkmap, t0, lg)
        lim2, _ = pl.pin_limit_at(b, f, pin, mkmap, t0 - timedelta(hours=2), lg)
        lead = (start - t0).total_seconds() / 3600 if start else None
        res = a["result"]
        sd = (a.get("side") or "").upper()
        R.append({"lg": lg, "mk": a["market"], "day": t0.astimezone(ET).strftime("%Y-%m-%d"), "lead": lead,
                  "side": sd if sd in ("OVER", "UNDER") else a["market"], "book": a.get("book"),
                  "size_x": size_x(a), "nm": a.get("new_money"), "quiet": not a.get("sharp_agree") and not a.get("sharp_oppose"),
                  "agree": bool(a.get("sharp_agree")), "pulled": bool(a.get("pulled")),
                  "gettable": best is not None and best >= want - 1e-9, "best": best, "best_bk": best_bk,
                  "clv": round(100 * (c["p"] * want - 1), 2), "u": units(res, want),
                  "u_best": units(res, best) if best and best >= want - 1e-9 else None,
                  "lim": lim, "lim_how": how, "lim_x": (lim / lim2) if lim and lim2 else None,
                  "own_clv": a.get("clv_cents")})

    def st_(xs, only_get=True):
        g = [x for x in xs if x["gettable"]] if only_get else xs
        if not g:
            return f"n {len(xs)} | gettable 0"
        w = sum(x["u"] > 0 for x in g)
        l_ = sum(x["u"] < 0 for x in g)
        u = sum(x["u"] for x in g)
        cv = [x["clv"] for x in g]
        h1 = [x for x in g if x["day"] <= FIT_END]
        h2 = [x for x in g if x["day"] > FIT_END]
        pp = lambda z: f"{sum(x['u'] for x in z) / len(z):+.3f} (n{len(z)})" if z else "n0"
        return (f"n {len(xs)} | gettable {len(g)} | {w}-{l_} {u:+.2f}u {u / len(g):+.3f}/play | Pinnacle CLV "
                f"{stt.mean(cv):+.2f}% beat {100 * sum(v > 0 for v in cv) / len(cv):.0f}% | H1 {pp(h1)} H2 {pp(h2)}")

    rule = [r for r in R if r["lg"] == "NBA" and r["mk"] == "total" and r["lead"] is not None and r["lead"] >= 4]
    L = [f"LIQUIDITY ALERTS vs DOWNLOADED HISTORY - PAPER ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         f"Graded 1u flat at the ALERT price (after fee). Gettable = that price or better on ProphetX/Novig/Kalshi/PM US within "
         f"{GET_SEC}s of the alert. CLV vs Pinnacle's no-vig close. H1 <= {FIT_END} < H2. Judged rows count gettable plays only.",
         f"Alerts in scope {len(A)}, read {len(R)}. Not read: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v),
         f"Gettable: {sum(r['gettable'] for r in R)}/{len(R)}.", "",
         "JUDGED - NBA totals, alerted 4h+ before tip:",
         f"   {st_(rule)}",
         f"   all plays incl. not gettable (alert price): {st_(rule, False)}",
         f"   gettable plays at the best price found: "
         + (f"{sum(r['u_best'] for r in rule if r['u_best'] is not None):+.2f}u" if any(r['u_best'] is not None for r in rule) else "n0"),
         "", "INSIDE THE RULE (gettable):"]
    for nm, f in (("Under", lambda r: r["side"] == "UNDER"), ("Over", lambda r: r["side"] == "OVER"),
                  ("4-12h", lambda r: r["lead"] < 12), ("12h+", lambda r: r["lead"] >= 12),
                  ("size 2x+", lambda r: (r["size_x"] or 0) >= 2), ("size 1.5-2x", lambda r: 1.5 <= (r["size_x"] or 0) < 2),
                  ("size <1.5x", lambda r: (r["size_x"] or 0) < 1.5), ("quiet", lambda r: r["quiet"]),
                  ("sharp agrees", lambda r: r["agree"]), ("pulled", lambda r: r["pulled"]), ("stayed", lambda r: not r["pulled"]),
                  ("Kalshi trigger", lambda r: r["book"] == "kalshi"), ("Polymarket trigger", lambda r: r["book"] == "polymarket"),
                  ("Pinnacle limit rising 1.5x+ (vs 2h before)", lambda r: (r["lim_x"] or 0) >= 1.5),
                  ("Pinnacle limit not rising", lambda r: r["lim_x"] is not None and r["lim_x"] < 1.5),
                  ("no Pinnacle limit read", lambda r: r["lim"] is None),
                  # Nov 4 (Peter + Muse): the print-size split. On the board's own close, NBA totals 4h+ with a
                  # 25-50k print is +18.22u on 80 (both halves) while 50k+ is negative. These rows grade that same
                  # split at the ALERT price against PINNACLE'S no-vig close - the test that decides whether the
                  # candidate cell is a lane or a hot streak.
                  ("print under 25k", lambda r: (r["nm"] or 0) < 25_000),
                  ("print 25-50k  <= THE CANDIDATE", lambda r: 25_000 <= (r["nm"] or 0) < 50_000),
                  ("print 50-100k", lambda r: 50_000 <= (r["nm"] or 0) < 100_000),
                  ("print 100k+", lambda r: (r["nm"] or 0) >= 100_000),
                  ("print 25-50k, unders", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["side"] == "UNDER"),
                  ("print 25-50k, overs", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["side"] == "OVER"),
                  ("print 25-50k, quiet (no sharp tag)", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["quiet"]),
                  ("print 25-50k, 4-12h", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["lead"] < 12),
                  ("print 25-50k, 12h+", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["lead"] >= 12)):
        L.append(f"   {nm}: {st_([r for r in rule if f(r)])}")
    lims = sorted(r["lim"] for r in rule if r["lim"])
    if len(lims) >= 9:
        t1, t2 = lims[len(lims) // 3], lims[(2 * len(lims)) // 3]
        L.append(f"   Pinnacle limit low (<= {t1:,.0f}): {st_([r for r in rule if r['lim'] and r['lim'] <= t1])}")
        L.append(f"   Pinnacle limit mid: {st_([r for r in rule if r['lim'] and t1 < r['lim'] <= t2])}")
        L.append(f"   Pinnacle limit high (> {t2:,.0f}): {st_([r for r in rule if r['lim'] and r['lim'] > t2])}")
    L += ["", "NBA totals under 4h (the rule's excluded side):",
          f"   {st_([r for r in R if r['lg'] == 'NBA' and r['mk'] == 'total' and r['lead'] is not None and r['lead'] < 4])}",
          "", "BY LEAGUE x MARKET (descriptive, all leads, gettable):"]
    for lg in LEAGUES:
        for mk in ("total", "moneyline", "spread"):
            xs = [r for r in R if r["lg"] == lg and r["mk"] == mk]
            if xs:
                L.append(f"   {lg} {mk}: {st_(xs)}")
    ag = [r for r in rule if r["own_clv"] is not None]
    if ag:
        L += ["", f"CHECK - exchange close vs Pinnacle close on the rule's plays: exchange CLV {stt.mean(r['own_clv'] for r in ag):+.2f}c, "
                  f"Pinnacle CLV {stt.mean(r['clv'] for r in ag):+.2f}% (n {len(ag)})"]
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} "
             f"(billable {cl.STATS['billable']}).")
    ex.send("Bets LIQUIDITY vs HISTORY (paper)", "\n".join(L))
    print(f"liq history test: scope {len(A)}, read {len(R)}, gettable {sum(r['gettable'] for r in R)}, "
          f"rule {len(rule)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
