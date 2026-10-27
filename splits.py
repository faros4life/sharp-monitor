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

Oct 27 (Peter + Muse): liquidity spreads CLOSED by decision (status only: prints still log and grade as before); three
time-block watch splits (liq_overnight, liq_evening, ntfy_evening). All clock times are America/New_York via zoneinfo
(DST-aware). Lead = start_utc minus alert_utc everywhere here; minutes_before_start is not used.
Streams: SENT (pushed), MUTED (logged, never pushed), LIVE (phase-1 subset of SENT), LIQ-MAIN, LIQ-EXTRA.
"Paper" = never bet. ALL PLAYS = every resulted play in a stream; GRADED ERA = Oct 20+ only.
"""
import json
import os
from datetime import datetime, timezone
from statistics import median
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

FWD = "2026-10-26T04:00:00Z"      # Mon Oct 26, 12:00 AM ET: forward record starts
LIQ_CLEAN = "2026-10-22T14:30:00Z"   # liquidity clean window (Oct 22 ~10:30 AM ET), locked with Muse Oct 25
KILL_N, KILL_UPP = 30, -0.10


def _t(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None


def lead(a):
    """Minutes from the alert to the listed start: start_utc minus alert_utc (Oct 27: never minutes_before_start)."""
    t, st = _t(a.get("alert_utc")), _t(a.get("start_utc"))
    return (st - t).total_seconds() / 60 if t and st else None


def et_hour(a, *fields):
    """Hour of day in America/New_York (DST-aware) of the first present time field, or None if untimeable."""
    for f in fields:
        t = _t(a.get(f)) if a.get(f) else None
        if t is not None:
            return t.astimezone(ET).hour
    return None


HR_BOOKS = ("hardrockbet", "hardrockbet_fl")
LIQ_T = ("alerted_utc", "first_seen_utc")    # liquidity alert time: alerted_utc, fallback first_seen_utc


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
    ("tier2_core", "Tier 2 core (paper)", "tier",
     "Paper record only, no money and no size. SENT alerts passing the phase-1 filter (ProphetX-priced, NCAAF/NBA spreads "
     "+ unders, NFL unders, not 12-24h, not late), after-fee price -130 or better, monitor grade B, and market = NCAAF/NBA "
     "spread or NBA under. Feed-side core of Muse's Tier 2 (Muse adds Muse grade 80+, depth at the alert number and a "
     "second-signal overlap). Forward from Oct 27.",
     lambda a: tier2_core(a), "units_flat"),
    ("ntfy_evening", "Evening sends, ex-Hard Rock", "scan",
     "SENT alerts whose pricing book is not Hard Rock, sent 8:00 PM-11:59 PM ET (alert_utc, DST-aware). Watch split, "
     "not a cut: overlaps the 12-24h lead band heavily. Historical read (Muse, ex-HR): -0.22/play, n=20.",
     lambda a: SENT(a) and a.get("book_key") not in HR_BOOKS and et_hour(a, "alert_utc") in range(20, 24), "units_flat"),
    ("muted_midday", "Muted midday (11 AM-2 PM ET)", "scan",
     "MUTED alerts only (sent_to_phone false), alerted 11:00 AM-1:59 PM ET (alert_utc, DST-aware), all books, all markets. "
     "Forward watch, NOT an unmute: if it holds >= +0.10/play at 30 forward resulted, unmuting midday non-Top 25 alerts "
     "becomes a review question for Peter. Historical read (Muse, ALL PLAYS): 24-8, +12.60u, +0.39/play, n=32, "
     "concentrated (ProphetX-priced 16-1, +12.67u; +10.90u from the week of Oct 12); graded era +1.70u on 13.",
     lambda a: not SENT(a) and et_hour(a, "alert_utc") in range(11, 14), "units_flat"),
]
TIER2_START = "2026-10-27T04:00:00Z"   # Tue Oct 27, 12:00 AM ET: tier2_core registered


def tier2_core(a):
    """Feed-side core of Tier 2 (Peter + Muse, Oct 27): phase-1 paper filter (SENT, ProphetX-priced, not 12-24h, not
    late, NCAAF/NBA spreads + unders, NFL unders) + after-fee price no worse than -130 + monitor grade B + market NCAAF/NBA
    spread or NBA under. Muse's full Tier 2 adds Muse grade 80+, depth at the alert number and a second signal."""
    paf = a.get("price_after_fee")
    mk = (a.get("sport") in ("NCAAF", "NBA") and a.get("kind") == "spr") or (a.get("sport") == "NBA" and is_under(a))
    return SENT(a) and phase1_core(a) and a.get("grade") == "B" and mk and paf is not None and paf >= -130


