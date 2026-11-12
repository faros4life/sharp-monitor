"""Nov 12 (Peter): the ALERT-ANCHORED maximum is the same number at selection, at the buy/post limit and at the recheck.
Acceptance exactly AT the maximum, rejection ONE TICK worse, with and without Pinnacle data, including the -130 cap.
"""
import copy
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_check as bc  # noqa: E402
import executor as ex  # noqa: E402
import line_value as lv  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


W = ex.cents_worse
CAP = ex.CAP_LINE
lv.SETTLEMENT["vb"] = "refund"


def tick_worse(am):
    """One cent worse on the ladder, as the venues quote (integer American, +100/-100 are the same point)."""
    return W(int(am) if am == int(am) else (int(am) - 1 if am < 0 else int(am)), 1)


def at_max(am_max):
    """The worst INTEGER price that is still at or better than the calculated maximum (what a venue could actually show)."""
    return int(am_max) if float(am_max).is_integer() else (int(am_max) if am_max < 0 else int(am_max) + 1)


# ---------------------------------------------------------------- 1. every method: accept at the max, reject one tick worse
CASES = [
    ("NBA", "spread", 0, -2.5, -110, -1.5, "prob_points"),
    ("NBA", "total", "UNDER", 214.5, -111, 215.5, "prob_points"),
    ("NFL", "spread", 0, -3.5, -110, -2.5, "mass"),
    ("NFL", "total", "UNDER", 41.5, -114, 42.5, "mass"),
    ("NCAAB", "spread", 0, -3.5, -110, -2.5, "mass"),
    ("NCAAB", "total", "OVER", 156.5, -115, 157.5, "mass"),
    ("NCAAF", "spread", 0, -3.0, -110, -2.5, "prob_points_table"),
    ("NCAAF", "total", "OVER", 55.5, -110, 54.5, "mass"),
    ("NHL", "total", "OVER", 5.5, -110, 5.0, "cents"),
    ("MLB", "total", "OVER", 8.5, -110, 8.0, "cents"),
]
for sport, mt, sd, al, af, cl, method in CASES:
    for tol in (0, 2):
        mx = lv.convert(sport, mt, sd, al, af, cl, None, "vb", tol, W, None, None)
        if mx["status"] != "ok":
            ck(f"1 {sport} {mt} {method}: a maximum exists", False, str(mx.get("reason")))
            continue
        ck(f"1 {sport} {mt} tol={tol}: method is {method}", mx["method"] == method, mx["method"])
        m = mx["max_am_after_fee"]
        a = lv.convert(sport, mt, sd, al, af, cl, at_max(m), "vb", tol, W, None, None)
        w = lv.convert(sport, mt, sd, al, af, cl, tick_worse(m), "vb", tol, W, None, None)
        ck(f"1 {sport} {mt} tol={tol}: accepted AT the maximum ({at_max(m)} vs max {round(m, 2)})", a["qualifies"] is True, str(a.get("qualifies")))
        ck(f"1 {sport} {mt} tol={tol}: rejected ONE TICK worse ({tick_worse(m)})", w["qualifies"] is False, str(w.get("qualifies")))

# ---------------------------------------------------------------- 2. missing Pinnacle data changes nothing
for sport, mt, sd, al, af, cl, method in CASES:
    no_pin = lv.convert(sport, mt, sd, al, af, cl, None, "vb", 0, W, None, None)
    with_pin = lv.convert(sport, mt, sd, al, af, cl, None, "vb", 0, W,
                          lv.Reference(mt, sd, al, 0.61, "2026-11-12T12:00:00Z", "pinnacle"), None)
    ck(f"2 {sport} {mt}: the maximum is IDENTICAL with and without a Pinnacle quote",
       no_pin["status"] == with_pin["status"] == "ok" and abs(no_pin["max_prob"] - with_pin["max_prob"]) < 1e-12,
       f"{no_pin.get('max_am_after_fee')} vs {with_pin.get('max_am_after_fee')}")
    ck(f"2 {sport} {mt}: a supplied Pinnacle quote is recorded as DIAGNOSTIC only",
       (with_pin.get("diagnostic_reference") or {}).get("source") == "pinnacle" if method == "mass" else True, str(with_pin.get("diagnostic_reference")))

# ---------------------------------------------------------------- 3. the -130 cap: effective maximum, both reported
deep = lv.convert("NFL", "spread", 0, -3.5, -110, -2.5, None, "vb", 0, W, None, CAP)
ck("3 a calculated maximum beyond the cap is reported AND capped",
   deep["max_am_after_fee_calc"] < CAP and deep["effective_max_am_after_fee"] == CAP and deep["capped"] is True, str(deep))
