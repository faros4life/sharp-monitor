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


def classify(rows, index, norm=_norm, links=None, ruled=None):
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
            elif ls == "link_source_incomplete":
                # Nov 17 (Peter): the venue read failed, so the link was not CHECKED - a different state from a row
                # that has no order reference, with the opposite remedy. Never promoted; just named correctly.
                status = "venue_read_unavailable"
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
        if ruled is not None:
            rl, why = ruled_lane(r, ruled[0], ruled[1])
            if why:
                st["ruled:" + why] += 1
                items.append((r, "UNATTRIBUTED(" + why + ")", None))
                continue
            if rl:
                st["ruled"] += 1
                if r.get("lane") and canon_lane(r["lane"]) != rl:
                    st["ruled_vs_tracker_text_disagree"] += 1
                items.append((r, "RULED:" + rl, None))
                continue
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
            "units": "UNAVAILABLE (no verified unit schedule)", "time_diag": time_diag(plays),
            "_settled_timed": timed}   # PRIVATE: per-play rows for the scorecard (Telegram only, never printed)


def build(rows, index, norm=_norm, links=None, clv=None, ruled=None):
    """ruled = (bot_live_export.TRIGGERS, tracker_build.toks) or None."""
    items, stats, conflicts = classify(rows, index, norm, links, ruled)
    groups = consolidate(items)
    # Exactly-once: every bot row must sit in exactly one play in exactly one bucket (partial fills merge into
    # their play, never into a second one). A failure here means the recap double- or under-counts.
    ids = [i for ps in groups.values() for p in ps for i in p.get("ids") or []]
    once = {"rows": len(rows), "rows_in_plays": len(ids), "distinct": len(set(ids)),
            "ok": len(ids) == len(set(ids)) == len(rows)}
    return {"join": stats, "lane_conflicts": conflicts, "exactly_once": once,
            "row_bucket": {str(r.get("id") or ""): b for r, b, _k in items},
            "buckets": {b: bucket_report(ps, clv) for b, ps in sorted(groups.items())}}


CSV_FIELDS = ("bucket", "segment", "book", "plays", "verified_money", "W", "L", "P", "risked", "net", "roi_pct", "first", "last")


# Verified unit schedule: (lane, effective-from UTC, unit in dollars to win). Peter, 15 Nov 2026: "Lane 1 300";
# executor.LIVE_UNIT records the change $200 -> $300 on 9 Nov. A segment gets units ONLY when EXACT-attributed
# to that lane and every play in it is dated on/after the effective time. Other lanes: UNAVAILABLE until confirmed.
# R1 and BOARD V3: executor.R1_UNIT / BOARD_UNIT, both "Peter, 11 Nov" written approvals, unchanged since.
UNIT_SCHEDULE = {"PHASE 1": ("2026-11-09T00:00:00+00:00", 300.0),
                 "R1": ("2026-11-11T00:00:00+00:00", 200.0),
                 "BOARD V3": ("2026-11-11T00:00:00+00:00", 200.0)}


def units_for(bucket, seg_range, net):
    lane = bucket.split(":", 1)[1] if bucket.startswith("EXACT:") else None
    if lane not in UNIT_SCHEDULE or not seg_range or not seg_range[0]:
        return None
    since, unit = UNIT_SCHEDULE[lane]
    t0, t1 = utc(seg_range[0]), utc(since)
    return round(net / unit, 2) if t0 and t1 and t0 >= t1 else None


