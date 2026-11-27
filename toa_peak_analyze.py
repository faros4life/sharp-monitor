"""toa_peak_analyze.py - reads the 15 s series written by toa_peak_probe (PROBE_OUT) and answers Peter's Nov 26 list:
Pinnacle line moves and price-only moves caught/missed and delays; exchange changes by size; after-fee opportunities,
how long they last and how many each sampler loses; and the alerts that fired in the window (Liquidity Dogs, Lane 1
candidates, Board PLAY calls): how long the alerted price stayed available and what a 30 s / 60 s / 5 min observer got.

Research only, zero API calls. Every venue quote from The Odds API is an INDICATIVE top-of-book price with no size; a
"bot-tradeable venue" is one the executor can trade (clv_std.AUTO), not proof that size was there.
Thresholds: a change under 1 cent of implied probability is INSIGNIFICANT; an opportunity is ACTIONABLE at >= +1.0%
after fees against Pinnacle's exact-line no-vig price at the same poll, MARGINAL at 0 to +1%.
Log: counts, seconds, cents and percentages only.
"""
import collections
import gzip
import json
import os
import statistics as st
import sys

import clv_std as cs

SP_LG = {"basketball_nba": "NBA", "basketball_ncaab": "NCAAB", "americanfootball_ncaaf": "NCAAF",
         "americanfootball_nfl": "NFL"}
TOA_KEY = {"novig.us": "novig", "novig": "novig", "prophetx": "prophetx", "kalshi": "kalshi",
           "polymarket.us": "polymarket_us", "polymarket_us": "polymarket_us", "hardrockbet": "hardrockbet_fl"}
ACT = 0.01
RATES = {"15s": 15, "30s": 30, "60s": 60, "5min": 300}


def dec(am):
    return None if am in (None, 0) else (1 + am / 100 if am > 0 else 1 + 100 / abs(am))


def ip(am):
    d = dec(am)
    return 1 / d if d else None


def cents(a, b):
    return abs(ip(a) - ip(b)) * 100 if ip(a) and ip(b) else 0.0


def tier(c):
    return "<1c (insignificant)" if c < 1 else ("1-2c" if c < 2 else ">=2c")


def changes(obs):
    out, prev = [], None
    for _i, t, v in obs:
        v = tuple(v)
        if v != prev:
            if prev is not None:
                out.append((t, prev, v))
            prev = v
    return out


def sampled(obs, step):
    return [x for x in obs if x[0] % step == 0]


def med(xs):
    return f"{st.median(xs):.0f}s" if xs else "n/a"


def toks(s):
    import clv_scorecard as sc
    return set(sc.toks(s))


def load_series(path):
    d = json.load(gzip.open(path, "rt"))
    S = {tuple(k): [(a, b, tuple(v)) for a, b, v in obs] for k, obs in d["series"]}
    return d, S


def pin_moves(S, start, step_of):
    tot, cau, dl = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    for (sp, eid, bk, mk, oc), obs in S.items():
        if bk != "pinnacle" or mk not in ("spreads", "totals", "h2h"):
            continue
        truth = changes(obs)
        for t0, pv, v in truth:
            kind = "line" if pv[0] != v[0] else "price-only"
            if kind == "price-only" and cents(pv[1], v[1]) < 1:
                kind = "price-only <1c"
            b = "<=60 min" if start.get(eid, 0) - t0 <= 3600 else ">60 min"
            for r, step in step_of.items():
                tot[(kind, b, r)] += 1
                hit = next((t for _i, t, vv in sampled(obs, step) if t >= t0 and vv == v), None)
                if hit is not None:
                    cau[(kind, b, r)] += 1
                    dl[(kind, b, r)].append(hit - t0)
    return tot, cau, dl


def exch_changes(S, start, step_of):
    c = collections.Counter()
    for (sp, eid, bk, mk, oc), obs in S.items():
        if bk == "pinnacle":
            continue
        for r, step in step_of.items():
            for t0, pv, v in changes(sampled(obs, step)):
                b = "<=60 min" if start.get(eid, 0) - t0 <= 3600 else ">60 min"
                tr = "line change" if pv[0] != v[0] else tier(cents(pv[1], v[1]))
                c[(b, r, tr)] += 1
    return c


