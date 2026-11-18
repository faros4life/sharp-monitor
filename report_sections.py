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


# ---------------------------------------------------------------- SECTION K: paper Board -> live executor (Nov 17)
def _board_side(side_text):
    t = str(side_text or "").strip().lower()
    if t.startswith("over"):
        return "OVER"
    if t.startswith("not over") or t.startswith("under"):
        return "UNDER"
    return None


def _live_position(c, live_rows):
    """The venue-confirmed live Board V3 position for a paper call: same ET game day, both team tokens of the paper
    game present in the live row's game text, same OVER/UNDER. Exactly one match or None (never guessed)."""
    import tracker_build as _tb
    sd = _board_side(c.get("side"))
    gt = str(c.get("game") or "").split(":")[0]
    teams = [_tb.toks(x) - _tb.WEAK for x in gt.split(" vs ")]
    if len(teams) != 2 or not all(teams) or not sd:
        return None
    hits = []
    for b in live_rows or []:
        if _et_day(b.get("game_start")) != c.get("day") and _et_day(b.get("settled")) != c.get("day"):
            continue
        bt = str(b.get("bet") or "").strip().lower()
        bsd = "OVER" if bt.startswith("over") else ("UNDER" if bt.startswith("under") else None)
        g = _tb.toks(b.get("game")) - _tb.WEAK
        if bsd == sd and all(t & g for t in teams):
            hits.append(b)
    return hits[0] if len(hits) == 1 else None


def paper_live_trace(calls, orders, fills, start_et=START_ET, live_rows=None):
    """PRIVATE ONLY. Every paper Bets Board PLAY call from start_et traced to the live executor's own record of it.
    Join is the board play key the executor writes (board|<league>|<game>|<market>|<OVER/UNDER>) - exact, never
    fuzzy. Category per call: NOT DECIDED (no executor record) | DECIDED, NOT PLACED (reason) | PLACED, NO FILL
    (fill state) | FILLED. Also lists filled live board orders that were not paper PLAY calls. Pure."""
    d = lambda x: x if isinstance(x, dict) else {}
    pk = {str(f.get("play_key")): f for f in (fills or {}).values() if f.get("play_key")}
    by_key = {}
    for o in orders or []:
        by_key.setdefault(str(o.get("key") or ""), []).append(o)
    out, seen = [], set()
    for k, c in sorted((calls or {}).items(), key=lambda kv: str(kv[1].get("at") or "")):
        if c.get("call") != "PLAY" or str(c.get("day") or "") < start_et:
            continue
        sd = _board_side(c.get("side"))
        key = f"board|{c.get('league')}|{c.get('game')}|{c.get('mk')}|{sd}"
        seen.add(key)
        os_ = by_key.get(key) or []
        row = {"day": c.get("day"), "game": c.get("game"), "side": c.get("side"), "paper_price": c.get("price"),
               "paper_book": c.get("book"), "result": c.get("result") or "UNGRADED", "units": c.get("units"), "key": key}
        lp = _live_position(c, live_rows)
        if lp is not None:
            # Venue evidence wins: a confirmed live Board V3 position is FILLED whatever the registry fill record says
            # (several venue fills carry no registry fill record - Section G).
            row["cat"] = "FILLED"
            row["detail"] = f"venue-confirmed live position, {lp.get('book')} live price {lp.get('price')} vs paper {c.get('price')}, live result {lp.get('result') or 'OPEN'}"
        elif not os_:
            row["cat"], row["detail"] = "NOT DECIDED", "no executor record for this play key"
        if lp is None and os_:
            o = os_[-1]
            lo = d(o.get("live_order"))
            f = fills.get(str(lo.get("order_id"))) or fills.get(str(lo.get("client_id"))) or pk.get(key) \
                or pk.get(key.split("|", 1)[-1]) or {}
            st = f.get("state")
            if lo.get("status") != "placed":
                row["cat"] = "DECIDED, NOT PLACED"
                row["detail"] = " | ".join(str(x)[:60] for x in (o.get("verdict"), o.get("live_why_not") or lo.get("reason") or o.get("reason")) if x)
            elif st in ("FILLED", "PARTIAL"):
                row["cat"] = "FILLED"
                row["detail"] = (f"{lo.get('book') or o.get('fill_book')} live after-fee {o.get('live_px_price_after_fee')} "
                                 f"line {o.get('live_px_line')} vs paper {c.get('price')} line {c.get('line')}")
            else:
                row["cat"], row["detail"] = "PLACED, NO FILL", f"fill state {st or 'NO FILL RECORD'}"
        out.append(row)
    extra = []
    for key, os_ in by_key.items():
        if not key.startswith("board|") or key in seen:
            continue
        o = os_[-1]
        lo = d(o.get("live_order"))
        if (o.get("et_day") or _et_day(o.get("decided_utc")) or "") < start_et or lo.get("status") != "placed":
            continue
        extra.append({"key": key, "day": o.get("et_day") or _et_day(o.get("decided_utc")), "venue": lo.get("book")})
    summ = {}
    for r in out:
        x = summ.setdefault(r["cat"], {"n": 0, "W": 0, "L": 0, "P": 0, "UNGRADED": 0, "units": 0.0})
        x["n"] += 1
        x[r["result"] if r["result"] in ("W", "L", "P") else "UNGRADED"] += 1
        x["units"] = round(x["units"] + ((r["units"] or 0) if r["result"] in ("W", "L", "P") else 0), 2)
    return out, extra, summ