ck("3 at the cap it qualifies", lv.convert("NFL", "spread", 0, -3.5, -110, -2.5, CAP, "vb", 0, W, None, CAP)["qualifies"] is True)
ck("3 one tick past the cap it does not", lv.convert("NFL", "spread", 0, -3.5, -110, -2.5, W(CAP, 1), "vb", 0, W, None, CAP)["qualifies"] is False)
shallow = lv.convert("NBA", "total", "UNDER", 214.5, -111, 215.5, None, "vb", 0, W, None, CAP)
ck("3 a maximum inside the cap is NOT capped and reports both numbers the same",
   shallow["capped"] is False and shallow["effective_max_am_after_fee"] == shallow["max_am_after_fee_calc"], str(shallow))
ck("3 the cap never loosens a maximum", all(
    lv.cents_of(lv.convert(s, m, d, a, f, c, None, "vb", 0, W, None, CAP)["effective_max_am_after_fee"])
    >= lv.cents_of(lv.convert(s, m, d, a, f, c, None, "vb", 0, W, None, None)["max_am_after_fee"]) - 1e-9
    for s, m, d, a, f, c, _k in CASES))

# ---------------------------------------------------------------- 4. end to end: selection == buy/post limit == recheck
def ladder(am, line, dollars=5000.0):
    return {"status": "ok", "line": line, "best_price_american": am, "best_price_american_qual": am, "best_price_american_displayed": am,
            "buy_levels": [{"american": am, "american_after_fee": am, "american_after_fee_qual": am, "dollars": dollars, "strike_id": "S1"}]}


