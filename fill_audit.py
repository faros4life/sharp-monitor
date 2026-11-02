#!/usr/bin/env python3
"""
NTFY FILL AUDIT (Nov 2, 2026; Peter 16:17 "do it"). HYPOTHESIS ONLY - paper, reads history, touches no bet.
The bucket report showed the ntfy sharp alerts beat the close 84% - but measured at the price IN the alert. This asks how
much of that was actually gettable: for every alert on a book we hold history for (Hard Rock, ProphetX, Kalshi, Novig;
NBA / NFL / NCAAF / NHL; games from Oct 12 = history depth), it reads that book's own price for the alerted side and line
at the alert time, +1 min and +5 min, and grades CLV vs Pinnacle's no-vig close (after fees) at the price really there.
  SEEN      = history shows the book at the alert price or better at the alert time (the alert was real)
  STILL UP  = the same line at the alert price or better (after fees) +1 / +5 min later
  CLV @ +N  = Pinnacle close fair x book's after-fee price at +N - 1, whatever the price was (line gone = not gettable)
Uses the shared history cache (games already cached cost nothing). FIT / CHECK by date. Private email; log prints counts.
"""
import json
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
SLUG = {"Hard Rock": "hardrockbet", "ProphetX": "prophetx", "Kalshi": "kalshi", "Novig": "novig.us"}
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
TOL = 0.002   # decimal-price tolerance for "same price"


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("fill audit: ODDSPAPI_KEY not set")
        return
    alerts = [a for a in (json.load(open("alerts.json")).get("alerts") or [])
              if a.get("book") in SLUG and a.get("sport") in LEAGUES and cl.tp(a.get("alert_utc")) and cl.tp(a["alert_utc"]) >= FROM]
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    R, miss = [], {"no fixture": 0, "game not finished": 0, "history error": 0, "no book history": 0, "no close": 0,
                   "price not found at alert": 0}
    for a in alerts:
        lg, t0, slug = a["sport"], cl.tp(a["alert_utc"]), SLUG[a["book"]]
        b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc"), "book": a["book"]}
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if not start or now - start < hc.FINAL_AFTER:
            miss["game not finished"] += 1
            continue
        h = hc.get_hist(fid, ["pinnacle", slug], start)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            continue
        pin, bk = cl.book_markets(h, "pinnacle"), cl.book_markets(h, slug)
        if not bk:
            miss["no book history"] += 1
            continue
        c, why = cl.close_for(b, f, pin, mkmap, start, lg)
        if not c:
            miss["no close"] += 1
            continue
        want = cl.am_to_dec(a.get("price_after_fee") or a.get("price"))
        q = {}
        for lab, dt in (("t0", 0), ("t1", 1), ("t5", 5)):
            w = min(t0 + timedelta(minutes=dt), start)
            x = cl.novig_at(b, f, bk, mkmap, w, lg)
            q[lab] = el.eff(slug, x[0]) if x else None
        if q["t0"] is None:
            miss["price not found at alert"] += 1
            continue
        r = {"book": a["book"], "lg": lg, "kind": a.get("kind"), "day": t0.astimezone(ET).strftime("%Y-%m-%d"),
             "alert_clv": round(100 * (c["p"] * want - 1), 2), "seen": q["t0"] >= want - TOL,
             "late": (start - t0) <= timedelta(minutes=30)}
        for lab in ("t1", "t5"):
            r[f"up_{lab}"] = q[lab] is not None and q[lab] >= want - TOL
            r[f"clv_{lab}"] = round(100 * (c["p"] * q[lab] - 1), 2) if q[lab] else None
        r["clv_t0"] = round(100 * (c["p"] * q["t0"] - 1), 2)
        R.append(r)

    def st_(xs, k):
        v = [x[k] for x in xs if x.get(k) is not None]
        if not v:
            return "-"
        return f"{stt.mean(v):+.2f}% beat {sum(1 for y in v if y > 0)}/{len(v)} ({100 * sum(1 for y in v if y > 0) / len(v):.0f}%)"

    def row(lab, xs):
        if not xs:
            return f"  {lab}: n 0"
        n = len(xs)
        return (f"  {lab}: n {n} | seen at alert {sum(x['seen'] for x in xs)}/{n} | still up +1 {sum(x['up_t1'] for x in xs)}/{n}, "
                f"+5 {sum(x['up_t5'] for x in xs)}/{n}\n      CLV at alert price {st_(xs, 'alert_clv')} | at book price then "
                f"{st_(xs, 'clv_t0')} | +1 min {st_(xs, 'clv_t1')} | +5 min {st_(xs, 'clv_t5')} (line gone = excluded)")
    days = sorted({x["day"] for x in R})
    mid = days[(len(days) - 1) // 2] if days else ""
    J = [x for x in R if not x["late"]]
    L = [f"NTFY FILL AUDIT - HYPOTHESIS ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET | alerts on Hard Rock / ProphetX / Kalshi / Novig, "
         f"NBA NFL NCAAF NHL, from {FROM.date()} | FIT <= {mid} < CHECK",
         "SEEN = book history shows the alert price or better at the alert time. STILL UP = same line, alert price or better (after fees).",
         "CLV = Pinnacle no-vig close x after-fee decimal - 1. LATE (final 30 min) reported separately.",
         f"Alerts in scope {len(alerts)}, graded {len(R)}. Not graded: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v), "",
         row("ALL (not LATE)", J),
         row("FIT", [x for x in J if x["day"] <= mid]),
         row("CHECK", [x for x in J if x["day"] > mid]),
         row("LATE (final 30 min)", [x for x in R if x["late"]]), "", "By book:"]
    for bk in SLUG:
        L.append(row(bk, [x for x in J if x["book"] == bk]))
    L += ["", "By league x market:"]
    for lg in LEAGUES:
        for k, nm in (("tot", "totals"), ("spr", "spreads"), ("ml", "moneyline")):
            xs = [x for x in J if x["lg"] == lg and x["kind"] == k]
            if xs:
                L.append(row(f"{lg} {nm}", xs))
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} (billable {cl.STATS['billable']}).")
    ex.send("Bets NTFY FILL AUDIT (HYPOTHESIS)", "\n".join(L))
    print(f"fill audit: in scope {len(alerts)}, graded {len(R)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