def render_trace(out, extra, summ):
    L = ["", f"SECTION K - PAPER BETS BOARD PLAY -> LIVE EXECUTOR, from {START_ET} ET (private; exact play-key join)",
         "  Does the live path exclude winners, losers, or both? Paper W-L and paper units by what the executor did:"]
    for cat in ("FILLED", "PLACED, NO FILL", "DECIDED, NOT PLACED", "NOT DECIDED"):
        x = summ.get(cat)
        if x:
            L.append(f"   {cat:<20} n {x['n']:>2} | paper W-L-P {x['W']}-{x['L']}-{x['P']} (ungraded {x['UNGRADED']}) | paper units {x['units']:+.2f}u")
    for r in out:
        L.append(f"  {r['day']} | {r['game']} | {r['side']} | paper {r['paper_book']} {r['paper_price']} {r['result']} | "
                 f"{r['cat']}: {r['detail']}")
    L.append(f"  live board orders placed that were NOT paper PLAY calls: {len(extra)}")
    for e in extra:
        L.append(f"   - {e['day']} | {e['key']} | {e['venue']}")
    return "\n".join(L)


# ---------------------------------------------------------------- SECTION L: live fill rate (Nov 17, Project 3)
def _am_to_p(a):
    try:
        a = float(a)
    except (TypeError, ValueError):
        return None
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _order_confirmed(key, lane, rows_by_lane):
    """A venue-confirmed live position (EXACT bucket of this lane) for an order key: same side word, every team of
    the key's game present in the position's game text. Exactly one match, else None - never guessed."""
    import tracker_build as _tb
    parts = key.split("|")
    if len(parts) < 5:
        return None
    game, side = parts[2].split(":")[0], parts[4].upper()
    teams = [_tb.toks(x) - _tb.WEAK for x in game.replace(" vs ", " @ ").replace(" at ", " @ ").split(" @ ")]
    if len(teams) != 2 or not all(teams):
        return None
    hits = []
    for b in rows_by_lane.get(lane) or []:
        g = _tb.toks(b.get("game")) - _tb.WEAK
        bt = str(b.get("bet") or "").strip().lower()
        sw = "OVER" if bt.startswith("over") else ("UNDER" if bt.startswith("under") else None)
        if side in ("OVER", "UNDER") and sw != side:
            continue
        if side not in ("OVER", "UNDER") and not (_tb.toks(side) - _tb.WEAK) & (_tb.toks(b.get("bet")) - _tb.WEAK):
            continue
        if all(t & g for t in teams):
            hits.append(b)
    return hits[0] if len(hits) == 1 else None


