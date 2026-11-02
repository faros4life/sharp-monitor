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
(close chance x after-fee decimal - 1, in %). Fee assumptions: ProphetX 2% of winnings; Kalshi 0.07 x P x (1 - P) per
contract; Novig and Polymarket US none. DEPTH IS NOT CHECKED: a stale quote may have had no size behind it, so any
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
import executor as ex
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
    if book == "kalshi":
        p = 1 / dec
        return 1 / (p * (1 + 0.07 * (1 - p)))
    return dec


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
        h1 = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle,novig.us,prophetx")
        h2 = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="kalshi,polymarket.us")
        if any(isinstance(h, dict) and h.get("_error") for h in (h1, h2)):
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
                if x.get("close_fair") is not None:
                    x["clv_af"] = round(100 * (x["close_fair"] * eff(bk, x["hr_price"]) - 1), 2)
                st["sightings"].append(x)
                new += 1
        st["done"][fid] = cl.iso(now)
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
    S = st["sightings"]
    days = sorted({x["day"] for x in S})
    mid = days[(len(days) - 1) // 2] if days else ""
    L = [f"EXCHANGE-LAG STUDY (paper; OddsPapi history; Pinnacle vs Novig / ProphetX / Kalshi / Polymarket US; "
         f"NBA/NFL/NCAAF/NHL from {WINDOW_FROM.date()})",
         "Test = SLOW-HR registered L/P (persist 3 min + confirm at +5) with the exchange in Hard Rock's place.",
         "CLV vs Pinnacle no-vig close at that line; after fees: ProphetX 2% of winnings, Kalshi 0.07xPx(1-P), Novig/Polymarket 0.",
         "DEPTH NOT CHECKED: a stale quote may have had no size. Any pass needs the gettable-price audit before bot use.",
         f"FIT = sightings on game days <= {mid}; CHECK = after. Bar (proposed): >= 100, after-fee CLV > 0, beat close >= 53%, both halves.",
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
    L += ["", "NEWEST 25 SIGHTINGS:"]
    for x in sorted(S, key=lambda x: x["t_move"])[-25:][::-1]:
        L.append(f"  {x['t_confirm'][:16]}Z {NAME[x['book']]} {x['league']} {x['game']} | {x['type']} {x['team']} "
                 f"{x['line'] if x['line'] is not None else ''} | {x['hr_am']:+d} | {x['detail'].replace('Hard Rock', NAME[x['book']])} | "
                 f"Type {x['kind']}{' LATE' if x['late'] else ''} | {x['mins_before']} min pre-start"
                 + (f" | after-fee CLV {x['clv_af']:+.2f}%" if x.get("clv_af") is not None else ""))
    L += ["", f"Calls this run: {len(cl.CALLS)} (billable {cl.STATS['billable']})"]
    ex.send(f"Bets EXCHANGE-LAG STUDY {now.astimezone(ET).strftime('%Y-%m-%d %H:%M')}", "\n".join(L))


if __name__ == "__main__":
    main()
