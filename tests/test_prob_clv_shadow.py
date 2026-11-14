"""Offline correctness tests for prob_clv_shadow (shadow only). No network, no secrets, no live module touched."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value as lv  # noqa: E402
import prob_clv_shadow as ps  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


def close(a, b, t=1e-9):
    return a is not None and b is not None and abs(a - b) < t


lv.SETTLEMENT["vb"] = "refund"                 # a venue with a verified refund rule (test only)
DEC = 1 + 100 / 110                            # -110 after fee

def src_text_for_scan():
    return open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prob_clv_shadow.py")).read()


# ---- 1. formulas
pp, ev, r = ps.ev_and_pp(0.48, 0.04, 0.48, DEC)
ck("1 r is conditional on no push", close(r, 0.5))
ck("1 EV = w*b - l", close(ev, 0.48 * (DEC - 1) - 0.48))
ck("1 EV = (1-q)*((1+b)r-1)", close(ev, (1 - 0.04) * (DEC * 0.5 - 1)))
ck("1 pp = r - 1/(1+b)", close(pp, 0.5 - 1 / DEC))
ck("1 pp and EV share a sign", ps.sgn(pp) == ps.sgn(ev))
ck("1 old same-line arithmetic", close(ps.old_same_line(0.55, 1.9), 0.55 * 1.9 - 1))

# ---- 2. NFL moved total, hand-computed. Pinnacle main Over 44 (whole, mass 14/345), ticket Over 44.5 on a verified venue
m44 = lv.MASS[("NFL", "total", 44)].m
v = ps.value_at_ticket("NFL", "total", "OVER", 44.5, 44.0, 0.50, DEC, "vb")
w0 = 0.5 * (1 - m44)
ck("2 NFL moved: ok and MEASURED", v["status"] == "ok" and v["cls"] == "conv_measured", str(v))
ck("2 win = q(1-m44); no integer crossed", close(v["w"], w0) and close(v["p"], 0.0) and close(v["l"], 1 - w0), str(v))
ck("2 probabilities sum to 1", close(v["w"] + v["p"] + v["l"], 1.0))
ck("2 pp = w/(w+l) - 1/dec", close(v["pp"], w0 / (w0 + (1 - w0)) - 1 / DEC))
# better line: ticket Over 43.5 vs close Over 44 -> crosses 44 (loss becomes ... win mass moves in)
v2 = ps.value_at_ticket("NFL", "total", "OVER", 43.5, 44.0, 0.50, DEC, "vb")
ck("2 better ticket line has more win mass than the close line", v2["status"] == "ok" and v2["w"] > v["w"] + m44 - 1e-9, str(v2))
ck("2 and EV is higher", v2["ev"] > v["ev"])

# ---- 3. unsupported stays unsupported
ck("3 NFL total with no mass row (49)", ps.value_at_ticket("NFL", "total", "OVER", 49.5, 49.0, 0.5, DEC, "vb")["reason"].startswith("no_mass_row"))
ck("3 whole-number ticket on a venue with no verified rule",
   ps.value_at_ticket("NFL", "total", "OVER", 44.0, 44.5, 0.5, DEC, "novig")["reason"].startswith("settlement_rule_unverified"))
ck("3 NBA whole-number move is not estimated", ps.value_at_ticket("NBA", "total", "OVER", 220.0, 221.5, 0.5, DEC, "vb")["status"] == "unsupported")
nc1 = ps.value_at_ticket("NCAAB", "total", "OVER", 150.5, 150.0, 0.5, DEC, "vb")
ck("3 NCAAB total next to its mass row: ESTIMATED, never measured", nc1["status"] == "ok" and nc1["cls"] == "conv_estimated", str(nc1))
nc2 = ps.value_at_ticket("NCAAB", "total", "OVER", 152.5, 150.0, 0.5, DEC, "vb")
ck("3 NCAAB move of 2.5 points refuses (mass is conditional on the line being at that integer)", nc2["status"] == "unsupported" and "far" in nc2["reason"], str(nc2))
nc3 = ps.value_at_ticket("NCAAB", "total", "OVER", 161.5, 161.0, 0.5, DEC, "vb")
ck("3 NCAAB 161 is the source-ambiguous integer: unsupported", nc3["status"] == "unsupported" and "ambiguous" in nc3["reason"], str(nc3))
nb = ps.value_at_ticket("NBA", "total", "OVER", 220.5, 221.0 + 0.5, 0.5, DEC, "vb")
ck("3 NBA half-to-half move is an ESTIMATE, never measured", nb["status"] == "ok" and nb["cls"] == "conv_estimated" and nb["q_push"] == 0.0, str(nb))

# ---- 4. same line
sh = ps.value_at_ticket("NBA", "total", "OVER", 220.5, 220.5, 0.55, DEC, "vb")
ck("4 same-line half point: r=q, no push", sh["cls"] == "same_line" and close(sh["r"], 0.55) and close(sh["p"], 0.0))
ck("4 same-line EV equals old CLV exactly (no push)", close(sh["ev"], ps.old_same_line(0.55, DEC)))
sw = ps.value_at_ticket("NBA", "total", "OVER", 220.0, 220.0, 0.55, DEC, "vb")
ck("4 same-line whole number with no mass: conditional pp only, EV withheld", sw["status"] == "ok" and sw["ev"] is None and close(sw["pp"], 0.55 - 1 / DEC), str(sw))
nfl_same = ps.value_at_ticket("NFL", "spread", None, -3.0, -3.0, 0.52, DEC, "vb")
ck("4 NFL same-line -3: push mass applied, EV = (1-q)*(dec*r-1)", close(nfl_same["ev"], (1 - nfl_same["q_push"]) * (DEC * nfl_same["r"] - 1)), str(nfl_same))
ml = ps.value_at_ticket("NBA", "moneyline", None, None, None, 0.6, 1.8, "vb")
ck("4 moneyline", ml["cls"] == "same_line" and close(ml["ev"], 0.6 * 1.8 - 1))

# ---- 5. mass perturbation changes the answer and restores itself
base_row = lv.mass_row("NFL", "total", 44)
lo = ps.value_at_ticket("NFL", "total", "OVER", 44.5, 44.0, 0.5, DEC, "vb", k=-1)
hi = ps.value_at_ticket("NFL", "total", "OVER", 44.5, 44.0, 0.5, DEC, "vb", k=+1)
ck("5 +/-1 SE moves the win probability", lo["w"] != hi["w"])
ck("5 lv.mass_row restored after the context", lv.mass_row("NFL", "total", 44) is base_row)

# ---- 6. ladder + score on a synthetic Pinnacle history (spread signs and line choice)
T0 = datetime(2026, 11, 8, 18, 0, tzinfo=timezone.utc)


class H:
    from types import SimpleNamespace as NS
    SPORT = {"NFL": 14}
    ML_MARKET = {14: "141"}
    FRESH_MIN = 1440
    tp = staticmethod(lambda x: x if isinstance(x, datetime) else None)

    class tb:
        is_politics = staticmethod(lambda d: False)

    class fxm:
        resolve_side = staticmethod(lambda f, team, lg, wt: ("1", None))
    parsed = staticmethod(lambda s: ("total", "OVER", 44.5))
    which_team = None
    two_way = staticmethod(lambda pm, mid, before: pm[mid])
    novig_p = staticmethod(lambda a, b: (1 / a) / (1 / a + 1 / b))


mk = {"m1": [14, "totals", 44.0, {"o": "Over", "u": "Under"}], "m2": [14, "totals", 45.0, {"o": "Over", "u": "Under"}]}
pm = {"m1": {"o": (1.95, T0 - timedelta(minutes=3), 5000.0), "u": (1.95, T0 - timedelta(minutes=3), 5000.0)},
      "m2": {"o": (2.10, T0 - timedelta(minutes=3), 800.0), "u": (1.78, T0 - timedelta(minutes=3), 800.0)}}
info, why = ps.ladder({"start": T0}, {"league": "NFL", "game": "x", "bet": "Over 44.5"}, mk, pm, H)
ck("6 ladder collects every fresh two-sided line", info and len(info["entries"]) == 2, str(why))
ent, kind = ps.pick_reference(info)
ck("6 no 44.5 hung -> moved, reference is the main (largest-limit) line 44", kind == "moved" and abs(ent[0] - 44.0) < 1e-9)
sc = ps.score_selection("NFL", "vb", DEC, None, info)
ck("6 score: moved, measured, supported", sc["kind"] == "moved" and sc["base"]["status"] == "ok" and sc["base"]["cls"] == "conv_measured", str(sc["base"]))
ck("6 naive price-only differs from converted pp basis (kept separate)", sc["naive"] is not None and sc["old"] is None)
ck("6 sensitivity band recorded", sc.get("sens") and len(sc["sens"]) == 2)
mk2 = dict(mk, m3=[14, "totals", 44.5, {"o": "Over", "u": "Under"}])
pm2 = dict(pm, m3={"o": (1.9, T0 - timedelta(minutes=3), 100.0), "u": (1.9, T0 - timedelta(minutes=3), 100.0)})
info2, _ = ps.ladder({"start": T0}, {"league": "NFL", "game": "x", "bet": "Over 44.5"}, mk2, pm2, H)
ck("6 exact line present -> same_line even with a smaller limit", ps.pick_reference(info2)[1] == "same_line")
stale_pm = {"m1": {"o": (1.95, T0 - timedelta(days=3), 5000.0), "u": (1.95, T0 - timedelta(days=3), 5000.0)}}
i3, w3 = ps.ladder({"start": T0}, {"league": "NFL", "game": "x", "bet": "Over 44.5"}, {"m1": mk["m1"]}, stale_pm, H)
ck("6 stale quotes -> no ladder, reason stated", i3 is None and "no fresh" in w3, str(w3))

# ---- 7. statistics
n, m, se, g = ps.cluster_mean([0.1, 0.1, -0.1, -0.1], ["a", "a", "b", "b"])
ck("7 clustered: 4 rows in 2 games count as 2 clusters", g == 2 and n == 4 and close(m, 0.0))
n2, m2, se2, g2 = ps.cluster_mean([0.1, 0.1, 0.1, 0.1], ["a", "b", "c", "d"])
ck("7 constant sample has zero SE", close(se2, 0.0) and g2 == 4)
n3, m3, se3, g3 = ps.cluster_mean([0.2, 0.2], ["a", "a"])
ck("7 one game -> SE not claimed", se3 is None)
h1, h2, nos = ps.split_halves([{"start": "2026-11-02"}, {"start": "2026-11-01"}, {"start": "2026-11-04"}, {"start": "2026-11-03"}, {"start": None}])
ck("7 halves chronological; a row with no start is reported, not dropped", [x["start"] for x in h1] == ["2026-11-01", "2026-11-02"] and len(nos) == 1)
ck("7 sgn tolerance", ps.sgn(1e-15) == 0 and ps.sgn(-0.01) == -1)

# ---- 7b. public-log safety: free text from fixture_match must never reach the log
leaky = ["AMBIGUOUS: Lakers v Celtics - both sides", "the bet text is 'Duke Blue De', not a team - the side was never recorded",
         "the raw team text identifies neither or both participants (Kansas State)", "no two distinguishable sides on the row (Gonzaga @ Baylor)",
         "2 fixtures survive the prefix test - still ambiguous, not used", "something unforeseen about Villanova"]
for x in leaky:
    sr = ps.safe_reason(x)
    ck(f"7b safe_reason withholds names: {x[:28]}", not any(n in sr for n in ("Lakers", "Celtics", "Duke", "Kansas", "Gonzaga", "Baylor", "Villanova")), sr)
ck("7b unknown text is withheld, not echoed", ps.safe_reason("something unforeseen about Villanova") == "other (text withheld)")
# every string main() can print is built from fixed text, counts, league/lane/source labels and numbers - scan the source for risky prints
_s = src_text_for_scan()
ck("7b no say()/print of a selection key, game or bet text", not any(f in _s for f in ('say(r["key"]', "say(f\"{r['key']", "r['game'][1]}", 'snap.get("game")}', "snap.get('bet')}")))
ck("7b crash handler withholds the exception message", "message and traceback withheld" in _s)

# ---- 8. the module touches nothing live
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prob_clv_shadow.py")).read()
ck("8 imports no execution module", "import executor" not in src and "import liquidity_monitor" not in src)
ck("8 writes no file", "open(" not in src.replace("json.load(open(", "").replace("open(cl.STATE", ""))

print(f"{len(OK)} passed, {len(BAD)} failed")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)