TIER = {"tier2_core": {"start": TIER2_START, "open": (30, 0.70, 0.30), "dies": (20, 0.55)}}   # Peter's target bars


def liq_total_side(a):
    """Over/under for a liquidity total print, from side_label ("Over 6.5 ...", "NOT Over 237.5 points" = under)."""
    import re
    lab = a.get("side_label") or ""
    o = "over" if re.search(r"\bover\b", lab, re.I) else "under" if re.search(r"\bunder\b", lab, re.I) else None
    if o and lab.upper().startswith("NOT "):
        o = "under" if o == "over" else "over"
    return o


def lead_liq(a):
    t, st = _t(a.get("alerted_utc") or a.get("first_seen_utc")), _t(a.get("start_utc"))
    return (st - t).total_seconds() / 60 if t and st else None


def liq_nba_tot(a):
    return a.get("league") == "NBA" and a.get("market") == "total"


BREAKDOWN = {"muted_midday"}   # splits reported with by-book and by-market cuts every run


def market_of(a):
    k = a.get("kind")
    return {"spr": "spread", "ml": "moneyline", "rl": "run/puck line"}.get(k) or (
        "total over" if is_over(a) else "total under" if is_under(a) else (k or "?"))


def breakdown(rows, uf, key):
    groups = {}
    for a in rows:
        groups.setdefault(key(a), []).append(a)
    out = {g: stats(r, uf) for g, r in groups.items()}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["units"]))
