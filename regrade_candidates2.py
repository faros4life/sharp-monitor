#!/usr/bin/env python3
"""REGRADE 2 (audit of 10 Nov 2026): nba_backtest, nba_backtest2, p1_backtest, x2_backtest. OFFLINE, CACHE-ONLY, ZERO CREDITS.
Each script's own code and registered rules run UNCHANGED (p1 by executing its source with two labelled one-line
captures); only the grading inputs differ between 'original' and 'corrected':
  corrected : close ONLY at the bet's own line (no half-point model / 'main moved'); every Pinnacle and exchange quote
              no older than 60 min; exchange quotes at or BEFORE decision time only (no later-quote look-ahead);
              league passed to the fee model; unique games (one sighting per game per cell).
Only non-cache host reached: ESPN public scores (nba scripts). Nothing here touches live code, the ledger or kill switch."""
import os
import sys

import netguard
netguard.refuse_if_proxied(os.environ)
netguard.install(allow=("smtp.gmail.com", "site.api.espn.com"))

import json
import statistics as stt
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import exchange_lag as el
import executor as ex
import hist_cache as hc
import tracker_build as tb

MODE = {"c": False, "lg": None}
MK = json.load(open(cl.MKFILE)).get("m") or {}
_orig_get_hist = hc.get_hist
OLD = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _cached(fid, books, start=None):
    for b in books:
        if not os.path.exists(hc._path(fid, b)):
            return {"_error": "not cached"}
    return _orig_get_hist(fid, books, OLD)


hc.get_hist = _cached


def _refuse(*a, **k):
    raise RuntimeError("OddsPapi call refused")


def _api(path, paid=False, **kw):
    if path == "/historical-odds":
        return _cached(kw.get("fixtureId"), [x for x in (kw.get("bookmakers") or "pinnacle").split(",")])
    raise RuntimeError("OddsPapi call refused: " + path)


cl.api, cl.bill = _api, _refuse
cl.load_markets = lambda st, now: MK
cl.refresh_fixtures = lambda *a, **k: None
ex.send = lambda *a, **k: None
STATE_FX = {}
for path in (cl.STATE, "exlag/state.enc", "slowhr/state.enc"):
    try:
        d = tb.dec(json.load(open(path)))
        for fid, f in (d.get("fixtures") or d.get("fx") or {}).items():
            STATE_FX.setdefault(fid, f)
    except Exception as e:
        print(f"cannot read {path}: {type(e).__name__}")
_real_dec = tb.dec


def fresh():
    return timedelta(minutes=60) if MODE["c"] else timedelta(hours=24)


def say(t=""):
    print(t)


def cellstat(xs, split, uniq_key=None, bar_n=100, rows_n=None):
    """xs: dicts with day, clv. Returns (text, bar) with FIT/CHECK on unique games if uniq_key."""
    if uniq_key:
        seen, U = set(), []
        for x in xs:
            k = x[uniq_key]
            if k not in seen:
                seen.add(k)
                U.append(x)
        xs = U
    c = [x["clv"] for x in xs if x.get("clv") is not None]
    if not c:
        return "n 0", False
    F = [x["clv"] for x in xs if x.get("clv") is not None and x["day"] <= split]
    C = [x["clv"] for x in xs if x.get("clv") is not None and x["day"] > split]

    def ok(v):
        return bool(v) and stt.mean(v) > 0 and sum(a > 0 for a in v) / len(v) >= 0.53
    bar = (rows_n if rows_n is not None else len(c)) >= bar_n and ok(F) and ok(C)
    m = lambda v: f"{stt.mean(v):+.2f}" if v else "  n/a"
    return (f"n {len(c):3d} CLV {stt.mean(c):+6.2f}% beat {100 * sum(a > 0 for a in c) / len(c):3.0f}% "
            f"[FIT {m(F)}/{len(F)} CHECK {m(C)}/{len(C)}]"), bar


