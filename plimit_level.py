#!/usr/bin/env python3
"""
ITEM 56 - P-LIMIT LEVEL as a weight on sharp alerts (Nov 3, 2026; Peter 10:33 "can we also use the P limit";
spec pinned by Claude 10:38 + 10:39, Muse pins 10:38 / 10:52). PAPER / MEASUREMENT ONLY - reads history, touches no bet.

Population: alerts.json "alerts", NBA / NFL / NCAAF / NHL, kinds spr / tot / ml, graded W/L/P, Polymarket-priced
excluded (pricing_bettable false), inside the history window (from Oct 12). SENT = judged stream; MUTED = a split.
LIMIT: Pinnacle's RAW OddsPapi max-stake limit on the alert's market and side at the last tick at or before alert_utc,
at the alert's own line when Pinnacle has it, else Pinnacle's main line for that market (labelled). No tick within
60 min before the alert = "no limit" (reported, never dropped silently).
HIGH (judged) = limit > the league x market median of FIT SENT alerts (alert day <= Oct 28 ET), frozen and applied to both
halves; LOW = <= that median. Tertiles by FIT-only cut points are descriptive.
GETTABLE (judged price) = best after-fee EXCHANGE price (ProphetX / Novig / Kalshi / Polymarket US) at the alert line
+5 min after the alert; graded at that actual price. No exchange at the line at +5 min = NOT GETTABLE (counted, not
graded). Alert price shown as descriptive only.
JUDGED: HIGH beats LOW = higher average CLV AND higher units in BOTH halves, n >= 50 per half per group; a half where CLV
and units disagree does not pass. Hours-to-start is a mandatory split (limits rise toward tip-off). Standard buckets on
HIGH and on LOW. Private email; the log prints counts only.
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
FIT_END = "2026-10-28"
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
        R.append({"lg": lg, "mk": kind, "sc": sc, "sent": bool(a.get("sent_to_phone")), "day": t0.astimezone(ET).strftime("%Y-%m-%d"),
                  "lead": lead, "late": lead is not None and lead < 30, "am": a.get("price_after_fee"), "edge": a.get("edge_pct"),
                  "limit": limit, "lim_how": how, "gettable": best is not None,
                  "clv_g": round(100 * (c["p"] * best - 1), 2) if best else None, "u_g": units(best) if best else None,
                  "clv_a": round(100 * (c["p"] * want - 1), 2), "u_a": units(want)})
    S = [r for r in R if r["sent"]]
    # FIT-only medians and tertiles per league x market, frozen
    cuts = {}
    for lg in LEAGUES:
        for mk in ("totals", "spreads", "moneyline"):
            v = sorted(r["limit"] for r in S if r["lg"] == lg and r["mk"] == mk and r["limit"] and r["day"] <= FIT_END)
            if len(v) >= 5:
                cuts[(lg, mk)] = (stt.median(v), v[len(v) // 3], v[(2 * len(v)) // 3])
    for r in R:
        cu = cuts.get((r["lg"], r["mk"]))
        r["grp"] = None if not r["limit"] or not cu else ("HIGH" if r["limit"] > cu[0] else "LOW")
        r["ter"] = None if not r["limit"] or not cu else ("T1 low" if r["limit"] <= cu[1] else "T3 high" if r["limit"] > cu[2] else "T2 mid")

    def st_(xs, basis="g"):
        g = [x for x in xs if x[f"clv_{basis}"] is not None]
        if not g:
            return f"n {len(xs)} | graded 0"
        cv = [x[f"clv_{basis}"] for x in g]
        u = sum(x[f"u_{basis}"] for x in g)
        return (f"n {len(xs)} | graded {len(g)} | CLV {stt.mean(cv):+.2f}% beat {sum(v > 0 for v in cv)}/{len(cv)} "
                f"({100 * sum(v > 0 for v in cv) / len(cv):.0f}%) | {u:+.2f}u")

    def mean_u(xs):
        g = [x for x in xs if x["clv_g"] is not None]
        return (stt.mean(x["clv_g"] for x in g) if g else None, sum(x["u_g"] for x in g) if g else None, len(g))
    J = [r for r in S if not r["late"]]
    H1 = [r for r in J if r["day"] <= FIT_END]
    H2 = [r for r in J if r["day"] > FIT_END]
    L = [f"ITEM 56 - P-LIMIT LEVEL ON SENT SHARP ALERTS - PAPER ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Judged at the +5-min best after-fee EXCHANGE price (ProphetX/Novig/Kalshi/PM US). HIGH = Pinnacle raw limit at alert >",
         f"the league x market median of FIT sent alerts (<= {FIT_END}), frozen. FIT = H1 <= {FIT_END} < H2. LATE (final 30 min) apart.",
         f"Alerts in scope {len(A)}, read {len(R)} (sent {len(S)}). Not read: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v),
         f"Sent alerts with no Pinnacle limit within 60 min: {sum(1 for r in S if not r['limit'])} (reported, not graded by group). "
         f"Limit read at the alert's own line {sum(1 for r in S if r['lim_how'] == 'own line')}, main line {sum(1 for r in S if r['lim_how'] == 'main line')}.",
         f"Gettable at +5 min: {sum(r['gettable'] for r in S)}/{len(S)} sent.", "",
         "FROZEN CUTS (FIT median | tertiles), raw OddsPapi dollars:"]
    for (lg, mk), cu in sorted(cuts.items()):
        L.append(f"   {lg} {mk}: median {cu[0]:,.0f} | T1<= {cu[1]:,.0f} < T2 <= {cu[2]:,.0f} < T3")
    L += ["", "JUDGED (sent, not late, gettable price):"]
    verdict = []
    for nm, xs in (("H1", H1), ("H2", H2)):
        hi = mean_u([r for r in xs if r["grp"] == "HIGH"])
        lo = mean_u([r for r in xs if r["grp"] == "LOW"])
        L.append(f"   {nm} HIGH: {st_([r for r in xs if r['grp'] == 'HIGH'])}")
        L.append(f"   {nm} LOW:  {st_([r for r in xs if r['grp'] == 'LOW'])}")
        if hi[2] < 50 or lo[2] < 50:
            verdict.append(f"{nm} not enough yet (HIGH {hi[2]}, LOW {lo[2]} graded; need 50 each)")
        elif hi[0] > lo[0] and hi[1] > lo[1]:
            verdict.append(f"{nm} HIGH wins on CLV and units")
        elif hi[0] < lo[0] and hi[1] < lo[1]:
            verdict.append(f"{nm} LOW wins on CLV and units")
        else:
            verdict.append(f"{nm} split (CLV and units disagree): does not pass")
    L.append("   VERDICT: " + "; ".join(verdict) + (" -> PASSES (HIGH beats LOW both halves)" if all("HIGH wins" in v for v in verdict) else " -> does not pass"))
    L += ["", "Same, at the ALERT price (descriptive only):"]
    for g in ("HIGH", "LOW"):
        L.append(f"   {g}: {st_([r for r in J if r['grp'] == g], 'a')}")
    L += ["", "HOURS TO START (mandatory; limits rise toward tip-off):"]
    for lo_, hi_, nm in ((30, 120, "30m-2h"), (120, 360, "2-6h"), (360, 1440, "6-24h"), (1440, 1e9, "24h+")):
        xs = [r for r in J if r["lead"] is not None and lo_ <= r["lead"] < hi_]
        L.append(f"   {nm}: HIGH {st_([r for r in xs if r['grp'] == 'HIGH'])} || LOW {st_([r for r in xs if r['grp'] == 'LOW'])}")
    L += ["", "TERTILES (descriptive):"] + [f"   {t}: {st_([r for r in J if r['ter'] == t])}" for t in ("T1 low", "T2 mid", "T3 high")]
    L += ["", "BY LEAGUE x MARKET (sent, not late):"]
    for (lg, mk) in sorted(cuts):
        xs = [r for r in J if r["lg"] == lg and r["mk"] == mk]
        L.append(f"   {lg} {mk}: HIGH {st_([r for r in xs if r['grp'] == 'HIGH'])} || LOW {st_([r for r in xs if r['grp'] == 'LOW'])}")
    L += ["", "MUTED (split, not judged):"] + [f"   {g}: {st_([r for r in R if not r['sent'] and not r['late'] and r['grp'] == g])}" for g in ("HIGH", "LOW")]
    L += ["", "LATE (final 30 min, own line):"] + [f"   {g}: {st_([r for r in S if r['late'] and r['grp'] == g])}" for g in ("HIGH", "LOW")]

    def recs(xs):
        return [{"day": r["day"], "clv": r["clv_g"], "lg": r["lg"], "mk": r["mk"], "sc": r["sc"], "lead": r["lead"], "late": r["late"],
                 "edge": r["edge"], "am": r["am"], "pin_limit": r["limit"]} for r in xs if r["clv_g"] is not None]
    for g in ("HIGH", "LOW"):
        L += [""] + bkt.section(f"item 56 {g}-limit SENT alerts at the +5-min gettable price (CLV %)", recs([r for r in S if r["grp"] == g]), "%")
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} (billable {cl.STATS['billable']}).")
    ex.send("Bets ITEM 56 P-LIMIT LEVEL (paper)", "\n".join(L))
    print(f"plimit level: scope {len(A)}, read {len(R)}, sent {len(S)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
