#!/usr/bin/env python3
"""
NBA TOTALS MODEL - BACKTEST #2 (Nov 2, 2026; Peter yes 13:02 ET). HYPOTHESIS. Same window, split, bar and no-look-ahead
rule as backtest #1 (nba_backtest.py, Muse 12:19 terms); tests the three changes proposed from #1's result. Each is
kept only if it improves the CHECK half (Muse rule).

  a) BIAS FIX: variant REG+B = the live model's number + the average (Pinnacle close - our number) over all graded games
     on EARLIER dates (no look-ahead; needs >= 15 earlier games, else no number that day).
  b) TIMING: OPEN (Pinnacle's first totals tick + 1 min) is primary; T-6h (the live model's post time) for comparison.
  c) PRICE: each sighting graded at Pinnacle's own price (PIN) and at each exchange's price on that side at that line,
     AFTER FEES (Peter 13:06: add Polymarket and Kalshi): NOVIG (no fee), PROPHETX (2% of winnings), KALSHI
     (0.07 x P x (1-P) per contract), POLY = Polymarket US (executor taker model 0.0695 x P x (1-P), Muse 13:19), and BEST.
     An exchange's quote = its last tick at or before the sighting time if under 24 h old, else its first tick within
     2 h after (delay logged). DEPTH: the tick's 'limit' is logged where history carries it; not gettable proof.

Grade: CLV % = Pinnacle no-vig close at that line x decimal - 1. Bar per cell (registered): >= 100 games graded,
avg CLV > 0 and beat-close >= 53% in FIT and in CHECK. Read-only: private email; the log prints counts only.
"""
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import buckets as bkt
import executor as ex
import hist_cache as hc
import nba_backtest as b1
import nba_totals_model as nm
import tracker_build as tb

LO, HI, SPLIT = b1.LO, b1.HI, b1.SPLIT
THRESH = (2.0, 3.0, 4.0)
TIMES = ("OPEN", "T-6h")
MIN_BIAS_N = 15
EXCH = {"NOVIG": "novig.us", "PROPHETX": "prophetx", "KALSHI": "kalshi", "POLY": "polymarket.us"}
PX = ("PIN", "NOVIG", "PROPHETX", "KALSHI", "POLY", "BEST")


def novig_at(xm, mkmap, line, side, t):
    """(decimal, tick time, limit, delay_min) for an exchange's side at that total line, or None."""
    for mid, (s, ty, hcap, outs) in mkmap.items():
        if s != 11 or ty != "totals" or abs(hcap - line) > 1e-9 or mid not in xm:
            continue
        oid = {v: k for k, v in outs.items()}.get(side)
        tk = []
        for x in (((xm[mid].get("outcomes") or {}).get(oid) or {}).get("players") or {}).get("0") or []:
            c, p = cl.tp(x.get("createdAt")), tb.num(x.get("price"))
            if c and p and p > 1:
                tk.append((c, p, tb.num(x.get("limit"))))
        tk.sort()
        before = [x for x in tk if x[0] <= t and t - x[0] <= timedelta(hours=24)]
        if before:
            x = before[-1]
            return x[1], x[0], x[2], 0
        after = [x for x in tk if t < x[0] <= t + timedelta(hours=2)]
        if after:
            x = after[0]
            return x[1], x[0], x[2], round((x[0] - t).total_seconds() / 60)
    return None


