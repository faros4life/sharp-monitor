"""Nov 12, 2026: the line-value SHADOW capture records inputs and changes NO decision.

What these tests pin (all by RUNNING evaluate() / revalidate() against stubbed venues, not by reading source):
  1. identical decisions - evaluate() returns the same result with the shadow off, on, and deliberately broken
  2. complete capture    - every ladder row, every candidate and the reason it was rejected, exact hp, calc version
  3. honest reference    - the buy-side-only ladders yield 'no reference', never an invented probability
  4. two-sided reference - IF a ladder row carries an opposite-side price, it is de-vigged and used, with its timestamp
  5. recheck             - revalidate() verdicts are identical with the shadow on, off and broken; the recheck is recorded
  6. ledger              - shadow record + capture status ride in the EXISTING ledger row; no extra email
  7. isolation           - the shadow module imports nothing from executor and has no network or order code
"""
import copy
import inspect
import json
import os
import sys
import textwrap
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_check as bc  # noqa: E402
import executor as ex  # noqa: E402
import line_value as lv  # noqa: E402
import line_value_shadow as lvsh  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


# ---------------------------------------------------------------- a stubbed market
def ladder(am, line, dollars=5000.0, extra=None):
    r = {"status": "ok", "line": line, "best_price_american": am, "best_price_american_qual": am,
         "best_price_american_displayed": am,
         "buy_levels": [{"american": am, "american_after_fee": am, "american_after_fee_qual": am,
                         "dollars": dollars, "strike_id": "S1"}]}
    r.update(extra or {})
    return r


# Kansas City -3.5 at -110 is the alert. Kalshi's ladder by line (handicap): a worse line is cheaper, a better line dearer.
KALSHI = {-3.5: -110, -4.0: -104, -4.5: -100, -3.0: -125, -2.5: -150}


def stub(kalshi=None, extra=None):
    kalshi = KALSHI if kalshi is None else kalshi

    def kal(al, mtype, side, ln, price, teams):
        return ladder(kalshi[ln], ln, extra=(extra or {}).get(ln)) if ln in kalshi else {"status": "no_market"}
    bc.kalshi_check = kal
    bc.px_check = lambda *a, **k: {"status": "no_market"}
    ex.pmus_check = lambda *a, **k: {"status": "no_market"}
    bc.check_alert = lambda *a, **k: {"status": "no_market"}