def fill_rate(orders, fills, fx, start_et=START_ET, rows_by_lane=None):
    """PRIVATE ONLY. Every PLACED live order leg since start_et: lane, venue, outcome, price gap and timing.
    Outcome from the registry fill record first (FILLED/PARTIAL -> FILLED; NO_FILL/EXPIRED/CANCELLED -> NOT FILLED;
    PLACED/RESTING -> PENDING), else from Section G's venue evidence (fx), else UNKNOWN - never guessed.
    Price gap = live after-fee implied probability minus the alert's after-fee implied probability, in cents
    (positive = the live order asked for a WORSE price than the alert). Pure."""
    d = lambda x: x if isinstance(x, dict) else {}
    pk = {str(f.get("play_key")): f for f in (fills or {}).values() if isinstance(f, dict) and f.get("play_key")}
    ev = {}
    for e in fx or []:
        for i in e.get("ids") or []:
            ev[i] = e.get("category") or ""
    legs = []
    for o in orders or []:
        day = o.get("et_day") or _et_day(o.get("decided_utc")) or ""
        if day < start_et:
            continue
        key = str(o.get("key") or "")
        lane = key.split("|", 1)[0] if key.split("|", 1)[0] in ("board", "r1", "rule", "rules") else (o.get("source") or "phase1")
        lane = {"board": "BOARD V3", "r1": "R1", "rule": "PHASE 1", "rules": "PHASE 1"}.get(lane, "PHASE 1")   # report keeps V3 as the lane's historical name; the live rule is named in the executor's own notifications
        more = o.get("live_more")
        for kind, lo in [("first", d(o.get("live_order"))), ("rest", d(o.get("live_rest")))] + \
                [("balance", d(x)) for x in (more if isinstance(more, list) else [])]:
            if lo.get("status") != "placed":
                continue
            ids = [str(lo.get(k)) for k in ("order_id", "client_id") if lo.get(k)]
            st = next((d(fills.get(i)).get("state") for i in ids if i in (fills or {})), None)
            if st is None and kind == "first":
                # the venue runner writes the fill under the play key (lane prefix optional) - same join as integrity()
                f_ = pk.get(key) or pk.get(key.split("|", 1)[-1])
                st = d(f_).get("state") if f_ else None
            if st in ("FILLED", "PARTIAL"):
                outc = "FILLED"
            elif st in ("NO_FILL", "EXPIRED", "CANCELLED", "CANCELED"):
                outc = "NOT FILLED"
            elif st in ("PLACED", "RESTING"):
                outc = "PENDING"
            else:
                c = next((ev[i] for i in ids if i in ev), "")
                outc = ("FILLED" if c.startswith(("FILLED", "VENUE SHOWS")) else
                        "NOT FILLED" if c.startswith(("NO FILL", "UNFILLED")) else "UNKNOWN")
            if outc != "FILLED" and kind == "first" and _order_confirmed(key, lane, rows_by_lane or {}):
                outc = "FILLED"   # venue evidence wins over a stale or missing registry fill record
            pa, pl = _am_to_p(o.get("alert_price_after_fee")), _am_to_p(o.get("live_px_price_after_fee"))
            dec, st_u = _t(o.get("decided_utc")), _t(o.get("start_utc"))
            legs.append({"day": day, "lane": lane, "kind": kind, "venue": str(lo.get("book") or o.get("live_book") or "?").lower(),
                         "outcome": outc, "key": key,
                         "gap_c": round(100 * (pl - pa), 1) if (pa is not None and pl is not None) else None,
                         "latency_min": round(o["latency_s"] / 60) if isinstance(o.get("latency_s"), (int, float)) else None,
                         "to_start_min": round((st_u - dec).total_seconds() / 60) if (dec and st_u) else None})
    summ = {}
    for g in legs:
        x = summ.setdefault((g["lane"], g["venue"]), {"placed": 0, "FILLED": 0, "NOT FILLED": 0, "PENDING": 0, "UNKNOWN": 0})
        x["placed"] += 1
        x[g["outcome"]] += 1
    return legs, summ


