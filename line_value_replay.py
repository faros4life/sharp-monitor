#!/usr/bin/env python3
"""LINE VALUE REPLAY (Nov 12, 2026). Reports coverage first, changes second, and never invents an input.

Reads text files that each hold an executor email body (the LEDGER block, found with rfind + raw_decode exactly as
every other reader in this repo does) and/or a 'LINEVALUE SHADOW' email body. Prints COUNTS only: no stakes, no
balances, no keys.

For every recorded decision it says which of three things is true:
  A. LEGACY-EXACT   the old decision can be reproduced bit for bit (needs the exact hp and the full pre-filter ladder)
  B. NEW-CALC EXACT the line_value calculation can be run (needs an independent two-sided reference, the mass of
                    every integer the move crosses, and a verified settlement rule for any whole-number line)
  C. CHANGES        only computed for B-exact decisions: which candidates the new calculation would admit or reject
                    where the legacy rule did the opposite, with the numbers that explain why

A missing input is labelled UNREPLAYABLE with the input named. Nothing is reconstructed from today's quotes, from a
rounded figure in an email, or from a default.

Usage:   python3 -I line_value_replay.py email1.txt [email2.txt ...]
"""
import json
import sys
from collections import Counter

import line_value as lv

MARK = "LEDGER (machine-readable"
SHADOW_MARK = "LINEVALUE (machine-readable)"


# ---------------------------------------------------------------- reading
def extract_json(text, marker):
    """rfind the marker, then raw_decode from the first bracket (the repo's one way of reading these blocks)."""
    i = text.rfind(marker)
    if i < 0:
        return None
    j = min((k for k in (text.find("[", i), text.find("{", i)) if k >= 0), default=-1)
    if j < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(text[j:])
    return obj


def split_key(key):
    """'NBA|Charlotte Hornets @ Phoenix Suns|total|UNDER' -> (sport, market, side)."""
    p = (key or "").split("|")
    return (p[0] if p else None), (p[2] if len(p) > 2 else None), (p[3] if len(p) > 3 else None)


# ---------------------------------------------------------------- legacy ledger rows
def classify_row(row):
    """Coverage for one recorded decision. Pure: reads only what the row recorded."""
    sport, market, side = split_key(row.get("key"))
    alert_line = row.get("alert_line")
    mtype = "total" if market == "total" else ("spread" if alert_line is not None else "moneyline")
    out = {"key": row.get("key"), "source": row.get("source"), "mtype": mtype, "verdict": row.get("verdict"),
           "legacy_exact": False, "new_calc_exact": False, "unreplayable": [], "structure": {}, "change": None}
    # what the ledger NEVER recorded - true of every row written before the shadow capture existed
    lvs = row.get("lvs") if row.get("lvs_capture") == "ok" else None
    out["capture"] = row.get("lvs_capture", "absent (row predates capture)")
    if lvs:   # captured going forward: hp, full ladder and rejected candidates ARE recorded; the reference may still be absent
        out["unreplayable"] += [] if lvs.get("reference") else ["independent_reference"]
    else:
        out["unreplayable"] += ["independent_reference", "exact_hp", "complete_prefilter_ladder", "rejected_candidates"]
    if "venues_considered" not in row or row["venues_considered"] is None:
        out["unreplayable"].append("venues_considered")
    if alert_line is None or mtype == "moneyline":
        out["unreplayable"].append("line_based_market_only")
        return out
    cands = row.get("venues_considered") or []
    out["lane1"] = (row.get("source") or "rules") == "rules" and not ((row.get("live_order") or {}).get("lane"))
    out["ncaaf_gap"] = False
    reasons, mass_ok, settle_ok = Counter(), True, True
    for c in cands:
        if c.get("line") is None:
            continue
        rq = lv.requirements(sport, mtype, side if mtype == "total" else 0, alert_line, c["line"], c.get("book"))
        mass_ok &= rq["mass_ok"]
        settle_ok &= rq["settlement"] in ("n/a", "refund")
        for r in rq["reasons"]:
            reasons[r.split(":")[0]] += 1
            if sport == "NCAAF" and mtype == "total" and r.startswith("no_mass_row:") and int(r.split(":")[1]) in lv.NCAAF_TOTAL_GAP:
                out["ncaaf_gap"] = True
    out["structure"] = {"evaluated": bool(cands), "candidates_recorded": len(cands), "mass_rows_for_every_move": bool(cands) and mass_ok,
                        "settlement_ok_for_every_move": bool(cands) and settle_ok, "gaps": dict(reasons)}
    return out


