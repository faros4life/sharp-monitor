#!/usr/bin/env python3
"""close_detail must reproduce close_for's own probability from the two odds it reports. Synthetic data only."""
import sys
from datetime import datetime, timedelta, timezone

import clv_close_detail as cd
import clv_ledger as cl

START = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc)
OK, BAD = [], []


def check(n, c, d=""):
    (OK if c else BAD).append(n)
    print(f"  [{'PASS' if c else 'FAIL'}] {n} {d}")


def tk(t, p, lim=5000):
    return [{"createdAt": t.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "price": p, "limit": lim}]


FIX = {"p1": "Utah Jazz", "p2": "Dallas Mavericks", "lg": "NBA", "start": START.isoformat()}
t0 = START - timedelta(minutes=7)
t1 = START - timedelta(minutes=12)


def main():
    # totals, own line
    pm = {"900": {"outcomes": {"o": {"players": {"0": tk(t0, 1.80)}}, "u": {"players": {"0": tk(t1, 2.05)}}}}}
    mk = {"900": [11, "totals", 230.5, {"o": "Over", "u": "Under"}]}
    q = {"bet": "Under 230.5"}
    c, _ = cl.close_for(q, FIX, pm, mk, START, "NBA")
    d = cd.close_detail(q, FIX, pm, mk, START, "NBA", c)
    check("totals: detail reproduces close_for", d["detail_check"] == "ok", str(d.get("detail_check")))
    check("totals: Under is the held outcome, with BOTH odds and BOTH ages",
          d["pin_outcome_held"] == "u" and d["pin_dec_held"] == 2.05 and d["pin_dec_other"] == 1.80
          and d["age_held_min"] == 12 and d["age_other_min"] == 7 and d["pin_market_id"] == "900")
    # totals, modelled: must be flagged, never 'ok'
    q2 = {"bet": "Under 228.5"}
    c2, _ = cl.close_for(q2, FIX, pm, mk, START, "NBA")
    d2 = cd.close_detail(q2, FIX, pm, mk, START, "NBA", c2)
    check("modelled close is flagged as modelled", d2["detail_check"].startswith("modelled"), d2["detail_check"])
    # moneyline
    pm3 = {"111": {"outcomes": {"111": {"players": {"0": tk(t0, 1.50)}}, "112": {"players": {"0": tk(t0, 2.70)}}}}}
    mk3 = {"111": [11, "moneyline", 0, {"111": "1", "112": "2"}]}
    q3 = {"bet": "Dallas Mavericks ML"}
    c3, why = cl.close_for(q3, FIX, pm3, mk3, START, "NBA")
    d3 = cd.close_detail(q3, FIX, pm3, mk3, START, "NBA", c3) if c3 else {"detail_check": f"close_for: {why}"}
    check("moneyline: detail reproduces close_for", d3["detail_check"] == "ok", str(d3.get("detail_check")))
    # spread sign: team 2 at +6.5 is team 1 at -6.5
    pm4 = {"950": {"outcomes": {"a": {"players": {"0": tk(t0, 1.91)}}, "b": {"players": {"0": tk(t0, 1.95)}}}}}
    mk4 = {"950": [11, "spreads", -6.5, {"a": "1", "b": "2"}]}
    q4 = {"bet": "Dallas Mavericks +6.5"}
    c4, why4 = cl.close_for(q4, FIX, pm4, mk4, START, "NBA")
    d4 = cd.close_detail(q4, FIX, pm4, mk4, START, "NBA", c4) if c4 else {"detail_check": f"close_for: {why4}"}
    check("spread +6.5 on team 2 resolves to team-1 line -6.5 and reproduces", d4["detail_check"] == "ok"
          and d4.get("pin_line_t1") == -6.5 and d4.get("pin_outcome_held") == "b", str(d4))
    print(f"\n{len(OK)} passed, {len(BAD)} failed")
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
