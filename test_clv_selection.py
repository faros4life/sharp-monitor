#!/usr/bin/env python3
"""
STAGE 2 REGRESSION (Peter, Nov 13 2026): one selection is one CLV observation.

Pins the Nov 12 shape that produced the defect - Toronto @ Philadelphia Under 223.5 filled on
ProphetX in 13 pieces, each its own certified row - plus dup_of, identity-not-price grouping,
and the guarantees that nothing is deleted and nothing is merged on a guess.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_selection as cs   # noqa: E402

BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def fill(stake, pay, clv, close=0.52, game="Toronto Raptors @ Philadelphia 76ers",
         bet="Under 223.5", lg="NBA", **kw):
    s = {"league": lg, "game": game, "bet": bet, "book": "ProphetX", "source": "bot",
         "stake": stake, "to_pay": pay, "game_start": "2026-11-13T00:00:00Z"}
    s.update(kw.pop("snap", {}))
    return {"clv": clv, "close_p": close, "snap": s, "how": "own line", **kw}


def main():
    print("1. thirteen ProphetX fills of one bet collapse to ONE observation")
    bets = {f"px|{300 + i}": fill(10.0, 20.4, 0.0141 + i * 0.0001) for i in range(13)}
    obs = cs.selections(bets)
    check("one selection", len(obs) == 1, list(obs))
    o = list(obs.values())[0]
    check("n_fills records all 13", o["n_fills"] == 13, o["n_fills"])
    check("stake is the summed position", o["stake"] == 130.0, o["stake"])
    check("built from the position, not a mean of CLVs",
          o["basis"].startswith("position"), o["basis"])
    # 13 x $10 -> $130 staked, 13 x $20.40 -> $265.20 payout, so dec = 2.04; close 0.52
    check("clv is close x position price - 1", abs(o["clv"] - (0.52 * 2.04 - 1)) < 1e-9, o["clv"])
    check("stats counts one observation, not 13", cs.stats([o])["n"] == 1)
    check("stats still reports the 13 fills", cs.stats([o])["fills"] == 13)

    print("2. no fill is deleted and no input dict is mutated")
    before = {k: dict(v) for k, v in bets.items()}
    cs.selections(bets)
    check("every original row still present", set(bets) == set(before), "rows changed")
    check("rows unchanged", all(bets[k]["clv"] == before[k]["clv"] for k in bets))
    check("ids of every fill are kept on the observation", len(o["ids"]) == 13, len(o["ids"]))

    print("3. different lines are DIFFERENT selections")
    bets = {"a": fill(100, 190, 0.02, bet="Under 223.5"),
            "b": fill(100, 190, 0.02, bet="Under 224.5")}
    check("two lines -> two selections", len(cs.selections(bets)) == 2)

    print("4. opposite sides are different selections")
    bets = {"a": fill(100, 190, 0.02, bet="Under 223.5"),
            "b": fill(100, 190, 0.02, bet="Over 223.5")}
    check("over and under do not merge", len(cs.selections(bets)) == 2)

    print("5. different games do not merge, same game across venues does")
    bets = {"a": fill(100, 190, 0.02, game="Toronto Raptors @ Philadelphia 76ers"),
            "b": fill(100, 190, 0.02, game="Boston Celtics @ New York Knicks")}
    check("different games -> two selections", len(cs.selections(bets)) == 2)
    bets = {"nv|1": fill(100, 190, 0.02, game="Toronto Raptors @ Philadelphia 76ers"),
            "px|2": fill(100, 190, 0.03, game="Philadelphia 76ers v Toronto Raptors")}
    check("same game, two venues -> one selection", len(cs.selections(bets)) == 1,
          list(cs.selections(bets)))

    print("6. dup_of is honoured, and by IDENTITY not price")
    bets = {"nv|x": fill(200, 380, 0.01, game="Charlotte Hornets @ Phoenix Suns", bet="Under 214.5"),
            "mn|y": fill(200, 380, 0.01, game="Hornets at Suns", bet="Under 214.5 (+100)")}
    tracker = {"nv|x": {"league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns", "bet": "Under 214.5"},
               "mn|y": {"dup_of": "nv|x", "league": "NBA", "game": "Hornets at Suns", "bet": "Under 214.5 (+100)"}}
    obs = cs.selections(bets, tracker)
    check("note and venue row collapse to one", len(obs) == 1, list(obs))
    check("the collapse is attributed to dup_of",
          any(str(v.get("why", "")).startswith("dup_of") for v in obs.values()),
          [v.get("why") for v in obs.values()])

    print("7. a dup_of chain that does not resolve still keeps its row")
    bets = {"mn|z": fill(50, 95, 0.01)}
    tracker = {"mn|z": {"dup_of": "nv|missing"}}
    obs = cs.selections(bets, tracker)
    check("unresolvable dup_of falls back to own identity", len(obs) == 1, list(obs))
    check("row is not dropped", list(obs.values())[0]["n_fills"] == 1)

    print("8. unparsable bet text is never merged into a neighbour")
    bets = {"a": fill(100, 190, 0.02, bet="Under 223.5"),
            "weird": fill(100, 190, 0.02, bet="")}
    obs = cs.selections(bets)
    check("unparsable row keeps its own selection", len(obs) == 2, list(obs))
    check("and is labelled UNIDENTIFIED",
          any(k.startswith("UNIDENTIFIED|") for k in obs), list(obs))

    print("9. the fallback is used and MARKED when stake/payout cannot be summed")
    bets = {"a": fill(None, None, 0.10), "b": fill(None, None, 0.00)}
    o2 = list(cs.selections(bets).values())[0]
    check("fallback basis is explicit", o2["basis"].startswith("FALLBACK"), o2["basis"])
    check("equal-weighted mean when no stake anywhere", abs(o2["clv"] - 0.05) < 1e-9, o2["clv"])
    bets = {"a": fill(300, None, 0.10), "b": fill(100, None, 0.00)}
    o3 = list(cs.selections(bets).values())[0]
    check("stake-weighted when stakes exist but payouts do not",
          abs(o3["clv"] - 0.075) < 1e-9, o3["clv"])

    print("10. rows with no CLV never create an observation")
    bets = {"a": {"snap": {"league": "NBA", "game": "A @ B", "bet": "Under 1.5"}}}
    check("unscored selection is absent", cs.selections(bets) == {}, cs.selections(bets))

    print("11. excluded ids are honoured")
    bets = {f"px|{i}": fill(10, 20.4, 0.01) for i in range(3)}
    check("exclusion drops the row from the group",
          list(cs.selections(bets, exclude={"px|0"}).values())[0]["n_fills"] == 2)

    print("12. halves() reports what it could not place")
    rows = [{"clv": 0.01, "game_start": "2026-11-01T00:00:00Z"},
            {"clv": 0.02, "game_start": "2026-11-05T00:00:00Z"},
            {"clv": 0.03}]
    h1, h2, nod = cs.halves(rows)
    check("undated rows are returned, not silently dropped", len(nod) == 1, nod)
    check("halves split the dated rows", len(h1) + len(h2) == 2, (h1, h2))

    print("13. ROI is never fabricated when profit is absent")
    rows = [{"clv": 0.01, "stake": 100.0, "result": "L"}]
    st_ = cs.stats(rows)
    check("roi_pct is None when no row carries profit", st_["roi_pct"] is None, st_["roi_pct"])
    check("has_profit counts zero", st_["has_profit"] == 0, st_["has_profit"])
    check("profit is None, not 0.0", st_["profit"] is None, st_["profit"])
    rows = [{"clv": 0.01, "stake": 100.0, "result": "W", "profit": 25.0}]
    st_ = cs.stats(rows)
    check("roi_pct computed when profit exists", abs(st_["roi_pct"] - 25.0) < 1e-9, st_["roi_pct"])

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all Stage 2 selection checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