# ---------------------------------------------------------------- shadow payloads (full replay)
def replay_play(pl):
    """B-exact replay of one SHADOW play record. Returns the per-candidate comparison with reasons."""
    ref = pl.get("reference")
    out = {"play_key": pl.get("play_key"), "has_reference": bool(ref), "cands": 0, "supported": 0, "unsupported": 0,
           "no_reference": 0, "other_gate": 0, "agree": 0, "would_reject": [], "would_admit": [], "reasons": Counter()}
    for c in pl.get("cands") or []:
        out["cands"] += 1
        sh = c.get("shadow") or {}
        st = sh.get("status")
        if sh.get("reason") == "no_reference" or st == "no_reference":
            out["no_reference"] += 1
            continue
        if st != "ok":
            out["unsupported"] += 1
            out["reasons"][sh.get("reason") or st or "unknown"] += 1
            continue
        out["supported"] += 1
        if c.get("legacy") not in ("qualified", "price_gate"):      # floor / depth / basis gates apply under BOTH rules
            out["other_gate"] += 1
            continue
        legacy = c.get("legacy") == "qualified"
        new = bool(sh.get("qualifies"))
        mx = sh.get("max_am_after_fee")
        row = {"book": c.get("book"), "line": c.get("line"), "am_after_fee": c.get("am_after_fee"), "method": sh.get("method"),
               "max_am_after_fee": None if mx is None else round(mx, 1), "allowance": sh.get("allowance"),
               "crossed": (sh.get("needs") or {}).get("crossed"), "legacy": c.get("legacy")}
        why_ok = f"{sh.get('method')}: max acceptable {row['max_am_after_fee']} (allowance {row['allowance']})"
        if legacy and not new:
            out["would_reject"].append(dict(row, why=f"price {row['am_after_fee']} is worse than the {why_ok}"))
        elif new and not legacy:
            out["would_admit"].append(dict(row, why=f"price {row['am_after_fee']} meets the {why_ok} but the legacy rule said '{c.get('legacy')}'"))
        else:
            out["agree"] += 1
    return out


# ---------------------------------------------------------------- report
def report(texts):
    rows, plays, rechecks = [], [], []
    for t in texts:
        led = extract_json(t, MARK)
        if isinstance(led, list):
            rows += [r for r in led if isinstance(r, dict)]
        for r in (led if isinstance(led, list) else []):   # shadow record rides inside the ledger row
            if isinstance(r, dict) and isinstance(r.get("lvs"), dict) and r.get("lvs_capture") == "ok":
                plays.append(r["lvs"])
            rechecks += (r.get("lvs_rechecks") or []) if isinstance(r, dict) else []
        sh = extract_json(t, SHADOW_MARK)   # legacy standalone payload (never emitted by the final design; still readable)
        if isinstance(sh, dict):
            plays += sh.get("plays") or []
            rechecks += sh.get("rechecks") or []
    cls = [classify_row(r) for r in rows]
    uniq = {(r.get("key"), r.get("alert_utc")) for r in rows}   # one play counts once, across lanes
    rep = {"ledger_rows_examined": len(rows), "unique_plays_examined": len(uniq),
           "legacy_exact": sum(c["legacy_exact"] for c in cls), "new_calc_exact": sum(c["new_calc_exact"] for c in cls),
           "unreplayable_inputs": Counter(i for c in cls for i in c["unreplayable"]),
           "capture_status": Counter(c["capture"].split(":")[0] for c in cls),
           "structure_evaluated": sum(1 for c in cls if c["structure"].get("evaluated")),
           "structure_ok_if_a_reference_existed": sum(1 for c in cls if c["structure"].get("mass_rows_for_every_move")
                                                      and c["structure"].get("settlement_ok_for_every_move")),
           "structure_gaps": Counter(g for c in cls for g in (c["structure"].get("gaps") or {})),
           "lane1_examined": sum(1 for c in cls if c.get("lane1")),
           "lane1_ncaaf_total_gap_58_68": sum(1 for c in cls if c.get("lane1") and c.get("ncaaf_gap")),
           "shadow_plays": len(plays), "shadow_with_reference": sum(1 for p in plays if p.get("reference")),
           "rechecks_recorded": len(rechecks)}
    rp = [replay_play(p) for p in plays]
    rep["shadow_candidates"] = sum(r["cands"] for r in rp)
    rep["shadow_supported"] = sum(r["supported"] for r in rp)
    rep["shadow_unsupported"] = sum(r["unsupported"] for r in rp)
    rep["shadow_no_reference"] = sum(r["no_reference"] for r in rp)
    rep["shadow_agree"] = sum(r["agree"] for r in rp)
    rep["shadow_other_gate"] = sum(r["other_gate"] for r in rp)
    rep["would_reject"] = [x for r in rp for x in r["would_reject"]]
    rep["would_admit"] = [x for r in rp for x in r["would_admit"]]
    rep["shadow_unsupported_reasons"] = Counter(k for r in rp for k in r["reasons"].elements())
    return rep


