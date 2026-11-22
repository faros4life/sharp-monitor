#!/usr/bin/env python3
"""DAILY LAST-50 REPORT - deterministic, no model in the loop (Peter, 13 Nov).

For every test whose per-play records are readable in this repo, take the LAST 50 graded plays
(one play = game + market + side, first alert only), split 25 older / 25 newer, and report units,
ROI, standardized CLV and n for each half and overall. CLV is the ONE adopted basis only:
(Pinnacle no-vig close prob x net entry decimal AFTER FEES - 1) x 100, via clv_scorecard.std_clv
and clv_std. No stored CLV field is read. Rows without a usable close are EXCLUDED AND COUNTED,
never substituted. Where a test has no standard CLV the CLV cell says "n/a" and the test cannot
be called a pass.

Read-only: no bet, no rule, no threshold, no registry change. Flat 1u at the logged price, so
the output carries units and percentages only - no dollars, stakes or balances.
Tests whose data is not in these files are listed UNANSWERED with the reason.

Verdict ladder (policy of 11 Nov): n < 50 -> NO VERDICT. Else CLEAR FAIL only if the units CI sits
below zero; POTENTIAL PASS only if both halves are positive on units AND on certified CLV AND the
units CI sits above zero; everything else CONTINUE TESTING. A 50-play window is noisy, so every
units figure prints its 95% CI.
"""
import csv
import io
import json
import os
import random
import re
import statistics as st
import sys
from collections import Counter

import clv_scorecard as sc

N = 50
SEED = 20261113
L = []


def say(t=""):
    L.append(t)
    if os.environ.get("LAST50_PRINT") == "1":   # public Actions log: counts only, so print only when asked locally
        print(t)


def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return None
    if isinstance(d, list):
        return d
    for k in ("alerts", "bets"):
        if isinstance(d, dict) and isinstance(d.get(k), list):
            return d[k]
    return d


def am_from_prob(p):
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if not 0 < p < 1:
        return None
    return round(100 * (1 - p) / p) if p < 0.5 else -round(100 * p / (1 - p))


def unit_of(am, res):
    if am is None or res not in ("W", "L"):
        return None
    return (am / 100 if am > 0 else 100 / abs(am)) if res == "W" else -1.0


def ci_mean(xs):
    """95% bootstrap CI of the mean, seeded so the same data prints the same interval."""
    if len(xs) < 2:
        return None
    rnd = random.Random(SEED)
    ms = sorted(st.mean(rnd.choices(xs, k=len(xs))) for _ in range(2000))
    return ms[50], ms[1949]


def window(rows):
    """Dedupe to one play per key (first alert), order by time, keep the last N graded."""
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r["ts"]):
        if r["res"] not in ("W", "L", "P") or r["key"] in seen:
            continue
        seen.add(r["key"])
        out.append(r)
    return out[-N:], len(out)


def half_stats(xs):
    graded = [r for r in xs if r["res"] in ("W", "L")]
    us = [unit_of(r["am"], r["res"]) for r in graded]
    us = [u for u in us if u is not None]
    clvs = [r["clv"] for r in xs if r.get("clv") is not None]
    ex = [r for r in xs if r.get("us_exec", True)]          # s7 operational population (all rows when unmarked)
    ex_g = [r for r in ex if r["res"] in ("W", "L")]
    ex_u = [u for u in (unit_of(r["am"], r["res"]) for r in ex_g) if u is not None]
    pcl = [r["pclv"] for r in xs if r.get("pclv") is not None]
    return {"n": len(xs), "w": sum(1 for r in xs if r["res"] == "W"),
            "l": sum(1 for r in xs if r["res"] == "L"), "units": sum(us),
            "roi": (100 * sum(us) / len(us)) if us else None, "us": us,
            "clv": st.mean(clvs) if clvs else None, "clv_n": len(clvs), "clv_ci": ci_mean(clvs),
            "clv_pos_pct": (100 * sum(1 for c in clvs if c > 0) / len(clvs)) if clvs else None,
            "pclv": st.mean(pcl) if pcl else None, "pclv_n": len(pcl),
            "exec_n": len(ex), "exec_w": sum(1 for r in ex if r["res"] == "W"), "exec_l": sum(1 for r in ex if r["res"] == "L"),
            "exec_units": sum(ex_u), "exec_roi": (100 * sum(ex_u) / len(ex_u)) if ex_u else None,
            "pclv_src": next((r.get("pclv_src") for r in xs if r.get("pclv") is not None), None)}


def fmt(h):
    roi = "n/a" if h["roi"] is None else f"{h['roi']:+.1f}%"
    clv = "n/a" if h["clv"] is None else (f"{h['clv']:+.2f}% (n {h['clv_n']}, beat close {h['clv_pos_pct']:.0f}%"
                                          + (f", 95% CI [{h['clv_ci'][0]:+.2f}, {h['clv_ci'][1]:+.2f}]" if h.get("clv_ci") else "") + ")")
    if h.get("exec_n") is not None and h["exec_n"] != h["n"]:
        clv += (f" | coverage {h['clv_n']}/{h['exec_n']} US-executable, {h['clv_n']}/{h['n']} whole population"
                f" | executable subset {h['exec_w']}-{h['exec_l']} {h['exec_units']:+.2f}u")
    pv = "" if not h.get("pclv_n") else f" | provisional, NOT certified: {h['pclv']:+.2f}% (n {h['pclv_n']})"
    return f"n {h['n']:2d} | {h['w']}-{h['l']} | {h['units']:+6.2f}u | ROI {roi} | CERTIFIED CLV {clv}{pv}"


