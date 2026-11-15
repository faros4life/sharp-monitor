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


def ambiguity_kind(claims):
    """Fixed label for WHY one order id has several (key, lane) claims - counts only, no identifier.
    different_lanes | same_lane_prefix_variant (one key is the other with a lane prefix) | same_lane_different_keys"""
    lanes = {canon_lane(ln) for _k, ln in claims}
    if len(lanes) > 1:
        return "different_lanes"
    keys = [str(k) for k, _ln in claims]
    if len(keys) == 2 and any(a != b and a.split("|", 1)[-1] == b for a in keys for b in keys):
        return "same_lane_prefix_variant"
    return "same_lane_different_keys"


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
        return "ambiguous_claims:" + ambiguity_kind(claims), None, None
    (k, ln), = claims
    if not ln or not k:
        return "ambiguous_claims", None, None          # a claim without a lane or key proves nothing
    return "exact", ln, k


def classify(rows, index, norm=_norm, links=None):
    """-> (items, stats, conflicts). Each item: (row, bucket, group_key or None).
    Any non-empty tracker lane or lane_fuzzy that differs from the registry lane (after canon_lane) is a CONFLICT, whatever
    lane_src says: the row goes to CONFLICT(registry=<lane>), is listed in conflicts, is never merged and never counted EXACT."""
    items, st, conflicts = [], Counter(), []
    for i, r in enumerate(rows):
        status, lane, key = resolve(r, index, norm)
        via = "order_ref"
        if status == "no_order_ref" and links is not None:
            ls, ll, lk = resolve_link(r, links, index, norm)
            st["link:" + ls] += 1
            if ls == "exact_link":
                status, lane, key, via = "exact", ll, lk, "venue_link"
        if status == "exact":
            reg_c = canon_lane(lane)
            seen = {canon_lane(r.get(f)) for f in ("lane", "lane_fuzzy")} - {None}
            if seen and seen != {reg_c}:
                st["lane_conflict"] += 1
                conflicts.append({"row": i, "book": r.get("book"), "tracker_lanes": sorted(seen), "registry_lane": reg_c})
                items.append((r, f"CONFLICT(registry={reg_c})", None))
                continue
            st["exact"] += 1
            if via == "venue_link":
                st["exact_via_venue_link"] += 1
            # a venue-linked POSITION is its own play (never merged with another row); an order_ref row groups by claim
            gk = (norm(r.get("book")), key, reg_c) if via == "order_ref" else ("link", str(r.get("id")), reg_c)
            items.append((r, "EXACT:" + reg_c, gk))
            continue
        st[status] += 1
        status = status.split(":", 1)[0]
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
            "bet": rows[0].get("bet"), "rows": len(rows), "mixed_results": len(res) > 1,
            "ids": [str(r.get("id") or "") for r in rows]}


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


def _clv(plays, clv):
    """Certified Pinnacle CLV per play: the mean of its rows' certified values, and ONLY when every row
    carries one. A play with any missing close is counted missing, never as zero (Peter, 15 Nov)."""
    if clv is None:
        return {"clv_n": None}
    vals = []
    for p in plays:
        v = [clv.get(i) for i in p.get("ids") or []]
        if v and None not in v:
            vals.append(sum(v) / len(v))
    n = len(vals)
    return {"clv_n": n, "clv_missing": len(plays) - n,
            "clv_mean_pct": round(100 * sum(vals) / n, 2) if n else None,
            "clv_beat_pct": round(100 * sum(v > 0 for v in vals) / n, 1) if n else None}


def _agg(plays, clv=None):
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
            "roi_pct": round(net / risked * 100, 2) if risked else None, "by_book": by_book,
            **_clv(plays, clv)}


def time_diag(plays, now=None):
    """Counts only: per time field, how many plays carry it, how many lie AFTER the run time (a scheduled game_start can, a
    settlement should not), and how many are exactly 00:00:00 UTC (often a date-only default, not a real time)."""
    now = now or datetime.now(timezone.utc)
    out = {}
    for f in TIME_FIELDS:
        ts = [t for t in (utc(p.get(f)) for p in plays) if t is not None]
        raw = [p.get(f) for p in plays if p.get(f)]
        out[f] = {"present": len(ts), "unparseable": len(raw) - len(ts), "after_run": sum(1 for t in ts if t > now),
                  "midnight_utc": sum(1 for t in ts if (t.hour, t.minute, t.second) == (0, 0, 0))}
    return out


