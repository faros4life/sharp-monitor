#!/usr/bin/env python3
"""
PRIORITY 4 REGRESSION (Peter, Nov 13 2026): lane labels only where the linkage is provable.

The first attempt matched registry keys against selection keys verbatim and resolved ZERO of 280
selections, because the two sides spell the game differently - the registry records the alert's
full name ("Louisiana Ragin Cajuns @ UL Monroe Warhawks") while the ledger row carries the
venue's short form ("Louisiana @ UL Monroe").

The join is tolerant about SPELLING and strict about identity. These cases pin the strictness,
because a wrong lane label would move a bet's performance onto a strategy that never placed it.
"""
import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import clv_coverage as cov  # noqa: E402

BAD = []
WHEN = "2026-11-12T14:47:02Z"
GS = "2026-11-13T02:00:00Z"


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def order(lane, key, when=WHEN):
    return {"key": key, "source": lane, "decided_utc": when}


def main():
    LOU = "r1|NCAAF|Louisiana Ragin Cajuns @ UL Monroe Warhawks|total|UNDER"
    SEL = "NCAAF|louisiana+monroe+ul|total|UNDER|48.5"

    def lane(sel, orders, gs=GS):
        return cov.build_lane_resolver({"orders": orders})(sel, {"game_start": gs})

    print("1. the short and full game names join")
    check("Louisiana resolves to r1", lane(SEL, [order("r1", LOU)]) == "r1",
          lane(SEL, [order("r1", LOU)]))

    print("2. two lanes for the same selection resolve to NOTHING")
    both = [order("r1", LOU), order("board", LOU.replace("r1|", "board|"))]
    check("ambiguous lane refused", lane(SEL, both) is None, lane(SEL, both))

    print("3. identity is still strict")
    check("wrong league refused",
          lane(SEL, [order("r1", LOU.replace("NCAAF", "NBA"))]) is None)
    check("wrong side refused",
          lane(SEL, [order("r1", LOU.replace("|UNDER", "|OVER"))]) is None)
    check("wrong market refused",
          lane(SEL, [order("r1", LOU.replace("|total|", "|side|"))]) is None)
    check("unrelated game refused",
          lane(SEL, [order("r1", "r1|NCAAF|Houston Cougars @ Colorado Buffaloes|total|UNDER")]) is None)
    check("order 8 days from the game refused",
          lane(SEL, [order("r1", LOU, "2026-11-04T14:00:00Z")]) is None)

    print("4. merely overlapping names are not enough - the token sets must nest")
    # shares "louisiana" only; neither set contains the other
    other = "r1|NCAAF|Louisiana Tech Bulldogs @ Rice Owls|total|UNDER"
    check("overlap without nesting refused", lane(SEL, [order("r1", other)]) is None,
          lane(SEL, [order("r1", other)]))

    print("5. no registry evidence means no lane, never a default")
    check("empty registry -> None", lane(SEL, []) is None)
    check("order with no lane -> None",
          lane(SEL, [{"key": LOU.replace("r1|", ""), "source": "", "decided_utc": WHEN}]) is None)

    print("6. spreads join on side tokens, not exact text")
    SP = "r1|NCAAB|Furman Paladins @ Holy Cross Crusaders|side|Furman Paladins"
    SELSP = "NCAAB|cross+crusaders+furman+holy+paladins|spread|furman+paladins|+2.5"
    check("spread selection resolves", lane(SELSP, [order("r1", SP)]) == "r1",
          lane(SELSP, [order("r1", SP)]))
    check("the other side does not", lane(SELSP.replace("furman+paladins|", "crusaders+holy|"),
                                          [order("r1", SP)]) is None)

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all lane-linkage checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
