#!/usr/bin/env python3
"""PROBABILITY CLV (converted) - SHADOW ONLY (Peter, Nov 14 2026; joint review: GitHub issue #5).

READ-ONLY. Reads the ledger, the tracker and the cached Pinnacle histories. Writes nothing, fetches nothing,
no IMAP, no OddsPapi key, no stake or balance in any output (units and percentages only). It is NOT wired into
CLV_STANDARD.md, a headline, a gate or a lane rule. Category: EXECUTED CLV only (real fills) - it is never
pooled with AUTO / MANUAL / Passive Posting / Paper Fill-Supported.

WHAT IT MEASURES, per selection (one selection = one observation, fills collapsed exactly as clv_selection does):
  r    P(win | no push) of the ticket's OWN side at the ticket's OWN line, from Pinnacle's no-vig close
  q    P(push) at that line
  b    net profit per unit staked, AFTER FEES (the position's pay/stake - 1)
  Probability CLV (pp)  = r - 1/(1+b)                      conditional on no push
  Closing-implied EV    = (1-q) * ((1+b) r - 1) = w b - l  push refunded
Same sign by construction; EV also carries the push mass. Old same-line CLV = q_exact * dec - 1 is reported beside.

HOW THE CLOSE REACHES THE TICKET'S LINE. Pinnacle's own number at the ticket's line when it hung one (same_line).
Otherwise its MAIN line (largest limit) is moved to the ticket's line with line_value.outcomes_at, which rebuilds
coherent win / push / loss from landing masses (no generic probability increment is applied across a whole number,
and no push is bolted on afterwards). Classes, never merged:
  same_line        exact line, no conversion
  conv_measured    NFL masses measured in this repo (measure_nfl_push.py)            <- the ONLY primary validation cohort
  conv_estimated   published masses (NCAAF/NCAAB) or NBA probability-points on half-point lines: ESTIMATES, not validated
  conv_unsupported anything else, with the line_value reason; never interpolated, never guessed
"""
import collections
import contextlib
import dataclasses
import math
import os
import sys
from datetime import datetime, timezone

import line_value as lv

CALC = "prob_clv_shadow/v1"
Z95 = 1.96
SIGN_EPS = 1e-12


# ------------------------------------------------------------------ arithmetic (pure)
def ev_and_pp(w, p, l, dec):
    """(Probability CLV in probability points, closing-implied EV per unit staked, r). dec is AFTER-FEE decimal."""
    if w + l <= 0:
        raise lv.Unsupported("no_decided_probability")
    r = w / (w + l)
    return r - 1.0 / dec, w * (dec - 1.0) - l, r


def old_same_line(q_exact, dec):
    """The existing same-line CLV arithmetic (clv_basis.clv without the rounding): close * dec - 1."""
    return q_exact * dec - 1.0


@contextlib.contextmanager
def perturbed(k):
    """Mass sensitivity: k=-1/0/+1. Measured rows move by one SE; published rows (no SE) by 25% of themselves."""
    orig = lv.mass_row

    def mr(sport, mtype, kk):
        row = orig(sport, mtype, kk)
        if row is None or k == 0:
            return row
        d = row.se if (row.n and row.se == row.se) else 0.25 * row.m
        return dataclasses.replace(row, m=min(1.0, max(0.0, row.m + k * d)))

    lv.mass_row = mr
    try:
        yield
    finally:
        lv.mass_row = orig


