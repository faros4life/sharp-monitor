#!/usr/bin/env python3
"""
Regression tests for the three defects Peter found reviewing the CLV code on Nov 6.

1. LOOK-AHEAD BIAS. clv_report read the book as of t0 + QUOTE_MAX_AGE_S, i.e. up to 15 minutes
   AFTER the alert fired. Opportunity CLV must use only prices available at or before the alert.
2. CONTEXT NOT PROPAGATED. clv_std.net_dec() did not pass league or live into exchange_lag.eff(),
   so ProphetX NHL was priced on the 2%-of-gains commission instead of its 0.035/0.01 maker-taker
   scale, and a Novig live or futures take was priced at zero instead of 0.06.
3. INCONSISTENT CLOSE FRESHNESS. clv_ledger.close_for() dropped a spreads/totals candidate older
   than FRESH_MIN but computed the same age on the moneyline path and ignored it.

These run with no secrets, no network and no cache - they test the rules, not the data.
"""
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import exchange_lag as el

OK, BAD = [], []


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def main():
    print("REGRESSION - the three defects from Peter's Nov 6 code review\n")

    # ---------------------------------------------------------------- 1. look-ahead
    print("1. LOOK-AHEAD BIAS - a quote after the alert must never be readable")
    t0 = datetime(2026, 11, 1, 18, 0, 0, tzinfo=timezone.utc)
    # a synthetic two-way market: one tick BEFORE the alert, one 10 minutes AFTER it
    before, after = t0 - timedelta(seconds=300), t0 + timedelta(seconds=600)
    def tick(when, price):
        return {"createdAt": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "price": price, "limit": 500}
    pm = {"1": {"outcomes": {
        "a": {"players": {"0": [tick(before, 2.00), tick(after, 1.40)]}},
        "b": {"players": {"0": [tick(before, 2.00), tick(after, 3.20)]}}}}}
    at_alert = cl.two_way(pm, 1, t0)
    check("reading AT the alert returns the pre-alert tick",
          at_alert.get("a", (None,))[0] == 2.00, f"got {at_alert.get('a', ('-',))[0]}")
    later = cl.two_way(pm, 1, t0 + timedelta(seconds=900))
    check("reading at t0+900s WOULD have returned the post-alert tick (the old bug)",
          later.get("a", (None,))[0] == 1.40, f"got {later.get('a', ('-',))[0]}")
    src = open("clv_report.py").read()
    check("clv_report reads at the alert timestamp, not t0 + window",
          "\n        when = t0\n" in src and "when = min(t0 + timedelta" not in src)
    # the price moved 2.00 -> 1.40; pricing off the later tick would misstate the opportunity
    check("the synthetic move is large enough to matter", abs(2.00 - 1.40) > 0.5,
          "a 0.60 decimal swing is ~30% of the price")

    # ---------------------------------------------------------------- 2. context
    print("\n2. CONTEXT PROPAGATION - league and live must reach eff()")
    d = 1.9091                      # -110
    px_nba = cs.net_dec("prophetx", d, league="NBA")
    px_nhl = cs.net_dec("prophetx", d, league="NHL")
    check("ProphetX NHL is priced differently from ProphetX NBA", px_nba != px_nhl,
          f"NBA {px_nba:.4f} vs NHL {px_nhl:.4f}")
    check("ProphetX NHL matches eff()'s NHL taker scale",
          abs(px_nhl - el.eff("prophetx", d, False, False, "NHL")) < 1e-12)
    nv_pre = cs.net_dec("novig", d, live=False)
    nv_live = cs.net_dec("novig", d, live=True)
    check("Novig pre-game take is free", abs(nv_pre - d) < 1e-12, f"{nv_pre:.4f}")
    check("Novig LIVE take is not free", nv_live < d - 1e-6,
          f"live {nv_live:.4f} vs raw {d:.4f}, drag {(d - nv_live) / d * 100:.2f}%")
    check("net_clv carries the context too",
          cs.net_clv(0.52, d, "prophetx", league="NHL") != cs.net_clv(0.52, d, "prophetx", league="NBA"))
    # ProphetX alone, so the league actually drives the winning net price. With Novig in the set
    # Novig wins both at 1.91 and the league is invisible - which is how the first version of this
    # test failed while the code was right.
    q = {"prophetx": 1.91}
    nhl_b, nhl_n, _ = cs.best_net(q, "auto", league="NHL")
    nba_b, nba_n, _ = cs.best_net(q, "auto", league="NBA")
    check("best_net carries the context too", nhl_n != nba_n,
          f"NHL {nhl_n:.4f} vs NBA {nba_n:.4f}")
    check("defaults are unchanged, so no existing caller moves",
          abs(cs.net_dec("prophetx", d) - el.eff("prophetx", d)) < 1e-12
          and abs(cs.net_dec("novig", d) - d) < 1e-12)

    # ---------------------------------------------------------------- 3. close freshness
    print("\n3. CLOSE FRESHNESS - the moneyline path must obey the same limit as spreads/totals")
    src = open("clv_ledger.py").read()
    ml = src[src.index('return None, "no Pinnacle moneyline close"'):src.index('# spreads / totals:')]
    check("the moneyline branch now tests age against FRESH_MIN",
          "age > FRESH_MIN" in ml)
    check("and it returns a named reason rather than a stale close",
          "moneyline close older than the freshness limit" in ml)
    check("spreads/totals still enforce it", "if age > FRESH_MIN:" in src[src.index('# spreads / totals:'):])
    check("FRESH_MIN is unchanged - the rule was not loosened to make this pass",
          cl.FRESH_MIN == 24 * 60, f"FRESH_MIN={cl.FRESH_MIN}")

    # ---------------------------------------------------------------- 4. the final three
    print("\n4. FINAL THREE - partial coverage, invalid-data exclusions, pregame verification")
    rpt = open("clv_report.py").read()
    check("Pinnacle alone is required; exchanges are whatever is held",
          'os.path.exists(hc._path(fid, "pinnacle"))' in rpt
          and "have = [x for x in EXCH if os.path.exists(hc._path(fid, x))]" in rpt
          and 'for x in ("pinnacle",) + EXCH' not in rpt)
    check("get_hist is asked ONLY for cached books - the zero-credit guard",
          'hc.get_hist(fid, ["pinnacle"] + have, start)' in rpt
          and 'hc.get_hist(fid, ["pinnacle"] + list(EXCH)' not in rpt)
    check("the quote loop iterates the held books, not all of EXCH",
          "for slug in have:" in rpt and "for slug in EXCH:" not in rpt)
    check("missing coverage is recorded and reported",
          "missing_book[" in rpt and "EXCHANGE COVERAGE" in rpt)
    check("close_suspect is excluded, alongside the existing artifact flag",
          'not a.get("close_suspect")' in rpt and 'not a.get("artifact")' in rpt)
    # count flags inside the POPULATION comprehension only - a later counting line that mentions
    # the same key is not a filter, which is what the first version of this check got wrong
    comp = rpt[rpt.index("A = [a for a in pop"):rpt.index("n_artifact =")]
    check("no NEW filter was invented - only the two established flags gate the population",
          comp.count("and not a.get(") == 2
          and 'not a.get("artifact")' in comp and 'not a.get("close_suspect")' in comp,
          f"{comp.count('and not a.get(')} exclusion flags in the population filter")
    check("pregame is VERIFIED, not assumed", "in_play = bool(start) and t0 >= start" in rpt)
    check("the verified status drives the fee schedule", "live=in_play" in rpt
          and "live=False)" not in rpt.split("in_play = ")[1][:600])
    check("in-play rows are counted and reported", "n_inplay" in rpt and "in_play" in rpt)
    # the pregame flag must actually change the price on a Novig take
    check("in_play changes a Novig take's net price",
          cs.net_dec("novig", 1.9091, live=True) < cs.net_dec("novig", 1.9091, live=False) - 1e-6,
          f"pregame {cs.net_dec('novig', 1.9091, live=False):.4f} vs "
          f"in-play {cs.net_dec('novig', 1.9091, live=True):.4f}")

    print(f"\n{len(OK)} passed, {len(BAD)} failed")
    if BAD:
        for b in BAD:
            print(f"  FAILED: {b}")
        return 1
    print("ALL REGRESSION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
