#!/usr/bin/env python3
"""
SMALL-BOOK SURGE BACKTEST (Nov 4, 2026; Peter 10:25 "yes we need to do that ... you might have enough now").
PAPER / MEASUREMENT ONLY - reads the downloaded history, changes nothing the monitor, board, lanes or executor read.

Question: the liquidity monitor's $25k trigger can never fire on thin books (Novig ~$16k, ProphetX ~$8k a side on NBA
totals). Would a RELATIVE trigger - a side jumping to 2x+ its exchange's normal size - have found winners there?

Source: the shared OddsPapi history cache (hcache), Oct 12+, NBA / NFL / NCAAF / NHL, exchanges Novig, ProphetX, Kalshi and
Polymarket US. SIZE = OddsPapi's 'limit' on each exchange tick: the size offered at that best price (a proxy for the monitor's
full bid stack, not the same measure).
NORMAL = median tick size for that exchange x league x bet type (ML, SPREAD, OVER, UNDER) over all PRIOR days (no lookahead;
a key needs >= NORM_MIN_TICKS ticks first). Main lines only: ML priced 15-85c, spreads/totals 30-70c, pregame.
SURGE = the first tick where a side's size crosses REL_X x normal (previous tick under it) with the jump >= REL_NEW_FRAC x
normal; one per game x exchange x bet type x side (the earliest).
GRADE: 1u flat at that tick's price after the exchange's fee (the price the bot would take, or better); W/L/P from ESPN finals;
CLV vs Pinnacle's no-vig close. H1 <= FIT_END < H2. Private email; the log prints counts only.
"""
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import finals as fin
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("novig.us", "prophetx", "kalshi", "polymarket.us")
NAME = {"novig.us": "Novig", "prophetx": "ProphetX", "kalshi": "Kalshi", "polymarket.us": "Polymarket US"}
FROM = datetime.fromisoformat(os.environ.get("SBS_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)
FIT_END = os.environ.get("SBS_FIT_END", "") or "2026-10-28"
REL_X = float(os.environ.get("SBS_REL_X", "") or "2.0")
REL_NEW_FRAC = float(os.environ.get("SBS_REL_NEW_FRAC", "") or "0.5")
NORM_MIN_TICKS = int(os.environ.get("SBS_NORM_MIN_TICKS", "") or "200")
ABS_MIN = 25000   # the live monitor's absolute trigger, to split out what the relative trigger ADDS
LOOKBACK = timedelta(hours=4)   # Nov 4 (Peter 10:29 "both"): GAME normal = that side's own size over the 4 hours before
MIN_LEAD = timedelta(hours=4)   # ...and the 4H variants use only times 4+ hours before tip, for the normal and the surge
MODES = {   # all three run on the same games and are reported side by side
    "LEAGUE": "league normal (exchange x league x bet type, prior days' median), any time pregame",
    "LEAGUE-4H": "league normal from ticks 4h+ before tip only; surges 4h+ before tip only",
    "GAME-4H": "that game side's own size over the previous 4 hours (time-weighted: the size carried in counts); 4h+ before tip only",
}


def band_ok(typ, p):
    return (0.15 <= p <= 0.85) if typ == "moneyline" else (0.30 <= p <= 0.70)


def bet_kind(typ, name):
    return {"Over": "OVER", "Under": "UNDER"}.get(name) if typ == "totals" else ("ML" if typ == "moneyline" else "SPREAD")


def bet_text(f, typ, hcap, name):
    if typ == "totals":
        return f"{name} {hcap:g}"
    team = f["n1"] if name == "1" else f["n2"]
    if typ == "spreads":
        return f"{team} {(hcap if name == '1' else -hcap):+g}"
    return f"{team} ML"


def series(f, xm, mkmap, start, lg):
    """[(key_kind, mid, typ, hcap, name, [(t, dec, limit), ...])] pregame, for one exchange's markets on one game."""
    sid = cl.SPORT.get(lg)
    out = []
    for mid, m in (xm or {}).items():
        mm = mkmap.get(str(mid))
        if not mm or mm[0] != sid or mm[1] not in ("moneyline", "spreads", "totals"):
            continue
        if mm[1] == "moneyline" and str(mid) != str(cl.ML_MARKET.get(sid)):
            continue
        _, typ, hcap, outs = mm
        for oid, o in (m.get("outcomes") or {}).items():
            name = outs.get(str(oid))
            kind = bet_kind(typ, name) if name else None
            if not kind:
                continue
            ticks = []
            for t in (o.get("players") or {}).get("0") or []:
                ct, pr, lim = cl.tp(t.get("createdAt")), tb.num(t.get("price")), tb.num(t.get("limit"))
                if ct and pr and pr > 1 and lim is not None and ct < start:
                    ticks.append((ct, pr, lim))
            if ticks:
                ticks.sort(key=lambda z: z[0])
                out.append((kind, str(mid), typ, hcap, name, ticks))
    return out


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("small-book surge: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), now.astimezone(ET))
    games = []
    for fid, f in (st.get("fixtures") or {}).items():
        s = cl.tp(f.get("start"))
        if f.get("lg") in LEAGUES and s and FROM <= s <= now - timedelta(hours=4):
            games.append((s, fid, f))
    games.sort()
    miss = {"not in cache": 0, "history error": 0}
    # pass 1: every game's pregame exchange tick series (kept in memory; read the cache once)
    G = []
    for s, fid, f in games:
        if not all(os.path.exists(hc._path(fid, b)) for b in ("pinnacle",) + EXCH):
            miss["not in cache"] += 1
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), s)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            continue
        ser = {b: series(f, cl.book_markets(h, b), mkmap, s, f["lg"]) for b in EXCH}
        G.append((s, fid, f, ser, cl.book_markets(h, "pinnacle")))
    # pass 2: surges per mode (normals from prior days only, or the game's own previous 4 hours)
    S = []
    for mode in MODES:
        hist, pend, cur_day, norm_cache = {}, {}, None, {}
        for s, fid, f, ser, pin in G:
            day = s.astimezone(ET).strftime("%Y-%m-%d")
            if day != cur_day:
                for k, v in pend.items():
                    hist.setdefault(k, []).extend(v)
                pend, cur_day, norm_cache = {}, day, {}
            for b, rows in ser.items():
                seen_side = set()
                for kind, mid, typ, hcap, name, ticks in rows:
                    key = f"{b}|{f['lg']}|{kind}"
                    main = [z for z in ticks if band_ok(typ, 1 / z[1])]
                    if mode != "LEAGUE":
                        main = [z for z in main if s - z[0] >= MIN_LEAD]
                    if (kind, name) in seen_side or not main:
                        if mode != "GAME-4H":
                            pend.setdefault(key, []).extend(z[2] for z in main if z[2] > 0)
                        continue
                    if mode == "GAME-4H":
                        for i2 in range(1, len(main)):
                            ct, pr, lim = main[i2]
                            prev = main[i2 - 1][2]
                            lo = ct - LOOKBACK
                            win = [z[2] for z in main[:i2] if z[0] >= lo]
                            carry = [z[2] for z in main[:i2] if z[0] < lo][-1:]   # the size in force when the window opened
                            base = win + carry
                            if not base or main[0][0] > lo:
                                continue   # need a full 4 hours of this side's history first
                            nm = stt.median(base)
                            if nm > 0 and prev < REL_X * nm <= lim and lim - prev >= REL_NEW_FRAC * nm:
                                S.append({"mode": mode, "day": day, "lg": f["lg"], "book": b, "kind": kind, "typ": typ,
                                          "hcap": hcap, "name": name, "t": ct, "start": s, "dec": pr, "lim": lim,
                                          "prev": prev, "normal": nm, "f": f, "pin": pin})
                                seen_side.add((kind, name))
                                break
                        continue
                    pend.setdefault(key, []).extend(z[2] for z in main if z[2] > 0)
                    if key not in norm_cache:
                        hv = hist.get(key) or []
                        norm_cache[key] = stt.median(hv) if len(hv) >= NORM_MIN_TICKS else None
                    nm = norm_cache[key]
                    if not nm:
                        continue
                    prev = None
                    for ct, pr, lim in main:
                        if prev is not None and prev < REL_X * nm <= lim and lim - prev >= REL_NEW_FRAC * nm:
                            S.append({"mode": mode, "day": day, "lg": f["lg"], "book": b, "kind": kind, "typ": typ,
                                      "hcap": hcap, "name": name, "t": ct, "start": s, "dec": pr, "lim": lim, "prev": prev,
                                      "normal": nm, "f": f, "pin": pin})
                            seen_side.add((kind, name))
                            break
                        prev = lim
    # grade
    R = []
    for x in S:
        f = x["f"]
        side = x["name"]
        res = None
        try:
            res = fin.result({"league": x["lg"], "game": f"{f['n1']} vs {f['n2']}", "start": f.get("start"),
                              "type": x["typ"], "line": x["hcap"], "side": side})
        except Exception:
            res = None
        if res not in ("W", "L", "P"):
            miss["no final"] = miss.get("no final", 0) + 1
            continue
        dec = el.eff(x["book"], x["dec"])
        b = {"bet": bet_text(f, x["typ"], x["hcap"], side), "league": x["lg"], "game": f"{f['n1']} vs {f['n2']}",
             "game_start": f.get("start"), "book": x["book"]}
        c, _ = cl.close_for(b, f, x["pin"], mkmap, x["start"], x["lg"])
        clv = round(100 * (c["p"] * dec - 1), 2) if c else None
        if clv is not None and clv > 15:   # same rule as P1 / exchange-lag: > +15% vs the close is a misread quote
            miss["suspect quote dropped"] = miss.get("suspect quote dropped", 0) + 1
            continue
        R.append({"mode": x["mode"], "day": x["day"], "lg": x["lg"], "book": x["book"], "kind": x["kind"],
                  "lead": (x["start"] - x["t"]).total_seconds() / 3600, "mult": x["lim"] / x["normal"],
                  "new": x["lim"] - x["prev"], "clv": clv, "u": fin.units_wl(res, dec), "res": res})

    def stl(xs):
        if not xs:
            return "n 0"
        w = sum(r["res"] == "W" for r in xs)
        l_ = sum(r["res"] == "L" for r in xs)
        u = sum(r["u"] for r in xs)
        cv = [r["clv"] for r in xs if r["clv"] is not None]
        h1 = [r for r in xs if r["day"] <= FIT_END]
        h2 = [r for r in xs if r["day"] > FIT_END]
        pp = lambda z: f"{sum(r['u'] for r in z) / len(z):+.3f} (n{len(z)})" if z else "n0"
        cvs = f"Pinnacle CLV {stt.mean(cv):+.2f}% beat {100 * sum(v > 0 for v in cv) / len(cv):.0f}%" if cv else "no CLV"
        return f"n {len(xs)} | {w}-{l_} {u:+.2f}u {u / len(xs):+.3f}/play | {cvs} | H1 {pp(h1)} H2 {pp(h2)}"

    L = [f"SMALL-BOOK SURGE BACKTEST - PAPER ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         f"Surge = a side's offered size (OddsPapi tick limit) crosses {REL_X:g}x its NORMAL with a jump >= {REL_NEW_FRAC:g}x normal; "
         "first per game x exchange x bet type x side; main lines, pregame. Graded 1u at that tick's price after fee; ESPN "
         f"finals; CLV vs Pinnacle no-vig close. H1 <= {FIT_END} < H2. Three NORMALS, side by side:"]
    L += [f"   {m}: {d}" for m, d in MODES.items()]
    L += [f"Games {len(games)}, read {len(G)}; surges {len(S)}, graded {len(R)}. Not graded: "
          + ", ".join(f"{k} {v}" for k, v in miss.items() if v),
          "Size is the offer at the best price only, not the full bid stack the monitor reads: a proxy."]
    RA = R
    for mode in MODES:
        R = [r for r in RA if r["mode"] == mode]
        L += ["", "=" * 20 + f" NORMAL: {mode} " + "=" * 20]
        small = [r for r in R if r["new"] < ABS_MIN]
        L += [f"ALL SURGES: {stl(R)}",
             f"WHAT THE FIX ADDS (jump under ${ABS_MIN:,} - the live trigger can't see these): {stl(small)}",
             f"jump ${ABS_MIN:,}+ (the live trigger would see these): {stl([r for r in R if r['new'] >= ABS_MIN])}", "",
             "BY EXCHANGE (all leagues and bet types):"]
        for b in EXCH:
            L.append(f"   {NAME[b]}: {stl([r for r in R if r['book'] == b])}")
            L.append(f"      under ${ABS_MIN // 1000}k jump: {stl([r for r in small if r['book'] == b])}")
        L += ["", "NBA TOTALS (the rule's market):"]
        nt = [r for r in R if r["lg"] == "NBA" and r["kind"] in ("OVER", "UNDER")]
        L.append(f"   all: {stl(nt)}")
        L.append(f"   4h+ before tip: {stl([r for r in nt if r['lead'] >= 4])}")
        L.append(f"   under 4h: {stl([r for r in nt if r['lead'] < 4])}")
        for b in EXCH:
            L.append(f"   {NAME[b]}, 4h+: {stl([r for r in nt if r['book'] == b and r['lead'] >= 4])}")
        for k in ("UNDER", "OVER"):
            L.append(f"   {k.title()}s, 4h+: {stl([r for r in nt if r['kind'] == k and r['lead'] >= 4])}")
        L += ["", "SIZE OF THE SURGE (all, 4h+):"]
        f4 = [r for r in R if r["lead"] >= 4]
        for lo, hi, nm in ((2, 3, "2-3x normal"), (3, 5, "3-5x"), (5, 1e9, "5x+")):
            L.append(f"   {nm}: {stl([r for r in f4 if lo <= r['mult'] < hi])}")
        L += ["", "BY LEAGUE x BET TYPE (all leads):"]
        for lg in LEAGUES:
            for k in ("UNDER", "OVER", "ML", "SPREAD"):
                xs = [r for r in R if r["lg"] == lg and r["kind"] == k]
                if xs:
                    L.append(f"   {lg} {k}: {stl(xs)}")
        L += ["", "LEAD TIME (all):"]
        for lo, hi, nm in ((0, 1, "under 1h"), (1, 4, "1-4h"), (4, 12, "4-12h"), (12, 1e9, "12h+")):
            L.append(f"   {nm}: {stl([r for r in R if lo <= r['lead'] < hi])}")
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} "
             f"(billable {cl.STATS['billable']}).")
    ex.send("Bets SMALL-BOOK SURGE BACKTEST (paper)", "\n".join(L))
    print(f"small-book surge: games {len(games)}, read {len(G)}, surges {len(S)}, graded {len(RA)}, "
          f"cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