def main():
    if not cl.KEY:
        print("NBA backtest 2: ODDSPAPI_KEY not set")
        return
    boxes, games = {}, []
    day = datetime.fromisoformat("2026-10-20").date()
    while day.isoformat() <= HI:
        try:
            for g in nm.scoreboard(day):
                if g["completed"] and g["hs"] is not None:
                    bx = nm.box(g["id"])
                    if bx:
                        boxes[g["id"]] = {"start": g["start"], "teams": bx}
                    if LO <= b1.etd(g["start"]) <= HI:
                        g["final"] = float(g["hs"]) + float(g["as"])
                        games.append(g)
        except Exception:
            pass
        day += timedelta(days=1)
    st = {"billable": {}}
    mkmap = cl.load_markets(st, b1.NOW)
    cl.refresh_fixtures(st, b1.NOW, "NBA", datetime.fromisoformat(LO) - timedelta(days=1), datetime.fromisoformat(HI) + timedelta(days=2))
    fx = st.get("fixtures") or {}
    rows, why = [], {}
    for g in sorted(games, key=lambda g: g["start"]):
        fid = b1.match(fx, g)
        if not fid:
            why["no OddsPapi fixture"] = why.get("no OddsPapi fixture", 0) + 1
            continue
        h = hc.get_hist(fid, ["pinnacle", "novig.us", "prophetx", "kalshi", "polymarket.us"], nm.pt(g["start"]))   # shared cache
        if isinstance(h, dict) and h.get("_error"):
            why[f"history {h['_error']}"] = why.get(f"history {h['_error']}", 0) + 1
            continue
        pm = cl.book_markets(h, "pinnacle")
        xm = {k: cl.book_markets(h, b) for k, b in EXCH.items()}
        s0 = nm.pt(g["start"])
        close = b1.totals_at(pm, mkmap, s0)
        if not b1.main_line(close):
            why["no Pinnacle totals close"] = why.get("no Pinnacle totals close", 0) + 1
            continue
        ft = b1.first_tick(pm, mkmap)
        at = {"OPEN": min(ft + timedelta(minutes=1), s0) if ft else None, "T-6h": s0 - timedelta(hours=6)}
        snap = {}
        for k, t in at.items():
            m = b1.main_line(b1.totals_at(pm, mkmap, t)) if t else None
            if m:
                snap[k] = {"t": t, "line": m[0], "over": m[1], "under": m[2], "p_over": m[3]}
        r = b1.ratings_asof(boxes, b1.etd(g["start"]), 10, 10.0)
        if not r:
            why["no prior games (opening days)"] = why.get("no prior games (opening days)", 0) + 1
            continue
        num = b1.number(r, g["home"], g["away"])[0]
        # keep only the exchange quotes needed (both sides at each snapshot line), not whole histories (memory: runs died ~17 min)
        quotes = {k: {sd: {px: novig_at(xm[px], mkmap, sn["line"], sd, sn["t"]) for px in EXCH if xm.get(px)}
                      for sd in ("Over", "Under")} for k, sn in snap.items()}
        rows.append({"day": b1.etd(g["start"]), "game": f"{g['away']} @ {g['home']}", "final": g["final"],
                     "close": b1.main_line(close)[0], "close_c": close, "snap": snap, "reg": num, "xm": [k for k, v in xm.items() if v],
                     "_q": quotes})
        del h, pm, xm
    # bias per day from EARLIER dates only
    for row in rows:
        prev = [x["close"] - x["reg"] for x in rows if x["day"] < row["day"]]
        row["bias"] = round(stt.mean(prev), 2) if len(prev) >= MIN_BIAS_N else None
        row["num"] = {"REG": row["reg"]}
        if row["bias"] is not None:
            row["num"]["REG+B"] = round(row["reg"] + row["bias"], 1)
        row["sig"] = {}
        for v, n in row["num"].items():
            for k, sn in row["snap"].items():
                gap = n - sn["line"]
                side = "Over" if gap > 0 else "Under"
                pc = b1.p_at(row["close_c"], sn["line"], side)
                d = (row["final"] - sn["line"]) * (1 if side == "Over" else -1)
                res = "P" if abs(d) < 1e-9 else ("W" if d > 0 else "L")
                pin_dec = sn["over"] if side == "Over" else sn["under"]
                q = {"PIN": (pin_dec, 0, None)}
                for px, bk in EXCH.items():
                    nv = row["_q"][k][side].get(px)
                    if nv:
                        q[px] = (el.eff(bk, nv[0]), nv[3], nv[2])
                ex_q = [(px, x) for px, x in q.items() if px != "PIN"]
                if ex_q:
                    bp, bx = max(ex_q, key=lambda z: z[1][0])
                    q["BEST"] = (bx[0], bx[1], bx[2])
                    q["BEST"] = q["BEST"] + (bp,)
                for px, x in q.items():
                    dec = x[0]
                    row["sig"][f"{v}|{k}|{px}"] = {
                        "gap": round(gap, 1), "side": side, "line": sn["line"], "dec": dec,
                        "clv": None if pc is None else round(100 * (pc * dec - 1), 2),
                        "res": res, "u": 0.0 if res == "P" else (dec - 1 if res == "W" else -1.0),
                        "delay": x[1], "lim": x[2], "src": x[3] if len(x) > 3 else px}
    for row in rows:
        row.pop("_q", None)
        row.pop("close_c", None)
    report(rows, why, len(games))
    print(f"NBA backtest 2: games {len(games)}, graded {len(rows)}, calls {len(cl.CALLS)}")   # counts only