def render_fill_rate(legs, summ):
    import statistics as _st
    med = lambda v: (round(_st.median(v), 1) if v else None)
    L = ["", f"SECTION L - LIVE FILL RATE, every placed order leg from {START_ET} ET (private)",
         "  outcome: registry fill record first, else venue evidence (Section G), else UNKNOWN. gap = live after-fee price "
         "minus the alert's, in cents of probability (+ = worse than the alert)."]
    for (lane, venue), x in sorted(summ.items()):
        dec = x["FILLED"] + x["NOT FILLED"]
        rate = f"{100 * x['FILLED'] / dec:.0f}%" if dec else "n/a"
        L.append(f"   {lane:<9} {venue:<14} placed {x['placed']:>2} | filled {x['FILLED']} | not filled {x['NOT FILLED']} | "
                 f"pending {x['PENDING']} | unknown {x['UNKNOWN']} | fill rate {rate}")
    for outc in ("FILLED", "NOT FILLED"):
        g = [l for l in legs if l["outcome"] == outc]
        if g:
            L.append(f"   {outc:<10} median gap {med([l['gap_c'] for l in g if l['gap_c'] is not None])}c | median alert->order "
                     f"{med([l['latency_min'] for l in g if l['latency_min'] is not None])} min | median order->tip "
                     f"{med([l['to_start_min'] for l in g if l['to_start_min'] is not None])} min")
    for l in legs:
        L.append(f"  {l['day']} | {l['lane']} | {l['venue']} | {l['kind']} | {l['outcome']} | gap {l['gap_c']}c | "
                 f"alert->order {l['latency_min']} min | order->tip {l['to_start_min']} min | {l['key']}")
    return "\n".join(L)


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
        out.append({"game": b.get("game"), "bet": b.get("bet"), "book": b.get("book"), "category": cat,
                    "id": i, "league": b.get("league") or (r or {}).get("snap", {}).get("league"),
                    "why": str((r or {}).get("why") or "")[:70], "tries": (r or {}).get("tries"),
                    "done": (r or {}).get("done"), "has_start": bool(b.get("game_start"))})
    return out


# ---------------------------------------------------------------- V4 / gate verification (Peter, 18 Nov, Option 1)
# The private audit goes to Telegram, which Claude cannot read, and Gmail is off limits, so two approved
# verifications had no route back: whether a board ledger row actually persisted its V4 evidence, and what
# live_why_not says for a board call that never executed. Neither needs a private figure - a confirming venue's
# liquidity is market data, and a gate reason is a reason - so this block is printed COUNTS AND REASON CODES ONLY to
# the Actions log. No stake, balance, account, order id or game name. Reporting only: it decides nothing.
V4_MIN_CONFIRM = 10000.0


def _mask(t, n=90):
    """Reason text with every digit run masked, so a line, price or amount cannot ride along inside it."""
    import re
    return re.sub(r"\d", "#", str(t or ""))[:n]