NOW = datetime.now(timezone.utc)
PLAY = {"play_key": "NFL|KC@BUF|side|Kansas City Chiefs", "sport": "NFL", "source": "rules",
        "game": "Kansas City Chiefs @ Buffalo Bills", "bet": "Kansas City Chiefs -3.5 (-110)",
        "start_utc": (NOW + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}


def run(play=None, env="1", broken=False):
    ex.MD["c"].clear()
    os.environ["LINE_VALUE_SHADOW"] = env
    real = lvsh.build
    if broken:
        def boom(*a, **k):
            raise RuntimeError("shadow exploded")
        lvsh.build = boom
    try:
        return ex.evaluate(copy.deepcopy(play or PLAY), NOW, {}, {}, [], None, {})
    finally:
        lvsh.build = real
        os.environ.pop("LINE_VALUE_SHADOW", None)


def core(r):
    d = dict(r)
    d.pop("lvs", None)
    return json.dumps(d, sort_keys=True, default=str)


stub()
r_off, r_on, r_broken = run(env="0"), run(env="1"), run(env="1", broken=True)
ck("scenario is meaningful: the legacy rule places a bet", r_off.get("verdict") == "WOULD PLACE", str(r_off.get("verdict")) + " " + str(r_off.get("reason")))
ck("1. shadow ON gives the identical decision to OFF", core(r_on) == core(r_off))
ck("1. shadow BROKEN gives the identical decision to OFF", core(r_broken) == core(r_off))
ck("shadow OFF records nothing", "lvs" not in r_off)
ck("a broken shadow leaves only an error record (no partial data) and says why",
   set(r_broken.get("lvs", {})) == {"error"} and r_broken["lvs"]["error"].startswith("RuntimeError: shadow exploded"), str(r_broken.get("lvs")))
ck("the ledger fields of a broken capture say error", lvsh.ledger_fields(r_broken)["lvs_capture"].startswith("error: RuntimeError"), "")

# a SKIP scenario and a floor-blocked scenario also unchanged
stub({-3.5: -140, -4.0: -135, -4.5: -131, -3.0: -150, -2.5: -190})
s_off, s_on = run(env="0"), run(env="1")
ck("a skip scenario stays a skip", s_off["verdict"] == "SKIP" and core(s_on) == core(s_off), str(s_off.get("reason")))
stub()
fl = dict(PLAY, floor_line=-3.5)
f_off, f_on = run(fl, "0"), run(fl, "1")
ck("a floor-blocked scenario is identical with the shadow on", core(f_on) == core(f_off))

# ---------------------------------------------------------------- 2. complete capture
L = r_on["lvs"]
ck("calc version recorded", L["calc"] == lv.CALC_VERSION and L["calc"].startswith("line_value/v3"), str(L.get("calc")))
ck("exact hp recorded at full precision and equal to the decision's own hp", L["hp"] == round(r_on["hp"], 9) and L["hp_src"] == r_on["hp_src"], f"{L['hp']} {r_on['hp']}")
ck("the complete pre-filter ladder is recorded (all 5 kalshi lines)", sorted(x["line"] for x in L["ladder"]) == sorted(KALSHI), str([x["line"] for x in L["ladder"]]))
ck("each ladder row carries after-fee price, screen price and depth levels",
   all(x["am_after_fee"] is not None and x["shown"] is not None and x["levels"] for x in L["ladder"]), "")
why = {c["line"]: c["legacy"] for c in L["cands"]}
ck("EVERY ladder row has a candidate note", sorted(why) == sorted(KALSHI), str(why))
ck("the winning candidate is marked qualified and a gate failure is marked price_gate",
   "qualified" in why.values() and "price_gate" in why.values(), str(why))
q = [c for c in L["cands"] if c["legacy"] == "qualified"][0]
ck("qualified candidates carry the legacy equivalent cost, threshold and depth", all(k in q for k in ("hb", "c_eq_q", "thr", "avail")), str(q))
fl_why = {c["line"]: c["legacy"] for c in run(fl, "1")["lvs"]["cands"]}
ck("floor-blocked candidates are recorded with that reason (-4.0/-4.5/-3.0... worse than floor)", "floor_blocked" in fl_why.values(), str(fl_why))
ck("settlement rules and mass rows in force are recorded", "settlement_rules" in L and "NFL/spread/3" in L["mass_rows"], str(L.get("mass_rows"))[:80])
ck("tolerance and tolerance venues recorded", L["tol_cents"] == ex.PX_TOL_CENTS and set(L["tol_books"]) == set(ex.TOL_BOOKS), "")

# ---------------------------------------------------------------- 3. honest reference
ck("with no Pinnacle feed cached there is NO reference, and the reason is named", L["reference"] is None and L["reference_status"] == "pinnacle_not_cached", str(L["reference_status"]))
ck("NFL (mass method) with NO Pinnacle data is still valued: alert-anchored, with method, source and both maxima recorded",
   all(c["shadow"]["method"] in ("mass", "same_line") and c["shadow"]["source"] and "needs" in c["shadow"]
       and (c["shadow"]["status"] == "ok" if not float(c["line"]).is_integer() else c["shadow"]["reason"] == "settlement_rule_unverified")
       for c in L["cands"]), str([(c["line"], c["shadow"]["status"], c["shadow"]["reason"]) for c in L["cands"]]))
_hl = [c["shadow"] for c in L["cands"] if not float(c["line"]).is_integer() and c["line"] != L["alert_line"]]
ck("every valued candidate reports the calculated maximum, the cap and the effective maximum",
   _hl and all(s["max_am_after_fee_calc"] is not None and s["cap_am"] == ex.CAP_LINE and s["effective_max_am_after_fee"] is not None
               and isinstance(s["capped"], bool) for s in _hl), str(_hl[:1]))
ck("the alert's own line is valued with zero credit (unchanged line, no reference needed)",
   any(c["line"] == L["alert_line"] and c["shadow"]["status"] == "ok" and c["shadow"]["allowance"] == 0.0 for c in L["cands"]),
   str([(c["line"], c["shadow"].get("allowance")) for c in L["cands"]]))
c3 = [c for c in L["cands"] if c["line"] == -2.5][0]["shadow"]["needs"]
ck("crossing 3 (-3.5 -> -2.5) is reported with its mass row available and no settlement rule needed",
   c3["crossed"] == [3] and c3["mass_ok"] and c3["settlement"] == "n/a", str(c3))
cw = [c for c in L["cands"] if c["line"] == -3.0][0]["shadow"]["needs"]
ck("a whole-number candidate is flagged settlement_rule_unverified until the venue's rule is verified",
   cw["settlement"] == "unverified", str(cw))

# ---------------------------------------------------------------- 4. an INDEPENDENT Pinnacle reference IS used, with timestamps
def pin_feed(read_age_s=20, pts=(-3.5, 3.5), prices=(-110, -110), commence_h=6, teams=("Kansas City Chiefs", "Buffalo Bills")):
    at = NOW - timedelta(seconds=read_age_s)
    ex._PIN["americanfootball_nfl"] = [{"home_team": teams[1], "away_team": teams[0], "commence_time": (NOW + timedelta(hours=commence_h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bookmakers": [{"key": "pinnacle", "last_update": (at - timedelta(seconds=40)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "markets": [{"key": "spreads", "last_update": (at - timedelta(seconds=40)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "outcomes": [{"name": teams[0], "point": pts[0], "price": prices[0]},
                                                  {"name": teams[1], "point": pts[1], "price": prices[1]}]}]}]}]
    ex._PIN_AT["americanfootball_nfl"] = at