def render(rep):
    """(text, csv_rows) for PRIVATE delivery only. Aggregates per bucket and segment; never a game, bet, ticket or row."""
    L = ["PROJECT 2 - live lane audit (private). Buckets never mix: EXACT (VERIFIED) = venue order id or venue fill/trade link -> one",
         "registry claim; RULED = Peter's 13 Nov game-level lane table (Oct 31 - Nov 12), never EXACT; FUZZY = tracker text label (UNVERIFIED);",
         "UNATTRIBUTED = no provable lane; CONFLICT = tracker vs registry disagree.",
         "Units (EXACT plays only, dated on/after the unit's start): Lane 1 300 from 9 Nov; R1 200 and Board V3 200 from 11 Nov. ROI = net / risked.",
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


# ------------------------------------------------------------------ Peter, 16 Nov 04:43 "USE BOTH"
RULED_LANE = {"lane 1": "PHASE 1", "r1": "R1", "bets board v3": "BOARD V3", "board v3": "BOARD V3", "board": "BOARD V3"}
RULED_FROM, RULED_TO = "2026-10-31", "2026-11-12"       # Peter: RULED recovers Oct 31 - Nov 12 only


def ruled_lane(row, triggers, toks):
    """The lane Peter RULED for this row's game (bot_live_export.TRIGGERS: his 13 Nov recap table), by the SAME rule the
    Last-50 panel uses (bot_live_export.trigger_plays): game date within +-1 day of the ruled MM-DD, and a word of each
    ruled team in the row's game text. -> (lane, None) | (None, 'ruled_multi_lane') | (None, None).
    Game-level evidence: a RULED lane is never EXACT."""
    from datetime import datetime as _d, timedelta as _td
    day = str(row.get("game_start") or row.get("settled") or row.get("first_seen") or "")[:10]
    gt = toks(row.get("game") or "")
    hits = set()
    for lane, games in (triggers or {}).items():
        for md, a, b in games:
            d0 = _d.strptime("2026-" + md, "%Y-%m-%d")
            if not (RULED_FROM <= d0.strftime("%Y-%m-%d") <= RULED_TO):
                continue
            days = {(d0 + _td(days=x)).strftime("%Y-%m-%d") for x in (-1, 0, 1)}
            A, B = (a if isinstance(a, (set, frozenset)) else {a}), (b if isinstance(b, (set, frozenset)) else {b})
            if day in days and (A & gt) and (B & gt):
                hits.add(RULED_LANE.get(str(lane).strip().lower(), str(lane).upper()))
    if len(hits) > 1:
        return None, "ruled_multi_lane"
    return (next(iter(hits)), None) if hits else (None, None)


def index_from_sources(sources, row_lane, venue):
    """Claims index built from several order sources, DEDUPLICATED BY IMMUTABLE ID: {order or client id: [(venue, key, lane)]}
    plus per-id provenance. sources = [(name, rows)]. A claim is (venue, key, lane); the same claim seen in two sources is ONE
    claim. Two DIFFERENT claims on one id across sources are kept both, so resolve() reports them ambiguous (never picks).
    -> (index, stats). stats counts ids by source overlap and cross-source conflicts; never an identifier."""
    d = lambda x: x if isinstance(x, dict) else {}
    claims, seen_in, no_lane = {}, {}, 0
    for name, rows in sources:
        for row in rows or []:
            key = row.get("key")
            more = row.get("live_more")
            los = [d(row.get("live_order")), d(row.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]
            placed = [lo for lo in los if lo.get("status") == "placed" and lo.get("order_id") and not lo.get("intent")
                      and not lo.get("voided") and not str(lo.get("order_id")).startswith("intent-")]
            if not key or not placed:
                continue
            lane = row_lane(row)
            if not lane:
                no_lane += 1
                continue
            for lo in placed:
                for fld in ("order_id", "client_id"):
                    i = str(lo.get(fld) or "")
                    if not i or i.startswith("intent-"):
                        continue
                    c = (venue(lo.get("book") or row.get("fill_book")), str(key), lane)
                    claims.setdefault(i, set()).add(c)
                    seen_in.setdefault(i, set()).add(name)
    names = [n for n, _r in sources]
    st = Counter()
    for i, src in seen_in.items():
        st["ids_in_" + "+".join(n for n in names if n in src)] += 1
        if len(src) > 1 and len({(v, canon_lane(ln)) for v, _k, ln in claims[i]}) > 1:
            st["ids_cross_source_conflict"] += 1
    st["rows_no_provable_lane"] = no_lane
    return {i: sorted(c) for i, c in claims.items()}, dict(st)


def fills_without_tracker_row(links, index, row_ids):
    """Count venue positions (Novig nv|.. / ProphetX px|..) whose fills belong to OUR registry orders but which have NO tracker
    row at all - a bot fill the tracker never recorded. Counts only."""
    out = Counter()
    for tid, orders in (links or {}).items():
        if tid == "_incomplete" or tid in row_ids:
            continue
        if any(i in (index or {}) for ids in orders for i in ids):
            out[tid.split("|", 1)[0]] += 1
    return dict(out)


# ---- ProphetX per-order matching detail (Peter, 16 Nov: resolve the 100-row get_trades cap) -----------------------------
# ProphetX reference: /v2/mm/get_wager_matching_detail "supports filtering by wager_ids and time range (from/to) with
# cursor pagination" (next_cursor; limit max 100). A wager is an order. READ-ONLY.
PX_ID_KEYS = ("wager_id", "order_id", "id_wager", "bet_id")
PX_QTY_KEYS = ("matched_stake", "matched_quantity", "stake", "quantity", "matched_amount", "filled_quantity")


def px_match_records(resp):
    """Every dict anywhere in a response that carries a wager/order id. Pure."""
    out, stack = [], [resp]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            if any(x.get(k) not in (None, "") for k in PX_ID_KEYS):
                out.append(x)
            stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
        elif isinstance(x, list):
            stack.extend(x)
    return out


def px_next_cursor(resp):
    stack = [resp]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            for k in ("next_cursor", "nextCursor"):
                if k in x:
                    return x[k] or None
            stack.extend(v for v in x.values() if isinstance(v, dict))
    return None


def px_matched_ids(records):
    """Order ids with a matched (filled) amount. A record whose every quantity field is zero is NOT a fill;
    a record with no quantity field is a matching-detail row, which the endpoint returns only for matches."""
    ids = set()
    for r in records:
        q = [r.get(k) for k in PX_QTY_KEYS if r.get(k) not in (None, "")]
        try:
            filled = (not q) or any(float(v) > 0 for v in q)
        except (TypeError, ValueError):
            filled = True
        if filled:
            ids.update(str(r.get(k)) for k in PX_ID_KEYS if r.get(k) not in (None, ""))
    return ids


def px_classify(order_ids, matched, complete):
    """FILLED when the venue shows a match; UNFILLED only when the paged read is provably complete; else UNKNOWN."""
    if any(str(i) in matched for i in order_ids):
        return "FILLED"
    return "UNFILLED" if complete else "UNKNOWN"


def px_has_cursor_field(resp):
    stack = [resp]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            if "next_cursor" in x or "nextCursor" in x:
                return True
            stack.extend(v for v in x.values() if isinstance(v, dict))
    return False


def text_label_yields(row, registry_lane, other_lanes_same_event):
    """16 Nov (Peter): 'Tracker labels alone cannot override a verified registry claim.' True when a CONFLICT is only
    the tracker's own TEXT label disagreeing: the registry claim is exact (caller), the label was not registry-derived,
    and no registry order exists for the same event under the label's lane. Anything else stays CONFLICT. Pure."""
    if str(row.get("lane_src") or "") == "registry-order-id":
        return False
    seen = {canon_lane(row.get(f)) for f in ("lane", "lane_fuzzy")} - {None}
    reg = canon_lane(registry_lane)
    if not reg or not seen or seen == {reg}:
        return False
    return not (seen - {reg}) & {canon_lane(x) for x in (other_lanes_same_event or [])}
