#!/usr/bin/env python3
"""
BOARD LAB (Nov 3, 2026; Peter 9:53 AM "there is a lot of info here that we should be using to make the right calls").
PAPER / READ-ONLY. Re-derives every past Bets Board call (PLAY / LEAN / DEAD) day by day with the board's own rules
(board_build.score), then reports every board field as a bucket with both halves (H1 <= median day < H2), the standard
bucket list (BUCKETS.md), and the current rules vs the proposed v2 rules side by side. Graded 1u flat at the board
price; CLV in cents vs the board close. Changes nothing the board, alerts or executor read. Private email; the log
prints counts only.
"""
from collections import Counter
from datetime import datetime, timezone

import board_build as bb
import bucket_report as br
import buckets as bkt
import executor as ex

ET = br.ET


def rows():
    by_day = {}
    for x in bb.load():
        at = bb.t(x.get("alerted_utc"))
        if at:
            by_day.setdefault(at.astimezone(ET).strftime("%Y-%m-%d"), []).append(x)
    R = []
    for d, xs in sorted(by_day.items()):
        rs = []
        for x in xs:
            st = bb.t(x.get("start_utc"))
            rs.append({"x": x, "at": bb.t(x.get("alerted_utc")), "g": bb.game_of(x), "mk": x.get("market"), "sd": bb.side_of(x),
                       "side": x.get("side_label") or "", "new": x.get("new_money") or 0, "conf": bool(x.get("rule_met")),
                       "status": "pulled" if x.get("pulled") else ("game started" if st else "still there")})
        bb.score(rs)
        for r in rs:
            x = r["x"]
            if (x.get("clv_cents") is None or x.get("artifact") or x.get("close_suspect")
                    or x.get("result") not in ("W", "L", "P")):
                continue
            y = dict(x)
            y["_tag"], y["_day"] = r.get("v1", r["tag"]), d   # v1 call (the board shows v2 from Nov 3)
            R.append(y)
    return R


def moved_toward(r):
    return (r.get("price") or 0) > (r.get("price_when_first_seen") or 0) + 0.005


def v2(r):
    """Proposed v2 (Nov 3, sent to Muse for registration; paper only)."""
    if r.get("pulled") or moved_toward(r) or r.get("market") == "spread":
        return "OFF"
    am = r.get("price_american") or 0
    ok = r.get("price_rule") != "ml_edge_fail"
    if ok and ((r.get("league") == "NBA" and r.get("market") == "total") or (r.get("market") == "moneyline" and -250 <= am <= -110)):
        return "PLAY"
    return "LEAN" if r.get("market") in ("moneyline", "total") else "OFF"


def v2s(r):
    """v2-STRICT (Muse, Nov 3 ~10:15 AM): PLAY = NBA totals only (no ML-favorite leg); same OFF rules as v2."""
    t = v2(r)
    if t == "PLAY" and not (r.get("league") == "NBA" and r.get("market") == "total"):
        return "LEAN"
    return t


REG_UTC = "2026-11-03T15:15:00Z"   # v2 / v2-STRICT registered by Muse ~10:15 AM ET Nov 3: judged on calls alerted after this


def st(xs):
    if not xs:
        return "n0"
    w = sum(r["result"] == "W" for r in xs)
    l_ = sum(r["result"] == "L" for r in xs)
    u = sum(r.get("units_flat") or 0 for r in xs)
    c = sum(r["clv_cents"] for r in xs) / len(xs)
    b = sum(r["clv_cents"] > 0 for r in xs)
    return f"n{len(xs)} {w}-{l_} {u:+.1f}u CLV {c:+.2f}c beat {b}/{len(xs)}"


def gettable(r):
    """Muse registration Nov 3 ~10:21 AM: the +15-minute price is the gettable proxy (price_after_15m, best book then).
    None when nothing was still bettable at +15 min."""
    g = r.get("price_after_15m")
    if r.get("still_actionable") is False or g is None or not 0 < g < 1:
        return None
    return g