TIMED = {"ntfy_evening": ("alert_utc",), "muted_midday": ("alert_utc",), "liq_overnight": LIQ_T, "liq_evening": LIQ_T}   # time splits -> time fields
FORCED_CLOSED = {   # closed by decision at a review (sticky), not by the kill bar; the prints keep logging and grading
    "liq_spreads": ("2026-10-27T10:00:00Z", "Closed by Peter, Oct 27, on Muse's complete-log read: 191 resulted, "
                    "-32.15u (-0.17/play), negative in every time block and every lead window."),
}
LIQ = [
    ("liq_totals_not_agree", "Liquidity totals, no sharp agree", "scan",
     "Liquidity main feed, market = total, sharp_agree empty, artifacts excluded, alerted from Oct 22 10:30 AM ET.",
     lambda a: a.get("market") == "total" and not a.get("sharp_agree"), "units_flat"),
    ("liq_sharp_oppose", "Liquidity vs sharp (oppose)", "scan",
     "Liquidity main feed, sharp_oppose not empty (a Pinnacle-move alert on the other side), artifacts excluded, alerted "
     "from Oct 22 10:30 AM ET.",
     lambda a: bool(a.get("sharp_oppose")), "units_flat"),
    ("liq_spreads", "Liquidity spreads", "scan",
     "Liquidity main feed, market = spread, artifacts excluded, alerted from Oct 22 10:30 AM ET. CLOSED as a promotion "
     "candidate (status only: spread prints still appear in the feed and log and grade exactly as before).",
     lambda a: a.get("market") == "spread", "units_flat"),
    ("liq_overnight", "Liquidity overnight (12-5 AM ET)", "scan",
     "LIQ-MAIN prints alerted 12:00-4:59 AM ET (alerted_utc, fallback first_seen_utc; DST-aware), artifacts excluded. "
     "Historical read (Muse): +9.11u, +0.14/play, n=65 - the only positive liquidity time block.",
     lambda a: et_hour(a, *LIQ_T) in range(0, 5), "units_flat"),
    ("liq_evening", "Liquidity evening (5-8 PM ET)", "scan",
     "LIQ-MAIN prints alerted 5:00-7:59 PM ET (alerted_utc, fallback first_seen_utc; DST-aware), artifacts excluded. "
     "Negative watch: historical read (Muse) -20.99u, -0.17/play, n=125; if it holds forward it becomes a skip window.",
     lambda a: et_hour(a, *LIQ_T) in range(17, 20), "units_flat"),
    ("liq_nba_totals", "NBA liquidity totals (lane)", "scan",
     "LIQ-MAIN, league NBA, market total, artifacts excluded, alerted from Wed Oct 28 12:00 AM ET. Registered Oct 27 "
     "(Peter + Muse, VALUE LAB #4): the only liquidity cell beyond luck. Peter's decision bar: 25 forward resulted at "
     ">= +0.10u/play AND CLV+ >= 55% -> eligible for live (unders first, best after-fee price across ProphetX/Kalshi/PM US).",
     liq_nba_tot, "units_flat"),
    ("liq_nba_totals_under", "NBA liquidity totals - unders", "scan",
     "liq_nba_totals, under side only (side_label). The side Peter would take live first.",
     lambda a: liq_nba_tot(a) and liq_total_side(a) == "under", "units_flat"),
    ("liq_nba_totals_quiet", "NBA liquidity totals - no sharp tag", "scan",
     "liq_nba_totals with sharp_agree AND sharp_oppose both empty (history: 21-6, +0.52/play, CLV+ 78%). Lens on the lane.",
     lambda a: liq_nba_tot(a) and not a.get("sharp_agree") and not a.get("sharp_oppose"), "units_flat"),
    ("liq_nba_totals_4to12", "NBA liquidity totals - lead 4-12h", "scan",
     "liq_nba_totals with lead (start_utc minus alerted_utc) 4h to under 12h (history: 22-10, +0.35/play). Lens on the lane.",
     lambda a: liq_nba_tot(a) and lead_liq(a) is not None and 240 <= lead_liq(a) < 720, "units_flat"),
    ("liq_nba_totals_small", "NBA liquidity totals - $25-50k prints", "scan",
     "liq_nba_totals with new_money under $50,000 (history: +0.28/play). Lens on the lane.",
     lambda a: liq_nba_tot(a) and (a.get("new_money") or 0) < 50000, "units_flat"),
    ("liq_nba_totals_evac", "NBA liquidity totals - evacuation", "scan",
     "liq_nba_totals where the trigger book's new_other_side < 0 (money left the other side). Registered by Muse Oct 27.",
     lambda a: liq_nba_tot(a) and ((a.get("depth_by_book") or {}).get(a.get("book")) or {}).get("new_other_side", 0) < 0,
     "units_flat"),
    ("liq_nba_price_band", "NBA liquidity, price -129..-105", "scan",
     "LIQ-MAIN NBA, any market, price_american -129 to -105 (history: 50-29, +0.20/play). Registered Oct 27.",
     lambda a: a.get("league") == "NBA" and -129 <= (a.get("price_american") or 0) <= -105, "units_flat"),
]
LIQ_START = {"liq_overnight": FWD, "liq_evening": FWD, **{k: "2026-10-28T04:00:00Z" for k in ("liq_nba_totals", "liq_nba_totals_under", "liq_nba_totals_quiet", "liq_nba_totals_4to12", "liq_nba_totals_small", "liq_nba_totals_evac", "liq_nba_price_band")}}   # time splits start at the Oct 26 registry start


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
    if kind == "tier":   # Peter's target bars (Oct 27): sizing talk opens only on proof, label dies below it (sticky)
        if prev.get("status") == "CLOSED":
            return "CLOSED", prev.get("closed_utc")
        b = TIER[sid]
        wl = s["W"] + s["L"]
        wr = s["W"] / wl if wl else None
        if wl >= b["dies"][0] and wr is not None and wr <= b["dies"][1]:
            return "CLOSED", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        n, w, u = b["open"]
        if s["resulted"] >= n and wr is not None and wr >= w and (s["u_per_play"] or 0) >= u:
            return "SIZING DISCUSSION ELIGIBLE at next review", None
        return "OPEN (record only, no size)", None
    if sid in FORCED_CLOSED:
        return "CLOSED", FORCED_CLOSED[sid][0]
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
            "control": "none (comparison only)",
            "tier": "sizing discussion opens only at >= 30 forward resulted AND >= 70% wins AND >= +0.30u/play, at a "
                    "scheduled review; below that, record only"}[kind]


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
    untimed = {}
    for stream, src, specs in (("SENT/MUTED", alerts, NTFY), ("LIQ-MAIN", liq, LIQ)):
        for sid, name, kind, defn, f, uf in specs:
            start = (TIER[sid]["start"] if sid in TIER else FWD) if stream != "LIQ-MAIN" else LIQ_START.get(sid, LIQ_CLEAN)
            tf = TIMED.get(sid)
            pool = src
            if tf:   # time splits: entries with no usable time stay in the stream's record, out of this split - counted
                ut = [a for a in src if et_hour(a, *tf) is None]
                untimed[sid] = len(ut)
                pool = [a for a in src if et_hour(a, *tf) is not None]
            tfields = tf or (("alerted_utc",) if stream == "LIQ-MAIN" else ("alert_utc",))

            def at(a, tfields=tfields):   # the entry's alert time (first present field), "" if none
                return next((a[x] for x in tfields if a.get(x)), "")
            rows = [a for a in pool if at(a) >= start and f(a)]
            s = stats(rows, uf)
            st, cl = judge(sid, kind, s, prev.get(sid, {}))
            row = dict(id=sid, name=name, type=kind, stream=(stream if stream == "LIQ-MAIN" else ("SENT+MUTED" if sid == "ncaab" else "SENT")), definition=defn,
                       start_utc=start, promotion_bar=bars(kind),
                       kill_bar=("none" if kind == "control" else "label dies at <= 55% wins on 20+ forward W/L (sticky)"
                                 if kind == "tier" else f">= {KILL_N} resulted at <= {KILL_UPP}u/play -> CLOSED"),
                       status=st, closed_utc=cl, **s)
            if sid in FORCED_CLOSED:
                row["closed_note"] = FORCED_CLOSED[sid][1]
            if tf or kind == "tier":   # all-history reference (ALL PLAYS in the feed, not forward)
                row["all_history"] = stats([a for a in pool if f(a)], uf)
            if sid in BREAKDOWN:
                allr = [a for a in pool if f(a)]
                row["by_book"] = {"forward": breakdown(rows, uf, lambda a: a.get("book_key") or "?"),
                                  "all_history": breakdown(allr, uf, lambda a: a.get("book_key") or "?")}
                row["by_market"] = {"forward": breakdown(rows, uf, market_of),
                                    "all_history": breakdown(allr, uf, market_of)}
            out.append(row)
    # ProphetX decay tripwire: the next 30 ProphetX-priced sent alerts from the forward start, paper + live
    px = sorted([a for a in alerts if (a.get("alert_utc") or "") >= FWD and SENT(a) and a.get("book_key") == "prophetx"
                 and a.get("result") in ("W", "L", "P")], key=lambda a: a["alert_utc"])[:30]
    pu = round(sum(a["units_flat"] for a in px) / len(px), 3) if px else None
    trip = {"rule": "next 30 forward ProphetX-priced plays at or below 0.00u/play = PAUSE LIVE and review early",
            "resulted": len(px), "u_per_play": pu,
            "status": ("PAUSE LIVE" if len(px) >= 30 and pu is not None and pu <= 0 else
                       ("passed" if len(px) >= 30 else "counting"))}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {"note": __doc__.strip(), "splits": out, "prophetx_tripwire": trip, "gaps": gaps_report(gaps),
            "untimed": untimed,
            "resulted_rule": "resulted = result W, L or P with a unit value (pushes count as 0u); liquidity artifacts excluded; "
                             "pending and ungraded plays do not count"}
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
                  f"{'' if s['true_close_value_pct'] is None else format(s['true_close_value_pct'], '+.2f')} | {s['status']}"
                  f"{' (by decision, ' + s['closed_utc'][:10] + ')' if s['id'] in FORCED_CLOSED else ''} |")
    hist = [s for s in out if s.get("all_history")]
    if hist:
        md += ["", "**All-history reference (every resulted play in the feed, not forward; read only):** "
               + "; ".join(f"{s['name']} {s['all_history']['W']}-{s['all_history']['L']}-{s['all_history']['P']}, "
                           f"{s['all_history']['units']:+.2f}u ({'-' if s['all_history']['u_per_play'] is None else format(s['all_history']['u_per_play'], '+.3f')}/play)"
                           for s in hist)]
    def cell(st):
        return (f"{st['W']}-{st['L']}-{st['P']}, {st['units']:+.2f}u"
                + ("" if st["u_per_play"] is None else f" ({st['u_per_play']:+.3f}/play)") + f", n={st['resulted']}")
    for s in out:
        if s["id"] in BREAKDOWN:
            md += ["", f"**{s['name']}: breakdowns** (resulted plays only)", "",
                   "| Cut | Group | Forward | All history |", "|---|---|---|---|"]
            for cut, lab in (("by_book", "Book"), ("by_market", "Market")):
                f_, h_ = s[cut]["forward"], s[cut]["all_history"]
                for g in list(h_) + [g for g in f_ if g not in h_]:
                    if (h_.get(g) or {}).get("resulted") or (f_.get(g) or {}).get("resulted"):
                        md.append(f"| {lab} | {g} | {cell(f_[g]) if g in f_ and f_[g]['resulted'] else '-'} | "
                                  f"{cell(h_[g]) if g in h_ and h_[g]['resulted'] else '-'} |")
    md += ["", "**Closed by decision:** " + " ".join(f"{s['name']}: {s['closed_note']}" for s in out if s.get("closed_note"))]
    md += ["", f"**ProphetX tripwire:** {trip['resulted']}/30 resulted, "
               f"{'-' if pu is None else format(pu, '+.3f')}u/play - {trip['status']}.", "",
           "**Price gaps (measurement only):** " + json.dumps(gaps_report(gaps)), "",
           "**Counting rules:** resulted = W, L or P with a unit value (pushes count, at 0u); liquidity artifacts excluded; "
           "pending/ungraded plays don't count. Times are America/New_York (DST-aware). Lead = start minus alert time. "
           "Streams: SENT (pushed), MUTED (logged, never pushed), LIVE (phase-1 subset of SENT), LIQ-MAIN, LIQ-EXTRA; "
           "paper = never bet. ALL PLAYS = every resulted play in a stream; GRADED ERA = Oct 20+ only.", "",
           "**Untimed entries** (stay in their stream's record, left out of time splits): "
           + (", ".join(f"{k} {v}" for k, v in untimed.items()) or "none") + ".", "", "## Definitions", ""]
    md += [f"- **{s['name']}** ({s['type']}; promote {s['promotion_bar']}; kill {s['kill_bar']}): {s['definition']}" for s in out]
    with open("SPLITS.md", "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"Splits: {len(out)} tracked; closed: {sum(s['status'] == 'CLOSED' for s in out)}; "
          f"eligible: {sum(s['status'].startswith('ELIGIBLE') for s in out)}; tripwire: {trip['status']}")   # counts only


if __name__ == "__main__":
    main()
