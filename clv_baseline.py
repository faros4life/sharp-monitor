"""clv_baseline.py - two CLV diagnostics (Peter, Nov 26). READ-ONLY, CACHE-ONLY, NO API CALL, WRITES NOTHING.

Certified CLV is untouched and stays the official number. Everything here is an ADDITIONAL diagnostic.

TEST 1 - zero-movement baseline. The CLV a play would score if Pinnacle's no-vig price never moved after the alert:
    baseline = p_alert * entry_net - 1
where p_alert is Pinnacle's exact-line two-sided no-vig price IN FORCE AT THE ALERT, read by the SAME function that
certifies the close (clv_basis.pinnacle_no_vig_close) with the cut-off moved from the start to the alert time, from
the same cached history. It splits exactly:
    certified CLV = gross alert edge (p_alert * raw - 1)       what the venue's own price offered vs fair
                  + transaction cost (p_alert * (net - raw))   that venue's fee
                  + market movement  ((p_close - p_alert) * net) what happened after the alert
    baseline-adjusted CLV = certified - baseline = market movement
A row whose alert-time price cannot be read on the same basis as its close gets NO baseline (excluded, counted).

TEST 2 - matched fills. A bot fill is matched to a paper row only on the same league, start day, market, line, side
and an identical closing price (|p_close - fill close| <= 0.002). Both are then priced against the FILL's close:
    execution = p_close * (fill_net - alert_net)
Matched and unmatched paper rows are reported side by side so selection bias is visible, never extrapolated.

Public log: percentages, counts, W-L and units only. No dollars, stakes or keys.
"""
import contextlib
import io
import json
import os
import statistics as st
import sys
from collections import Counter
from datetime import timedelta, timezone

import clv_basis as cb
import clv_ledger as cl
import clv_obs_audit as oa
import clv_std as cs
import fixture_match as fxm
import tracker_build as tb

CERT_HOW = ("own line", "moneyline")
SAME_CLOSE = 0.002
ET = timezone(timedelta(hours=-5))


def decompose(p_alert, p_close, raw, net):
    """Percent components. Pure. They sum to the certified CLV exactly."""
    gross = 100 * (p_alert * raw - 1)
    fee = 100 * p_alert * (net - raw)
    move = 100 * (p_close - p_alert) * net
    return {"gross": gross, "fee": fee, "baseline": gross + fee, "move": move, "clv": gross + fee + move}


def raw_dec(x, src):
    if src == "liquidity":
        c = tb.num(x.get("price"))
        return 1 / c if c and 0 < c < 1 else None
    am = tb.num(x.get("price"))
    return cl.am_to_dec(am) if am is not None else None


def alert_time(x, src):
    return cl.tp(x.get("alerted_utc") if src == "liquidity" else x.get("alert_utc"))