def v4_verify(rows, lane_of):
    """(lines, summary) for every BOARD order row. Pure. rows are ledger/registry order rows; lane_of(row) -> lane."""
    out, seen = [], {"rows": 0, "with_evidence": 0, "accept": 0, "reject": 0, "rule_match": 0, "rule_mismatch": 0,
                     "basis_corrected": 0, "basis_raw": 0, "no_v4_field": 0}
    for r in rows or []:
        if str(lane_of(r) or "").upper() not in ("BOARD V3", "BOARD V4", "BOARD"):
            continue
        seen["rows"] += 1
        v = r.get("board_v4") if isinstance(r.get("board_v4"), dict) else None
        if v is None:
            seen["no_v4_field"] += 1
            out.append("  V4 row: no board_v4 field on this order row (written before 17 Nov, or not a board play)")
            continue
        ok = v.get("ok") is True
        seen["accept" if ok else "reject"] += 1
        ev = v.get("evidence") if isinstance(v.get("evidence"), dict) else {}
        if ev:
            seen["with_evidence"] += 1
        st = [x for x in (v.get("strength") or []) if isinstance(x, dict) and x.get("confirming")]
        # does the decision match the approved rule? accept requires a confirming venue at or above the floor
        size = ev.get("size")
        match = (ok and size is not None and float(size) >= V4_MIN_CONFIRM) or (not ok and not ev)
        seen["rule_match" if match else "rule_mismatch"] += 1
        basis = r.get("board_fee_basis")
        seen["basis_corrected" if basis is True else "basis_raw"] += 1
        rt = r.get("route") if isinstance(r.get("route"), dict) else {}
        out.append(f"  V4 row: {'ACCEPT' if ok else 'REJECT'} | evidence {'yes' if ev else 'no'}"
                   + (f" | venue {ev.get('book')} size {int(size):,} >= floor {int(V4_MIN_CONFIRM):,}" if size is not None else "")
                   + (f" | ratio {st[0].get('ratio')}x money {st[0].get('money')}" if st else " | ratio/money not recorded")
                   + f" | price basis {'corrected after-fee' if basis is True else ('raw' if basis is False else 'not recorded')}"
                   + f" | route {_mask(rt.get('rule'), 46) or 'not recorded'}"
                   + f" | matches approved rule: {'YES' if match else 'NO'}"
                   + (f" | why {_mask(v.get('why'), 60)}" if not ok and v.get("why") else ""))
    return out, seen


def gate_reasons(rows, lane_of, lanes=("BOARD V3", "BOARD V4", "BOARD")):
    """Why board orders did not go live, as masked reason text with counts. Pure. No game, side price or amount."""
    from collections import Counter
    c, out = Counter(), []
    for r in rows or []:
        if str(lane_of(r) or "").upper() not in tuple(x.upper() for x in lanes):
            continue
        w = r.get("live_why_not")
        if isinstance(w, list):
            w = "; ".join(str(x) for x in w)
        if not w:
            continue
        c[_mask(w, 110)] += 1
    for why, n in c.most_common():
        out.append(f"  gate reason x{n}: {why}")
    return out, dict(c)


def clv_reason_class(why):
    """Coarse, stable reason class for the missing-CLV trend log (Nov 17)."""
    w = str(why or "").lower()
    for k, v in (("side was never recorded", "side not captured"), ("not a team", "side not captured"),
                 ("fixture not in any cached store", "fixture not yet fetched"), ("no fixture", "fixture unmatched"),
                 ("no oddspapi fixture matched", "fixture unmatched"), ("maps onto", "fixture unmatched"),
                 ("fixture doubt", "fixture uncertain"), ("no pinnacle", "no same-line Pinnacle close"),
                 ("freshness", "stale close"), ("history", "history unavailable"), ("stale", "excluded as stale"),
                 ("not parsed", "bet text not parsed"), ("not covered", "league not covered"), ("never scored", "never scored")):
        if k in w:
            return v
    return "other"


def clv_trend(cx, lane_of):
    """{(reason class, lane, league): n} over every settled bot bet since START_ET without certified CLV. Pure."""
    from collections import Counter
    return dict(Counter((clv_reason_class(e.get("why") or e.get("category")), lane_of(e.get("id")), e.get("league") or "?")
                        for e in cx or []))


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
# Nov 17 (Peter, CLV_STANDARD.md section 1): only a same-line Pinnacle close (or the exact moneyline market) is
# CERTIFIED. A close read off Pinnacle's main line and moved to the bet's number with the half-point table is an
# ESTIMATE: reported separately, never in a certified mean, half, interval or qualification gate. Ledger rows are
# read, never changed.
CERT_HOW = ("own line", "moneyline")


