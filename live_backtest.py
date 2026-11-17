#!/usr/bin/env python3
"""READ-ONLY HISTORICAL BACKTEST OF THE THREE LIVE STRATEGIES (Peter, 17 Nov 2026, Project 3). No network, no writes.

Replays every graded alert / frozen board call through the CURRENT live selection code, using only fields stored
at alert time:
  Phase 1  - alerts.json, sent to phone, agree_rules.decide(a) == AGREE and agree_rules.phase1(a, True) eligible.
  R1       - alerts.json, agree_rules.r1(a) eligible, first alert per bet (executor.derive_key), cap 10/day ET.
  Board V3 - board/calls.json frozen v3 PLAY calls on NBA totals, one per game key. recon=True rows were
             reconstructed on Nov 6 rather than frozen at decision time; they are counted separately.
Every strategy: one play per bet key, first in time. Entry = the after-fee price at alert time (alerts carry
price_after_fee; board prices are netted through the venue fee). Sizing is Peter's rule in units: minus money to
win 1u, plus money risk 1u. Certified CLV comes from the committed cache-only certificates (paper/ and
liquidity/clv_certified.json, own line or exact moneyline only) or an alert's own clv_verified close; nothing
else counts and a missing close is never a zero.

NOT replayable from stored data, stated rather than assumed: Muse vetoes, Peter's manual-bet holds, cross-lane
"already bet" conflicts, venue depth. Fills are assumed at the alert price; the live fill rate is reported by
p2-audit Section L, not here. Rules were tuned on part of this history, so each strategy is split at the date its
current rule was adopted: only plays after it are out of sample.
"""
import collections
import json
import math
import sys
from datetime import datetime, timedelta, timezone

import agree_rules as ar
import clv_scorecard as sc
import executor as ex

ET = timezone(timedelta(hours=-5))
# Commit times (UTC) of the gates now deployed. Selection = the lane's current eligibility rule.
ADOPTED = {"Phase 1": "2026-11-05T01:20:00Z",    # 8b2e6ff Matchbook-only out, 12-24h paper (after 3fdce8c NCAAF overs)
           "R1": "2026-11-11T13:24:00Z",         # 46c8d65 R1 lane as specified
           "Board V3": "2026-11-06T03:41:00Z"}   # 3393fcf calls frozen at post (v3 rule 259c46e, Nov 4 20:50)
NO_TOL = "2026-11-13T13:45:00Z"                  # bc911ee no-tolerance value gate, all lanes
ROUTE = "2026-11-17T14:44:00Z"                   # 33167fb trigger venue first, balance to Novig, all lanes
BOARD_CONFIRM_MIN = 15
CERT_HOW = ("own line", "moneyline")


def load(p, k=None):
    try:
        d = json.load(open(p))
    except (OSError, ValueError):
        return {} if k else []
    return (d.get(k) if k else d) if isinstance(d, dict) else d


