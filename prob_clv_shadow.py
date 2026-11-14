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
import gzip
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

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
            try:
                lv.push_ok(book, c1, sport, mtype)        # whole-number ticket: the VENUE's refund rule must be verified
            except lv.Unsupported as u_:
                if same:                                  # quote coverage yes; pp AND EV withheld (both assume a refunded push)
                    out.update(status="ok", cls="same_line_settlement_unverified", r=q_ref, pp=None, ev=None, reason=u_.code)
                    return out
                raise
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
    mx = max(e[3] for e in info["entries"])
    rec = {"kind": kind, "ref_line": ref_line, "q_ref": q_ref, "base": base,
           "limit_ratio": (ent[3] / mx) if mx else None, "is_main": (ent[3] >= mx - 1e-9), "n_lines": len(info["entries"]),
           "age_min": ent[2],
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


# ------------------------------------------------------------------ reconciliation helpers (pure)
def stored_kind(how):
    """How a STORED ledger close was read: exact (verified same-line), moved (modelled half-point move) or none."""
    h = (how or "").strip().lower()
    if h in ("own line", "moneyline"):
        return "exact"
    return "moved" if h.startswith("main") else ("none" if not h else "other")


def compare_fill(stored_clv, stored_close_p, row_dec, q_ref, tol=0.0006):
    """Row-level check of one stored certified fill against the recomputed close. Returns dict(delta, mismatch, cause).
    cause: 'close' (stored close prob differs from the recomputed one), 'price' (the decimal the stored CLV implies differs
    from the row's own after-fee decimal), 'both', 'rounding' (neither; sub-tolerance arithmetic), or 'n/a'."""
    if stored_clv is None or row_dec is None or q_ref is None:
        return {"delta": None, "mismatch": False, "cause": "n/a"}
    re = q_ref * row_dec - 1.0
    d = stored_clv - re
    if abs(d) <= tol:
        return {"delta": d, "mismatch": False, "cause": "agree"}
    close_diff = stored_close_p is not None and abs(stored_close_p - q_ref) > 1e-4
    implied = ((stored_clv + 1.0) / stored_close_p) if stored_close_p else None
    price_diff = implied is not None and abs(implied - row_dec) > 1e-3
    return {"delta": d, "mismatch": True, "cause": "both" if (close_diff and price_diff) else "close" if close_diff
            else "price" if price_diff else "rounding"}


SIDE_LABELS = {"side never recorded", "held team not matched to fixture", "side text matches neither or both teams",
               "bet text names no team", "abbreviation matcher unavailable", "side text too short", "no two distinguishable sides",
               "row has no two sides", "no side text on row"}


def ours_prefix(label, default):
    """D2: a side-resolution failure is OUR row data, never a limit of Pinnacle's market data."""
    return "ROW-DATA(side)" if label in SIDE_LABELS else default


def now_label(rec):
    st = rec["status"]
    if st == "no_close":
        return "no_close:" + (rec["why"] or "?").split(":")[0].split("(")[0]
    return st


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

# PUBLIC-LOG SAFETY. Reason strings from fixture_match / the ladder can embed team names and bet text
# ("AMBIGUOUS: <p1> v <p2>", "the bet text is '<text>'"). Nothing free-text is ever printed: every such string is mapped to a
# FIXED label here, and anything unrecognised is withheld.
SAFE = (("could not split", "row has no two sides"), ("no raw side", "no side text on row"), ("ambiguous", "ambiguous fixture or side match"),
        ("too short", "side text too short"), ("neither or both", "side text matches neither or both teams"),
        ("no venue ticker", "no venue ticker on row"), ("ticker codes", "ticker matches no fixture"),
        ("no two distinguishable", "no two distinguishable sides"), ("no league on", "no league on row"),
        ("no fixture in any cache", "no fixture in any cache"), ("none maps onto", "no candidate maps onto the row"),
        ("names no team", "bet text names no team"), ("not a team", "side never recorded"),
        ("abbreviation matcher", "abbreviation matcher unavailable"), ("held team not matched", "held team not matched to fixture"),
        ("no start time", "no start time"), ("politics", "politics market"), ("did not parse", "bet text did not parse"),
        ("no sport id", "league has no sport id"), ("stale", "closing quote stale"), ("no fresh two-sided", "no fresh two-sided Pinnacle line"),
        ("no two-sided", "no two-sided Pinnacle moneyline"))


def safe_label(x, default="?"):
    """A short label (source, venue) is printed only if it looks like a label: letters, digits, space, ( ) . _ - and at most 40 chars."""
    import re
    t = str(x or "").strip()
    return t if re.fullmatch(r"[A-Za-z0-9 ()._\-]{1,40}", t) else (default if not t else "other (label withheld)")


def safe_reason(text):
    t = str(text or "").lower()
    for sub, lab in SAFE:
        if sub in t:
            return lab
    return "other (text withheld)"


def say(t=""):
    OUT.append(t)
    print(t, flush=True)


def venue_id(book):
    import clv_std as cs
    try:
        return cs.canon(book).replace(".", "_")
    except Exception:
        return str(book or "").lower().replace(" ", "_").replace(".", "_")


def pin_state(dirpath, fid):
    """READ-ONLY state of one fixture's cached Pinnacle file: (state, other_books).
    state: present | absent | unreadable | zero_byte. other_books: how many OTHER cached book files exist for the same
    fixture id (0 = nothing at all was ever stored for it). Never fetches, never writes."""
    p = os.path.join(dirpath, f"{fid}__pinnacle.json.gz")
    try:
        others = sum(1 for n_ in os.listdir(dirpath) if n_.startswith(f"{fid}__") and n_ != f"{fid}__pinnacle.json.gz")
    except OSError:
        others = 0
    if not os.path.exists(p):
        return "absent", others
    try:
        if os.path.getsize(p) == 0:
            return "zero_byte", others
        with gzip.open(p, "rt") as fh:
            json.load(fh)
    except Exception:
        return "unreadable", others
    return "present", others


def cache_inventory(dirpath):
    """Counts only: files by book suffix and the UTC date span of Pinnacle file mtimes (restored mtimes show how old the
    restored snapshot is; they are not game data)."""
    by, pin_m = collections.Counter(), []
    try:
        names = os.listdir(dirpath)
    except OSError:
        return {"files": 0, "by_book": {}, "pin_first": None, "pin_last": None}
    for n_ in names:
        if "__" not in n_:
            continue
        b_ = safe_label(n_.split("__", 1)[1].split(".", 1)[0], "?")
        by[b_] += 1
        if b_ == "pinnacle":
            try:
                pin_m.append(os.path.getmtime(os.path.join(dirpath, n_)))
            except OSError:
                pass
    d_ = lambda t_: datetime.fromtimestamp(t_, timezone.utc).date().isoformat()
    return {"files": sum(by.values()), "by_book": dict(by), "pin_first": d_(min(pin_m)) if pin_m else None,
            "pin_last": d_(max(pin_m)) if pin_m else None}


def stored_fid_relation(stored, resolved, dirpath):
    """How the fixture id our reader resolved relates to the id the ledger stored on the rows when it scored them:
    none | same | different:<file state of the STORED id's Pinnacle file>."""
    stored = {s_ for s_ in stored if s_}
    if not stored:
        return "none"
    if resolved in stored:
        return "same"
    return "different:" + ",".join(sorted({pin_state(dirpath, s_)[0] for s_ in stored}))


def week_of(day):
    """ISO date of the Monday of the week of a 'YYYY-MM-DD' string, else None."""
    try:
        d_ = datetime.strptime(str(day)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d_ - timedelta(days=d_.weekday())).isoformat()


def finished_state(start, now=None):
    """finished | not_finished | unknown, by hist_cache's own rule (a game is final 4 h after its listed start)."""
    try:
        t_ = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        if t_.tzinfo is None:
            t_ = t_.replace(tzinfo=timezone.utc)
    except ValueError:
        return "unknown"
    return "finished" if (now or datetime.now(timezone.utc)) - t_ >= timedelta(hours=4) else "not_finished"


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
    # prep is used ONLY to group rows into selections. The stored CLV of a selection is collapsed from CERTIFIED rows only
    # (clv_coverage's own definition: clv present and not fixture_doubt). The first run collapsed certified and uncertified
    # rows together with a placeholder, which can dilute the stored close - D3/D4 may partly be that reader defect.
    prep = {k: dict(r, clv=(r["clv"] if r.get("clv") is not None else -999)) for k, r in bets.items()}
    obs = csel.selections(prep, tracker, exclude=set(stale))
    recs = []
    for key, o in obs.items():
        ids = o["ids"]
        rows = [bets[i] for i in ids]
        snaps = [r.get("snap") or {} for r in rows]
        snap = snaps[0]
        cert = [(i, bets[i]) for i in ids if bets[i].get("clv") is not None and not bets[i].get("fixture_doubt")]
        oc = csel.collapse(cert) if cert else None
        pairs = [(H.tb.num(s_.get("stake")), H.tb.num(s_.get("to_pay"))) for s_ in snaps]
        full = [(a, b) for a, b in pairs if a and b and b > a]
        dec = (sum(b for _a, b in full) / sum(a for a, _b in full)) if full else cl.eff_dec(snap)
        gross = None
        if snap.get("book") == "ProphetX" and all(s_.get("price") not in (None, "") for s_ in snaps):
            gross = sum((H.tb.num(s_.get("stake")) or 1) * cl.am_to_dec(s_["price"]) for s_ in snaps) / \
                    (sum((H.tb.num(s_.get("stake")) or 1) for s_ in snaps) or 1)
        parts = key.split("|")
        trk = [tracker.get(i) or {} for i in ids]
        rec = {"key": key, "lg": snap.get("league"), "book": venue_id(snap.get("book")), "source": safe_label(snap.get("source")),
               "lane": lane_for(key, o) or "UNKNOWN", "start": o.get("game_start"), "fills": len(ids), "fills_cert": len(cert),
               "game": (snap.get("league"), parts[1] if len(parts) > 1 else key, str(o.get("game_start") or "")[:10]),
               "profit": o.get("profit"), "stake": o.get("stake"), "result": o.get("result"), "dec": dec,
               "stored_clv": oc["clv"] if oc else None, "stored_how": (oc.get("how") if oc else None) or [],
               "fillrows": [{"cert": r_.get("clv") is not None and not r_.get("fixture_doubt"), "clv": r_.get("clv"),
                             "close_p": r_.get("close_p"), "how": r_.get("how"), "dec": cl.eff_dec(r_.get("snap") or {})}
                            for r_ in rows],
               "flags": {"game": bool(snap.get("game")), "bet": bool(snap.get("bet")), "start": bool(snap.get("game_start")),
                         "fixture": any(bool(r_.get("fixture")) for r_ in rows), "tracker_league": any(bool(t_.get("league")) for t_ in trk)},
               "status": None, "why": None, "sc": None,
               "stored_fids": [r_.get("fixture") for r_ in rows], "fid": None, "pin": None, "pin_others": None}
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
            lab = safe_reason(note)
            rec.update(status="no_close", why=f"{ours_prefix(lab, 'FIXTURE-CACHE')}: no fixture matched ({lab})")
            recs.append(rec)
            continue
        rec["fid"] = fid
        h = cv._cached_pin(fid)
        rec["pin"], rec["pin_others"] = pin_state(cv.HC, fid) if h is None else ("present", None)
        if h is None:
            rec.update(status="no_close", why="PINNACLE-DATA: fixture known, history never downloaded")
            recs.append(rec)
            continue
        f = fx_state.get(fid) or alt_f.get(fid) or {}
        info, why = ladder(f, snap, mkmap, cl.book_markets(h, "pinnacle"), H)
        if info is None:
            lab = safe_reason(why)
            cls_ = "POLICY" if ("parse" in str(why) or "politics" in str(why)) else ours_prefix(lab, "PINNACLE-DATA")
            rec.update(status="no_close", why=f"{cls_}: {lab}")
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


def quant(vals, qs=(0, .25, .5, .75, 1)):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return "n/a"
    return " ".join(f"{v[min(len(v) - 1, int(round(q * (len(v) - 1))))]:.2f}" for q in qs)


def block(label, recs, lane_unit):
    if not recs:
        say(f"  {label:<34} n 0")
        return
    g = [r["game"] for r in recs]
    okr = [r for r in recs if r["sc"] and r["sc"]["base"]["status"] == "ok"]
    ppr = [r for r in okr if r["sc"]["base"]["pp"] is not None]
    evr = [r for r in okr if r["sc"]["base"]["ev"] is not None]
    oldr = [r for r in recs if r["sc"] and r["sc"]["old"] is not None]
    say(f"  {label:<34} selections {len(recs)} fills {sum(r['fills'] for r in recs)} games {len(set(g))}  {roi_units(recs, lane_unit)}")
    say(f"      old same-line CLV : {fmt_mean([r['sc']['old'] for r in oldr], [r['game'] for r in oldr])}")
    say(f"      Probability CLV   : {fmt_mean([r['sc']['base']['pp'] for r in ppr], [r['game'] for r in ppr], 100, ' pp')}")
    say(f"      closing-implied EV: {fmt_mean([r['sc']['base']['ev'] for r in evr], [r['game'] for r in evr])}")


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
    SL = ("same_line", "same_line_settlement_unverified")
    say("=" * 100)
    say("1. COVERAGE (fills = ledger rows; selections = one bet however many fills; games = unique games)")
    say(f"  ledger rows {len(bets)}; excluded as stale/duplicate {len(stale)}; ELIGIBLE fills {nfill(recs)} in {len(recs)} selections, {games(recs)} games")
    say(f"  stored certified close (clv present, not fixture_doubt) - FILLS: {sum(r['fills_cert'] for r in recs)} in "
        f"{sum(1 for r in recs if r['fills_cert'])} selections")
    say(f"  (run 1 reported 194: it counted EVERY fill of any selection holding a stored CLV, i.e. "
        f"{sum(r['fills'] for r in recs if r['fills_cert'])} here - that was a reader defect, not a ledger fact)")
    for label, st_ in (("same_line (Pinnacle hung the ticket's line)", "same_line"),
                       ("same_line_settlement_unverified (D1; pp/EV withheld)", "same_line_settlement_unverified"),
                       ("conv_measured (NFL masses)", "conv_measured"), ("conv_estimated (published / NBA points)", "conv_estimated"),
                       ("conv_unsupported", "conv_unsupported"), ("no_close", "no_close")):
        rs = by.get(st_, [])
        say(f"  {label:<56} selections {len(rs):4d} fills {nfill(rs):4d} games {games(rs):4d}")
    say("  conv_unsupported by reason (never interpolated):")
    for k_, v_ in collections.Counter((r["why"] or "?").split(":")[0] + (":" + r["why"].split(":")[1] if r["why"] and r["why"].startswith("no_mass_row") else "")
                                      for r in by.get("conv_unsupported", [])).most_common():
        say(f"      {v_:4d}  {k_}")
    say("  no_close - OUR data (ROW-DATA, FIXTURE-CACHE) kept apart from Pinnacle market data (PINNACLE-DATA), opposite remedies:")
    for k_, v_ in sorted(collections.Counter((r["why"] or "?").split(":")[0] for r in by.get("no_close", [])).items()):
        say(f"      {v_:4d}  {k_}")
    for k_, v_ in collections.Counter(r["why"] for r in by.get("no_close", [])).most_common():
        say(f"           {v_:4d}  {k_}")
    glob_ = [r for r in recs if r["book"] in ("polymarket_global", "polymarket")]
    say(f"  Denominators: whole population {len(recs)} selections / {nfill(recs)} fills; priceable (US-executable, "
        f"excl. Polymarket-global) {len(recs) - len(glob_)} / {nfill(recs) - nfill(glob_)}")
    say("  venues present (selections): " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r["book"] for r in recs).most_common()))

    say("=" * 100)
    say("2. COHORTS - the SAME selections, side by side. NFL (measured) is the only primary conversion-validation cohort.")
    block("A. same_line, all sports", by.get("same_line", []), LU)
    block("A. same_line, NFL", [r for r in by.get("same_line", []) if r["lg"] == "NFL"], LU)
    block("A'. same_line, settlement unverified", by.get("same_line_settlement_unverified", []), LU)
    block("B. conv_measured", by.get("conv_measured", []), LU)
    for lg_ in sorted({r["lg"] for r in by.get("conv_estimated", [])}):
        block(f"C. conv_estimated {lg_}", [r for r in by["conv_estimated"] if r["lg"] == lg_], LU)

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
    sl_rows = [r for r in by.get("same_line", []) if r["sc"]["base"]["pp"] is not None]
    s1 = sum(1 for r in sl_rows if sgn(r["sc"]["old"]) != sgn(r["sc"]["base"]["pp"]))
    s2 = sum(1 for r in sl_rows if r["sc"]["base"]["ev"] is not None and sgn(r["sc"]["old"]) != sgn(r["sc"]["base"]["ev"]))
    say(f"  same_line rows: sign(old) != sign(Probability CLV) {s1}; sign(old) != sign(EV) {s2} of {len(sl_rows)} (expected 0)")
    mv = [r for r in recs if r["sc"] and r["sc"]["kind"] == "moved" and r["sc"]["base"]["status"] == "ok"]
    say(f"  moved rows with a supported conversion: {len(mv)}")
    nfee = [r for r in recs if r["sc"] and r["sc"].get("gross_pp") is not None and r["sc"]["base"]["pp"] is not None]
    fee = [r for r in nfee if sgn(r["sc"]["gross_pp"]) != sgn(r["sc"]["base"]["pp"])]
    say(f"  FEE (ProphetX only; exchanges are fee-inclusive by construction): {len(nfee)} comparable, {len(fee)} change sign")

    say("=" * 100)
    say("5. D3 / D4 RECONCILIATION (fill level; every ledger fill is in exactly one line below)")
    br, brsel = collections.Counter(), collections.defaultdict(set)
    cmp_rows = []
    for idx, r in enumerate(recs):
        nl = now_label(r)
        for f in r["fillrows"]:
            if f["cert"]:
                k = stored_kind(f["how"])
                sub = ""
                if r["sc"] is not None and r["sc"]["kind"] == "same_line" and k == "exact":
                    c = compare_fill(f["clv"], f["close_p"], f["dec"], r["sc"]["q_ref"])
                    sub = " | agree" if not c["mismatch"] else f" | DIFFER({c['cause']})"
                    if c["mismatch"]:
                        cmp_rows.append((idx, r, f, c))
                lab = (f"stored[{k}]", nl + sub)
            else:
                lab = ("no stored close", nl)
            br[lab] += 1
            brsel[lab].add(idx)
    say(f"  {'stored close':<18}{'now':<62}{'fills':>6}{'selections':>12}")
    for lab, n_ in sorted(br.items(), key=lambda x: -x[1]):
        say(f"  {lab[0]:<18}{lab[1]:<62}{n_:>6}{len(brsel[lab]):>12}")
    say(f"  TOTAL {sum(br.values())} fills (must equal eligible {nfill(recs)}): {'TIES' if sum(br.values()) == nfill(recs) else 'DOES NOT TIE'}")
    allc = [(i, r, f) for i, r in enumerate(recs) for f in r["fillrows"] if f["cert"] and r["sc"] is not None
            and r["sc"]["kind"] == "same_line" and stored_kind(f["how"]) == "exact"]
    say(f"  D3 at FILL level: {len(allc)} stored exact-close fills compared; {len(cmp_rows)} differ by > 6 bp; causes: "
        + (", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(c["cause"] for *_x, c in cmp_rows).items()) or "none"))
    selm = [r for r in recs if r["sc"] is not None and r["sc"]["kind"] == "same_line" and r["stored_clv"] is not None and r["dec"]
            and r["fills_cert"] == r["fills"] and all(stored_kind(f["how"]) == "exact" for f in r["fillrows"])]
    selbad = [r for r in selm if abs(r["stored_clv"] - old_same_line(r["sc"]["q_ref"], r["dec"])) > 0.0006]
    say(f"  D3 at SELECTION level (run 1 method, now over FULLY certified selections only): {len(selm)} compared, {len(selbad)} differ by > 6 bp")
    mixed = [r for r in recs if 0 < r["fills_cert"] < r["fills"]]
    say(f"  selections with BOTH certified and uncertified fills (the run-1 reader mixed these): {len(mixed)} ({nfill(mixed)} fills)")
    say("  D3 detail (numbers only; ordinal, not a key): idx sport venue delta_bp stored_close recomputed_close row_dec implied_dec cause fills limit_ratio")
    for j, (idx, r, f, c) in enumerate(cmp_rows[:15]):
        q_ = r["sc"]["q_ref"]
        imp = (f["clv"] + 1) / f["close_p"] if f["close_p"] else None
        say(f"    {j:>2} {r['lg']:<6} {r['book']:<12} {1e4 * c['delta']:+7.1f}bp  {f['close_p'] if f['close_p'] is None else round(f['close_p'], 4)}  {q_:.4f}  "
            f"{f['dec']:.4f}  {imp if imp is None else round(imp, 4)}  {c['cause']:<8} fills {r['fills']}  lim "
            f"{'n/a' if r['sc']['limit_ratio'] is None else format(r['sc']['limit_ratio'], '.2f')}")

    say("=" * 100)
    say("6. D1 / D2 / D5 / MISSING LEAGUE")
    u = by.get("same_line_settlement_unverified", [])
    say(f"  D1 same_line_settlement_unverified: {len(u)} selections / {nfill(u)} fills; whole-number ticket line: "
        f"{sum(1 for r in u if r['sc']['ref_line'] is not None and abs(r['sc']['ref_line'] - round(r['sc']['ref_line'])) < 1e-9)}; "
        f"ticket line == Pinnacle line (kind same_line): {sum(1 for r in u if r['sc']['kind'] == 'same_line')}")
    say("      by sport/venue: " + ", ".join(f"{a_}/{b_} {n_}" for (a_, b_), n_ in collections.Counter((r['lg'], r['book']) for r in u).most_common()))
    hc = [r for r in u if r["fills_cert"]]
    say(f"      of these, selections already in the EXISTING stored-certified headline population: {len(hc)} ({sum(r['fills_cert'] for r in hc)} certified fills) "
        f"- they carry the same unverified refund assumption today")
    ms = [r for r in by.get("conv_unsupported", []) if (r["why"] or "").startswith("settlement_rule_unverified")]
    say(f"      moved-line tickets unsupported only by settlement: {len(ms)}")
    d2 = [r for r in by.get("no_close", []) if (r["why"] or "").startswith("ROW-DATA(side)")]
    say(f"  D2 side-resolution failures now labelled ROW-DATA(side): {len(d2)} selections / {nfill(d2)} fills")
    sa = by.get("same_line", [])
    mn = [r for r in sa if r["sc"]["is_main"]]
    al = [r for r in sa if not r["sc"]["is_main"]]
    say(f"  D5 same_line closes: main-line (largest limit on the ladder) {len(mn)} sel / {nfill(mn)} fills; alternate-line {len(al)} sel / {nfill(al)} fills")
    say(f"      alternate-line limit as a ratio of the ladder's main-line limit (min 25% 50% 75% max): {quant([r['sc']['limit_ratio'] for r in al])}")
    say("      by sport (main/alt): " + ", ".join(f"{lg_} {sum(1 for r in mn if r['lg'] == lg_)}/{sum(1 for r in al if r['lg'] == lg_)}"
                                                for lg_ in sorted({r['lg'] for r in sa})))
    for nm_, grp in (("main-line", mn), ("alternate-line", al)):
        block(f"D5 {nm_}", grp, LU)
    # D5 sensitivity cut (Peter-approved Nov 14, sensitivity only: NOT a validated rule). Ratio = this line's Pinnacle limit / the
    # ladder's largest limit; the main line is 1.00 by construction.
    hi = [r for r in sa if r["sc"]["limit_ratio"] is not None and r["sc"]["limit_ratio"] >= 0.9]
    lo = [r for r in sa if r["sc"]["limit_ratio"] is not None and r["sc"]["limit_ratio"] < 0.9]
    na_ = [r for r in sa if r["sc"]["limit_ratio"] is None]
    say("  D5 cut by limit ratio (sensitivity only; no main-line superiority claim; n and distinct games shown):")
    for nm_, grp in (("limit ratio >= 0.90", hi), ("limit ratio <  0.90", lo), ("limit ratio n/a", na_)):
        block(f"D5 {nm_}", grp, LU)
        if grp:
            say(f"      by source: " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r['source'] for r in grp).most_common())
                + f"  | of which alternate (ratio < 1): {sum(1 for r in grp if not r['sc']['is_main'])}")
    rows_nl = [r for r in by.get("no_close", []) if (r["why"] or "").startswith("ROW-DATA: no league")]
    say(f"  MISSING LEAGUE: {len(rows_nl)} selections / {nfill(rows_nl)} fills")
    say("      by source: " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r['source'] for r in rows_nl).most_common()))
    say("      by venue : " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r['book'] for r in rows_nl).most_common()))
    fl = collections.Counter(k_ for r in rows_nl for k_, v_ in r["flags"].items() if v_)
    say(f"      fields present on these rows (of {len(rows_nl)}): " + ", ".join(f"{k_} {fl.get(k_, 0)}" for k_ in ("game", "bet", "start", "fixture", "tracker_league")))
    say(f"      recoverable from an immutable source field with no guessing (tracker row already carries a league): {fl.get('tracker_league', 0)}; "
        f"with a stored fixture id: {fl.get('fixture', 0)}")
    say("=" * 100)
    say("6b. D6 - SELECTIONS WITH A KNOWN FIXTURE BUT NO USABLE CACHED PINNACLE FILE (read-only; counts only)")
    inv = cache_inventory(cv.HC)
    say(f"  restored cache inventory: {inv['files']} files; by book: " + ", ".join(f"{k_} {v_}" for k_, v_ in sorted(inv["by_book"].items()))
        + f"; Pinnacle file mtimes span {inv['pin_first']} .. {inv['pin_last']} (UTC dates)")
    nh = [r for r in recs if (r["why"] or "").startswith("PINNACLE-DATA: fixture known, history never downloaded")]
    nhc = [r for r in nh if r["fills_cert"]]
    say(f"  no-history selections: {len(nh)} sel / {nfill(nh)} fills / {len({r.get("fid") for r in nh})} distinct fixtures / {len({r['game'] for r in nh})} distinct games")
    say(f"  of which STORED-CERTIFIED (legacy clv_coverage definition): {len(nhc)} sel / {sum(r['fills_cert'] for r in nhc)} certified fills / "
        f"{len({r.get("fid") for r in nhc})} distinct fixtures / {len({r['game'] for r in nhc})} distinct games")
    for nm_, grp in (("all no-history", nh), ("stored-certified", nhc)):
        if not grp:
            continue
        say(f"  [{nm_}] Pinnacle file state: " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r.get("pin") for r in grp).most_common()))
        say(f"  [{nm_}] other-book files cached for the same fixture id: some {sum(1 for r in grp if r.get("pin_others"))} / none {sum(1 for r in grp if not r.get("pin_others"))}")
        say(f"  [{nm_}] ledger-stored fixture id vs the id this reader resolved: "
            + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(stored_fid_relation(r.get("stored_fids") or [], r.get("fid"), cv.HC) for r in grp).most_common()))
        say(f"  [{nm_}] game final by hist_cache's 4 h rule: "
            + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(finished_state(r["start"]) for r in grp).most_common()))
        say(f"  [{nm_}] by league: " + ", ".join(f"{k_} {v_}" for k_, v_ in collections.Counter(r["lg"] for r in grp).most_common()))
        if inv["pin_last"]:
            say(f"  [{nm_}] game start after the newest restored Pinnacle file: "
                f"{sum(1 for r in grp if str(r['start'] or '')[:10] > inv['pin_last'])} of {len(grp)}")
    wk = collections.defaultdict(lambda: [0, 0, 0])
    for r in recs:
        if r.get("fid") is None:
            continue
        w_ = week_of(r["start"]) or "unknown"
        wk[w_][0] += 1
        wk[w_][1] += 1 if r.get("pin") == "present" else 0
        wk[w_][2] += 1 if (r.get("pin") != "present" and r["fills_cert"]) else 0
    say("  by game-start week (Monday): selections with a resolved fixture | Pinnacle file present | missing AND stored-certified")
    for w_ in sorted(wk):
        say(f"    {w_}  {wk[w_][0]:>4} {wk[w_][1]:>5} {wk[w_][2]:>5}")
    say("=" * 100)
    say("7. UNCERTAINTY: every mean is a selection mean with a GAME-clustered 95% CI (normal approx.); not a test of edge.")
    say("   Nothing here is promoted; CLV_STANDARD.md, the headline, gates and live settings are untouched.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e_:        # the message of a KeyError etc. can be a selection key (game names): print the type only
        print(f"FATAL: {type(e_).__name__} (message and traceback withheld: they can carry row text)", flush=True)
        sys.exit(1)
