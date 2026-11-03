#!/usr/bin/env python3
"""
PAPER RULES TRACKER (Nov 3, 2026; Peter 8:13 AM "build what you need"; Betting Test Queue items 25, 27, 29-33, 50).
FORWARD PAPER ONLY - reads the public alerts.json, places nothing, changes no alert. Every rule below was frozen in the
queue doc before its first tag; a rule's clock starts at its registration time (START), never earlier (no backfill).
Graded 1u flat at the alert's after-fee price (units_flat). "Beat close" is alerts.json's beat_close, which is LINE-based
(item 16 is reconciling it with price CLV) - labelled as such. Readouts are valid only once item 16 shows the prices
were gettable. Private email; the log prints counts only.

Frozen definitions (band = a TOTAL priced -111 to -120 after fee; lead = minutes before start at alert):
 29 SKIP-BAND        SENT alerts, not band  (control: SENT alerts in the band)
 30 UNDERS+RULE      SENT unders, not band
 31 PX+RULE          SENT ProphetX-priced, not band
 32 CFB-UNDERS+RULE  ALL alerts (sent or not), NCAAF unders, not band
 33 GRADE TIERS      SENT alerts. AND tier = price better than -110 AND lead >= 180; ONE = exactly one of the two;
                     NONE = neither. ProphetX variant (price only): A better than -110, B -110 to -120, Z worse than -120
 25 EDGE >= 0        primary SENT ProphetX-priced edge_pct >= 0; secondaries ProphetX edge >= +1, all books edge >= 0;
                     controls edge < 0 on the same populations (from Nov 2 8:24 PM ET, Muse's registration)
 27 12-24H           SENT ProphetX-priced, grade A/B, not late, lead 720-1440 min (approximation of "phase-1 qualifying,
                     12-24h out": the phase-1 market scope is not re-applied - labelled)
 50 HR-EV (live)     SENT or not, Hard Rock-priced, edge_pct >= 2 (bands 2-4 / 4-8 / 8+) - the live analog of SLOW-HR-EV
 60 P1-TOTALS        SENT phase-1 LIVE-qualifying alerts, totals only (control: phase-1 spreads); from Nov 3 11:45 AM ET
 61 EDGE2            any book, SENT or not, edge_pct >= +2 vs Pinnacle's new no-vig fair after fee, per book; from 11:45 AM ET
Nov 3 (item 16): beat close / CLV here are the TRUE close (close_value_pct, beat_true_close), price-based - not the line.
"""
import json
import statistics as stt
from datetime import datetime, timezone

import buckets as bkt
import executor as ex

ET_OFF = 5   # EST (DST ended Nov 1)
T29 = "2026-11-03T05:00:00Z"   # items 29-33 and 50: from Nov 3 00:00 ET (Muse 6:19 AM: start as paper today)
T25 = "2026-11-03T01:24:00Z"   # Nov 2 8:24 PM ET registration
T27 = "2026-11-02T21:30:00Z"   # Nov 2 4:30 PM ET (12-24h split adopted at the Nov 2 review)
T60 = "2026-11-03T16:45:00Z"   # items 60/61: Nov 3 11:45 AM ET (Peter "ok do it"; LIVE paused 11:33)


def tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def rows():
    A = (json.load(open("alerts.json")).get("alerts") or [])
    out = []
    for a in A:
        t = tp(a.get("alert_utc"))
        if not t:
            continue
        paf = a.get("price_after_fee")
        kind, bet = a.get("kind"), str(a.get("bet") or "")
        sc = ("under" if bet.upper().startswith("UNDER") else "over") if kind == "tot" else \
             (("dog" if (a.get("point") or 0) > 0 else "fav") if kind == "spr" else None)
        lead = a.get("minutes_before_start")
        out.append({"a": a, "t": a["alert_utc"], "sent": bool(a.get("sent_to_phone")), "book": a.get("book"),
                    "lg": a.get("sport"), "mk": {"tot": "totals", "spr": "spreads", "ml": "moneyline"}.get(kind),
                    "sc": sc, "paf": paf, "lead": lead, "edge": a.get("edge_pct"), "grade": a.get("grade"),
                    "late": bool(a.get("late")), "res": a.get("result"), "u": a.get("units_flat"),
                    "beat": a.get("beat_true_close"), "tcv": a.get("close_value_pct"), "day": (t.timestamp() - ET_OFF * 3600),   # Nov 3: TRUE close (item 16)
                    "band": kind == "tot" and paf is not None and -120 <= paf <= -111})
    for r in out:
        r["day"] = datetime.fromtimestamp(r["day"], timezone.utc).strftime("%Y-%m-%d")
    return out


def rec(xs):
    g = [x for x in xs if x["res"] in ("W", "L", "P")]
    w = sum(x["res"] == "W" for x in g)
    l_ = sum(x["res"] == "L" for x in g)
    p = sum(x["res"] == "P" for x in g)
    u = sum(x["u"] or 0 for x in g)
    b = [x["beat"] for x in g if x["beat"] is not None]
    tc = [x["tcv"] for x in g if x.get("tcv") is not None]
    return (f"n {len(xs)} (graded {len(g)}) {w}-{l_}" + (f"-{p}" if p else "") + f" {u:+.2f}u"
            + (f" | TRUE close {stt.mean(tc):+.2f}%, beat {sum(map(bool, b))}/{len(b)}" if b and tc else ""))