def clv_method(r):
    """'certified' | 'estimated' | 'unknown' for a scored CLV ledger row (r['how'] is set by clv_ledger.close_for)."""
    how = str((r or {}).get("how") or "")
    if how in CERT_HOW:
        return "certified"
    if how.startswith("main ") and " moved to " in how:
        return "estimated"
    return "unknown"


def split_clv(cb, excluded):
    """(certified, estimated, unknown) {id: clv} from the ledger rows that carry a CLV and are not excluded."""
    out = ({}, {}, {})
    for k, r in (cb or {}).items():
        if r.get("clv") is None or r.get("fixture_doubt") or k in excluded:
            continue
        out[("certified", "estimated", "unknown").index(clv_method(r))][k] = r["clv"]
    return out


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


def lane_scope(rep, lane, clv, unit_sched, est=None):
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
    est_seg = {k: seg_stats(x, est or {}, unit, since) for k, x in (("whole", plays), ("H1", plays[:h]), ("H2", plays[h:]))}
    return {"whole": w, "H1": h1, "H2": h2, "open": b.get("open_or_ambiguous", 0), "verdict": g["verdict"],
            "clauses": g.get("clauses") or [], "est": est_seg, "plays": plays}


def combined_scope(by):
    """All proven lanes together: W-L-P, net, risked, ROI, units (sum of each lane's own-unit figure, only when every
    lane has one), and certified / estimated CLV pooled over plays. Each play appears in exactly one lane."""
    xs = [x for x in by.values() if x]
    if not xs:
        return None
    out = {}
    for seg in ("whole", "H1", "H2"):
        ss = [x[seg] for x in xs]
        es = [x["est"][seg] for x in xs]
        n_c = sum(s["clv_n"] for s in ss)
        n_e = sum(s["clv_n"] for s in es)
        risked = sum(s["risked"] for s in ss)
        out[seg] = {"n": sum(s["n"] for s in ss), "W": sum(s["W"] for s in ss), "L": sum(s["L"] for s in ss),
                    "P": sum(s["P"] for s in ss), "net": round(sum(s["net"] for s in ss), 2), "risked": round(risked, 2),
                    "roi": round(100 * sum(s["net"] for s in ss) / risked, 2) if risked else None,
                    "units": (round(sum(s["units"] for s in ss), 2) if all(s["units"] is not None for s in ss) else None),
                    "clv": (round(sum(s["clv"] * s["clv_n"] for s in ss if s["clv_n"]) / n_c, 2) if n_c else None),
                    "clv_n": n_c, "clv_missing": sum(s["clv_missing"] for s in ss),
                    "est_clv": (round(sum(s["clv"] * s["clv_n"] for s in es if s["clv_n"]) / n_e, 2) if n_e else None),
                    "est_n": n_e}
    return out


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
                e_ = x["est"][seg]
                L.append(f"   {'':<8} {seg:<5} ESTIMATED CLV (line-move adjusted, NOT certified, not in any gate) "
                         f"{f(e_['clv'], suf='%')}{'' if not e_['clv_ci'] else ' CI ' + str(e_['clv_ci'])} on {e_['clv_n']} "
                         f"beat {('n/a' if e_['beat'] is None else str(e_['beat']) + '%')}")
            L.append(f"   {lane:<8} open {x['open']} | QUALIFICATION (certified CLV only): {x['verdict']}")
            for c in x["clauses"]:
                if c["state"] != "MET":
                    L.append(f"            - {c['clause']}: {c['state']} {c.get('detail', '')}")
        cb_ = combined_scope(by)
        if cb_:
            for seg in ("whole", "H1", "H2"):
                s_ = cb_[seg]
                L.append(f"   {'COMBINED':<8} {seg:<5} n {s_['n']:>2} W-L-P {s_['W']}-{s_['L']}-{s_['P']} net {s_['net']:+.2f} "
                         f"units {f(s_['units'], suf='u')} ROI {f(s_['roi'], suf='%')} | certified CLV {f(s_['clv'], suf='%')} "
                         f"on {s_['clv_n']} (missing {s_['clv_missing']}) | estimated CLV {f(s_['est_clv'], suf='%')} on {s_['est_n']}")
    L.append(f"  Kept separate (not in any lane above): {non_exact}")
    return "\n".join(L)