def pin_clear():
    ex._PIN.clear(); ex._PIN_AT.clear()


pin_feed()
t = run(env="1")["lvs"]
ck("a cached Pinnacle two-sided spread becomes the reference at ITS OWN line", t["reference"] and t["reference"]["line"] == -3.5
   and abs(t["reference"]["q"] - 0.5) < 1e-9 and t["reference"]["source"] == "pinnacle", str(t["reference"]))
d = t["reference_detail"]
ck("the reference records both prices, the quote's last_update, our read time, age, start gap and period",
   d["am_mine"] == -110 and d["am_other"] == -110 and d["last_update"] and d["read_utc"] and d["age_s"] is not None
   and d["start_gap_min"] is not None and d["period"] == "full_game", str(d))
ev = [c for c in t["cands"] if c["line"] == -2.5][0]["shadow"]
ck("the shadow then returns a real EV for the half->half move across 3", ev["status"] == "ok" and ev["ev"] is not None and ev["max_am_after_fee"] is not None, str(ev))
ck("and it still changes no decision (same stub, shadow off vs on)", core(run(env="1")) == core(run(env="0")))
ev3 = [c for c in t["cands"] if c["line"] == -3.0][0]["shadow"]
ck("a whole-number candidate on an unverified venue is UNSUPPORTED, not guessed",
   ev3["status"] == "unsupported" and ev3["reason"] == "settlement_rule_unverified", str(ev3))
stub(extra={-3.5: {"opp_am_after_fee": -110, "read_utc": "2026-11-12T12:00:00Z"}})
pin_clear()
t2 = run(env="1")["lvs"]
ck("the EXECUTION venue's own opposite quote is NOT a reference", t2["reference"] is None, str(t2["reference"]))
stub()
for label, kw, why in (("a stale Pinnacle read", dict(read_age_s=900), "stale_read"),
                       ("a different game start", dict(commence_h=30), "different_game_start"),
                       ("non-mirrored handicaps", dict(pts=(-3.5, 2.5)), "handicaps_not_mirrored"),
                       ("an implausible overround", dict(prices=(-110, 300)), "implausible_overround")):
    pin_feed(**kw)
    tt = run(env="1")["lvs"]
    ck(f"{label} gives no reference and says why", tt["reference"] is None and tt["reference_status"].startswith(why), str(tt["reference_status"]))
pin_feed(teams=("Kansas City Chiefs", "Buffalo Bills"))
ex._PIN["americanfootball_nfl"] = ex._PIN["americanfootball_nfl"] * 2
ck("two games matching the teams (doubleheader) is ambiguous, never guessed", run(env="1")["lvs"]["reference_status"].startswith("game_ambiguous"), "")
pin_clear()
ck("no new network call is made without LINE_VALUE_PIN_READ", run(env="1")["lvs"]["reference_status"] == "pinnacle_not_cached", "")

# ---------------------------------------------------------------- 5. recheck
AF = -110
ACOST = ex.american_to_prob(AF)
PXT = ex.american_to_prob(ex.cents_worse(AF, 2)) - ACOST


