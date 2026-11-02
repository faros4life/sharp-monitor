#!/usr/bin/env python3
"""
SLOW-HR BACKTEST (Nov 2, 2026; Peter 15:46: "can we backtest?"). HYPOTHESIS ONLY. Runs the registered SLOW-HR test
(slow_hr.sightings, unchanged: Type L = Pinnacle main line moves >= 0.5 while Hard Rock shows the old line; Type P = same
line, Pinnacle price moves >= 8c while Hard Rock stays within 2c; persistence 3 min + confirmation at +5 min) over every
finished NFL / NCAAF / NHL game since Oct 12 (OddsPapi's history depth), Pinnacle vs Hard Rock, from the shared history
cache. Graded on Pinnacle's no-vig close at Hard Rock's line (CLV in cents, plus % at Hard Rock's price). FIT = first half
of game dates, CHECK = second half. Bar shown (house): >= 100, CLV > 0 and beat-close >= 53% in BOTH halves.
DEVIATIONS as in SLOW-HR: Pinnacle close as the consensus proxy; FEED-LAG not wired. Hard Rock limits Peter on NBA / NCAAB,
so those leagues are excluded. Private email; the log prints counts only.
"""
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import buckets as bkt
import executor as ex
import hist_cache as hc
import slow_hr as sh
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NFL", "NCAAF", "NHL")
EXB = ["novig.us", "prophetx", "kalshi", "polymarket.us"]
KEYS = (3, 7, 10, 14)


def _hr_main(book, mkmap, sid, typ, when):
    """Closest-to-even line for that market type at that time (fresh ticks), or None."""
    best = None
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in book:
            continue
        nmo = {v: k for k, v in outs.items()}
        a, b = (nmo.get("Over"), nmo.get("Under")) if typ == "totals" else (nmo.get("1"), nmo.get("2"))
        pa = sh.at(sh.ticks((book[mid].get("outcomes") or {}).get(a) or {}), when)
        pb = sh.at(sh.ticks((book[mid].get("outcomes") or {}).get(b) or {}), when)
        if not pa or not pb or when - min(pa[0], pb[0]) > timedelta(hours=24):
            continue
        d = abs(1 / pa[1] - 1 / pb[1])
        if best is None or d < best[0]:
            best = (d, hcap)
    return best[1] if best else None


def enrich(x, lg, pin, hr, h, mkmap, start):
    """Muse 15:52 conditioning fields: market, side class (fav/dog by POINTS, over/under), key numbers, still bettable at
    +1 / +5 min after detection, and whether other books (exchanges) moved with Pinnacle."""
    sid, typ, side, line = cl.SPORT[lg], x["type"], x["side"], x["line"]
    tc, tm = cl.tp(x["t_confirm"]), cl.tp(x["t_move"])
    mid = outs = None
    for m, (s, t, hcap, o) in mkmap.items():
        if s == sid and t == typ and m in hr and (typ == "moneyline" or (line is not None and abs(hcap - line) < 1e-9)):
            mid, outs = m, o
            break
    oid = {v: k for k, v in (outs or {}).items()}.get(side)
    # side class
    if typ == "totals":
        x["sclass"] = "under" if side == "Under" else "over"
    else:
        if typ == "spreads":
            mine = line if side == "1" else -line
        else:
            spl = None
            best = None
            for m, (s, t, hcap, o) in mkmap.items():
                if s == sid and t == "spreads" and m in pin:
                    tw = cl.two_way(pin, m, tm)
                    if len(tw) == 2:
                        lim = min(v[2] for v in tw.values())
                        if best is None or lim > best:
                            best, spl = lim, hcap
            mine = None if spl is None else (spl if side == "1" else -spl)
        x["sclass"] = "pick" if mine in (None, 0) else ("fav" if mine < 0 else "dog")
    # key numbers (football spreads)
    x["key"] = None
    if typ == "spreads" and lg in ("NFL", "NCAAF"):
        import re
        mm = re.search(r"Pinnacle ([-+]?[0-9.]+) -> ([-+]?[0-9.]+)", x["detail"])
        a, b = (abs(float(mm.group(1))), abs(float(mm.group(2)))) if mm else (abs(line), abs(line))
        lo_, hi_ = min(a, b), max(a, b)
        if a != b and any(lo_ <= k <= hi_ for k in KEYS):
            x["key"] = "move crosses/lands on 3/7/10/14"
        elif abs(line) in KEYS or any(abs(abs(line) - k) == 0.5 for k in KEYS):
            x["key"] = "stale line on/next to a key number"
        else:
            x["key"] = "no key number"
    # still bettable at Hard Rock 1 and 5 minutes after detection (same line still Hard Rock's, price within 2c)
    for mins in (1, 5):
        t = tc + timedelta(minutes=mins)
        ok = False
        if mid and oid and t <= start:
            tk = sh.at(sh.ticks((hr[mid].get("outcomes") or {}).get(oid) or {}), t)
            cur = _hr_main(hr, mkmap, sid, typ, t) if typ != "moneyline" else line
            ok = bool(tk) and abs(sh.cents(tk[1]) - sh.cents(x["hr_price"])) <= 2 and (typ == "moneyline" or cur == line)
        x[f"live{mins}"] = ok
    # did the other books (exchanges) move with Pinnacle?
    moved = False
    for bk in EXB:
        xb = cl.book_markets(h, bk)
        if not xb:
            continue
        if x["kind"] == "L" and typ != "moneyline":
            l0, l1 = _hr_main(xb, mkmap, sid, typ, tm - timedelta(minutes=15)), _hr_main(xb, mkmap, sid, typ, tc)
            if l0 is not None and l1 is not None and l0 != l1:
                moved = True
        elif mid and oid and mid in xb:
            s0 = sh.at(sh.ticks((xb[mid].get("outcomes") or {}).get(oid) or {}), tm - timedelta(minutes=15))
            s1 = sh.at(sh.ticks((xb[mid].get("outcomes") or {}).get(oid) or {}), tc)
            if s0 and s1 and sh.cents(s0[1]) - sh.cents(s1[1]) >= 4:
                moved = True
    x["wide"] = moved
    # #11 (Muse 15:57): Pinnacle's RAW limit when it moved (main market of that type, largest limit at the move time)
    plim = None
    for m, (s, t, hcap, o) in mkmap.items():
        if s == sid and t == typ and m in pin:
            tw = cl.two_way(pin, m, tm)
            if len(tw) == 2:
                lim = min(v[2] for v in tw.values())
                if plim is None or lim > plim:
                    plim = lim
    x["pin_limit"] = plim
