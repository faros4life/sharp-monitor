#!/usr/bin/env python3
"""R1 live lane tests (Peter, 11 Nov). Offline: no secrets, no network, no order path. Nothing here can place a bet."""
import json, os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("EXEC_LIVE", "off")
os.environ.setdefault("EXEC_R1_LIVE", "off")
import agree_rules as AR
import executor as X

FAIL = []


def ck(name, cond, extra=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAIL.append(name)


now = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)
iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
base = {"book_key": "prophetx", "sport": "NCAAF", "top25": False, "kind": "spr", "bet": "Ohio State -3.5 (-110)",
        "late": False, "confirmed_by": ["BetOnline"], "price_after_fee": -112,
        "alert_utc": iso(now), "start_utc": iso(now + timedelta(hours=6)), "game": "Michigan @ Ohio State"}

print("A. R1 predicate")
ck("base spread qualifies", AR.r1(base)[0], str(AR.r1(base)[1]))
ck("NCAAB spread qualifies", AR.r1(dict(base, sport="NCAAB"))[0])
ck("totals under qualifies", AR.r1(dict(base, kind="tot", bet="Under 55 (-110)"))[0])
ck("totals OVER refused", not AR.r1(dict(base, kind="tot", bet="Over 55 (-110)"))[0])
ck("moneyline refused", not AR.r1(dict(base, kind="ml"))[0])
ck("Hard Rock-priced refused", not AR.r1(dict(base, book_key="hardrockbet"))[0])
ck("Novig-priced refused", not AR.r1(dict(base, book_key="novig"))[0])
ck("Top 25 refused (Lane 1's)", not AR.r1(dict(base, top25=True))[0])
ck("untagged Top 25 refused", not AR.r1(dict(base, top25=None))[0])
ck("NBA refused", not AR.r1(dict(base, sport="NBA"))[0])
ck("late refused", not AR.r1(dict(base, late=True))[0])
ck("Matchbook-only refused", not AR.r1(dict(base, confirmed_by=["Matchbook"]))[0])
ck("BetOnline+Matchbook allowed", AR.r1(dict(base, confirmed_by=["BetOnline", "Matchbook"]))[0])
ck("3h lead refused", not AR.r1(dict(base, start_utc=iso(now + timedelta(hours=3))))[0])
ck("exactly 4h lead allowed", AR.r1(dict(base, start_utc=iso(now + timedelta(hours=4))))[0])
ck("20h lead allowed (12-24h window is paper for Lane 1, not R1)", AR.r1(dict(base, start_utc=iso(now + timedelta(hours=20))))[0])
ck("-119 allowed", AR.r1(dict(base, price_after_fee=-119))[0])
ck("-120 refused", not AR.r1(dict(base, price_after_fee=-120))[0])
ck("missing price refused (fail closed)", not AR.r1(dict(base, price_after_fee=None))[0])
ck("muted alert is still eligible (sent_to_phone ignored)", AR.r1(dict(base, sent_to_phone=False))[0])

print("\nB. Lane 1 and the board are untouched")
ck("Lane 1 unit 300", X.LIVE_UNIT == 300.0 and X.unit_for(None) == 300.0 and X.unit_for("rules") == 300.0)
ck("board unit 200", X.unit_for("board") == 200.0)
ck("R1 unit 200", X.R1_UNIT == 200.0 and X.unit_for("r1") == 200.0)
ck("R1 -110 risks 220 to win 200", X.live_stake(-110, X.R1_UNIT) == (220.0, 200.0))
ck("R1 +150 risks 200 to win 300", X.live_stake(150, X.R1_UNIT) == (200.0, 300.0))
ck("phase1 unchanged: NCAAF Top-25 ProphetX under still live-eligible",
   AR.phase1(dict(base, top25=True, kind="tot", bet="Under 55 (-110)"), True)[0])
ck("phase1 unchanged: R1's own spread is NOT Lane 1", not AR.phase1(base, True)[0])
ck("R1 switch is OFF by default", X.R1_LIVE is False)

print("\nC. r1_gate: own limit, fail closed")
X.R1.update(risk=0.0, keys=set(), known=False)
ck("unknown exposure refuses", not X.r1_gate(220.0, "k1")[0])
X.R1.update(known=True)
ck("fresh day passes", X.r1_gate(220.0, "k1")[0])
X.R1.update(risk=800.0, keys={"a", "b", "c"})
ck("800 + 220 > 1000 refused", not X.r1_gate(220.0, "k9")[0])
ck("800 + 190 = 990 passes", X.r1_gate(190.0, "k9")[0])
X.R1.update(risk=0.0, keys={f"p{i}" for i in range(X.R1_MAX_PLAYS)})
ck("play cap refuses a new key", not X.r1_gate(220.0, "new")[0])
ck("same key (retry/top-up) not counted as extra", X.r1_gate(220.0, "p0")[0])
ck("zero/garbage risk refused", not X.r1_gate(0, "k")[0] and not X.r1_gate("x", "k")[0])
X.R1.update(risk=0.0, keys=set(), known=False)

print("\nD. r1_plays reads muted alerts, first alert only")
import tempfile
a1 = dict(base, sent_to_phone=False)
a2 = dict(base, sent_to_phone=False, alert_utc=iso(now + timedelta(minutes=20)), price_after_fee=-115)   # repeat alert, same play
a3 = dict(base, sent_to_phone=False, game="Texas @ Oklahoma", bet="Oklahoma -7 (-110)")
a4 = dict(base, book_key="hardrockbet", game="X @ Y", bet="Y -2 (-110)")
d = tempfile.mkdtemp(); cwd = os.getcwd(); os.chdir(d)
json.dump({"alerts": [a1, a2, a3, a4]}, open("alerts.json", "w"))
try:
    out = X.r1_plays(now + timedelta(minutes=30))
finally:
    os.chdir(cwd)
ck("2 plays (repeat collapsed, Hard Rock dropped)", len(out) == 2, str(len(out)))
ck("source r1, key namespace r1|", all(p["source"] == "r1" and p["play_key"].startswith("r1|") for p in out))
ck("first alert wins (price -112, not the repeat)", out and out[0]["r1_entry"]["price_after_fee"] == -112)

print("\nE. real data: R1 selects exactly the cherry-picked set")
feed = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alerts.json")))["alerts"]
hit = [e for e in feed if e.get("units_flat") is not None and AR.r1(e)[0]]
print(f"  R1 on graded history: {len(hit)} plays, {sum(e['units_flat'] for e in hit):+.2f}u")
ck("selects a non-empty, mostly-spread set", len(hit) > 20 and sum(1 for e in hit if e["kind"] == "spr") >= 20)

print("\nFAILED: " + ", ".join(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)