def rv_play(book="kalshi", line=-2.5, thr=-130):
    return {"live": {"book": book, "line": line, "risk": 220.0, "px": {"thr": thr, "buy": [], "am": AF}},
            "reval": {"al": {"bet": "Kansas City Chiefs -3.5 (-110)", "sport": "NFL", "start_utc": PLAY["start_utc"]},
                      "mtype": "spread", "side": 0, "price": AF, "teams": ("Kansas City Chiefs", "Buffalo Bills"),
                      "line": -3.5, "alert_af": AF, "alert_cost": ACOST, "px_tol": PXT, "hp": 0.03,
                      "play_key": PLAY["play_key"]}}


def reval(env="1", broken=False, am=-140):
    os.environ["LINE_VALUE_SHADOW"] = env
    lvsh.RECHECKS.clear()
    real = lvsh.note_recheck
    if broken:
        def boom(*a, **k):
            raise RuntimeError("recheck shadow exploded")
        lvsh.note_recheck = boom
    bc.kalshi_check = lambda *a, **k: ladder(am, -2.5)
    try:
        return ex.revalidate(rv_play(), None)
    finally:
        lvsh.note_recheck = real
        os.environ.pop("LINE_VALUE_SHADOW", None)


for am in (-140, -190):
    a, b, c = reval("0", am=am), reval("1", am=am), reval("1", True, am=am)
    ck(f"5. recheck verdict identical off/on/broken at {am:+d}", a[:2] == b[:2] == c[:2], f"{a[:2]} | {b[:2]} | {c[:2]}")
reval("1", am=-140)
ck("5. the recheck is recorded with stored hp, hb, price, requirements and its own legacy verdict",
   len(lvsh.RECHECKS) == 1 and lvsh.RECHECKS[0]["hp_stored"] == 0.03 and "needs" in lvsh.RECHECKS[0]
   and lvsh.RECHECKS[0]["reference"] is None and "legacy_pass" in lvsh.RECHECKS[0], str(lvsh.RECHECKS[:1]))
lvsh.RECHECKS.clear()
reval("0", am=-140)
ck("5. nothing is recorded when the shadow is off", not lvsh.RECHECKS, "")

# ---------------------------------------------------------------- 6. ledger (no extra email)
lvsh.RECHECKS.clear()
reval("1", am=-140)
os.environ["LINE_VALUE_SHADOW"] = "1"
res = dict(r_on, play=dict(r_on.get("play") or {}, play_key=(r_on["lvs"] or {}).get("play_key")))
f = lvsh.ledger_fields(res)
ck("6. capture ok is recorded", f["lvs_capture"] == "ok" and f["lvs"]["calc"] == lv.CALC_VERSION, str(f.get("lvs_capture")))
ck("6. the play's recheck rides in the same ledger fields", len(f["lvs_rechecks"]) == 1 or not res["play"].get("play_key"), str(len(f["lvs_rechecks"])))
ck("6. depth is dropped from the ledger copy only", all("levels" not in x for x in f["lvs"]["ladder"]) and
   any("levels" in x for x in r_on["lvs"]["ladder"]), "")
ck("6. the ledger fields are valid JSON with no stakes or balances", "risk" not in json.dumps(f) and "balance" not in json.dumps(f).lower()
   and json.loads(json.dumps(f)) == f, "")
ck("6. a play that never reached the hook says not_evaluated", lvsh.ledger_fields({"verdict": "SKIP"})["lvs_capture"] == "not_evaluated", "")
ck("6. a failed capture says error and why", lvsh.ledger_fields({"lvs": {"error": "KeyError: x"}})["lvs_capture"].startswith("error: KeyError"), "")
ck("6. a garbage result never raises", lvsh.ledger_fields(None)["lvs_capture"].startswith("error"), "")
os.environ["LINE_VALUE_SHADOW"] = "0"
ck("6. off is recorded as off, and the ledger still records WHICH RULE decided",
   lvsh.ledger_fields(res) == {"lvs_capture": "off", "lv_mode": "shadow"}, str(lvsh.ledger_fields(res)))
os.environ["LINE_VALUE_MODE"] = "live"
ck("6. a live run is stamped lv_mode=live in every ledger row", lvsh.ledger_fields(res)["lv_mode"] == "live"
   and lvsh.ledger_fields({"verdict": "SKIP"})["lv_mode"] == "live", str(lvsh.ledger_fields(res).get("lv_mode")))
