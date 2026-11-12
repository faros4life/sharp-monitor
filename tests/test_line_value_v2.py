"""Nov 12 (Peter's consolidated values): the three input types, one shared convert(), explicit unsupported cases."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex  # noqa: E402  (only for cents_worse, the tolerance function the legacy rule uses)
import line_value as lv  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


def close(a, b, t=1e-6):
    return a is not None and b is not None and abs(a - b) < t


W = ex.cents_worse
lv.SETTLEMENT["vb"] = "refund"      # a venue with a VERIFIED refund rule, for whole-number tests only
C = lambda *a, **k: lv.convert(*a, **k)

# ---- 1. three input types never mixed
r = C("NBA", "spread", 0, -2.5, -110, -2.0, None, "vb")
ck("1 NBA spread half point: prob points 0.020604, stored as probability", r["method"] == "prob_points" and r["input_type"] == "probability points"
   and close(r["allowance"], .020604) and close(r["max_prob"], lv.am_to_prob(-110) + .020604), str(r))
r = C("NHL", "total", "OVER", 5.5, -110, 5.0, None, "vb")
ck("1 NHL total half goal: 25 CENTS, -110 -> -135 (not a probability)", r["method"] == "cents" and r["input_type"] == "American-odds cents"
   and r["allowance"] == 25.0 and r["max_am_after_fee"] == -135, str(r))
ref = lv.Reference("spread", 0, -3.5, 0.5, "t", "pinnacle")
r = C("NFL", "spread", 0, -3.5, -110, -2.5, None, "vb", ref=ref)
ck("1 NFL: landing mass through win/push/loss, needs the reference", r["method"] == "mass" and r["input_type"] == "landing mass"
   and r["status"] == "ok" and "w" in r and r["reference"]["source"] == "pinnacle", str(r))
r = C("NFL", "spread", 0, -3.5, -110, -2.5, None, "vb")
ck("1 NFL without a reference is unsupported/no_reference (never a constant)", r["status"] == "unsupported" and r["reason"] == "no_reference")
ck("1 every registry entry records source, input type and status", all(v.get("source") and v.get("input_type") and v.get("status") for v in lv.VALUES.values()))
ck("1 every record carries method, source, lines, prices, allowance, assumptions and calc",
   all(k in r for k in ("method", "source", "alert_line", "alert_am_after_fee", "cand_line", "allowance", "assumptions", "calc")))

# ---- 2. favourable and unfavourable moves, exact start/end, signed margins
f = C("NBA", "spread", 0, -2.5, -110, -1.5, -128, "vb")      # favourite's line improves by a point
u = C("NBA", "spread", 0, -1.5, -110, -2.5, -100, "vb")      # the reverse: worsens
ck("2 favourable full point: +4.1479 pts, -110 may pay up to about -130", close(f["allowance"], .041479) and -131 < f["max_am_after_fee"] < -129, str(f))
ck("2 unfavourable full point: -4.1479 pts, needs better than -110", close(u["allowance"], -.041479) and u["max_am_after_fee"] > -100 + 5, str(u))
ck("2 -128 qualifies on the favourable move; -100 does not on the unfavourable one", f["qualifies"] is True and u["qualifies"] is False)
d = C("NBA", "spread", 1, 2.5, -110, 3.5, -128, "vb")        # underdog: +2.5 -> +3.5 is the favourable direction
ck("2 signed: the underdog's favourable move is UP (+2.5 -> +3.5)", close(d["allowance"], .041479), str(d))
d2 = C("NBA", "spread", 1, 3.5, -110, 2.5, -128, "vb")
ck("2 signed: +3.5 -> +2.5 is unfavourable for the underdog", close(d2["allowance"], -.041479), str(d2))
o = C("NBA", "total", "UNDER", 214.5, -110, 215.5, -115, "vb")
ck("2 under: 214.5 -> 215.5 is favourable (+2.4343 pts)", close(o["allowance"], .024343), str(o))
ck("2 full point used directly, not 2x half (NBA spread 4.1479 != 2 x 2.0604)", not close(.041479, 2 * .020604, 1e-4))

# ---- 3. half-step vs full-step, placeholders
ck("3 MLB total full run is 41.5c, not 2 x 20", C("MLB", "total", "OVER", 8.5, -110, 7.5, None, "vb")["allowance"] == 41.5)
ck("3 NHL full goal is 50c", C("NHL", "total", "OVER", 6.5, -110, 5.5, None, "vb")["allowance"] == 50.0)
g = C("NHL", "spread", 0, -1.5, 120, -0.5, 100, "vb")
ck("3 generic full-point puck line (-1.5 -> -0.5) is unsupported, NOT the ML conversion", g["status"] == "unsupported" and g["reason"] == "generic_full_point_not_supplied", str(g))
h = C("NHL", "spread", 0, -1.5, 120, -1.0, 100, "vb")
ck("3 half-goal puck line is 37.5c on a venue with a verified refund rule", h["status"] == "ok" and h["allowance"] == 37.5, str(h))
h2 = C("NHL", "spread", 0, -1.5, 120, -1.0, 100, "novig")
ck("3 ...and unsupported on a venue whose tie rule is unverified (placeholder does not establish settlement)",
   h2["status"] == "unsupported" and h2["reason"] == "settlement_rule_unverified", str(h2))
m = C("MLB", "moneyline", 0, None, -150, -1.5, 115, "novig")
ck("3 MLB ML -> -1.5 is the specific 65c: -150 -> must be +115 or better", m["status"] == "ok" and m["allowance"] == -65.0 and m["max_am_after_fee"] == 115 and m["qualifies"] is True, str(m))
m2 = C("NHL", "moneyline", 1, None, 130, 1.5, -140, "novig")
ck("3 NHL dog ML +130 -> +1.5 may pay 80c: up to -150", m2["allowance"] == 80.0 and m2["max_am_after_fee"] == -150 and m2["qualifies"] is True, str(m2))
ck("3 cents placeholders are labelled Peter-approved placeholder assumptions", all("placeholder" in lv.VALUES[k]["status"] for k in (("NHL", "total"), ("NHL", "spread"), ("MLB", "total"), ("MLB", "spread"))))

# ---- 4. even-money crossing and identical outcomes
e = C("MLB", "total", "OVER", 8.5, 110, 8.0, None, "vb")
ck("4 +110 less 20c crosses even money to -110", e["max_am_after_fee"] == -110, str(e))
e = C("MLB", "total", "OVER", 8.5, 105, 8.0, None, "vb")
ck("4 +105 less 20c: 5c to even, 15c past -> -115", e["max_am_after_fee"] == -115, str(e))
ck("4 cents_of(+100) == cents_of(-100) == 0", lv.cents_of(100) == 0 and lv.cents_of(-100) == 0)
i = C("NHL", "spread", 0, -0.5, -150, 0.0, -150, "vb")
ck("4 NHL -0.5 vs pick-em: identical winning outcomes -> zero credit", i["status"] == "ok" and i["allowance"] == 0.0 and i["qualifies"] is True
   and "identical" in " ".join(i["assumptions"]), str(i))
z = C("NBA", "spread", 0, -1.5, -110, 0.5, -110, "vb")
ck("4 NBA move across zero is unsupported (sample excludes it)", z["status"] == "unsupported" and z["reason"] == "crosses_zero", str(z))
f3 = C("NBA", "spread", 0, -2.5, -110, -4.0, -110, "vb")
ck("4 a 1.5-point move has no listed value -> unsupported", f3["status"] == "unsupported" and f3["reason"] == "move_size_not_listed", str(f3))

# ---- 5. NCAAF spreads: exact listed pairs only
t = C("NCAAF", "spread", 0, -3.0, -110, -2.5, None, "vb")
ck("5 -3 -> -2.5 is 3.4178 pts", close(t["allowance"], .034178), str(t))
t = C("NCAAF", "spread", 0, -3.0, -110, -2.0, None, "vb")
ck("5 -3 -> -2 is 4.5551 pts from the ORIGINAL spread (not 3.4178 + anything)", close(t["allowance"], .045551), str(t))
t = C("NCAAF", "spread", 1, 7.0, -110, 8.0, None, "vb")
ck("5 +7 -> +8 is 3.7874 pts", close(t["allowance"], .037874), str(t))
t = C("NCAAF", "spread", 0, -2.5, -110, -2.0, None, "vb")
ck("5 an unlisted start (-2.5) is unsupported, never extended", t["status"] == "unsupported" and t["reason"] == "pair_not_in_table", str(t))
t = C("NCAAF", "spread", 0, -2.5, -110, -3.0, None, "vb")
ck("5 walking a listed pair backwards removes the same credit", close(t["allowance"], -.034178) and "reverse" in " ".join(t["assumptions"]), str(t))

# ---- 6. NCAAF totals gap, NCAAB totals parity and the ambiguous 161, NCAAB spreads
rt = lambda ln: lv.Reference("total", "OVER", ln, 0.5, "t", "pinnacle")
g = C("NCAAF", "total", "OVER", 60.5, -110, 59.5, -120, "vb", ref=rt(60.5))
ck("6 NCAAF total crossing 60 (in the 58-68 gap) is unsupported/no_mass_row", g["status"] == "unsupported" and g["reason"] == "no_mass_row", str(g))
g = C("NCAAF", "total", "OVER", 55.5, -110, 54.5, -120, "vb", ref=rt(55.5))
ck("6 NCAAF total crossing 55 uses the published 4.5%", g["status"] == "ok" and close(g["w"] - 0.5, .045), str(g))
b = C("NCAAB", "total", "OVER", 161.5, -110, 160.5, -120, "vb", ref=rt(161.5))
ck("6 NCAAB total at 161 returns source_boundary_ambiguous", b["status"] == "unsupported" and b["reason"] == "source_boundary_ambiguous", str(b))
b = C("NCAAB", "total", "OVER", 140.5, -110, 139.5, -120, "vb", ref=rt(140.5))
ck("6 NCAAB total crossing 140 (even, 137-152) uses 2.1%", b["status"] == "ok" and close(b["w"] - 0.5, .021), str(b))
b = C("NCAAB", "total", "OVER", 141.5, -110, 140.5, -120, "vb", ref=rt(141.5))
ck("6 NCAAB total crossing 141 (odd, 137-152) uses 2.4%", b["status"] == "ok" and close(b["w"] - 0.5, .024), str(b))
b = C("NCAAB", "total", "OVER", 180.5, -110, 179.5, -120, "vb", ref=rt(180.5))
ck("6 NCAAB total beyond the listed ranges is unsupported", b["status"] == "unsupported" and b["reason"] == "no_mass_row", str(b))
s = C("NCAAB", "spread", 0, -3.5, -110, -2.5, -125, "vb", ref=lv.Reference("spread", 0, -3.5, 0.5, "t", "pinnacle"))
ck("6 NCAAB spread crossing 3 uses 87/1563 and is labelled an approximation off the exact closing line",
   s["status"] == "ok" and close(s["w"] - 0.5, 87 / 1563) and any("approximation" in a for a in s["assumptions"]), str(s))

# ---- 7. whole-number settlement and fees once
w = C("NFL", "spread", 0, -3.5, -110, -3.0, -120, "novig", ref=ref)
ck("7 whole-number endpoint on an unverified exchange is unsupported (a sportsbook refund proves nothing)", w["status"] == "unsupported" and w["reason"] == "settlement_rule_unverified")
w = C("NFL", "spread", 0, -3.5, -110, -3.0, -120, "vb", ref=ref)
ck("7 ...and valued on a venue with a verified refund rule, with the push mass of 3 explicit", w["status"] == "ok" and close(w["p"], lv.MASS[("NFL", "spread", 3)].m), str(w))
src = open(lv.__file__).read()
ck("7 no fee code in the calculation (prices arrive after fees, once)", "WIN_FEE" not in src and "taker" not in src.lower().replace("taker fee", ""))

# ---- 8. selection, max price and recheck agree (same function, same bar)
for sport, mt, sd, a, c, bk, rf in (("NBA", "spread", 0, -2.5, -1.5, "vb", None), ("NHL", "total", "OVER", 5.5, 5.0, "vb", None),
                                     ("NFL", "spread", 0, -3.5, -2.5, "vb", ref), ("NCAAF", "spread", 0, -3.0, -2.5, "vb", None)):
    for tol in (0, 2):
        mx = C(sport, mt, sd, a, -110, c, None, bk, tol, W, rf)
        at = C(sport, mt, sd, a, -110, c, mx["max_am_after_fee"], bk, tol, W, rf)
        past = C(sport, mt, sd, a, -110, c, mx["max_am_after_fee"] - 1 if mx["max_am_after_fee"] < 0 else mx["max_am_after_fee"] - 1, bk, tol, W, rf)
        ck(f"8 {sport} tol={tol}: the max price qualifies and 1c past it does not", at["qualifies"] is True and past["qualifies"] is False, f"{mx['max_am_after_fee']} {at['qualifies']} {past['qualifies']}")

# ---- 9. incoherent results are rejected, not clipped
bad = C("NBA", "spread", 0, -2.5, -5000, -1.5, None, "vb")
ck("9 a credit that would push the cost past 1 is rejected as incoherent", bad["status"] == "unsupported" and bad["reason"] == "incoherent_probability", str(bad))
ck("9 unknown market is a named unsupported", C("MLB", "team_total", 0, 4.5, -110, 4.0, None, "vb")["reason"] == "market_not_supported")

print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
