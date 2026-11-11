"""Nov 11: one failed ProphetX call among 45 must not erase knowledge of 100 open trades.

Run 43079165131: ProphetX answered at 3.94s per call (0.14s in the other pass of the same job) and
1 of 45 calls came back unusable. That single failure propagated out of px_positions as None, made
the venue "blind", and blocked every live order for the run on ALL FOUR venues.

Wrong blast radius. get_trades SUCCEEDED - all 100 open trades were known, so exposure WAS known.
The walk only resolves each trade's strike_id to a game/market for the conflict check, and an
unresolved strike is already tolerated and reported as prophetx_partial.

So: a walk failure degrades to PARTIAL. A trades-read failure still returns None and still blinds
the venue, because that is the case where exposure genuinely cannot be verified.
"""
import sys
import types

import positions

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


TRADE = {"strike_id": "S1", "status": "matched", "winning_status": "open"}


def fake_bc(trades=None, trades_raises=False, walk_raises=False):
    m = types.ModuleType("book_check")
    m.PX_ACCESS, m.PX_SECRET = "a", "b"
    m.PX_TOURNAMENTS = {"NBA": 132}
    m.px_login = lambda: True

    def px_call(path):
        if "get_trades" in path:
            if trades_raises:
                raise RuntimeError("get_trades HTTP 500")
            return {"data": {"trades": trades if trades is not None else [TRADE]}}
        return {}
    m.px_call = px_call

    def px_events(lg):
        if walk_raises:
            raise RuntimeError("HTTP Error 429: rate limited")
        return [{"event_id": 1, "name": "A @ B", "scheduled": "2026-11-11T23:00:00Z"}]
    m.px_events = px_events
    m.px_markets = lambda eid: [{"type": "total"}]
    m.px_lines = lambda mk: [([{"strike_id": "S1", "name": "under 212.5"}], 212.5)]
    return m


def run(**kw):
    positions.WHY.clear()
    sys.modules["book_check"] = fake_bc(**kw)
    sys.modules.pop("px_live", None)
    return positions.px_positions()


# ---------------------------------------------------------------- a walk failure is PARTIAL
got = run(walk_raises=True)
ck("a walk failure does NOT blind the venue", got is None, False)
ck("it returns a list (possibly empty) instead", isinstance(got, list), True)
assert "prophetx_walk" in positions.WHY, f"the incomplete lookup must be recorded: {positions.WHY}"
CHECKS.append(("the incomplete strike lookup is recorded", True, True))
assert "prophetx" not in positions.WHY, \
    "a walk failure must not set the blind reason - that is reserved for an unknown trades list"
CHECKS.append(("a walk failure does not set the blind reason", True, True))

# ---------------------------------------------------------------- a trades failure is BLIND
ck("a trades-read failure still returns None (blind)", run(trades_raises=True), None)
assert "prophetx" in positions.WHY, "the blind reason must be recorded"
CHECKS.append(("exposure unknown -> blind, never zero", True, True))

# ---------------------------------------------------------------- normal path still resolves
got = run()
ck("a healthy read returns the resolved position", len(got), 1)
ck("resolved to the right book", got[0]["book"], "prophetx")
ck("resolved to the right strike", got[0]["strike_id"], "S1")

# no trades at all is an empty list, not None: we read successfully and you hold nothing there
ck("zero open trades is an empty list, not blind", run(trades=[]), [])

# ---------------------------------------------------------------- no key / login failure stay blind
positions.WHY.clear()
m = fake_bc()
m.PX_ACCESS = None
sys.modules["book_check"] = m
ck("no key -> blind", positions.px_positions(), None)

positions.WHY.clear()
m = fake_bc()
m.px_login = lambda: False
sys.modules["book_check"] = m
ck("login failure -> blind", positions.px_positions(), None)

print(f"PASS  test_px_positions_blind.py  {len(CHECKS)} checks")