def stats(S):
    if not S:
        return "n 0"
    c = [s["clv"] for s in S if s["clv"] is not None]
    w, l_ = sum(s["res"] == "W" for s in S), sum(s["res"] == "L" for s in S)
    out = f"n {len(S)}"
    if c:
        out += f" | CLV {stt.mean(c):+.2f}% beat-close {sum(x > 0 for x in c)}/{len(c)} ({100 * sum(x > 0 for x in c) / len(c):.0f}%)"
    return out + f" | {w}-{l_} {sum(s['u'] for s in S):+.2f}u"


def passes(S):
    c = [s["clv"] for s in S if s["clv"] is not None]
    return bool(c) and stt.mean(c) > 0 and sum(x > 0 for x in c) / len(c) >= 0.53


def report(rows, why, n_games):
    L = [f"NBA TOTALS MODEL - BACKTEST #2 (HYPOTHESIS) | games {LO} to {HI} ET | FIT <= {SPLIT} < CHECK",
         "Tests: a) bias fix REG+B (our number + avg Pinnacle-close-minus-ours from EARLIER dates, >= 15 games);",
         "b) OPEN vs T-6h; c) price: PIN = Pinnacle's own; NOVIG / PROPHETX / KALSHI / POLY = that exchange AFTER FEES; BEST = best exchange.",
         "CLV % = Pinnacle no-vig close at that line x after-fee decimal - 1. Fees: ProphetX 2% of winnings, Kalshi 0.07xPx(1-P), Polymarket US 0.0695xPx(1-P), Novig 0.",
         "Kept only if it improves the CHECK half. Exchange depth logged where history has it; not proof the price was gettable.",
         "", f"Games {n_games}; graded {len(rows)}; not graded: " + (", ".join(f"{v} x {k}" for k, v in why.items()) or "none"),
         "Games with exchange history: " + ", ".join(f"{px} {sum(1 for r in rows if px in r['xm'])}" for px in EXCH)]
    bl = [r["bias"] for r in rows if r["bias"] is not None]
    if bl:
        L.append(f"Bias applied (Pinnacle close minus our number, earlier dates): first {bl[0]:+.1f}, last {bl[-1]:+.1f}, "
                 f"games with a bias {len(bl)}")
    for v in ("REG", "REG+B"):
        g = [r for r in rows if v in r["num"]]
        if g:
            L.append(f"MAE vs final, {v} (n {len(g)}): ours {stt.mean(abs(r['num'][v] - r['final']) for r in g):.2f} | Pinnacle open "
                     f"{stt.mean(abs(r['snap']['OPEN']['line'] - r['final']) for r in g if 'OPEN' in r['snap']):.2f} | close "
                     f"{stt.mean(abs(r['close'] - r['final']) for r in g):.2f}")
    L += ["", "BAR CELLS (gap >= 3.0): >= 100 games graded, CLV > 0 and beat-close >= 53% in FIT and CHECK"]
    for v in ("REG", "REG+B"):
        for k in TIMES:
            for px in PX:
                key = f"{v}|{k}|{px}"
                S = [r["sig"][key] for r in rows if key in r["sig"] and abs(r["sig"][key]["gap"]) >= 3.0]
                F = [r["sig"][key] for r in rows if key in r["sig"] and abs(r["sig"][key]["gap"]) >= 3.0 and r["day"] <= SPLIT]
                C = [r["sig"][key] for r in rows if key in r["sig"] and abs(r["sig"][key]["gap"]) >= 3.0 and r["day"] > SPLIT]
                ok = len(rows) >= 100 and passes(F) and passes(C)
                L += [f"  {v:<5} {k:<4} {px:<5}: {stats(S)} | {'MEETS BAR' if ok else 'does not meet bar'}",
                      f"        FIT {stats(F)}", f"        CHECK {stats(C)}"]
    L += ["", "ALL THRESHOLDS:"]
    for v in ("REG", "REG+B"):
        for k in TIMES:
            for px in PX:
                key = f"{v}|{k}|{px}"
                for th in THRESH:
                    S = [r["sig"][key] for r in rows if key in r["sig"] and abs(r["sig"][key]["gap"]) >= th]
                    sides = f" (Over {sum(s['side'] == 'Over' for s in S)} / Under {sum(s['side'] == 'Under' for s in S)})" if S else ""
                    L.append(f"  {v:<5} {k:<4} {px:<5} gap>={th:g}: {stats(S)}{sides}")
    L.append("")
    for px in EXCH:
        nv = [r["sig"][k] for r in rows for k in r["sig"] if k == f"REG+B|OPEN|{px}"]
        if nv:
            d = [s["delay"] for s in nv]
            lims = [s["lim"] for s in nv if s["lim"]]
            L.append(f"{px} at OPEN (REG+B, all gaps): {len(nv)} priced; same-time quote {sum(1 for x in d if x == 0)}, later quote "
                     f"{sum(1 for x in d if x > 0)} (median delay {stt.median([x for x in d if x > 0]) if any(x > 0 for x in d) else 0} min); "
                     f"depth logged on {len(lims)}" + (f", median USD {stt.median(lims):,.0f}" if lims else ""))
    bs = [r["sig"][k]["src"] for r in rows for k in r["sig"] if k == "REG+B|OPEN|BEST"]
    if bs:
        L.append("BEST price came from: " + ", ".join(f"{px} {bs.count(px)}" for px in EXCH if bs.count(px)))
    L += ["", "REG+B OPEN SIGHTINGS (gap >= 3.0):"]
    for r in rows:
        s, n_ = r["sig"].get("REG+B|OPEN|PIN"), r["sig"].get("REG+B|OPEN|BEST")
        if s and abs(s["gap"]) >= 3.0:
            L.append(f"  {r['day']} {r['game']} | ours {r['num']['REG+B']} vs Pin open {s['line']:g} (close {r['close']:g}) | {s['side']} "
                     f"Pin {cl.dec_to_am(s['dec']):+d} CLV {s['clv'] if s['clv'] is not None else '-'}%"
                     + (f" | best exchange {n_['src']} {cl.dec_to_am(n_['dec']):+d} after fees, CLV {n_['clv'] if n_['clv'] is not None else '-'}%" if n_ else " | no exchange price")
                     + f" | final {r['final']:g} {s['res']}")
    for k in TIMES:
        kk = f"REG+B|{k}|PIN"
        S = [dict(r["sig"][kk], day=r["day"]) for r in rows if kk in r["sig"] and abs(r["sig"][kk]["gap"]) >= 3.0]
        L += [""] + bkt.section(f"REG+B {k}, gap >= 3 (CLV % at Pinnacle price)",
                                [{"day": s["day"], "clv": s["clv"], "lg": "NBA", "mk": "totals", "sc": s["side"].lower(),
                                  "am": bkt.dec_to_am(s["dec"]), "lead": 360 if k == "T-6h" else None} for s in S], "%")
    L += ["", f"Calls: {len(cl.CALLS)} total; billable {cl.STATS['billable']}; history cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}"]
    ex.send("Bets NBA MODEL BACKTEST #2 (HYPOTHESIS)", "\n".join(L))


if __name__ == "__main__":
    main()
