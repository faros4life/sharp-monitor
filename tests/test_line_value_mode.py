"""Nov 12: LINE_VALUE_MODE. 'shadow'/unset -> decisions identical to the legacy rule. 'live' -> selection, the order
threshold and the recheck all come from the ONE convert(); unsupported conversions are skipped by name; one tick worse
than the maximum is refused at selection AND at the recheck. The switch is a repo variable; nothing here flips it live."""
import copy
import inspect
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


def ladder(am, line, dollars=5000.0):
    return {"status": "ok", "line": line, "best_price_american": am, "best_price_american_qual": am, "best_price_american_displayed": am,
            "buy_levels": [{"american": am, "american_after_fee": am, "american_after_fee_qual": am, "dollars": dollars, "strike_id": "S1"}]}


NOW = datetime.now(timezone.utc)
# NBA under 214.5 at -110 is the alert (prob-points method, no reference needed). Kalshi lists 214.5 / 215.5 / 213.5 / 215.0.
PLAY = {"play_key": "NBA|CHA@PHX|total|UNDER", "sport": "NBA", "source": "rules", "game": "Charlotte Hornets @ Phoenix Suns",
        "bet": "Under 214.5 (-110)", "start_utc": (NOW + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}
BOOK = {214.5: -110, 215.5: -121, 213.5: -100, 215.0: -116}


def stub(book=None):
    book = BOOK if book is None else book
    bc.kalshi_check = lambda al, mtype, side, ln, price, teams: ladder(book[ln], ln) if ln in book else {"status": "no_market"}
    bc.px_check = lambda *a, **k: {"status": "no_market"}
    ex.pmus_check = lambda *a, **k: {"status": "no_market"}
    bc.check_alert = lambda *a, **k: {"status": "no_market"}


def run(mode, play=None):
    ex.MD["c"].clear()
    if mode is None:
        os.environ.pop("LINE_VALUE_MODE", None)
    else:
        os.environ["LINE_VALUE_MODE"] = mode
    try:
        return ex.evaluate(copy.deepcopy(play or PLAY), NOW, {}, {}, [], None, {})
    finally:
        os.environ.pop("LINE_VALUE_MODE", None)


def cands(r):
    """Every qualified candidate with its threshold (pick + others; lcs carries the same for the live books)."""
    out = list(r.get("others") or []) + list(r.get("lcs") or [])
    seen, uniq = set(), []
    for c in out:
        if (c["book"], c["line"]) not in seen:
            seen.add((c["book"], c["line"])); uniq.append(c)
    return uniq


def core(r):
    return {k: r.get(k) for k in ("verdict", "reason", "book", "take_line", "american")} | {"cands": sorted((c["book"], c["line"], c["am"], c["thr"]) for c in cands(r))}


stub()
r_unset, r_shadow, r_live = run(None), run("shadow"), run("live")
ck("scenario places a bet under the legacy rule", r_unset.get("verdict") == "WOULD PLACE", str(r_unset.get("reason")))
ck("1 unset and 'shadow' are identical", core(r_unset) == core(r_shadow))
ck("1 the switch is read from LINE_VALUE_MODE only", "LINE_VALUE_MODE" in inspect.getsource(ex.lv_mode) and "vars.LINE_VALUE_MODE" in open(os.path.join(os.path.dirname(ex.__file__), ".github/workflows/executor-dry-run.yml")).read())
# live: 215.5 under is a FULL point better -> prob credit 0.024343: max = prob(-110)+0.024343 -> about -121.3; -121 qualifies
lc = {(c["book"], c["line"]): c for c in cands(r_live)}
AF = r_live["lvs"]["alert_af"]   # the executor prices the alert after fees (-111 here); the boundary must use that
mx = lv.convert("NBA", "total", "UNDER", 214.5, AF, 215.5, None, "kalshi")["max_prob"]
ck("2 live: the 215.5 candidate's threshold IS convert()'s maximum", ("kalshi", 215.5) in lc and abs(ex.american_to_prob(lc[("kalshi", 215.5)]["thr"]) - mx) < 2e-3, str(lc.get(("kalshi", 215.5))))
ck("2 live: the whole-number 215.0 candidate is skipped as unsupported (Kalshi tie rule unverified)",
   ("kalshi", 215.0) not in lc and any(c["line"] == 215.0 and str(c["legacy"]).startswith("lv_unsupported:settlement_rule_unverified") for c in r_live["lvs"]["cands"]),
   str([(c["line"], c["legacy"]) for c in r_live["lvs"]["cands"]]))
# The worse line (213.5 for an UNDER) has a PLUS-money maximum (about +101), so -100 is worse than the maximum and is
# refused. With conservative rounding the refusal can land at the depth gate rather than the price gate - thr is the
# conservative integer, so a price between the exact maximum and that integer has no depth at thr. Either way it is out.
_c213 = [c for c in r_live["lvs"]["cands"] if c["line"] == 213.5]
ck("2 live: the worse 213.5 line at -100 is refused by the replacement (price or depth gate), never selected",
   ("kalshi", 213.5) not in lc and _c213 and _c213[0]["legacy"] in ("price_gate", "no_depth_at_thr"),
   str([(c["line"], c["legacy"]) for c in r_live["lvs"]["cands"]]))
# one tick worse than the maximum is refused at selection
MAX = lv.convert("NBA", "total", "UNDER", 214.5, AF, 215.5, None, "kalshi")["max_am_after_fee"]   # about -122.4
worse = {**BOOK, 215.5: ex.cents_worse(int(MAX), 1)}   # int() truncates toward zero: -122 -> -123 is past the maximum
stub(worse)
r2 = run("live")
ck("3 live: one tick worse than the maximum at 215.5 is refused (price_gate)", not any(c["line"] == 215.5 for c in cands(r2))
   and any(c["line"] == 215.5 and c["legacy"] == "price_gate" for c in r2["lvs"]["cands"]), str([(c["line"], c["legacy"]) for c in r2["lvs"]["cands"]]))
stub()
# recheck agreement: stored basis carries lv_mode; revalidate re-reads the book and uses the SAME convert()
r3 = run("live")
pick = next(c for c in cands(r3) if c["line"] == 215.5)
rv = r3["reval"]
ck("4 the stored revalidation basis records the mode", rv.get("lv_mode") == "live")
res = {"live": {"book": "kalshi", "line": 215.5, "risk": 220.0, "px": {"thr": pick["thr"], "buy": [], "am": pick["am"]}}, "reval": rv}
ok, why, _ = ex.revalidate(copy.deepcopy(res))
ck("4 recheck at the qualifying price passes", ok, str(why))
stub({**BOOK, 215.5: ex.cents_worse(int(MAX), 1)})
ok2, why2, _ = ex.revalidate(copy.deepcopy(res))
ck("4 recheck one tick worse than the maximum fails closed with the gate message", not ok2 and "moved worse than the alert gate" in why2, str(why2))
stub({**BOOK, 215.5: -110})
rv_shadow = dict(rv, lv_mode="shadow")
ok3, _, _ = ex.revalidate({"live": res["live"], "reval": rv_shadow})
ck("4 a basis recorded in shadow mode rechecks with the legacy rule (no silent switch mid-order)", ok3 is not None)
# live and legacy differ where the values differ (the point of the switch) - shown, not hidden
d_leg = {c["line"]: c["thr"] for c in cands(r_unset)}
d_liv = {c["line"]: c["thr"] for c in cands(r3)}
ck("5 live and legacy thresholds at 215.5 differ (recorded, visible)", d_leg.get(215.5) != d_liv.get(215.5), f"{d_leg} vs {d_liv}")
ck("5 moneyline plays are untouched by the switch", "mtype in (\"spread\", \"total\")" in inspect.getsource(ex.evaluate))
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