def gst(xs):
    """Same calls graded at the +15-min gettable price: 1u flat at that cost; CLV = (close - gettable cost) x 100."""
    G = [(r, gettable(r)) for r in xs]
    ok = [(r, g) for r, g in G if g is not None]
    if not ok:
        return f"n0 gettable (of {len(xs)})"
    u = sum(((1 - g) / g) if r["result"] == "W" else (-1.0 if r["result"] == "L" else 0.0) for r, g in ok)
    c = [(r["close_price"] - g) * 100 for r, g in ok if r.get("close_price") is not None]
    w = sum(r["result"] == "W" for r, _ in ok)
    l_ = sum(r["result"] == "L" for r, _ in ok)
    return (f"n{len(ok)} gettable (of {len(xs)}) {w}-{l_} {u:+.1f}u CLV {sum(c) / max(len(c), 1):+.2f}c "
            f"beat {sum(v > 0 for v in c)}/{len(c)}")


def gclv(xs):
    c = [(r["close_price"] - gettable(r)) * 100 for r in xs if gettable(r) is not None and r.get("close_price") is not None]
    return (sum(c) / len(c) if c else None), len(c)


def holds(a, b):
    f = lambda xs: len(xs) >= 15 and sum(r.get("units_flat") or 0 for r in xs) > 0 and sum(r["clv_cents"] for r in xs) > 0
    return f(a) and f(b)


