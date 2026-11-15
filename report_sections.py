"""Daily report sections B (Project 1) and D (data integrity). Pure functions, counts only.

Inputs are plain dicts already decrypted by the caller. Nothing here reads a network, a venue or an
executor module, and nothing writes.
"""
from datetime import datetime, timezone, timedelta

START_ET = "2026-11-12"
ET = timezone(timedelta(hours=-5))
P1_BASELINE_UTC = None   # NOT CONFIRMED. Until Peter confirms it, no fill is called "qualifying".
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


def project1(bot_rows, clv, baseline_utc=P1_BASELINE_UTC):
    """Bot rows first observed (ingest_checked, a never-overwritten stamp) on/after 12 Nov ET."""
    fresh = [b for b in bot_rows if (_et_day(b.get("ingest_checked")) or "") >= START_ET]
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
        q = [b for b in graded if _t(b.get("ingest_checked")) and _t(b.get("ingest_checked")) >= b0]
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
    placed_ids, placed_missing = 0, 0
    for o in orders:
        day = o.get("et_day") or _et_day(o.get("decided_utc")) or ""
        if day < START_ET:
            continue
        more = o.get("live_more")
        for lo in [d(o.get("live_order")), d(o.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]:
            if lo.get("status") == "placed" and (lo.get("order_id") or lo.get("client_id")):
                placed_ids += 1
                if not any(str(lo.get(k)) in fills for k in ("order_id", "client_id") if lo.get(k)):
                    placed_missing += 1
    nonterm = sum(1 for f in fills.values() if f.get("state") in ("PLACED", "RESTING"))
    since = [b for b in bot_rows if (_et_day(b.get("settled")) or "") >= START_ET or not b.get("settled")]
    settled = [b for b in since if b.get("result") in SETTLED]
    join = (rep or {}).get("join") or {}
    buckets = (rep or {}).get("buckets") or {}
    not_exact = sum(v["all"]["settled"] + v["open_or_ambiguous"] for b, v in buckets.items() if not b.startswith("EXACT"))
    last_src = max([str(b.get("settled") or "") for b in bot_rows] + [str(b.get("ingest_checked") or "") for b in bot_rows] or [""])
    return {"placed_orders_since_start": placed_ids, "placed_orders_without_fill_record": placed_missing,
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
