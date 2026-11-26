"""clv_baseline: the decomposition sums exactly, and a fill matches only the identical selection and close."""
import clv_baseline as cb_

fails = 0


def ok(cond, msg):
    global fails
    print(("  ok   " if cond else "  FAIL ") + msg)
    fails += 0 if cond else 1


d = cb_.decompose(0.50, 0.52, 1.95, 1.90)
ok(abs(d["clv"] - 100 * (0.52 * 1.90 - 1)) < 1e-9, "components sum to the certified CLV exactly")
ok(abs(d["baseline"] - 100 * (0.50 * 1.90 - 1)) < 1e-9, "baseline = alert fair x after-fee entry - 1")
ok(abs(d["fee"] - 100 * 0.5 * (1.90 - 1.95)) < 1e-9 and d["fee"] < 0, "fee is the after-fee shortfall, negative")
ok(abs(d["move"] - (d["clv"] - d["baseline"])) < 1e-9, "baseline-adjusted CLV is the movement after the alert")
z = cb_.decompose(0.5, 0.5, 1.909, 1.909)
ok(abs(z["move"]) < 1e-12 and z["clv"] < 0, "no movement at -110 scores below zero: the vig alone")

rows = [("a", "NBA", "2026-11-25", frozenset({"bulls", "hornets"}), cb_.bet_shape("Under 223.5"), 0.51, 1.90)]
f = {"league": "NBA", "day": "2026-11-25", "game": "Chicago Bulls at Charlotte Hornets", "bet": "Under 223.5",
     "pin": 0.511, "net": 1.95, "am": -105, "res": "W", "venue": "novig"}
ok(cb_.match_fills([f], rows).get("a") is f, "same league, day, total side, line and close -> matched")
ok(not cb_.match_fills([dict(f, bet="Over 223.5")], rows), "other side -> not matched")
ok(not cb_.match_fills([dict(f, bet="Under 224.5")], rows), "other line -> not matched")
ok(not cb_.match_fills([dict(f, pin=0.53)], rows), "different close -> not matched")
ok(not cb_.match_fills([dict(f, day="2026-11-26")], rows), "different day -> not matched")
ok(not cb_.match_fills([dict(f, game="Lakers at Celtics")], rows), "different game -> not matched")

print("FAILED" if fails else "all passed")
raise SystemExit(1 if fails else 0)
