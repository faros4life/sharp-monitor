"""Regression: provisional closes can never appear under a certified-CLV heading (Peter, 16 Nov). No network."""
import sys
import last50_report as L
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
A = [{"result": "W", "sent_to_phone": True, "price": -110, "price_after_fee": -110, "close_fair_prob": 0.56,
      "book_key": "novig", "alert_utc": "2026-11-10T00:00:00Z", "game": "A @ B", "sport": "NBA", "kind": "tot",
      "bet": "Under 220", "clv_verified": False, "edge_pct": 3},
     {"result": "L", "sent_to_phone": True, "price": -110, "price_after_fee": -110, "close_fair_prob": 0.56,
      "book_key": "novig", "alert_utc": "2026-11-11T00:00:00Z", "game": "C @ D", "sport": "NBA", "kind": "tot",
      "bet": "Under 221", "clv_verified": True, "edge_pct": 3}]
Q = [{"result": "W", "price_american": -110, "close_price": 0.6, "book": "kalshi", "alerted_utc": "2026-11-10T00:00:00Z",
      "game": "E @ F", "league": "NBA", "market": "total", "side": "UNDER", "lead_min": 300, "new_money": 30000}]
orig = L.load
L.load = lambda name: {"alerts.json": A, "liquidity/alerts.json": Q}.get(name)
try:
    S = L.sharp_rows(); M = L.misprice_rows(); LQ = L.liq_rows()
finally:
    L.load = orig
check("a live feed read (clv_verified False) is NOT certified", S[0]["clv"] is None and S[0]["pclv"] is not None)
check("only clv_verified True reaches certified CLV", S[1]["clv"] is not None and S[1]["pclv"] is None)
check("Exchange Misprice obeys the same rule", any(r["clv"] is None and r["pclv"] is not None for r in M))
check("a venue's own close is never certified Pinnacle CLV", LQ[0]["clv"] is None and LQ[0]["pclv"] is not None
      and "not Pinnacle" in LQ[0]["pclv_src"])
h = L.half_stats(S)
check("half_stats certified CLV uses certified rows only", h["clv_n"] == 1 and h["pclv_n"] == 1)
check("units do not depend on CLV fields", L.half_stats([dict(r, clv=None, pclv=None) for r in S])["units"] == h["units"])
w = [dict(S[0], res="W")] * 50
hh = L.half_stats(w)
check("no certified CLV -> INSUFFICIENT EVIDENCE, never a pass", L.verdict(w, hh, hh, hh).startswith("INSUFFICIENT EVIDENCE"))
check("confidence counts certified coverage only", L.confidence(hh["n"], hh["clv_n"]) == "LOW")
check("the text line labels provisional values NOT certified", "provisional, NOT certified" in L.fmt(h) and "CERTIFIED CLV" in L.fmt(h))
tpl = open("last50_page.html").read()
check("page headings say Certified CLV", "<th>Certified CLV (coverage)</th>" in tpl and "<th>Certified CLV</th>" in tpl)
check("provisional values have their own labelled column", tpl.count("Provisional, NOT certified") >= 2)
check("no bare 'CLV' column heading remains", "<th>CLV</th>" not in tpl and "<th>CLV (coverage)</th>" not in tpl)
check("the page explains the correction", "Corrected 16 Nov 2026" in tpl)
src = open("last50_report.py").read()
lines = src.splitlines()
idx = [i for i, l in enumerate(lines) if "sc.std_clv(" in l]
check("every computed close is routed through a certification check or into the provisional field",
      len(idx) >= 3 and all(any("pclv" in l for l in lines[i:i + 6]) for i in idx), idx)
check("SLOW-HR's uncertified close is provisional too", '"clv": None, "pclv": clv' in src)
neg = [dict(S[0], res="W", clv=-2.0 + (i % 3) * 0.1) for i in range(50)]
hn = L.half_stats(neg)
check("representative certified CLV with a CI below zero -> CLEAR FAIL", L.verdict(neg, hn, hn, hn).startswith("CLEAR FAIL"))
thin = [dict(r, clv=None) if i >= 39 else r for i, r in enumerate(neg)]
ht = L.half_stats(thin)
check("the same negative CLV on only 39/50 -> INSUFFICIENT EVIDENCE, not a fail", L.verdict(thin, ht, ht, ht).startswith("INSUFFICIENT"))
# --- CLV_STANDARD.md s7 denominator consistency (16 Nov) ---
src7 = open("last50_report.py").read()
check("every 80% coverage test uses the executable denominator (no bare 0.8 * n left)",
      "0.8 * ho[\"n\"]" not in src7 and "0.8 * h[\"n\"]" not in src7 and src7.count("exec_n") >= 6)
bot = [dict(S[0], res="W" if i % 2 else "L", clv=-2.0 - (i % 4) * 0.3, us_exec=True) for i in range(39)]
bot += [dict(S[0], res="W", clv=None, us_exec=True)]                       # 1 executable, history missing
bot += [dict(S[0], res="L", clv=None, us_exec=False) for _ in range(10)]   # 10 Polymarket Global
hb = L.half_stats(bot)
check("s7: coverage is 39/40 executable, whole population 39/50", hb["clv_n"] == 39 and hb["exec_n"] == 40 and hb["n"] == 50)
check("s7: a negative certified CI on 39/40 executable -> CLEAR FAIL", L.verdict(bot, hb, hb, hb).startswith("CLEAR FAIL"))
check("s7: confidence uses the same denominator", L.confidence(hb["n"], hb["clv_n"], hb["exec_n"]) == "HIGH"
      and L.confidence(hb["n"], hb["clv_n"]) == "MEDIUM")
check("the missing-history play is NOT assumed: it stays uncertified and inside the denominator",
      sum(1 for r in bot if r["clv"] is None and r["us_exec"]) == 1 and hb["exec_n"] == 40)
check("executable subset W-L excludes the non-executable plays",
      hb["exec_w"] + hb["exec_l"] == 40 and hb["w"] + hb["l"] == 50)
check("both coverage figures are printed when they differ", "39/40 US-executable" in L.fmt(hb) and "39/50 whole population" in L.fmt(hb))
plain = L.half_stats([dict(r) for r in S])
check("a test with no executability marks keeps n as its denominator", plain["exec_n"] == plain["n"])
import json as _j, tempfile as _tf, os as _os
tf = _tf.NamedTemporaryFile("w", suffix=".json", delete=False)
_j.dump({"certified": {}, "rejected": {"a|1": "VENUE_NOT_PRICEABLE: polymarket is not tradeable from the US (x)",
                                       "b|1": "MISSING_HISTORY: fixture f has no cached Pinnacle history",
                                       "c|1": "VENUE_NOT_PRICEABLE: venue not in the venue registry"}}, tf); tf.close()
mk = {r["aid"]: r for r in L.liq_certified([{"aid": a, "clv": None, "pclv": 1.0, "res": "W", "am": -110} for a in ("a|1", "b|1", "c|1")], tf.name)}
_os.unlink(tf.name)
check("only 'not tradeable from the US' leaves the denominator", mk["a|1"]["us_exec"] is False and mk["b|1"]["us_exec"] is True
      and mk["c|1"]["us_exec"] is True)
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_last50_certified: all passed")