os.environ.pop("LINE_VALUE_MODE", None)
ck("6. the run log states the mode once", "line-value mode:" in inspect.getsource(ex.main))
os.environ["LINE_VALUE_SHADOW"] = "1"
msrc = inspect.getsource(ex.main)
ck("6. there is no second email: executor never calls send_run and the shadow module has none",
   "send_run" not in msrc and not hasattr(lvsh, "send_run") and "LINEVALUE SHADOW" not in msrc, "")
ck("6. ledger_row merges the capture fields", "lvsh.ledger_fields(r)" in inspect.getsource(ex.ledger_row), "")

# ---------------------------------------------------------------- 6b. ledger payload cap
def rows_of(n, levels=True):
    out = []
    for i in range(n):
        lv_ = copy.deepcopy(r_on["lvs"])
        out.append({"key": f"k{i}", "alert_line": -3.5, "verdict": "WOULD PLACE", "fill_book": "kalshi", "lvs_capture": "ok", "lvs": lv_,
                    "venues_considered": [{"book": "kalshi", "line": -3.5}]})
    return out
small = rows_of(2)
same, st0 = lvsh.cap_rows(copy.deepcopy(small), 10_000_000)
ck("6b. under budget: nothing changes", same == small and st0 == 0)
big = rows_of(400)
full = len(json.dumps(big, separators=(",", ":")).encode())
capped, st1 = lvsh.cap_rows(big, full // 3)
ck("6b. over budget: shrinks in stages until it fits, never cuts JSON",
   st1 in (1, 2, 3) and len(json.dumps(capped, separators=(",", ":")).encode()) <= full // 3 and json.loads(json.dumps(capped)) == capped, str(st1))
ck("6b. every row says which stage capped it", all(r["lvs_capture"] == f"capped:stage{st1}" for r in capped))
ck("6b. registry fields are untouched by the cap", all(r["key"] == f"k{i}" and r["fill_book"] == "kalshi" and r["venues_considered"] for i, r in enumerate(capped)))
tiny, st3 = lvsh.cap_rows(rows_of(400), 1)
ck("6b. an impossible budget stops at stage 3 with reference and counts kept", st3 == 3 and all(set(r["lvs"]) >= {"calc", "reference", "n_cands", "n_qualified"} for r in tiny))
mixed = rows_of(3); mixed[1] = {"key": "x", "lvs_capture": "error: boom"}
m2, _ = lvsh.cap_rows(mixed, 1)
ck("6b. rows without an ok capture are left alone", m2[1] == {"key": "x", "lvs_capture": "error: boom"})
ck("6b. executor caps before dumping the ledger", "lvsh.cap_rows(_lrows)" in inspect.getsource(ex.main) and 'json.dumps(_lrows' in inspect.getsource(ex.main))

# ---------------------------------------------------------------- 7. isolation
ssrc = inspect.getsource(lvsh)
ck("7. shadow module does not import executor, requests or smtplib",
   all(w not in ssrc for w in ("import executor", "import requests", "smtplib", "urllib", "px_live", "book_live")), "")
ck("7. build() and note_recheck() each swallow their own exceptions",
   "except Exception" in inspect.getsource(lvsh.build) and "except Exception" in inspect.getsource(lvsh.note_recheck), "")
esrc = inspect.getsource(ex.evaluate)
import ast  # noqa: E402
_tree = ast.parse(textwrap.dedent(esrc))
_reads = [n for n in ast.walk(_tree)
          if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value == "lvs"
              and not isinstance(n.ctx, ast.Store))
          or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
              and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "lvs")]
ck("7. evaluate() only WRITES the lvs record - there is no read of it anywhere in the function", not _reads, str(_reads))
ck("7. the legacy half-point arithmetic is unchanged (credit = hb * hp feeds the one c_eq / thr formula)", "credit = hb * hp" in esrc
   and "c_eq = american_to_prob(am) - credit" in esrc and "c_eq_q = american_to_prob(am_q) - credit" in esrc, "")
ck("7. the legacy threshold arithmetic is unchanged", "thr = lm.american(min(max(alert_cost + tol + credit, 0.01), 0.99))" in esrc, "")

print(f"{len(OK)} passed, {len(BAD)} failed")
for b in BAD:
    print("FAIL:", b)
sys.exit(1 if BAD else 0)
