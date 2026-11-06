#!/usr/bin/env python3
"""
EXCHANGE-LAG STUDY (Nov 2, 2026; Peter yes 12:32 ET). Paper / measurement only: nothing here places, alerts or
changes a bet. The SLOW-HR registered test, aimed at the exchanges Peter is not limited on.

Source: OddsPapi free history (/historical-odds, 3 books per call), Pinnacle plus Novig, ProphetX, Kalshi and
Polymarket US, for every started NBA / NFL / NCAAF / NHL game from WINDOW_FROM (Oct 12: the history depth).
Sighting test per exchange = slow_hr.sightings() unchanged (SLOW-HR registered L / P definitions, persistence 3 min,
confirmation read at +5 min), with the exchange in Hard Rock's place:
  Type L = Pinnacle's main line moves >= 0.5 while the exchange's most even line is still the old number.
  Type P = same line, Pinnacle's price moves >= 8c within 15 min while the exchange's price on that side stays within
           2c of its pre-move price.
Grade: CLV vs Pinnacle's no-vig close at that line. Shown raw (cents of probability, as SLOW-HR) and AFTER FEES
(close chance x after-fee decimal - 1, in %). Fees (Muse registration 12:50): ProphetX 2% of winnings; Kalshi
0.07 x P x (1 - P) per contract; Polymarket US = the executor's taker model 0.0695 x P x (1 - P) per contract (today's
Pistons fill: screen -117, after-fee -126); Novig none. DEPTH IS NOT CHECKED: a stale quote may have had no size behind it, so any
pass needs the gettable-price audit before bot use.
Split: FIT = first half of the window by date, CHECK = second half. Bar shown (proposed, pending Muse): >= 100
sightings, avg after-fee CLV > 0 and beat-close >= 53%, in both halves.
Billable: /fixtures once per league for the window, then at most daily for new games. Encrypted state
(exlag/state.enc); private email; the log prints counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import buckets as bkt
import finals as fin
import executor as ex
import hist_cache as hc
import slowhr_backtest as sbt
import slow_hr as sh
import tracker_build as tb

ET = tb.ET
STATE = "exlag/state.enc"
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("novig.us", "prophetx", "kalshi", "polymarket.us")
NAME = {"novig.us": "Novig", "prophetx": "ProphetX", "kalshi": "Kalshi", "polymarket.us": "Polymarket US"}
WINDOW_FROM = datetime.fromisoformat(os.environ.get("EXLAG_FROM", "") or "2026-10-12").replace(tzinfo=timezone.utc)
MAX_GAMES = int(os.environ.get("EXLAG_MAX", "") or "300")


def eff(book, dec):
    """After-fee decimal: what $1 staked pays back."""
    if book == "prophetx":
        return 1 + (dec - 1) * 0.98
    if book in ("kalshi", "polymarket.us"):
        p = 1 / dec
        return 1 / (p * (1 + (0.07 if book == "kalshi" else ex.PMUS_FEE) * (1 - p)))
    return dec


def raw_for(book, net_dec, lo=1.0001, hi=200.0):
    """The RAW price this venue must SHOW so that, after its fee, we net net_dec.

    Peter, Nov 6: "post clv net fees and add to the price for those exchanges". One CLV basis - net
    of fees, so every venue is apples-to-apples - and the fee expressed as a price REQUIREMENT per
    venue, which is actionable at the order level instead of being a footnote on the number.

    The add is NOT a constant and must never be hard-coded: Kalshi and Polymarket are p x (1-p)
    shaped (1.7% of the decimal at -300, 3.4% at even money, 5.2% at +300) while ProphetX is a flat
    2% of winnings and so moves the OTHER way, growing as the price shortens. This inverts eff()
    numerically, so it stays correct for whatever eff() says and needs no separate fee table.

    Worked, at -110 net: ProphetX -108, Kalshi -103, Polymarket -103. At -104 net, Kalshi needs
    +103 - near even money the 7% is large enough that Kalshi and Polymarket fall out of contention
    on arithmetic alone, with no rule needed to exclude them.
    """
    if net_dec is None or net_dec <= 1:
        return None
    if eff(book, net_dec) >= net_dec - 1e-12:      # no fee at this venue: the raw price IS the net
        return net_dec
    for _ in range(200):                           # eff() is monotonic in dec, so bisection is exact enough
        mid = (lo + hi) / 2
        if eff(book, mid) < net_dec:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def size_at(xm, mkmap, lg, x, when):
    """Nov 3 (Peter yes: size check): OddsPapi's 'limit' on the exchange tick for this side at that time, or None."""
    sid = cl.SPORT.get(lg)
    typ, name = x.get("type"), str(x.get("side"))
    if sid is None:
        return None
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in xm:
            continue
        if typ != "moneyline" and (x.get("line") is None or abs(hcap - x["line"]) > 1e-9):
            continue
        if typ == "moneyline" and mid != cl.ML_MARKET.get(sid):
            continue
        oid = {v: k for k, v in outs.items()}.get(name)
        m = (xm.get(mid) or {}).get("outcomes", {}).get(oid) or {}
        lt = cl.last_tick((m.get("players") or {}).get("0"), when)
        if lt:
            return tb.num(lt[1].get("limit"))
    return None


