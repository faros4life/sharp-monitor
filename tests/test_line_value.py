"""Nov 12, 2026: line_value.py - push-aware value of a line move. Pure arithmetic; no network.

What these tests pin:
  1. the two halves of a whole number are NOT equal   - loss->push is worth +m, push->win is worth +m*b
  2. probabilities are coherent                       - win + push + loss == 1 and none negative, across a grid
  3. fees are applied exactly once                    - the module prices exactly what it is handed (after-fee)
  4. same-line identity with the legacy rule          - alert price (or its 2c-worse tolerance) is the exact boundary
  5. one bar for selection, maximum price and recheck - max_acceptable() is the boundary evaluate() uses
  6. unsupported is a labelled answer, never a guess  - no mass row, unverified settlement, far from line, one-sided
  7. every mass row carries its provenance            - dataset, dates, n >= 200, se consistent with m and n
  8. conditional-on-no-push de-vig                     - a two-sided quote is not an absolute probability
  9. thresholds                                        - spread / over / under map to the right c and the right event
"""
import inspect
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value as lv  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


M3 = lv.MASS[("NFL", "spread", 3)].m          # 0.092
lv.SETTLEMENT["testbook"] = "refund"          # a verified-refund venue for the whole-number tests only


def ref(line, q=0.5, mtype="spread", side=0):
    return lv.Reference(mtype, side, line, q, "2026-11-12T12:00:00Z", "testref")


# ---------------------------------------------------------------- 1. halves are not equal
for am in (-110, -130, -105, +120, +150):
    b = lv.net_per_dollar(am)
    r = ref(-3.0, 0.5)                                          # whole-number reference: -3
    o_loss = lv.outcomes_at(r, "NFL", -3.5)                     # margin 3 = LOSS
    o_push = lv.outcomes_at(r, "NFL", -3.0)                     # margin 3 = PUSH
    o_win = lv.outcomes_at(r, "NFL", -2.5)                      # margin 3 = WIN
    d1 = lv.ev_per_dollar(o_push, am) - lv.ev_per_dollar(o_loss, am)
    d2 = lv.ev_per_dollar(o_win, am) - lv.ev_per_dollar(o_push, am)
    ck(f"loss->push is worth +m at {am:+d}", close(d1, M3), f"{d1:.6f} vs {M3}")
    ck(f"push->win is worth +m*b at {am:+d}", close(d2, M3 * b), f"{d2:.6f} vs {M3 * b:.6f}")
    if abs(b - 1.0) > 1e-6:
        ck(f"the two halves differ at {am:+d}", abs(d1 - d2) > 1e-6, f"{d1:.5f} {d2:.5f}")
ck("the legacy half-and-half assumption is NOT what the module returns at -130",
   not close(lv.net_per_dollar(-130), 1.0), "")

# ---------------------------------------------------------------- 2. coherence across a grid
bad = []
for q in (0.2, 0.35, 0.5, 0.65, 0.8):
    for ref_line in (-1, -1.5, -3, -3.5, -4, -6.5, -7, -7.5, -10, 2.5, 3, 3.5):
        for cand in (ref_line - 1, ref_line - 0.5, ref_line, ref_line + 0.5, ref_line + 1):
            try:
                o = lv.outcomes_at(ref(ref_line, q), "NFL", cand)
            except lv.Unsupported:
                continue
            if abs(o.w + o.p + o.l - 1) > 1e-9 or min(o.w, o.p, o.l) < -1e-12:
                bad.append((q, ref_line, cand, o))
ck("win+push+loss==1 and none negative on the whole grid", not bad, str(bad[:2]))
ck("a better line never lowers P(win) (spread: higher handicap is better)", all(
    lv.outcomes_at(ref(-3.5, 0.5), "NFL", c + 0.5).w >= lv.outcomes_at(ref(-3.5, 0.5), "NFL", c).w - 1e-12
    for c in (-4.5, -4.0, -3.5, -3.0)), "")
ck("half->half across 3 moves exactly m3 of win probability",
   close(lv.outcomes_at(ref(-3.5, 0.5), "NFL", -2.5).w - lv.outcomes_at(ref(-3.5, 0.5), "NFL", -3.5).w, M3), "")
ck("half->half across 3 needs no settlement rule (no push at either end)",
   lv.evaluate(ref(-3.5), "NFL", "unlisted_venue", -3.5, -110, -2.5, -125)["status"] == "ok", "")

