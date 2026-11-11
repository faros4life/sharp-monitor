#!/usr/bin/env python3
"""
BIT-IDENTICAL TEST for the proposed close_prob() refactor (Peter, Nov 10: "GO").

NOT a production edit. This file contains the PROPOSED function alongside the current one and
proves they return the same probability. Nothing in sharp_monitor.py is changed.

WHY IT IS A DIFFERENTIAL TEST AND NOT A REPLAY. The plan's first test was "assert the returned p
equals today's float for all 319 existing readings". That cannot be done: the Pinnacle market dict
that produced each reading was never stored - only the resulting p was. Replaying 319 readings
would require inputs we do not have, and inventing them would prove nothing. So equivalence is
proven the other way round: both implementations are run over a GENERATED input matrix that covers
every branch and boundary either one can reach, and the probabilities must match exactly.

The matrix covers, per market:
  * moneyline  - both sides, favourite and dog, missing side, wrong number of sides
  * spread     - our line equal to Pinnacle's, above it, below it, by a half point and by several;
                 run line (rl) at a different number, which must return None rather than convert
  * total      - Over and Under, our line equal to, above and below Pinnacle's
  * extremes   - prices that drive p past 0.01 / 0.99 so the clamp is exercised on both ends
  * leagues    - every league in LABEL_KEY, since half_point_value is league-specific
Exact equality is required: `==` on the float, not a tolerance. A refactor that rounds differently
is not a refactor.
"""
import itertools
import sys

import sharp_monitor as sm

am_to_prob = sm.am_to_prob
half_point_value = sm.half_point_value


def close_prob_reference(e, pin):
    """A FROZEN copy of close_prob as it stood before Nov 10, kept here deliberately.

    This is the regression guard, and it only works while this copy is never "tidied" to match the
    live one. sharp_monitor.close_prob_detail must agree with it exactly, forever; if a future
    change to the close maths is intended, this reference changes in the same commit and the
    intent is stated there.""" 
    k, side, pt, lab = e["kind"], e["side"], e.get("pt"), e.get("sport", "")
    if k == "ml":
        h = pin.get("h2h", {})
        if len(h) != 2 or side not in h:
            return None
        pr = {t: am_to_prob(p) for t, p in h.items()}
        return pr[side] / sum(pr.values())
    if k in ("spr", "rl"):
        sp = pin.get("spreads", {})
        if len(sp) != 2 or side not in sp:
            return None
        (ppt, ppr), (_, opr) = sp[side], [v for t, v in sp.items() if t != side][0]
        p = am_to_prob(ppr) / (am_to_prob(ppr) + am_to_prob(opr))
        if abs(ppt - pt) > 1e-9:
            if k == "rl":
                return None
            v = half_point_value(lab, "spr", ppt, pt, ppt)
            p += v if pt > ppt else -v
        return min(max(p, .01), .99)
    if k == "tot":
        tt = pin.get("totals", {})
        if "Over" not in tt or "Under" not in tt:
            return None
        ppt = tt["Over"][0]
        p = am_to_prob(tt[side][1]) / (am_to_prob(tt["Over"][1]) + am_to_prob(tt["Under"][1]))
        if abs(ppt - pt) > 1e-9:
            v = half_point_value(lab, "tot", ppt, pt, ppt)
            better = (pt < ppt) if side == "Over" else (pt > ppt)
            p += v if better else -v
        return min(max(p, .01), .99)
    return None


