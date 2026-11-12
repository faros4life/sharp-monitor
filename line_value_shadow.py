"""LINE VALUE SHADOW CAPTURE (Nov 12, 2026). Records, never decides.

The executor's legacy half-point rule keeps making every decision. This module assembles, for each play the
executor evaluates, the inputs a replay needs and the line_value verdict where one can honestly be given:

  - the complete pre-filter ladder (every book/line read, before the floor / gate / liquidity filters)
  - EVERY candidate with the reason it was rejected, or that it qualified (selection)
  - the exact hp (full precision) and where it came from, the legacy threshold, the tolerance
  - the independent reference, its timestamp and source - or WHY there is none
  - what the new calculation would need for that move (crossed integers, mass rows, settlement rule)
  - the settlement rules and calc version in force
  - the order-time recheck (RECHECKS), with the same fields

Nothing here is read by a decision. Every entry point swallows its own exceptions: a failure to record can
never change, delay or block an order. Emails carry counts of rows, never balances or stakes.
"""
import json
import os

import line_value as lv

RECHECKS = []          # appended by executor.revalidate(); read by ledger_fields()


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def reference_for(ctx, ladder):
    """(Reference | None, why, detail). DIAGNOSTIC ONLY since Nov 12: the replacement is alert-anchored, so nothing here
    gates a decision. When present it must still be INDEPENDENT of the venue being priced: a separate book,
    two-sided, with a line and timestamps (line_value_ref validates game, market, line, period, freshness and the
    reference book's settlement rule). The execution venue's own opposite quote is recorded in the ladder for
    information but is NOT used - it would only restate the venue's price."""
    import line_value_ref as lr
    ref, rec = lr.pinnacle_reference(ctx.get("pin"), ctx["mtype"], ctx["side"], ctx.get("start_utc"),
                                     ctx.get("now_dt"), ctx["sport"])
    return ref, ("pinnacle_two_sided" if ref else (rec.get("why") or "no_reference")), rec


def _shadow_one(ctx, ref, cand, worse):
    """The line_value verdict for one candidate through the ONE shared convert(): method, source, allowance,
    assumptions and calc version are all in the record. A mass method with no reference says 'no_reference'."""
    book, line, am = cand["book"], cand["line"], cand.get("am_after_fee")
    req = lv.requirements(ctx["sport"], ctx["mtype"], ctx["side"], ctx["alert_line"], line, book)
    out = {"needs": req}
    if am is None:
        return dict(out, status="no_price")
    tol = ctx["tol_cents"] if book in ctx["tol_books"] else 0
    cv = lv.convert(ctx["sport"], ctx["mtype"], ctx["side"], ctx["alert_line"], ctx["alert_af"], line, am, book, tol, worse, ref,
                    ctx.get("cap_am"))
    keep = ("status", "reason", "detail", "qualifies", "ev", "ev_bar", "w", "p", "l", "method", "input_type", "value_status",
            "source", "allowance", "assumptions", "max_am_after_fee", "max_am_after_fee_calc", "effective_max_am_after_fee",
            "capped", "cap_am", "max_prob", "c_eq", "max_cents", "calc", "reference", "diagnostic_reference")
    return dict(out, **{k: cv.get(k) for k in keep})


def build(ctx, ladder, cand_notes, worse):
    """The per-play record. ctx: play_key, source, sport, mtype, side, alert_line, alert_af, tol_cents, tol_books,
    hp, hp_src, floor, now_utc. ladder: rows {book,line,am_after_fee,shown,am_q,levels,[opp_am_after_fee]}.
    cand_notes: rows {book,line,am_after_fee,legacy:<why rejected | 'qualified'>,hb,c_eq_q,thr}."""
    try:
        ref, why, rdet = reference_for(ctx, ladder)
        cands = []
        for c in cand_notes:
            cands.append(dict(c, shadow=_shadow_one(ctx, ref, c, worse)))
        return {"calc": lv.CALC_VERSION, "play_key": ctx.get("play_key"), "source": ctx.get("source"),
                "sport": ctx["sport"], "mtype": ctx["mtype"], "side": str(ctx["side"]),
                "alert_line": ctx["alert_line"], "alert_af": ctx["alert_af"], "tol_cents": ctx["tol_cents"],
                "tol_books": list(ctx["tol_books"]), "hp": _r(ctx["hp"], 9), "hp_src": ctx["hp_src"],
                "floor": ctx.get("floor"), "now_utc": ctx.get("now_utc"),
                "reference": ({"line": ref.line, "q": _r(ref.q, 6), "ts": ref.ts, "source": ref.source} if ref else None),
                "reference_status": why, "reference_detail": rdet,
                "settlement_rules": {("/".join(k) if isinstance(k, tuple) else k): v for k, v in lv.SETTLEMENT.items()},
                "mass_rows": sorted(f"{k[0]}/{k[1]}/{k[2]}" for k in lv.MASS),
                "ladder": ladder, "cands": cands}
    except Exception as ex:     # recording must never touch a decision
        return {"calc": lv.CALC_VERSION, "error": str(ex)[:120]}


