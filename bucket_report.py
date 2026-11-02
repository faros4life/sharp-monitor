#!/usr/bin/env python3
"""
BUCKET REPORT (Nov 2, 2026; Peter 16:07-16:08: "test the new bucket set on all the data and plays we already have" -
"paper, liquidity, ntfy, EV, etc."). HYPOTHESIS ONLY - reads stored records, makes no OddsPapi calls.

Applies the standard bucket list (BUCKETS.md) to every graded record we already hold, source by source (CLV units differ
between sources, so sources are never pooled):
  EV study sightings (A / B / M triggers; ev-study branch)   - CLV vs Pinnacle close, cents
  EV maker posts                                              - CLV vs Pinnacle close, cents
  Liquidity board rows (liquidity/alerts.json)                - the monitor's own CLV, cents
  Liquidity-extra rows                                        - same
  ntfy sharp alerts (alerts.json)                             - beat-close flag (CLV text is mixed pts / %)
  CLV ledger bets: bot / ntfy played / Street Value / Peter   - CLV vs Pinnacle close, %, after fees (encrypted state)
Buckets that a source cannot support (no field) are printed as "not in this source".
FIT = first half of dates, CHECK = second half (per source). HOLDS = >= 15 per half, CLV > 0 and beat-close >= 53% in both.
Private email; the log prints counts only.
"""
import json
import os
import re
import statistics as stt
from datetime import datetime, timezone

import clv_ledger as cl
import executor as ex
import tracker_build as tb

ET = tb.ET
KEYS = (3, 7, 10, 14)


