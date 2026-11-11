"""Every live play alerts to the phone, all three lanes (Peter, Nov 11).

R1's own signal alerts are MUTED upstream by the non-Top-25 filter, so before this the first
notification for an R1 play was its FILL - money moved before Peter saw the play. The alert now
fires for every lane at the moment the order is about to go in, and the fill/partial/refusal/error
notes still follow.
"""
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


SENT = []
_push, _tg = ex.push, ex.tg
ex.push = lambda t, b, mirror=True: SENT.append((t, b, mirror))
ex.tg = lambda *a, **k: SENT.append(("TG", a[0] if a else "", None))


def r_for(lane, src, bk="novig", af=-115, shown=-115, am=-117, risk=234.0, win=200.0, partial=False):
    return {"play": {"sport": "NCAAF", "game": "Army @ Navy", "bet": "Under 44.5 (-115)", "source": src},
            "live": {"lane": lane, "book": bk, "line": 44.5, "am": am, "shown": shown,
                     "risk": risk, "to_win": win, "partial": partial},
            "entry": {"price_after_fee": af}}


# ---------------------------------------------------------------- fires for every lane
for lane, src, tag in (("r1", "r1", "[R1]"), ("board", "board", "[BOARD V3]"), (None, "rules", "[PHASE 1]")):
    SENT.clear()
    ex.live_play_alert(r_for(lane, src))
    ck(f"{tag} live play alerts", len(SENT) == 1, str(len(SENT)))
    title, body, mirror = SENT[0]
    ck(f"{tag} title is lane-labelled LIVE PLAY", title.startswith(f"{tag} LIVE PLAY"), title)
    ck(f"{tag} mirrors to Telegram", mirror is True)
    for needle, what in (("Army @ Navy", "game"), ("Under 44.5", "bet"), ("line 44.5", "line"),
                         ("alert -115 after fees", "after-fee alert odds"),
                         ("Novig", "exchange"), ("proposed stake $234.00", "proposed stake")):
        if what == "exchange" and lane != "r1":
            continue
        ck(f"{tag} carries the {what}", needle in body, body)
    ck(f"{tag} says how to pause", "STOP on ntfy" in body)

# ---------------------------------------------------------------- content edge cases
SENT.clear()
ex.live_play_alert(r_for("r1", "r1", partial=True))
ck("a short-depth play warns PARTIAL expected", "PARTIAL expected" in SENT[0][1], SENT[0][1])
SENT.clear()
ex.live_play_alert(r_for("r1", "r1", af=None))
ck("a missing alert price omits the line rather than printing junk",
   "after fees" not in SENT[0][1].split("routing")[0], SENT[0][1])
ck("  and still names the exchange and stake",
   "Novig" in SENT[0][1] and "proposed stake" in SENT[0][1], SENT[0][1])
SENT.clear()
ex.live_play_alert({"play": {}, "live": {}, "entry": {}})
ck("a degenerate play still alerts as PHASE 1 rather than raising",
   len(SENT) == 1 and SENT[0][0].startswith("[PHASE 1] LIVE PLAY"), str(SENT))

# ---------------------------------------------------------------- wired, all lanes, before the order
mb = inspect.getsource(ex.main)
ck("the alert fires in the dispatch block", "live_play_alert(r)" in mb)
ck("it is NOT gated to one lane",
   'lane_of(r) == "r1"' not in mb.split("live_play_alert(r)")[0][-400:])
ck("it fires BEFORE the order", mb.index("live_play_alert(r)") < mb.index('r["live"]["order"] = live_order(r)'))
ck("it only fires on a play that is actually going live",
   'get("go")' in mb.split("live_play_alert(r)")[0][-400:])
ck("an alert failure can never block the order", "never block the order" in mb)
ck("the failure is printed, not raised", "live play alert failed" in mb)

# ---------------------------------------------------------------- no duplicates
# code only: the docstring says "push()" and a substring count reads that as a call
import ast as _ast  # noqa: E402
_t = _ast.parse(inspect.getsource(ex.live_play_alert))
for _n in _ast.walk(_t):
    if isinstance(_n, (_ast.FunctionDef, _ast.Module)) and _ast.get_docstring(_n):
        _n.body = _n.body[1:]
_code = _ast.unparse(_t)
ck("one push per play (push mirrors once to Telegram)", _code.count("push(") == 1, str(_code.count("push(")))
ck("the play alert does not also call tg() directly", "tg(" not in _code)
ck("cross-run dedupe: a play is processed once (already_handled greps the pid)",
   "gsearch_strict(M, pid(" in inspect.getsource(ex.already_handled))
ck("R1 plays use the game+side key namespace, so a re-sent alert never re-alerts",
   '("rules", "lane2")' in inspect.getsource(ex.already_handled))
ck("the outcome notes are separate events, still sent",
   'lane_note(r, "FILLED"' in inspect.getsource(ex.live_order))

# ---------------------------------------------------------------- nothing about betting changed
ck("units unchanged", (ex.LIVE_UNIT, ex.BOARD_UNIT, ex.R1_UNIT) == (300.0, 200.0, 200.0))
ck("caps unchanged", ex.BOARD_MAX_PLAYS == 10 and ex.R1_MAX_PLAYS == 10)
ck("limits unchanged", ex.BOARD_DAILY_RISK == 1500.0 and ex.R1_DAILY_RISK == 1500.0)
ck("global stop unchanged", ex.px_live.DAILY_STOP == 2250.0)
ck("tolerance unchanged", ex.TOL_BOOKS == ("prophetx", "novig") and ex.PX_TOL_CENTS == 2)
ck("cap unchanged", ex.CAP_LINE == -130)
ck("live_play_alert places nothing",
   not any(w in inspect.getsource(ex.live_play_alert) for w in ("place(", "submit_order", "_place(")))
ck("it does not touch qualification",
   not any(w in inspect.getsource(ex.live_play_alert) for w in ("phase1(", "agree_rules.r1", "r1_gate", "board_gate")))

ex.push, ex.tg = _push, _tg
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