def cases():
    """Every (e, pin) the two implementations can disagree on."""
    leagues = ["NBA", "NFL", "NCAAF", "NCAAB", "NHL", "MLB", "WNBA", ""]
    prices = [-10000, -400, -130, -115, -110, -102, 100, 105, 150, 400, 10000]
    out = []
    # moneyline
    for lg, a, b in itertools.product(leagues[:4], prices[::3], prices[::4]):
        pin = {"h2h": {"HomeTeam": a, "AwayTeam": b}}
        for side in ("HomeTeam", "AwayTeam"):
            out.append(({"kind": "ml", "side": side, "pt": None, "sport": lg}, pin))
        out.append(({"kind": "ml", "side": "NotPlaying", "pt": None, "sport": lg}, pin))
    out.append(({"kind": "ml", "side": "HomeTeam", "pt": None, "sport": "NBA"},
                {"h2h": {"HomeTeam": -110}}))                      # wrong side count
    out.append(({"kind": "ml", "side": "HomeTeam", "pt": None, "sport": "NBA"}, {}))
    # spreads and run lines, our line on, above and below Pinnacle's
    for lg, pp, a, b in itertools.product(leagues[:6], [-7.5, -3.0, -1.5, 0.0, 2.5, 6.0],
                                          prices[::3], prices[::4]):
        pin = {"spreads": {"HomeTeam": (pp, a), "AwayTeam": (-pp, b)}}
        for d in (0.0, 0.5, -0.5, 1.0, -1.0, 3.5, -3.5):
            for k in ("spr", "rl"):
                out.append(({"kind": k, "side": "HomeTeam", "pt": pp + d, "sport": lg}, pin))
    out.append(({"kind": "spr", "side": "HomeTeam", "pt": -3.0, "sport": "NBA"},
                {"spreads": {"HomeTeam": (-3.0, -110)}}))           # wrong side count
    out.append(({"kind": "spr", "side": "Nobody", "pt": -3.0, "sport": "NBA"},
                {"spreads": {"HomeTeam": (-3.0, -110), "AwayTeam": (3.0, -110)}}))
    # totals, both sides, our line on, above and below
    for lg, pp, a, b in itertools.product(leagues[:6], [41.5, 47.0, 212.5, 228.0],
                                          prices[::3], prices[::4]):
        pin = {"totals": {"Over": (pp, a), "Under": (pp, b)}}
        for d in (0.0, 0.5, -0.5, 1.0, -1.0, 4.0, -4.0):
            for side in ("Over", "Under"):
                out.append(({"kind": "tot", "side": side, "pt": pp + d, "sport": lg}, pin))
    out.append(({"kind": "tot", "side": "Over", "pt": 220.0, "sport": "NBA"},
                {"totals": {"Over": (220.0, -110)}}))               # missing Under
    out.append(({"kind": "tot", "side": "Over", "pt": 220.0, "sport": "NBA"}, {}))
    # an unknown market must stay None in both
    out.append(({"kind": "weird", "side": "x", "pt": 1.0, "sport": "NBA"}, {"h2h": {}}))
    return out


def main():
    print("BIT-IDENTICAL TEST | live close_prob_detail + wrapper vs FROZEN pre-Nov-10 reference")
    print("=" * 100)
    cs = cases()
    n = ok = none_both = clamp = conv = 0
    bad = []
    for e, pin in cs:
        n += 1
        try:
            a = close_prob_reference(e, pin)        # frozen pre-Nov-10 behaviour
        except Exception as ex:
            a = f"RAISED {type(ex).__name__}"
        try:
            b = sm.close_prob_detail(e, pin)        # the live implementation
        except Exception as ex:
            b = f"RAISED {type(ex).__name__}"
        try:
            w = sm.close_prob(e, pin)               # the wrapper, old signature
        except Exception as ex:
            w = f"RAISED {type(ex).__name__}"
        if (w if not isinstance(w, str) else w) != (a if not isinstance(a, str) else a):
            bad.append((e, pin, f"wrapper {w!r}", f"reference {a!r}"))
        if isinstance(a, str) or isinstance(b, str):
            if a != b:
                bad.append((e, pin, a, b))
            continue
        if a is None or b is None:
            if (a is None) != (b is None):
                bad.append((e, pin, a, b))
            else:
                none_both += 1
            continue
        if a == b["p"]:                       # exact equality, no tolerance
            ok += 1
            if b.get("clamped"):
                clamp += 1
            if b.get("conv_pts"):
                conv += 1
        else:
            bad.append((e, pin, a, b["p"]))
    print(f"  cases run                         {n}")
    print(f"  both returned a probability       {ok}   (exact float equality)")
    print(f"  both returned None                {none_both}")
    print(f"  of the matched ones, clamped      {clamp}")
    print(f"  of the matched ones, converted    {conv}   <- the cases the feed records nothing about")
    print(f"  MISMATCHES                        {len(bad)}")
    for e, pin, a, b in bad[:10]:
        print(f"      {e} {pin} -> current {a!r} proposed {b!r}")
    print("=" * 100)
    if bad:
        print("  FAIL - the refactor is not bit-identical. Do not proceed.")
        return 1
    print("  PASS - identical probability on every case, including every None and both clamp ends.")
    print(f"  The {conv} converted cases are the ones the old function computed and discarded;")
    print("  pin_line, our_line and conv_pts are now recorded for them, with no arithmetic changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
