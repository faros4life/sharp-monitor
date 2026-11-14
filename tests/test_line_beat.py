"""Offline adversarial tests for line_beat (shadow-only line-beat scorecard). No network, no secrets."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_beat as lb  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + ("" if cond else f"  [{detail}]"))


def L(*lines):
    """Ladder entries: (line, q, age, limit). The first line given is the 50/50 main at the top limit."""
    out = []
    for i, ln in enumerate(lines):
        out.append((ln, 0.5 if i == 0 else 0.5 + 0.06 * i, 2, 5000 if i == 0 else 1000))
    return out


def G(mtype, side, bet, close, clv=None, open_=None, why=None):
    """open_ defaults to a ladder whose main is the ticket's own line (so points = close main move vs the ticket line)."""
    ci = {"mtype": mtype, "side": side, "bet_line": bet, "entries": close}
    oi = {"mtype": mtype, "side": side, "bet_line": bet, "entries": open_ if open_ is not None else L(bet)} if open_ != "none" else None
    return lb.grade(ci, clv, oi, why)


# ---- signed points: totals (main at placement -> main at close)
ck("over: main 44.5 at bet, 46.5 at close -> +2", G("total", "OVER", 44.5, L(46.5))["points"] == 2.0)
ck("over: main 46.5 at bet, 44.5 at close -> -2", G("total", "OVER", 46.5, L(44.5))["points"] == -2.0)
ck("under: main 46.5 -> 44.5 -> +2", G("total", "UNDER", 46.5, L(44.5))["points"] == 2.0)
ck("under: main 44.5 -> 46.5 -> -2", G("total", "UNDER", 44.5, L(46.5))["points"] == -2.0)
# ---- spreads in bettor orientation
ck("dog +3.5 -> +2.5 -> +1", G("spread", None, 3.5, L(2.5))["points"] == 1.0)
ck("fav -2.5 -> -3.5 -> +1", G("spread", None, -2.5, L(-3.5))["points"] == 1.0)
ck("fav -3.5 -> -2.5 -> -1", G("spread", None, -3.5, L(-2.5))["points"] == -1.0)
ck("dog +2.5 -> +3.5 -> -1", G("spread", None, 2.5, L(3.5))["points"] == -1.0)
ck("pick'em crossing zero: +1 -> -1.5 -> +2.5", G("spread", None, 1.0, L(-1.5))["points"] == 2.5)
# ---- THE DEFECT: an alternate-line ticket is not a beat when the market did not move
alt = G("total", "OVER", 220.5, L(224.5), -0.04, open_=L(224.5))
ck("alt line Over 220.5 with main 224.5 -> 224.5 is a TIE, not +4 (bought points are not a beat)", alt["points"] == 0.0 and alt["line"] == lb.TIE, str(alt))
alt2 = G("spread", None, -1.5, L(-4.5), None, open_=L(-3.5))
ck("alt spread ticket graded on the MAIN move only (-3.5 -> -4.5 = +1)", alt2["points"] == 1.0)
# ---- half-point / whole-number / tie
g = G("total", "OVER", 45.0, L(45.0))
ck("whole-number no move -> tie, 0 points", g["line"] == lb.TIE and g["points"] == 0.0)
ck("half-point move our way is a beat", G("total", "UNDER", 45.5, L(45.0))["line"] == lb.BEAT)
ck("half-point move against is a loss", G("spread", None, -7.5, L(-7.0))["line"] == lb.LOSS)
# ---- main-line selection
ent = [(44.5, 0.50, 2, 4800), (45.5, 0.45, 2, 5000), (43.5, 0.56, 2, 900)]
ck("main = nearest 50/50 within 90% of the top limit, not simply the largest limit", lb.main_line(ent) == (44.5, None))
ent2 = [(44.5, 0.50, 2, 5000), (45.5, 0.50, 2, 4900)]
ck("ambiguous close main -> excluded", lb.main_line(ent2) == (None, "main line ambiguous")
   and G("total", "OVER", 44.5, ent2)["status"] == "main line ambiguous")
ck("ambiguous placement main -> excluded, labelled 'at placement'", G("total", "OVER", 44.5, L(44.5), open_=ent2)["status"]
   == "main line ambiguous at placement")
ent3 = [(44.5, 0.50, 2, 400), (45.5, 0.47, 2, 5000)]
ck("a 50/50 line below the limit floor is not main", lb.main_line(ent3)[0] == 45.5)
ck("empty ladder -> excluded", lb.main_line([]) == (None, "no line on the ladder"))
ck("zero limits -> excluded", lb.main_line([(44.5, 0.5, 2, 0)]) == (None, "no limit on the ladder"))
# ---- exclusions, never zero-filled
ck("no Pinnacle close -> excluded with reason, no points", lb.grade(None)["status"] == "no Pinnacle close" and lb.grade(None)["points"] is None)
ck("no placement ladder -> excluded with the given reason", G("total", "OVER", 44.5, L(44.5), open_="none", why="no placement time")["status"]
   == "no placement time" and G("total", "OVER", 44.5, L(44.5), open_="none", why="placed after start")["status"] == "placed after start")
