"""Synthetic tests: only genuine, unique, total-market Pinnacle certifications reach LIQ-SMALL / LIQ-BOT. No network."""
import json, os, sys, tempfile
os.environ.setdefault("TRACKER_PASSPHRASE", "synthetic-test-only")
import liq_clv_certify as lc
import last50_report as L
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
base = {"result": "W", "league": "NBA", "market": "total", "lead_min": 300, "new_money": 10000, "game": "A @ B", "alerted_utc": "2026-11-10T00:00:00Z"}
X = [dict(base, key="k1"), dict(base, key="k2"), dict(base, key="k3"), dict(base, key="k4"), dict(base, key="k5"), dict(base, key="k5")]
CLS = {"k1": ("VERIFIED_PINNACLE", {"clv": 0.012, "fid": "f1", "how": "own line", "age_min": 3, "entry": 1.9}),
       "k2": ("NO_SAME_LINE_QUOTE", "no Pinnacle quote at that line"),
       "k3": ("VERIFIED_PINNACLE", {"clv": 0.02, "fid": "f3", "how": "own line", "age_min": None, "entry": 1.9}),
       "k4": ("VERIFIED_PINNACLE", {"clv": 0.02, "fid": "f4", "how": "moneyline", "age_min": 2, "entry": 1.9}),
       "k5": ("VERIFIED_PINNACLE", {"clv": 0.02, "fid": "f5", "how": "own line", "age_min": 2, "entry": 1.9})}
KIND = {"k4": "ml"}
cert, rej = lc.certify(X, lambda x: CLS[x["key"]], lambda x: KIND.get(x["key"], "total"))
ids = lambda k: f"{k}|2026-11-10T00:00:00Z"
check("a verified same-line Pinnacle close is certified, as a percent", ids("k1") in cert and cert[ids("k1")]["clv_pct"] == 1.2, cert)
check("no same-line Pinnacle quote -> rejected with its class", rej.get(ids("k2"), "").startswith("NO_SAME_LINE_QUOTE"))
check("no recorded quote time -> rejected (timing)", rej.get(ids("k3"), "").startswith("TIMING"))
check("a bet that is not a total -> rejected (market)", rej.get(ids("k4"), "").startswith("MARKET"))
check("a duplicated alert id -> both rejected as ambiguous", rej.get(ids("k5"), "").startswith("AMBIGUOUS") and ids("k5") not in cert)
check("scope: Kalshi-style non-NBA or non-total rows excluded", not lc.in_scope(dict(base, league="NHL")) and not lc.in_scope(dict(base, market="spread")))
check("scope: LIQ-SMALL rows (25-50k) included even under 4h lead", lc.in_scope(dict(base, lead_min=30, new_money=30000)))
check("scope: suspect closes excluded", not lc.in_scope(dict(base, close_suspect=True)))
# integration into Last 50
tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
json.dump({"certified": {ids("k1"): {"clv_pct": 1.2}}}, tmp); tmp.close()
rows = [{"aid": ids("k1"), "clv": None, "pclv": 3.0, "res": "W", "am": -110}, {"aid": ids("k2"), "clv": None, "pclv": 2.0, "res": "L", "am": -110}]
out = L.liq_certified(rows, tmp.name)
check("only certified ids receive certified CLV", out[0]["clv"] == 1.2 and out[1]["clv"] is None)
check("the venue close stays provisional, never promoted", out[0]["pclv"] == 3.0 and out[1]["pclv"] == 2.0)
check("inputs are not mutated", rows[0]["clv"] is None)
check("W-L and units are unchanged by certification", L.half_stats(out)["units"] == L.half_stats(rows)["units"])
check("missing certified file -> nothing certified", all(r["clv"] is None for r in L.liq_certified(rows, "/nonexistent.json")))
src = open("last50_report.py").read()
check("Kalshi NBA unders is NOT given certified values (out of scope for now)",
      'liq_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"\n                                                     and r["side"] == "UNDER"' not in src)
check("the certify job holds no API key and calls no network", "ODDSPAPI" not in open(".github/workflows/liq-clv-certify.yml").read()
      and "urlopen" not in open("liq_clv_certify.py").read() and "api(" not in open("liq_clv_certify.py").read())
os.unlink(tmp.name)
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_liq_clv_certify: all passed")
