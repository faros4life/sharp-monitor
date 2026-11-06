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
import json
import os
import random
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
NORM_MIN_TICKS = int(os.environ.get("SBS_NORM_MIN_TICKS", "") or "50")
SANE_C = float(os.environ.get("SBS_SANE_C", "") or "0.05")   # Nov 4 (Peter 12:11 "fix yes"): price within 5c of Pinnacle fair
RES_CAP = 20000   # Nov 4: normals keep a capped random sample of sizes per key (memory)
ABS_MIN = 25000   # the live monitor's absolute trigger, to split out what the relative trigger ADDS
LOOKBACK = timedelta(hours=4)   # Nov 4 (Peter 10:29 "both"): GAME normal = that side's own size over the 4 hours before
MIN_LEAD = timedelta(hours=4)   # ...and the 4H variants use only times 4+ hours before tip, for the normal and the surge
MODES = {   # all three run on the same games and are reported side by side
    "LEAGUE": "league normal (exchange x league x bet type, prior days' median), any time pregame",
    "LEAGUE-4H": "league normal from ticks 4h+ before tip only; surges 4h+ before tip only",
    "GAME-4H": "that game side's own size over the previous 4 hours (time-weighted: the size carried in counts); 4h+ before tip only",
}


# Nov 4 (Peter 13:44, after the 5x+ breakdown): main lines only, no dust jumps, no off-range lines.
# The 5x+ cell's units came from ~19 longshots priced ~30c (mostly Kalshi alt spreads) and from tiny jumps ($233-$900).
MAIN_LO = float(os.environ.get("SBS_MAIN_LO", "") or "0.35")   # implied price band for every bet type
MAIN_HI = float(os.environ.get("SBS_MAIN_HI", "") or "0.65")
MIN_JUMP = float(os.environ.get("SBS_MIN_JUMP", "") or "2000")  # a surge's jump must be at least this many dollars
# full-game line ranges (the NHL 1.5 "totals" were another market mislabeled in the history)
TOTAL_RANGE = {"NBA": (190, 265), "NFL": (30, 65), "NCAAF": (30, 85), "NHL": (4.5, 7.5)}
SPREAD_MAX = {"NBA": 20, "NFL": 17.5, "NCAAF": 35, "NHL": 1.5}


def band_ok(typ, p):
    return MAIN_LO <= p <= MAIN_HI