def value_at_ticket(sport, mtype, side, bet_line, ref_line, q_ref, dec, book, k=0):
    """Coherent close value at the ticket's line.

    Returns dict(status, cls, w, p, l, pp, ev, r, q_push, reason). status is 'ok' or 'unsupported'. For a same-line half-point
    ticket nothing but q_ref is needed. Raises nothing."""
    out = {"status": "unsupported", "cls": None, "w": None, "p": None, "l": None, "pp": None, "ev": None, "r": None,
           "q_push": None, "reason": None}
    try:
        if mtype == "moneyline":
            w, p, l = q_ref, 0.0, 1.0 - q_ref
            cls = "same_line"
        else:
            same = abs(float(bet_line) - float(ref_line)) < lv.EPS
            c1 = lv.cover_threshold(mtype, side, bet_line)
            lv.push_ok(book, c1, sport, mtype)            # whole-number ticket: the VENUE's refund rule must be verified
            spec = lv.VALUES.get((sport, mtype)) or {}
            measured = str(spec.get("status", "")).startswith("measured")
            ref = lv.Reference(mtype, side, float(ref_line), q_ref, "close", "pinnacle")
            try:
                with perturbed(k):
                    o = lv.outcomes_at(ref, sport, bet_line)
                w, p, l = o.w, o.p, o.l
                cls = "same_line" if same else ("conv_measured" if measured else "conv_estimated")
            except lv.Unsupported as u:
                if same:                                    # same line but no push mass: only the conditional r is honest
                    r_only = q_ref
                    out.update(status="ok", cls="same_line", r=r_only, pp=r_only - 1.0 / dec, ev=None,
                               reason=f"push_mass_unsupported:{u.code}")
                    return out
                if sport == "NBA" and mtype in ("spread", "total") and not lv.is_whole(c1) \
                        and not lv.is_whole(lv.cover_threshold(mtype, side, ref_line)):
                    rec = lv.convert(sport, mtype, side, float(ref_line), -110, float(bet_line), None, book)
                    if rec.get("status") != "ok" or rec.get("allowance") is None:
                        raise lv.Unsupported(rec.get("reason") or "nba_points_unsupported", rec.get("detail") or "")
                    r_est = min(max(q_ref + rec["allowance"], 0.01), 0.99)
                    w, p, l = r_est, 0.0, 1.0 - r_est
                    cls = "conv_estimated"
                    out["reason"] = "nba_prob_points_half_to_half(estimate)"
                else:
                    raise
        pp, ev, r = ev_and_pp(w, p, l, dec)
        out.update(status="ok", cls=cls, w=w, p=p, l=l, pp=pp, ev=ev, r=r, q_push=p)
    except lv.Unsupported as u:
        out.update(status="unsupported", reason=f"{u.code}" + (f":{u.detail}" if u.detail else ""))
    except Exception as e:                                 # a defect in this module must not look like a market fact
        out.update(status="unsupported", reason=f"module_error:{type(e).__name__}")
    return out


