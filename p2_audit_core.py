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
TIME: four different fields; none is called fill time. Every value is parsed to UTC; an unparseable value counts as no time. Chronological key = first present of game_start, settled, placed,
  first_seen; the basis used is reported per lane, and a lane that mixes bases is flagged."""
import math
import re
from collections import Counter
from datetime import datetime, timezone

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


def utc(v):
    """A timestamp as an aware UTC datetime, or None. Naive values are taken as UTC; unparseable -> None (never sorted as text)."""
    if not v:
        return None
    try:
        t = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


def time_basis(r):
    """(field, UTC datetime) of the first PARSEABLE time field, or (None, None)."""
    for f in TIME_FIELDS:
        t = utc(r.get(f))
        if t is not None:
            return f, t
    return None, None


# executor.LANE_NAME (executor.py:951) plus the registry's own spellings. Matched after _norm, so 'r1' == 'R1'.
LANE_CANON = {"rules": "PHASE 1", "rule": "PHASE 1", "phase1": "PHASE 1", "lane1": "PHASE 1",
              "board": "BOARD V3", "boardv3": "BOARD V3", "r1": "R1", "lane2": "LANE 2"}


def canon_lane(v):
    """Canonical lane name, or None for an empty value. An unknown spelling is returned as-is (upper-cased), so it can only
    ever create a CONFLICT, never silently match."""
    n = _norm(v)
    if not n:
        return None
    return LANE_CANON.get(n, str(v).strip().upper())


def resolve(row, index, norm=_norm):
    """index: {order_id: [(venue, play_key, lane), ...]}.
    -> (status, lane, play_key). status: exact | no_order_ref | ref_not_in_registry | venue_unmatched | ambiguous_claims
    A claim counts only when BOTH the row's venue and the claim's venue are present and equal after normalisation; a missing
    venue on either side is venue_unmatched, never a wildcard."""
    ref = str(row.get("order_ref") or "")
    if not ref:
        return "no_order_ref", None, None
    cl = index.get(ref, [])
    if not cl:
        return "ref_not_in_registry", None, None
    ven = norm(row.get("book"))
    claims = {(k, ln) for v, k, ln in cl if v and ven and norm(v) == ven}
    if not claims:
        return "venue_unmatched", None, None
    if len(claims) > 1:
        return "ambiguous_claims", None, None
    (k, ln), = claims
    if not ln or not k:
        return "ambiguous_claims", None, None          # a claim without a lane or key proves nothing
    return "exact", ln, k


def classify(rows, index, norm=_norm):
    """-> (items, stats, conflicts). Each item: (row, bucket, group_key or None).
    Any non-empty tracker lane or lane_fuzzy that differs from the registry lane (after canon_lane) is a CONFLICT, whatever
    lane_src says: the row goes to CONFLICT(registry=<lane>), is listed in conflicts, is never merged and never counted EXACT."""
    items, st, conflicts = [], Counter(), []
    for i, r in enumerate(rows):
        status, lane, key = resolve(r, index, norm)
        if status == "exact":
            reg_c = canon_lane(lane)
            seen = {canon_lane(r.get(f)) for f in ("lane", "lane_fuzzy")} - {None}
            if seen and seen != {reg_c}:
                st["lane_conflict"] += 1
                conflicts.append({"row": i, "book": r.get("book"), "tracker_lanes": sorted(seen), "registry_lane": reg_c})
                items.append((r, f"CONFLICT(registry={reg_c})", None))
                continue
            st["exact"] += 1
            items.append((r, "EXACT:" + reg_c, (norm(r.get("book")), key, reg_c)))
            continue
        st[status] += 1
        if r.get("lane"):
            items.append((r, "FUZZY:" + (canon_lane(r["lane"]) or str(r["lane"])), None))
        else:
            items.append((r, "UNATTRIBUTED(" + status + ")", None))
    return items, dict(st), conflicts


def _combine(rows):
    """One play from several rows that share a verified registry claim. Money counts only if EVERY row is finite; a play whose rows
    disagree on result, or are not all settled, stays unsettled/ambiguous (None) and is never guessed."""
    res = {r.get("result") for r in rows}
    result = next(iter(res)) if len(res) == 1 and next(iter(res)) in SETTLED else None
    sv, pv = [finite(r.get("stake")) for r in rows], [finite(r.get("profit")) for r in rows]
    # EVERY component stake must be finite and > 0: one bad component (e.g. -50 beside 100) makes the whole play's money
    # unverified, so a sum can never launder it into a valid 50.
    ok = result is not None and None not in sv and None not in pv and all(v > 0 for v in sv)
    def pick(f, fn):
        ts = [(utc(r.get(f)), r.get(f)) for r in rows if utc(r.get(f)) is not None]
        return fn(ts, key=lambda x: x[0])[1] if ts else ""
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
    timed = sorted([p for p in settled if time_basis(p)[0]], key=lambda p: time_basis(p)[1])   # aware UTC datetimes
    basis = Counter(time_basis(p)[0] for p in timed)
    h = len(timed) // 2
    def rng(f):
        v = sorted(t for t in (utc(p.get(f)) for p in plays) if t is not None)
        return [v[0].isoformat(), v[-1].isoformat()] if v else None
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


CSV_FIELDS = ("bucket", "segment", "book", "plays", "verified_money", "W", "L", "P", "risked", "net", "roi_pct", "first", "last")


def render(rep):
    """(text, csv_rows) for PRIVATE delivery only. Aggregates per bucket and segment; never a game, bet, ticket or row."""
    L = ["PROJECT 2 - live lane audit (private). Buckets never mix: EXACT = venue order id -> one registry claim;",
         "FUZZY = the tracker's own lane label (UNVERIFIED); UNATTRIBUTED = no provable lane; CONFLICT = tracker vs registry disagree.",
         "Units: UNAVAILABLE (no verified unit schedule with effective dates). ROI = net / risked on verified-money plays only.",
         f"Join: {rep.get('join')} | lane conflicts: {len(rep.get('lane_conflicts') or [])}", ""]
    rows = []
    for b, v in (rep.get("buckets") or {}).items():
        L.append(f"[{b}]  open/ambiguous {v['open_or_ambiguous']}  settled-no-time {v['settled_no_time']}  "
                 f"time basis {v['time_basis_used']}{'  MIXED' if v['MIXED_TIME_BASIS'] else ''}")
        rg = v.get("game_start_range") or v.get("settled_range") or [None, None]
        for seg in ("all", "H1", "H2", "last50"):
            a = v[seg]
            roi = "n/a" if a["roi_pct"] is None else f"{a['roi_pct']:+.2f}%"
            L.append(f"  {seg:<6} plays {a['settled']:>4} verified {a['verified_money']:>4}  W-L-P {a['W']}-{a['L']}-{a['P']}  "
                     f"risked {a['risked']:.2f} net {a['net']:+.2f} ROI {roi}")
            rows.append({"bucket": b, "segment": seg, "book": "ALL", "plays": a["settled"], "verified_money": a["verified_money"],
                         "W": a["W"], "L": a["L"], "P": a["P"], "risked": a["risked"], "net": a["net"], "roi_pct": a["roi_pct"],
                         "first": rg[0] if seg == "all" else "", "last": rg[1] if seg == "all" else ""})
            for bk, x in a["by_book"].items():
                rows.append({"bucket": b, "segment": seg, "book": bk, "plays": x["n"], "verified_money": x["n"], "W": "", "L": "",
                             "P": "", "risked": x["risked"], "net": x["net"], "roi_pct": x["roi_pct"], "first": "", "last": ""})
        L.append(f"  multi-row plays {v['multi_row_plays']}, mixed-result plays {v['mixed_result_plays']}, "
                 f"possible splits flagged (not merged) {v['possible_split_flagged_NOT_MERGED']}")
        L.append("")
    return "\n".join(L), rows
