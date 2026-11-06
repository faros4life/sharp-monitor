#!/usr/bin/env python3
"""
LANE 3: POST AND WAIT, AT THE FEE-EQUIVALENT PRICE (paper; Peter, Nov 6).

Peter's rule: "use the alert price and if it's not there we post it" ... "post it on novig, so no fee,
so whatever that equal price would be" ... "or post anyplace no fee with the best liquidity".

Every board PLAY so far triggered on a FEE book (Kalshi 29, Polymarket 18 of 47). The price that nets
the same as the alert, on a venue charging us nothing, is the alert's AFTER-FEE decimal. A Kalshi
screen -104 nets -112, so we post -112. That is a WORSE raw price than the screen, i.e. EASIER to
fill: the rule declines to pay a fee, it demands no premium.

Why the board's own grade cannot answer this: it books every play at the alert price as if taken
instantly. This RESTS the order and asks whether the venue's own price ever came to us before tip.

TWO BASES, because one input is missing. Every fee in this repo is a TAKER fee (book_check: "prices
compared AFTER the taker fee"; executor: "Polymarket US taker"), and we hold NO maker schedule for any
venue. So:
  NOVIG ONLY   - the only venue exchange_lag.eff() treats as costing nothing. Conservative, and true
                 today whatever the maker schedules turn out to be.
  ANY VENUE    - the same target, fillable on any of the four, which is only right if posting is
                 actually free where we post. OPTIMISTIC and NOT established - it is the upper bracket,
                 and it is wrong by exactly the maker fees we have not looked up.

The question that decides the idea is ADVERSE SELECTION, not fill rate: a resting bid fills when the
market moves against it. So Pinnacle's no-vig fair for our side AT THE FILL is reported beside its
fair AT THE ALERT. A negative mean change means the better price was bought with worse selection.

Read-only, paper, no orders, NO billable OddsPapi call (fixtures come from the ledger's existing
cache). Private email; the Actions log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import nba_names as nn

ALERTS = os.environ.get("NP_ALERTS", "") or "liquidity/alerts.json"
CALLS = os.environ.get("NP_CALLS", "") or "board/calls.json"
STEP = int(os.environ.get("NP_STEP_MIN", "") or "5")
VENUES = ["novig.us", "prophetx", "kalshi", "polymarket.us"]
NOFEE = [v for v in VENUES if abs(el.eff(v, 1.9091) - 1.9091) < 1e-9]
SLUG = {"kalshi": "kalshi", "polymarket": "polymarket.us", "novig": "novig.us", "prophetx": "prophetx"}


def am(d):
    return round(-100 / (d - 1)) if d < 2 else round(100 * (d - 1))


def first_fill(b, f, mk, mkmap, t0, tip, lg, target):
    """First moment from t0 to tip at which this venue offered target or better on our side."""
    w = t0
    while w <= tip:
        q = cl.novig_at(b, f, mk, mkmap, w, lg)
        if q and q[0] >= target - 1e-9:
            return w, q[0]
        w += timedelta(minutes=STEP)
    return None, None


def main():
    now = datetime.now(timezone.utc)
    alerts = (json.load(open(ALERTS)) or {}).get("alerts") or []
    calls = (json.load(open(CALLS)) or {}).get("calls") or {}
    play = {k for k, v in calls.items() if v.get("call") == "PLAY"}
    pop = [a for a in alerts if f"{a.get('key') or ''}|{a.get('alerted_utc') or ''}" in play]

    st = {"billable": {}}
    try:
        prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"], st["fx_last"] = dict(prev.get("fixtures") or {}), dict(prev.get("fx_last") or {})
        print(f"post test: reusing {len(st['fixtures'])} cached fixtures - no /fixtures purchase")
    except Exception as e:
        print(f"post test: no fixture cache ({type(e).__name__})")
    mkmap = cl.load_markets(st, now)

    R, miss = [], {"no fixture": 0, "no history": 0, "no alert price": 0}
    for a in pop:
        lg, side, line = (a.get("league") or "").upper(), a.get("side"), a.get("line")
        t0, tip = cl.tp(a.get("alerted_utc")), cl.tp(a.get("start_utc"))
        if not t0 or not tip or not a.get("price") or line is None:
            miss["no alert price"] += 1
            continue
        trig = SLUG.get(a.get("book"), a.get("book"))
        target = el.eff(trig, 1 / a["price"])
        b = {"league": lg, "game": a.get("game"), "teams": nn.teams_of(a),
             "bet": f"{'Over' if side == 'OVER' else 'Under'} {float(line):g} (-110)",
             "game_start": a.get("start_utc"), "flip": False}
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            continue
        f = st["fixtures"][fid]
        h = hc.get_hist(fid, ["pinnacle"] + VENUES, cl.tp(f.get("start")) or tip)
        if isinstance(h, dict) and h.get("_error"):
            miss["no history"] += 1
            continue
        pin = cl.book_markets(h, "pinnacle")
        pa, _ = cl.close_for(b, f, pin, mkmap, t0, lg)
        row = {"game": a.get("game"), "side": side, "line": line, "trig": trig,
               "screen": a.get("price_american"), "post_am": am(target), "post_dec": round(target, 4),
               "lead_h": round((tip - t0).total_seconds() / 3600, 1), "res": a.get("result"),
               "pin_alert": (round(pa["p"], 4) if pa else None)}
        for basis, vs in (("nofee", NOFEE), ("any", VENUES)):
            best = None
            for v in vs:
                w, d = first_fill(b, f, cl.book_markets(h, v), mkmap, t0, tip, lg, target)
                if w and (best is None or w < best[0]):
                    best = (w, d, v)
            if best:
                pf, _ = cl.close_for(b, f, pin, mkmap, best[0], lg)
                u = ((best[1] - 1) if row["res"] == "W" else -1.0 if row["res"] == "L" else 0.0) \
                    if row["res"] in ("W", "L", "P") else None
                row[basis] = {"fill": True, "wait_h": round((best[0] - t0).total_seconds() / 3600, 1),
                              "dec": round(best[1], 4), "venue": best[2],
                              "pin_fill": (round(pf["p"], 4) if pf else None),
                              "u": (round(u, 3) if u is not None else None)}
            else:
                row[basis] = {"fill": False}
        R.append(row)

    L = ["LANE 3 - POST AND WAIT AT THE FEE-EQUIVALENT PRICE (paper; no billable OddsPapi call)",
         "",
         "Rule: post at the alert price NET OF THE TRIGGER BOOK'S FEE, on a venue that charges us",
         "nothing. A Kalshi screen -104 nets -112, so we post -112 - a worse raw price, therefore",
         "EASIER to fill. The rule declines the fee; it demands no premium.",
         "",
         f"NO-FEE VENUES per exchange_lag.eff(): {NOFEE or 'none'}.",
         "CAVEAT: every fee in this repo is a TAKER fee and we hold NO maker schedule for any venue.",
         "So the 'any venue' basis below is an UPPER BRACKET, wrong by exactly the maker fees we have",
         "not looked up. The 'no-fee' basis is the one that stands today.",
         "",
         f"population {len(pop)} frozen board PLAYs, measured {len(R)}"
         + (f" | not measured: {', '.join(f'{v} {k}' for k, v in miss.items() if v)}" if any(miss.values()) else ""),
         f"walked each venue's own history every {STEP} min from the alert to tip.", ""]

    for basis, name in (("nofee", f"POSTED ON A NO-FEE VENUE {NOFEE}"), ("any", "POSTED ANYWHERE (upper bracket)")):
        fl = [r for r in R if r[basis]["fill"]]
        gr = [r for r in fl if r[basis].get("u") is not None]
        L.append(f"--- {name} ---")
        L.append(f"  filled before tip: {len(fl)}/{len(R)}" + (f" ({len(fl)/len(R)*100:.0f}%)" if R else ""))
        if gr:
            w = sum(1 for r in gr if r["res"] == "W")
            tot = sum(r[basis]["u"] for r in gr)
            L.append(f"  graded fills: {len(gr)} | {w}-{len(gr)-w} | {tot:+.2f}u | {tot/len(gr):+.3f}/play")
            wt = sorted(r[basis]["wait_h"] for r in fl)
            L.append(f"  wait to fill: median {wt[len(wt)//2]:.1f} h | max {wt[-1]:.1f} h")
            vc = {}
            for r in fl:
                vc[r[basis]["venue"]] = vc.get(r[basis]["venue"], 0) + 1
            L.append(f"  filled on: {', '.join(f'{k} {v}' for k, v in sorted(vc.items(), key=lambda x: -x[1]))}")
        both = [r for r in fl if r["pin_alert"] and r[basis].get("pin_fill")]
        if both:
            d = [r[basis]["pin_fill"] - r["pin_alert"] for r in both]
            bad = sum(1 for x in d if x < 0)
            L.append(f"  ADVERSE SELECTION: n {len(both)} | Pinnacle fair for our side moved "
                     f"{sum(d)/len(d)*100:+.2f} pts from alert to fill | against us {bad}/{len(both)} "
                     f"({bad/len(both)*100:.0f}%)")
        L.append("")

    L.append(f"{'game':24s} {'sd':5s} {'line':>6s} {'trig':13s} {'scr':>5s} {'post':>5s} {'lead':>5s} "
             f"{'fill':>4s} {'wait':>5s} {'venue':11s} {'res':>4s} {'u':>7s}")
    for r in sorted(R, key=lambda r: (not r["nofee"]["fill"], str(r["game"]))):
        n = r["nofee"]
        L.append(f"{str(r['game'])[:24]:24s} {str(r['side'])[:5]:5s} {str(r['line']):>6s} {r['trig'][:13]:13s} "
                 f"{str(r['screen']):>5s} {r['post_am']:>5d} {r['lead_h']:>5.1f} "
                 f"{'yes' if n['fill'] else 'no':>4s} "
                 f"{(format(n['wait_h'], '.1f') if n.get('wait_h') is not None else '-'):>5s} "
                 f"{str(n.get('venue') or '-')[:11]:11s} {str(r['res']):>4s} "
                 f"{(format(n['u'], '+.3f') if n.get('u') is not None else '-'):>7s}")

    body = "\n".join(L)
    nf = sum(1 for r in R if r["nofee"]["fill"])
    print(f"post test: measured {len(R)}, no-fee fills {nf}, any-venue fills {sum(1 for r in R if r['any']['fill'])}")
    try:
        ex.send("Bets LANE 3 - post and wait at the fee-equivalent price (paper)", body)
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