def line_ok(lg, typ, hcap):
    if typ == "totals":
        lo, hi = TOTAL_RANGE.get(lg, (0, 1e9))
        return lo <= hcap <= hi
    if typ == "spreads":
        return abs(hcap) <= SPREAD_MAX.get(lg, 1e9)
    return True


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
        if not line_ok(lg, typ, hcap):
            continue   # Nov 4: off-range line = not the full-game main market
        for oid, o in (m.get("outcomes") or {}).items():
            name = outs.get(str(oid))
            kind = bet_kind(typ, name) if name else None
            if not kind:
                continue
            ticks = []
            for t in (o.get("players") or {}).get("0") or []:
                ct, pr, lim = cl.tp(t.get("createdAt")), tb.num(t.get("price")), tb.num(t.get("limit"))
                if ct and pr and pr > 1 and lim is not None and ct < start and band_ok(typ, 1 / pr):
                    ticks.append((ct, pr, lim))   # Nov 4: main-band ticks only (memory: alt lines dropped here)
            if ticks:
                ticks.sort(key=lambda z: z[0])
                slim = [ticks[0]]
                for z in ticks[1:]:   # Nov 4 (memory): keep only ticks where the offered size changed
                    if z[2] != slim[-1][2]:
                        slim.append(z)
                out.append((kind, str(mid), typ, hcap, name, slim))
    return out


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("small-book surge: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    # Nov 6 (Peter, "everything fixed"): reuse the fixtures the CLV ledger already paid for rather
    # than re-buying them. Read-only - nothing here saves that state. Requires TRACKER_PASSPHRASE in
    # the workflow; without it the decrypt fails, this falls through to the fetch, and the calls are
    # bought with nothing in the log to say so. That silence is how plimit-level spent 5 unapproved
    # credits on Nov 6, so the secret and this block always ship together.
    try:
        _prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(_prev.get("fixtures") or {})
        st["fx_last"] = dict(_prev.get("fx_last") or {})
        print(f"fixture cache: reusing {len(st['fixtures'])} fixtures - no re-purchase")
    except Exception as _e:
        print(f"fixture cache: unavailable ({type(_e).__name__}) - fixtures will be fetched")
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
    # Nov 4: ONE PASS, one game at a time (two runs were killed holding every game's ticks): read a game, find its surges
    # under all three normals, grade them while its history is loaded, fold its sizes into the normals, drop it.
    # Normals keep a capped random sample per key (RES_CAP sizes) instead of every tick.
    rng = random.Random(7)
    seen_n = {m: {} for m in MODES}          # key -> sizes seen so far (for the reservoir)
    hist = {m: {} for m in MODES}            # key -> reservoir of sizes from PRIOR days
    pend = {m: {} for m in MODES}            # key -> sizes from the current day, folded in when the day changes
    cur_day, norm_cache = None, {}
    R, read = [], 0

    def fold(mode, key, vals):
        res, n = hist[mode].setdefault(key, []), seen_n[mode].get(key, 0)
        for v in vals:
            n += 1
            if len(res) < RES_CAP:
                res.append(v)
            else:
                k = rng.randrange(n)
                if k < RES_CAP:
                    res[k] = v
        seen_n[mode][key] = n

    for s, fid, f in games:
        if not all(os.path.exists(hc._path(fid, b)) for b in ("pinnacle",) + EXCH):
            miss["not in cache"] += 1
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), s)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            continue
        pin = cl.book_markets(h, "pinnacle")
        ser = {b: series(f, cl.book_markets(h, b), mkmap, s, f["lg"]) for b in EXCH}
        del h
        read += 1
        if read % 200 == 0:
            print(f"small-book surge: read {read} games")   # counts only
        day = s.astimezone(ET).strftime("%Y-%m-%d")
        if day != cur_day:
            for m in MODES:
                for k, v in pend[m].items():
                    fold(m, k, v)
            pend = {m: {} for m in MODES}
            cur_day, norm_cache = day, {}
        found = []
        for mode in MODES:
            for b, rows in ser.items():
                seen_side = set()
                for kind, mid, typ, hcap, name, ticks in rows:
                    key = f"{b}|{f['lg']}|{kind}"
                    main = ticks if mode == "LEAGUE" else [z for z in ticks if s - z[0] >= MIN_LEAD]
                    if mode != "GAME-4H":   # time-weighted: one sample per 15 min the size was on the book (max 96)
                        end = s if mode == "LEAGUE" else s - MIN_LEAD
                        pv = pend[mode].setdefault(key, [])
                        for i3, z in enumerate(main):
                            if z[2] <= 0:
                                continue
                            nxt = main[i3 + 1][0] if i3 + 1 < len(main) else end
                            pv.extend([z[2]] * max(1, min(96, int((nxt - z[0]).total_seconds() // 900))))
                    if (kind, name) in seen_side or len(main) < 2:
                        continue
                    if mode == "GAME-4H":
                        for i2 in range(1, len(main)):
                            ct, pr, lim = main[i2]
                            prev = main[i2 - 1][2]
                            lo = ct - LOOKBACK
                            if main[0][0] > lo:
                                continue   # need a full 4 hours of this side's history first
                            base = [z[2] for z in main[:i2] if z[0] >= lo] + [z[2] for z in main[:i2] if z[0] < lo][-1:]
                            nm = stt.median(base)
                            if nm > 0 and prev < REL_X * nm <= lim and lim - prev >= max(REL_NEW_FRAC * nm, MIN_JUMP):
                                found.append((mode, b, kind, typ, hcap, name, ct, pr, lim, prev, nm))
                                seen_side.add((kind, name))
                                break
                        continue
                    ck = (mode, key)
                    if ck not in norm_cache:
                        hv = hist[mode].get(key) or []
                        norm_cache[ck] = stt.median(hv) if seen_n[mode].get(key, 0) >= NORM_MIN_TICKS and hv else None
                    nm = norm_cache[ck]
                    if not nm:
                        continue
                    for i2 in range(1, len(main)):
                        ct, pr, lim = main[i2]
                        prev = main[i2 - 1][2]
                        if prev < REL_X * nm <= lim and lim - prev >= max(REL_NEW_FRAC * nm, MIN_JUMP):
                            found.append((mode, b, kind, typ, hcap, name, ct, pr, lim, prev, nm))
                            seen_side.add((kind, name))
                            break
        # one play counts once (Peter 10:58): per mode, the FIRST surge on a game + bet type + side across exchanges
        found.sort(key=lambda z: z[6])
        firsts = set()
        for mode, b, kind, typ, hcap, name, ct, pr, lim, prev, nm in found:
            pk = (mode, kind, name)
            first = pk not in firsts
            firsts.add(pk)
            try:
                res = fin.result({"league": f["lg"], "game": f"{f['n1']} vs {f['n2']}", "start": f.get("start"),
                                  "type": typ, "line": hcap, "side": name})
            except Exception:
                res = None
            if res not in ("W", "L", "P"):
                miss["no final"] = miss.get("no final", 0) + 1
                continue
            dec = el.eff(b, pr)
            bb = {"bet": bet_text(f, typ, hcap, name), "league": f["lg"], "game": f"{f['n1']} vs {f['n2']}",
                  "game_start": f.get("start"), "book": b}
            c, _ = cl.close_for(bb, f, pin, mkmap, s, f["lg"])
            # Nov 4 fix: a surge counts as SANE only if the exchange's own price (before fee) was within SANE_C of
            # Pinnacle's no-vig fair for that side AT THE SURGE TIME - big size parked at an off-market price is not a bet
            ft, _ = cl.close_for(bb, f, pin, mkmap, ct, f["lg"])
            sane = bool(ft) and abs(1 / pr - ft["p"]) <= SANE_C
            clv = round(100 * (c["p"] * dec - 1), 2) if c else None
            if clv is not None and clv > 15:   # same rule as P1 / exchange-lag: > +15% vs the close is a misread quote
                miss["suspect quote dropped"] = miss.get("suspect quote dropped", 0) + 1
                continue
            R.append({"mode": mode, "first": first, "day": day, "lg": f["lg"], "book": b, "kind": kind,
                      "lead": (s - ct).total_seconds() / 3600, "mult": lim / nm, "new": lim - prev, "clv": clv,
                      "u": fin.units_wl(res, dec), "res": res, "sane": sane, "hcap": hcap, "price": pr,
                      "fair_t": ft["p"] if ft else None, "game": f"{f['n1']} vs {f['n2']}"})
        del ser, pin
    G = range(read)
    S = R
    RALL = R
    R = [r for r in RALL if r["first"]]   # every table below is one-play-once unless it says otherwise

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
         f"Surge = a side's offered size (OddsPapi tick limit) crosses {REL_X:g}x its NORMAL with a jump >= {REL_NEW_FRAC:g}x normal and >= ${MIN_JUMP:,.0f}; "
         f"main lines priced {MAIN_LO * 100:.0f}-{MAIN_HI * 100:.0f}c, full-game line ranges only; "
         "ONE PLAY COUNTS ONCE: the first surge per game x bet type x side across exchanges; main lines, pregame. Graded 1u at that tick's price after fee; ESPN "
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
            L.append(f"   {NAME[b]} (surged first): {stl([r for r in R if r['book'] == b])}")
            L.append(f"      incl. surges after another exchange on the same play: {stl([r for r in RALL if r['mode'] == mode and r['book'] == b])}")
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
    L += ["", "=" * 20 + " PRICE-SANE ONLY (exchange price within %.0fc of Pinnacle fair at the surge; one play counts once) " % (SANE_C * 100) + "=" * 20]
    for mode in MODES:
        Z = [r for r in RA if r["mode"] == mode and r["sane"]]
        z4 = [r for r in Z if r["lead"] >= 4]
        L += ["", f"-- {mode} --", f"   ALL: {stl(Z)}", f"   jump under ${ABS_MIN // 1000}k (what the fix adds): {stl([r for r in Z if r['new'] < ABS_MIN])}",
              f"   4h+ before tip: {stl(z4)}"]
        for b in EXCH:
            L.append(f"   {NAME[b]} (surged first), 4h+: {stl([r for r in z4 if r['book'] == b])}")
        nt = [r for r in z4 if r["lg"] == "NBA" and r["kind"] in ("OVER", "UNDER")]
        L.append(f"   NBA totals 4h+: {stl(nt)}")
        for b in EXCH:
            L.append(f"      {NAME[b]}: {stl([r for r in nt if r['book'] == b])}")
        for k in ("UNDER", "OVER"):
            L.append(f"      {k.title()}s: {stl([r for r in nt if r['kind'] == k])}")
        for lo, hi, nm in ((2, 3, "2-3x"), (3, 5, "3-5x"), (5, 1e9, "5x+")):
            L.append(f"   size {nm}, 4h+: {stl([r for r in z4 if lo <= r['mult'] < hi])}")
        for lg in LEAGUES:
            for k in ("UNDER", "OVER", "ML", "SPREAD"):
                xs = [r for r in z4 if r["lg"] == lg and r["kind"] == k]
                if xs:
                    L.append(f"   {lg} {k}, 4h+: {stl(xs)}")
    # Nov 4 (Peter 12:57 "yes. but it looks promising"): 5x+ price-sane breakdown, every normal, 4h+, one play once
    L += ["", "=" * 20 + " 5x+ PRICE-SANE BREAKDOWN (4h+ before tip; one play counts once) " + "=" * 20]
    for mode in MODES:
        F5 = [r for r in RA if r["mode"] == mode and r["sane"] and r["lead"] >= 4 and r["mult"] >= 5]
        L += ["", f"-- {mode} --", f"   ALL 5x+: {stl(F5)}"]
        for lo, hi, nm in ((5, 10, "5-10x"), (10, 1e9, "10x+")):
            L.append(f"   {nm}: {stl([r for r in F5 if lo <= r['mult'] < hi])}")
        for b in EXCH:
            L.append(f"   {NAME[b]} (surged first): {stl([r for r in F5 if r['book'] == b])}")
        for lg in LEAGUES:
            xs = [r for r in F5 if r["lg"] == lg]
            if xs:
                L.append(f"   {lg}: {stl(xs)}")
                for k in ("UNDER", "OVER", "ML", "SPREAD"):
                    ys = [r for r in xs if r["kind"] == k]
                    if ys:
                        L.append(f"      {lg} {k}: {stl(ys)}")
        for k in ("UNDER", "OVER", "ML", "SPREAD"):
            L.append(f"   all leagues {k}: {stl([r for r in F5 if r['kind'] == k])}")
        L.append(f"   4-12h before tip: {stl([r for r in F5 if r['lead'] < 12])}")
        L.append(f"   12h+ before tip: {stl([r for r in F5 if r['lead'] >= 12])}")
        L.append(f"   jump under $25k: {stl([r for r in F5 if r['new'] < ABS_MIN])}")
        L.append(f"   jump $25k+: {stl([r for r in F5 if r['new'] >= ABS_MIN])}")
        L.append(f"   exchange price at or better than Pinnacle fair: {stl([r for r in F5 if r['fair_t'] is not None and 1 / r['price'] <= r['fair_t']])}")
        L.append(f"   exchange price worse than Pinnacle fair (within 5c): {stl([r for r in F5 if r['fair_t'] is not None and 1 / r['price'] > r['fair_t']])}")
        if mode == "LEAGUE-4H":
            L.append("   plays (date | league | bet | exchange | x normal | jump $ | hrs to tip | price dec | Pinnacle fair | result | units):")
            for r in sorted(F5, key=lambda z: z["day"]):
                L.append(f"      {r['day']} | {r['lg']} | {r['kind']} {r['hcap']} | {NAME[r['book']]} | {r['mult']:.1f}x | "
                         f"${r['new']:,.0f} | {r['lead']:.1f} | {r['price']} | {r['fair_t']:.3f} | {r['res']} | {r['u']:+.2f}")
    sane_n = sum(1 for r in RA if r["sane"])
    L += ["", f"Price-sane share of graded surges: {sane_n} of {len(RA)} ({100 * sane_n / max(len(RA), 1):.0f}%)."]
    # NHL totals diagnostic (Nov 4: NHL unders 1-155 in the first run = a grading or line-mapping bug to find)
    NH = [r for r in RA if r["mode"] == "GAME-4H" and r["lg"] == "NHL" and r["kind"] in ("OVER", "UNDER")]
    from collections import Counter
    L += ["", "NHL TOTALS DIAGNOSTIC (GAME-4H, all graded surges):",
          "   lines seen: " + ", ".join(f"{k}: {v}" for k, v in sorted(Counter(r["hcap"] for r in NH).items())),
          "   by side and result: " + ", ".join(f"{k}: {v}" for k, v in sorted(Counter((r["kind"], r["res"]) for r in NH).items())),
          f"   with a Pinnacle fair at the surge: {sum(1 for r in NH if r['fair_t'] is not None)} of {len(NH)}; price-sane: {sum(1 for r in NH if r['sane'])}",
          "   sample (first 12 unders): game | book | line | exchange price (decimal) | Pinnacle fair at surge | result"]
    for r in [r for r in NH if r["kind"] == "UNDER"][:12]:
        L.append(f"      {r['game']} | {NAME[r['book']]} | {r['hcap']} | {r['price']} | "
                 f"{'-' if r['fair_t'] is None else round(r['fair_t'], 3)} | {r['res']}")
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} "
             f"(billable {cl.STATS['billable']}).")
    ex.send("Bets SMALL-BOOK SURGE BACKTEST (paper)", "\n".join(L))
    print(f"small-book surge: games {len(games)}, read {len(G)}, surges {len(S)}, graded {len(RA)}, "
          f"cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()