def bucket_report(plays, clv=None):
    """Halves and last 50 are cut on ALL settled plays that have a time, BEFORE any money exclusion."""
    settled = [p for p in plays if p.get("result") in SETTLED]
    timed = sorted([p for p in settled if time_basis(p)[0]], key=lambda p: time_basis(p)[1])   # aware UTC datetimes
    basis = Counter(time_basis(p)[0] for p in timed)
    h = len(timed) // 2
    def rng(f):
        v = sorted(t for t in (utc(p.get(f)) for p in plays) if t is not None)
        return [v[0].isoformat(), v[-1].isoformat()] if v else None
    return {"open_or_ambiguous": len(plays) - len(settled), "settled_no_time": len(settled) - len(timed),
            "all": _agg(settled, clv), "H1": _agg(timed[:h], clv), "H2": _agg(timed[h:], clv),
            "last50": _agg(timed[-50:], clv),
            "time_basis_used": dict(basis), "MIXED_TIME_BASIS": len(basis) > 1,
            "placed_range": rng("placed"), "first_seen_range": rng("first_seen"), "settled_range": rng("settled"),
            "game_start_range": rng("game_start"), "multi_row_plays": sum(p["rows"] > 1 for p in plays),
            "mixed_result_plays": sum(p["mixed_results"] for p in plays),
            "possible_split_flagged_NOT_MERGED": sum(v - 1 for v in Counter((p.get("game"), p.get("bet"), p.get("book")) for p in plays).values() if v > 1),
            "units": "UNAVAILABLE (no verified unit schedule)", "time_diag": time_diag(plays)}


def build(rows, index, norm=_norm, links=None, clv=None):
    items, stats, conflicts = classify(rows, index, norm, links)
    return {"join": stats, "lane_conflicts": conflicts,
            "buckets": {b: bucket_report(ps, clv) for b, ps in sorted(consolidate(items).items())}}


CSV_FIELDS = ("bucket", "segment", "book", "plays", "verified_money", "W", "L", "P", "risked", "net", "roi_pct", "first", "last")


# Verified unit schedule: (lane, effective-from UTC, unit in dollars to win). Peter, 15 Nov 2026: "Lane 1 300";
# executor.LIVE_UNIT records the change $200 -> $300 on 9 Nov. A segment gets units ONLY when EXACT-attributed
# to that lane and every play in it is dated on/after the effective time. Other lanes: UNAVAILABLE until confirmed.
UNIT_SCHEDULE = {"PHASE 1": ("2026-11-09T00:00:00+00:00", 300.0)}


def units_for(bucket, seg_range, net):
    lane = bucket.split(":", 1)[1] if bucket.startswith("EXACT:") else None
    if lane not in UNIT_SCHEDULE or not seg_range or not seg_range[0]:
        return None
    since, unit = UNIT_SCHEDULE[lane]
    t0, t1 = utc(seg_range[0]), utc(since)
    return round(net / unit, 2) if t0 and t1 and t0 >= t1 else None


def render(rep):
    """(text, csv_rows) for PRIVATE delivery only. Aggregates per bucket and segment; never a game, bet, ticket or row."""
    L = ["PROJECT 2 - live lane audit (private). Buckets never mix: EXACT = venue order id -> one registry claim;",
         "FUZZY = the tracker's own lane label (UNVERIFIED); UNATTRIBUTED = no provable lane; CONFLICT = tracker vs registry disagree.",
         "Units: Lane 1 (PHASE 1) at 300 to win from 9 Nov, EXACT plays only; other lanes UNAVAILABLE until confirmed. ROI = net / risked on verified-money plays.",
         f"Join: {rep.get('join')} | lane conflicts: {len(rep.get('lane_conflicts') or [])}", ""]
    rows = []
    for b, v in (rep.get("buckets") or {}).items():
        L.append(f"[{b}]  open/ambiguous {v['open_or_ambiguous']}  settled-no-time {v['settled_no_time']}  "
                 f"time basis {v['time_basis_used']}{'  MIXED' if v['MIXED_TIME_BASIS'] else ''}")
        rg = v.get("game_start_range") or v.get("settled_range") or [None, None]
        for seg in ("all", "H1", "H2", "last50"):
            a = v[seg]
            roi = "n/a" if a["roi_pct"] is None else f"{a['roi_pct']:+.2f}%"
            u_ = units_for(b, v.get("settled_range"), a["net"]) if a["verified_money"] else None
            roi += "  units " + ("UNAVAILABLE" if u_ is None else f"{u_:+.2f}u")
            L.append(f"  {seg:<6} plays {a['settled']:>4} verified {a['verified_money']:>4}  W-L-P {a['W']}-{a['L']}-{a['P']}  "
                     f"risked {a['risked']:.2f} net {a['net']:+.2f} ROI {roi}")
            if a.get("clv_n") is not None:
                cm = "n/a" if a["clv_mean_pct"] is None else f"{a['clv_mean_pct']:+.2f}%"
                bp = "n/a" if a["clv_beat_pct"] is None else f"{a['clv_beat_pct']}%"
                L.append(f"         CLV {cm} on {a['clv_n']} certified, beat close {bp}, missing close {a['clv_missing']}")
            rows.append({"bucket": b, "segment": seg, "book": "ALL", "plays": a["settled"], "verified_money": a["verified_money"],
                         "W": a["W"], "L": a["L"], "P": a["P"], "risked": a["risked"], "net": a["net"], "roi_pct": a["roi_pct"],
                         "first": rg[0] if seg == "all" else "", "last": rg[1] if seg == "all" else ""})
            for bk, x in a["by_book"].items():
                rows.append({"bucket": b, "segment": seg, "book": bk, "plays": x["n"], "verified_money": x["n"], "W": "", "L": "",
                             "P": "", "risked": x["risked"], "net": x["net"], "roi_pct": x["roi_pct"], "first": "", "last": ""})
        L.append("  time fields (present / after run / 00:00 UTC): " + ", ".join(
            f"{f_} {d_['present']}/{d_['after_run']}/{d_['midnight_utc']}" for f_, d_ in v["time_diag"].items()))
        L.append(f"  multi-row plays {v['multi_row_plays']}, mixed-result plays {v['mixed_result_plays']}, "
                 f"possible splits flagged (not merged) {v['possible_split_flagged_NOT_MERGED']}")
        L.append("")
    return "\n".join(L), rows


