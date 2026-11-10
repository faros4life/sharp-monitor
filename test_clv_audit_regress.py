#!/usr/bin/env python3
"""Regression tests for the Nov 10 CLV forensic audit. No secrets, no network, no cache.
Each test pins one defect class so a future edit cannot reintroduce it silently."""
import sys
from datetime import datetime, timedelta, timezone

import clv_audit_fixes as fx
import clv_ledger as cl
import clv_std as cs

OK, BAD = [], []
START = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc)


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def ticks(*pairs):
    return [{"createdAt": iso(t), "price": p, "limit": 5000} for t, p in pairs]


def total_market(mid, line, over_ticks, under_ticks):
    pm = {str(mid): {"outcomes": {"o": {"players": {"0": over_ticks}}, "u": {"players": {"0": under_ticks}}}}}
    mk = {str(mid): [11, "totals", line, {"o": "Over", "u": "Under"}]}
    return pm, mk


FIX = {"p1": "Utah Jazz", "p2": "Dallas Mavericks", "lg": "NBA", "start": iso(START)}


def main():
    # B. double-applied fee ---------------------------------------------------------------------
    paf = -116                                        # ProphetX -110 shown, already after the 2% fee
    once = fx.entry_net_dec("prophetx", paf, fx.STORED_NET)
    twice = fx.entry_net_dec("prophetx", paf, fx.STORED_RAW)
    check("price_after_fee is not charged a second time", once > twice and abs(once - cl.am_to_dec(paf)) < 1e-12,
          f"once {once:.4f} vs twice {twice:.4f}")
    check("Kalshi after-fee price: second fee is larger than ProphetX's",
          fx.entry_net_dec("kalshi", -116, fx.STORED_NET) - fx.entry_net_dec("kalshi", -116, fx.STORED_RAW) >
          once - twice)
    check("Novig / Hard Rock unaffected by basis (no fee)",
          abs(fx.entry_net_dec("novig", -110, fx.STORED_NET) - fx.entry_net_dec("novig", -110, fx.STORED_RAW)) < 1e-9 and
          abs(fx.entry_net_dec("hardrockbet", -110, fx.STORED_NET) - fx.entry_net_dec("hardrockbet", -110, fx.STORED_RAW)) < 1e-9)
    try:
        fx.entry_net_dec("betfair", -110, fx.STORED_NET)
        check("unknown venue refused", False)
    except cs.UnknownVenue:
        check("unknown venue refused", True)

    # A. wrong closing-book field ---------------------------------------------------------------
    check("exchange self-close is reported in cents, not as CLV", fx.self_close_move_cents(0.53, 0.53) == 0.0)
    # the scorecard's mistake: close_price x net decimal measures the FEE, not value
    fee_only = fx.pin_clv(0.53, cs.net_dec("kalshi", 1 / 0.53))
    check("close==entry on Kalshi 'CLV' is pure fee drag (proves the mislabel)", fee_only < -1.0, f"{fee_only}%")

    # opposite-side selection -------------------------------------------------------------------
    t0 = START - timedelta(minutes=5)
    pm, mk = total_market(900, 230.5, ticks((t0, 1.80)), ticks((t0, 2.05)))
    under, _ = cl.close_for({"bet": "Under 230.5"}, FIX, pm, mk, START, "NBA")
    over, _ = cl.close_for({"bet": "Over 230.5"}, FIX, pm, mk, START, "NBA")
    check("Over and Under closes are complements", under and over and abs(under["p"] + over["p"] - 1) < 1e-9)
    check("Under uses the Under side (Under priced longer => lower prob)", under["p"] < 0.5 < over["p"])

    # modelled vs verified ----------------------------------------------------------------------
    c, why = cl.close_for({"bet": "Under 228.5"}, FIX, pm, mk, START, "NBA")
    check("different total => modelled close", c is not None and c["how"].startswith("main "), str(c))
    check("modelled close is NOT verified", c is not None and not cs.close_verified(c["how"]))
    check("pin_close_usable rejects the modelled close", not fx.pin_close_usable(c))
    check("pin_close_usable accepts the own-line close", fx.pin_close_usable(under))

    # stale quotes ------------------------------------------------------------------------------
    old = START - timedelta(minutes=cl.FRESH_MIN + 30)
    pm2, mk2 = total_market(901, 230.5, ticks((old, 1.9)), ticks((old, 1.9)))
    c2, why2 = cl.close_for({"bet": "Under 230.5"}, FIX, pm2, mk2, START, "NBA")
    check("close older than FRESH_MIN is dropped", c2 is None, str(why2))
    mid_age = START - timedelta(minutes=854)
    pm3, mk3 = total_market(902, 230.5, ticks((mid_age, 1.9)), ticks((mid_age, 1.9)))
    c3, _ = cl.close_for({"bet": "Under 230.5"}, FIX, pm3, mk3, START, "NBA")
    check("registered 24h rule ACCEPTS a 854-min-old 'close' (audit finding, documented not changed)",
          c3 is not None and c3["age_min"] == 854)
    check("a tighter reporting cap rejects it", not fx.pin_close_usable(c3, max_age_min=60))

    # future-price look-ahead -------------------------------------------------------------------
    after = START + timedelta(minutes=3)
    pm4, mk4 = total_market(903, 230.5, ticks((t0, 1.80), (after, 1.20)), ticks((t0, 2.05), (after, 4.00)))
    c4, _ = cl.close_for({"bet": "Under 230.5"}, FIX, pm4, mk4, START, "NBA")
    check("tick after event start is ignored", c4 is not None and abs(c4["p"] - under["p"]) < 1e-9)
    tw = cl.two_way(pm4, 903, t0 - timedelta(seconds=1))
    check("two_way at an earlier time sees nothing from the future", tw == {})

    # cross-event mismatch ----------------------------------------------------------------------
    F = {"a": {"lg": "NBA", "start": iso(START), "p1": "Houston Rockets", "p2": "Oklahoma City Thunder"},
         "b": {"lg": "NBA", "start": iso(START), "p1": "Los Angeles Lakers", "p2": "Los Angeles Clippers"}}
    st = {"fixtures": F}
    bet = {"league": "NBA", "game": "Lakers vs Rockets", "game_start": iso(START)}
    check("two teams from different games match no fixture", cl.find_fixture(st, bet) is None)

    print(f"\n{len(OK)} passed, {len(BAD)} failed")
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
