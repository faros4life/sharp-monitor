#!/usr/bin/env python3
"""
NTFY FILL AUDIT (Nov 2, 2026; Peter 16:17 "do it"; terms registered by Muse 16:19 ET). HYPOTHESIS ONLY - measurement,
reads history, touches no bet; no live change off this audit without Peter's yes.
The bucket report showed the ntfy sharp alerts beat the close 84% - measured at the price IN the alert. This asks how much
was actually gettable. Population: every SENT alert (sent to phone) on NBA / NFL / NCAAF / NHL with history coverage
(cache window starts Oct 12 - labelled, not silently truncated); not-sent alerts ride as a labelled split.
For each alert, at the alert time, +1 min and +5 min, it reads the after-fee price AT THE ALERT LINE on ProphetX, Novig,
Kalshi, Polymarket US and Hard Rock (where history carries it):
  GETTABLE  = some book has the alert line at the alert after-fee price or better (per book shown too)
  CLV       = Pinnacle no-vig close x after-fee decimal - 1, at the alert price and at the best price actually up
  SEEN      = the alerted book's own history shows the alert price or better at the alert time (where we hold that book)
FIT / CHECK by date; LATE (final 30 min) apart. Private email; the log prints counts only.
"""
import json
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import buckets as bkt
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
BOOKS = {"prophetx": "ProphetX", "novig.us": "Novig", "kalshi": "Kalshi", "polymarket.us": "Polymarket US", "hardrockbet": "Hard Rock"}
ALERT_BOOK = {"Hard Rock": "hardrockbet", "ProphetX": "prophetx", "Kalshi": "kalshi", "Novig": "novig.us"}
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
TOL = 0.002   # decimal-price tolerance for "same price"
CACHE_ONLY = (os.environ.get("FILL_CACHE_ONLY") or "") == "1"   # Peter 16:29: run on the data we already hold, no downloads


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("fill audit: ODDSPAPI_KEY not set")
        return
    every = [a for a in (json.load(open("alerts.json")).get("alerts") or []) if a.get("sport") in LEAGUES and cl.tp(a.get("alert_utc"))]
    before = sum(1 for a in every if cl.tp(a["alert_utc"]) < FROM)
    alerts = [a for a in every if cl.tp(a["alert_utc"]) >= FROM]
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    R, miss = [], {"no fixture": 0, "game not finished": 0, "history error": 0, "no close": 0, "alert line on no book": 0,
                   "not in cache yet": 0}
    for a in alerts:
        lg, t0 = a["sport"], cl.tp(a["alert_utc"])
        b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc"), "book": a.get("book")}
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if not start or now - start < hc.FINAL_AFTER:
            miss["game not finished"] += 1
            continue
        if CACHE_ONLY and not all(os.path.exists(hc._path(fid, x)) for x in ["pinnacle"] + list(BOOKS)):
            miss["not in cache yet"] += 1
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(BOOKS), start)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            continue
        c, why = cl.close_for(b, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
        if not c:
            miss["no close"] += 1
            continue
        want = cl.am_to_dec(a.get("price_after_fee") or a.get("price"))
        q = {}   # q[label][slug] = after-fee decimal at the alert line, or None
        for lab, dt in (("t0", 0), ("t1", 1), ("t5", 5)):
            w = min(t0 + timedelta(minutes=dt), start)
            q[lab] = {}
            for slug in BOOKS:
                bk = cl.book_markets(h, slug)
                x = cl.novig_at(b, f, bk, mkmap, w, lg) if bk else None
                q[lab][slug] = el.eff(slug, x[0]) if x else None
        if not any(v for lab in q for v in q[lab].values()):
            miss["alert line on no book"] += 1
            continue
        own = ALERT_BOOK.get(a.get("book"))
        pz = cl.parsed(b)
        sc = None
        if pz and pz[0] == "total":
            sc = pz[1].lower()
        elif pz and pz[0] == "spread" and pz[2] is not None:
            ln = -pz[2] if pz[3] else pz[2]
            sc = "fav" if ln < 0 else "dog" if ln > 0 else None
        r = {"book": a.get("book"), "lg": lg, "kind": a.get("kind"), "sent": bool(a.get("sent_to_phone")), "sc": sc,
             "lead": (start - t0).total_seconds() / 60, "edge": a.get("edge_pct"), "am": cl.dec_to_am(want),
             "line": (-pz[2] if pz[3] else pz[2]) if pz and pz[0] == "spread" and pz[2] is not None else None,
             "day": t0.astimezone(ET).strftime("%Y-%m-%d"), "late": (start - t0) <= timedelta(minutes=30),
             "alert_clv": round(100 * (c["p"] * want - 1), 2),
             "seen": (q["t0"][own] is not None and q["t0"][own] >= want - TOL) if own else None}
        for lab in ("t1", "t5"):
            ups = [v for v in q[lab].values() if v]
            best = max(ups) if ups else None
            r[f"get_{lab}"] = best is not None and best >= want - TOL
            r[f"clv_{lab}"] = round(100 * (c["p"] * best - 1), 2) if best else None
            for slug in BOOKS:
                v = q[lab][slug]
                r[f"{slug}_{lab}"] = None if v is None else (v >= want - TOL)
                r[f"{slug}_clv_{lab}"] = round(100 * (c["p"] * v - 1), 2) if v else None
        R.append(r)

    def cl_(xs, k):
        v = [x[k] for x in xs if x.get(k) is not None]
        if not v:
            return "-"
        return f"{stt.mean(v):+.2f}% beat {sum(1 for y in v if y > 0)}/{len(v)} ({100 * sum(1 for y in v if y > 0) / len(v):.0f}%)"

    def pct(xs, k):
        v = [x[k] for x in xs if x.get(k) is not None]
        return f"{sum(v)}/{len(v)} ({100 * sum(v) / len(v):.0f}%)" if v else "-"

    def row(lab, xs):
        if not xs:
            return [f"  {lab}: n 0"]
        return [f"  {lab}: n {len(xs)} | alerted book SEEN at alert price {pct(xs, 'seen')} | GETTABLE (any book) +1 {pct(xs, 'get_t1')}, "
                f"+5 {pct(xs, 'get_t5')}",
                f"      CLV at alert price {cl_(xs, 'alert_clv')} | at best price up +1 {cl_(xs, 'clv_t1')} | +5 {cl_(xs, 'clv_t5')}"]
    S = [x for x in R if x["sent"]]
    days = sorted({x["day"] for x in S})
    mid = days[(len(days) - 1) // 2] if days else ""
    J = [x for x in S if not x["late"]]
    L = [("PARTIAL - CACHED GAMES ONLY (no downloads; full run follows the cache fill) | " if CACHE_ONLY else "") + f"NTFY FILL AUDIT - HYPOTHESIS ONLY (terms: Muse 16:19 ET) | {now.astimezone(ET):%Y-%m-%d %H:%M} ET | FIT <= {mid} < CHECK",
         f"COVERAGE WINDOW: history cache starts {FROM.date()}; {before} NBA/NFL/NCAAF/NHL alerts before then are NOT covered (stated, not dropped silently).",
         "GETTABLE = the alert line at the alert after-fee price or better on ProphetX / Novig / Kalshi / Polymarket US / Hard Rock (history).",
         "CLV = Pinnacle no-vig close x after-fee decimal - 1. 'Best price up' = best after-fee price at the alert line on those books (line gone = excluded).",
         f"Alerts in window {len(alerts)}, graded {len(R)} (sent {len(S)}). Not graded: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v), "",
         "SENT ALERTS (primary):"]
    L += row("ALL (not LATE)", J) + row("FIT", [x for x in J if x["day"] <= mid]) + row("CHECK", [x for x in J if x["day"] > mid])
    L += row("LATE (final 30 min)", [x for x in S if x["late"]])
    L += ["", "PER BOOK (sent, not LATE): alert line at the alert price or better on that book / CLV at that book's price"]
    for slug, nm in BOOKS.items():
        L.append(f"  {nm}: +1 {pct(J, f'{slug}_t1')}, +5 {pct(J, f'{slug}_t5')} | CLV +1 {cl_(J, f'{slug}_clv_t1')} | +5 {cl_(J, f'{slug}_clv_t5')}")
    L += ["", "BY ALERTED BOOK (sent, not LATE):"]
    for bk in sorted({x["book"] for x in J}):
        L += row(bk, [x for x in J if x["book"] == bk])
    L += ["", "BY LEAGUE x MARKET (sent, not LATE):"]
    for lg in LEAGUES:
        for k, nm in (("tot", "totals"), ("spr", "spreads"), ("ml", "moneyline")):
            xs = [x for x in J if x["lg"] == lg and x["kind"] == k]
            if xs:
                L += row(f"{lg} {nm}", xs)
    L += ["", "NOT SENT (labelled split, not part of the judged population):"] + row("not sent, not LATE", [x for x in R if not x["sent"] and not x["late"]])
    mkn = {"tot": "totals", "spr": "spreads", "ml": "moneyline"}
    L += [""] + bkt.section("SENT alerts at the best price up +1 min (CLV %); still bettable = gettable at +1 / +5",
                            [{"day": x["day"], "clv": x["clv_t1"], "lg": x["lg"], "mk": mkn.get(x["kind"]), "sc": x["sc"],
                              "key": bkt.key_class(x["lg"], mkn.get(x["kind"]), x.get("line")), "live1": x["get_t1"], "live5": x["get_t5"],
                              "lead": x["lead"], "late": x["late"], "edge": x.get("edge"), "am": x.get("am")} for x in S], "%")
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} (billable {cl.STATS['billable']}).")
    ex.send("Bets NTFY FILL AUDIT (HYPOTHESIS)", "\n".join(L))
    print(f"fill audit: in window {len(alerts)}, graded {len(R)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
