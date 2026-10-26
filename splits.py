#!/usr/bin/env python3
"""
Paper-split registry (Muse + Claude, Oct 25-26, 2026). PAPER RECORD ONLY: reads alerts.json, liquidity/alerts.json and
liquidity/gaps.json, writes splits.json + SPLITS.md. Units only (1u flat after fees, as in the feeds) - no dollar amounts.

Registry discipline (every split): written definition, start date, promotion bar, KILL bar.
  - Kill bar (all splits): 30+ resulted at <= -0.10u/play -> CLOSED (sticky: stays closed once hit).
  - Promotion bar: scan-derived splits >= 30 forward resulted AND >= +0.10u/play;
    a-priori splits (defined before looking at the data) >= 20 resulted AND positive.
  - Meeting a promotion bar only makes a split ELIGIBLE: promotions happen at scheduled reviews, never mid-stream.
Forward only: a split counts plays alerted on/after its start date.
"""
import json
import os
from datetime import datetime, timezone
from statistics import median

FWD = "2026-10-26T04:00:00Z"      # Mon Oct 26, 12:00 AM ET: forward record starts
LIQ_CLEAN = "2026-10-22T14:30:00Z"   # liquidity clean window (Oct 22 ~10:30 AM ET), locked with Muse Oct 25
KILL_N, KILL_UPP = 30, -0.10


def lead(a):
    return a.get("minutes_before_start")


def is_under(a):
    return a.get("kind") == "tot" and (a.get("bet") or "").lower().startswith("under")


def is_over(a):
    return a.get("kind") == "tot" and (a.get("bet") or "").lower().startswith("over")


def in_1224(a):
    return lead(a) is not None and 720 <= lead(a) < 1440


def phase1_core(a):   # Muse AGREE is not in alerts.json; the executor's LEDGER carries it
    sport_ok = (a.get("sport") in ("NCAAF", "NBA") and (a.get("kind") == "spr" or is_under(a))) or \
        (a.get("sport") == "NFL" and is_under(a))   # NFL: unders only (Peter, Oct 26)
    return (a.get("book_key") == "prophetx" and a.get("grade") in ("A", "B") and sport_ok
            and not in_1224(a) and not a.get("late"))


SENT = lambda a: bool(a.get("sent_to_phone"))
NTFY = [
    ("phase1", "Phase-1 live filter (paper view)", "a-priori",
     "Sent alerts priced on ProphetX at alert time, Grade A/B, NCAAF/NBA spreads or unders, NFL unders only, not sent 12-24h before "
     "start, not late. Muse AGREE is applied in the executor ledger, not here.",
     lambda a: SENT(a) and phase1_core(a), "units_flat"),
    ("phase1_control", "Phase-1 control group", "control",
     "Sent ProphetX-priced Grade A/B alerts that phase 1 EXCLUDES (overs, moneylines, NHL, NFL, MLB, or 12-24h before "
     "start). Shows whether the cuts help forward. No promotion bar; kill bar not applied.",
     lambda a: SENT(a) and a.get("book_key") == "prophetx" and a.get("grade") in ("A", "B") and not phase1_core(a),
     "units_flat"),
    ("hr_routed", "Hard Rock-priced, routed", "a-priori",
     "Sent alerts priced on Hard Rock, graded at the alert price (the executor routes them to the best exchange).",
     lambda a: SENT(a) and a.get("book_key") in ("hardrockbet", "hardrockbet_fl"), "units_flat"),
    ("hr_fade", "Fade Hard Rock-priced", "scan",
     "Same alerts as 'Hard Rock-priced, routed' (sent, priced on Hard Rock), graded on the OTHER side at the real "
     "opposite-side price logged when the alert fired (fade_units, 1u after fees). Plays without a logged fade price do "
     "not count. Read next to HR-routed: both directions of every Hard Rock-priced alert.",
     lambda a: SENT(a) and a.get("book_key") in ("hardrockbet", "hardrockbet_fl") and a.get("fade_price_after_fee") is not None,
     "fade_units"),
    ("pmg_routed", "PM-global-priced, routed", "a-priori",
     "Sent alerts priced on global Polymarket, graded at the alert price (routed to the best exchange). Closing "
     "population: global PM left RETAIL_BOOKS on Oct 25.",
     lambda a: SENT(a) and a.get("book_key") == "polymarket", "units_flat"),
    ("unders_only", "Unders only", "scan",
     "Sent alerts on unders (any book, any sport).",
     lambda a: SENT(a) and is_under(a), "units_flat"),
    ("combined", "Combined filter", "scan",
     "Sent alerts NOT priced on Hard Rock, NOT sent 12-24h before start, NOT overs.",
     lambda a: SENT(a) and a.get("book_key") not in ("hardrockbet", "hardrockbet_fl") and not in_1224(a) and not is_over(a),
     "units_flat"),
    ("worse_125", "Priced -125 or worse", "scan",
     "Sent alerts with price after fee at -125 or worse.",
     lambda a: SENT(a) and (a.get("price_after_fee") or 0) <= -125, "units_flat"),
    ("ncaab", "College basketball", "scan",
     "Every NCAAB alert, sent or log-only (the AP Top 25 rule mutes the rest). November Pinnacle numbers are softer "
     "(preseason ratings): early reads carry a signal-quality discount.",
     lambda a: a.get("sport") == "NCAAB", "units_flat"),
    ("fade_1224", "Fade alerts sent 12-24h out", "scan",
     "Sent alerts 12-24h before start, graded on the OTHER side at the real opposite-side price logged when the alert "
     "fired (fade_units). Plays without a logged opposite price do not count.",
     lambda a: SENT(a) and in_1224(a) and a.get("fade_units") is not None, "fade_units"),
]
LIQ = [
    ("liq_totals_not_agree", "Liquidity totals, no sharp agree", "scan",
     "Liquidity main feed, market = total, sharp_agree empty, artifacts excluded, alerted from Oct 22 10:30 AM ET.",
     lambda a: a.get("market") == "total" and not a.get("sharp_agree"), "units_flat"),
    ("liq_sharp_oppose", "Liquidity vs sharp (oppose)", "scan",
     "Liquidity main feed, sharp_oppose not empty (a Pinnacle-move alert on the other side), artifacts excluded, alerted "
     "from Oct 22 10:30 AM ET.",
     lambda a: bool(a.get("sharp_oppose")), "units_flat"),
]