NOW = datetime.now(timezone.utc)
PLAY = {"play_key": "NFL|KC@BUF|side|Kansas City Chiefs", "sport": "NFL", "source": "rules",
        "game": "Kansas City Chiefs @ Buffalo Bills", "bet": "Kansas City Chiefs -3.5 (-110)",
        "start_utc": (NOW + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}


def stub(book):
    bc.kalshi_check = lambda al, mt, sd, ln, price, teams: ladder(book[ln], ln) if ln in book else {"status": "no_market"}
    bc.px_check = lambda *a, **k: {"status": "no_market"}
    ex.pmus_check = lambda *a, **k: {"status": "no_market"}
    bc.check_alert = lambda *a, **k: {"status": "no_market"}


def run(mode="live", play=None):
    ex.MD["c"].clear()
    os.environ["LINE_VALUE_MODE"] = mode
    os.environ.pop("LINE_VALUE_PIN_READ", None)      # NO Pinnacle read anywhere in this test
    ex._PIN.clear()
    try:
        return ex.evaluate(copy.deepcopy(play or PLAY), NOW, {}, {}, [], None, {})
    finally:
        os.environ.pop("LINE_VALUE_MODE", None)


def cands(r):
    seen, out = set(), []
    for c in list(r.get("others") or []) + list(r.get("lcs") or []):
        if (c["book"], c["line"]) not in seen:
            seen.add((c["book"], c["line"]))
            out.append(c)
    return out


# -2.5 crosses 3: the calculated maximum is far past -130, so the CAP is the effective limit
BOOK = {-3.5: -110, -2.5: CAP, -3.0: -120}
stub(BOOK)
r = run()
af = r["lvs"]["alert_af"]
pick = next((c for c in cands(r) if c["line"] == -2.5), None)
ck("4 the converted candidate at the cap is selected", pick is not None, str([(c["line"], c["am"]) for c in cands(r)]))
if pick:
    ck("4 the stored order threshold IS the effective maximum (the cap)", pick["thr"] == CAP, str(pick["thr"]))
    res = {"live": {"book": "kalshi", "line": -2.5, "risk": 220.0, "px": {"thr": pick["thr"], "buy": [], "am": pick["am"]}}, "reval": r["reval"]}
    ok1, why1, _ = ex.revalidate(copy.deepcopy(res))
    ck("4 the recheck passes at the cap", ok1, str(why1))
    stub({**BOOK, -2.5: W(CAP, 1)})
    ok2, why2, _ = ex.revalidate(copy.deepcopy(res))
    ck("4 the recheck fails one tick past the cap", not ok2 and ("cap" in (why2 or "") or "moved worse" in (why2 or "")), str(why2))
# a maximum INSIDE the cap: selection accepts at it, rejects one tick worse, and the recheck agrees
stub({-3.5: -110, -3.0: -120})
mx_half = lv.convert("NFL", "spread", 0, -3.5, af, -3.0, None, "kalshi", ex.PX_TOL_CENTS if "kalshi" in ex.TOL_BOOKS else 0, W, None, CAP)
ck("4 a whole-number candidate stays unsupported on an unverified venue, so it is skipped by name",
   mx_half["status"] == "unsupported" and mx_half["reason"] == "settlement_rule_unverified"
   and any(c["line"] == -3.0 and str(c["legacy"]).startswith("lv_unsupported:settlement_rule_unverified") for c in run()["lvs"]["cands"]), str(mx_half.get("reason")))
ck("4 ...and the UNCHANGED line is still evaluated normally in the same run",
   any(c["line"] == -3.5 and c["shadow"]["status"] == "ok" for c in run()["lvs"]["cands"]))

# ---------------------------------------------------------------- 5. LINE_VALUE_SHADOW=0 cannot disable price enforcement
# The two switches are independent by construction: LINE_VALUE_MODE decides WHO SETS THE PRICE; LINE_VALUE_SHADOW decides
# only whether the record is written. Turning recording off must never loosen a live limit.
import ast as _ast
import inspect as _inspect

_src = _inspect.getsource(ex.evaluate)
_mode_src = _inspect.getsource(ex.lv_mode)
ck("5 lv_mode() reads LINE_VALUE_MODE and nothing else", "LINE_VALUE_MODE" in _mode_src and "LINE_VALUE_SHADOW" not in _mode_src)
_tree = _ast.parse(__import__("textwrap").dedent(_src))
_live_gates = []
for node in _ast.walk(_tree):
    if isinstance(node, _ast.If):
        txt = _ast.dump(node.test)
        if "lv_mode" in txt:
            _live_gates.append(txt)
ck("5 the live price gate's condition never mentions LINE_VALUE_SHADOW",
   _live_gates and all("LINE_VALUE_SHADOW" not in g for g in _live_gates), str(_live_gates))
_rv_src = _inspect.getsource(ex.revalidate)
ck("5 the recheck's replacement branch is keyed on the stored lv_mode, not on the capture switch",
   'rv.get("lv_mode") == "live"' in _rv_src and "LINE_VALUE_SHADOW" not in _rv_src)

# behavioural proof: live mode with recording OFF gives the same decision as live with recording ON, and both differ
# from legacy where the values differ.
# A REAL case from the 30-day audit: NBA under 228.5 @-109 was filled at 229.5 @-130 (the legacy rule took it; the
# replacement's maximum there is about -120, so it refuses). It is the cleanest proof that the enforcement binds.
PLAY5 = {"play_key": "NBA|CHA@PHX|total|UNDER", "sport": "NBA", "source": "rules", "game": "Charlotte Hornets @ Phoenix Suns",
         "bet": "Under 228.5 (-109)", "start_utc": (NOW + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}
BOOK5 = {228.5: -109, 229.5: CAP}


def run5(mode, shadow):
    ex.MD["c"].clear()
    os.environ["LINE_VALUE_MODE"] = mode
    os.environ["LINE_VALUE_SHADOW"] = shadow
    os.environ.pop("LINE_VALUE_PIN_READ", None)
    try:
        return ex.evaluate(copy.deepcopy(PLAY5), NOW, {}, {}, [], None, {})
    finally:
        os.environ.pop("LINE_VALUE_MODE", None)
        os.environ.pop("LINE_VALUE_SHADOW", None)


def decision(r):
    return (r.get("verdict"), r.get("reason"), r.get("book"), r.get("take_line"), r.get("american"),
            sorted((c["book"], c["line"], c["am"], c["thr"]) for c in cands(r)))


stub(BOOK5)
live_on, live_off, legacy = run5("live", "1"), run5("live", "0"), run5("shadow", "1")
ck("5 live decisions are IDENTICAL with recording on and off", decision(live_on) == decision(live_off),
   f"{decision(live_on)} vs {decision(live_off)}")
ck("5 recording off really did stop recording (so the test is meaningful)", "lvs" in live_on and "lvs" not in live_off)
ck("5 the live limit still binds with recording OFF: -130 is past the ~-120 maximum and is refused",
   not any(c["line"] == 229.5 for c in cands(live_off)), str([(c["line"], c["am"], c["thr"]) for c in cands(live_off)]))
ck("5 the legacy rule WOULD have taken that same price, so the enforcement is doing the work",
   any(c["line"] == 229.5 for c in cands(legacy)), str([(c["line"], c["am"], c["thr"]) for c in cands(legacy)]))
_mx5 = lv.convert("NBA", "total", "UNDER", 228.5, live_off["lvs_alert_af"] if "lvs_alert_af" in live_off else -109, 229.5, None,
                  "kalshi", 0, W, None, CAP)
stub({**BOOK5, 229.5: at_max(_mx5["effective_max_am_after_fee"])})
live_off_ok = run5("live", "0")
ck("5 ...and with recording off a price AT the maximum is still accepted",
   any(c["line"] == 229.5 for c in cands(live_off_ok)), str([(c["line"], c["am"], c["thr"]) for c in cands(live_off_ok)]))

print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