PIN = {}


def by_poll(S):
    """{(eid, mk, oc, bk): {poll i: (t, point, price)}}; also indexes Pinnacle by (eid, mk) for the fair price."""
    PIN.clear()
    for (sp, eid, bk, mk, oc), obs in S.items():
        if bk == "pinnacle":
            PIN.setdefault((eid, mk), []).append((oc, {i: (t, v[0], v[1]) for i, t, v in obs}))
    return {(eid, mk, oc, bk): {i: (t, v[0], v[1]) for i, t, v in obs} for (sp, eid, bk, mk, oc), obs in S.items()}


def fair(P, eid, mk, oc, i, point):
    """Pinnacle exact-line two-sided no-vig probability of outcome oc at poll i, or None."""
    me = P.get((eid, mk, oc, "pinnacle"), {}).get(i)
    if not me or me[1] != point:
        return None
    others = [v[i] for o, v in PIN.get((eid, mk), []) if o != oc and i in v]
    if len(others) != 1:
        return None
    o = others[0]
    if mk == "spreads" and (o[1] is None or point is None or abs(o[1] + point) > 1e-9):
        return None
    if mk == "totals" and o[1] != point:
        return None
    a, b = ip(me[2]), ip(o[2])
    return a / (a + b) if a and b else None


def edge(P, lg, eid, mk, oc, bk, i):
    q = P.get((eid, mk, oc, bk), {}).get(i)
    if not q or dec(q[2]) is None:
        return None
    p = fair(P, eid, mk, oc, i, q[1])
    v = cs.canon(bk, strict=False)
    if p is None or not v:
        return None
    try:
        nd = cs.net_dec(v, dec(q[2]), league=lg)
    except Exception:
        return None
    return None if nd is None else p * nd - 1


def opportunities(S, P, start, sp_of, poll_t, poll_s):
    """Windows of consecutive polls at >= +1% (and 0..1%) after fees, per venue quote at its exact line."""
    out = []
    keys = {(eid, mk, oc, bk) for (sp, eid, bk, mk, oc) in S if bk != "pinnacle"}
    for eid, mk, oc, bk in keys:
        lg = SP_LG.get(sp_of.get(eid))
        cur = None
        for i in sorted(P[(eid, mk, oc, bk)]):
            e = edge(P, lg, eid, mk, oc, bk, i)
            lvl = "actionable" if e is not None and e >= ACT else ("marginal" if e is not None and e >= 0 else None)
            if lvl and cur and cur[0] == lvl and i == cur[2] + 1:
                cur[2] = i
                continue
            if cur:
                out.append((eid, bk) + tuple(cur))
            cur = [lvl, i, i] if lvl else None
        if cur:
            out.append((eid, bk) + tuple(cur))
    rows = []
    for eid, bk, lvl, s, e in out:
        t0 = poll_t[s] if s < len(poll_t) else 0
        dur = (poll_t[e] - t0 + poll_s) if e < len(poll_t) else poll_s
        b = "<=60 min" if start.get(eid, 0) - t0 <= 3600 else ">60 min"
        trade = "bot-tradeable" if cs.canon(bk, strict=False) in cs.AUTO else "manual only"
        seen = {}
        for r, step in RATES.items():
            k = step // poll_s
            first = next((j for j in range(s, e + 1) if j % k == 0), None)
            seen[r] = None if first is None else poll_t[first] - t0
        rows.append({"lvl": lvl, "b": b, "trade": trade, "dur": dur, "seen": seen})
    return rows