def load(path, key):
    try:
        with open(path) as f:
            return json.load(f).get(key) or []
    except Exception:
        return []


def stats(rows, ufield):
    res = [a for a in rows if a.get("result") in ("W", "L", "P") and a.get(ufield) is not None]
    u = [a[ufield] for a in res]
    cv = [a["close_value_pct"] for a in res if a.get("close_value_pct") is not None]
    return {"plays": len(rows), "resulted": len(res), "W": sum(a["result"] == "W" for a in res),
            "L": sum(a["result"] == "L" for a in res), "P": sum(a["result"] == "P" for a in res),
            "units": round(sum(u), 2), "u_per_play": round(sum(u) / len(u), 3) if u else None,
            "true_close_value_pct": round(sum(cv) / len(cv), 2) if cv else None, "true_close_n": len(cv)}


def judge(sid, kind, s, prev):
    if prev.get("status") == "CLOSED":
        return "CLOSED", prev.get("closed_utc")
    upp, n = s["u_per_play"], s["resulted"]
    if kind != "control" and n >= KILL_N and upp is not None and upp <= KILL_UPP:
        return "CLOSED", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if kind == "scan" and n >= 30 and upp is not None and upp >= 0.10:
        return "ELIGIBLE at next review", None
    if kind == "a-priori" and n >= 20 and upp is not None and upp > 0:
        return "ELIGIBLE at next review", None
    return "OPEN", None


def bars(kind):
    return {"scan": ">= 30 forward resulted AND >= +0.10u/play", "a-priori": ">= 20 resulted AND positive",
            "control": "none (comparison only)"}[kind]


def gaps_report(gaps):
    g = [x for x in gaps if (x.get("first_seen_utc") or x.get("seen_utc") or "") >= FWD[:10]]
    if not g:
        return {"gaps": 0}
    days = sorted({(x.get("first_seen_utc") or x["seen_utc"])[:10] for x in g})
    life = [x.get("lifetime_min") or 0 for x in g]
    edges = sorted(x["edge_pct"] for x in g)
    sizes = [x.get("size_est") or 0 for x in g]
    return {"gaps": len(g), "per_day": round(len(g) / len(days), 1), "edge_pct_median": median(edges),
            "edge_pct_p90": edges[min(len(edges) - 1, int(0.9 * len(edges)))],
            "size_est_median_upper_bound": median(sizes),
            "seen_once_share": round(sum(1 for x in g if (x.get("scans_seen") or 1) == 1) / len(g), 2),
            "lifetime_min_median": median(life), "lived_10min_plus": sum(1 for v in life if v >= 10),
            "with_200_both_legs_upper_bound": sum(1 for v in sizes if v >= 200),
            "scan_sec_median": median([x["scan_sec"] for x in g if x.get("scan_sec") is not None] or [0])}