# ------------------------------------------------------------------ the Pinnacle ladder (reads cached history only)
def ladder(fixture, snap, mkmap, pm, H):
    """(info, why). info = {mtype, side, bet_line, entries:[(bettor_line, q_bettor, age_min, limit)]}.

    H is a namespace of the clv_ledger helpers (parsed, which_team, two_way, novig_p, SPORT, ML_MARKET, FRESH_MIN, tp, fxm,
    tb) so the module stays pure and testable. Same guards as clv_basis.pinnacle_no_vig_close; the only difference is that
    EVERY fresh two-sided line is returned, not just the exact one."""
    start = H.tp(fixture.get("start")) or H.tp(snap.get("game_start"))
    if not start:
        return None, "no start time on the fixture or the row"
    try:
        if H.tb.is_politics({"game": snap.get("game"), "bet": snap.get("bet")}):
            return None, "politics market, not a sports bet"
    except Exception:
        pass
    pz = H.parsed(snap)
    if not pz:
        return None, "bet text did not parse"
    lg = snap.get("league")
    sid = H.SPORT.get(lg)
    if sid is None:
        return None, f"league {lg or 'unknown'} has no sport id"
    if pz[0] == "ml":
        mid = H.ML_MARKET.get(sid)
        tw = H.two_way(pm, mid, start) if mid else {}
        oc = {v: k for k, v in ((mkmap.get(mid) or [0, 0, 0, {}])[3]).items()}
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return None, "no two-sided Pinnacle moneyline quote before start"
        age = (start - min(tw[o1][1], tw[o2][1])).total_seconds() / 60
        if age > H.FRESH_MIN:
            return None, f"moneyline close {age / 60:.0f}h stale"
        side, why = H.fxm.resolve_side(fixture, pz[1], lg, H.which_team)
        if not side:
            return None, why
        if pz[3]:
            side = "2" if side == "1" else "1"
        p = H.novig_p(tw[o1][0], tw[o2][0])
        return {"mtype": "moneyline", "side": None, "bet_line": None,
                "entries": [(None, p if side == "1" else 1 - p, age, min(tw[o1][2], tw[o2][2]))]}, None
    typ = "spreads" if pz[0] == "spread" else "totals"
    want, side_is_1 = pz[2], None
    if typ == "spreads":
        sd, why = H.fxm.resolve_side(fixture, pz[1], lg, H.which_team)
        if not sd:
            return None, why
        if pz[3]:
            sd, want = ("2" if sd == "1" else "1"), -want
        side_is_1 = sd == "1"
        side_lab = None
    else:
        side_lab = pz[1]                                    # "OVER" / "UNDER"
    entries = []
    for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
        if sp != sid or t != typ or mid not in pm:
            continue
        tw = H.two_way(pm, mid, start)
        nm = {v: k for k, v in outs.items()}
        a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a not in tw or b not in tw:
            continue
        age = (start - min(tw[a][1], tw[b][1])).total_seconds() / 60
        if age > H.FRESH_MIN:
            continue
        pa = H.novig_p(tw[a][0], tw[b][0])                  # team 1 covers hcap / over hcap
        lim = min(tw[a][2], tw[b][2])
        if typ == "spreads":
            entries.append((hcap if side_is_1 else -hcap, pa if side_is_1 else 1 - pa, age, lim))
        else:
            entries.append((hcap, pa if side_lab == "OVER" else 1 - pa, age, lim))
    if not entries:
        return None, f"no fresh two-sided Pinnacle {typ} close"
    return {"mtype": "spread" if typ == "spreads" else "total", "side": side_lab, "bet_line": float(want),
            "entries": entries}, None


def pick_reference(info):
    """(entry, kind): the ticket's own line when Pinnacle hung it, else Pinnacle's main line (largest limit, then most even)."""
    if info["mtype"] == "moneyline":
        return info["entries"][0], "same_line"
    for e in info["entries"]:
        if abs(e[0] - info["bet_line"]) < 1e-9:
            return e, "same_line"
    return max(info["entries"], key=lambda e: (e[3], -abs(e[1] - 0.5))), "moved"


def score_selection(sport, book, dec, gross_dec, info):
    """Everything computed for one selection from its ladder. Pure."""
    ent, kind = pick_reference(info)
    mt, side, bl = info["mtype"], info["side"], info["bet_line"]
    ref_line, q_ref = ent[0], ent[1]
    base = value_at_ticket(sport, mt, side, bl, ref_line, q_ref, dec, book)
    rec = {"kind": kind, "ref_line": ref_line, "q_ref": q_ref, "base": base,
           "old": old_same_line(q_ref, dec) if kind == "same_line" else None,
           "naive": None if kind == "same_line" else old_same_line(q_ref, dec),   # price-only, ignores the line difference
           "line_move": None if mt == "moneyline" else (bl - ref_line)}
    if base["status"] == "ok" and kind == "moved":
        lo = value_at_ticket(sport, mt, side, bl, ref_line, q_ref, dec, book, k=-1)
        hi = value_at_ticket(sport, mt, side, bl, ref_line, q_ref, dec, book, k=+1)
        rec["sens"] = [x["pp"] for x in (lo, hi) if x["status"] == "ok"]
    if gross_dec and base["status"] == "ok":
        g = value_at_ticket(sport, mt, side, bl, ref_line, q_ref, gross_dec, book)
        rec["gross_ev"] = g["ev"] if g["status"] == "ok" else None
        rec["gross_pp"] = g["pp"] if g["status"] == "ok" else None
    return rec