def note_recheck(rv, book, line, am_after_fee, hb, c_eq_q, legacy_pass, why=None):
    """Order-time recheck, same fields. Called from executor.revalidate(); swallows everything."""
    if os.environ.get("LINE_VALUE_SHADOW", "1") == "0":
        return
    try:
        al = rv.get("al") or {}
        req = lv.requirements(al.get("sport"), rv.get("mtype"), rv.get("side"), rv.get("line"), line, book)
        RECHECKS.append({"calc": lv.CALC_VERSION, "play_key": (rv.get("play_key") or al.get("play_key")),
                         "sport": al.get("sport"), "mtype": rv.get("mtype"), "side": str(rv.get("side")),
                         "alert_line": rv.get("line"), "alert_af": rv.get("alert_af"), "book": book, "line": line,
                         "am_after_fee": am_after_fee, "hb": hb, "hp_stored": _r(rv.get("hp"), 9),
                         "c_eq_q": _r(c_eq_q), "alert_cost": _r(rv.get("alert_cost")), "px_tol": _r(rv.get("px_tol")),
                         "legacy_pass": bool(legacy_pass), "legacy_why": why, "needs": req,
                         "reference": None, "reference_status": "not stored at evaluate time"})
    except Exception:
        pass


def ledger_fields(r):
    """Keys merged into the EXISTING ledger row (no extra email). Always returns lvs_capture, so a failed or skipped
    capture is a recorded fact and not silence: 'ok' | 'off' | 'not_evaluated' | 'error: <why>'. Never raises."""
    try:
        if os.environ.get("LINE_VALUE_SHADOW", "1") == "0":
            return {"lvs_capture": "off"}
        lvs = r.get("lvs")
        pk = (r.get("play") or {}).get("play_key")
        rcs = [x for x in RECHECKS if x.get("play_key") == pk] if pk else []
        if lvs is None:
            return {"lvs_capture": "not_evaluated", "lvs_rechecks": rcs}
        if "error" in lvs:
            return {"lvs_capture": "error: " + str(lvs["error"])[:100], "lvs_rechecks": rcs}
        slim = dict(lvs, ladder=[{k: v for k, v in row.items() if k != "levels"} for row in (lvs.get("ladder") or [])])
        return {"lvs_capture": "ok", "lvs": slim, "lvs_rechecks": rcs}
    except Exception as ex:
        return {"lvs_capture": "error: " + str(ex)[:100]}


LVS_BUDGET = int(os.environ.get("LINE_VALUE_BUDGET_BYTES", "") or 400_000)   # bytes of ledger JSON; email bodies truncate near 1 MB


def cap_rows(rows, budget=None):
    """Keep the run's ledger JSON under `budget` bytes by shrinking ONLY the lvs fields, in stages applied to every row
    (so the ledger is uniformly detailed), never by cutting JSON. Stage 1 drops the ladder; stage 2 drops per-candidate
    'needs' and the reference detail; stage 3 keeps only the reference and counts. lvs_capture records the stage.
    Non-lvs fields are never touched. Returns (rows, stage). Never raises."""
    budget = LVS_BUDGET if budget is None else budget
    try:
        def size():
            return len(json.dumps(rows, separators=(",", ":")).encode())
        stage = 0
        while size() > budget and stage < 3:
            stage += 1
            for r in rows:
                lvs = r.get("lvs") if isinstance(r, dict) else None
                if not isinstance(lvs, dict) or r.get("lvs_capture") not in ("ok",) and not str(r.get("lvs_capture", "")).startswith("capped"):
                    continue
                if stage == 1:
                    lvs.pop("ladder", None)
                elif stage == 2:
                    lvs.pop("reference_detail", None)
                    for c in lvs.get("cands") or []:
                        (c.get("shadow") or {}).pop("needs", None)
                else:
                    r["lvs"] = {"calc": lvs.get("calc"), "reference": lvs.get("reference"), "reference_status": lvs.get("reference_status"),
                                "hp": lvs.get("hp"), "n_cands": len(lvs.get("cands") or []),
                                "n_qualified": sum(1 for c in lvs.get("cands") or [] if c.get("legacy") == "qualified")}
                r["lvs_capture"] = f"capped:stage{stage}"
        return rows, stage
    except Exception:
        return rows, -1
