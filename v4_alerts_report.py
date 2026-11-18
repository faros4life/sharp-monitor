#!/usr/bin/env python3
"""BOARD V4 ALERTS - read-only. The V4 gate applied to the board alert population (Peter, Nov 18).

Not the V3 shadow population: every row here is a board PLAY call that reached an order, split by whether
executor.board_v4() confirms it from the alert's OWN stored alert-time evidence.

The population filter and the certified-CLV path are live_backtest's, reproduced here ONLY so that each
row keeps its call key - the first version of this file matched rows back to keys by timestamp and left 33
of 88 rows unresolvable, and those 33 carried nearly all the profit. A reader that drops a third of the
population non-randomly is the suspect, not the data.

READ-ONLY. Buys nothing, writes nothing, dispatches nothing, touches no live setting.

CAUTION, kept in the output: V4's rule was FOUND in the retro window, so the retro split is in-sample and
cannot confirm itself. Only rows at or after activation are out-of-sample.
"""
import collections
import sys
from datetime import timedelta

import clv_scorecard as sc
import executor as ex
import live_backtest as lb

V4_LIVE = "2026-11-17T19:00:00Z"   # EXEC_BOARD_V4 switched on (Peter, 17 Nov evening ET)


def population(C, pc, lc, feed, drop):
    """live_backtest.board_plays, with the call key carried on every row."""
    out, seen = [], set()
    for k, x in sorted(C.items(), key=lambda kv: kv[1].get("at") or ""):
        if x.get("call") != "PLAY" or x.get("mk") != "total" or (x.get("league") or x.get("lg")) != "NBA":
            continue
        src, at = feed.get(k), lb._t(x.get("at"))
        if src is None:
            drop["no source alert"] += 1
            continue
        pu = lb._t(src.get("pulled_utc")) if src.get("pulled") else None
        if pu and at and pu <= at + timedelta(minutes=lb.BOARD_CONFIRM_MIN):
            drop["pulled within 15 min"] += 1
            continue
        g = (x.get("day"), frozenset(sc.toks(x.get("game"))))
        if g in seen:
            continue
        seen.add(g)
        if x.get("result") not in ("W", "L", "P"):
            continue
        try:
            dec = sc.cs.net_dec(sc.cs.canon(x.get("book")), sc.cl.am_to_dec(float(x.get("price"))))
        except Exception:
            dec = None
        ok, why, evid = ex.board_v4(src)
        out.append({"key": k, "ts": x.get("at") or "", "day": x.get("day") or lb.et_day(x.get("at")),
                    "res": x["result"], "dec": dec, "clv": lb.cert_clv(pc, lc, f"liq|{k}", aid=k),
                    "recon": bool(x.get("recon")), "lg": "NBA",
                    "v4": bool(ok), "v4_why": why, "v4_evid": evid})
    return out


def main():
    C = lb.load("board/calls.json", "calls") or {}
    import board_build as bb
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    pc = (lb.load("paper/clv_certified.json") or {}).get("certified") or {}
    lc = (lb.load("liquidity/clv_certified.json") or {}).get("certified") or {}
    drop = collections.Counter()

    rows = population(C, pc, lc, feed, drop)
    conf = [r for r in rows if r["v4"]]
    rej = [r for r in rows if not r["v4"]]

    print("BOARD V4 ALERTS - read-only | the V4 gate on the board alert population")
    print(f"  population {len(rows)} settled board PLAY calls that reached an order "
          f"-> {len(conf)} V4-confirmed, {len(rej)} V4-rejected (every row resolved; none dropped)")
    print(f"  V4 activated {V4_LIVE}; rows at/after that are OUT-OF-SAMPLE, earlier rows IN-SAMPLE")
    print(f"  excluded by persistence/source: {dict(drop)}")
    print()
    for lab, L in (("V4 CONFIRMED", conf), ("V4 REJECTED", rej)):
        print(lb.line(f"{lab} - all", lb.summ(L)))
        print(lb.line("  in-sample (retro)", lb.summ([r for r in L if r["ts"] < V4_LIVE])))
        print(lb.line("  OUT-OF-SAMPLE (live)", lb.summ([r for r in L if r["ts"] >= V4_LIVE])))
        print()
    why = collections.Counter((r["v4_why"] or "?").split("(")[0].strip()[:58] for r in rej)
    print("  why rejected, within this population:")
    for w, n in why.most_common(8):
        print(f"    {n:4} x {w}")
    print()
    print("  CAUTION: V4's rule was found in the retro window, so the in-sample split cannot confirm it.")
    print("  Judge V4 on the OUT-OF-SAMPLE lines and on the sample size beside them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
