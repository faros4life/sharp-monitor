#!/usr/bin/env python3
"""REGRADE OF THE CANDIDATE-TESTING SCRIPTS (audit of 10 Nov 2026). OFFLINE, CACHE-ONLY, ZERO ODDSPAPI CREDITS.

Runs model_lab.run_league UNCHANGED (same models, edges, FIT/CHECK split and registered bar) twice over the same
cached Pinnacle history, and prints original vs corrected side by side. Only the GRADING inputs differ:
  original  : close may be MODELLED (main line moved by half-point values); quotes up to 24 h old; ProphetX fee
              taken at the 2% scale for every league (league not passed to exchange_lag.eff)
  corrected : close ONLY at the bet's own line (verified same-line, no half-point model); Pinnacle open/close and
              exchange quotes no older than 60 min; ProphetX NHL on its maker/taker scale (league passed);
              FIT/CHECK counted on UNIQUE GAMES (one sighting per game per cell)
No model, rule, threshold or live path is touched. The only non-OddsPapi host reached is ESPN's public scoreboard
(final scores, needed to grade W/L and to build the same ratings); everything betting-related comes from disk.
"""
import os
import sys

import netguard
netguard.refuse_if_proxied(os.environ)
netguard.install(allow=("smtp.gmail.com", "site.api.espn.com"))

import json
import statistics as stt
from datetime import timedelta

import clv_ledger as cl
import exchange_lag as el
import hist_cache as hc
import tracker_build as tb
import model_lab as ml


class _NoNet(RuntimeError):
    pass


def _refuse(*a, **k):
    raise _NoNet("OddsPapi call refused")


cl.api = _refuse
cl.bill = _refuse
cl.load_markets = _refuse
cl.refresh_fixtures = lambda *a, **k: None          # fixtures come from encrypted state on disk
_orig_get_hist = hc.get_hist


def _cached(fid, books, start=None):
    for b in books:
        if not os.path.exists(hc._path(fid, b)):
            return {"_error": "not cached"}
    return _orig_get_hist(fid, books, start)


hc.get_hist = _cached

MODE = {"corrected": False, "lg": None}
O_CANDS, O_CLOSE = ml.cands, ml.close_p


def fresh():
    return timedelta(minutes=60) if MODE["corrected"] else timedelta(hours=24)


def cands(pm, mkmap, sid, typ, when):
    out = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        nmo = {v: k for k, v in outs.items()}
        a, b = (nmo.get("Over"), nmo.get("Under")) if typ == "totals" else (nmo.get("1"), nmo.get("2"))
        tw = cl.two_way(pm, mid, when)
        if a not in tw or b not in tw or when - min(tw[a][1], tw[b][1]) > fresh():
            continue
        out.append({"mid": mid, "line": hcap, "a": a, "b": b, "da": tw[a][0], "db": tw[b][0],
                    "pa": cl.novig_p(tw[a][0], tw[b][0]), "lim": min(tw[a][2], tw[b][2])})
    return out


def close_p(c, typ, line, side_a, lg):
    if not MODE["corrected"]:
        return O_CLOSE(c, typ, line, side_a, lg)
    x = next((x for x in c if abs(x["line"] - line) < 1e-9), None)      # own line only; never modelled
    if not x:
        return None
    return x["pa"] if side_a else 1 - x["pa"]


def ex_best(hist, mkmap, mid, oid, t):
    best = None
    for bk in ml.EXCH:
        m = (cl.book_markets(hist, bk) or {}).get(mid) or {}
        lt = cl.last_tick((((m.get("outcomes") or {}).get(oid) or {}).get("players") or {}).get("0"), t)
        if lt and tb.num(lt[1].get("price")) and t - lt[0] <= fresh():
            dec = (el.eff(bk, float(lt[1]["price"]), league=MODE["lg"]) if MODE["corrected"]
                   else el.eff(bk, float(lt[1]["price"])))
            if best is None or dec > best[0]:
                best = (dec, ml.EXCH[bk])
    return best


ml.cands, ml.close_p, ml.ex_best = cands, close_p, ex_best


