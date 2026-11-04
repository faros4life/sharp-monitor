#!/usr/bin/env python3
"""
CLOSE-VS-CLOSE BY LEAGUE - RUN 1, PRELIMINARY, NOT JUDGED (Nov 4, 2026; Peter/Muse 11:04: "both, in sequence").
PAPER / MEASUREMENT ONLY - reads records and the downloaded history; changes nothing the monitor, board, lanes or executor read.

Question: per league, which close predicts results better - Pinnacle's no-vig close or the exchange's own close?
Run 1's job: prove the table works and show its shape. NO BENCHMARK FLIPS ON THIS RUN, whatever it shows.

Population: liquidity/alerts.json (LIQ-MAIN) + liquidity-extra/alerts.json (LIQ-EXTRA), NBA / NFL / NCAAF / NHL, moneyline /
spread / total, graded W/L (pushes out of the probability tests), DEDUPED: one play per game + market + side, the first alert
(Peter 10:58: "one play count 1x even if it comes in 5x").
CONTAMINATION GUARD (Oct 28 ruling): the exchange-close leg uses only alerts from CLEAN_FROM on, pregame, not close_suspect, not
an artifact. Earlier plays count toward units only; the excluded count is reported per league.
Both closes are compared on the SAME plays (rows with both). Price basis: the alert price after the trigger exchange's fee.
- Pinnacle close: no-vig win chance for the held side at the close (history cache).
- Exchange close: the monitor's last pregame read of the trigger exchange's price for the side, taken as its win chance.
Per league (and league x market where n >= 30): actual units | expected units under each close | wins vs expected wins under each
| log loss of each close vs results; overall and by halves (median day). Coverage < 90% in either half = "Incomplete: partial data".
RUN 2 GATE PREVIEW: exchange closes RECONSTRUCTED from history ticks (last tick before tip, the trigger exchange, alert line and
side; Kalshi / Novig / ProphetX - Polymarket global is not in the history) vs the monitor's clean closes: agreement within 1c on
the first 20 (registered gate: >= 18 of 20) and overall. Private email; the log prints counts only.
"""
import json
import math
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import liq_history_test as lh
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
SLUG = {"kalshi": "kalshi", "polymarket": "polymarket.us", "novig": "novig.us", "prophetx": "prophetx"}
REC_SLUG = {"kalshi": "kalshi", "novig": "novig.us", "prophetx": "prophetx"}   # Polymarket global is not in the history
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
CLEAN_FROM = os.environ.get("CVC_CLEAN_FROM", "") or "2026-10-28T00:00:00Z"
FILES = ("liquidity/alerts.json", "liquidity-extra/alerts.json")
CACHE_ONLY = (os.environ.get("CVC_CACHE_ONLY") or "1") == "1"