# ---------------------------------------------------------------- 3. fees exactly once
r0 = ref(-3.5, 0.55)
e_a = lv.evaluate(r0, "NFL", "kalshi", -3.5, -110, -3.5, -110)
o = lv.outcomes_at(r0, "NFL", -3.5)
ck("EV is w*b - l at exactly the price handed in (no fee inside)", close(e_a["ev"], o.w * lv.net_per_dollar(-110) - o.l), "")
ck("a screen price and its after-fee price give DIFFERENT EV (callers must pass after-fee, once)",
   abs(lv.ev_per_dollar(o, -110) - lv.ev_per_dollar(o, ex.cents_worse(-110, 2))) > 1e-4, "")
src = inspect.getsource(lv)
ck("module has no fee table or fee multiplication", "WIN_FEE" not in src and "taker_fee" not in src and "* 0.98" not in src, "")

# ---------------------------------------------------------------- 4. same-line identity with the legacy rule
for am0 in (-130, -115, -110, -105, 100, 120):
    for tolc, label in ((0, "no tolerance"), (2, "2c tolerance")):
        rr = ref(-2.5, 0.52)
        at_bar = ex.cents_worse(am0, tolc) if tolc else am0
        e_in = lv.evaluate(rr, "NFL", "kalshi", -2.5, am0, -2.5, at_bar, tolc, ex.cents_worse)
        e_out = lv.evaluate(rr, "NFL", "kalshi", -2.5, am0, -2.5, ex.cents_worse(at_bar, 1), tolc, ex.cents_worse)
        ck(f"same line, price at the bar qualifies ({am0:+d}, {label})", e_in["status"] == "ok" and e_in["qualifies"], str(e_in))
        ck(f"same line, 1c past the bar does not ({am0:+d}, {label})", e_out["status"] == "ok" and not e_out["qualifies"], str(e_out))
        ck(f"same-line probability model does not matter ({am0:+d}, {label})",
           lv.evaluate(ref(-2.5, 0.40), "NFL", "kalshi", -2.5, am0, -2.5, at_bar, tolc, ex.cents_worse)["qualifies"], "")

# ---------------------------------------------------------------- 5. one bar for evaluate and max_acceptable
bad = []
for q in (0.45, 0.5, 0.6):
    for alert_line, cand_line in ((-3.5, -2.5), (-2.5, -3.5), (-3.5, -3.5), (-3.0, -2.5), (-3.5, -3.0), (-6.5, -7.5), (-7.5, -6.5)):
        for am0 in (-120, -110, 105):
            for tolc in (0, 2):
                rr = ref(alert_line, q)
                mx = lv.max_acceptable(rr, "NFL", "testbook", alert_line, am0, cand_line, tolc, ex.cents_worse)
                if mx["status"] != "ok":
                    continue
                am_edge = mx["max_am_after_fee"]
                # a price clearly better than the boundary qualifies; clearly worse does not
                better = lv.prob_to_am(max(mx["max_prob"] - 0.004, 0.02))
                worse = lv.prob_to_am(min(mx["max_prob"] + 0.004, 0.98))
                e_b = lv.evaluate(rr, "NFL", "testbook", alert_line, am0, cand_line, better, tolc, ex.cents_worse)
                e_w = lv.evaluate(rr, "NFL", "testbook", alert_line, am0, cand_line, worse, tolc, ex.cents_worse)
                e_e = lv.evaluate(rr, "NFL", "testbook", alert_line, am0, cand_line, am_edge, tolc, ex.cents_worse)
                if not (e_b["qualifies"] and not e_w["qualifies"] and abs(e_e["ev"] - e_e["ev_bar"]) < 1e-9):
                    bad.append((q, alert_line, cand_line, am0, tolc))
ck("max_acceptable is exactly evaluate()'s boundary (ev == ev_bar at the edge; better passes; worse fails)", not bad, str(bad[:3]))