# ---------------------------------------------------------------- SECTION J: per-play grade audit (Peter, 16 Nov)
def grade_rows(since_rows, row_bucket, certified, clv_rows, stale_ids, unit_sched, now_utc=None, estimated=None):
    """One graded line per bot position from START_ET, with the exact reason for every missing field. Pure.
    Never invents a result, a fill or a close: a missing value stays missing with its reason."""
    from p2_audit_core import utc, verified_money, SETTLED as _S
    now_utc = now_utc or datetime.now(timezone.utc)
    out = []
    for b in since_rows:
        i = str(b.get("id") or "")
        bucket = row_bucket.get(i, "?")
        lane = bucket.split(":", 1)[1] if bucket.startswith("EXACT:") else None
        res = b.get("result") if b.get("result") in _S else None
        gs = utc(b.get("game_start") or "")
        g = {"id": i, "date": _et_day(b.get("game_start") or b.get("settled")), "game": b.get("game"),
             "venue": b.get("book"), "bet": b.get("bet"), "bucket": bucket, "lane": lane, "result": res or "OPEN",
             "missing": []}
        # lane / trigger
        if not lane:
            g["missing"].append(f"lane: {bucket}")
        g["trigger"] = (lane + " rule (lane-level; no per-play trigger tag exists)") if lane else "UNKNOWN"
        # fill: EXACT = the venue order id or a venue fill/trade record ties this position to one registry order
        g["fill"] = "confirmed (venue-linked to one registry order)" if lane else "not proven"
        # settlement
        if not res:
            if gs and (now_utc - gs).total_seconds() > 36 * 3600:
                g["missing"].append("settlement: game ended over 36h ago and the venue shows no result")
                g["settle_status"] = "MISSING"
            else:
                g["settle_status"] = "open (game not finished)"
        else:
            g["settle_status"] = "settled"
        # money
        pl = {"result": res, "stake": b.get("stake"), "profit": b.get("profit")}
        if res and verified_money(pl):
            g["net"], g["roi"] = round(b["profit"], 2), round(100 * b["profit"] / b["stake"], 2)
            u = (unit_sched or {}).get(lane)
            g["units"] = (round(b["profit"] / u[1], 2) if u and gs and gs >= utc(u[0]) else None)
            if g["units"] is None:
                g["missing"].append("units: no verified unit for this lane and date")
        elif res:
            g["net"] = g["roi"] = g["units"] = None
            g["missing"].append("realized P/L: stake or profit missing or invalid on the venue row")
        else:
            g["net"] = g["roi"] = g["units"] = None
        # CLV
        c = certified.get(i)
        r = (clv_rows or {}).get(i)
        if c is not None:
            g["clv"], g["clv_status"] = round(100 * c, 2), "certified"
        else:
            g["clv"] = None
            if r is None:
                st = "not in the CLV ledger (never scored)"
            elif i in (stale_ids or set()):
                st = "excluded as stale"
            elif r.get("fixture_doubt"):
                st = "fixture doubt (Pinnacle match not certain)"
            elif (estimated or {}).get(i) is not None:
                st = (f"ESTIMATED only ({str(r.get('how'))[:40]}): {100 * estimated[i]:+.2f}% - line-move adjusted, "
                      "not a same-line close, never certified")
            elif r.get("clv") is not None:
                st = f"unclassified close method ({str(r.get('how'))[:30]}) - not certified"
            elif r.get("done"):
                st = "unrecoverable: " + str(r.get("why") or "no reason recorded")[:80]
            else:
                st = "pending: " + str(r.get("why") or "not scored yet")[:80]
            g["clv_status"] = st
            if res:
                g["missing"].append("certified CLV: " + st)
        g["fully_graded"] = bool(res and g.get("net") is not None and g.get("units") is not None
                                 and g["clv"] is not None and lane)
        out.append(g)
    return out