ck("unrecognised placement reason never leaks free text", G("total", "OVER", 44.5, L(44.5), open_="none", why="Duke @ UNC")["status"]
   == "no Pinnacle line at placement")
ck("placement ladder for another side -> excluded", lb.grade({"mtype": "total", "side": "OVER", "bet_line": 44.5, "entries": L(45.5)}, None,
   {"mtype": "total", "side": "UNDER", "bet_line": 44.5, "entries": L(44.5)})["status"] == "placement ladder does not match")
ck("placement ladder for another market -> excluded", lb.grade({"mtype": "total", "side": "OVER", "bet_line": 44.5, "entries": L(45.5)}, None,
   {"mtype": "spread", "side": "OVER", "bet_line": 44.5, "entries": L(44.5)})["status"] == "placement ladder does not match")
ck("total with no side -> excluded", G("total", None, 44.5, L(44.5))["status"] == "total side unknown")
ck("unknown market -> excluded", G("team_total", "OVER", 20.5, L(20.5))["status"] == "market not graded")
mlg = lb.grade({"mtype": "moneyline", "side": None, "bet_line": None, "entries": [(None, 0.55, 2, 5000)]}, 0.02)
ck("moneyline: points n/a, price only", mlg["status"] == "moneyline points not applicable" and mlg["points"] is None and mlg["price"] is True and mlg["any"] is True)
# ---- price and union
ck("same-line price beat = CLV > 0", G("total", "OVER", 44.5, L(44.5), 0.013)["price"] is True
   and G("total", "OVER", 44.5, L(44.5), -0.01)["price"] is False and G("total", "OVER", 44.5, L(44.5), 0.0)["price"] is False)
ck("no same-line CLV -> price unknown, not false", G("total", "OVER", 44.5, L(46.5))["price"] is None)
ck("union: line beat counts whatever the price", G("total", "OVER", 44.5, L(46.5), -0.03)["any"] is True)
ck("union: tie + price beat counts", G("total", "OVER", 44.5, L(44.5), 0.02)["any"] is True)
ck("union: tie + price loss does not", G("total", "OVER", 44.5, L(44.5), -0.02)["any"] is False)
ck("union: tie with unknown price is unknown, not a loss", G("total", "OVER", 44.5, L(44.5))["any"] is None)
ck("union: line LOSS + good price is NOT a proven win (no validated conversion)", G("total", "OVER", 46.5, L(44.5), 0.08)["any"] is False)
# ---- tally: denominators, no double counting
gs = [G("total", "OVER", 44.5, L(46.5), 0.01), G("total", "OVER", 44.5, L(44.5), 0.02), G("total", "OVER", 46.5, L(44.5), -0.01),
      lb.grade(None), G("total", "OVER", 44.5, ent2)]
t = lb.tally(gs)
ck("tally: verified excludes no-close and ambiguous", t["n"] == 5 and t["verified"] == 3 and t["beat"] == 1 and t["tie"] == 1 and t["loss"] == 1, str(t))
ck("tally: excluded buckets named and counted", t["excluded"] == {"no Pinnacle close": 1, "main line ambiguous": 1})
ck("tally: price denominator only counts known prices", t["price_n"] == 3 and t["price_beat"] == 2)
ck("tally: union counted once per ticket", t["any_n"] == 3 and t["any_beat"] == 2)
ck("pct formats numerator/denominator", lb.pct(1, 4) == "25.0% (1/4)" and lb.pct(0, 0) == "n/a (0/0)")
src = src_all = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "line_beat.py")).read()
# ---- public-log safety: every exclusion label passes the shadow report's label filter unchanged
import prob_clv_shadow as _ps  # noqa: E402
LABELS = ("no Pinnacle close", "main line ambiguous", "total side unknown", "market not graded", "moneyline points not applicable",
          "no line on the ladder", "no limit on the ladder", "placement ladder does not match", "no placement time",
          "placed after start", "no Pinnacle line at placement", "main line ambiguous at placement",
          "no line on the ladder at placement", "no limit on the ladder at placement")
ck("every exclusion label is log-safe (printed, not withheld)", all(_ps.safe_label(x) == x for x in LABELS))
ck("the label list covers every status line_beat can return",
   set(LABELS) >= {s_.split('"')[1] for s_ in src_all.split('status"] = ')[1:] if s_.startswith('"')} | {"no line on the ladder", "no limit on the ladder"} | set(lb.OPEN_REASONS))
# ---- purity
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#")).split('"""', 2)[2]
ck("pure: no import of any module at all", "import " not in code)
ck("pure: no file or network access", "open(" not in code and "urllib" not in code and "requests" not in code)

print(f"{len(OK)} passed, {len(BAD)} failed")
for x in BAD:
    print("FAIL", x)
sys.exit(1 if BAD else 0)