# a hand-worked case (independent arithmetic): reference q=.5 at -3.5, alert -110 at -3.5; candidate -2.5 (crosses 3)
rr = ref(-3.5, 0.5)
w1 = 0.5 + M3
l1 = 0.5 - M3          # the margin-3 mass leaves the LOSS column as it enters the WIN column
ev_bar_hand = 0.5 * (100 / 110) - 0.5
b_max = (ev_bar_hand + l1) / w1
c_hand = 1 / (1 + b_max)
mx = lv.max_acceptable(rr, "NFL", "kalshi", -3.5, -110, -2.5)
ck("hand-worked max price for crossing 3 matches", close(mx["max_prob"], c_hand, 1e-9), f"{mx['max_prob']} vs {c_hand}")
ck("crossing 3 allows a materially worse price than the alert (more than half a point at 3 is worth)",
   mx["max_am_after_fee"] < -110 - 10, str(mx))

# ---------------------------------------------------------------- 6. unsupported is a labelled answer
e = lv.evaluate(ref(231.5, 0.5, "total", "OVER"), "NBA", "novig", 231.5, -110, 230.5, -118)
ck("NBA total is a prob-points credit (no mass row used, reference ignored)", e["status"] == "ok" and e["method"] == "prob_points"
   and close(e["allowance"], .024343), str(e))   # a FULL point (231.5 -> 230.5) uses the full-point value, not 2x half
e = lv.evaluate(ref(-3.0, 0.5), "NFL", "unlisted_venue", -3.0, -110, -2.5, -120)
ck("whole-number line on a venue with no verified settlement rule -> unsupported", e["status"] == "unsupported"
   and e["reason"] == "settlement_rule_unverified", str(e))
e = lv.evaluate(lv.Reference("spread", 0, -3.5, 0.5, "t", "s", two_sided=False), "NFL", "kalshi", -3.5, -110, -3.5, -110)
ck("a one-sided reference is refused", e["status"] == "unsupported" and e["reason"] == "reference_not_two_sided", str(e))
e = lv.evaluate(lv.Reference("spread", 0, -3.5, 1.2, "t", "s"), "NFL", "kalshi", -3.5, -110, -3.5, -110)
ck("an impossible reference probability is refused", e["status"] == "unsupported", str(e))
e = lv.evaluate(ref(-3.5), "NFL", "kalshi", -3.5, -110, -9.5, -120)
ck("an integer far from the reference line is refused, not extrapolated", e["status"] == "unsupported", str(e))
e = lv.evaluate(lv.Reference("moneyline", 0, 0.0, 0.5, "t", "s"), "NFL", "kalshi", 0.0, -110, 0.0, -110)
ck("moneyline is not modelled here -> unsupported", e["status"] == "unsupported" and e["reason"] == "market_not_supported", str(e))
e = lv.evaluate(ref(5.5, 0.5, "total", "OVER"), "NHL", "novig", 5.5, -110, 6.5, -110)
ck("NHL total is a cents placeholder: a worse line (6.5 over) must be 50c better odds", e["status"] == "ok" and e["method"] == "cents"
   and e["allowance"] == -50.0 and e["max_am_after_fee"] == 140 and e["qualifies"] is False, str(e))

# ---------------------------------------------------------------- 7. provenance on every mass row
for key, row in lv.MASS.items():
    ck(f"{key}: source named", bool(row.source), row.source)
    ck(f"{key}: calculation / label described", bool(row.calc), "")
    ck(f"{key}: 0 < m < 0.5", 0 < row.m < 0.5, str(row.m))
    if key[0] == "NFL":
        ck(f"{key}: measured here - nflverse, dates, n >= MIN_N, binomial se", "nflverse" in row.source and ".." in row.dates
           and row.n >= lv.MIN_N and close(row.se, math.sqrt(row.m * (1 - row.m) / row.n), 1e-12), str(row))
    else:
        ck(f"{key}: published - labelled as not measured here", "published" in row.calc and "not measured here" in row.calc, row.calc)
ck("NFL 14 is not in the table (n=85, too thin)", ("NFL", "spread", 14) not in lv.MASS, "")
ck("NCAAB spread rows keep the exact fractions", close(lv.MASS[("NCAAB", "spread", 3)].m, 87 / 1563) and lv.MASS[("NCAAB", "spread", 3)].hits == 87
   and lv.MASS[("NCAAB", "spread", 3)].n == 1563, "")
ck("NCAAF totals 58-68 have no row (gap kept)", all(("NCAAF", "total", k) not in lv.MASS for k in range(58, 69)) and ("NCAAF", "total", 57) in lv.MASS
   and ("NCAAF", "total", 69) in lv.MASS and ("NCAAF", "total", 46) not in lv.MASS and ("NCAAF", "total", 80) not in lv.MASS, "")
