#!/usr/bin/env python3
"""
SHARED BASIS REGRESSION (Peter, Nov 14 2026): one versioned calculation, both systems.

Pins that clv_basis.clv is the arithmetic the live ledger already performs, that the basis is
versioned and stamped, that the two entry-price functions are kept distinct on purpose, and that
nothing falls back to a half-point conversion.
"""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_basis as cb   # noqa: E402
import clv_ledger as cl  # noqa: E402

BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def main():
    print("1. the arithmetic matches the ledger's own line, exactly")
    for p, d in ((0.5067, 1.9608), (0.4909, 2.0), (0.5527, 1.8519), (0.33, 1.5), (0.9, 1.11)):
        check(f"p={p} d={d}", cb.clv(p, d) == round(p * d - 1, 4), (cb.clv(p, d), round(p * d - 1, 4)))

    print("2. rounding happens once, from full precision")
    p_full = cl.novig_p(1.9090, 1.9610)
    check("Dallas is -0.0064 from full precision", cb.clv(p_full, 1.9608) == -0.0064,
          cb.clv(p_full, 1.9608))
    check("and -0.0065 from the rounded close", cb.clv(0.5067, 1.9608) == -0.0065,
          cb.clv(0.5067, 1.9608))

    print("3. missing inputs give None, never a substitute")
    check("no close -> None", cb.clv(None, 1.9) is None)
    check("no entry -> None", cb.clv(0.5, None) is None)
    check("garbage -> None", cb.clv("x", 1.9) is None)

    print("4. the basis is versioned and stamped")
    check("version present", bool(cb.BASIS_VERSION) and "." in cb.BASIS_VERSION, cb.BASIS_VERSION)
    check("stamp names the version", cb.BASIS_VERSION in cb.stamp(), cb.stamp())
    check("stamp names the fee model", "fee model" in cb.stamp().lower(), cb.stamp())

    print("5. the two entry prices are deliberately different functions")
    fill = {"stake": 100.0, "to_pay": 190.0}
    check("a real fill uses its own stake/payout",
          abs(cb.after_fee_from_fill(fill, cl.am_to_dec) - 1.9) < 1e-9,
          cb.after_fee_from_fill(fill, cl.am_to_dec))
    check("it agrees with clv_ledger.eff_dec",
          cb.after_fee_from_fill(fill, cl.am_to_dec) == cl.eff_dec(fill))
    q = cb.after_fee_from_quote(-110, "novig", cl.am_to_dec)
    check("a quote prices through the fee model", q is not None and 1.0 < q < 2.2, q)
    check("an unpriceable venue returns None, not a guess",
          cb.after_fee_from_quote(-110, "polymarket", cl.am_to_dec) is None,
          cb.after_fee_from_quote(-110, "polymarket", cl.am_to_dec))
    check("no book -> None", cb.after_fee_from_quote(-110, None, cl.am_to_dec) is None)

    print("6. the close refuses anything that is not the bet's own line")
    f = {"lg": "NBA", "start": "2026-11-13T01:00:00Z", "p1": "A A", "p2": "B B"}
    snap = {"league": "NBA", "bet": "Under 9999.5", "game": "A @ B",
            "game_start": "2026-11-13T01:00:00Z"}
    p, why = cb.pinnacle_no_vig_close(f, snap, {}, {}, cl.parsed, cl.which_team, cl.two_way,
                                      cl.novig_p, cl.SPORT, cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
    check("absent line -> None", p is None, p)
    check("and the reason names the line", "9999.5" in str(why) or "did not hang" in str(why), why)
    check("no conversion wording anywhere in the module",
          "moved to" not in open("clv_basis.py").read(), "a conversion path crept in")

    print("7. an uncovered league is refused rather than priced")
    p2, why2 = cb.pinnacle_no_vig_close(f, dict(snap, league="NCAAB", bet="Under 140.5"), {}, {},
                                        cl.parsed, cl.which_team, cl.two_way, cl.novig_p,
                                        cl.SPORT, cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
    check("refused", p2 is None)
    check("reason names the sport map", "sport id" in str(why2), why2)

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all shared-basis checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