def alert_rows(t0, t1, sports):
    """(strategy, alert dict normalised) for alerts inside the window."""
    import executor as ex
    def tp(s):
        import clv_ledger as cl
        x = cl.tp(s)
        return x.timestamp() if x else None
    lgs = {SP_LG[s] for s in sports if s in SP_LG}
    out = []
    A = json.load(open("alerts.json"))
    for a in (A if isinstance(A, list) else A.get("alerts") or []):
        t = tp(a.get("alert_utc"))
        if t and t0 <= t <= t1 and a.get("sport") in lgs:
            out.append(("LANE 1 PROXY (sharp alerts - NOT Lane 1 qualification)", {"t": t, "lg": a.get("sport"), "game": a.get("game"),
                        "bet": a.get("bet"), "book": a.get("book_key"), "am": a.get("price")}))
    Q = json.load(open("liquidity/alerts.json"))
    Q = Q if isinstance(Q, list) else Q.get("alerts") or []
    liq = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in Q if isinstance(x, dict)}
    def norm(x):
        return {"t": tp(x.get("alerted_utc")), "lg": x.get("league"), "game": x.get("game"), "mk": x.get("market"),
                "side": x.get("side"), "line": x.get("line"), "book": x.get("book"), "am": x.get("price_american")}
    for x in liq.values():
        t = tp(x.get("alerted_utc"))
        if t and t0 <= t <= t1 and x.get("league") in lgs and ex.dogs_qualifies(x) and ex.dogs_bet(x):
            out.append(("LIQUIDITY DOGS", norm(x)))
    B = (json.load(open("board/calls.json")) or {}).get("calls") or {}
    for k, c in B.items():
        x = liq.get(k)
        t = tp(c.get("at"))
        if c.get("call") == "PLAY" and x and t and t0 <= t <= t1 and x.get("league") in lgs:
            out.append(("BOARD PLAY calls", norm(x)))
    return out


def locate(a, S, names):
    """Series key of the alerted venue quote, or None. Both teams must appear in the alert's game string."""
    import clv_ledger as cl
    gt = toks(a["game"])
    eids = [e for e, (sp, h, w) in names.items() if SP_LG.get(sp) == a["lg"] and toks(h) & gt and toks(w) & gt]
    if len(eids) != 1:
        return None
    eid, bk = eids[0], TOA_KEY.get(cs.canon(a["book"], strict=False) or str(a["book"]))
    if a.get("bet"):
        pb = cl.parsed({"bet": a["bet"]})
        if not pb:
            return None
        kind, side, line = pb[0], pb[1], pb[2]
    else:
        kind = {"total": "total", "spread": "spread", "moneyline": "ml"}.get(a.get("mk"))
        side, line = a.get("side"), a.get("line")
    mk = {"total": "totals", "spread": "spreads", "ml": "h2h"}.get(kind)
    for (sp, e, b, m, oc), obs in S.items():
        if e != eid or b != bk or m != mk:
            continue
        if mk == "totals" and oc.lower() != str(side).lower():
            continue
        if mk != "totals" and not (toks(oc) & toks(side)):
            continue
        pts = [v[0] for _i, _t, v in obs]
        if mk != "h2h" and line is not None and not any(p is not None and abs(abs(p) - abs(float(line))) < 1e-9 for p in pts):
            continue
        return (sp, e, b, m, oc), (None if line is None else abs(float(line)))
    return None


def alert_follow(a, key, line, S, P, poll_t):
    obs = S[key]
    am = a["am"]
    after = [(i, t, v) for i, t, v in obs if t >= a["t"]]
    if not after or dec(am) is None:
        return None
    ok = lambda v: (line is None or (v[0] is not None and abs(abs(v[0]) - line) < 1e-9)) and dec(v[1]) and dec(v[1]) >= dec(am) - 1e-9
    gone = next((t for _i, t, v in after if not ok(v)), None)
    avail = (gone - a["t"]) if gone else None
    lg = SP_LG.get(key[0])
    res = {"avail": avail, "censored": gone is None, "dc": {}, "edge0": None, "edge5": None}
    for r, d in (("30s", 30), ("60s", 60), ("5min", 300)):
        x = next(((i, t, v) for i, t, v in after if t >= a["t"] + d), None)
        if x:
            same = line is None or (x[2][0] is not None and abs(abs(x[2][0]) - line) < 1e-9)
            res["dc"][r] = (ip(am) - ip(x[2][1])) * 100 if same else None   # a moved line is not a price change
    e0 = edge(P, lg, key[1], key[3], key[4], key[2], after[0][0])
    res["edge0"] = e0
    x5 = next(((i, t, v) for i, t, v in after if t >= a["t"] + 300), None)
    res["edge5"] = edge(P, lg, key[1], key[3], key[4], key[2], x5[0]) if x5 else None
    return res