ck("no NBA / NHL / MLB mass rows (those markets use other input types)", not any(k[0] in ("NBA", "NHL", "MLB") for k in lv.MASS), "")

# ---------------------------------------------------------------- 8. de-vig is conditional on no push
q = lv.devig_two_sided(-110, -110)
ck("symmetric two-sided quote de-vigs to 0.5", close(q, 0.5), str(q))
q = lv.devig_two_sided(-130, +110)
ck("de-vig is proportional", close(q, lv.am_to_prob(-130) / (lv.am_to_prob(-130) + lv.am_to_prob(110))), str(q))
# absolute probabilities at a whole-number reference line use the push mass
o = lv.outcomes_at(ref(-3.0, 0.5), "NFL", -3.0)
ck("absolute win at a whole-number reference = q*(1-m)", close(o.w, 0.5 * (1 - M3)), str(o))
ck("absolute push at a whole-number reference = m", close(o.p, M3), str(o))
ck("a half-line reference has no push", lv.outcomes_at(ref(-3.5, 0.5), "NFL", -3.5).p == 0.0, "")

# ---------------------------------------------------------------- 9. thresholds and events
ck("favorite -3 -> c=3", lv.cover_threshold("spread", 0, -3) == 3.0, "")
ck("underdog +3.5 -> c=-3.5", lv.cover_threshold("spread", 1, 3.5) == -3.5, "")
ck("over 44 -> c=44", lv.cover_threshold("total", "OVER", 44) == 44.0, "")
ck("under 44 -> c=-44", lv.cover_threshold("total", "UNDER", 44) == -44.0, "")
ck("a better line is a LOWER c (over 43.5 < over 44)", lv.cover_threshold("total", "OVER", 43.5) < lv.cover_threshold("total", "OVER", 44), "")
ck("a better under line is a LOWER c (under 44.5 < under 44)", lv.cover_threshold("total", "UNDER", 44.5) < lv.cover_threshold("total", "UNDER", 44), "")
ru = lv.Reference("total", "UNDER", 44.5, 0.5, "t", "s")
ow = lv.outcomes_at(ru, "NFL", 43.5)
ck("under 44.5 -> 43.5 loses exactly the total==44 mass of win probability",
   close(lv.outcomes_at(ru, "NFL", 44.5).w - ow.w, lv.MASS[("NFL", "total", 44)].m), f"{ow}")
ck("version string is set", lv.CALC_VERSION == "line_value/v2", "")
ck("prob_to_am / am_to_prob round-trip", all(abs(lv.am_to_prob(lv.prob_to_am(c)) - c) < 1e-9 for c in (0.1, 0.4, 0.5, 0.52, 0.6, 0.9)), "")
ck("matches executor.american_to_prob", all(close(lv.am_to_prob(a), ex.american_to_prob(a)) for a in (-300, -130, -110, -100, 100, 105, 250)), "")

# ---------------------------------------------------------------- 10. requirements() describes any move without a reference
rq = lv.requirements("NFL", "spread", 0, -3.5, -2.5, "kalshi")
ck("half->half across 3 needs the mass of 3 and no settlement rule",
   rq["crossed"] == [3] and rq["mass_ok"] and rq["settlement"] == "n/a" and not rq["reasons"], str(rq))
rq = lv.requirements("NFL", "spread", 0, -3.5, -3.0, "kalshi")
ck("half->whole needs a settlement rule: unverified venue is flagged",
   rq["settlement"] == "unverified" and "settlement_rule_unverified" in rq["reasons"], str(rq))
rq = lv.requirements("NFL", "spread", 0, -3.5, -3.0, "testbook")
ck("verified refund venue clears the settlement flag", rq["settlement"] == "refund", str(rq))
rq = lv.requirements("NBA", "total", "OVER", 231.5, 230.5, "novig")
ck("NBA total move: crossed integer 231 reported, no mass row", rq["crossed"] == [231] and not rq["mass_ok"]
   and "no_mass_row:231" in rq["reasons"], str(rq))
rq = lv.requirements("NFL", "total", "UNDER", 44.5, 45.5, "novig")
ck("under 44.5 -> 45.5 crosses total 45 (event integer is the TOTAL)", rq["crossed"] == [45] and rq["mass_ok"], str(rq))

