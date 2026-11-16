"""Daily report sections B (Project 1) and D (data integrity). Pure functions, counts only.

Inputs are plain dicts already decrypted by the caller. Nothing here reads a network, a venue or an
executor module, and nothing writes.
"""
from datetime import datetime, timezone, timedelta

START_ET = "2026-11-12"
ET = timezone(timedelta(hours=-5))
# Project 1 counts "the first 20 NEW graded fills" after the Phase 1 forward-capture merge. The
# first-seen stamp (ingest_checked) is written only by that code, first committed in d646659 at this
# time; a stamp cannot predate it, so the floor is conservative rather than tuned.
P1_BASELINE_UTC = "2026-11-14T17:57:29Z"
SETTLED = ("W", "L", "P")


def _t(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None


def _et_day(x):
    t = _t(x)
    return t.astimezone(ET).strftime("%Y-%m-%d") if t else None


def merge_orders(registry_rows, ledger_rows):
    """Registry rows plus ledger-preserved rows the registry has pruned. Identity = (key, decided_utc
    or et_day). Registry rows win on a tie: they are the live copy."""
    seen = {(r.get("key"), r.get("decided_utc") or r.get("et_day")) for r in registry_rows or []}
    extra = [r for r in ledger_rows or [] if (r.get("key"), r.get("decided_utc") or r.get("et_day")) not in seen]
    return list(registry_rows or []) + extra, len(extra)


def _event_time(b):
    """When the BET happened: placed, else game start, else settlement. Never the discovery stamp."""
    for k in ("placed", "game_start", "settled"):
        t = _t(b.get(k)) if b.get(k) else None
        if t:
            return t
    return None


def project1(bot_rows, clv, baseline_utc=P1_BASELINE_UTC):
    """Bot rows first observed (ingest_checked, a never-overwritten stamp) on/after 12 Nov ET AND whose bet itself
    happened then. 16 Nov: paging the tracker's ProphetX read discovered ~260 OLD trades in one run; their first-seen
    stamp is today, but they are history and must never count as new fills."""
    start = _t(START_ET + "T05:00:00+00:00")
    fresh = [b for b in bot_rows if (_et_day(b.get("ingest_checked")) or "") >= START_ET
             and _event_time(b) is not None and _event_time(b) >= start]
    graded = [b for b in fresh if b.get("result") in SETTLED]
    with_clv = [b for b in graded if clv.get(str(b.get("id"))) is not None]
    vals = [clv[str(b.get("id"))] for b in with_clv]
    out = {"first_seen_since_start": len(fresh), "graded": len(graded), "pending": len(fresh) - len(graded),
           "missing_close": len(graded) - len(with_clv),
           "clv_pos": sum(v > 0 for v in vals), "clv_neg": sum(v < 0 for v in vals),
           "clv_mean_pct": round(100 * sum(vals) / len(vals), 2) if vals else None}
    if baseline_utc is None:
        out["qualifying"] = None
        out["qualifying_why"] = "acceptance baseline timestamp NOT CONFIRMED - qualifying count withheld"
    else:
        b0 = _t(baseline_utc)
        q = [b for b in graded if _t(b.get("ingest_checked")) and _t(b.get("ingest_checked")) >= b0
             and _event_time(b) >= b0]
        out["qualifying"] = len(q)
    if len(vals) >= 2:
        order = sorted(with_clv, key=lambda b: str(b.get("settled") or ""))
        h = len(order) // 2
        hv = lambda xs: round(100 * sum(clv[str(b.get("id"))] for b in xs) / len(xs), 2) if xs else None
        out["h1_clv_pct"], out["h2_clv_pct"] = hv(order[:h]), hv(order[h:])
        out["halves_note"] = "PRELIMINARY" if len(vals) < 20 else ""
    return out


def integrity(orders, fills, bot_rows, clv, rep, px_complete, now=None):
    now = now or datetime.now(timezone.utc)
    d = lambda x: x if isinstance(x, dict) else {}
    placed_ids, placed_missing, by_id, by_key = 0, 0, 0, 0
    # Two proven joins, counted separately: fill record id == order/client id, or the fill's play_key ==
    # the order key with or without its lane prefix (the venue runner writes play_key unprefixed).
    pk = {str(f.get("play_key")) for f in fills.values() if f.get("play_key")}
    for o in orders:
        day = o.get("et_day") or _et_day(o.get("decided_utc")) or ""
        if day < START_ET:
            continue
        more = o.get("live_more")
        for lo in [d(o.get("live_order")), d(o.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]:
            if lo.get("status") == "placed" and (lo.get("order_id") or lo.get("client_id")):
                placed_ids += 1
                key = str(o.get("key") or "")
                if any(str(lo.get(k)) in fills for k in ("order_id", "client_id") if lo.get(k)):
                    by_id += 1
                elif key in pk or key.split("|", 1)[-1] in pk:
                    by_key += 1
                else:
                    placed_missing += 1
    nonterm = sum(1 for f in fills.values() if f.get("state") in ("PLACED", "RESTING"))
    since = [b for b in bot_rows if (_et_day(b.get("settled")) or "") >= START_ET or not b.get("settled")]
    settled = [b for b in since if b.get("result") in SETTLED]
    join = (rep or {}).get("join") or {}
    buckets = (rep or {}).get("buckets") or {}
    not_exact = sum(v["all"]["settled"] + v["open_or_ambiguous"] for b, v in buckets.items() if not b.startswith("EXACT"))
    last_src = max([str(b.get("settled") or "") for b in bot_rows] + [str(b.get("ingest_checked") or "") for b in bot_rows] or [""])
    return {"placed_orders_since_start": placed_ids, "fill_record_by_id": by_id, "fill_record_by_play_key": by_key,
            "placed_orders_without_fill_record": placed_missing,
            "fill_records_not_terminal": nonterm,
            "bot_rows_since_start": len(since), "settled_missing_certified_clv": sum(1 for b in settled if clv.get(str(b.get("id"))) is None),
            "open_bot_rows": sum(1 for b in since if b.get("result") not in SETTLED),
            "positions_without_exact_lane": not_exact, "lane_conflicts": len((rep or {}).get("lane_conflicts") or []),
            "prophetx_read_complete": bool(px_complete), "join_stats": join,
            "refreshed_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "latest_source_time": last_src or None}


def render(p1, integ, ledger_extra):
    L = ["", "SECTION B - PROJECT 1 (20-new-fill validation)"]
    q = p1["qualifying"]
    L.append(f"  new qualifying fills: {'WITHHELD' if q is None else q} / 20" + (f"  ({p1['qualifying_why']})" if q is None else ""))
    L.append(f"  first seen since 12 Nov ET {p1['first_seen_since_start']} | graded {p1['graded']} | pending {p1['pending']} | "
             f"missing close {p1['missing_close']}")
    cm = "n/a" if p1["clv_mean_pct"] is None else f"{p1['clv_mean_pct']:+.2f}%"
    n = p1["clv_pos"] + p1["clv_neg"]
    L.append(f"  CLV mean {cm} | positive {p1['clv_pos']}" + (f" ({100*p1['clv_pos']/n:.0f}%)" if n else "") +
             f" | negative {p1['clv_neg']}")
    if "h1_clv_pct" in p1:
        L.append(f"  H1 CLV {p1['h1_clv_pct']:+.2f}% | H2 CLV {p1['h2_clv_pct']:+.2f}% {p1['halves_note']}")
    L += ["", "SECTION D - DATA INTEGRITY"]
    for k, v in integ.items():
        L.append(f"  {k}: {v}")
    L.append(f"  orders restored from the durable ledger (pruned from the registry): {ledger_extra}")
    return "\n".join(L)


def day_selections(day, orders, fills, bot_rows, clv, row_bucket):
    """PRIVATE ONLY: every bot order decided on ET `day` and every bot position whose game starts that day.
    Lets Peter tick off his own list: anything he bet that is absent here was not placed by the bot."""
    d = lambda x: x if isinstance(x, dict) else {}
    pk = {str(f.get("play_key")): f for f in fills.values() if f.get("play_key")}
    out_o = []
    for o in orders:
        if (o.get("et_day") or _et_day(o.get("decided_utc"))) != day:
            continue
        key = str(o.get("key") or "")
        lo = d(o.get("live_order"))
        f = fills.get(str(lo.get("order_id"))) or fills.get(str(lo.get("client_id"))) or pk.get(key) or pk.get(key.split("|", 1)[-1]) or {}
        out_o.append({"key": key, "lane_src": o.get("source"), "order_status": lo.get("status"),
                      "venue": lo.get("book") or o.get("fill_book"), "fill_state": f.get("state") or "NO FILL RECORD"})
    out_p = []
    for b in bot_rows:
        if _et_day(b.get("game_start")) != day:
            continue
        i = str(b.get("id") or "")
        out_p.append({"game": b.get("game"), "bet": b.get("bet"), "book": b.get("book"),
                      "bucket": row_bucket.get(i, "?"), "result": b.get("result") or "OPEN",
                      "net": b.get("profit"), "clv": ("MISSING" if clv.get(i) is None else f"{100 * clv[i]:+.2f}%")})
    return out_o, out_p


def render_day(day, out_o, out_p, once):
    L = ["", f"SECTION E - BOT SELECTIONS FOR {day} (private; anything you bet that is not here was not a bot bet)",
         f"  exactly-once check: {'OK' if once.get('ok') else 'FAILED'} ({once.get('rows')} bot rows, "
         f"{once.get('rows_in_plays')} in plays, {once.get('distinct')} distinct)"]
    L.append(f"  bot orders decided that day: {len(out_o)}")
    for o in out_o:
        L.append(f"   - {o['key']} | lane {o['lane_src']} | {o['venue']} | order {o['order_status']} | fill {o['fill_state']}")
    L.append(f"  bot positions with a game that day: {len(out_p)}")
    for p in out_p:
        net = "" if p["net"] is None else f" | net {p['net']:+.2f}"
        L.append(f"   - {p['game']} | {p['bet']} | {p['book']} | {p['bucket']} | {p['result']}{net} | CLV {p['clv']}")
    return "\n".join(L)


def fill_exceptions(orders, fills, venue_order_ids, px_complete, px_evidence=None, tracked_ids=None):
    """Every placed order since START_ET with no registry fill record, classified by VENUE evidence.
    venue_order_ids: every order/client id seen in the venues' own fill and trade reads."""
    d = lambda x: x if isinstance(x, dict) else {}
    pk = {str(f.get("play_key")) for f in fills.values() if f.get("play_key")}
    out = []
    for o in orders:
        day = o.get("et_day") or _et_day(o.get("decided_utc")) or ""
        if day < START_ET:
            continue
        key = str(o.get("key") or "")
        more = o.get("live_more")
        for lo in [d(o.get("live_order")), d(o.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]:
            ids = [str(lo.get(k)) for k in ("order_id", "client_id") if lo.get(k)]
            if lo.get("status") != "placed" or not ids:
                continue
            if any(i in fills for i in ids) or key in pk or key.split("|", 1)[-1] in pk:
                continue
            venue = str(lo.get("book") or o.get("fill_book") or "?").lower()
            if any(i in venue_order_ids for i in ids):
                cat = "VENUE SHOWS A FILL - registry fill record missing (record gap, position is real)"
            elif "prophet" in venue and px_evidence is not None:
                from p2_audit_core import px_classify
                v = px_classify(ids, px_evidence.get("matched") or set(), bool(px_evidence.get("complete")))
                cat = {"FILLED": "FILLED - ProphetX matching detail shows a match (registry fill record missing)",
                       "UNFILLED": "UNFILLED - ProphetX matching detail, paged to the end, shows no match",
                       "UNKNOWN": "UNKNOWN - ProphetX matching detail incomplete or unreadable"}[v]
            elif "prophet" in venue and not px_complete:
                cat = "UNKNOWN - ProphetX trade read capped at 100, cannot prove fill or no fill"
            elif "novig" in venue or "prophet" in venue:
                cat = "NO FILL AT VENUE - complete venue read shows none (unfilled; not a position)"
            elif any(i in (tracked_ids or set()) for i in ids):
                cat = f"FILLED - a {venue} venue position row is linked to this order (Project 2)"
            else:
                cat = f"UNKNOWN - no venue read for {venue}"
            tr = None
            if cat.startswith(("FILLED", "VENUE SHOWS")):
                tr = any(i in (tracked_ids or set()) for i in ids)
            out.append({"day": day, "key": key, "venue": venue, "category": cat, "ids": ids,
                        "in_project2": tr})
    return out


def clv_exceptions(bot_rows, clv_rows, certified, stale_ids):
    """Every settled bot row since START_ET without a certified CLV, with the ledger's own reason."""
    out = []
    for b in bot_rows:
        i = str(b.get("id") or "")
        if b.get("result") not in SETTLED or (_et_day(b.get("game_start") or b.get("settled")) or "") < START_ET:
            continue
        if certified.get(i) is not None:
            continue
        r = clv_rows.get(i)
        if r is None:
            cat = "NOT IN CLV LEDGER - never scored (ingest gap)"
        elif i in stale_ids:
            cat = "EXCLUDED AS STALE - ledger row superseded/stale"
        elif r.get("fixture_doubt"):
            cat = "FIXTURE DOUBT - Pinnacle fixture match not certain"
        elif r.get("clv") is None and not r.get("done"):
            cat = f"PENDING - not yet scored (tries {r.get('tries') or 0}); {str(r.get('why') or 'no reason recorded')[:60]}"
        else:
            cat = f"UNRECOVERABLE - {str(r.get('why') or 'no reason recorded')[:60]}"
        out.append({"game": b.get("game"), "bet": b.get("bet"), "book": b.get("book"), "category": cat})
    return out


def render_exceptions(fx, cx):
    L = ["", f"SECTION G - RECONCILIATION OF EXCEPTIONS (from {START_ET} ET)",
         f"  placed orders with no registry fill record: {len(fx)}"]
    for e in fx:
        t_ = "" if e.get("in_project2") is None else (" | in Project 2: yes" if e["in_project2"] else " | in Project 2: NO - missing position")
        L.append(f"   - {e['day']} | {e['key']} | {e['venue']} | {e['category']}{t_}")
    L.append(f"  settled bot bets without certified CLV: {len(cx)} (never counted as zero)")
    for e in cx:
        L.append(f"   - {e['game']} | {e['bet']} | {e['book']} | {e['category']}")
    return "\n".join(L)


def category_counts(xs):
    c = {}
    for e in xs:
        k = e["category"].split(" - ")[0]
        c[k] = c.get(k, 0) + 1
    return c


# ---------------------------------------------------------------- SECTION H: final lane scorecard (Peter, 16 Nov)
CHANGE_UTC = "2026-11-11T16:31:19+00:00"     # the approved pricing-model change, 11 Nov 11:31:19 AM ET
LANES_LIVE = ("PHASE 1", "R1", "BOARD V3")


def _ci(vals):
    """95% normal interval for a mean, or None below 5 observations (not meaningful)."""
    n = len(vals)
    if n < 5:
        return None
    m = sum(vals) / n
    sd = (sum((v - m) ** 2 for v in vals) / (n - 1)) ** 0.5
    h = 1.96 * sd / n ** 0.5
    return [round(m - h, 2), round(m + h, 2)]


def seg_stats(plays, clv, unit, unit_since):
    """One segment: W-L-P, net, risked, ROI, units (only if every play is on/after the unit's start), certified CLV,
    beat-close %, coverage, and 95% intervals for CLV and units. Missing closes are excluded, never zero."""
    from p2_audit_core import verified_money, utc
    ok = [p for p in plays if verified_money(p)]
    net, risked = sum(p["profit"] for p in ok), sum(p["stake"] for p in ok)
    t0 = utc(unit_since) if unit_since else None
    def _when(p):
        return utc(p.get("game_start") or "") or utc(p.get("settled") or "")
    dated = bool(ok) and t0 is not None and all(_when(p) is not None and _when(p) >= t0 for p in ok)
    units_each = [p["profit"] / unit for p in ok] if (unit and dated) else None
    cv = []
    for p in plays:
        v = [clv.get(i) for i in p.get("ids") or []]
        if v and None not in v:
            cv.append(100 * sum(v) / len(v))
    return {"n": len(plays), "W": sum(p["result"] == "W" for p in plays), "L": sum(p["result"] == "L" for p in plays),
            "P": sum(p["result"] == "P" for p in plays), "net": round(net, 2), "risked": round(risked, 2),
            "roi": round(100 * net / risked, 2) if risked else None,
            "units": round(sum(units_each), 2) if units_each is not None else None,
            "units_ci": _ci(units_each) if units_each is not None else None,
            "clv": round(sum(cv) / len(cv), 2) if cv else None, "clv_n": len(cv), "clv_missing": len(plays) - len(cv),
            "beat": round(100 * sum(v > 0 for v in cv) / len(cv), 1) if cv else None, "clv_ci": _ci(cv)}


def lane_scope(rep, lane, clv, unit_sched):
    b = (rep.get("buckets") or {}).get("EXACT:" + lane)
    unit, since = (unit_sched.get(lane) or (None, None))[1], (unit_sched.get(lane) or (None, None))[0]
    if not b:
        return None
    plays = b.get("_settled_timed") or []
    h = len(plays) // 2
    w, h1, h2 = (seg_stats(x, clv, unit, since) for x in (plays, plays[:h], plays[h:]))
    from clv_dashboard import gate
    g = gate(lane, {"clv": h1["clv"], "units": h1["units"]}, {"clv": h2["clv"], "units": h2["units"]},
             {"n": w["clv_n"], "clv": w["clv"], "ci": w["clv_ci"], "pos": round((w["beat"] or 0) * w["clv_n"] / 100)}, True)
    return {"whole": w, "H1": h1, "H2": h2, "open": b.get("open_or_ambiguous", 0), "verdict": g["verdict"],
            "clauses": g.get("clauses") or []}


def render_scorecard(scopes, non_exact, unit_sched):
    def f(x, d=2, suf=""):
        return "n/a" if x is None else f"{x:+.{d}f}{suf}"
    L = ["", "SECTION H - LANE SCORECARD (EXACT attribution only; missing closes excluded, never zero)",
         "  Units: Lane 1 300 from 9 Nov; R1 and Board V3 200 from 11 Nov. 95% intervals shown only at n >= 5.",
         "  Qualification = the registered SCORECARD.md gate (clv_dashboard.gate), unchanged."]
    for scope, by in scopes:
        L.append(f"  -- {scope}")
        for lane in LANES_LIVE:
            x = by.get(lane)
            if not x:
                L.append(f"   {lane}: no settled EXACT plays")
                continue
            for seg in ("whole", "H1", "H2"):
                s_ = x[seg]
                L.append(f"   {lane:<8} {seg:<5} n {s_['n']:>2} W-L-P {s_['W']}-{s_['L']}-{s_['P']} net {s_['net']:+.2f} "
                         f"units {f(s_['units'], suf='u')}{'' if not s_['units_ci'] else ' CI ' + str(s_['units_ci'])} "
                         f"ROI {f(s_['roi'], suf='%')} | CLV {f(s_['clv'], suf='%')}"
                         f"{'' if not s_['clv_ci'] else ' CI ' + str(s_['clv_ci'])} on {s_['clv_n']} (missing {s_['clv_missing']}) "
                         f"beat {('n/a' if s_['beat'] is None else str(s_['beat']) + '%')}")
            L.append(f"   {lane:<8} open {x['open']} | QUALIFICATION: {x['verdict']}")
            for c in x["clauses"]:
                if c["state"] != "MET":
                    L.append(f"            - {c['clause']}: {c['state']} {c.get('detail', '')}")
    L.append(f"  Kept separate (not in any lane above): {non_exact}")
    return "\n".join(L)