def load(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def day(s):
    t = tb.tparse(s)
    return t.astimezone(ET).strftime("%Y-%m-%d") if t else None


def mins(a, b):
    ta, tb_ = tb.tparse(a), tb.tparse(b)
    return round((tb_ - ta).total_seconds() / 60) if ta and tb_ else None


def p_to_am(p):
    if not p or not 0 < p < 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def norm(source, lg, market, side, line, am, lead, d, clv, beat=None, **extra):
    """One graded record in the common shape."""
    mk = {"total": "totals", "spread": "spreads", "spr": "spreads", "tot": "totals", "ml": "moneyline", "h2h": "moneyline"}.get(market, market)
    s = str(side or "")
    if mk == "totals":
        sc = "under" if s.upper().startswith("UNDER") or "NOT OVER" in s.upper() else ("over" if s.upper().startswith("OVER") else None)
    elif mk == "spreads" and line is not None:
        sc = "pick" if line == 0 else ("fav" if line < 0 else "dog")
    else:
        sc = None   # moneyline: fav / dog by points needs the spread; not in these records (never by price sign)
    key = None
    if mk == "spreads" and lg in ("NFL", "NCAAF") and line is not None:
        key = "on/next to 3/7/10/14" if any(abs(abs(line) - k) <= 0.5 for k in KEYS) else "no key number"
    r = {"src": source, "lg": lg, "mk": mk, "sc": sc, "line": line, "am": am, "lead": lead, "day": d, "clv": clv,
         "beat": (clv > 0) if (beat is None and clv is not None) else beat, "key": key}
    r.update(extra)
    return r


def ev_rows():
    d = load("ev-study/ev_sightings.json", {}) or {}
    out = []
    for s in d.get("sightings") or []:
        if s.get("clv_pinnacle_c") is None:
            continue
        fs, ls = tb.tparse(s.get("first_seen_utc")), tb.tparse(s.get("last_seen_utc"))
        alive = (ls - fs).total_seconds() / 60 if fs and ls else None
        out.append(norm(f"EV study trigger {s.get('trigger')}", s.get("league"), s.get("market"), s.get("side") if s.get("market") != "total" else s.get("side"),
                        s.get("line"), s.get("sighting_american_af"), s.get("lead_min"), day(s.get("sighted_utc")), s.get("clv_pinnacle_c"),
                        edge=s.get("ev_pct"), alive=alive, move=s.get("move_type"), ldelta=s.get("line_delta"), pdelta=s.get("price_delta_cents"),
                        nbooks=s.get("n_books")))
    for m in d.get("maker") or []:
        if m.get("clv_pinnacle_c") is None:
            continue
        out.append(norm("EV maker posts", m.get("league"), m.get("market"), m.get("side"), m.get("line"), p_to_am(m.get("bid_screen")),
                        m.get("lead_min"), day(m.get("posted_utc")), m.get("clv_pinnacle_c")))
    return out


def board_rows(path, label):
    a = load(path, []) or []
    a = a if isinstance(a, list) else a.get("alerts") or []
    out = []
    for r in a:
        if r.get("clv_cents") is None or r.get("artifact"):
            continue
        out.append(norm(label, r.get("league"), r.get("market"), r.get("side"), tb.num(r.get("line")), r.get("price_american"),
                        mins(r.get("alerted_utc"), r.get("start_utc")), day(r.get("alerted_utc")), float(r["clv_cents"])))
    return out


def ntfy_rows():
    a = (load("alerts.json", {}) or {}).get("alerts") or []
    out = []
    for x in a:
        if x.get("beat_close") is None:
            continue
        bet = x.get("bet") or ""
        m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*\(", bet)
        line = float(m.group(1)) if m else tb.num(x.get("point"))
        side = bet.split(" ")[0] if x.get("kind") == "tot" else bet
        cv = re.match(r"([+-]?\d+(?:\.\d+)?)", str(x.get("clv") or ""))
        out.append(norm("ntfy sharp alerts", x.get("sport"), x.get("kind"), side, line if x.get("kind") != "ml" else None, x.get("price_after_fee"),
                        x.get("minutes_before_start") or mins(x.get("alert_utc"), x.get("start_utc")), day(x.get("alert_utc")),
                        float(cv.group(1)) if cv else None, beat=bool(x.get("beat_close")), edge=x.get("edge_pct"),
                        clv_unit="pts / % mixed (beat-close is the comparable figure)"))
    return out


def ledger_rows():
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception:
        return []
    try:
        sv = cl.sv_registry()
    except Exception:
        sv = []
    out = []
    for k, rec in (st.get("bets") or {}).items():
        if rec.get("clv") is None:
            continue
        s = rec.get("snap") or {}
        pz = cl.parsed(s)
        if not pz:
            continue
        mk = {"total": "totals", "spread": "spreads", "ml": "moneyline"}[pz[0]]
        side = pz[1]
        line = pz[2]
        if mk == "spreads" and line is not None and len(pz) > 3 and pz[3]:
            line = -line   # NO / short side holds the other team at the opposite number
        lane = cl.lane_of(s, sv)
        d = cl.eff_dec(s)
        am = cl.dec_to_am(d) if d else None
        out.append(norm(f"CLV ledger - {lane}", s.get("league"), mk, side, line, am,
                        mins(s.get("placed"), s.get("game_start")), day(s.get("game_start")), round(100 * rec["clv"], 2),
                        clv_unit="%"))
    return out


def stats(xs):
    c = [x["clv"] for x in xs if x.get("clv") is not None]
    b = [x["beat"] for x in xs if x.get("beat") is not None]
    out = f"n {len(xs)}"
    if c:
        out += f" | CLV {stt.mean(c):+.2f}"
    if b:
        out += f" | beat close {sum(b)}/{len(b)} ({100 * sum(b) / len(b):.0f}%)"
    return out


def ok(xs):
    c = [x["clv"] for x in xs if x.get("clv") is not None]
    b = [x["beat"] for x in xs if x.get("beat") is not None]
    good_c = (stt.mean(c) > 0) if c else True
    return bool(b) and good_c and sum(b) / len(b) >= 0.53


def report_source(name, R):
    days = sorted({r["day"] for r in R if r["day"]})
    mid = days[(len(days) - 1) // 2] if days else ""
    L = [f"=== {name} === ({len(R)} graded; {days[0] if days else '-'} to {days[-1] if days else '-'}; FIT <= {mid} < CHECK)",
         f"  ALL: {stats(R)}"]

    def line(lab, xs, primary=False):
        f_, c_ = [x for x in xs if x["day"] and x["day"] <= mid], [x for x in xs if x["day"] and x["day"] > mid]
        hold = primary and len(f_) >= 15 and len(c_) >= 15 and ok(f_) and ok(c_)
        L.append(f"  {lab}: {stats(xs)} | FIT {stats(f_)} | CHECK {stats(c_)}" + ("   << HOLDS BOTH HALVES" if hold else ""))
    L.append(" PRIMARY")
    for mk in ("totals", "spreads", "moneyline"):
        xs = [r for r in R if r["mk"] == mk]
        if xs:
            line(f"Market {mk}", xs, True)
    for mk, scs in (("totals", ("under", "over")), ("spreads", ("dog", "fav"))):
        for sc in scs:
            xs = [r for r in R if r["mk"] == mk and r["sc"] == sc]
            if xs:
                line(f"{mk} x {sc}", xs, True)
    if any("alive" in r for r in R):
        for m_ in (1, 5):
            xs = [r for r in R if r.get("alive") is not None and r["alive"] >= m_]
            line(f"Still up >= {m_} min after sighting", xs, True)
            line(f"Gone within {m_} min", [r for r in R if r.get("alive") is not None and r["alive"] < m_], True)
    else:
        L.append("  Still bettable +1 / +5 min: not in this source")
    L.append(" SECONDARY")
    if any(r.get("move") for r in R):
        for mv in sorted({r.get("move") for r in R if r.get("move")}):
            line(f"Move type {mv}", [r for r in R if r.get("move") == mv])
        for lo, hi, lab in ((0.25, 1.0, "half point"), (1.0, 1.5, "1 point"), (1.5, 2.0, "1.5 points"), (2.0, 3.0, "2-2.5 pts"), (3.0, 99, "3+ pts")):
            xs = [r for r in R if r.get("ldelta") is not None and lo <= abs(r["ldelta"]) < hi]
            if xs:
                line(f"Line move {lab}", xs)
        for lo, hi in ((0.1, 8), (8, 12), (12, 20), (20, 30), (30, 999)):
            xs = [r for r in R if not r.get("ldelta") and r.get("pdelta") is not None and lo <= abs(r["pdelta"]) < hi]
            if xs:
                line(f"Price move {lo:g}-{hi if hi < 999 else '+'}c", xs)
    else:
        L.append("  Move type / move size: not in this source")
    for kb in ("on/next to 3/7/10/14", "no key number"):
        xs = [r for r in R if r.get("key") == kb]
        if xs:
            line(f"Football spreads {kb}", xs)
    for lo, hi, lab in ((0, 30, "LATE (final 30 min)"), (30, 120, "30m-2h"), (120, 360, "2-6h"), (360, 1440, "6-24h"), (1440, 10 ** 7, "24h+")):
        xs = [r for r in R if r.get("lead") is not None and lo <= r["lead"] < hi]
        if xs:
            line(f"Time before start {lab}", xs)
    if any(r.get("edge") is not None for r in R):
        for lo, hi in ((-99, 2), (2, 4), (4, 8), (8, 999)):
            xs = [r for r in R if r.get("edge") is not None and lo <= r["edge"] < hi]
            if xs:
                line(f"Edge {lo if lo > -99 else '<'}{'-' + str(hi) if hi < 999 else '+'}%", xs)
    else:
        L.append("  Edge band: not in this source")
    for lg in sorted({r["lg"] for r in R if r["lg"]}):
        for mk in ("totals", "spreads", "moneyline"):
            xs = [r for r in R if r["lg"] == lg and r["mk"] == mk]
            if len(xs) >= 5:
                line(f"{lg} {mk}", xs)
    xs1 = [r for r in R if r.get("am") is not None and r["am"] > -110]
    xs2 = [r for r in R if r.get("am") is not None and r["am"] <= -110]
    if xs1 or xs2:
        line("Price better than -110", xs1)
        line("Price -110 or worse", xs2)
    L.append("  Pinnacle limit at the move / market-wide vs lone: not in these records (SLOW-HR / exchange-lag only)")
    return L


def main():
    now = datetime.now(timezone.utc)
    sources = {}
    for r in ev_rows() + board_rows("liquidity/alerts.json", "Liquidity board") + board_rows("liquidity-extra/alerts.json", "Liquidity extra") \
            + ntfy_rows() + ledger_rows():
        sources.setdefault(r["src"], []).append(r)
    L = [f"BUCKET REPORT - HYPOTHESIS ONLY | standard buckets (BUCKETS.md) on every graded record we hold | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Sources are never pooled (CLV units differ: EV / board = cents; ledger = %; ntfy = beat-close only).",
         "Fav / dog by POINTS (spreads); moneyline sides are not classed (no spread in these records). HOLDS = >= 15 per half, CLV > 0, beat >= 53%.",
         "Paper lanes (ml_stay / pull_fade / solo) carry no grade field yet: listed by count only.", ""]
    lanes = load("lanes/lanes.json", {}) or {}
    L.append("Paper lanes (counts only): " + ", ".join(f"{k} {len(v)}" for k, v in lanes.items() if isinstance(v, dict)))
    L.append("")
    for name in sorted(sources, key=lambda k: -len(sources[k])):
        L += report_source(name, sources[name]) + [""]
    ex.send("Bets BUCKET REPORT (HYPOTHESIS)", "\n".join(L))
    print(f"bucket report: sources {len(sources)}, records {sum(len(v) for v in sources.values())}")   # counts only


if __name__ == "__main__":
    main()
