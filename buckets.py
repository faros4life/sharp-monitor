#!/usr/bin/env python3
"""
STANDARD BUCKETS (BUCKETS.md; Peter Nov 2 16:30: "i want all the buckets we made run on all tests").
One shared section printed at the end of every test's report so every model / backtest / audit is cut the same way.

Each record is a dict; a bucket whose field no record carries prints "not in this test" (never silently skipped):
  day   'YYYY-MM-DD' (FIT = first half of dates, CHECK = second half)     clv   CLV number (unit stated by the caller)
  beat  bool (optional; default clv > 0)                                    lg    league
  mk    'totals' | 'spreads' | 'moneyline'                                  sc    'under' | 'over' | 'fav' | 'dog' (by POINTS)
  live1 / live5  still bettable 1 / 5 min after detection (bool)            move  'L' (line moved) | 'P' (price only)
  ldelta points of the line move        pdelta cents of the price move      key   football key-number class (str)
  wide  other books moved with Pinnacle (bool)                              lead  minutes before start at detection
  late  bool (default lead < 30)        edge  % edge at detection           am    American price on the bet side
  pin_limit  Pinnacle's raw limit when it moved
PRIMARY buckets (1-3) can flag HOLDS (>= 15 per half, CLV > 0 and beat-close >= 53% in both). SECONDARY (4-12) refine only.
LATE (final 30 min) is graded on its own line and kept out of every other bucket.
"""
import statistics as stt

KEYS = (3, 7, 10, 14)
WIDE_DEF = ("#7 definition: other books = Novig, ProphetX, Kalshi, Polymarket US; window = 15 min before Pinnacle's move to the "
            "confirmation read; 'moved' = line changed, or price shortened >= 4c.")


def side_class(mk, side, line):
    """Over / under for totals; favorite / underdog BY POINTS from the bet side's own spread number. Moneyline: None
    unless the caller supplies the main spread (never by price sign)."""
    s = str(side or "").upper()
    if mk == "totals":
        return "under" if s.startswith("UNDER") or s.startswith("NOT OVER") else ("over" if s.startswith("OVER") else None)
    if mk == "spreads" and line is not None:
        return None if line == 0 else ("fav" if line < 0 else "dog")
    return None


def key_class(lg, mk, line):
    if mk != "spreads" or lg not in ("NFL", "NCAAF") or line is None:
        return None
    return "on/next to 3/7/10/14" if any(abs(abs(line) - k) <= 0.5 for k in KEYS) else "no key number"


def _beat(x):
    if x.get("beat") is not None:
        return bool(x["beat"])
    return None if x.get("clv") is None else x["clv"] > 0


def stats(xs, unit=""):
    c = [x["clv"] for x in xs if x.get("clv") is not None]
    b = [v for v in (_beat(x) for x in xs) if v is not None]
    out = f"n {len(xs)}"
    if c:
        out += f" | CLV {stt.mean(c):+.2f}{unit}"
    if b:
        out += f" | beat close {sum(b)}/{len(b)} ({100 * sum(b) / len(b):.0f}%)"
    u = [x["units"] for x in xs if x.get("units") is not None]   # Nov 3 (Peter): flat 1u result where a final score is known
    if u:
        out += f" | units {sum(u):+.2f}u ({sum(v > 0 for v in u)}-{sum(v < 0 for v in u)}, {len(u)} graded)"
    return out


def _ok(xs):
    c = [x["clv"] for x in xs if x.get("clv") is not None]
    b = [v for v in (_beat(x) for x in xs) if v is not None]
    return bool(b) and (stt.mean(c) > 0 if c else True) and sum(b) / len(b) >= 0.53


def _has(R, k):
    return any(x.get(k) is not None for x in R)