def size_fill(st, mkmap):
    """Fill x['size'] on stored sightings from the shared history cache only (never downloads)."""
    by = {}
    for x in st["sightings"]:
        if "size_checked" not in x:
            by.setdefault(x.get("fixture"), []).append(x)
    n = 0
    for fid, xs in by.items():
        books = sorted({x["book"] for x in xs})
        if not fid or not all(os.path.exists(hc._path(fid, b)) for b in books):
            continue
        h = hc.get_hist(fid, books, cl.tp(xs[0].get("start")))
        if isinstance(h, dict) and h.get("_error"):
            continue
        for x in xs:
            try:
                x["size"] = size_at(cl.book_markets(h, x["book"]), mkmap, x["league"], x, cl.tp(x["t_confirm"]))
            except Exception:
                x["size"] = None
            x["size_checked"] = True
            n += 1
    return n


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY or not tb.PASS:
        print("exchange lag: ODDSPAPI_KEY or TRACKER_PASSPHRASE not set; skipped")
        return
    try:
        st = tb.dec(json.load(open(STATE)))
    except Exception:
        st = {}
    if st.get("v") != "x1":
        st = {"v": "x1"}
    for k in ("done", "fixtures", "fx_last", "billable"):
        st.setdefault(k, {})
    st.setdefault("sightings", [])
    for x in st["sightings"]:   # re-price every sighting with the current fee model (Muse 12:50: PM US is not 0 fee)
        if x.get("close_fair") is not None:
            x["clv_af"] = round(100 * (x["close_fair"] * eff(x["book"], x["hr_price"]) - 1), 2)
    mkmap = cl.load_markets(st, now)
    for lg in LEAGUES:
        init = st.get("init_" + lg)
        if not init:
            st["fx_last"].pop(lg, None)
            cl.refresh_fixtures(st, now, lg, (WINDOW_FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=2)).astimezone(ET))
            if st["fx_last"].get(lg):
                st["init_" + lg] = cl.iso(now)
        elif now - cl.tp(st["fx_last"].get(lg) or init) > timedelta(hours=20):
            st["fx_last"].pop(lg, None)
            cl.refresh_fixtures(st, now, lg, (now - timedelta(days=3)).astimezone(ET), (now + timedelta(days=2)).astimezone(ET))
    todo = []
    for fid, f in st["fixtures"].items():
        s = cl.tp(f.get("start"))
        if f.get("lg") in LEAGUES and s and WINDOW_FROM <= s <= now - timedelta(minutes=10) and fid not in st["done"]:
            todo.append((s, fid, f))
    todo.sort()
    sh.FLOOR = WINDOW_FROM
    new = 0
    for s, fid, f in todo[:MAX_GAMES]:
        h1 = h2 = hc.get_hist(fid, ["pinnacle", "novig.us", "prophetx", "kalshi", "polymarket.us"], s)   # shared cache
        if isinstance(h1, dict) and h1.get("_error"):
            continue
        pin = cl.book_markets(h1, "pinnacle")
        if not pin:
            st["done"][fid] = cl.iso(now)
            continue
        f2 = {"participant1Name": f.get("n1"), "participant2Name": f.get("n2")}
        for bk in EXCH:
            xm = cl.book_markets(h1 if bk in ("novig.us", "prophetx") else h2, bk)
            if not xm:
                continue
            st.setdefault("coverage", {}).setdefault(f"{f['lg']}|{bk}", 0)
            st["coverage"][f"{f['lg']}|{bk}"] += 1
            for x in sh.sightings(fid, f2, f["lg"], pin, xm, mkmap, s):
                x["book"] = bk
                x["day"] = s.astimezone(ET).strftime("%Y-%m-%d")
                try:   # standard bucket fields (BUCKETS.md): side class, key numbers, still up +1/+5, market-wide, Pinnacle limit
                    sbt.enrich(x, f["lg"], pin, xm, h1, mkmap, s)
                except Exception:
                    pass
                if x.get("close_fair") is not None:
                    x["clv_af"] = round(100 * (x["close_fair"] * eff(bk, x["hr_price"]) - 1), 2)
                st["sightings"].append(x)
                new += 1
        st["done"][fid] = cl.iso(now)
    sized = size_fill(st, mkmap)
    print(f"exchange lag: size checked on {sized} sightings (cache only)")   # counts only
    report(st, now, len(todo[:MAX_GAMES]), len(todo), new)
    os.makedirs("exlag", exist_ok=True)
    json.dump(tb.enc(st), open(STATE, "w"))
    print(f"exchange lag: games {len(todo[:MAX_GAMES])} of {len(todo)} waiting, sightings +{new} "
          f"(total {len(st['sightings'])}), calls {len(cl.CALLS)}")   # counts only