def ll(p, y):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("close vs close: ODDSPAPI_KEY not set")
        return
    A = []
    for fn in FILES:
        try:
            for a in json.load(open(fn)).get("alerts") or []:
                a["_src"] = "LIQ-EXTRA" if "extra" in fn else "LIQ-MAIN"
                A.append(a)
        except Exception:
            pass
    A = [a for a in A if a.get("league") in LEAGUES and a.get("market") in ("moneyline", "spread", "total")
         and a.get("result") in ("W", "L", "P") and a.get("price") and cl.tp(a.get("alerted_utc"))
         and cl.tp(a["alerted_utc"]) >= FROM]
    A.sort(key=lambda a: a["alerted_utc"])
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), now.astimezone(ET))
    miss = {"no fixture": 0, "duplicate (same game+market+side)": 0, "not in cache": 0, "no Pinnacle close": 0}
    seen, R, hist = set(), [], {}
    for a in A:
        lg, t0 = a["league"], cl.tp(a["alerted_utc"])
        b = {"bet": lh.bet_text(a), "league": lg, "game": (a.get("game") or "").split(":")[0],
             "game_start": a.get("start_utc"), "book": a.get("book")}
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            continue
        dk = (fid, a["market"], str(a.get("side")))
        if dk in seen:
            miss["duplicate (same game+market+side)"] += 1
            continue
        seen.add(dk)
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if CACHE_ONLY and not all(os.path.exists(hc._path(fid, x)) for x in ("pinnacle",) + EXCH):
            miss["not in cache"] += 1
            continue
        if fid not in hist:
            hist.clear()   # one game at a time (memory)
            hist[fid] = hc.get_hist(fid, ["pinnacle"] + list(EXCH), start)
        h = hist[fid]
        if isinstance(h, dict) and h.get("_error"):
            miss["not in cache"] += 1
            continue
        c, _ = cl.close_for(b, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
        if not c:
            miss["no Pinnacle close"] += 1
            continue
        dec = el.eff(SLUG.get(a["book"], a["book"]), 1 / a["price"])
        clean = (a["alerted_utc"] >= CLEAN_FROM and not a.get("close_suspect") and not a.get("artifact")
                 and a.get("close_price") is not None and 0 < a["close_price"] < 1)
        rec = None
        rs = REC_SLUG.get(a["book"])
        if rs and clean:
            x = cl.novig_at(b, f, cl.book_markets(h, rs), mkmap, start - timedelta(minutes=1), lg)
            if x and x[0] and x[0] > 1:
                rec = 1 / x[0]
        res = a["result"]
        R.append({"lg": lg, "mk": a["market"], "day": t0.astimezone(ET).strftime("%Y-%m-%d"), "src": a["_src"],
                  "y": 1 if res == "W" else (0 if res == "L" else None), "u": lh.units(res, dec), "dec": dec,
                  "p_pin": c["p"], "p_ex": a["close_price"] if clean else None, "clean": clean, "rec": rec,
                  "t": a["alerted_utc"]})

    def table(xs):
        g = [r for r in xs if r["y"] is not None]
        both = [r for r in g if r["p_ex"] is not None]
        days = sorted({r["day"] for r in xs})
        mid = days[(len(days) - 1) // 2] if days else ""
        out = {"n": len(xs), "u": sum(r["u"] for r in xs), "both": len(both), "excluded": sum(1 for r in g if r["p_ex"] is None)}
        if both:
            out["exp_pin"] = sum(r["p_pin"] * r["dec"] - 1 for r in both)
            out["exp_ex"] = sum(r["p_ex"] * r["dec"] - 1 for r in both)
            out["u_both"] = sum(r["u"] for r in both)
            out["w"] = sum(r["y"] for r in both)
            out["ew_pin"] = sum(r["p_pin"] for r in both)
            out["ew_ex"] = sum(r["p_ex"] for r in both)
            out["ll_pin"] = stt.mean(ll(r["p_pin"], r["y"]) for r in both)
            out["ll_ex"] = stt.mean(ll(r["p_ex"], r["y"]) for r in both)
        cov = []
        for half in ([r for r in g if r["day"] <= mid], [r for r in g if r["day"] > mid]):
            cov.append(100 * sum(1 for r in half if r["p_ex"] is not None) / len(half) if half else 0)
        out["cov"] = cov
        return out

    def line(name, xs):
        t = table(xs)
        head = f"   {name}: n {t['n']} | actual {t['u']:+.2f}u (all plays)"
        if not t["both"]:
            return head + f" | both closes 0 (pre-fix excluded {t['excluded']}) -> Incomplete: partial data"
        inc = " -> Incomplete: partial data" if min(t["cov"]) < 90 else ""
        return (head + f"\n      on {t['both']} plays with both closes (pre-fix excluded {t['excluded']}; coverage H1 {t['cov'][0]:.0f}% "
                f"H2 {t['cov'][1]:.0f}%){inc}:\n"
                f"      actual {t['u_both']:+.2f}u | expected {t['exp_pin']:+.2f}u (Pinnacle no-vig close, alert price after fees) "
                f"| expected {t['exp_ex']:+.2f}u (exchange close, alert price after fees)\n"
                f"      wins {t['w']} vs expected {t['ew_pin']:.1f} (Pinnacle) / {t['ew_ex']:.1f} (exchange) | log loss "
                f"Pinnacle {t['ll_pin']:.4f} vs exchange {t['ll_ex']:.4f} (lower predicts better)")

    L = [f"CLOSE-VS-CLOSE BY LEAGUE - RUN 1, PRELIMINARY, NOT JUDGED | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Job: prove the table and show the shape. No benchmark flips on this run. Judged run = run 2, after the download.",
         f"Population: LIQ-MAIN + LIQ-EXTRA liquidity alerts, deduped one per game+market+side (first alert). Exchange-close leg: "
         f"alerts from {CLEAN_FROM[:10]}, pregame, not suspect (Oct 28 guard); earlier plays count toward units only.",
         f"Alerts in scope {len(A)}, plays read {len(R)}. Not read: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v), "",
         "BY LEAGUE:"]
    for lg in LEAGUES:
        xs = [r for r in R if r["lg"] == lg]
        if xs:
            L.append(line(lg, xs))
    L += ["", "BY LEAGUE x MARKET (n >= 30):"]
    for lg in LEAGUES:
        for mk in ("total", "moneyline", "spread"):
            xs = [r for r in R if r["lg"] == lg and r["mk"] == mk]
            if len(xs) >= 30:
                L.append(line(f"{lg} {mk}", xs))
    L += ["", "ALL LEAGUES:", line("all", R)]
    C = [r for r in R if r["clean"]]
    L += ["", f"CLEAN WINDOW ONLY ({CLEAN_FROM[:10]} on; halves inside it) - the SHAPE, not judged:"]
    for lg in LEAGUES:
        xs = [r for r in C if r["lg"] == lg]
        if xs:
            L.append(line(lg, xs))
    for lg in LEAGUES:
        for mk in ("total", "moneyline", "spread"):
            xs = [r for r in C if r["lg"] == lg and r["mk"] == mk]
            if len(xs) >= 30:
                L.append(line(f"{lg} {mk}", xs))
    V = [r for r in R if r["rec"] is not None]
    V.sort(key=lambda r: r["t"])
    agree = lambda xs: sum(1 for r in xs if abs(r["rec"] - r["p_ex"]) <= 0.01)
    first = V[:20]
    L += ["", "RUN 2 GATE PREVIEW - reconstructed exchange close (history ticks) vs the monitor's clean close:",
          f"   first 20: {agree(first)} of {len(first)} within 1c (registered gate: >= 18 of 20)"
          + (" -> would PASS" if len(first) == 20 and agree(first) >= 18 else " -> would not pass yet"),
          f"   all: {agree(V)} of {len(V)} within 1c"
          + (f"; median gap {stt.median(abs(r['rec'] - r['p_ex']) for r in V) * 100:.1f}c" if V else ""),
          "   (Kalshi / Novig / ProphetX only; Polymarket global is not in the history, so its pre-fix plays cannot be restored.)"]
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} "
             f"(billable {cl.STATS['billable']}).")
    ex.send("Bets CLOSE-VS-CLOSE run 1 (preliminary, paper)", "\n".join(L))
    print(f"close vs close: scope {len(A)}, read {len(R)}, both closes {sum(1 for r in R if r['p_ex'] is not None)}, "
          f"recon {len(V)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