# ------------------------------------------------------------------ NBA 1 and 2
def run_nba():
    import nba_backtest as b1
    import nba_backtest2 as b2
    cap = {}
    b1_p_at, b1_fresh = b1.p_at, b1.FRESH
    b2_novig = b2.novig_at

    def p_at(cands, line, side):
        if not MODE["c"]:
            return b1_p_at(cands, line, side)
        x = next((x for x in cands if abs(x[0] - line) < 1e-9), None)      # own line only
        if not x:
            return None
        return x[3] if side == "Over" else 1 - x[3]

    def novig_at(xm, mkmap, line, side, t):
        if not MODE["c"]:
            return b2_novig(xm, mkmap, line, side, t)
        for mid, (s, ty, hcap, outs) in mkmap.items():
            if s != 11 or ty != "totals" or abs(hcap - line) > 1e-9 or mid not in xm:
                continue
            oid = {v: k for k, v in outs.items()}.get(side)
            tk = []
            for x in (((xm[mid].get("outcomes") or {}).get(oid) or {}).get("players") or {}).get("0") or []:
                c, p = cl.tp(x.get("createdAt")), tb.num(x.get("price"))
                if c and p and p > 1:
                    tk.append((c, p, tb.num(x.get("limit"))))
            tk.sort()
            before = [x for x in tk if x[0] <= t and t - x[0] <= fresh()]     # never a later tick
            if before:
                x = before[-1]
                return x[1], x[0], x[2], 0
        return None

    b1.p_at, b2.novig_at = p_at, novig_at
    b1.report = lambda rows, why, n: cap.__setitem__("b1", rows)
    b2.report = lambda rows, why, n: cap.__setitem__("b2", rows)
    # the nba scripts read cl.KEY only as a guard; the placeholder is not a credential and cl.api is replaced above
    cl.KEY = "AUDIT-NO-CREDENTIAL"
    out = {}
    for corrected in (False, True):
        MODE["c"] = corrected
        b1.FRESH = fresh()
        for nm_, mod in (("b1", b1), ("b2", b2)):
            cap.pop(nm_, None)
            try:
                mod.main()
            except Exception as e:
                say(f"{nm_} {'corrected' if corrected else 'original'} crashed: {type(e).__name__} {str(e)[:80]}")
            out[(nm_, corrected)] = cap.get(nm_) or []
    split = b1.SPLIT
    say(f"NBA FIT <= {split} < CHECK; bar per cell: >=100 games graded, CLV>0 and beat>=53% in FIT and CHECK (gap>=3.0, one row per game)")
    for corrected in (False, True):
        say(f"  games graded {'corrected' if corrected else 'original '}: b1 {len(out[('b1', corrected)])}, b2 {len(out[('b2', corrected)])}")
    for k in ("OPEN", "T-6h", "T-2h"):
        for corrected in (False, True):
            rows = out[("b1", corrected)]
            xs = [dict(day=r["day"], clv=r["sig"][f"REG|{k}"]["clv"], g=r["id"]) for r in rows
                  if f"REG|{k}" in r.get("sig", {}) and abs(r["sig"][f"REG|{k}"]["gap"]) >= 3.0]
            t, bar = cellstat(xs, split, "g", rows_n=len(rows))
            say(f"nba_backtest REG {k:5s} Pinnacle price {'CORRECTED' if corrected else 'original '}: {t} | {'MEETS' if bar else 'no'}")
    for v in ("REG", "REG+B"):
        for k in ("OPEN", "T-6h"):
            for px in ("PIN", "NOVIG", "PROPHETX", "KALSHI", "POLY", "BEST"):
                for corrected in (False, True):
                    rows = out[("b2", corrected)]
                    key = f"{v}|{k}|{px}"
                    xs = [dict(day=r["day"], clv=r["sig"][key]["clv"], g=r["game"]) for r in rows
                          if key in r["sig"] and abs(r["sig"][key]["gap"]) >= 3.0]
                    if not xs and corrected is False:
                        break
                    t, bar = cellstat(xs, split, "g", rows_n=len(rows))
                    say(f"nba_backtest2 {v:5s} {k:5s} {px:8s} {'CORRECTED' if corrected else 'original '}: {t} | {'MEETS' if bar else 'no'}")
    for px in ("NOVIG", "PROPHETX", "KALSHI", "POLY"):
        d = [r["sig"][f"REG+B|OPEN|{px}"]["delay"] for r in out[("b2", False)] if f"REG+B|OPEN|{px}" in r["sig"]]
        if d:
            say(f"look-ahead in original nba_backtest2 {px}: {sum(1 for x in d if x > 0)} of {len(d)} OPEN quotes were taken AFTER the decision time")