def verdict(w, h1, h2, ho):
    if len(w) < N:
        return "NO VERDICT (n<50)"
    ci = ci_mean(ho["us"])
    if ci and ci[1] < 0:
        return "CLEAR FAIL"
    den = ho.get("exec_n", ho["n"])   # CLV_STANDARD.md s7 (14 Nov): eligible US-executable rows are the denominator
    if ho["clv_n"] < 0.8 * den:
        # without certified CLV on 80%+ of the executable window there is nothing to qualify on
        return f"INSUFFICIENT EVIDENCE (certified CLV {ho['clv_n']}/{den} executable, {ho['clv_n']}/{ho['n']} all)"
    cc = ho.get("clv_ci")
    if cc and cc[1] < 0:
        # SCORECARD.md: CLEAR FAIL also on "a precise and representative certified-CLV CI excluding zero negative"
        # (representative = certified on 80%+ of the EXECUTABLE window, s7, checked above)
        return f"CLEAR FAIL (certified CLV 95% CI {cc[0]:+.2f} to {cc[1]:+.2f}, below zero)"
    clv_ok = all(h["clv"] is not None and h["clv"] > 0 and h["clv_n"] >= 0.8 * h.get("exec_n", h["n"]) for h in (h1, h2))
    if ci and ci[0] > 0 and h1["units"] > 0 and h2["units"] > 0 and clv_ok:
        return "POTENTIAL PASS"
    return "CONTINUE TESTING"


def report(name, rows, note="", frozen=False):
    """One block per test. Returns (status, csv rows)."""
    w, total = window(rows)
    say("")
    say(f"{name}" + ("   [FROZEN - closed test, read-only regrade]" if frozen else ""))
    if note:
        say(f"  {note}")
    if not w:
        say("  UNANSWERED: no graded plays in the data this report can read")
        return "UNANSWERED", []
    h = len(w) // 2
    h1, h2, ho = half_stats(w[:h]), half_stats(w[h:]), half_stats(w)
    ci = ci_mean(ho["us"])
    say(f"  window: last {len(w)} of {total} graded plays | {w[0]['ts'][:10]} to {w[-1]['ts'][:10]}")
    say(f"  H1 (older)   {fmt(h1)}")
    say(f"  H2 (newer)   {fmt(h2)}")
    say(f"  OVERALL      {fmt(ho)}")
    if ci:
        say(f"  per-play units 95% CI [{ci[0]:+.2f}, {ci[1]:+.2f}] (n {len(ho['us'])})")
    v = verdict(w, h1, h2, ho)
    full = ho["clv"] is not None and ho["clv_n"] >= 0.8 * ho.get("exec_n", ho["n"])
    status = "ANSWERED" if len(w) >= N and full else "PARTIAL"
    say(f"  STATUS {status} | VERDICT {v} | CONFIDENCE {confidence(ho['n'], ho['clv_n'], ho.get('exec_n'))}")
    if ho["clv"] is None:
        say("  CLV: n/a - no standard (Pinnacle same-line, after-fee) close on these rows; cannot pass")
    elif ho["clv_n"] < ho["n"]:
        say(f"  CLV coverage {ho['clv_n']}/{ho['n']} rows usable; the rest are EXCLUDED, not estimated")
    out = [{"test": name, "half": "H1" if i < h else "H2", "ts": r["ts"], "game": r["game"],
            "price_am": r["am"], "result": r["res"], "certified_clv_pct": ("" if r["clv"] is None else round(r["clv"], 3)),
            "provisional_clv_pct_not_certified": ("" if r.get("pclv") is None else round(r["pclv"], 3)),
            "provisional_source": r.get("pclv_src") or ""}
           for i, r in enumerate(w)]
    return status, out


# --------------------------------------------------------------------------- populations
# 16 Nov (Peter): "clv" on a row is CERTIFIED Pinnacle CLV only. Anything else lives in "pclv", labelled by source,
# and never reaches a CLV heading, a verdict or a confidence grade.
PROV_ALERT = "provisional: live feed read 5-30 min before start, line not verified (clv_verified False)"
PROV_VENUE = "not Pinnacle: the alerting venue's own last pregame price"


def liq_certified(rows, path="liquidity/clv_certified.json", field="aid", keep=False):
    """16 Nov: certified Pinnacle CLV from liq_clv_certify (cache-only, clv_obs_audit waterfall) onto LIQ rows.
    Applied ONLY to LIQ-SMALL and LIQ-BOT. A row without a certified entry keeps clv None; its venue close stays
    in pclv, labelled. Returns new row dicts; the inputs and their W-L/units are untouched."""
    try:
        cert = (json.load(open(path)) or {}).get("certified") or {}
    except (OSError, ValueError):
        cert = {}
    try:
        rej = (json.load(open(path)) or {}).get("rejected") or {}
    except (OSError, ValueError):
        rej = {}
    out = []
    for r in rows:
        c = cert.get(r.get(field) or "")
        fill = c and c.get("clv_pct") is not None and not (keep and r.get("clv") is not None)
        o = dict(r, clv=c["clv_pct"]) if fill else dict(r)
        # CLV_STANDARD.md s7: a venue that cannot be bet from the US is outside the operational denominator.
        # ONLY that exact class; a missing close on an executable venue stays in as a genuine gap.
        why = str(rej.get(r.get(field) or "") or "")
        o["us_exec"] = not (why.startswith("VENUE_NOT_PRICEABLE") and "not tradeable from the US" in why)
        out.append(o)
    return out


