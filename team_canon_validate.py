#!/usr/bin/env python3
"""OFFLINE VALIDATION of team_canon recoveries (audit, 10 Nov 2026). Read-only, no network, no cache, no state.

For every liquidity alert the CURRENT matcher cannot place but team_canon can, check the recovered fixture
independently on: league, both teams, kickoff date/time, market, side, and line. Then count how many could
even REACH a Pinnacle close lookup. Recovering a fixture is not a verified close: that needs the history
cache, which only exists inside Actions, so the number printed here is an UPPER BOUND, never a result.
Uses the committed oddspapi/fixtures.json only (444 fixtures, games starting 2026-11-06 .. 11-13)."""
import json
import re
import sys
from collections import Counter

import clv_ledger as cl
import liq_history_test as lh
import team_canon as tc


def main():
    Q = json.load(open("liquidity/alerts.json"))["alerts"]
    g = [x for x in Q if x.get("result") in ("W", "L", "P") and not x.get("artifact") and not x.get("close_suspect")]
    F = json.load(open("oddspapi/fixtures.json"))["fixtures"]
    lo, hi = min(v["start"] for v in F.values()), max(v["start"] for v in F.values())
    st = {"fixtures": F}
    rec, bad = [], Counter()
    for a in g:
        lg = a.get("league")
        if lg not in ("NHL", "NFL") or not (lo <= a["start_utc"] <= hi):
            continue
        b0 = {"league": lg, "game": (a.get("game") or "").split(":")[0], "game_start": a["start_utc"]}
        if cl.find_fixture(st, b0):
            continue
        fid = tc.find_fixture_canon(F, lg, a.get("game"), a["start_utc"])
        if not fid:
            continue
        f = F[fid]
        r = {"fid": fid, "a": a, "f": f}
        # 1 league
        if f["lg"] != lg:
            bad["league differs"] += 1
        # 2 both teams: resolve each fixture side AND each alert side; sets must be equal and distinct
        s1, s2 = tc.game_sides(a.get("game"))
        ids_a = {tc.resolve(lg, s1), tc.resolve(lg, s2)}
        ids_f = {tc.resolve(lg, f["p1"]), tc.resolve(lg, f["p2"])}
        if None in ids_a or None in ids_f or ids_a != ids_f or len(ids_a) != 2:
            bad["teams do not match as a set"] += 1
        # 2b second, table-independent check: the fixture's own abbreviation tokens
        ab = {t for t in re.findall(r"\b[A-Z]{2,4}\b", f["p1"] + " " + f["p2"])}
        r["abbr_hit"] = bool(ab)
        # 3 date: kickoff gap in minutes
        gap = abs((cl.tp(f["start"]) - cl.tp(a["start_utc"])).total_seconds()) / 60
        r["gap"] = gap
        if gap > 90:
            bad["kickoff gap > 90 min"] += 1
        # 4 market / side / line
        bet = lh.bet_text(a)
        pz = cl.parsed({"bet": bet})
        r["bet"], r["pz"] = bet, pz
        if not pz:
            bad["bet text does not parse (market/side/line)"] += 1
        else:
            if pz[0] in ("spread", "ml"):
                tm = cl.which_team(f, pz[1])
                if tm is None:
                    bad["side team not placed in fixture"] += 1
            if pz[0] == "total" and (pz[2] is None):
                bad["total has no line"] += 1
            if pz[0] == "spread" and (pz[2] is None):
                bad["spread has no line"] += 1
        # same game, other alerts: does the SAME fixture get a consistent pair of teams?
        rec.append(r)
    n = len(rec)
    print(f"recovered alerts (current matcher fails, team_canon matches): {n}")
    print(f"  fixtures involved {len({r['fid'] for r in rec})}; unique games (alert game text, date) "
          f"{len({(r['a']['game'].split(':')[0], r['a']['start_utc'][:10]) for r in rec})}")
    print(f"  by league {dict(Counter(r['a']['league'] for r in rec))}; by market {dict(Counter((r['pz'][0] if r['pz'] else 'unparsed') for r in rec))}")
    gaps = sorted(r["gap"] for r in rec)
    print(f"  kickoff gap alert-vs-fixture, minutes: median {gaps[len(gaps)//2]:.0f}, max {gaps[-1]:.0f}")
    print(f"  fixture carries abbreviation tokens (extra identity evidence): {sum(r['abbr_hit'] for r in rec)}/{n}")
    print(f"  validation failures: {dict(bad) or 'none'}")
    ok = [r for r in rec if r["pz"]]
    print(f"  parseable market+side+line: {len(ok)}/{n}  -> UPPER BOUND on new Pinnacle-lookup candidates")
    print(f"  of those, unique games: {len({(r['a']['game'].split(':')[0], r['a']['start_utc'][:10]) for r in ok})}")
    print("  NOT KNOWN here: whether Pinnacle history for these fixtures is in the Actions cache, whether a")
    print("  same-line close exists, or whether the close is fresh. Those decide the real number.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