def render(rep, detail=True):
    """detail=False is the PUBLIC-LOG form: counts only - no game, line, price or book on any change line."""
    L = ["LINE VALUE REPLAY (counts only)",
         f"  legacy ledger rows examined: {rep['ledger_rows_examined']} ({rep['unique_plays_examined']} unique plays)",
         f"  A. legacy-exact (old decision reproducible):   {rep['legacy_exact']}",
         f"  B. new-calc exact (reference + masses + rule): {rep['new_calc_exact']}",
         "  UNREPLAYABLE, by missing input (rows): " + (", ".join(f"{k} {v}" for k, v in sorted(rep["unreplayable_inputs"].items())) or "none"),
         "  capture status (rows): " + (", ".join(f"{k} {v}" for k, v in sorted(rep["capture_status"].items())) or "none"),
         f"  mass-row/settlement check EVALUATED on {rep['structure_evaluated']} rows (it needs no reference); "
         f"supportable on {rep['structure_ok_if_a_reference_existed']}",
         f"  Lane 1 decisions examined: {rep['lane1_examined']}; needing a missing NCAAF total mass in 58-68: "
         f"{rep['lane1_ncaaf_total_gap_58_68']} ({(100 * rep['lane1_ncaaf_total_gap_58_68'] / rep['lane1_examined']) if rep['lane1_examined'] else 0:.1f}% of Lane 1)",
         "  gaps found where evaluated (absent mass row / unverified settlement, NOT 'none'): " + (", ".join(f"{k} {v}" for k, v in sorted(rep["structure_gaps"].items())) or "none"),
         f"  shadow records: {rep['shadow_plays']} plays ({rep['shadow_with_reference']} with a reference), {rep['rechecks_recorded']} rechecks",
         f"  shadow candidates: {rep['shadow_candidates']} = supported {rep['shadow_supported']} + unsupported "
         f"{rep['shadow_unsupported']} + no reference {rep['shadow_no_reference']}; of the supported: price-agree {rep['shadow_agree']}, "
         f"floor/depth-gated under both rules {rep['shadow_other_gate']}, price disagreements {len(rep['would_reject']) + len(rep['would_admit'])}",
         "  unsupported reasons: " + (", ".join(f"{k} {v}" for k, v in sorted(rep["shadow_unsupported_reasons"].items())) or "none"),
         f"  C. DECISIONS THAT CHANGE: would reject {len(rep['would_reject'])}, would admit {len(rep['would_admit'])}"]
    for tag, key in (("REJECT", "would_reject"), ("ADMIT", "would_admit")):
        if not detail:
            by = Counter("EV below the bar" if tag == "REJECT" else "EV meets the bar, legacy said no" for _ in rep[key])
            L += [f"    {tag} reason: {k} x{v}" for k, v in sorted(by.items())]
            continue
        for x in rep[key]:
            L.append(f"    {tag} {x['book']} {x['line']} {x['am_after_fee']:+d}: {x['why']}")
    L.append("  NOTE: these are shadow-calculation differences, not an outcome-level verdict on converted lines")
    return "\n".join(L)


if __name__ == "__main__":
    texts = [open(p, encoding="utf-8", errors="replace").read() for p in sys.argv[1:]]
    print(render(report(texts)))


# ---------------------------------------------------------------- per-fill detail (Peter, Nov 12 09:26): lines and prices, never stakes
def cents_worse(am, c):
    """Copy of executor.cents_worse (the audit must not import execution code)."""
    am = int(am)
    if am < 0:
        return am - c
    w = am - c
    return w if w >= 100 else -(100 + (100 - w))