# ------------------------------------------------------------------ P1
def run_p1():
    import inspect
    import p1_backtest as m
    src = inspect.getsource(m.main)
    src = src.replace('    days = sorted({r["day"] for r in R})', '    CAP["R"] = R\n    days = sorted({r["day"] for r in R})', 1)
    src = src.replace('R.append({"p1": p1(a),', 'R.append({"game": a.get("game"), "p1": p1(a),', 1)
    assert 'CAP["R"]' in src and '"game": a.get("game")' in src, "p1 capture points not found"
    cap = {}
    ns = m.__dict__
    ns["CAP"] = cap
    exec(compile(src, "p1_main_patched", "exec"), ns)
    patched_main = ns["main"]
    o_close_for, o_novig, o_eff, o_fresh = cl.close_for, cl.novig_at, el.eff, cl.FRESH_MIN
    cl.KEY = "AUDIT-NO-CREDENTIAL"
    # the originals are read from the module source above; wrappers apply only in corrected mode
    cl.close_for = lambda *a, **k: ((lambda r: r if (r[0] and cs.close_verified(r[0]["how"])) else (None, "modelled close excluded"))(o_close_for(*a, **k))
                                    if MODE["c"] else o_close_for(*a, **k))

    def novig(b, f, nm_pm, mkmap, when, lg):
        MODE["lg"] = lg
        x = o_novig(b, f, nm_pm, mkmap, when, lg)
        if MODE["c"] and x and x[1] > 3600:
            return None
        return x
    cl.novig_at = novig
    el.eff = lambda book, dec, **k: o_eff(book, dec, league=MODE["lg"]) if MODE["c"] else o_eff(book, dec, **k)
    res = {}
    for corrected in (False, True):
        MODE["c"] = corrected
        cl.FRESH_MIN = 60 if corrected else o_fresh
        cap.clear()
        try:
            patched_main()
        except Exception as e:
            say(f"p1 {'corrected' if corrected else 'original'} crashed: {type(e).__name__} {str(e)[:80]}")
        res[corrected] = list(cap.get("R") or [])
    allr = res[False] + res[True]
    days = sorted({r["day"] for r in res[False]})
    mid = days[(len(days) - 1) // 2] if days else "2026-10-24"
    say(f"P1: H1 <= {mid} < H2 (median alert day). No numeric bar was registered; shown on the house bar (CLV>0, beat>=53% in both halves, n>=100 unique games)")
    for lab, sel in (("PHASE-1 ALL", lambda r: True), ("PHASE-1 TOTALS", lambda r: r["mk"] == "totals"), ("PHASE-1 SPREADS", lambda r: r["mk"] == "spreads")):
        for basis, bl in (("g", "+5min exchange price"), ("a", "alert price")):
            for corrected in (False, True):
                P = [r for r in res[corrected] if r["p1"] and r["sent"] and not r["late"] and sel(r)]
                P = sorted(P, key=lambda r: -(r["lead"] or 0))
                xs = [dict(day=r["day"], clv=r[f"clv_{basis}"], g=(r["lg"], r["game"], r["mk"])) for r in P]
                t, bar = cellstat(xs, mid, "g")
                say(f"{lab:16s} {bl:21s} {'CORRECTED' if corrected else 'original '}: {t} | {'MEETS' if bar else 'no'}")


# ------------------------------------------------------------------ X2
def run_x2():
    import x2_backtest as m
    cl.KEY = "AUDIT-NO-CREDENTIAL"
    rs = m.rows()
    st = {"fixtures": dict(STATE_FX), "bets": {}}
    mk_ = MK
    res = []
    for r in rs:
        teams = r.get("teams") or []
        b = {"league": r["league"], "game": r.get("game"), "teams": [{"name": x} for x in teams], "game_start": r.get("start_utc")}
        fid = cl.find_fixture(st, b)
        if not fid:
            continue
        h = _cached(fid, ["pinnacle"])
        if isinstance(h, dict) and h.get("_error"):
            continue
        pm = cl.book_markets(h, "pinnacle")
        f = st["fixtures"][fid]
        when = tb.tparse(r.get("alerted_utc"))
        lim, how, _ = m.limit_at(r, f, pm, mk_, when)
        if lim is None:
            continue
        dep = {x: m.depth(r, x) for x in m.EXCH}
        tot = sum(dep.values())
        two5k = sum(1 for v in dep.values() if v >= 5000) >= 2
        start = cl.tp(f.get("start")) or tb.tparse(r.get("start_utc"))
        # corrected close: Pinnacle OWN line, both sides, last tick at/before start, no older than 60 min
        pcl = None
        sid = cl.SPORT[r["league"]]
        mk = r["market"]
        side, line = r.get("side"), r.get("line")
        try:
            if mk == "moneyline":
                held = cl.which_team(f, str(side))
                typ, want, name = "moneyline", None, held
            elif mk == "total":
                typ, want, name = "totals", float(line), ("Over" if str(side).upper() == "OVER" else "Under")
            else:
                held = cl.which_team(f, str(side))
                typ, name = "spreads", held
                want = None if (held is None or line is None) else (float(line) if held == "1" else -float(line))
            other = {"Over": "Under", "Under": "Over", "1": "2", "2": "1"}.get(name)
            if name and other and start:
                for mid, (s, ty, hcap, outs) in mk_.items():
                    if s != sid or ty != typ or mid not in pm or (want is not None and abs(hcap - want) > 1e-9):
                        continue
                    nm = {v: k for k, v in outs.items()}
                    tw = cl.two_way(pm, mid, start)
                    a_, b_ = nm.get(name), nm.get(other)
                    if a_ in tw and b_ in tw and start - min(tw[a_][1], tw[b_][1]) <= timedelta(minutes=60):
                        pcl = cl.novig_p(tw[a_][0], tw[b_][0])
                        break
        except Exception:
            pcl = None
        res.append({"league": r["league"], "market": mk, "game": r.get("game"), "day": str(r.get("alerted_utc"))[:10],
                    "pass_RAW": bool(tot >= 2 * lim and two5k and tot >= 25000), "pass_OJ": bool(tot >= 2 * lim * 4 / 3 and two5k and tot >= 25000),
                    "clv_o": (float(r["clv_cents"]) - m_fee(m, r)) if r.get("clv_cents") is not None else None,
                    "clv_c": (100 * (pcl - float(r["price"])) - m_fee(m, r)) if (pcl is not None and r.get("price")) else None,
                    "g": (r["league"], r.get("game"), r.get("side_label"))})
    days = sorted({x["day"] for x in res})
    mid = days[(len(days) - 1) // 2] if days else ""
    say(f"X2: rows matched {len(res)}; FIT <= {mid} < CHECK. CLV in cents of probability AFTER FEES at the row's book/price. Registered gate = 2X pass; house bar CLV>0 both halves (>=30 rows per half as in x2's HOLDS).")
    for gate in ("pass_RAW", "pass_OJ"):
        for key, lab in (("clv_o", "original (monitor's stored close)"), ("clv_c", "CORRECTED (verified own-line close, <=60min)")):
            xs = [dict(day=x["day"], clv=x[key], g=x["g"]) for x in res if x[gate]]
            c = [x["clv"] for x in xs if x["clv"] is not None]
            if key == "clv_c":
                seen, U = set(), []
                for x in xs:
                    if x["g"] not in seen:
                        seen.add(x["g"])
                        U.append(x)
                xs = U
            c = [x["clv"] for x in xs if x["clv"] is not None]
            F = [x["clv"] for x in xs if x["clv"] is not None and x["day"] <= mid]
            C = [x["clv"] for x in xs if x["clv"] is not None and x["day"] > mid]
            holds = len(F) >= 30 and len(C) >= 30 and stt.mean(F) > 0 and stt.mean(C) > 0 if F and C else False
            say(f"{gate} {lab:46s}: n {len(c):3d} mean {stt.mean(c) if c else float('nan'):+.2f}c [FIT {stt.mean(F) if F else float('nan'):+.2f}/{len(F)} CHECK {stt.mean(C) if C else float('nan'):+.2f}/{len(C)}] | {'HOLDS' if holds else 'no'}")


def m_fee(m, r):
    """x2's own fee_c, reproduced exactly (cents of probability at the row's book and price)."""
    p, bk = tb.num(r.get("price")), (r.get("book") or "").lower()
    if not p or not 0 < p < 1:
        return 0.0
    if bk == "prophetx":
        return 100 * (1 / (1 + (1 / p - 1) * 0.98) - p)
    if bk == "kalshi":
        return 100 * 0.07 * p * (1 - p)
    if bk in ("polymarket_us", "polymarket.us"):
        return 100 * ex.PMUS_FEE * p * (1 - p)
    if bk.startswith("polymarket"):
        return 100 * 0.03 * p * (1 - p)
    return 0.0


def main():
    if cl.KEY or cl.FREE_KEY:
        say("STOP: OddsPapi key present")
        return 2
    n = len([x for x in os.listdir(hc.DIR) if x.endswith("__pinnacle.json.gz")]) if os.path.isdir(hc.DIR) else 0
    say(f"preflight: {n} cached Pinnacle files; OddsPapi key present: False; fixtures on disk {len(STATE_FX)}")
    if not n:
        say("STOP: cache not restored")
        return 3
    for nm_, fn in (("NBA 1+2", run_nba), ("P1", run_p1), ("X2", run_x2)):
        say("")
        say(f"=== {nm_}")
        try:
            fn()
        except Exception as e:
            say(f"{nm_} failed: {type(e).__name__} {str(e)[:120]}")
    say(f"network guard refusals: {netguard.report() or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