# ------------------------------------------------------------------ statistics (pure)
def sgn(x):
    return 0 if x is None or abs(x) < SIGN_EPS else (1 if x > 0 else -1)


def cluster_mean(vals, clusters):
    """(n, mean, cluster-robust SE, #clusters). Clusters = games, so a spread and a total on one game are not two samples."""
    pairs = [(v, c) for v, c in zip(vals, clusters) if v is not None]
    n = len(pairs)
    if n == 0:
        return 0, None, None, 0
    m = sum(v for v, _ in pairs) / n
    by = collections.defaultdict(float)
    for v, c in pairs:
        by[c] += v - m
    g = len(by)
    se = math.sqrt(sum(s * s for s in by.values())) / n if g > 1 else None
    return n, m, se, g


def fmt_mean(vals, clusters, scale=100.0, unit="%", digits=2):
    n, m, se, g = cluster_mean(vals, clusters)
    if n == 0:
        return "n 0"
    ci = f" 95%CI [{scale * (m - Z95 * se):+.{digits}f},{scale * (m + Z95 * se):+.{digits}f}]" if se is not None else " CI n/a"
    return f"n {n} games {g} mean {scale * m:+.{digits}f}{unit}{ci}"


def split_halves(items, key="start"):
    have = sorted((x for x in items if x.get(key)), key=lambda x: x[key])
    mid = len(have) // 2
    return have[:mid], have[mid:], [x for x in items if not x.get(key)]


# ------------------------------------------------------------------ the run (needs the encrypted ledger: Actions only)
OUT = []


def say(t=""):
    OUT.append(t)
    print(t, flush=True)


def venue_id(book):
    import clv_std as cs
    try:
        return cs.canon(book).replace(".", "_")
    except Exception:
        return str(book or "").lower().replace(" ", "_").replace(".", "_")