def position_counts(grades, settled_plays, cert, est):
    """Section J headline counts by POSITION (a settled play may be several fill rows). A position is fully graded,
    certified or estimated only when EVERY one of its fill rows is. Pure."""
    g = {x["id"]: x for x in grades}
    def every(p, ok):
        return bool(p.get("ids")) and all(ok(i) for i in p["ids"])
    return {"fully_graded": sum(every(p, lambda i: (g.get(i) or {}).get("fully_graded")) for p in settled_plays),
            "certified_clv_positions": sum(every(p, lambda i: cert.get(i) is not None) for p in settled_plays),
            "estimated_clv_positions": sum(every(p, lambda i: est.get(i) is not None) for p in settled_plays)}


def grade_summary(rows):
    settled = [g for g in rows if g["result"] != "OPEN"]
    return {"positions": len(rows), "settled": len(settled), "open": len(rows) - len(settled),
            "fully_graded": sum(g["fully_graded"] for g in rows),
            "missing_settlement": sum(1 for g in rows if g.get("settle_status") == "MISSING"),
            "missing_pl": sum(1 for g in settled if g.get("net") is None),
            "missing_units": sum(1 for g in settled if g.get("net") is not None and g.get("units") is None),
            "missing_certified_clv": sum(1 for g in settled if g["clv"] is None),
            "missing_lane": sum(1 for g in rows if not g["lane"]),
            "missing_trigger_tag": len(rows)}   # no per-play trigger tag exists in any source


def render_grades(rows, summ):
    f = lambda x, s="": "n/a" if x is None else f"{x:+.2f}{s}"
    L = ["", f"SECTION J - EVERY BOT POSITION FROM {START_ET} ET, GRADED (private)",
         f"  positions {summ['positions']} | settled {summ['settled']} | open {summ['open']}"
         f"{' (' + str(summ['open_fill_rows']) + ' open fill rows)' if 'open_fill_rows' in summ else ''} | FULLY GRADED {summ['fully_graded']} positions"
         f"{' (' + str(summ['fully_graded_fill_rows']) + ' fill rows)' if 'fully_graded_fill_rows' in summ else ''} "
         f"| missing: settlement {summ['missing_settlement']}, P/L {summ['missing_pl']}, units {summ['missing_units']}, "
         f"certified CLV {summ['missing_certified_clv']}, lane {summ['missing_lane']}, per-play trigger tag {summ['missing_trigger_tag']}",
         "  Strategy qualification and rankings: INSUFFICIENT EVIDENCE until grading is complete."]
    for g in sorted(rows, key=lambda x: str(x["date"])):
        L.append(f"  {g['date']} | {g['lane'] or g['bucket']} | {g['venue']} | {g['game']} | {g['bet']} | {g['result']} | "
                 f"net {f(g.get('net'))} | units {f(g.get('units'), 'u')} | ROI {f(g.get('roi'), '%')} | "
                 f"CLV {f(g['clv'], '%') if g['clv'] is not None else g['clv_status']} | fill {g['fill']} | "
                 f"{'FULLY GRADED' if g['fully_graded'] else 'INCOMPLETE: ' + '; '.join(g['missing'])}")
    return "\n".join(L)