def paper_certified(rows, path="paper/clv_certified.json"):
    """17 Nov: certified Pinnacle CLV from paper_clv_certify (cache-only, same waterfall) onto the other paper tests,
    keyed by each row's "pid". Fills clv ONLY where the row has none; provisional values stay in pclv, labelled.
    A missing close is never a zero. s7: Polymarket Global rows leave the operational denominator, nothing else."""
    return liq_certified(rows, path, field="pid", keep=True)


def sharp_rows():
    S = load("alerts.json") or []
    rows = []
    for x in S:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P"):
            continue
        am = x.get("price_after_fee") if x.get("price_after_fee") is not None else x.get("price")
        c = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        cert = x.get("clv_verified") is True     # 16 Nov: the writer marks a live feed read PROVISIONAL (False)
        g = frozenset(sc.toks(x.get("game")))
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": c if cert else None, "pclv": None if cert else c,
                     "pclv_src": PROV_ALERT, "sent": bool(x.get("sent_to_phone")),
                     "pid": f"sharp|{x.get('alert_utc')}|{x.get('game')}|{x.get('bet')}|{x.get('book_key')}",
                     "lg": x.get("sport"), "kind": x.get("kind"), "bet": str(x.get("bet") or ""),
                     "key": (str(x.get("alert_utc") or "")[:10], g, str(x.get("kind")), str(x.get("bet") or ""))})
    return rows