def fair_at_alert(x, src, rec, allfx, mkmap):
    """(p_alert, None) or (None, reason). Same basis as the certified close or nothing."""
    ta = alert_time(x, src)
    if not ta:
        return None, "no alert time"
    fid = str(rec.get("fid") or "")
    snap = oa.snap_for(x, src)
    if fid.startswith("toa:"):
        import toa
        lg = snap.get("league")
        f = (toa.fixtures(lg) or {}).get(fid) if lg in toa.SPORT else None
        if not f:
            return None, "toa event not in store"
        if ta >= cl.tp(f.get("start")):
            return None, "alert at or after start"
        c, w = toa.close(snap, dict(f, start=cl.iso(ta)), fid, lg, cl.parsed, fxm.resolve_side, cl.which_team,
                         cl.novig_p, cl.FRESH_MIN)
        if not c:
            return None, "toa: " + " ".join(str(w).split()[:6])
        return (c["p"], None) if c.get("how") == rec.get("how") else (None, "different basis from the close")
    f, h = allfx.get(fid), oa.cached_pin(fid)
    if not f or h is None:
        return None, "no cached history"
    if ta >= cl.tp(f.get("start")):
        return None, "alert at or after start"
    p, why = cb.pinnacle_no_vig_close(dict(f, start=cl.iso(ta)), snap, mkmap, cl.book_markets(h, "pinnacle"),
                                      cl.parsed, cl.which_team, cl.two_way, cl.novig_p, cl.SCORE_SPORT,
                                      cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
    if p is None:
        return None, "no exact-line quote at the alert"
    if why.get("how") != rec.get("how"):
        return None, "different basis from the close"
    return p, None


def ci(xs):
    import last50_report as L
    return L.ci_mean(xs)


def m(xs):
    return st.mean(xs) if xs else None


def f_mean(xs, beat=False):
    if not xs:
        return "n/a"
    c = ci(xs)
    s = f"{m(xs):+.2f}% n{len(xs)}" + (f" [{c[0]:+.2f},{c[1]:+.2f}]" if c else "")
    if beat:
        s += f" beat {100 * sum(1 for v in xs if v > 0) / len(xs):.0f}%"
    return s


def norm_side(t):
    return frozenset(cl_toks(t)) if t else frozenset()


def cl_toks(s):
    import clv_scorecard as sc
    return sc.toks(s)


def bet_shape(bet, flip=False):
    pb = cl.parsed({"bet": bet, "flip": flip})
    if not pb:
        return None
    if pb[0] == "total":
        return ("total", str(pb[1]).upper(), pb[2], frozenset())
    return (pb[0], None, pb[2], norm_side(pb[1]))


def same_selection(a, b):
    """a, b: bet shapes. Totals: side and line. Spread/ML: line and a shared team token."""
    if not a or not b or a[0] != b[0] or a[2] != b[2]:
        return False
    if a[0] == "total":
        return a[1] == b[1]
    return bool(a[3] & b[3])


def match_fills(fills, rows):
    """{paper id: fill}. rows: [(id, league, et_day, game_tokens, shape, p_close, entry_net)]. Every condition must hold."""
    out = {}
    for fl in fills:
        fs = bet_shape(fl["bet"])
        ft = frozenset(cl_toks(fl["game"]))
        for rid, lg, day, gt, shape, pc_, _en in rows:
            if (lg == fl["league"] and day == fl["day"] and (gt & ft) and same_selection(shape, fs)
                    and abs(pc_ - fl["pin"]) <= SAME_CLOSE and rid not in out):
                out[rid] = fl
    return out


def captured_fills():
    """The executed_clv per-row export, captured in memory (no email). Included rows only."""
    import executed_clv as ec
    got = []
    ec.send_csv = lambda subject, body, rows, filename: got.extend(rows)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            ec.main()
        except SystemExit:
            pass
    return [{"day": r["day"], "league": r["league"], "game": r["game"], "bet": r["bet"], "venue": r["venue"],
             "am": tb.num(r["fill_american"]), "net": r["fill_net_decimal"], "pin": r["pin_close_novig_prob"],
             "res": r["result"]} for r in got if r.get("included") == 1]


def scorecard_windows():
    """{test label: last-50 window rows}, exactly as last50_report builds them. No email."""
    import last50_report as L
    cap, orig = {}, L.report
    L.report = lambda name, rows, note="", frozen=False: (cap.__setitem__(name, L.window(rows)[0]),
                                                          orig(name, rows, note, frozen))[1]
    L.send_report = lambda *a, **k: True
    with contextlib.redirect_stdout(io.StringIO()):
        L.main()
    return cap


def dogs_rows():
    """Liquidity Dogs as the live lane selects them: first print per game+market+side, dogs_qualifies, a readable bet."""
    import executor as ex
    import last50_report as L
    Q = oa.load(oa.LIQ) or []
    elig = sorted([x for x in Q if isinstance(x, dict) and not x.get("artifact") and not x.get("close_suspect")
                   and str(x.get("book") or "").strip().lower() not in ex.DOGS_NOT_BETTABLE and x.get("alerted_utc")],
                  key=lambda x: x["alerted_utc"])
    first = {}
    for x in elig:
        first.setdefault((str(x.get("game")).lower(), x.get("market"), str(x.get("side")).lower()), x)
    aids = {f"{x.get('key')}|{x.get('alerted_utc')}" for x in first.values()
            if ex.dogs_qualifies(x) and ex.dogs_bet(x)}
    return L.paper_certified([r for r in L.liq_rows() if r["aid"] in aids])


def block(name, w, B, FM):
    import last50_report as L
    say = print
    say("")
    say(name)
    if not w:
        say("  no graded plays")
        return
    h = len(w) // 2
    for tag, part in (("H1", w[:h]), ("H2", w[h:]), ("ALL", w)):
        hs = L.half_stats(part)
        ids = [r.get("pid") or ("liq|" + r["aid"] if r.get("aid") else None) for r in part]
        cert = [r["clv"] for r in part if r.get("clv") is not None]
        base = [B[i]["baseline"] for i in ids if i in B]
        adj = [B[i]["move"] for i in ids if i in B]
        fee = [B[i]["fee"] for i in ids if i in B]
        gross = [B[i]["gross"] for i in ids if i in B]
        mt = [i for i in ids if i in FM]
        fill = [FM[i]["fill_clv"] for i in mt]
        exe = [FM[i]["exec"] for i in mt]
        um = [r["clv"] for r, i in zip(part, ids) if r.get("clv") is not None and i not in FM]
        roi = "n/a" if hs["roi"] is None else f"{hs['roi']:+.1f}%"
        say(f"  {tag:<3} n{hs['n']} {hs['w']}-{hs['l']} {hs['units']:+.2f}u ROI {roi}")
        say(f"      certified CLV        {f_mean(cert, True)}")
        say(f"      zero-move baseline   {f_mean(base)}  (gross alert edge {f_mean(gross)} | fee {f_mean(fee)})")
        say(f"      baseline-adjusted    {f_mean(adj, True)}  (= market movement after the alert)")
        say(f"      fill-price CLV       {f_mean(fill, True)} | execution {f_mean(exe)} | "
            f"certified on unmatched rows {f_mean(um)}")


def main():
    import paper_clv_certify as pc
    import board_build as bb
    st_ = tb.dec(json.load(open(cl.STATE)))
    mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **(st_.get("fixtures") or {}))
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    try:
        lanes = json.load(open(pc.LANES))
    except (OSError, ValueError):
        lanes = {}
    certp = (json.load(open("paper/clv_certified.json")) or {}).get("certified") or {}
    certl = (json.load(open("liquidity/clv_certified.json")) or {}).get("certified") or {}

    # ---------------------------------------------------------------- TEST 1
    B, why, venue, rows = {}, Counter(), {}, []
    for i, x, src, pre in pc.gather(oa.load(oa.SHARP), oa.load(oa.LIQ), lanes, feed):
        rec = certp.get(i) or (certl.get(i[4:]) if i.startswith("liq|") else None)
        if pre or not rec or rec.get("how") not in CERT_HOW or not rec.get("entry_dec"):
            continue
        net, raw = rec["entry_dec"], raw_dec(x, src)
        p_close = (1 + rec["clv_pct"] / 100) / net
        snap = oa.snap_for(x, src)
        st0 = cl.tp(snap.get("game_start"))
        rows.append((i, snap.get("league"), st0.astimezone(ET).strftime("%Y-%m-%d") if st0 else None,
                     frozenset(cl_toks(snap.get("game"))), bet_shape(snap.get("bet")), p_close, net))
        if raw is None:
            why["no raw entry price"] += 1
            continue
        pa, w = fair_at_alert(x, src, rec, allfx, mkmap)
        if pa is None:
            why[w] += 1
            continue
        d = decompose(pa, p_close, raw, net)
        B[i] = d
        v = cs.canon(x.get("book_key") or x.get("book"), strict=False) or str(x.get("book"))
        venue.setdefault(v, []).append(d)

    print("TEST 1 - ZERO-MOVEMENT BASELINE (certified rows only; certified CLV unchanged)")
    print(f"  certified rows {len(rows)} | baseline computed {len(B)} | excluded {sum(why.values())}")
    for k, n in why.most_common():
        print(f"    excluded: {k:<40} {n}")
    print("  BY VENUE        baseline (= gross edge + fee)                     gross alert edge   fee")
    for v in sorted(venue, key=lambda v: -len(venue[v])):
        D = venue[v]
        print(f"    {v:<14} {f_mean([d['baseline'] for d in D]):<46} {m([d['gross'] for d in D]):+.2f}%  "
              f"{m([d['fee'] for d in D]):+.2f}%")

    # ---------------------------------------------------------------- TEST 2
    fills = captured_fills()
    FM = {}
    for rid, fl in match_fills(fills, [r for r in rows if r[2]]).items():
        en = next(r[6] for r in rows if r[0] == rid)
        FM[rid] = {"fill_clv": 100 * (fl["pin"] * fl["net"] - 1), "exec": 100 * fl["pin"] * (fl["net"] - en),
                   "fill": fl}
    used = {id(v["fill"]) for v in FM.values()}
    print("")
    print("TEST 2 - MATCHED FILLS (same league, day, market, line, side and close within 0.002)")
    print(f"  fills with a certified close {len(fills)} | matched to a paper row {len(used)} | "
          f"paper rows matched {len(FM)}")

    # ---------------------------------------------------------------- side by side
    print("")
    print("SIDE BY SIDE - last 50 per test, halves by date order. Certified CLV is the official number.")
    cap = scorecard_windows()
    for name, w in cap.items():
        block(name, w, B, FM)
    import last50_report as L
    dw = L.window(dogs_rows())[0]
    block("LIQUIDITY DOGS - paper record of the live Dogs rule (first print, +100, $25-50k, no sharp tag)", dw, B, FM)
    print("  Charlotte rows in the Dogs window:")
    for r in dw:
        if "charlotte" in str(r["game"]).lower():
            i = "liq|" + r["aid"]
            pct = lambda v: "n/a" if v is None else f"{v:+.2f}%"
            print(f"    {r['ts'][:16]} {r['game'][:40]} {r['am']:+} {r['res']} | certified {pct(r.get('clv'))} | "
                  f"baseline {pct((B.get(i) or {}).get('baseline'))} | fill {pct((FM.get(i) or {}).get('fill_clv'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