def stats(xs):
    c = [x["clv_cents"] for x in xs if x.get("clv_cents") is not None]
    a = [x["clv_af"] for x in xs if x.get("clv_af") is not None]
    if not a:
        return f"n {len(xs)}"
    return (f"n {len(xs)} | CLV {sum(c) / len(c):+.2f}c raw | after fees {sum(a) / len(a):+.2f}% | "
            f"beat close {sum(1 for v in a if v > 0)}/{len(a)} ({100 * sum(1 for v in a if v > 0) / len(a):.0f}%)")


def report(st, now, read, waiting, new):
    S0 = st["sightings"]
    # Nov 3 (Muse): a quote implying more than +15% vs Pinnacle's close is a misread / crossed book, not a fill (same rule
    # as p1_backtest). Dropped from every line below and counted here.
    S = [x for x in S0 if not (x.get("clv_af") is not None and x["clv_af"] > 15)]
    dropped = {bk: sum(1 for x in S0 if x["book"] == bk and x.get("clv_af") is not None and x["clv_af"] > 15) for bk in EXCH}
    days = sorted({x["day"] for x in S})
    mid = days[(len(days) - 1) // 2] if days else ""
    L = [f"EXCHANGE-LAG STUDY (paper; OddsPapi history; Pinnacle vs Novig / ProphetX / Kalshi / Polymarket US; "
         f"NBA/NFL/NCAAF/NHL from {WINDOW_FROM.date()})",
         "Test = SLOW-HR registered L/P (persist 3 min + confirm at +5) with the exchange in Hard Rock's place.",
         "CLV vs Pinnacle no-vig close at that line; after fees: ProphetX 2% of winnings, Kalshi 0.07xPx(1-P), Polymarket US 0.0695xPx(1-P), Novig 0.",
         "DEPTH NOT CHECKED: a stale quote may have had no size. Any pass needs the gettable-price audit before bot use.",
         f"FIT = sightings on game days <= {mid}; CHECK = after. Bar (proposed): >= 100, after-fee CLV > 0, beat close >= 53%, both halves.",
         "Suspect quotes dropped (> +15% vs the close): " + ", ".join(f"{NAME[k]} {v}" for k, v in dropped.items()),
         "", f"This run: {read} games read ({waiting - read} still waiting), sightings +{new}. Games done: {len(st['done'])}.",
         "Coverage (games with that exchange in history): " + ", ".join(f"{k} {v}" for k, v in sorted((st.get("coverage") or {}).items())),
         "", "BY EXCHANGE (not LATE):"]
    for bk in EXCH:
        xs = [x for x in S if x["book"] == bk and not x["late"]]
        fit, chk = [x for x in xs if x["day"] <= mid], [x for x in xs if x["day"] > mid]

        def ok(v):
            a = [x["clv_af"] for x in v if x.get("clv_af") is not None]
            return bool(a) and sum(a) / len(a) > 0 and sum(1 for z in a if z > 0) / len(a) >= 0.53
        bar = "MEETS BAR" if len(xs) >= 100 and ok(fit) and ok(chk) else "does not meet bar"
        L += [f"{NAME[bk]}: {stats(xs)} | {bar}", f"   FIT {stats(fit)}", f"   CHECK {stats(chk)}"]
        for lg in LEAGUES:
            for kind in ("L", "P"):
                v = [x for x in xs if x["league"] == lg and x["kind"] == kind]
                if v:
                    L.append(f"   {lg} type {kind}: {stats(v)}")
        lt = [x for x in S if x["book"] == bk and x["late"]]
        if lt:
            L.append(f"   LATE (final 30 min, own split): {stats(lt)}")
    L += ["", "SIZE AT THE STALE QUOTE (Nov 3; OddsPapi 'limit' on the exchange's own tick at the +5-min confirm; not LATE):"]
    for bk in EXCH:
        xs = [x for x in S if x["book"] == bk and not x["late"] and x.get("size_checked")]
        for lo, hi, lab in ((None, None, "no size shown"), (0, 100, "under 100"), (100, 500, "100-499"), (500, 10 ** 12, "500+")):
            v = [x for x in xs if (x.get("size") is None if lo is None else (x.get("size") is not None and lo <= x["size"] < hi))]
            if v:
                u = [fin.units(x, eff(bk, x["hr_price"])) for x in v if x.get("hr_price")]
                u = [z for z in u if z is not None]
                L.append(f"   {NAME[bk]} size {lab}: {stats(v)}" + (f" | units {sum(u):+.2f}u ({len(u)} graded)" if u else ""))

    # Nov 3 (Peter "get everything done now"; Muse): the stale edge sits largely on ALT lines at extreme prices. Split every
    # exchange by price band (main = screen price -135..+125; long = above +125; heavy = below -135) x size shown, with units.
    L += ["", "PRICE BAND x SIZE AT THE STALE QUOTE (not LATE; screen American price at the stale quote; size = OddsPapi limit at the confirm):"]

    def _pb(x):
        am = x.get("hr_am")
        if am is None:
            return None
        return "main (-135..+125)" if -135 <= am <= 125 else ("long (+126 or more)" if am > 125 else "heavy (-136 or less)")
    for bk in EXCH:
        xs = [x for x in S if x["book"] == bk and not x["late"]]
        for band in ("main (-135..+125)", "long (+126 or more)", "heavy (-136 or less)"):
            v = [x for x in xs if _pb(x) == band]
            if not v:
                continue
            for lab, w in (("any size", v), ("size 100-499", [x for x in v if x.get("size") is not None and 100 <= x["size"] < 500]),
                           ("size 500+", [x for x in v if x.get("size") is not None and x["size"] >= 500])):
                if not w:
                    continue
                u = [fin.units(x, eff(bk, x["hr_price"])) for x in w if x.get("hr_price")]
                u = [z for z in u if z is not None]
                fit, chk = [x for x in w if x["day"] <= mid], [x for x in w if x["day"] > mid]
                L.append(f"   {NAME[bk]} {band} {lab}: {stats(w)}" + (f" | units {sum(u):+.2f}u ({len(u)} graded)" if u else "")
                         + f" || FIT {stats(fit)} || CHECK {stats(chk)}")
            for typ in ("spreads", "moneyline", "totals"):
                w = [x for x in v if x["type"] == typ]
                if w:
                    u = [fin.units(x, eff(bk, x["hr_price"])) for x in w if x.get("hr_price")]
                    u = [z for z in u if z is not None]
                    L.append(f"      {typ}: {stats(w)}" + (f" | units {sum(u):+.2f}u" if u else ""))

    def _b(x):
        mk, ln_ = x["type"], x.get("line")
        if mk == "spreads" and ln_ is not None and x.get("side") == "2":
            ln_ = -ln_
        return {"day": x["day"], "clv": x.get("clv_af"), "lg": x["league"], "mk": mk,
                "sc": x.get("sclass") if x.get("sclass") in ("under", "over", "fav", "dog") else bkt.side_class(mk, x.get("side"), ln_),
                "key": bkt.key_class(x["league"], mk, ln_), "move": x.get("kind"),
                "ldelta": bkt.ldelta_from_detail(x.get("detail")) if x.get("kind") == "L" else None,
                "live1": x.get("live1"), "live5": x.get("live5"), "wide": x.get("wide"), "pin_limit": x.get("pin_limit"),
                "lead": x.get("mins_before"), "late": x.get("late"), "am": x.get("hr_am"),
                "units": fin.units(x, eff(x["book"], x["hr_price"]) if x.get("hr_price") else None)}   # Nov 3: ESPN final, flat 1u after fees
    L.append("(Sightings stored before Nov 2 lack still-up / market-wide / limit fields: those buckets cover new sightings only.)")
    for bx in EXCH:
        L += [""] + bkt.section(f"{NAME[bx]} slow quotes (CLV % after fees)", [_b(x) for x in S if x["book"] == bx], "%")
    # Nov 3 20:55 (Peter: "beat clv both half and constant losers - that doesnt look right"): DATA CHECK. If the close is right
    # and the grading is right, wins should track the Pinnacle close win chance. Wins far below it = a side / line / match error.
    try:   # the data check must never cost the rest of the report
        L += ["", "DATA CHECK - wins vs the close's own win chance (not LATE, graded, no push; z = (wins - expected) / sd):"]

        def _cal(xs):
            g = []
            for x in xs:
                if x.get("close_fair") is None or not x.get("hr_price"):
                    continue
                r = fin.result(x)
                if r in ("W", "L"):
                    g.append((x, r))
            if not g:
                return "graded 0", g
            w = sum(1 for _, r in g if r == "W")
            ex_ = sum(x["close_fair"] for x, _ in g)
            sd = sum(x["close_fair"] * (1 - x["close_fair"]) for x, _ in g) ** 0.5 or 1
            eu = sum(x["close_fair"] * eff(x["book"], x["hr_price"]) - 1 for x, _ in g)
            au = sum((eff(x["book"], x["hr_price"]) - 1) if r == "W" else -1.0 for x, r in g)
            return (f"graded {len(g)} | wins {w} vs expected {ex_:.1f} (z {(w - ex_) / sd:+.1f}) | "
                    f"units {au:+.2f}u vs expected {eu:+.2f}u"), g
        cells = []
        for bk in ("novig.us", "prophetx", "polymarket.us", "kalshi"):
            base = [x for x in S if x["book"] == bk and not x["late"]]
            bb_ = [(x, _b(x)) for x in base]
            cells += [(f"{NAME[bk]} all", base),
                      (f"{NAME[bk]} spreads x fav", [x for x, b in bb_ if b["mk"] == "spreads" and b["sc"] == "fav"]),
                      (f"{NAME[bk]} spreads x dog", [x for x, b in bb_ if b["mk"] == "spreads" and b["sc"] == "dog"]),
                      (f"{NAME[bk]} moneyline x dog", [x for x, b in bb_ if b["mk"] == "moneyline" and b["sc"] == "dog"]),
                      (f"{NAME[bk]} moneyline x fav", [x for x, b in bb_ if b["mk"] == "moneyline" and b["sc"] == "fav"]),
                      (f"{NAME[bk]} totals", [x for x, b in bb_ if b["mk"] == "totals"]),
                      (f"{NAME[bk]} price better than -110", [x for x in base if (x.get("hr_am") or -999) > -110]),
                      # Nov 3 21:20 (EV-lane audit: Polymarket US suspect gains sit on ALTERNATE lines - a misread line/side
                      # risk): main-price band (-135..+125) vs off-band (alternate-line prices) side by side
                      (f"{NAME[bk]} main price band -135..+125", [x for x in base if -135 <= (x.get("hr_am") or 0) <= 125]),
                      (f"{NAME[bk]} off-band (+126 or more / -136 or less)", [x for x in base if not -135 <= (x.get("hr_am") or 0) <= 125])]
        samp = []
        for nm, xs in cells:
            txt, g = _cal(xs)
            L.append(f"   {nm}: {txt}")
            if nm.endswith("better than -110") and not samp:
                samp = g
        L += ["", "HAND-CHECK SAMPLE (Novig, price better than -110; every 15th graded sighting, oldest first):"]
        for x, r in sorted(samp, key=lambda z: z[0]["start"])[::15][:20]:
            gm, p1h = fin.find(x["league"], x["game"], x["start"])
            sc = (f"ESPN away {gm['away'].get('abbr')} {gm['away'].get('pts')} - home {gm['home'].get('abbr')} {gm['home'].get('pts')}, "
                  f"participant 1 is {'home' if p1h else 'away'}") if gm else "ESPN not found"
            L.append(f"   {x['start'][:10]} {x['league']} {x['game']} | {x['type']} side {x['side']} ({x['team']}) line {x['line']} | "
                     f"price {x['hr_am']:+d} | close fair {x['close_fair']:.3f} | result {r} | {sc}")
    except Exception as e_:
        L.append(f"   DATA CHECK failed: {type(e_).__name__}: {str(e_)[:120]}")
    L += ["", "NEWEST 25 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-25:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {NAME[x['book']]} {x['league']} {x['game']} | {x['type']} {x['team']} "
                 f"{x['line'] if x['line'] is not None else ''} | {x['hr_am']:+d} | {x['detail'].replace('Hard Rock', NAME[x['book']])} | "
                 f"Type {x['kind']}{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start"
                 + (f" | after-fee CLV {x['clv_af']:+.2f}%" if x.get("clv_af") is not None else ""))
    L += ["", f"Calls this run: {len(cl.CALLS)} (billable {cl.STATS['billable']}); history cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}"]
    ex.send(f"Bets EXCHANGE-LAG STUDY {now.astimezone(ET).strftime('%Y-%m-%d %H:%M')}", "\n".join(L))


if __name__ == "__main__":
    main()