# ------------------------------------------------------------------ venue links (Peter, Nov 14 23:33: "Build it")
# A tracker row with no order_ref can still be tied to registry orders through the VENUE's own records, with no text match:
#   Novig     registry live_order.order_id (our client id) == fill.clientId; the fill carries marketId + outcomeId, which
#             IS the tracker key nv|{marketId}|{outcomeId}  (verified on real fills, clv-link-recon run 43240507919)
#   ProphetX  registry order_id == trade.order_id; the trade's id IS the tracker key px|{trade.id}
# A tracker row is a POSITION on Novig: every fill on it is an order, and the row is EXACT only if EVERY order resolves to
# a registry claim and they are all ONE lane. Money is never split across lanes; anything else fails closed.
PX_TRADES_CAP = 100   # every recorded GET /v4/mm/get_trades returned exactly 100 rows (px_fee_check, positions, link recon):
                      # treated as a CAP. No paging parameter is documented or used anywhere in the repo.


def px_trades_complete(trades, data_keys=()):
    """False when the ProphetX read may be truncated: it hit the observed 100-row cap, or the response carries any
    paging marker. A partial trade set must never produce EXACT (a missing trade could hide a second lane)."""
    marker = {k.lower() for k in data_keys} & {"next", "cursor", "next_cursor", "has_more", "page", "offset", "pagination"}
    return len(trades or []) < PX_TRADES_CAP and not marker


def link_index(fills, trades, complete=None):
    """{tracker id: [frozenset(order ids of one fill / trade), ...]} from venue fill and trade rows. Pure.
    complete = {"nv": bool, "px": bool}: a venue whose read may be truncated contributes NO link; its rows are marked
    in out["_incomplete"] so resolve_link reports link_source_incomplete instead of a wrong EXACT."""
    complete = {"nv": True, "px": True, **(complete or {})}
    out = {"_incomplete": {v for v, ok in complete.items() if not ok}}
    if not complete["nv"]:
        fills = []
    if not complete["px"]:
        trades = []
    for f in fills or []:
        f = f if isinstance(f, dict) else {}
        mk, oc = f.get("marketId"), f.get("outcomeId")
        ids = frozenset(str(x) for x in (f.get("clientId"), f.get("orderId")) if x not in (None, ""))
        if mk and oc and ids:
            out.setdefault(f"nv|{mk}|{oc}", []).append(ids)
    for t in trades or []:
        t = t if isinstance(t, dict) else {}
        if t.get("id") not in (None, "") and t.get("order_id") not in (None, ""):
            out.setdefault(f"px|{t['id']}", []).append(frozenset([str(t["order_id"])]))
    return out


def resolve_link(row, links, index, norm=_norm):
    """-> (status, lane, key). status: exact_link | no_venue_link | link_source_incomplete | link_order_not_in_registry |
    link_order_ambiguous | link_position_multi_lane | venue_unmatched"""
    rid = str(row.get("id") or "")
    if rid.split("|", 1)[0] in (links or {}).get("_incomplete", set()):
        return "link_source_incomplete", None, None
    orders = (links or {}).get(rid)
    if not orders:
        return "no_venue_link", None, None
    ven = norm(row.get("book"))
    if not ven:
        return "venue_unmatched", None, None
    lanes, keys = set(), set()
    for ids in set(orders):
        claims = {(k, ln) for i in ids for v, k, ln in index.get(i, []) if v and norm(v) == ven}
        if not claims:
            return "link_order_not_in_registry", None, None
        ls = {canon_lane(ln) for _k, ln in claims}
        if len(ls) != 1 or None in ls:
            return "link_order_ambiguous", None, None
        lanes |= ls
        keys |= {k for k, _ln in claims}
    if len(lanes) != 1:
        return "link_position_multi_lane", None, None
    return "exact_link", next(iter(lanes)), "|".join(sorted(keys))