def main(path):
    d, S = load_series(path)
    poll_s, poll_t, start, names = d["poll_s"], d["poll_t"], d["start"], d["names"]
    step_of = {r: s // poll_s for r, s in RATES.items()}
    sp_of = {e: v[0] for e, v in names.items()}
    print(f"SERIES: polls {len(poll_t)} every {poll_s}s | events {len(names)} | quote series {len(S)}")

    tot, cau, dl = pin_moves(S, start, step_of)
    print("PINNACLE MOVES: caught/total | median detection delay")
    for kind in ("line", "price-only", "price-only <1c"):
        for b in ("<=60 min", ">60 min"):
            row = [f"{r} {cau[(kind, b, r)]}/{tot[(kind, b, r)]} {med(dl[(kind, b, r)])}" for r in RATES]
            print(f"  {kind:<15} {b:<9} " + " | ".join(row) if tot[(kind, b, '15s')] else f"  {kind:<15} {b:<9} none")

    ex = exch_changes(S, start, step_of)
    print("EXCHANGE / OTHER-BOOK CHANGES seen by each sampler, by size (cents of implied probability)")
    for b in ("<=60 min", ">60 min"):
        for tr in ("line change", ">=2c", "1-2c", "<1c (insignificant)"):
            print(f"  {b:<9} {tr:<20} " + " | ".join(f"{r} {ex[(b, r, tr)]}" for r in RATES))

    P = by_poll(S)
    O = opportunities(S, P, start, sp_of, poll_t, poll_s)
    print("AFTER-FEE POTENTIAL OPPORTUNITIES vs Pinnacle exact-line no-vig (indicative quotes, no size - not confirmed executable trades)")
    for lvl in ("actionable", "marginal"):
        for trade in ("bot-tradeable", "manual only"):
            for b in ("<=60 min", ">60 min"):
                W = [w for w in O if w["lvl"] == lvl and w["trade"] == trade and w["b"] == b]
                if not W:
                    continue
                durs = [w["dur"] for w in W]
                lost = " | ".join(f"{r} lost {sum(1 for w in W if w['seen'][r] is None)} "
                                  f"delay {med([w['seen'][r] for w in W if w['seen'][r] is not None])}" for r in RATES)
                print(f"  {lvl:<10} {trade:<13} {b:<9} windows {len(W)} | median life {med(durs)} | "
                      f"<=30s {sum(x <= 30 for x in durs)} | <=5min {sum(x <= 300 for x in durs)} | {lost}")

    print("ALERTS IN THE WINDOW (alerted venue, alerted line; price change in cents, + = better for us)")
    rows = alert_rows(poll_t[0], poll_t[-1], {v[0] for v in names.values()})
    for strat in ("LIQUIDITY DOGS", "LANE 1 PROXY (sharp alerts - NOT Lane 1 qualification)", "BOARD PLAY calls"):
        A = [a for s, a in rows if s == strat]
        F = []
        for a in A:
            loc = locate(a, S, names)
            f = alert_follow(a, loc[0], loc[1], S, P, poll_t) if loc else None
            if f:
                F.append(f)
        if not A:
            print(f"  {strat}: no alerts in the window")
            continue
        av = [f["avail"] for f in F if f["avail"] is not None]
        line = (f"  {strat}: alerts {len(A)} | traced {len(F)} | price still there at end of window {sum(f['censored'] for f in F)}"
                f" | median availability (gone ones) {med(av)}")
        for r in ("30s", "60s", "5min"):
            v = [f["dc"][r] for f in F if f["dc"].get(r) is not None]
            line += f" | {r} {st.median(v):+.2f}c" if v else f" | {r} n/a"
        e0 = [f["edge0"] for f in F if f["edge0"] is not None]
        e5 = [f["edge5"] for f in F if f["edge5"] is not None]
        line += (f" | +EV after fees at alert {sum(e >= 0 for e in e0)}/{len(e0)}, after 5 min {sum(e >= 0 for e in e5)}/{len(e5)}")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROBE_OUT", "probe_series.json.gz")))