def main():
    alerts = load("alerts.json", "alerts")
    liq = [a for a in load(os.path.join("liquidity", "alerts.json"), "alerts") if not a.get("artifact")]
    gaps = load(os.path.join("liquidity", "gaps.json"), "gaps")
    try:
        prev = {s["id"]: s for s in json.load(open("splits.json")).get("splits", [])}
    except Exception:
        prev = {}
    out = []
    for sid, name, kind, defn, f, uf in NTFY:
        rows = [a for a in alerts if (a.get("alert_utc") or "") >= FWD and f(a)]
        s = stats(rows, uf)
        st, cl = judge(sid, kind, s, prev.get(sid, {}))
        out.append(dict(id=sid, name=name, type=kind, definition=defn, start_utc=FWD, promotion_bar=bars(kind),
                        kill_bar=("none" if kind == "control" else f">= {KILL_N} resulted at <= {KILL_UPP}u/play -> CLOSED"),
                        status=st, closed_utc=cl, **s))
    for sid, name, kind, defn, f, uf in LIQ:
        rows = [a for a in liq if (a.get("alerted_utc") or "") >= LIQ_CLEAN and f(a)]
        s = stats(rows, uf)
        st, cl = judge(sid, kind, s, prev.get(sid, {}))
        out.append(dict(id=sid, name=name, type=kind, definition=defn, start_utc=LIQ_CLEAN, promotion_bar=bars(kind),
                        kill_bar=f">= {KILL_N} resulted at <= {KILL_UPP}u/play -> CLOSED", status=st, closed_utc=cl, **s))
    # ProphetX decay tripwire: the next 30 ProphetX-priced sent alerts from the forward start, paper + live
    px = sorted([a for a in alerts if (a.get("alert_utc") or "") >= FWD and SENT(a) and a.get("book_key") == "prophetx"
                 and a.get("result") in ("W", "L", "P")], key=lambda a: a["alert_utc"])[:30]
    pu = round(sum(a["units_flat"] for a in px) / len(px), 3) if px else None
    trip = {"rule": "next 30 forward ProphetX-priced plays at or below 0.00u/play = PAUSE LIVE and review early",
            "resulted": len(px), "u_per_play": pu,
            "status": ("PAUSE LIVE" if len(px) >= 30 and pu is not None and pu <= 0 else
                       ("passed" if len(px) >= 30 else "counting"))}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {"note": __doc__.strip(), "splits": out, "prophetx_tripwire": trip, "gaps": gaps_report(gaps)}
    try:   # rewrite only when a number changed, so the 5-minute workflow doesn't commit a new timestamp every run
        old = json.load(open("splits.json"))
        old.pop("updated_utc", None)
        if old == json.loads(json.dumps(body)):
            print("Splits: unchanged")
            return
    except Exception:
        pass
    with open("splits.json", "w") as f:
        json.dump(dict(body, updated_utc=now), f, indent=1)
    md = [f"# Paper splits (updated {now})", "", "Units only, 1u flat after fees. Promotions happen only at scheduled "
          "reviews. Kill bar: 30+ resulted at -0.10u/play or worse closes a split.", "",
          "| Split | Type | Start | W-L-P | Units | u/play | True close % | Status |", "|---|---|---|---|---|---|---|---|"]
    for s in out:
        md.append(f"| {s['name']} | {s['type']} | {s['start_utc'][:10]} | {s['W']}-{s['L']}-{s['P']} | {s['units']:+.2f} | "
                  f"{'' if s['u_per_play'] is None else format(s['u_per_play'], '+.3f')} | "
                  f"{'' if s['true_close_value_pct'] is None else format(s['true_close_value_pct'], '+.2f')} | {s['status']} |")
    md += ["", f"**ProphetX tripwire:** {trip['resulted']}/30 resulted, "
               f"{'-' if pu is None else format(pu, '+.3f')}u/play - {trip['status']}.", "",
           "**Price gaps (measurement only):** " + json.dumps(gaps_report(gaps)), "", "## Definitions", ""]
    md += [f"- **{s['name']}** ({s['type']}; promote {s['promotion_bar']}; kill {s['kill_bar']}): {s['definition']}" for s in out]
    with open("SPLITS.md", "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"Splits: {len(out)} tracked; closed: {sum(s['status'] == 'CLOSED' for s in out)}; "
          f"eligible: {sum(s['status'].startswith('ELIGIBLE') for s in out)}; tripwire: {trip['status']}")   # counts only


if __name__ == "__main__":
    main()