def main():
    R = rows()
    after = lambda xs, t0: [x for x in xs if x["t"] >= t0]
    S29 = after([x for x in R if x["sent"]], T29)
    px = lambda x: x["book"] == "ProphetX"
    better = lambda x: x["paf"] is not None and x["paf"] > -110
    l3 = lambda x: (x["lead"] or 0) >= 180
    L = [f"PAPER RULES TRACKER - FORWARD PAPER ONLY | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
         "1u flat at the alert after-fee price. Beat close / CLV = TRUE close (close_value_pct, price-based; item 16). Readouts at each rule's",
         "registered count; nothing is judged before then.", ""]
    sec = []

    def lane(num, name, xs, ctl=None):
        L.append(f"{num} {name}: {rec(xs)}")
        if ctl is not None:
            L.append(f"   control: {rec(ctl)}")
        sec.append((f"{num} {name}", xs))
    lane(29, "SKIP-BAND (kept)", [x for x in S29 if not x["band"]], [x for x in S29 if x["band"]])
    lane(30, "UNDERS+RULE", [x for x in S29 if x["sc"] == "under" and not x["band"]])
    lane(31, "PX+RULE", [x for x in S29 if px(x) and not x["band"]])
    lane(32, "CFB-UNDERS+RULE (sent or not)", after([x for x in R if x["lg"] == "NCAAF" and x["sc"] == "under" and not x["band"]], T29))
    L.append("33 GRADE TIERS (sent):")
    for nm, f in (("AND", lambda x: better(x) and l3(x)), ("ONE", lambda x: better(x) != l3(x)), ("NONE", lambda x: not better(x) and not l3(x))):
        L.append(f"   {nm}: {rec([x for x in S29 if f(x)])}")
    L.append("   ProphetX price-only variant:")
    for nm, f in (("A (>-110)", lambda x: better(x)), ("B (-110..-120)", lambda x: x["paf"] is not None and -120 <= x["paf"] <= -110),
                  ("Z (worse)", lambda x: x["paf"] is not None and x["paf"] < -120)):
        L.append(f"     {nm}: {rec([x for x in S29 if px(x) and f(x)])}")
    S25 = after([x for x in R if x["sent"] and x["edge"] is not None], T25)
    L.append("25 EDGE >= 0 SLICE (sent, from Nov 2 8:24 PM ET):")
    for nm, xs in (("PRIMARY ProphetX edge >= 0", [x for x in S25 if px(x) and x["edge"] >= 0]),
                   ("ProphetX edge >= +1", [x for x in S25 if px(x) and x["edge"] >= 1]),
                   ("all books edge >= 0", [x for x in S25 if x["edge"] >= 0]),
                   ("CONTROL ProphetX edge < 0", [x for x in S25 if px(x) and x["edge"] < 0]),
                   ("CONTROL all books edge < 0", [x for x in S25 if x["edge"] < 0])):
        L.append(f"   {nm}: {rec(xs)}")
    if S25:
        L.append(f"   stated edge of the flow: mean {stt.mean(x['edge'] for x in S25):+.2f}%, median {stt.median(x['edge'] for x in S25):+.2f}%")
    lane(27, "12-24H (approx. phase-1 qualifying)", after([x for x in R if x["sent"] and px(x) and x["grade"] in ("A", "B")
                                                         and not x["late"] and 720 <= (x["lead"] or 0) < 1440], T27))
    H = after([x for x in R if x["book"] == "Hard Rock" and x["edge"] is not None and x["edge"] >= 2], T29)
    L.append("50 HR-EV live analog (Hard Rock-priced, edge >= 2%, sent or not):")
    for nm, lo, hi in (("2-4%", 2, 4), ("4-8%", 4, 8), ("8%+", 8, 1e9)):
        L.append(f"   {nm}: {rec([x for x in H if lo <= x['edge'] < hi])}")
    sec.append(("50 HR-EV", H))
    L.append("")
    for title, xs in sec:
        recs = [{"day": x["day"], "clv": x.get("tcv"), "beat": x["beat"], "lg": x["lg"], "mk": x["mk"], "sc": x["sc"],
                 "lead": x["lead"], "late": x["late"], "edge": x["edge"], "am": x["paf"]} for x in xs]
        L += bkt.section(f"{title} (CLV = TRUE close value %, price-based; units above)", recs, "%") + [""]
    # Nov 3 11:45 (Peter "ok do it"): the two rebuild candidates for LIVE, judged on TRUE close, clock from T60
    import agree_rules as ar

    def p1(a):
        ok, why = ar.phase1(a, True)
        why = [w for w in why if w != "no Muse AGREE"]
        return bool(ok or not why) and ar.hr_priced(a) is False and ar.deadband(a) is False   # = sharp_monitor.phase1_label
    F = after([x for x in R if x["sent"] and x["a"].get("pricing_bettable") is not False], T60)
    L += ["", "60 P1-TOTALS (phase-1 LIVE-qualifying SENT alerts, totals only; candidate LIVE rebuild):",
          f"   {rec([x for x in F if x['mk'] == 'totals' and p1(x['a'])])}",
          f"   control, phase-1 spreads: {rec([x for x in F if x['mk'] == 'spreads' and p1(x['a'])])}",
          "61 EDGE2 (any book, SENT or not, stated edge vs Pinnacle's new no-vig fair >= +2% after fee; mispricing, not lag):"]
    E2 = after([x for x in R if x["a"].get("pricing_bettable") is not False and x["edge"] is not None and x["edge"] >= 2], T60)
    for bk in sorted({x["book"] for x in E2}):
        L.append(f"   {bk}: {rec([x for x in E2 if x['book'] == bk])}")
    L.append(f"   all books: {rec(E2)}")
    sec += [("60 P1-TOTALS", [x for x in F if x["mk"] == "totals" and p1(x["a"])]), ("61 EDGE2", E2)]
    ex.send("Bets PAPER RULES TRACKER (forward, items 25/27/29-33/50/60/61; TRUE close)", "\n".join(L))
    print(f"paper rules: {len(R)} alerts read, {len(S29)} sent since Nov 3")   # counts only


if __name__ == "__main__":
    main()