def cell(S, key, mid, uniq):
    if uniq:
        seen, U = set(), []
        for s in S:
            k = (s["lg"], s["typ"], s["game"], s["side"])
            if k not in seen:
                seen.add(k)
                U.append(s)
        S = U
    c = [s[key] for s in S if s.get(key) is not None]
    if not c:
        return "n 0", False
    F = [s[key] for s in S if s.get(key) is not None and s["day"] <= mid]
    C = [s[key] for s in S if s.get(key) is not None and s["day"] > mid]

    def ok(v):
        return bool(v) and stt.mean(v) > 0 and sum(x > 0 for x in v) / len(v) >= 0.53
    bar = len(c) >= 100 and ok(F) and ok(C)
    return (f"n {len(c):3d} CLV {stt.mean(c):+6.2f}% beat {100 * sum(x > 0 for x in c) / len(c):3.0f}% "
            f"[FIT {stt.mean(F) if F else float('nan'):+.2f}/{len(F)} CHECK {stt.mean(C) if C else float('nan'):+.2f}/{len(C)}]"), bar


def run(mkmap, st, corrected):
    MODE["corrected"] = corrected
    sigs, why = [], {}
    for lg in ml.LEAGUES:
        if lg in ml.ESPN and (lg in cl.SPORT or lg == "NCAAB"):
            MODE["lg"] = lg
            try:
                ml.run_league(lg, mkmap, st, sigs, why)
            except Exception as e:
                why.setdefault(lg, {})["crashed"] = type(e).__name__
    return sigs, why


def main():
    if cl.KEY or cl.FREE_KEY:
        print("STOP: an OddsPapi key is present")
        return 2
    n = len([x for x in os.listdir(hc.DIR) if x.endswith("__pinnacle.json.gz")]) if os.path.isdir(hc.DIR) else 0
    print(f"preflight: {n} cached Pinnacle files; OddsPapi key present: False")
    if not n:
        print("STOP: cache not restored")
        return 3
    st = {"fixtures": {}, "fx_last": {}, "billable": {}}
    for path in (cl.STATE, "exlag/state.enc", "slowhr/state.enc"):
        try:
            d = tb.dec(json.load(open(path)))
        except Exception as e:
            print(f"STOP-ish: cannot read {path} ({type(e).__name__})")
            continue
        for fid, f in (d.get("fixtures") or d.get("fx") or {}).items():
            st["fixtures"].setdefault(fid, f)
    print(f"fixtures available: {len(st['fixtures'])}")
    mkmap = json.load(open(cl.MKFILE)).get("m") or {}
    res = {}
    for corrected in (False, True):
        res[corrected] = run(mkmap, st, corrected)
        print(f"{'corrected' if corrected else 'original '}: sightings {len(res[corrected][0])}; coverage "
              + "; ".join(f"{k}: {v}" for k, v in res[corrected][1].items()))
    days = sorted({s["day"] for s in res[False][0]})
    mid = days[(len(days) - 1) // 2] if days else ""
    print(f"FIT <= {mid} < CHECK. Cell format: n, mean CLV, beat-close, [FIT mean/n, CHECK mean/n]. Registered bar: >=100, CLV>0, beat>=53% both halves.")
    cells = []
    for lg in ml.LEAGUES:
        for typ in ("all-unders", "all-overs", "totals", "spreads", "moneyline"):
            cells.append((lg, typ))
    for lg, typ in cells:
        row = {}
        for corrected in (False, True):
            S = [s for s in res[corrected][0] if s["lg"] == lg and s["typ"] == typ and (typ.startswith("all-") or s["edge"] >= ml.EDGE_REG)]
            row[corrected] = S
        if not row[False] and not row[True]:
            continue
        print(f"{lg} {typ}{'' if typ.startswith('all-') else ' (edge>=4)'}")
        for key, lab in (("clv", "Pinnacle price"), ("clv_x", "best exch after fees")):
            for corrected in (False, True):
                txt, bar = cell(row[corrected], key, mid, uniq=corrected)
                print(f"   {lab:21s} {'CORRECTED' if corrected else 'original '}: {txt} | bar {'MEETS' if bar else 'no'}")
    print(f"network guard refusals: {netguard.report() or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