def recover_hp(row, mtype, side):
    """The legacy half-point allowance backed out of a recorded off-line candidate's threshold:
    thr = american(alert_cost + tol + hb*hp)  =>  hp = (prob(thr) - alert_cost - tol) / hb. thr is an integer price, so the
    recovery carries the 1-cent rounding; returns (hp, +/-err) or (None, why). Never reconstructs from today's quotes."""
    af, al = row.get("alert_price_after_fee"), row.get("alert_line")
    if af is None or al is None:
        return None, "alert price/line not recorded"
    c_alert = lv.cover_threshold(mtype, side, al)
    for c in row.get("venues_considered") or []:
        if c.get("line") is None or c.get("thr") is None or abs(float(c["line"]) - float(al)) < 1e-9:
            continue
        hb = (c_alert - lv.cover_threshold(mtype, side, c["line"])) / 0.5
        if abs(hb) < 1e-9:
            continue
        tolc = c.get("tolerance_cents") or 0
        cost = lv.am_to_prob(af)
        tol = lv.am_to_prob(cents_worse(af, tolc)) - cost if tolc else 0.0
        thr = int(c["thr"])
        hp = (lv.am_to_prob(thr) - cost - tol) / hb
        err = abs(lv.am_to_prob(cents_worse(thr, 1)) - lv.am_to_prob(thr)) / abs(hb)
        return round(hp, 5), round(err, 5)
    return None, "no off-line candidate recorded (hp only appears in a threshold at another line)"


def fill_detail(row):
    sport, market, side = split_key(row.get("key"))
    mtype = "total" if market == "total" else ("spread" if row.get("alert_line") is not None else "moneyline")
    d = {"alert_utc": row.get("alert_utc"), "key": row.get("key"), "lane": "lane1" if (row.get("source") or "rules") == "rules" else row.get("source"),
         "verdict": row.get("verdict"), "live": row.get("live"), "alert_line": row.get("alert_line"), "alert_af": row.get("alert_price_after_fee"),
         "fill_book": row.get("fill_book") or (row.get("live_order") or {}).get("book"), "fill_line": row.get("fill_line"),
         "fill_af": row.get("fill_price_after_fee"), "is_minus_130": row.get("fill_price_after_fee") == -130,
         "old_hp": None, "old_hp_err": None, "old_hp_note": None, "method": None, "repl_max_af": None, "repl_verdict": None, "repl_reason": None}
    if mtype == "moneyline" or d["alert_line"] is None or d["alert_af"] is None:
        d["repl_verdict"], d["repl_reason"] = "unresolved", "not a line market or alert not recorded"
        return d
    hp, err = recover_hp(row, mtype, side if mtype == "total" else 0)
    if hp is None:
        d["old_hp_note"] = err
    else:
        d["old_hp"], d["old_hp_err"] = hp, err
    if d["fill_line"] is None or d["fill_af"] is None:
        d["repl_verdict"], d["repl_reason"] = "unresolved", "no fill recorded"
        return d
    tolc = next((c.get("tolerance_cents") for c in row.get("venues_considered") or [] if c.get("book") == d["fill_book"]), 0) or 0
    cv = lv.convert(sport, mtype, side if mtype == "total" else 0, d["alert_line"], d["alert_af"], d["fill_line"], d["fill_af"],
                    d["fill_book"], tolc, cents_worse, None)      # ref=None: history holds no reference; mass methods say so
    d["method"] = cv.get("method")
    if cv["status"] != "ok":
        d["repl_verdict"], d["repl_reason"] = "unresolved", f"{cv['reason']}" + (f" ({cv['detail']})" if cv.get("detail") else "")
        return d
    d["repl_max_af"] = round(cv["max_am_after_fee"], 1)
    d["repl_verdict"] = "would_accept" if cv["qualifies"] else "would_reject"
    d["repl_reason"] = f"{cv['method']} allowance {cv['allowance']}: max {d['repl_max_af']} vs fill {d['fill_af']}"
    return d


def fill_details(texts):
    out = []
    for t in texts:
        led = extract_json(t, MARK)
        for r in (led if isinstance(led, list) else []):
            if isinstance(r, dict) and r.get("fill_price_after_fee") is not None:
                out.append(fill_detail(r))
    return out


def fill_counts(details):
    c = Counter()
    for d in details:
        c["fills"] += 1
        c[f"verdict:{d['repl_verdict']}"] += 1
        if d["is_minus_130"]:
            c["fills_at_-130"] += 1
            c[f"-130:{d['repl_verdict']}"] += 1
        if d["old_hp"] is not None:
            c["old_hp_recovered"] += 1
    return c
