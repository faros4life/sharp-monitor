"""Project 2 audit - PURE functions (no network, no tracker/registry import). Read-only arithmetic.

IDENTITY RULES
  * Rows are consolidated ONLY when their venue order id resolves to exactly ONE registry claim (venue-scoped) and several rows
    share that claim's (venue, play key, lane). Nothing else is ever merged: not game+bet+book, not Novig market|outcome
    (a position id, not an order id), not a ProphetX strike id (a market id, not an order id).
  * Lane comes from the registry claim. A tracker stamp that disagrees is reported as a CONFLICT (registry wins, row listed).
  * Buckets never mix: EXACT:<lane> | FUZZY:<tracker lane, unverified> | UNATTRIBUTED(<reason>).
MONEY: stake and profit must be finite numbers, stake > 0, row settled. ROI = net profit / amount risked on those rows only.
  Fee treatment is NOT established here: it is whatever each venue reader wrote into 'profit'. ROI is therefore also split by book.
UNITS: UNAVAILABLE (no verified historical unit schedule).
TIME: four different fields; none is called fill time. Chronological key = first present of game_start, settled, placed,
  first_seen; the basis used is reported per lane, and a lane that mixes bases is flagged."""
import math
import re
from collections import Counter

SETTLED = ("W", "L", "P")
TIME_FIELDS = ("game_start", "settled", "placed", "first_seen")


def _norm(v):
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def finite(x):
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def verified_money(r):
    s, p = finite(r.get("stake")), finite(r.get("profit"))
    return r.get("result") in SETTLED and s is not None and s > 0 and p is not None


def time_basis(r):
    for f in TIME_FIELDS:
        if r.get(f):
            return f, str(r[f])
    return None, ""


def resolve(row, index, norm=_norm):
    """index: {order_id: [(venue, play_key, lane), ...]}.
    -> (status, lane, play_key). status: exact | no_order_ref | ref_not_in_registry | ambiguous_claims"""
    ref = str(row.get("order_ref") or "")
    if not ref:
        return "no_order_ref", None, None
    ven = norm(row.get("book"))
    claims = {(k, ln) for v, k, ln in index.get(ref, []) if not v or not ven or norm(v) == ven}
    if not claims:
        return "ref_not_in_registry", None, None
    if len(claims) > 1:
        return "ambiguous_claims", None, None
    (k, ln), = claims
    if not ln or not k:
        return "ambiguous_claims", None, None          # a claim without a lane or key proves nothing
    return "exact", ln, k


def classify(rows, index, norm=_norm):
    """-> (items, stats, conflicts). Each item: (row, bucket, group_key or None)."""
    items, st, conflicts = [], Counter(), []
    for i, r in enumerate(rows):
        status, lane, key = resolve(r, index, norm)
        st[status] += 1
        if status == "exact":
            if r.get("lane_src") == "registry-order-id" and r.get("lane") and r["lane"] != lane:
                st["lane_conflict"] += 1
                conflicts.append({"row": i, "book": r.get("book"), "tracker_lane": r.get("lane"), "registry_lane": lane})
            items.append((r, "EXACT:" + lane, (norm(r.get("book")), key, lane)))
        elif r.get("lane"):
            items.append((r, "FUZZY:" + str(r["lane"]), None))
        else:
            items.append((r, "UNATTRIBUTED(" + status + ")", None))
    return items, dict(st), conflicts


def _combine(rows):
    """One play from several rows that share a verified registry claim. Money counts only if EVERY row is finite; a play whose rows
    disagree on result, or are not all settled, stays unsettled/ambiguous (None) and is never guessed."""
    res = {r.get("result") for r in rows}
    result = next(iter(res)) if len(res) == 1 and next(iter(res)) in SETTLED else None
    sv, pv = [finite(r.get("stake")) for r in rows], [finite(r.get("profit")) for r in rows]
    ok = result is not None and None not in sv and None not in pv
    pick = lambda f, fn: fn([str(r[f]) for r in rows if r.get(f)] or [""])
    return {"result": result, "stake": sum(sv) if ok else None, "profit": sum(pv) if ok else None,
            "game_start": pick("game_start", min), "settled": pick("settled", max), "placed": pick("placed", min),
            "first_seen": pick("first_seen", min), "book": rows[0].get("book"), "game": rows[0].get("game"),
            "bet": rows[0].get("bet"), "rows": len(rows), "mixed_results": len(res) > 1}


def consolidate(items):
    """-> {bucket: [play, ...]}. Only items with a group key merge; each unkeyed row is its own play."""
    groups, out = {}, {}
    for r, bucket, key in items:
        if key is None:
            p = _combine([r])
            p["rows"] = 1
            out.setdefault(bucket, []).append(p)
        else:
            groups.setdefault((bucket, key), []).append(r)
    for (bucket, _), rs in groups.items():
        out.setdefault(bucket, []).append(_combine(rs))
    return out


def _agg(plays):
    ok = [p for p in plays if verified_money(p)]
    risked, net = sum(p["stake"] for p in ok), sum(p["profit"] for p in ok)
    by_book = {}
    for b in sorted({str(p.get("book")) for p in ok}):
        q = [p for p in ok if str(p.get("book")) == b]
        rk, nt = sum(p["stake"] for p in q), sum(p["profit"] for p in q)
        by_book[b] = {"n": len(q), "risked": round(rk, 2), "net": round(nt, 2), "roi_pct": round(nt / rk * 100, 2)}
    return {"settled": len(plays), "verified_money": len(ok), "unverified_money": len(plays) - len(ok),
            "W": sum(p["result"] == "W" for p in plays), "L": sum(p["result"] == "L" for p in plays),
            "P": sum(p["result"] == "P" for p in plays), "risked": round(risked, 2), "net": round(net, 2),
            "roi_pct": round(net / risked * 100, 2) if risked else None, "by_book": by_book}


def bucket_report(plays):
    """Halves and last 50 are cut on ALL settled plays that have a time, BEFORE any money exclusion."""
    settled = [p for p in plays if p.get("result") in SETTLED]
    timed = sorted([p for p in settled if time_basis(p)[0]], key=lambda p: time_basis(p)[1])
    basis = Counter(time_basis(p)[0] for p in timed)
    h = len(timed) // 2
    rng = lambda f: [min(v), max(v)] if (v := [str(p[f]) for p in plays if p.get(f)]) else None
    return {"open_or_ambiguous": len(plays) - len(settled), "settled_no_time": len(settled) - len(timed),
            "all": _agg(settled), "H1": _agg(timed[:h]), "H2": _agg(timed[h:]), "last50": _agg(timed[-50:]),
            "time_basis_used": dict(basis), "MIXED_TIME_BASIS": len(basis) > 1,
            "placed_range": rng("placed"), "first_seen_range": rng("first_seen"), "settled_range": rng("settled"),
            "game_start_range": rng("game_start"), "multi_row_plays": sum(p["rows"] > 1 for p in plays),
            "mixed_result_plays": sum(p["mixed_results"] for p in plays),
            "possible_split_flagged_NOT_MERGED": sum(v - 1 for v in Counter((p.get("game"), p.get("bet"), p.get("book")) for p in plays).values() if v > 1),
            "units": "UNAVAILABLE (no verified unit schedule)"}


def build(rows, index, norm=_norm):
    items, stats, conflicts = classify(rows, index, norm)
    return {"join": stats, "lane_conflicts": conflicts,
            "buckets": {b: bucket_report(ps) for b, ps in sorted(consolidate(items).items())}}