def section(title, R, unit=""):
    """Lines for one population. Callers add a header saying what CLV means in their test."""
    R = [dict(x) for x in R]
    for x in R:
        if x.get("late") is None:
            x["late"] = x.get("lead") is not None and x["lead"] < 30
    days = sorted({x["day"] for x in R if x.get("day")})
    mid = days[(len(days) - 1) // 2] if days else ""
    J = [x for x in R if not x["late"]]
    L = [f"--- STANDARD BUCKETS (BUCKETS.md): {title} | {len(R)} records, {days[0] if days else '-'} to {days[-1] if days else '-'}; "
         f"FIT <= {mid} < CHECK; LATE kept apart ---",
         f"  ALL (not LATE): {stats(J, unit)}",
         f"  LATE (final 30 min, own line): {stats([x for x in R if x['late']], unit)}" if _has(R, "lead") or any(x["late"] for x in R)
         else "  LATE (final 30 min): not in this test (no detection time)"]

    def ln(lab, xs, primary=False):
        f_, c_ = [x for x in xs if x.get("day") and x["day"] <= mid], [x for x in xs if x.get("day") and x["day"] > mid]
        hold = primary and len(f_) >= 15 and len(c_) >= 15 and _ok(f_) and _ok(c_)
        L.append(f"  {lab}: {stats(xs, unit)} | FIT {stats(f_, unit)} | CHECK {stats(c_, unit)}" + ("   << HOLDS BOTH HALVES" if hold else ""))
    L.append(" PRIMARY")
    for mk in ("totals", "spreads", "moneyline"):
        xs = [x for x in J if x.get("mk") == mk]
        if xs:
            ln(f"1 Market {mk}", xs, True)
    if _has(J, "sc"):
        for mk, scs in (("totals", ("under", "over")), ("spreads", ("dog", "fav")), ("moneyline", ("dog", "fav"))):
            for sc in scs:
                xs = [x for x in J if x.get("mk") == mk and x.get("sc") == sc]
                if xs:
                    ln(f"2 {mk} x {sc}", xs, True)
        for sc in ("under", "over", "dog", "fav"):
            xs = [x for x in J if x.get("sc") == sc]
            if xs:
                ln(f"2 Side {sc} (all markets)", xs, True)
    else:
        L.append("  2 Side (over/under, fav/dog by points): not in this test")
    if _has(J, "live1") or _has(J, "live5"):
        for m_ in (1, 5):
            ln(f"3 Still bettable +{m_} min", [x for x in J if x.get(f"live{m_}") is True], True)
            ln(f"3 Gone within {m_} min", [x for x in J if x.get(f"live{m_}") is False], True)
    else:
        L.append("  3 Still bettable +1 / +5 min: not in this test")
    L.append(" SECONDARY (refine only)")
    if _has(J, "move"):
        for mv in ("L", "P"):
            xs = [x for x in J if x.get("move") == mv]
            if xs:
                ln(f"4 Move type {mv} ({'line moved' if mv == 'L' else 'price only'})", xs)
    else:
        L.append("  4 Move type (L / P): not in this test")
    if _has(J, "ldelta") or _has(J, "pdelta"):
        for lo, hi, lab in ((0.25, 1.0, "0.5 pt"), (1.0, 1.5, "1 pt"), (1.5, 2.0, "1.5 pts"), (2.0, 3.0, "2-2.5 pts"), (3.0, 99, "3+ pts")):
            xs = [x for x in J if x.get("ldelta") is not None and lo <= abs(x["ldelta"]) < hi]
            if xs:
                ln(f"5 Line move {lab}", xs)
                for lg in sorted({x.get("lg") for x in xs if x.get("lg")}):
                    ys = [x for x in xs if x.get("lg") == lg]
                    if len(ys) >= 5:
                        ln(f"    {lg}", ys)
        for lo, hi, lab in ((8, 12, "8-11c"), (12, 20, "12-19c"), (20, 30, "20-29c"), (30, 999, "30c+")):
            xs = [x for x in J if not x.get("ldelta") and x.get("pdelta") is not None and lo <= abs(x["pdelta"]) < hi]
            if xs:
                ln(f"5 Price move {lab}", xs)
    else:
        L.append("  5 Move size: not in this test")
    if _has(J, "key"):
        for kb in sorted({x["key"] for x in J if x.get("key")}):
            ln(f"6 Football spreads: {kb}", [x for x in J if x.get("key") == kb])
    else:
        L.append("  6 Football key numbers: not in this test (no NFL/NCAAF spreads, or no line)")
    if _has(J, "wide"):
        ln("7 Market-wide (other books moved with Pinnacle)", [x for x in J if x.get("wide") is True])
        ln("7 Pinnacle moved alone", [x for x in J if x.get("wide") is False])
        L.append("    " + WIDE_DEF)
    else:
        L.append("  7 Market-wide vs lone: not in this test")
    if _has(J, "lead"):
        for lo, hi, lab in ((30, 120, "30m-2h"), (120, 360, "2-6h"), (360, 1440, "6-24h"), (1440, 10 ** 7, "24h+")):
            xs = [x for x in J if x.get("lead") is not None and lo <= x["lead"] < hi]
            if xs:
                ln(f"8 Time before start {lab}", xs)
    else:
        L.append("  8 Time before start: not in this test")
    if _has(J, "edge"):
        for lo, hi, lab in ((-1e9, 2, "under 2%"), (2, 4, "2-4%"), (4, 8, "4-8%"), (8, 1e9, "8%+")):
            xs = [x for x in J if x.get("edge") is not None and lo <= x["edge"] < hi]
            if xs:
                ln(f"9 Edge {lab}", xs)
    else:
        L.append("  9 Edge at detection: not in this test")
    lgs = sorted({x.get("lg") for x in J if x.get("lg")})
    for lg in lgs:
        for mk in ("totals", "spreads", "moneyline"):
            xs = [x for x in J if x.get("lg") == lg and x.get("mk") == mk]
            if len(xs) >= 5:
                ln(f"10 {lg} {mk}", xs)
    if _has(J, "pin_limit"):
        for lg in lgs:
            xs = [x for x in J if x.get("lg") == lg and x.get("pin_limit")]
            if len(xs) >= 6:
                med = stt.median(x["pin_limit"] for x in xs)
                ln(f"11 {lg} Pinnacle limit > {med:,.0f} (league median, raw)", [x for x in xs if x["pin_limit"] > med])
                ln(f"11 {lg} Pinnacle limit <= {med:,.0f}", [x for x in xs if x["pin_limit"] <= med])
    else:
        L.append("  11 Pinnacle limit when it moved: not in this test")
    if _has(J, "am"):
        ln("12 Price better than -110", [x for x in J if x.get("am") is not None and x["am"] > -110])
        ln("12 Price -110 or worse", [x for x in J if x.get("am") is not None and x["am"] <= -110])
    else:
        L.append("  12 Price vs -110: not in this test")
    L += grid_lines(J, unit, mid)
    return L


# Nov 4 (Muse's grid, Peter 2:09 PM "when we have all data we start with this table"): every test also prints
# League x Market (ML Fav / ML Dog / Spread Fav / Spread Dog / Over / Under), units first, ranked by total units. Per cell: units, % per
# 1u play, W-L-P, n, distinct games (where the records carry a game key), CLV in units (actual / expected / difference;
# expected = sum of each play's CLV at the Pinnacle close, only where CLV is in % of the stake), both halves, and the
# judged size (smaller of n and distinct games: < 50 too thin, 50 checkpoint, 100 judged). A short candidate list ends it.
def _mlabel(x):
    mk = x.get("mk")
    if mk == "totals":
        return {"under": "Under", "over": "Over"}.get(x.get("sc"), "Total")
    m = {"spreads": "Spread", "moneyline": "ML"}.get(mk, mk or "?")
    # Peter Nov 4 2:24 PM "we should do favorite underdog": ML and Spread are split into favorite and underdog
    sc = x.get("sc")
    if sc not in ("fav", "dog") and mk == "moneyline" and x.get("am") is not None:
        sc = "fav" if float(x["am"]) < 0 else "dog"   # ML records carry no side class: the price decides (minus = favorite)
    return m + {"fav": " Fav", "dog": " Dog"}.get(sc, "")


def _gkey(x):
    for k in ("game_id", "fid", "ev", "game", "match"):
        if x.get(k):
            return str(x[k])
    return None


def grid_lines(J, unit, mid):
    G = [x for x in J if x.get("units") is not None and x.get("lg")]
    if not G:
        return ["  GRID (league x market, units first): not in this test (no graded units)"]
    pct = unit == "%"
    bench = "Pinnacle no-vig close" if pct else "this test's own close (cents; expected units not computed)"
    L = [f" GRID - League x Market, units first (benchmark: {bench}); judged on the smaller of n and distinct games"]
    cells = {}
    for x in G:
        cells.setdefault((x["lg"], _mlabel(x)), []).append(x)
    rows = []
    for (lg, mk), xs in cells.items():
        u = sum(x["units"] for x in xs)
        n = len(xs)
        w = sum(1 for x in xs if x["units"] > 0)
        lo = sum(1 for x in xs if x["units"] < 0)
        g = {_gkey(x) for x in xs if _gkey(x)}
        ng = len(g) if g else None
        jn = min(n, ng) if ng else n
        h1 = [x for x in xs if x.get("day") and x["day"] <= mid]
        h2 = [x for x in xs if x.get("day") and x["day"] > mid]
        hu = lambda h: (sum(x["units"] for x in h), len(h))
        (u1, n1), (u2, n2) = hu(h1), hu(h2)
        c = [x["clv"] for x in xs if x.get("clv") is not None]
        if pct and c:
            exp = sum(c) / 100.0
            clv = f"CLV units actual {u:+.2f} / expected {exp:+.2f} / {u - exp:+.2f}"
        else:
            exp = None
            clv = f"CLV {sum(c) / len(c):+.2f}{unit}" if c else "CLV -"
        size = "too thin" if jn < 50 else ("checkpoint" if jn < 100 else "judged")
        read = ""
        if exp is not None:
            if exp > 0 and u > 0:
                read = " | read: beat the close and won"
            elif exp > 0 and u < 0 and jn >= 100:
                read = " | read: FLAG - beat the close but lost units (data check / benchmark)"
            elif exp < 0 and u > 0:
                read = " | read: lost to the close but won units (ran hot)"
        rows.append((u, f"  {lg} {mk}: {u:+.2f}u | {100 * u / n:+.1f}% | {w}-{lo}-{n - w - lo} | n {n}"
                        f" | games {ng if ng is not None else '-'} | {clv}"
                        f" | H1 {u1:+.2f}u {(100 * u1 / n1) if n1 else 0:+.1f}% (n {n1}) | H2 {u2:+.2f}u {(100 * u2 / n2) if n2 else 0:+.1f}% (n {n2})"
                        f" | {size}{read}", dict(u=u, n=n, jn=jn, u1=u1, u2=u2, exp=exp, lab=f"{lg} {mk}")))
    rows.sort(key=lambda r: -r[0])
    L += [r[1] for r in rows]
    # Peter Nov 4 2:10 PM "i want to see all cells": every league x every market is printed, empty ones too
    lgs = sorted({x["lg"] for x in G})
    empty = [f"{lg} {mk}" for lg in lgs for mk in ("ML Fav", "ML Dog", "Spread Fav", "Spread Dog", "Over", "Under") if (lg, mk) not in cells]
    if empty:
        L.append("  n 0 (no plays in this test): " + ", ".join(empty))
    cand = [r[2] for r in rows if r[2]["u"] > 0 and r[2]["u1"] > 0 and r[2]["u2"] > 0 and r[2]["jn"] >= 50
            and (r[2]["exp"] is None or r[2]["exp"] >= 0)]
    L.append("  GRID CANDIDATES (positive units, both halves positive, judged size 50+"
             + (", not behind the close" if pct else "") + "): "
             + (", ".join(f"{c_['lab']} ({c_['u']:+.2f}u, n {c_['n']})" for c_ in cand) if cand else "none"))
    return L


def dec_to_am(d):
    if not d or d <= 1:
        return None
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def p_to_am(p):
    if not p or not 0 < p < 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def ldelta_from_detail(detail):
    """Points Pinnacle's line moved, from a SLOW-HR / exchange-lag detail string 'Pinnacle a -> b ...'; None if not there."""
    import re
    m = re.search(r"Pinnacle ([-+]?[0-9.]+) -> ([-+]?[0-9.]+)", detail or "")
    return abs(float(m.group(2)) - float(m.group(1))) if m else None
