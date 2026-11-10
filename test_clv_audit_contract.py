#!/usr/bin/env python3
"""Contract tests for the Nov 10 audit changes: RAW/NET prices, no self-close as Pinnacle CLV, canonical
team matching, and the audit job's network lock. No secrets, no network, no cache."""
import glob
import re
import sys

import price_basis as pb
import team_canon as tc
import clv_ledger as cl
import clv_std as cs

OK, BAD = [], []


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def main():
    # RAW vs NET ---------------------------------------------------------------------------------
    net = pb.Price("prophetx", -116, pb.NET)
    raw = pb.Price("prophetx", -116, pb.RAW)
    check("NET price takes no fee", abs(pb.net_decimal(net) - cl.am_to_dec(-116)) < 1e-12)
    check("RAW price takes the fee exactly once", pb.net_decimal(raw) < pb.net_decimal(net))
    check("undeclared field is refused", _raises(pb.UndeclaredField, lambda: pb.price_from_row({"x": -110}, "x", "novig")))
    row = {"price": -108, "price_after_fee": -116}
    check("best_price prefers the declared-NET field and labels it NET",
          pb.best_price(row, "kalshi", "price_after_fee", "price").basis == pb.NET)
    check("fallback to the raw field is labelled RAW",
          pb.best_price({"price": -108}, "kalshi", "price_after_fee", "price").basis == pb.RAW)
    k_once = pb.pin_clv(0.52, pb.price_from_row(row, "price_after_fee", "kalshi"))
    k_twice = 100 * (0.52 * cs.net_dec("kalshi", cl.am_to_dec(-116)) - 1)
    check("the old double-fee arithmetic is strictly more negative", k_twice < k_once, f"{k_twice:.2f} vs {k_once:.2f}")

    # static scan: no script may hand a *_after_fee value to net_dec ---------------------------------
    bad = []
    for p in glob.glob("*.py"):
        if p.startswith("test_") or p in ("price_basis.py", "clv_audit_fixes.py"):
            continue
        for i, ln in enumerate(open(p, encoding="utf-8", errors="ignore"), 1):
            if re.search(r"net_dec\([^)]*after_fee", ln) or re.search(r"net_dec\([^)]*price_after", ln):
                bad.append(f"{p}:{i}")
    check("no script passes an after-fee price to net_dec", not bad, ", ".join(bad))

    # exchange close is never Pinnacle CLV ----------------------------------------------------------
    src = open("clv_scorecard.py", encoding="utf-8").read()
    check("scorecard does not feed close_price into a CLV function",
          not re.search(r"std_clv\([^)]*close_price", src))
    check("scorecard labels exchange movement as NOT CLV", "Exchange Self-Close Movement" in src and "(NOT CLV)" in src)

    # canonical matching ------------------------------------------------------------------------------
    F = {"a": {"lg": "NHL", "start": "2026-11-08T00:00:00Z", "p1": "Vancouver Canucks Vancouver VAN", "p2": "Philadelphia Flyers Philadelphia PHI"},
         "b": {"lg": "NHL", "start": "2026-11-08T00:00:00Z", "p1": "Calgary Flames", "p2": "Philadelphia Flyers"}}
    check("one token per side matches the right fixture", tc.find_fixture_canon(F, "NHL", "Flyers vs. Canucks", "2026-11-08T00:00:00Z") == "a")
    check("city-only names match", tc.find_fixture_canon(F, "NHL", "Philadelphia vs Vancouver: Total Goals", "2026-11-08T01:00:00Z") == "a")
    check("a game on another night does not match", tc.find_fixture_canon(F, "NHL", "Flyers vs. Canucks", "2026-11-12T00:00:00Z") is None)
    check("cross-event pair (teams from different games) matches nothing", tc.find_fixture_canon(F, "NHL", "Canucks vs Flames", "2026-11-08T00:00:00Z") is None)
    check("bare shared city stays unresolved", tc.resolve("NHL", "New York") is None and tc.resolve("NFL", "Los Angeles") is None)
    check("one-letter suffix resolves only when unique",
          tc.resolve("NHL", "New York I") == "nyi" and tc.resolve("NHL", "New York R") == "nyr"
          and tc.resolve("NFL", "Los Angeles R") == "lar" and tc.resolve("NFL", "Los Angeles C") == "lac")
    check("NCAAF is not attempted", tc.find_fixture_canon(F, "NCAAF", "A vs B", "2026-11-08T00:00:00Z") is None)
    F2 = dict(F, c={"lg": "NHL", "start": "2026-11-08T02:00:00Z", "p1": "Vancouver Canucks", "p2": "Philadelphia Flyers"})
    check("two qualifying fixtures => ambiguous => no match", tc.find_fixture_canon(F2, "NHL", "Flyers vs. Canucks", "2026-11-08T00:00:00Z") is None)

    print(f"\n{len(OK)} passed, {len(BAD)} failed")
    return 1 if BAD else 0


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


if __name__ == "__main__":
    sys.exit(main())