# ---- settlement evidence is evidence, not activation (Nov 12)
ck("S1 no settlement rule is ACTIVE on any real venue", lv.SETTLEMENT == {} or set(lv.SETTLEMENT) <= {"testbook"}, str(lv.SETTLEMENT))
ck("S2 every evidence row names venue, rule, status, finding and a source or says not read",
   all(e["book"] and e["rule"] and e["status"] and e["finding"] and (e["source"] or e["status"] == "not_read") for e in lv.SETTLEMENT_EVIDENCE))
ck("S3 no evidence row is marked verified beyond 'summary_read' (no original-text confirmation yet)",
   all(e["status"] in ("summary_read", "unconfirmed_for_mainline", "not_read", "not_found") for e in lv.SETTLEMENT_EVIDENCE))
ck("S4 Novig is never assumed to refund (voids settle at fair value)", not any(e["book"] == "novig" and e["rule"] == "refund" for e in lv.SETTLEMENT_EVIDENCE))
for bk in ("novig", "kalshi", "polymarket_us", "prophetx"):
    try:
        lv.push_ok(bk, 3.0, "NFL", "spread"); ok_ = False
    except lv.Unsupported as u:
        ok_ = u.code == "settlement_rule_unverified"
    ck(f"S5 a whole-number line on {bk} is unsupported until a refund rule is ACTIVATED", ok_)
ck("S6 half lines never need a rule", lv.push_ok("novig", 214.5, "NBA", "total") is True)
lv.SETTLEMENT[("prophetx", "NCAAB", "spread")] = "refund"
ck("S7 a sport-specific activation applies to that class only",
   lv.push_ok("prophetx", 5.0, "NCAAB", "spread") is True and lv.requirements("NFL", "spread", 0, -2.5, -3.0, "prophetx")["settlement"] == "unverified")
del lv.SETTLEMENT[("prophetx", "NCAAB", "spread")]
# ---- per-total rows, no pooled fallback, line-distance guard (Nov 12)
ck("T1 the pooled whole-total fallback is gone", ("NFL", "total", "*") not in lv.MASS and lv.mass_row("NFL", "total", 37) is None)
ck("T2 supported NFL totals are exactly those with n >= 200 of their own", sorted(k[2] for k in lv.MASS if k[:2] == ("NFL", "total")) == [41, 42, 43, 44, 45, 46, 47])
for tot in (37, 40, 48, 51):
    rq = lv.requirements("NFL", "total", "OVER", tot - 0.5, tot + 0.5, "novig")
    ck(f"T3 total {tot} (n < 200) is unsupported, not pooled", not rq["mass_ok"] and f"no_mass_row:{tot}" in rq["reasons"], str(rq))
ck("T4 every row's share is hits/n and its se is binomial", all(abs(r.m - r.hits / r.n) < 1e-12 and abs(r.se - math.sqrt(r.m * (1 - r.m) / r.n)) < 1e-12 for k, r in lv.MASS.items() if k[0] == "NFL"))
ck("T5 each row states its own first..last dates and the conditioning rule", all(".." in r.dates and r.dates != "" and "closing line is exactly" in r.calc for k, r in lv.MASS.items() if k[0] == "NFL"))
rq = lv.requirements("NFL", "total", "OVER", 44.5, 47.5, "novig")
ck("T6 a mass row far from the quoted line is refused (no extrapolation) for totals too", not rq["mass_ok"] and any(r.startswith("mass_far_from_line") for r in rq["reasons"]), str(rq))
try:
    lv.outcomes_at(lv.Reference("total", "OVER", 44.5, 0.5, "t", "s"), "NFL", 47.5); far = False
except lv.Unsupported as u:
    far = u.code == "mass_far_from_line"
ck("T7 outcomes_at refuses the same far move", far)
ck("T8 spread rows still reproduce the verified values", [round(lv.MASS[("NFL", "spread", k)].m, 4) for k in (1, 3, 4, 6, 7, 10)] == [0.0131, 0.0921, 0.0247, 0.0381, 0.0690, 0.0686])
print(f"{len(OK)} passed, {len(BAD)} failed")
for b in BAD:
    print("FAIL:", b)
sys.exit(1 if BAD else 0)
