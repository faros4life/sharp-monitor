#!/usr/bin/env python3
"""
2X BACKTEST (Nov 2, 2026; Muse approved in the PLIMIT acceptance, clarified 10:36 ET). Labelled HYPOTHESIS, not evidence:
the forward BOARD-2X grade from ship day stays the test of record.

Rows: the liquidity monitor's board rows (liquidity/alerts.json), NBA / NFL / NHL / NCAAF, alerted Oct 22 - Nov 1 (ET).
Liquidity side: OUR monitor's own depth_by_book on the row (all levels where recorded, else the best level).
Limit: Pinnacle's limit for the row's market and side at the row's alert time, from OddsPapi's free history (the row's
own line when Pinnacle hung it, else Pinnacle's main line for that side, flagged MAIN). Both scales are graded:
RAW (OddsPapi dollars) and OJ (x4/3, OddsJam's scale, per the Nov 2 identity check), until Muse rules.

2X gates (Peter's rule as registered): bet-side exchange liquidity (Novig + ProphetX + Kalshi) >= 2x the limit; at least
2 of Novig / ProphetX / Kalshi at >= $5k each on that side; >= $25k total. (3x in playoffs: none in this window.)
Graded on the rows' own result / flat units / CLV (the monitor's numbers). Private email; the log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LO, HI = os.environ.get("BT_FROM", "2026-10-22"), os.environ.get("BT_TO", "2026-11-01")
EXCH = ("novig", "prophetx", "kalshi")
SCALE = {"RAW": 1.0, "OJ": 4 / 3}


def depth(r, b):
    d = (r.get("depth_by_book") or {}).get(b) or {}
    v = d.get("this_side_all_levels") if d.get("this_side_all_levels") is not None else d.get("this_side")
    return float(v or 0)


def rows():
    a = json.load(open("liquidity/alerts.json"))
    a = a if isinstance(a, list) else a.get("alerts") or []
    out = []
    for r in a:
        t = tb.tparse(r.get("alerted_utc"))
        if not t or r.get("league") not in cl.SPORT or r.get("market") not in ("moneyline", "spread", "total"):
            continue
        d = t.astimezone(ET).strftime("%Y-%m-%d")
        if LO <= d <= HI:
            out.append(r)
    return out


def limit_at(r, f, pm, mkmap, when):
    """(Pinnacle limit for the row's side at that time, 'OWN'|'MAIN', price) or (None, why, None)."""
    lg, mk, side, line = r["league"], r["market"], r.get("side"), r.get("line")
    sid = cl.SPORT[lg]
    if mk == "moneyline":
        t = cl.which_team(f, str(side))
        if not t:
            return None, "team not matched", None
        mid = cl.ML_MARKET[sid]
        oid = {v: k for k, v in (mkmap.get(mid) or [0, 0, 0, {}])[3].items()}.get(t)
        tw = cl.two_way(pm, mid, when)
        return (tw[oid][2], "OWN", tw[oid][0]) if oid in tw else (None, "no Pinnacle moneyline tick", None)
    typ = "spreads" if mk == "spread" else "totals"
    if typ == "totals":
        name, want = ("Over" if str(side).upper() == "OVER" else "Under"), float(line)
    else:
        t = cl.which_team(f, str(side))
        if not t or line is None:
            return None, "team/line not matched", None
        name, want = t, (float(line) if t == "1" else -float(line))   # stated as team 1's handicap
    best, own = None, None
    for mid, (s, ty, hcap, outs) in mkmap.items():
        if s != sid or ty != typ or mid not in pm:
            continue
        oid = {v: k for k, v in outs.items()}.get(name)
        tw = cl.two_way(pm, mid, when)
        if oid not in tw:
            continue
        lim = tw[oid][2]
        if abs(hcap - want) < 1e-9:
            own = (lim, "OWN", tw[oid][0])
        if best is None or lim > best[0]:
            best = (lim, "MAIN", tw[oid][0])
    return own or best or (None, "no Pinnacle tick at that time", None)


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("2X backtest: ODDSPAPI_KEY not set")
        return
    st = {"bets": {}, "billable": {}}
    rs = rows()
    mkmap = cl.load_markets(st, now)
    # fixtures for the window, one call per league
    for lg in sorted({r["league"] for r in rs}):
        st.setdefault("fx_last", {}).pop(lg, None)
        lo = datetime.fromisoformat(LO).replace(tzinfo=ET) - timedelta(days=1)
        hi = datetime.fromisoformat(HI).replace(tzinfo=ET) + timedelta(days=3)
        cl.refresh_fixtures(st, now, lg, lo, hi)
    hist, res, why = {}, [], {}
    for r in rs:
        teams = r.get("teams") or []
        b = {"league": r["league"], "game": r.get("game"), "teams": [{"name": x} for x in teams], "game_start": r.get("start_utc")}
        fid = cl.find_fixture(st, b)
        if not fid:
            why["no OddsPapi fixture matched"] = why.get("no OddsPapi fixture matched", 0) + 1
            continue
        if fid not in hist:
            hist[fid] = hc.get_hist(fid, ["pinnacle"], tb.tparse(r.get("start_utc")))   # shared history cache
        h = hist[fid]
        if isinstance(h, dict) and h.get("_error"):
            why[f"history HTTP {h['_error']}"] = why.get(f"history HTTP {h['_error']}", 0) + 1
            continue
        pm = cl.book_markets(h, "pinnacle")
        when = tb.tparse(r.get("alerted_utc"))
        lim, how, pin_price = limit_at(r, st["fixtures"][fid], pm, mkmap, when)
        if lim is None:
            why[how] = why.get(how, 0) + 1
            continue
        dep = {x: depth(r, x) for x in EXCH}
        tot = sum(dep.values())
        two5k = sum(1 for v in dep.values() if v >= 5000) >= 2
        rec = {"league": r["league"], "market": r["market"], "game": r.get("game"), "side": r.get("side_label"),
               "alerted": r.get("alerted_utc"), "limit_raw": lim, "how": how, "liq": round(tot), "two5k": two5k,
               "result": r.get("result"), "units": r.get("units_flat"), "clv": r.get("clv_cents"), "pulled": bool(r.get("pulled")),
               "confirmed": bool(r.get("rule_met")), "book": r.get("book"), "price": tb.num(r.get("price"))}
        for sc, k in SCALE.items():
            rec["pass_" + sc] = bool(tot >= 2 * lim * k and two5k and tot >= 25000)
        res.append(rec)

    def line(xs, label):
        g = [x for x in xs if x["result"] in ("W", "L", "P")]
        w, l_, p = (sum(1 for x in g if x["result"] == c) for c in ("W", "L", "P"))
        u = sum(float(x["units"] or 0) for x in g)
        c = [float(x["clv"]) for x in xs if x["clv"] is not None]
        return (f"  {label}: rows {len(xs)}, graded {len(g)} ({w}-{l_}-{p}), flat units {u:+.2f}"
                + (f" ({u / len(g):+.3f}/row)" if g else "") + (f", avg CLV {sum(c) / len(c):+.2f}c on {len(c)}" if c else ""))

    L = [f"2X BACKTEST - HYPOTHESIS, not evidence (board rows {LO} to {HI} ET; NBA/NFL/NHL/NCAAF)",
         "Liquidity = our monitor's depth on the bet side (Novig + ProphetX + Kalshi). Limit = Pinnacle's limit for that side at the",
         "row's alert time (OddsPapi history; own line when hung, else Pinnacle's main line for the side, flagged MAIN).",
         "Gates: liquidity >= 2x limit; 2 of Novig/ProphetX/Kalshi >= $5k; >= $25k total. Graded on the rows' own result/units/CLV.", "",
         f"Rows in window: {len(rs)}; with a Pinnacle limit: {len(res)} (own line {sum(1 for x in res if x['how'] == 'OWN')}, "
         f"main line {sum(1 for x in res if x['how'] == 'MAIN')}); not matched: " + ", ".join(f"{v} x {k}" for k, v in why.items())]
    for sc in SCALE:
        p = [x for x in res if x["pass_" + sc]]
        q = [x for x in res if not x["pass_" + sc]]
        L += ["", f"SCALE {sc} ({'OddsPapi dollars' if sc == 'RAW' else 'x4/3 = OddsJam dollars'}):", line(p, "2X PASS"), line(q, "not 2X")]
        for lg in sorted({x["league"] for x in res}):
            L.append(line([x for x in p if x["league"] == lg], f"  2X PASS {lg}"))
        for mk in ("moneyline", "spread", "total"):
            L.append(line([x for x in p if x["market"] == mk], f"  2X PASS {mk}"))
        L.append(line([x for x in p if x["confirmed"] and not x["pulled"]], "  2X PASS, confirmed and not pulled"))
    # Nov 2 (Peter: "adjust per sport ... back test to see what works"): ratio bands per sport, fit half vs check half
    MID = os.environ.get("BT_SPLIT", "2026-10-27")
    BANDS = (2, 3, 5, 10, 20, 50)
    L += ["", f"PER-SPORT RATIO BANDS (ratio = bet-side exchange money / P limit on OddsJam scale; gates 2 of 3 >= $5k and >= $25k kept).",
          f"FIT half = alerts through {MID} ET; CHECK half = after. A cutoff only counts if it holds in CHECK."]
    for x in res:
        x["ratio"] = x["liq"] / (x["limit_raw"] * 4 / 3) if x["limit_raw"] else 0
        x["half"] = "FIT" if (tb.tparse(x["alerted"]).astimezone(ET).strftime("%Y-%m-%d") <= MID) else "CHECK"
    for lg in sorted({x["league"] for x in res}):
        rs_ = sorted(x["ratio"] for x in res if x["league"] == lg)
        if not rs_:
            continue
        q = lambda p: rs_[min(len(rs_) - 1, int(p * len(rs_)))]
        L.append(f"  {lg}: rows {len(rs_)}, ratio median {q(0.5):.1f}x, top 25% >= {q(0.75):.1f}x, top 10% >= {q(0.9):.1f}x")
        for bnd in BANDS:
            for hf in ("FIT", "CHECK"):
                xs = [x for x in res if x["league"] == lg and x["half"] == hf and x["ratio"] >= bnd and x["two5k"] and x["liq"] >= 25000]
                L.append(line(xs, f"    >= {bnd}x {hf}"))
    # Nov 2 13:50 (Peter: "run a bunch of tests, see what's the best P-limit number"): full multiplier sweep per sport x
    # market, both directions. Honest selection: the cutoff is CHOSEN on FIT only (best FIT CLV with >= 30 rows), then
    # its CHECK result is reported as the out-of-sample answer. HOLDS = >= 30 rows and avg CLV > 0 in BOTH halves.
    GRID = (1, 2, 3, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500)

    def fee_c(x):
        """Fee load in cents of probability at the row's own book and price (Muse 13:54: freeze on AFTER-FEE CLV)."""
        p, bk = x.get("price"), (x.get("book") or "").lower()
        if not p or not 0 < p < 1:
            return 0.0
        if bk == "prophetx":
            return 100 * (1 / (1 + (1 / p - 1) * 0.98) - p)
        if bk == "kalshi":
            return 100 * 0.07 * p * (1 - p)
        if bk.startswith("polymarket"):
            return 100 * ex.PMUS_FEE * p * (1 - p)
        return 0.0

    def cell(xs):
        c = [float(x["clv"]) - fee_c(x) for x in xs if x["clv"] is not None]
        g = [x for x in xs if x["result"] in ("W", "L", "P")]
        u = sum(float(x["units"] or 0) for x in g)
        return len(xs), (sum(c) / len(c) if c else None), (u / len(g) if g else None)

    def fmt(t):
        n, c, u = t
        return f"n {n:>3} after-fee CLV {c:+.2f}c {u:+.3f}u" if c is not None and u is not None else f"n {n:>3}"
    L += ["", "MULTIPLIER SWEEP (OJ scale; gates kept). '>=' = ratio at or above; '<' = below (low money vs limit).",
          "CLV here is AFTER FEES at the row's own book and price (Muse 13:54): ProphetX 2% of winnings, Kalshi 0.07xPx(1-P), PM US 0.0695xPx(1-P).",
          "Cutoff picked on FIT ONLY (best FIT CLV, >= 30 rows); CHECK = out-of-sample answer. HOLDS = >= 30 rows, CLV > 0 both halves.",
          "CAUTION: about 30 cutoffs x 20 sport/market cells are tested; some HOLDS lines will be luck. Trust only the FIT-chosen list."]
    picks = []
    for lg in sorted({x["league"] for x in res}) + ["ALL"]:
        for mk in ("ALL", "moneyline", "spread", "total"):
            base = [x for x in res if (lg == "ALL" or x["league"] == lg) and (mk == "ALL" or x["market"] == mk)
                    and x["two5k"] and x["liq"] >= 25000]
            if len(base) < 40:
                continue
            L.append(f"  {lg} {mk}: rows {len(base)}")
            best = None
            for d in (">=", "<"):
                for m in GRID:
                    sel = [x for x in base if (x["ratio"] >= m if d == ">=" else x["ratio"] < m)]
                    F, C = cell([x for x in sel if x["half"] == "FIT"]), cell([x for x in sel if x["half"] == "CHECK"])
                    if F[0] < 10 and C[0] < 10:
                        continue
                    holds = F[0] >= 30 and C[0] >= 30 and (F[1] or -1) > 0 and (C[1] or -1) > 0
                    L.append(f"    {d}{m:>4}x  FIT {fmt(F)} | CHECK {fmt(C)}" + ("  HOLDS" if holds else ""))
                    if F[0] >= 30 and F[1] is not None and (best is None or F[1] > best[0]):
                        best = (F[1], d, m, F, C)
            if best:
                picks.append(f"  {lg} {mk}: FIT-chosen cutoff {best[1]}{best[2]}x -> FIT {fmt(best[3])} | CHECK {fmt(best[4])}"
                             + ("  (holds out of sample)" if best[4][0] >= 30 and (best[4][1] or -1) > 0 else "  (does NOT hold)"))
    L += ["", "FIT-CHOSEN CUTOFFS AND THEIR OUT-OF-SAMPLE RESULT:"] + picks
    L += ["", "2X PASS rows on the OJ scale (newest 25):"]
    for x in sorted([x for x in res if x["pass_OJ"]], key=lambda x: x["alerted"])[-25:][::-1]:
        L.append(f"  {x['alerted'][:16]} {x['league']} {x['game']} | {x['side']} | liq USD {x['liq']:,} vs limit {x['limit_raw']:,.0f} "
                 f"(OJ {x['limit_raw'] * 4 / 3:,.0f}, {x['how']}) | {x['result'] or '-'} {x['units'] if x['units'] is not None else ''}")
    L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in cl.CALLS[:3]) + f" ... ({len(cl.CALLS)} total; billable {cl.STATS['billable']})"]
    ex.send("Bets 2X BACKTEST (HYPOTHESIS)", "\n".join(L))
    print(f"2X backtest: rows {len(rs)}, limited {len(res)}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