def main():
    R = rows()
    days = sorted({r["_day"] for r in R})
    mid = days[(len(days) - 1) // 2] if days else ""
    H1 = lambda xs: [r for r in xs if r["_day"] <= mid]
    H2 = lambda xs: [r for r in xs if r["_day"] > mid]
    L = [f"BOARD LAB - PAPER, READ-ONLY | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
         f"{len(R)} graded board calls {days[0] if days else '-'} to {days[-1] if days else '-'}; H1 <= {mid} < H2. "
         "1u flat at the board price; CLV cents vs the board close. ** = positive units AND CLV in both halves, n >= 15 each.",
         "Many slices are scanned: expect some false positives. Decisions only at the scheduled review.", ""]

    def line(name, xs):
        a, b = H1(xs), H2(xs)
        L.append(f"{'**' if holds(a, b) else '  '}{name}: {st(xs)} | H1 {st(a)} | H2 {st(b)}")

    L.append("v1 RULES (the board until Nov 3; kickoff call):")
    for t in ("PLAY", "LEAN", "DEAD"):
        line(t, [r for r in R if r["_tag"] == t])
    L.append("v2 (registered by Muse ~10:15 AM ET Nov 3) - IN-SAMPLE backtest:")
    for t in ("PLAY", "LEAN", "OFF"):
        line(f"v2 {t}", [r for r in R if v2(r) == t])
    line("v2-STRICT PLAY (NBA totals only)", [r for r in R if v2s(r) == "PLAY"])
    FW = [r for r in R if str(r.get("alerted_utc") or "") >= REG_UTC]
    L.append(f"FORWARD ONLY (alerted after registration {REG_UTC}; the judged numbers; bar n >= 100, CLV > 0, beat >= 53%, both halves):")
    for name, f in (("current PLAY", lambda r: r["_tag"] == "PLAY"), ("current LEAN", lambda r: r["_tag"] == "LEAN"),
                    ("v2 PLAY", lambda r: v2(r) == "PLAY"), ("v2 LEAN", lambda r: v2(r) == "LEAN"),
                    ("v2-STRICT PLAY", lambda r: v2s(r) == "PLAY"),
                    ("DESCRIPTIVE ML fav -110..-250 (not pulled, not moved toward, any price_rule; Muse Nov 3, not PLAY)",
                     lambda r: r.get("market") == "moneyline" and -250 <= (r.get("price_american") or 0) <= -110
                     and not r.get("pulled") and not moved_toward(r)),
                    ("DESCRIPTIVE NBA-TOTALS-ALL (pulled included; Muse Amendment 3, item 55, not PLAY)",
                     lambda r: r.get("league") == "NBA" and r.get("market") == "total")):
        L.append(f"   {name}: {st([r for r in FW if f(r)])}")
    PL = [r for r in FW if v2s(r) == "PLAY"]
    L.append(f"   BOARD PLAY (NBA totals only; the one registered PLAY rule) at the +15-min GETTABLE price - THE JUDGED LINE: {gst(PL)}")
    L.append(f"   same PLAY calls at the board price (secondary): {st(PL)}")
    c50, k = gclv(PL)
    L.append(f"   STOP-AT-50 counter (gettable basis): {min(k, 50)}/50 resulted" + (f", avg CLV {c50:+.2f}c" if c50 is not None else "")
             + (" -> STOP: negative at 50, lane closed (Muse registration)" if k >= 50 and c50 is not None and c50 < 0 else
                (" -> passed the 50 check; live still needs the full 100" if k >= 50 else "")))
    L.append(f"   in-sample for reference, board PLAY at gettable price: {gst([r for r in R if v2s(r) == 'PLAY'])}")
    NA = [r for r in FW if r.get("league") == "NBA" and r.get("market") == "total"]
    L.append(f"   item 55 NBA-TOTALS-ALL forward at gettable price: {gst(NA)} | pulled only: {gst([r for r in NA if r.get('pulled')])}")
    L.append("Everything above FORWARD ONLY is in-sample (the rules were picked from it): descriptive, not judged.")
    today = (datetime.now(timezone.utc).astimezone(ET)).strftime("%Y-%m-%d")
    yday = sorted(d for d in days if d < today)[-1:] if days else []
    if yday:
        Y = [r for r in R if r["_day"] == yday[0]]
        L.append(f"Last graded day {yday[0]}: current PLAY {st([r for r in Y if r['_tag'] == 'PLAY'])} | LEAN {st([r for r in Y if r['_tag'] == 'LEAN'])}"
                 f" | v2 PLAY {st([r for r in Y if v2(r) == 'PLAY'])}")
    L += ["", "FIELD SCAN (every call, any tag):"]
    F = [("money pulled", lambda r: r.get("pulled")), ("money kept", lambda r: not r.get("pulled")),
         ("second-book confirmed", lambda r: r.get("rule_met")), ("not confirmed", lambda r: not r.get("rule_met")),
         ("sharp alert agrees", lambda r: bool(r.get("sharp_agree"))), ("sharp alert opposes", lambda r: bool(r.get("sharp_oppose"))),
         ("still bettable at +15 min", lambda r: r.get("still_actionable") is True),
         ("gone by +15 min", lambda r: r.get("still_actionable") is False),
         ("price moved toward since first seen", moved_toward),
         ("price drifted away since first seen", lambda r: (r.get("price") or 0) < (r.get("price_when_first_seen") or 0) - 0.005),
         ("money >= 50% of base depth", lambda r: (r.get("new_money") or 0) >= 0.5 * (r.get("base_depth") or 1e18)),
         ("money < 20% of base depth", lambda r: (r.get("new_money") or 0) < 0.2 * (r.get("base_depth") or 1)),
         ("confirmed within 5 min", lambda r: (r.get("confirmed_after_min") if r.get("confirmed_after_min") is not None else 99) <= 5),
         ("confirmed after 20+ min", lambda r: (r.get("confirmed_after_min") or 0) >= 20)]
    for lo, hi in ((0, 1e5), (1e5, 2.5e5), (2.5e5, 5e5), (5e5, 1e18)):
        F.append((f"new money ${lo / 1e3:.0f}K-" + (f"${hi / 1e3:.0f}K" if hi < 1e17 else "up"),
                  lambda r, lo=lo, hi=hi: lo <= (r.get("new_money") or 0) < hi))
    for b in sorted({r.get("book") for r in R if r.get("book")}):
        F.append((f"source book {b}", lambda r, b=b: r.get("book") == b))
    for v in sorted({str(r.get("price_rule")) for r in R}):
        F.append((f"price_rule {v}", lambda r, v=v: str(r.get("price_rule")) == v))
    for lg in sorted({r.get("league") for r in R if r.get("league")}):
        for mk in ("moneyline", "spread", "total"):
            F.append((f"{lg} {mk}", lambda r, lg=lg, mk=mk: r.get("league") == lg and r.get("market") == mk))
    F += [("ML fav -110 to -250", lambda r: r.get("market") == "moneyline" and -250 <= (r.get("price_american") or 0) <= -110),
          ("ML fav worse than -250", lambda r: r.get("market") == "moneyline" and (r.get("price_american") or 0) < -250),
          ("ML dog", lambda r: r.get("market") == "moneyline" and (r.get("price_american") or 0) > 0)]
    # Nov 3 (Peter 10:33 "can we also use the P limit"): Pinnacle limit at alert (x2/limits.json, from Nov 2 only)
    X2 = bb.x2_limits()
    for r in R:
        r["_pl"] = X2.get(f"{r.get('key')}|{r.get('alerted_utc')}") or {}
    has = [r for r in R if r["_pl"].get("p_alert")]
    med = {}
    for lg in {r.get("league") for r in has}:
        v = sorted(r["_pl"]["p_alert"] for r in has if r.get("league") == lg)
        med[lg] = v[len(v) // 2]
    F += [("P limit at alert known (from Nov 2)", lambda r: bool(r["_pl"].get("p_alert"))),
          ("P limit at alert > league median", lambda r: bool(r["_pl"].get("p_alert")) and r["_pl"]["p_alert"] > med.get(r.get("league"), 1e18)),
          ("P limit at alert <= league median", lambda r: bool(r["_pl"].get("p_alert")) and r["_pl"]["p_alert"] <= med.get(r.get("league"), -1)),
          ("2X tag (exchange money >= 2x P limit)", lambda r: r["_pl"].get("x2") is True),
          ("no 2X tag (limit known)", lambda r: bool(r["_pl"].get("p_alert")) and r["_pl"].get("x2") is not True)]
    for name, f in F:
        xs = [r for r in R if f(r)]
        if xs:
            line(name, xs)

    def rec(r):
        mk = {"spread": "spreads", "total": "totals", "moneyline": "moneyline"}.get(r.get("market"))
        sd = str(r.get("side") or "").upper()
        sc = ("under" if sd.startswith("UNDER") else "over") if mk == "totals" else \
             (("dog" if (r.get("line") or 0) > 0 else "fav") if mk == "spreads" else
              ("dog" if (r.get("price_american") or 0) > 0 else "fav"))
        return {"day": r["_day"], "clv": r["clv_cents"], "lg": r.get("league"), "mk": mk, "sc": sc, "lead": r.get("lead_min"),
                "am": r.get("price_american")}
    for title, xs in (("Board: current LEAN + PLAY", [r for r in R if r["_tag"] in ("PLAY", "LEAN")]),
                      ("Board: v2 PLAY (in-sample)", [r for r in R if v2(r) == "PLAY"]),
                      ("Board: v2 PLAY forward only", [r for r in R if v2(r) == "PLAY" and str(r.get("alerted_utc") or "") >= REG_UTC]),
                      ("Board: every call", R)):
        L += [""] + bkt.section(f"{title} (CLV cents vs board close)", [rec(r) for r in xs], "c")
    ex.send("Bets BOARD LAB (paper: every board field, current vs v2 rules)", "\n".join(L))
    print(f"board lab: {len(R)} graded calls, tags {dict(Counter(r['_tag'] for r in R))}")   # counts only


if __name__ == "__main__":
    main()