def liq_rows():
    Q = load("liquidity/alerts.json") or []
    rows = []
    for x in Q:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or x.get("artifact") or x.get("close_suspect"):
            continue
        am = x.get("price_american")
        c = sc.std_clv(x.get("close_price"), am, x.get("book"))
        # 16 Nov: close_price is the ALERTING VENUE'S own last pregame price (liquidity_monitor), not Pinnacle.
        rows.append({"ts": str(x.get("alerted_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": None, "pclv": c, "pclv_src": PROV_VENUE,
                     "aid": f"{x.get('key')}|{x.get('alerted_utc')}",
                     "pid": f"liq|{x.get('key')}|{x.get('alerted_utc')}",
                     "lg": x.get("league"), "mk": x.get("market"),
                     "side": x.get("side"), "book": x.get("book"), "lead": x.get("lead_min"),
                     "nm": x.get("new_money"),
                     "key": (str(x.get("alerted_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             x.get("market"), x.get("side"))})
    return rows


def lane_rows(name):
    d = (load("lanes/lanes.json") or {}).get(name) or {}
    rows = []
    for k, x in d.items():
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or not x.get("entered"):
            continue
        am = am_from_prob(x.get("price"))
        rows.append({"ts": str(x.get("snapshot_utc") or x.get("detected_utc") or ""), "game": x.get("game") or "",
                     "am": am, "res": x["result"], "clv": None, "pid": f"lane:{name}|{k}",
                     "key": (str(x.get("start_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             x.get("market"), x.get("side") or x.get("pulled_side"))})
    return rows


HR1_START = "2026-11-18"   # Peter, 18 Nov: "start the hr1 fresh today with 0. We only count live plays."


def hr1_live_rows(acct):
    """HR1's RECORD: Peter's own manual Hard Rock bets tagged source HR1, from 18 Nov forward. Nothing else counts -
    not an alert the rule selected, not a play he passed on. Empty until he places and logs the first one."""
    return [r for r in manual_rows(acct, "HR1") if str(r.get("ts") or "") >= HR1_START]


def hr1_alert_rows():
    """DIAGNOSTIC, not a record: alerts matching agree_rules.hr1, graded at the alert price. Peter has bet none of
    these. Kept so the push can be checked against what the rule selects; never reported as HR1's performance."""
    import agree_rules as ar
    rows, seen = [], set()
    for x in sorted(load("alerts.json") or [], key=lambda a: str(a.get("alert_utc") or "")):
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or not ar.hr1(x)[0]:
            continue
        k = (str(x.get("start_utc"))[:10], frozenset(sc.toks(x.get("game"))), x.get("kind"), ar.side_of(x))
        if k in seen:
            continue
        seen.add(k)
        am = x.get("price_after_fee")
        c = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        cert = x.get("clv_verified") is True
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am, "res": x["result"],
                     "clv": c if cert else None, "pclv": None if cert else c, "pclv_src": PROV_ALERT,
                     "pid": f"sharp|{x.get('alert_utc')}|{x.get('game')}|{x.get('bet')}|{x.get('book_key')}", "key": k})
    return paper_certified(rows)


def board_v4_rows(field="call"):
    """Board V4 (live since 17 Nov 12:40 ET): the V3 call log filtered by executor.board_v4 - a second book confirmed
    the same game, market, side and line at alert time. ONE definition of the gate: the executor's own function."""
    try:
        import board_build as bb
        import executor as ex
        feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    except Exception:
        return []
    return [r for r in liq_certified(board_rows(field)) if ex.board_v4(feed.get(r.get("aid") or ""))[0]]


def board_rows(field="call"):
    """field="call" = the live v3 call; field="v2" = the superseded v2 call, which keeps grading (reg 14)."""
    d = (load("board/calls.json") or {}).get("calls") or {}
    try:   # Nov 17: grade late-finishing calls from the full feeds (same fix the board build now applies)
        import board_build as _bb
        _bb.backfill_results(d, _bb.load())
    except Exception:
        pass
    rows = []
    for k, x in d.items():
        if x.get(field) != "PLAY" or x.get("result") not in ("W", "L", "P"):
            continue
        rows.append({"ts": str(x.get("at") or ""), "game": x.get("game") or "", "am": x.get("price"),
                     "res": x["result"], "clv": None, "aid": k,   # aid = the source liquidity alert id (key|alerted_utc)
                     "key": (x.get("day"), frozenset(sc.toks(x.get("game"))), x.get("mk"), x.get("side"))})
    return rows


EXCH = ("prophetx", "novig", "kalshi", "polymarket_us", "polymarket.us")
T18 = "2026-11-03T16:45:00Z"   # EDGE2 clock (paper_rules T60); reg 18 is its SENT exchange subset


def misprice_rows():
    """Reg 18 EXCHANGE MISPRICE: a SENT alert priced at an exchange, stated edge_pct >= +2 vs Pinnacle fair after fee,
    bettable pricing only (Polymarket Global is refused), from the EDGE2 clock. Read-only over alerts.json."""
    S = load("alerts.json") or []
    rows = []
    for x in S:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or not x.get("sent_to_phone"):
            continue
        if str(x.get("book_key") or "").lower() not in EXCH or x.get("pricing_bettable") is False:
            continue
        try:
            if float(x.get("edge_pct")) < 2:
                continue
        except (TypeError, ValueError):
            continue
        if str(x.get("alert_utc") or "") < T18:
            continue
        am = x.get("price_after_fee") if x.get("price_after_fee") is not None else x.get("price")
        c_ = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        cert = x.get("clv_verified") is True
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am, "res": x["result"],
                     "clv": c_ if cert else None, "pclv": None if cert else c_, "pclv_src": PROV_ALERT,
                     "pid": f"sharp|{x.get('alert_utc')}|{x.get('game')}|{x.get('bet')}|{x.get('book_key')}",
                     "key": (str(x.get("alert_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             str(x.get("kind")), str(x.get("bet") or ""))})
    return rows


# --------------------------------------------------------------------------- Board V4 split (Peter, 17 Nov, O19)
CHEAP = ("novig", "prophetx")          # fee ~0 and ~2c: these took every board fill before the correction
MARGINAL = ("kalshi", "polymarket_us", "polymarket.us")   # fee 7-8c: only fillable once the floor is on the same basis
BV4_TITLE = "BOARD V4 SPLIT (O19) - actual after-fee fills, by price basis and by fill venue"


def _grp(rows):
    """(n, W-L, after-fee units, ROI, certified CLV, coverage). Units at the FILL price; a missing close is
    never counted as zero, so coverage is reported beside the mean and never hidden inside it."""
    n = len(rows)
    w = sum(r.get("res") == "W" for r in rows)
    l = sum(r.get("res") == "L" for r in rows)
    u = sc.units(rows)
    rk = 0.0
    for r in rows:
        try:
            d = sc.cl.am_to_dec(float(r["am"]))
            rk += 1 / (d - 1) if d < 2 else 1.0
        except (TypeError, ValueError, KeyError, ZeroDivisionError):
            pass
    c = [r["clv"] for r in rows if r.get("clv") is not None]
    return {"n": n, "w": w, "l": l, "u": u, "roi": (100 * u / rk) if rk else None,
            "clv": (sum(c) / len(c)) if c else None, "cn": len(c)}


def _line(tag, g):
    if not g["n"]:
        return f"  {tag:<34} no fills yet"
    roi = f"{g['roi']:+6.1f}%" if g["roi"] is not None else "     -"
    clv = f"{g['clv']:+.2f}% on {g['cn']}/{g['n']}" if g["clv"] is not None else f"- on 0/{g['n']}"
    return f"  {tag:<34} n {g['n']:>3}  {g['w']}-{g['l']}  {g['u']:+7.2f}u  ROI {roi}  certified CLV {clv}"


def board_v4_split(rows):
    """Two comparisons Peter asked for, on SETTLED board fills only. Pure.
    Peter's warning, kept in the output: a worse entry price does not by itself say the marginal fills lose money."""
    rows = [r for r in rows or [] if r.get("res") in ("W", "L", "P")]
    def books_of(r):
        return [str(b).strip().lower() for b in (r.get("books") or [])]
    out = ["", BV4_TITLE,
           "  basis = the board floor this order used: corrected = the trigger venue's own after-fee price (17 Nov on)."]
    out.append(_line("BEFORE the fee correction", _grp([r for r in rows if r.get("fee_basis") is not True])))
    out.append(_line("AFTER the fee correction", _grp([r for r in rows if r.get("fee_basis") is True])))
    out.append("")
    out.append(_line("filled Novig / ProphetX only", _grp([r for r in rows if books_of(r)
                                                           and all(b in CHEAP for b in books_of(r))])))
    out.append(_line("any Kalshi / Polymarket US leg", _grp([r for r in rows if any(b in MARGINAL for b in books_of(r))])))
    out.append(_line("fill venue not recorded", _grp([r for r in rows if not books_of(r)])))
    out.append("  a lower CLV on the newly eligible venues is expected from their entry price alone; it does not say")
    out.append("  whether those bets are profitable. Read units and ROI beside it, and the sample size beside both.")
    return out


# --------------------------------------------------------------------------- R1 25-fill checkpoint (registered 17 Nov)
R1_CHECK_N = 25
R1_CHECK_TITLE = f"R1 CHECKPOINT (registered 17 Nov by Peter) - decision at {R1_CHECK_N} unique live settled fills"


def r1_checkpoint(rows, n_target=R1_CHECK_N):
    """One line. Pure: counts unique settled live R1 fills, and states the registered verdict only AT the target.
    Units are at the fill price after fees; CLV counts certified closes only and a missing close is never a zero."""
    rows = [r for r in rows or [] if r.get("res") in ("W", "L", "P")]
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: str(r.get("ts") or "")):
        k = r.get("key")
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    n = len(uniq)
    u = sc.units(uniq)
    c = [r["clv"] for r in uniq if r.get("clv") is not None]
    m = (sum(c) / len(c)) if c else None
    head = (f"  {n}/{n_target} unique live settled fills | units {u:+.2f} | certified CLV "
            + (f"{m:+.2f}% on {len(c)}" if m is not None else f"- on 0 of {n}"))
    if n < n_target:
        return head + f" | {n_target - n} to go, no decision before then"
    if u <= 0 and (m is not None and m <= 0):
        return head + " | VERDICT: PAUSE FOR REVIEW (units and certified CLV both nonpositive)"
    if m is not None and m > 0 and u < 0:
        return head + " | VERDICT: INCONCLUSIVE - certified CLV positive, units negative. Peter decides; do NOT extend"
    if m is None:
        return head + " | VERDICT: NO CERTIFIED CLV at the checkpoint - report coverage, Peter decides"
    return head + " | VERDICT: CONTINUE (units and/or certified CLV positive)"


# --------------------------------------------------------------------------- live (reporting ledger)
def live_rows(acct, lane):
    """One row per LIVE BOT PLAY with a confirmed fill and a settled result (live_ledger.account)."""
    return [{"ts": p["t"], "game": p["key"].split("|")[1] if "|" in p["key"] else p["key"], "am": p["am_net"],
             "res": p["res"], "clv": p["clv"], "key": p["key"]}
            for p in acct["plays"] if p["lane"] == lane and p["res"] in ("W", "L", "P") and p["am_net"] is not None]


FILL_IMPLIED_TITLE = "FILL-IMPLIED CLV - live plays priced at what the venues actually FILLED"


def fill_implied_block(acct):
    """Its OWN measure, reported beside the certified basis and NEVER blended into it (Peter, Nov 18).

    `clv` elsewhere in this report is the official clv_report basis: a verified same-line or exact-moneyline
    Pinnacle close. This block prices the same plays at the venues' own fill prices, per leg, each with its
    own venue fee. The two answer different questions - the certified number scores the SIGNAL at the alert
    price, this one scores the ACCOUNT - so they are never averaged together or substituted for each other.

    Percentages and counts only; no stakes, dollars or account data.
    """
    rows = [p for p in acct["plays"] if p.get("clv_fill") is not None]
    out = [FILL_IMPLIED_TITLE,
           "  not the official clv_report basis - a separate measure, never blended with certified CLV"]
    if not rows:
        out.append("  no live play carries a certified close yet - nothing to price")
        return out
    for lane in sorted({str(p["lane"]) for p in rows}):
        L = [p for p in rows if str(p["lane"]) == lane]
        v = [p["clv_fill"] for p in L]
        beat = sum(1 for x in v if x > 0)
        mean = sum(v) / len(v)
        se = (sum((x - mean) ** 2 for x in v) / (len(v) * (len(v) - 1))) ** 0.5 if len(v) > 1 else None
        band = f" +/-{se:.2f} (1 s.e.)" if se is not None else " (n=1, no spread)"
        out.append(f"  {lane:<9} n {len(v)} of {sum(1 for p in acct['plays'] if p['lane'] == lane)} plays | "
                   f"fill-implied CLV {mean:+.2f}%{band} | beat close {beat}/{len(v)}")
    by = {}
    for p in rows:
        for l in p.get("clv_fill_legs") or []:
            by.setdefault(l["book"] or "unknown", []).append(l["clv"])
    if by:
        out.append("  by fill venue (per leg, that venue's own fee):")
        for b in sorted(by):
            v = by[b]
            out.append(f"    {b:<14} n {len(v)} | {sum(v)/len(v):+.2f}% | beat close {sum(1 for x in v if x > 0)}/{len(v)}")
    gap = [(p["clv_fill"], p["clv"]) for p in rows if p.get("clv") is not None]
    if gap:
        d = [f - c for f, c in gap]
        out.append(f"  fill vs certified on the same {len(gap)} plays: "
                   f"fill {sum(f for f, _ in gap)/len(gap):+.2f}% | certified {sum(c for _, c in gap)/len(gap):+.2f}% | "
                   f"gap {sum(d)/len(d):+.2f}pp (zero tolerance means fills price at or better than the alert)")
    return out


def manual_rows(acct, src):
    return [{"ts": m["t"], "game": f"{m['game']} - {m['bet']}", "am": m["am"], "res": m["res"], "clv": m["clv"],
             "key": tuple(sorted(m["rows"]))}
            for m in acct["manual"] if m["src"] == src and m["res"] in ("W", "L", "P") and m["am"] is not None]


# --------------------------------------------------------------------------- SLOW-HR / DOG BAND (paper)
SLOWHR_EV_MIN = 2.0                      # slowhr_cell.EV_MIN - the registered cell
DOG_BAND_FROM = "2026-11-07T05:00:00Z"   # REGISTRY 12: forward from 7 Nov (ET)


def slowhr_rows(dog_band=False):
    """SLOW-HR (#11) registered cell: Type P x moneyline x Hard Rock underdog (price > 0) x EV >= +2% x not LATE, first
    sighting per event + market + side (slowhr_cell rules), graded 1u at the Hard Rock price on ESPN finals.
    DOG BAND (#12): the same cell, +100 to +299 only, from 7 Nov. Paper. None if the state cannot be decrypted."""
    if not os.environ.get("TRACKER_PASSPHRASE"):
        return None
    try:
        import tracker_build as tb
        S = (tb.dec(json.load(open("slowhr/state.enc"))) or {}).get("sightings") or []
        import finals as fin
    except Exception as e:
        print(f"slowhr not readable ({type(e).__name__})")
        return None
    first = {}
    for x in sorted(S, key=lambda z: str(z.get("t_move") or "")):
        am = x.get("hr_am")
        if not (x.get("kind") == "P" and x.get("type") == "moneyline" and am is not None and am > 0
                and x.get("ev_pct") is not None and x["ev_pct"] >= SLOWHR_EV_MIN and not x.get("late")):
            continue
        if dog_band and not (100 <= am <= 299 and str(x.get("t_confirm") or "") >= DOG_BAND_FROM):
            continue
        day = str(x.get("start") or "")[:10]
        ev = (x.get("league"), day, frozenset(sc.toks(x.get("game"))), x.get("type"), str(x.get("side")))
        first.setdefault(ev, x)
    rows = []
    for k, x in first.items():
        try:
            res = fin.result(x)
        except Exception:
            res = None
        if res is None:
            continue
        cf = x.get("close_fair")
        clv = None if cf is None or not x.get("hr_price") else 100 * (float(cf) * float(x["hr_price"]) - 1)
        rows.append({"ts": str(x.get("t_confirm") or x.get("t_move") or ""), "game": f"{x.get('game')} - {x.get('team')}",
                     "am": x["hr_am"], "res": res, "clv": None, "pclv": clv,   # 16 Nov: no certification record
                     "pclv_src": "SLOW-HR close_fair: no certification record", "key": k})
    return rows


def confidence(n, clv_n, exec_n=None):
    """Stated rule: HIGH = 50 plays and certified CLV on 80%+; MEDIUM = 25+ plays and CLV on 50%+; else LOW.
    Coverage is against eligible US-executable rows (CLV_STANDARD.md s7) when the caller knows them."""
    den = exec_n if exec_n is not None else n
    cov = (clv_n / den) if den else 0
    if n >= 50 and cov >= 0.8:
        return "HIGH"
    if n >= 25 and cov >= 0.5:
        return "MEDIUM"
    return "LOW"


def registry_names():
    out = {}
    try:
        for ln in open("REGISTRY.md"):
            m = re.match(r"\|\s*(\d+)\s*\|\s*\*\*(.+?)\*\*", ln)
            if m:
                out[int(m.group(1))] = m.group(2).strip()
    except OSError:
        pass
    return out


CSV_COLS = ["test", "half", "ts", "game", "price_am", "result", "certified_clv_pct",
            "provisional_clv_pct_not_certified", "provisional_source"]


def send_report(body, rows):
    """EMAIL delivery. NOT Telegram (Peter, Nov 22: "I don't need paper or research to telegram").

    This used to chunk the whole report into Telegram plus a CSV document, and the reason was in
    its own old docstring: "Peter, 13 Nov: no Gmail". That rule was about CLAUDE READING Peter's
    mailbox - it was never about where a report is delivered. The rule got applied to sending as
    well, so a VALUE LAB research report landed on the LIVE ALERT FEED every morning at 5:24 ET,
    in a dozen chunks plus an attachment, between the order notices Peter actually watches.
    clv_report.py has always emailed; this is the same channel, not a new one.

    Credentials are read from the environment directly rather than through executor.gmail(),
    because importing executor does live-trading setup at import time and this is a read-only
    reporter. Same three secrets, no new credential.

    The CSV stays an ATTACHMENT: a truncated body can be silently half-valid, a CSV cannot.
    Missing secrets or a failed send still returns False, and main() exits non-zero on it, so a
    dead reporter stays loud. Nothing is printed to the public log except a count."""
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    user = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
    to = (os.environ.get("EMAIL_TO") or "").strip() or user
    if not (user and pw):
        print("email not configured - report NOT delivered")
        return False
    try:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        m = MIMEMultipart()
        m["Subject"] = "Bets VALUE LAB - LAST-50 REPORT"
        m["From"], m["To"] = user, to
        m.attach(MIMEText(body, "plain", "utf-8"))
        part = MIMEBase("text", "csv")
        part.set_payload(buf.getvalue().encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename="last50_plays.csv")
        m.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=120) as sv:
            sv.login(user, pw)
            sv.sendmail(user, [to], m.as_string())
    except Exception as e:
        print(f"email send failed ({type(e).__name__})")
        return False
    print(f"emailed: report + CSV ({len(rows)} rows)")
    return True


WHY_NOT = {
    4: "no executed-play log links Hard Rock wagers to scanner flags (only 2 documented pushes); signals are not bets",
    10: "post_test recomputes on each run; no stored per-play record - not integrated yet",
    15: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    16: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    17: "registry one-liner only; start date and data source not documented",
    19: "'gettable' is not defined anywhere; the 61-row second queue is player props, which Peter excluded",
    20: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    21: "CLOSED - final read 11 Nov (FAIL); not re-graded here",
    22: "no FanDuel / DraftKings play log exists (exlag covers the four exchanges only)",
    23: "CLOSED - CLEAR FAIL 11 Nov; not re-graded here",
}


def main():
    import live_ledger as ll
    say("VALUE LAB - LAST-50 REPORT (deterministic; no model computed these numbers)")
    say(sc.cs.stamp())
    say("LIVE first (real fills only), then the top 5 paper tests, then the rest. Paper and live are never pooled.")
    say("Window: last 50 graded plays per test, one play per game+market+side, older half / newer half.")
    say("Flat 1u at the actual fill (live) or logged (paper) price. No dollars. Fills are never assumed.")
    say("CLV: CERTIFIED only (Pinnacle no-vig close, same line or moneyline, after fees); coverage printed. Provisional")
    say("     closes (live feed reads, venue closes) are shown separately, labelled, and never count toward a verdict.")
    say("CONFIDENCE: HIGH = 50 plays and certified CLV on 80%+; MEDIUM = 25+ plays and CLV on 50%+; else LOW.")

    status, csv_rows = {}, []
    covered = set()

    def run(label, rows, note="", frozen=False):
        s, o = report(label, rows, note, frozen)
        status[label] = s
        csv_rows.extend(o)

    # ------------------------------------------------------------------ LIVE
    say("")
    say("=" * 100)
    say(f"LIVE - actual bot fills from {ll.START_UTC[:10]} 00:00 ET (reporting ledger; lane from the bot's own order row)")
    say("=" * 100)
    src = ll.load()
    if src is None:
        say("  UNANSWERED: reporting ledger / tracker not decrypted in this run (TRACKER_PASSPHRASE missing)")
        acct = None
    else:
        Lg, B, C = src
        acct = ll.account(Lg, B, C, ll.feed_alerts())
        for lane, reg_n in (("LANE 1", 1), ("R1", None), ("BOARD V3", None), ("LANE 2", 8)):
            rows = live_rows(acct, lane)
            run(f"{lane} - live fills", rows, "confirmed fills only; partial fills merged; 1u at the fill price")
            if reg_n and rows:
                covered.add(reg_n)
        # ------------------------------------------------------------ R1 pre-registered checkpoint (Peter, 17 Nov)
        # "CONTINUE TO 25 LIVE SETTLED FILLS." Registered IN ADVANCE so the decision is not re-argued each week:
        # at 25 unique live settled selections, PAUSE FOR REVIEW if units <= 0 AND certified CLV <= 0; if CLV > 0
        # and units < 0, report INCONCLUSIVE and wait for Peter - never extend the window automatically. Nothing
        # here changes R1's rule, stakes, price floor or risk limits, and it never overrides a daily stop.
        for _ln in board_v4_split(live_rows(acct, "BOARD V3")):
            say(_ln)
        say("")
        say(R1_CHECK_TITLE)
        say(r1_checkpoint(live_rows(acct, "R1")))
        if not live_rows(acct, "LANE 2"):
            say("  LANE 2: no live orders in the ledger - Lane 2 is paper + dry-run (REGISTRY 8)")
        res_by_key = {p["key"]: p["res"] for p in acct["plays"]}
        am_by_key = {p["key"]: p["am_net"] for p in acct["plays"]}
        rest = [{"ts": r["t"], "game": r["key"].split("|")[1], "am": r["am"] if r["am"] is not None else am_by_key.get(r["key"]),
                 "res": res_by_key.get(r["key"]), "clv": None, "key": r["key"]}
                for r in ll.resting(Lg) if r["filled"] and (r["am"] is not None or am_by_key.get(r["key"]) is not None)]
        run("RESTING BIDS (reg 2) - resting legs that filled", rest,
            "graded with the play's settled result at the resting leg's own fill price (the play's blended price when the leg "
            "has none); CLV not joined per leg")
        covered.add(2)
        nf = [r for r in ll.resting(Lg) if not r["filled"]]
        say(f"  resting legs with no confirmed fill: {len(nf)} (excluded)")

        say("")
        for _ln in fill_implied_block(acct):
            say(_ln)

        say("")
        say("LIVE RECONCILIATION - every bot order in the window")
        for p in sorted(acct["plays"], key=lambda p: p["t"]):
            clv = "n/a" if p["clv"] is None else f"{p['clv']:+.2f}%"
            fi = "n/a" if p.get("clv_fill") is None else f"{p['clv_fill']:+.2f}%"
            vn = ",".join(f"{l['book']}@{l['am']}:{l['clv']:+.2f}%" for l in (p.get("clv_fill_legs") or [])) or "-"
            say(f"  COUNTED  {p['t'][:16]} {p['lane']:<9} {p['key']} | fill {p['am']} (after fees {p['am_net']}) "
                f"{p['res'] or '-'} | {p['status']} | "
                f"{p['evidence']} | legs {p['fills']} | CLV {clv} | fill-implied {fi} [{vn}]")
        for e in sorted(acct["excluded"], key=lambda e: e["t"]):
            say(f"  EXCLUDED {e['t'][:16]} {str(e['lane']):<9} {e['key']} | {e['why']}")
        for u in sorted(acct["unresolved"], key=lambda u: u["t"]):
            say(f"  UNRESOLVED {u['t'][:16]} {str(u['lane']):<9} {u['key']} | {u['why']} | tracker rows {len(u['rows'])}")

    # ------------------------------------------------------------------ MANUAL (real money, not bot)
    say("")
    say("=" * 100)
    say("MANUAL - Peter's own bets (bot-linked fills removed, partial fills merged)")
    say("=" * 100)
    if acct is None:
        say("  UNANSWERED: tracker not decrypted in this run")
    else:
        run("PETER - FEED PLAYS (reg 3)", manual_rows(acct, "Peter feed"),
            "manual bets with an alert (sharp / liquidity / board) on the same game+market+side BEFORE the bet")
        run("STREET VALUE (reg 5)", manual_rows(acct, "Street Value"), "rows tagged Street Value from the private SV notes")
        covered.update({3, 5})
        other = [m for m in acct["manual"] if m["src"] == "manual, no feed origin"]
        say(f"  manual bets with no documented feed origin (not graded as a strategy): {len(other)}")

    # ------------------------------------------------------------------ PAPER
    S = sharp_rows()
    Q = liq_rows()
    paper = [
        (6, "STEAM (reg 6) - sharp alerts, all graded", paper_certified(S), "the whole Steam alert feed; not any one lane"),
        (None, "SHARP ALERTS - sent to phone", paper_certified([r for r in S if r["sent"]]), ""),
        (None, "SHARP ALERTS - NBA unders", paper_certified([r for r in S if r["lg"] == "NBA" and "under" in r["bet"].lower()]),
         "PROXY for Lane 1's market only, not Lane 1's fills"),
        (None, "LIQ - NBA UNDER, Kalshi-triggered", paper_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                     and r["side"] == "UNDER" and r["book"] == "kalshi"]), "bettable venue only"),
        (9, "LIQ-BOT (reg 9) - NBA totals, 4h+ lead", liq_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                       and r["lead"] is not None and r["lead"] >= 240]), ""),
        (13, "LIQ-SMALL (reg 13) - NBA totals, $25-50k prints", liq_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                                and r["nm"] is not None and 25000 <= r["nm"] <= 50000]), ""),
        (25, "PULL_FADE (reg 25)", paper_certified(lane_rows("pull_fade")), "price is the logged probability"),
        (26, "SOLO (reg 26)", paper_certified(lane_rows("solo")), "price is the logged probability"),
        (7, "BOARD V4 (reg 7) - LIVE since 17 Nov", board_v4_rows(), "V3 PLAY calls that a second book confirmed at alert time ($10k, same line); the live board rule"),
        (7, "BOARD V3 (reg 7) - shadow", liq_certified(board_rows()), "every PLAY call, confirmed or not; the pre-17-Nov live rule, now shadow only"),
        (14, "BOARD v2 (reg 14) - superseded 6 Nov", liq_certified(board_rows("v2")), "v2 PLAY calls from the same frozen call log; kept for history, not a live rule"),
        (None, f"HR1 - LIVE MANUAL PLAYS (from {HR1_START})", (hr1_live_rows(acct) if acct else []),
         f"HR1's record: Peter's own Hard Rock bets tagged source HR1, from {HR1_START}. Nothing before that date and no alert he did not bet"),
        (24, "ML_STAY (reg 24)", paper_certified(lane_rows("ml_stay")), "price is the logged probability"),
        (18, "EXCHANGE MISPRICE (reg 18)", paper_certified(misprice_rows()), "SENT, exchange-priced, edge >= +2% vs Pinnacle fair, from 3 Nov"),
    ]
    for reg_n, label, dog in ((11, "SLOW-HR (reg 11) - registered cell", False), (12, "DOG BAND (reg 12)", True)):
        rows = slowhr_rows(dog)
        if rows is None:
            say("")
            say(f"{label}: UNANSWERED - slowhr state not decrypted in this run")
        else:
            paper.append((reg_n, label, rows, "Type P ML Hard Rock dogs, EV >= +2%, not LATE, first sighting; ESPN finals"
                          + ("; +100 to +299, from 7 Nov" if dog else "")))

    def rank(item):
        w, _t = window(item[2])
        ci = ci_mean(half_stats(w)["us"]) if len(w) >= N else None
        return ci[0] if ci else -9.0

    top = sorted([x for x in paper if len(window(x[2])[0]) >= N], key=rank, reverse=True)[:5]
    say("")
    say("=" * 100)
    say("PAPER - TOP 5 by the lower end of the units 95% CI (50-play windows only; no CLV gate applied to the rank)")
    say("=" * 100)
    for reg_n, label, rows, note in top:
        run(label, rows, note)
    say("")
    say("=" * 100)
    say("PAPER - all other tests")
    say("=" * 100)
    for reg_n, label, rows, note in paper:
        if reg_n:
            covered.add(reg_n)
        if (reg_n, label, rows, note) not in top:
            run(label, rows, note)

    reg = registry_names()
    say("")
    say("=" * 100)
    say("NOT IN THIS REPORT - with the reason")
    say("=" * 100)
    for n, name in sorted(reg.items()):
        if n in covered:
            continue
        say(f"  #{n:>2} {name} - {WHY_NOT.get(n, 'research track; not verified as a play log (not classified yet)')}")
    say("")
    say("OPEN ITEMS (carried until answered or you close them)")
    say("  1. UNRESOLVED live plays above count for nobody until a venue order record settles who placed them.")
    say("  2. Novig bot fills join the tracker by bot wallet + play (E3): the tracker stores a Novig position id, not the")
    say("     order id. E1/E2 are exact order-id joins.")
    say("  3. #15 / #16 / #20 definitions and start dates; #17 / #19 documented rules (see above).")
    say("  4. Circa close not included; Pinnacle only.")
    say("")
    say("SUMMARY: " + ", ".join(f"{k}: {v}" for k, v in Counter(status.values()).items()))
    return 0 if send_report("\n".join(L), csv_rows) else 1


if __name__ == "__main__":
    sys.exit(main())