FROM = datetime.fromisoformat(os.environ.get("BT_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("slow-hr backtest: ODDSPAPI_KEY not set")
        return
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    todo = sorted((cl.tp(f["start"]), fid, f) for fid, f in (st.get("fixtures") or {}).items()
                  if f.get("lg") in LEAGUES and cl.tp(f.get("start")) and FROM <= cl.tp(f["start"]) <= now - hc.FINAL_AFTER)
    sh.FLOOR = FROM
    S, games, no_hr, errs = [], 0, 0, 0
    for s, fid, f in todo:
        h = hc.get_hist(fid, ["pinnacle", "hardrockbet"] + EXB, s)
        if isinstance(h, dict) and h.get("_error"):
            errs += 1
            continue
        pin, hr = cl.book_markets(h, "pinnacle"), cl.book_markets(h, "hardrockbet")
        if not pin or not hr:
            no_hr += 1
            continue
        games += 1
        for x in sh.sightings(fid, {"participant1Name": f.get("n1"), "participant2Name": f.get("n2")}, f["lg"], pin, hr, mkmap, s):
            x["day"] = s.astimezone(ET).strftime("%Y-%m-%d")
            if x.get("close_fair") is not None:
                x["clv_pct"] = round(100 * (x["close_fair"] * x["hr_price"] - 1), 2)
            try:
                enrich(x, f["lg"], pin, hr, h, mkmap, s)
            except Exception:
                x.setdefault("sclass", None)
            S.append(x)
    days = sorted({x["day"] for x in S})
    mid = days[(len(days) - 1) // 2] if days else ""

    def stats(xs):
        c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
        p = [x["clv_pct"] for x in xs if x.get("clv_pct") is not None]
        if not c:
            return f"n {len(xs)}"
        return (f"n {len(xs)} | CLV {stt.mean(c):+.2f}c ({stt.mean(p):+.2f}% at HR price) | beat close "
                f"{sum(1 for v in c if v > 0)}/{len(c)} ({100 * sum(1 for v in c if v > 0) / len(c):.0f}%)")

    def ok(xs):
        c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
        return bool(c) and stt.mean(c) > 0 and sum(1 for v in c if v > 0) / len(c) >= 0.53
    J = [x for x in S if not x["late"]]
    F, C = [x for x in J if x["day"] <= mid], [x for x in J if x["day"] > mid]
    L = [f"SLOW-HR BACKTEST - HYPOTHESIS ONLY | Pinnacle vs Hard Rock | NFL / NCAAF / NHL | games {FROM.date()} to now | FIT <= {mid} < CHECK",
         "Registered SLOW-HR test, unchanged (L: line moved >= 0.5, HR on old line; P: price moved >= 8c, HR within 2c; persist 3 min + confirm +5).",
         "Grade: Pinnacle no-vig close at Hard Rock's line. DEVIATIONS: Pinnacle close as consensus proxy; FEED-LAG not wired.", "",
         f"Games read: {games} (no Hard Rock or Pinnacle history: {no_hr}; errors: {errs}); cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}",
         f"ALL (not LATE): {stats(J)}  | bar: {'MEETS' if len(J) >= 100 and ok(F) and ok(C) else 'does not meet'}",
         f"  FIT  {stats(F)}", f"  CHECK {stats(C)}",
         f"  LATE (final 30 min, own split): {stats([x for x in S if x['late']])}"]
    for k in ("L", "P"):
        L.append(f"  Type {k}: {stats([x for x in J if x['kind'] == k])}")
    # Muse 15:52: PRIMARY buckets (may trigger the alert rule) and SECONDARY (refine only)
    L += ["", "PRIMARY BUCKETS (Muse 15:52) - each with FIT / CHECK:"]

    def fc(xs):
        f_, c_ = [x for x in xs if x["day"] <= mid], [x for x in xs if x["day"] > mid]
        return f"{stats(xs)}\n        FIT {stats(f_)}\n        CHECK {stats(c_)}" + ("   << HOLDS BOTH HALVES" if ok(f_) and ok(c_) and len(f_) >= 15 and len(c_) >= 15 else "")
    for typ in ("totals", "spreads", "moneyline"):
        L.append(f"  Market {typ}: " + fc([x for x in J if x["type"] == typ]))
    for sc in ("under", "over", "dog", "fav", "pick"):
        xs = [x for x in J if x.get("sclass") == sc]
        if xs:
            L.append(f"  Side {sc}: " + fc(xs))
    for typ, scs in (("totals", ("under", "over")), ("spreads", ("dog", "fav")), ("moneyline", ("dog", "fav"))):
        for sc in scs:
            xs = [x for x in J if x["type"] == typ and x.get("sclass") == sc]
            if xs:
                L.append(f"  {typ} x {sc}: " + fc(xs))
    for mins in (1, 5):
        L.append(f"  Still bettable at Hard Rock {mins} min after detection: " + fc([x for x in J if x.get(f"live{mins}")]))
        L.append(f"  Gone within {mins} min: " + fc([x for x in J if f"live{mins}" in x and not x.get(f"live{mins}")]))
    L += ["", "SECONDARY BUCKETS (refine only; cannot trigger the alert rule on their own):"]
    for kb in ("move crosses/lands on 3/7/10/14", "stale line on/next to a key number", "no key number"):
        xs = [x for x in J if x.get("key") == kb]
        if xs:
            L.append(f"  Football spreads, {kb}: {stats(xs)}")
    L.append(f"  Other books (exchanges) moved with Pinnacle: {stats([x for x in J if x.get('wide')])}")
    L.append(f"  Pinnacle moved alone: {stats([x for x in J if 'wide' in x and not x.get('wide')])}")
    L.append("    (#7 definition: books = Novig, ProphetX, Kalshi, Polymarket US. Window = 15 min before Pinnacle's move to the "
             "confirmation read. Type L: that exchange's closest-to-even number changed; Type P: its price on the bet side "
             "shortened >= 4c.)")
    # #11 (Muse 15:57): Pinnacle's raw limit at the move; cut = that league's median raw limit (stated)
    L.append("  #11 PINNACLE LIMIT WHEN IT MOVED (raw OddsPapi dollars; cut = league median over these sightings):")
    for lg in LEAGUES:
        xs = [x for x in J if x["league"] == lg and x.get("pin_limit")]
        if not xs:
            continue
        med = stt.median(x["pin_limit"] for x in xs)
        L.append(f"    {lg} cut {med:,.0f}: high {stats([x for x in xs if x['pin_limit'] > med])} | "
                 f"low {stats([x for x in xs if x['pin_limit'] <= med])}")
    # #12 (Muse 15:57): Hard Rock's price on the stale side
    L.append(f"  #12 Hard Rock stale price better than -110: {stats([x for x in J if sh.cents(x['hr_price']) > -10])}")
    L.append(f"  #12 Hard Rock stale price -110 or worse: {stats([x for x in J if sh.cents(x['hr_price']) <= -10])}")
    for lg in LEAGUES:
        for typ in ("totals", "spreads", "moneyline"):
            xs = [x for x in J if x["league"] == lg and x["type"] == typ]
            if xs:
                L.append(f"  {lg} {typ}: {stats(xs)}")
    # Peter 15:49: buckets by SIZE of Pinnacle's move (half point, full point, ...; price-move cents for Type P)
    import re

    def move_size(x):
        m = re.search(r"Pinnacle ([-+]?[0-9.]+) -> ([-+]?[0-9.]+)", x["detail"]) if x["kind"] == "L" else None
        if m:
            return abs(float(m.group(2)) - float(m.group(1)))
        m = re.search(r"\(([0-9.]+)c\)", x["detail"])
        return float(m.group(1)) if m else None
    for x in S:
        x["msize"] = move_size(x)
    L.append("  BY SIZE OF PINNACLE'S MOVE (Type L, points; Hard Rock still on the old number):")
    for lo, hi, lab in ((0.5, 1.0, "half point"), (1.0, 1.5, "1 point"), (1.5, 2.0, "1.5 points"), (2.0, 3.0, "2-2.5 points"), (3.0, 99, "3+ points")):
        xs = [x for x in J if x["kind"] == "L" and x.get("msize") is not None and lo - 1e-9 <= x["msize"] < hi - 1e-9]
        L.append(f"    {lab:<12}: {stats(xs)}")
        for lg in LEAGUES:
            ys = [x for x in xs if x["league"] == lg]
            if ys:
                L.append(f"        {lg}: {stats(ys)}")
    L.append("  BY SIZE OF PINNACLE'S MOVE (Type P, cents; same number, Hard Rock price within 2c):")
    for lo, hi, lab in ((8, 12, "8-11c"), (12, 20, "12-19c"), (20, 30, "20-29c"), (30, 999, "30c+")):
        xs = [x for x in J if x["kind"] == "P" and x.get("msize") is not None and lo <= x["msize"] < hi]
        L.append(f"    {lab:<12}: {stats(xs)}")
        for lg in LEAGUES:
            ys = [x for x in xs if x["league"] == lg]
            if ys:
                L.append(f"        {lg}: {stats(ys)}")
    L.append("  BY MINUTES BEFORE START:")
    for lo, hi in ((30, 120), (120, 360), (360, 1440), (1440, 99999)):
        xs = [x for x in J if lo <= x["mins_before"] < hi]
        L.append(f"    {lo // 60 if lo >= 60 else lo}{'h' if lo >= 60 else 'm'}-{(str(hi // 60) + 'h') if hi < 99999 else '+'}: {stats(xs)}")
    for lo, hi in ((2, 4), (4, 8), (8, 99)):
        xs = [x for x in J if x.get("ev_pct") is not None and lo <= x["ev_pct"] < hi]
        L.append(f"  EV vs Pinnacle fair at sighting {lo}-{hi if hi < 99 else '+'}%: {stats(xs)}")
    mb = [x["mins_before"] for x in J]
    if mb:
        L.append(f"  Minutes before start (median): {stt.median(mb):.0f}")
    def _b(x):
        mk, ln_ = x["type"], x.get("line")
        if mk == "spreads" and ln_ is not None and x.get("side") == "2":
            ln_ = -ln_
        return {"day": x["day"], "clv": x.get("clv_pct"), "lg": x["league"], "mk": mk,
                "sc": x.get("sclass") if x.get("sclass") in ("under", "over", "fav", "dog") else None,
                "key": bkt.key_class(x["league"], mk, ln_), "move": x.get("kind"),
                "ldelta": bkt.ldelta_from_detail(x.get("detail")) if x.get("kind") == "L" else None,
                "live1": x.get("live1"), "live5": x.get("live5"), "wide": x.get("wide"), "pin_limit": x.get("pin_limit"),
                "lead": x.get("mins_before"), "late": x.get("late"), "edge": x.get("ev_pct"), "am": x.get("hr_am")}
    L += [""] + bkt.section("SLOW-HR sightings at the Hard Rock price (CLV %)", [_b(x) for x in S], "%")
    L += ["", "NEWEST 25 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-25:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {x['league']} {x['game']} | {x['type']} {x['team']} {x['line'] if x['line'] is not None else ''} | "
                 f"HR {x['hr_am']:+d} | {x['detail']} | Type {x['kind']}{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start"
                 + (f" | Pin limit {x['pin_limit']:,.0f}" if x.get("pin_limit") else "")
                 + (f" | CLV {x['clv_cents']:+.2f}c" if x.get("clv_cents") is not None else ""))
    L += ["", f"Calls: {len(cl.CALLS)} (billable {cl.STATS['billable']})"]
    ex.send("Bets SLOW-HR BACKTEST (HYPOTHESIS)", "\n".join(L))
    print(f"slow-hr backtest: games {games}, sightings {len(S)}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()