def build_records(st, tracker, reg, mkmap, H, cv, cb, cl, csel, cstale, fxm):
    bets = st.get("bets") or {}
    try:
        stale = cstale.stale_map(bets, tracker)
    except Exception:
        stale = {}
    alt = cv.all_fixture_ids()
    alt_f = {fid: f for fid, (f, _p) in alt.items()}
    fx_state = st.get("fixtures") or {}
    lane_for = cv.build_lane_resolver(reg)
    prep = {k: dict(r, clv=(r["clv"] if r.get("clv") is not None else -999)) for k, r in bets.items()}
    obs = csel.selections(prep, tracker, exclude=set(stale))
    recs = []
    for key, o in obs.items():
        rows = [bets[i] for i in o["ids"]]
        snaps = [r.get("snap") or {} for r in rows]
        snap = snaps[0]
        stake = sum(H.tb.num(s.get("stake")) or 0 for s in snaps)
        pay = sum(H.tb.num(s.get("to_pay")) or 0 for s in snaps)
        dec = pay / stake if (stake and pay and pay > stake) else cl.eff_dec(snap)
        gross = None
        if snap.get("book") == "ProphetX" and all(s.get("price") not in (None, "") for s in snaps):
            gross = sum((H.tb.num(s.get("stake")) or 1) * cl.am_to_dec(s["price"]) for s in snaps) / \
                    (sum((H.tb.num(s.get("stake")) or 1) for s in snaps) or 1)
        stored = [r.get("clv") for r in rows if r.get("clv") is not None]
        had_stored = any(r.get("clv") is not None for r in rows)
        parts = key.split("|")
        rec = {"key": key, "lg": snap.get("league"), "book": venue_id(snap.get("book")), "source": snap.get("source") or "?",
               "lane": lane_for(key, o) or "UNKNOWN", "start": o.get("game_start"), "fills": o["n_fills"],
               "game": (snap.get("league"), parts[1] if len(parts) > 1 else key, str(o.get("game_start") or "")[:10]),
               "profit": o.get("profit"), "stake": o.get("stake"), "result": o.get("result"), "dec": dec,
               "stored_clv": o["clv"] if had_stored else None, "stored_how": o.get("how") or [],
               "status": None, "why": None, "sc": None}
        if not dec:
            rec.update(status="no_close", why="ROW-DATA: no after-fee execution price")
            recs.append(rec)
            continue
        if not snap.get("league"):
            rec.update(status="no_close", why="ROW-DATA: no league recorded")
            recs.append(rec)
            continue
        fid, _where, note = cb.resolve_fixture(snap, fx_state, alt_f, cl.find_fixture, fxm.ordered_match, cl.tp)
        if not fid:
            rec.update(status="no_close", why="FIXTURE-CACHE: no fixture matched (" + str(note)[:40] + ")")
            recs.append(rec)
            continue
        h = cv._cached_pin(fid)
        if h is None:
            rec.update(status="no_close", why="PINNACLE-DATA: fixture known, history never downloaded")
            recs.append(rec)
            continue
        f = fx_state.get(fid) or alt_f.get(fid) or {}
        info, why = ladder(f, snap, mkmap, cl.book_markets(h, "pinnacle"), H)
        if info is None:
            cls_ = "POLICY" if ("parse" in str(why) or "politics" in str(why)) else "PINNACLE-DATA"
            rec.update(status="no_close", why=f"{cls_}: {str(why)[:60]}")
            recs.append(rec)
            continue
        rec["sc"] = score_selection(snap.get("league"), rec["book"], dec, gross, info)
        b = rec["sc"]["base"]
        rec["status"] = b["cls"] if b["status"] == "ok" else "conv_unsupported"
        rec["why"] = b["reason"]
        recs.append(rec)
    return recs, stale, bets


def roi_units(recs, lane_unit):
    have = [r for r in recs if r["profit"] is not None]
    settled = [r for r in recs if r["result"] and r["stake"]]
    ss = sum(r["stake"] for r in settled)
    roi = f"ROI {100 * sum(r['profit'] for r in have) / ss:+.2f}%" if (have and ss) else "ROI n/a"
    lanes = {r["lane"] for r in recs}
    if len(lanes) == 1 and next(iter(lanes)) in lane_unit and have:
        u = f"{sum(r['profit'] for r in have) / lane_unit[next(iter(lanes))]:+.1f}u"
    else:
        u = "units n/a (lane mixed/unknown)"
    return f"{roi}  {u}"


def block(label, recs, lane_unit):
    if not recs:
        say(f"  {label:<34} n 0")
        return
    g = [r["game"] for r in recs]
    pp = [r["sc"]["base"]["pp"] for r in recs if r["sc"] and r["sc"]["base"]["status"] == "ok"]
    ev = [r["sc"]["base"]["ev"] for r in recs if r["sc"] and r["sc"]["base"]["status"] == "ok" and r["sc"]["base"]["ev"] is not None]
    old = [r["sc"]["old"] for r in recs if r["sc"] and r["sc"]["old"] is not None]
    gg = lambda sel: [r["game"] for r in recs if r["sc"] and r["sc"]["base"]["status"] == "ok" and sel(r)]
    say(f"  {label:<34} selections {len(recs)} fills {sum(r['fills'] for r in recs)} games {len(set(g))}  {roi_units(recs, lane_unit)}")
    say(f"      old same-line CLV : {fmt_mean(old, [r['game'] for r in recs if r['sc'] and r['sc']['old'] is not None])}")
    say(f"      Probability CLV   : {fmt_mean(pp, gg(lambda r: True), 100, ' pp')}")
    say(f"      closing-implied EV: {fmt_mean(ev, gg(lambda r: r['sc']['base']['ev'] is not None))}")


