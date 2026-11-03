#!/usr/bin/env python3
"""
Paper lanes pre-registered by Muse, Nov 1 2026 (VALUE LAB). Paper only: no live use, no executor input.
Runs in the bets-board workflow every ~10 min and keeps lanes/lanes.json (public: market data and paper results only).

LIQ-ML-STAY: a moneyline liquidity row enters at the LAST snapshot taken >= 60 min before start if, at that snapshot,
  status = still there, confirmed (rule_met), new money >= $100k, board call PLAY or LEAN. Paper bet = that team's ML at
  the monitor's current price (price_source=monitor). Headline: NHL + NBA + NFL; NCAAF/MLB/others observe-only splits.
  Later pulls / final status are recorded as splits only. Bars: readout 50, promote >= +0.08u/play overall AND NHL+NBA
  >= +0.10 AND CLV >= 0; kill at 40 if <= 0.00u/play.
LIQ-PULL-FADE: a row with new money >= $100k and confirmed whose money is detected PULLED while >= 30 min remain before
  start -> paper-bet the OPPOSITE side of the same market at 1 - the pulled side's monitor price at detection
  (price_source=monitor). Pulls detected < 30 min pre-start are logged observe-only. Bars: readout 40; kill at 30 if
  <= 0.00u/play.
LIQ-SOLO (Nov 1, Peter; pre-registered by Muse, VALUE LAB): a moneyline or total row enters at the LAST snapshot taken >= 60 min
  before start if, at that snapshot, status = still there, NOT confirmed (rule_met false: big money on one book only),
  new money >= $100k. Paper bet = that side at the monitor price. Backtest (hypothesis only, hindsight): unconfirmed
  rows that stayed, $100k+, 49-23 +13.2u; unconfirmed ML that stayed 118-52 +15.5u. Spreads excluded. Bars: readout
  at 50 resulted; promotion needs >= +0.08u/play overall AND ML split >= +0.05 AND CLV >= 0; kill at 40 if <= 0.00u/play.
Grading: flat 1.00u risked at the entry price (win pays (1-p)/p), from the liquidity feed's result. Forward from
Mon Nov 2, 2026 00:00 ET; the Oct 22-31 backtest is never part of the record.
"""
import json
import os
from datetime import datetime, timezone

import board_build as bb

START = datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc)   # Mon Nov 2 00:00 ET
F = "lanes/lanes.json"
HEAD = ("NHL", "NBA", "NFL")


def pay(p, res):
    if res == "P":
        return 0.0
    if res == "W" and p and 0 < p < 1:
        return round((1 - p) / p, 4)
    return -1.0 if res == "L" else None


def main():
    now = datetime.now(timezone.utc)
    try:
        L = json.load(open(F))
    except Exception:
        L = {}
    ml, pf, so = L.setdefault("ml_stay", {}), L.setdefault("pull_fade", {}), L.setdefault("solo", {})
    _, rows, _ = bb.build(upcoming=True)
    # results for everything we've logged (rows may have rolled out of the upcoming window)
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    if now >= START:
        for r in rows:
            x = r["x"]
            k = f"{x.get('key')}|{x.get('alerted_utc')}"
            st = bb.t(x.get("start_utc"))
            if not st:
                continue
            mins = (st - now).total_seconds() / 60
            p = x.get("close_price") or x.get("price")
            # LIQ-ML-STAY: keep overwriting the snapshot while >= 60 min out; it freezes on its own after that
            if r["mk"] == "moneyline" and mins >= 60:
                e = ml.get(k) or {}
                if not e.get("frozen"):
                    ok = (r["status"] == "still there" and r["conf"] and r["new"] >= 100_000 and r.get("v1", r["tag"]) in ("PLAY", "LEAN"))   # v1 call: lane registered on it
                    ml[k] = {"game": r["game"], "league": r["league"], "side": r["side"], "book": r["book"],
                             "new_money": round(r["new"]), "status": r["status"], "confirmed": r["conf"], "tag": r["tag"],
                             "start_utc": x.get("start_utc"), "snapshot_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "mins_to_start": round(mins), "entered": ok, "price": p, "price_source": "monitor",
                             "headline": r["league"] in HEAD}
            # LIQ-SOLO: same freeze-at-T-60 mechanics as ML-STAY
            if r["mk"] in ("moneyline", "total") and mins >= 60:
                e = so.get(k) or {}
                if not e.get("frozen"):
                    ok = r["status"] == "still there" and not r["conf"] and r["new"] >= 100_000
                    so[k] = {"game": r["game"], "league": r["league"], "market": r["mk"], "side": r["side"],
                             "book": r["book"], "new_money": round(r["new"]), "status": r["status"],
                             "confirmed": r["conf"], "tag": r["tag"], "start_utc": x.get("start_utc"),
                             "snapshot_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "mins_to_start": round(mins),
                             "entered": ok, "price": p, "price_source": "monitor",
                             "headline": r["league"] in HEAD}   # Muse: NHL+NBA+NFL headline; others observe-only
            # LIQ-PULL-FADE: first time we see a qualifying pull
            if r["new"] >= 100_000 and r["conf"] and x.get("pulled") and k not in pf:
                pu = bb.t(x.get("pulled_utc")) or now
                if pu < START:
                    continue   # forward only: pulls before Nov 2 are never part of the record
                lead = (st - pu).total_seconds() / 60
                pf[k] = {"game": r["game"], "league": r["league"], "market": r["mk"], "pulled_side": r["side"],
                         "book": r["book"], "new_money": round(r["new"]), "pulled_utc": x.get("pulled_utc"),
                         "detected_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "mins_to_start_at_pull": round(lead),
                         "entered": lead >= 30, "price": round(1 - p, 4) if p else None, "price_source": "monitor",
                         "start_utc": x.get("start_utc")}
    for k, e in list(ml.items()) + list(so.items()):
        st = bb.t(e.get("start_utc"))
        if st and (st - now).total_seconds() < 3600:
            e["frozen"] = True
        x = feed.get(k)
        if x and e.get("entered") and x.get("result") and not e.get("result"):
            e["result"] = x["result"]
            e["units"] = pay(e.get("price"), x["result"])
            e["final_status"] = "pulled" if x.get("pulled") else "stayed"
            e["close_price"] = x.get("close_price")
            e["clv"] = round(x["close_price"] - e["price"], 4) if x.get("close_price") and e.get("price") else None
    for k, e in pf.items():
        x = feed.get(k)
        if x and e.get("entered") and x.get("result") and not e.get("result"):
            res = {"W": "L", "L": "W", "P": "P"}.get(x["result"])
            e["result"] = res
            e["units"] = pay(e.get("price"), res)
    os.makedirs("lanes", exist_ok=True)
    with open(F, "w") as f:
        json.dump(L, f, indent=1, sort_keys=True)
    n = lambda d: sum(1 for e in d.values() if e.get("entered"))
    print(f"Lanes: ML-STAY {n(ml)}, PULL-FADE {n(pf)}, SOLO {n(so)} entries")   # counts only


if __name__ == "__main__":
    main()