def et_day(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(ET).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def units(dec, res):
    if dec is None or dec <= 1 or res not in ("W", "L", "P"):
        return None, None
    risk = 1 / (dec - 1) if dec < 2 else 1.0
    return {"W": risk * (dec - 1), "L": -risk, "P": 0.0}[res], risk


def cert_clv(pc, lc, pid, aid=None, a=None):
    for src, i in ((pc, pid), (lc, aid)):
        c = (src or {}).get(i or "")
        if c and c.get("clv_pct") is not None and str(c.get("how") or "own line") in CERT_HOW:
            return c["clv_pct"]
    if a is not None and a.get("clv_verified") is True:
        am = a.get("price_after_fee") if a.get("price_after_fee") is not None else a.get("price")
        return sc.std_clv(a.get("close_fair_prob"), am, a.get("book_key"))
    return None


def alert_plays(A, pc, which):
    out, seen, perday = [], set(), collections.Counter()
    for a in sorted(A, key=lambda a: a.get("alert_utc") or ""):
        if not isinstance(a, dict):
            continue
        if which == "R1":
            ok = ar.r1(a)[0]
        else:
            ok = ar.decide(a).get("verdict") == "AGREE" and ar.phase1(a, True)[0]
        if not ok:
            continue
        k = ex.derive_key({"sport": a.get("sport"), "game": a.get("game"), "bet": a.get("bet"),
                           "start_utc": a.get("start_utc")})
        if not k or k in seen:
            continue
        seen.add(k)
        d = et_day(a.get("alert_utc"))
        if which == "R1":
            if perday[d] >= ex.R1_MAX_PLAYS:
                continue
            perday[d] += 1
        if a.get("result") not in ("W", "L", "P"):
            continue
        am = a.get("price_after_fee") if a.get("price_after_fee") is not None else a.get("price")
        try:
            dec = sc.cl.am_to_dec(float(am))
        except (TypeError, ValueError):
            dec = None
        pid = f"sharp|{a.get('alert_utc')}|{a.get('game')}|{a.get('bet')}|{a.get('book_key')}"
        out.append({"ts": a.get("alert_utc") or "", "day": d, "res": a["result"], "dec": dec, "clv": cert_clv(pc, None, pid, a=a), "recon": False,
                    "lg": a.get("sport")})
    return out


def _t(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def board_plays(C, pc, lc, feed, drop):
    """15-min persistence: a call whose source money was pulled within 15 min of posting never reaches an order.
    'Price not moved toward the side' is NOT reconstructable (no point-in-time price path) and is not applied."""
    out, seen = [], set()
    for k, x in sorted(C.items(), key=lambda kv: kv[1].get("at") or ""):
        if x.get("call") != "PLAY" or x.get("mk") != "total" or (x.get("league") or x.get("lg")) != "NBA":
            continue
        src, at = feed.get(k), _t(x.get("at"))
        if src is None:
            drop["no source alert"] += 1
            continue
        pu = _t(src.get("pulled_utc")) if src.get("pulled") else None
        if pu and at and pu <= at + timedelta(minutes=BOARD_CONFIRM_MIN):
            drop["pulled within 15 min"] += 1
            continue
        g = (x.get("day"), frozenset(sc.toks(x.get("game"))))
        if g in seen:
            continue
        seen.add(g)
        if x.get("result") not in ("W", "L", "P"):
            continue
        try:
            dec = sc.cs.net_dec(sc.cs.canon(x.get("book")), sc.cl.am_to_dec(float(x.get("price"))))
        except Exception:
            dec = None
        out.append({"ts": x.get("at") or "", "day": x.get("day") or et_day(x.get("at")), "res": x["result"], "dec": dec,
                    "clv": cert_clv(pc, lc, f"liq|{k}", aid=k), "recon": bool(x.get("recon")), "lg": "NBA"})
    return out


def summ(rows):
    w = sum(r["res"] == "W" for r in rows)
    l = sum(r["res"] == "L" for r in rows)
    u = rk = 0.0
    for r in rows:
        a, b = units(r["dec"], r["res"])
        if a is not None:
            u += a
            rk += b
    c = [r["clv"] for r in rows if r["clv"] is not None]
    m = sum(c) / len(c) if c else None
    se = (math.sqrt(sum((v - m) ** 2 for v in c) / (len(c) - 1)) / math.sqrt(len(c))) if len(c) > 1 else None
    return {"n": len(rows), "w": w, "l": l, "u": u, "roi": 100 * u / rk if rk else None, "clv": m, "se": se, "cn": len(c)}


def line(tag, s):
    if not s["n"]:
        return f"  {tag:<22} n 0"
    roi = f"{s['roi']:+.1f}%" if s["roi"] is not None else "-"
    if s["clv"] is None:
        cv = "CLV - (0 certified)"
    else:
        ci = f" [{s['clv'] - 1.96 * s['se']:+.2f}, {s['clv'] + 1.96 * s['se']:+.2f}]" if s["se"] else ""
        cv = f"CLV {s['clv']:+.2f}%{ci} on {s['cn']}/{s['n']}"
    return f"  {tag:<22} n {s['n']:>3}  {s['w']}-{s['l']}  {s['u']:+6.2f}u  ROI {roi:>7}  {cv}"


def main():
    A = load("alerts.json", "alerts") or []
    C = load("board/calls.json", "calls") or {}
    import board_build as bb
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    drop = collections.Counter()
    pc = (load("paper/clv_certified.json") or {}).get("certified") or {}
    lc = (load("liquidity/clv_certified.json") or {}).get("certified") or {}
    print("LIVE STRATEGY BACKTEST - read-only, current rules, alert-time fields, cache-only certified CLV")
    for name, rows in (("Phase 1", alert_plays(A, pc, "P1")), ("R1", alert_plays(A, pc, "R1")),
                       ("Board V3", board_plays(C, pc, lc, feed, drop))):
        rows.sort(key=lambda r: r["ts"])
        cut = ADOPTED[name]
        print(f"\n{name}: {rows[0]['day'] if rows else '-'} to {rows[-1]['day'] if rows else '-'}; selection rule {cut}")
        print(line("RETRO all (what-if)", summ(rows)))
        print(line("retro before rule", summ([r for r in rows if r["ts"] < cut])))
        print(line("FORWARD since rule", summ([r for r in rows if r["ts"] >= cut])))
        print(line("FORWARD since no-tol", summ([r for r in rows if r["ts"] >= NO_TOL])))
        print(line("since routing Nov 17", summ([r for r in rows if r["ts"] >= ROUTE])))
        l50 = rows[-50:]
        h = len(l50) // 2
        print(line(f"last {len(l50)}", summ(l50)))
        print(line("  first half", summ(l50[:h])))
        print(line("  second half", summ(l50[h:])))
        if any(r["recon"] for r in rows):
            print(line("reconstructed calls", summ([r for r in rows if r["recon"]])))
            print(line("frozen calls", summ([r for r in rows if not r["recon"]])))
        if name == "Board V3":
            print("  excluded by persistence/source:", dict(drop))
        print("  by league:", {k: f"{s['w']}-{s['l']} {s['u']:+.2f}u" for k, s in
                               ((lg, summ([r for r in rows if r["lg"] == lg])) for lg in sorted({r["lg"] for r in rows}))})
    return 0


if __name__ == "__main__":
    sys.exit(main())