def main():
    import json
    import clv_basis as cb
    import clv_coverage as cv
    import clv_ledger as cl
    import clv_selection as csel
    import clv_stale as cstale
    import fixture_match as fxm
    import tracker_build as tb

    class H:
        pass
    for n_ in ("parsed", "which_team", "two_way", "novig_p", "SPORT", "ML_MARKET", "FRESH_MIN", "tp"):
        setattr(H, n_, getattr(cl, n_))
    H.fxm, H.tb = fxm, tb
    say("PROBABILITY CLV (converted) - SHADOW ONLY. Read-only; nothing written, fetched or changed. " + CALC)
    say(f"generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Category: EXECUTED CLV (real fills) only - never pooled with the other four.")
    say("CLV_STANDARD.md is unchanged; no headline, gate, lane rule or live setting reads any figure below.")
    try:
        st = tb.dec(json.load(open(cl.STATE)))
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        say(f"FATAL: encrypted state unreadable ({type(e).__name__})")
        return 1
    reg = None
    try:
        import registry
        reg = registry.load() if registry.enabled() else None
    except Exception:
        pass
    try:
        mkmap = (json.load(open(cv.MKFILE)) or {}).get("m") or {}
    except Exception:
        mkmap = {}
    recs, stale, bets = build_records(st, tracker, reg, mkmap, H, cv, cb, cl, csel, cstale, fxm)
    LU = cv.LANE_UNIT
    ok = [r for r in recs if r["sc"] and r["sc"]["base"]["status"] == "ok"]
    by = collections.defaultdict(list)
    for r in recs:
        by[r["status"]].append(r)
    nfill = lambda rs: sum(r["fills"] for r in rs)
    games = lambda rs: len({r["game"] for r in rs})
    say("=" * 100)
    say("1. COVERAGE (fills = ledger rows; selections = one bet however many fills; games = unique games)")
    say(f"  ledger rows {len(bets)}; excluded as stale/duplicate {len(stale)}; ELIGIBLE fills {nfill(recs)} in {len(recs)} selections, {games(recs)} games")
    say(f"  stored certified close (ledger 'clv' present): fills {sum(r['fills'] for r in recs if r['stored_clv'] is not None)}")
    for label, st_ in (("same_line (Pinnacle hung the ticket's line)", "same_line"), ("conv_measured (NFL masses)", "conv_measured"),
                       ("conv_estimated (published masses / NBA points)", "conv_estimated"), ("conv_unsupported", "conv_unsupported"),
                       ("no_close", "no_close")):
        rs = by.get(st_, [])
        say(f"  {label:<48} selections {len(rs):4d} fills {nfill(rs):4d} games {games(rs):4d}")
    say("  conv_unsupported by reason (never interpolated):")
    for k_, v_ in collections.Counter((r["why"] or "?").split(":")[0] + (":" + r["why"].split(":")[1] if ":" in (r["why"] or "") and r["why"].split(":")[0] == "no_mass_row" else "")
                                      for r in by.get("conv_unsupported", [])).most_common():
        say(f"      {v_:4d}  {k_}")
    say("  no_close, fixture-cache failures SEPARATE from unavailable Pinnacle market data (opposite remedies):")
    for k_, v_ in sorted(collections.Counter((r["why"] or "?").split(":")[0] for r in by.get("no_close", [])).items()):
        say(f"      {v_:4d}  {k_}")
    for k_, v_ in collections.Counter(r["why"] for r in by.get("no_close", [])).most_common():
        say(f"           {v_:4d}  {k_}")
    say("  Denominators: eligible = every non-stale fill above; priceable (US-executable) = eligible minus Polymarket-global rows:")
    glob_ = [r for r in recs if r["book"] in ("polymarket_global", "polymarket")]
    say(f"      whole population {len(recs)} selections / {nfill(recs)} fills;  priceable {len(recs) - len(glob_)} / {nfill(recs) - nfill(glob_)}")
    say("  READER CHECK (stored ledger CLV vs this script's same-line recompute; a mismatch means suspect the reader first):")
    sl = [r for r in by.get("same_line", []) if r["stored_clv"] is not None and r["sc"]["old"] is not None]
    bad = [r for r in sl if abs(r["stored_clv"] - r["sc"]["old"]) > 0.0006]
    say(f"      same-line rows with a stored CLV {len(sl)}; differing by > 6bp {len(bad)}")
    moved_stored = [r for r in recs if any("main" in str(h_) for h_ in r["stored_how"])]
    say(f"      stored certified rows whose close was an OLD modelled half-point move: {len(moved_stored)} selections")

    say("=" * 100)
    say("2. VALIDATION COHORTS - side by side on the SAME selections. NFL (measured) is the only primary validation cohort.")
    say("  A. same_line: no conversion, so old CLV and Probability CLV share one close. Differences are push scaling only.")
    block("A. same_line, all sports", by.get("same_line", []), LU)
    block("A. same_line, NFL", [r for r in by.get("same_line", []) if r["lg"] == "NFL"], LU)
    say("  B. conv_measured (NFL, converted from Pinnacle's main line with MEASURED masses) - PRIMARY conversion validation:")
    block("B. conv_measured", by.get("conv_measured", []), LU)
    say("  C. conv_estimated - ESTIMATES (published masses / NBA probability points). NOT validated; never mixed with B:")
    for lg_ in sorted({r["lg"] for r in by.get("conv_estimated", [])}):
        block(f"C. conv_estimated {lg_}", [r for r in by["conv_estimated"] if r["lg"] == lg_], LU)
    say("  'naive price-only' (close price ignoring the line difference) for moved rows, beside Probability CLV:")
    for cls_ in ("conv_measured", "conv_estimated"):
        rs = [r for r in by.get(cls_, [])]
        nv = [r["sc"]["naive"] for r in rs]
        say(f"      {cls_:<15} naive {fmt_mean(nv, [r['game'] for r in rs])}")

    say("=" * 100)
    say("3. HALVES (chronological, by selection count) per lane and per source - supported selections only")
    for dim in ("lane", "source"):
        say(f"  by {dim}:")
        for v_ in sorted({r[dim] for r in ok}):
            sub = [r for r in ok if r[dim] == v_]
            h1, h2, nos = split_halves(sub)
            say(f"    {dim} {v_}: {len(sub)} selections ({len(nos)} with no start time, in neither half)")
            for nm_, hh in (("H1", h1), ("H2", h2)):
                if hh:
                    block("   " + nm_, hh, LU)

    say("=" * 100)
    say("4. SENSITIVITY / SIGN CHANGES")
    sl_rows = by.get("same_line", [])
    s1 = sum(1 for r in sl_rows if sgn(r["sc"]["old"]) != sgn(r["sc"]["base"]["pp"]))
    s2 = sum(1 for r in sl_rows if r["sc"]["base"]["ev"] is not None and sgn(r["sc"]["old"]) != sgn(r["sc"]["base"]["ev"]))
    say(f"  same_line rows: sign(old) != sign(Probability CLV) {s1}; sign(old) != sign(EV) {s2} of {len(sl_rows)} (expected 0: same close, same sign)")
    mv = [r for r in recs if r["sc"] and r["sc"]["kind"] == "moved" and r["sc"]["base"]["status"] == "ok"]
    flips = [r for r in mv if sgn(r["sc"]["naive"]) != sgn(r["sc"]["base"]["pp"])]
    say(f"  moved rows with a supported conversion {len(mv)}; naive-vs-converted sign changes {len(flips)}: "
        f"neg->pos {sum(1 for r in flips if sgn(r['sc']['naive']) < 0)}, pos->neg {sum(1 for r in flips if sgn(r['sc']['naive']) > 0)}")
    fee = [r for r in recs if r["sc"] and r["sc"].get("gross_pp") is not None and sgn(r["sc"]["gross_pp"]) != sgn(r["sc"]["base"]["pp"])]
    nfee = [r for r in recs if r["sc"] and r["sc"].get("gross_pp") is not None]
    say(f"  FEE treatment (ProphetX only: displayed price has no fee in it; exchanges are fee-inclusive by construction, effect 0): "
        f"{len(nfee)} rows comparable, {len(fee)} change sign when the 2% fee is applied")
    fragile = [r for r in mv if r["sc"].get("sens") and min(r["sc"]["sens"] + [r["sc"]["base"]["pp"]]) < 0 < max(r["sc"]["sens"] + [r["sc"]["base"]["pp"]])]
    say(f"  CONVERSION assumption (masses +/-1 SE measured, +/-25% published): {len(fragile)} of {len(mv)} converted rows change sign inside that band")
    leg = [r for r in mv if r["stored_clv"] is not None and any("main" in str(h_) for h_ in r["stored_how"])]
    lf = [r for r in leg if sgn(r["stored_clv"]) != sgn(r["sc"]["base"]["pp"])]
    say(f"  LEGACY stored CLV (old half-point-moved closes, sharp_monitor half-point table) vs converted, same selections: {len(leg)} comparable, "
        f"{len(lf)} change sign (neg->pos {sum(1 for r in lf if r['stored_clv'] < 0)}, pos->neg {sum(1 for r in lf if r['stored_clv'] > 0)})")
    say(f"      legacy {fmt_mean([r['stored_clv'] for r in leg], [r['game'] for r in leg])}")
    say(f"      converted ProbCLV {fmt_mean([r['sc']['base']['pp'] for r in leg], [r['game'] for r in leg], 100, ' pp')}")
    say("  sign-change detail (no game names; line move = ticket line minus Pinnacle's main line):")
    for r in flips[:25]:
        sc = r["sc"]
        why = []
        if sc.get("sens") and min(sc["sens"] + [sc["base"]["pp"]]) < 0 < max(sc["sens"] + [sc["base"]["pp"]]):
            why.append("assumption-fragile")
        if sc.get("gross_pp") is not None and sgn(sc["gross_pp"]) != sgn(sc["base"]["pp"]):
            why.append("fee")
        why = "+".join(why) or "line movement"
        say(f"      {r['lg']:<6} {r['status']:<14} move {sc['line_move']:+.1f}  naive {100 * sc['naive']:+.2f}%  "
            f"ProbCLV {100 * sc['base']['pp']:+.2f}pp  driver: {why}")

    say("=" * 100)
    say("5. UNCERTAINTY: every mean above is a selection mean with a GAME-clustered 95% CI (normal approx.); n and games are printed beside it.")
    say("   A mean CI is a statement about this sample's selections, not about the strategy; none of this is a statistical test of edge.")
    say("=" * 100)
    say("6. WHAT WOULD HAVE TO BE TRUE BEFORE Probability CLV COULD REPLACE the same-line headline:")
    for t_ in ("a. Peter amends CLV_STANDARD.md sec 1 (converted closes) and sec 5 in writing - not decided here.",
               "b. Measured landing masses for every sport and market it would cover; NCAAB/NCAAF/NBA currently rest on published estimates.",
               "c. Venue settlement rules verified for each whole-number ticket (SETTLEMENT table is mostly 'unverified').",
               "d. Pinnacle alternate-line probabilities used to back-test the converted close where Pinnacle also hung the ticket's line.",
               "e. Fixture-cache failures reduced (section 1) and coverage not correlated with line movement (compare covered vs uncovered).",
               "f. Out-of-sample stability across a held-out period, with clustered intervals.",
               "g. Peter's explicit approval. No promotion is implied by this report."):
        say("   " + t_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
