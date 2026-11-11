"""Persistent strike_id -> identity cache (Nov 11, Peter: "resolve each strike once, not on every
executor run").

px_positions resolved every open strike on EVERY run by walking the whole ProphetX catalogue - one
px_markets call per event across six leagues. Run 43079165131: 45 calls / 177.4s with the venue
answering at 3.94s each. A strike_id names one selection in one market and never changes meaning,
so it is resolved once and remembered.

The line this file defends: the cache is an ENTITY map. It may say what a strike IS. It may never
say what is held, or what anything is worth - trades and prices are always read live. And a strike
that ends up unresolved by an INCOMPLETE walk still blinds the venue, cache or no cache.
"""
import sys
import types

import positions
import registry as rg

CHECKS = []


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


REC = {"book": "prophetx", "game": "A @ B", "date": "2026-11-11", "mtype": "total",
       "label": "under 212.5"}
CALLS = {"markets": 0, "events": 0}


def fake_bc(strikes=("S1",), raise_all=False):
    m = types.ModuleType("book_check")
    m.PX_ACCESS, m.PX_SECRET = "a", "b"
    m.PX_TOURNAMENTS = {"NBA": 132}
    m.px_login = lambda: True
    m.px_call = lambda path: {"data": {"trades": [
        {"strike_id": s, "status": "matched", "winning_status": "open"} for s in strikes]}}

    def px_events(lg):
        CALLS["events"] += 1
        if raise_all:
            raise RuntimeError("429")
        return [{"event_id": 1, "name": "A @ B", "scheduled": "2026-11-11T23:00:00Z"}]

    def px_markets(eid):
        CALLS["markets"] += 1
        return [{"type": "total"}]
    m.px_events, m.px_markets = px_events, px_markets
    m.px_lines = lambda mk: [([{"strike_id": "S1", "name": "under 212.5"}], 212.5)]
    return m


def run(cache=None, written=None, **kw):
    positions.WHY.clear()
    CALLS.update(markets=0, events=0)
    sys.modules["book_check"] = fake_bc(**kw)
    sys.modules.pop("px_live", None)
    fake_rg = types.ModuleType("registry")
    fake_rg.strike_map = lambda: dict(cache or {})
    fake_rg.put_strikes = lambda d: (written is not None and written.update(d)) or True
    sys.modules["registry"] = fake_rg
    return positions.px_positions()


# ---------------------------------------------------------------- a hit skips the catalogue walk
got = run(cache={"S1": REC})
ck("a cached strike resolves", len(got), 1)
ck("to the right game", got[0]["game"], "A @ B")
ck("marked as prophetx", got[0]["book"], "prophetx")
ck("NO market calls were made", CALLS["markets"], 0)
ck("NO event calls were made", CALLS["events"], 0)
assert "from cache" in positions.WHY.get("prophetx_walk_s", ""), positions.WHY
CHECKS.append(("cache hits are reported", True, True))

# ---------------------------------------------------------------- a miss still walks, then writes
written = {}
got = run(cache={}, written=written)
ck("a miss still resolves via the walk", len(got), 1)
ck("and the walk really ran", CALLS["markets"] >= 1, True)
ck("the newly resolved strike is written back", "S1" in written, True)
for f in rg.STRIKE_FIELDS:
    assert written["S1"].get(f) is not None, f"{f} must be stored"
CHECKS.append(("a complete identity record is stored", True, True))

# an already-cached strike is not rewritten
written2 = {}
run(cache={"S1": REC}, written=written2)
ck("a cached strike is not written again", written2, {})

# ---------------------------------------------------------------- the cache never masks blindness
got = run(cache={}, raise_all=True)
ck("unresolved + incomplete walk still blinds, cache or not", got, None)
assert "conflict status cannot be established" in positions.WHY.get("prophetx", ""), positions.WHY
CHECKS.append(("blind reason preserved with the cache in place", True, True))

# a cache that covers everything means the walk never runs, so API failures cannot blind
got = run(cache={"S1": REC}, raise_all=True)
ck("a fully cached read survives a dead ProphetX catalogue", len(got), 1)
ck("because no catalogue call was needed", CALLS["events"], 0)

# ---------------------------------------------------------------- malformed and stale entries
for bad in ({"S1": {"book": "prophetx"}},                       # missing fields
            {"S1": "not a dict"},                               # wrong type
            {"S1": {f: None for f in rg.STRIKE_FIELDS}}):       # present but empty
    written3 = {}
    got = run(cache=bad, written=written3)
    ck("a malformed entry is ignored and re-walked", CALLS["markets"] >= 1, True)
    ck("and resolves correctly anyway", len(got), 1)

# strike_map itself filters malformed records
rg._call = lambda *a, **k: (500, {})
ck("an unreadable cache is {} , so the walk simply runs", rg.strike_map(), {})

# ---------------------------------------------------------------- entity data only
src = open(positions.__file__).read()
i = src.index("PERSISTENT STRIKE IDENTITY CACHE")
blk = src[i:i + 1600]
# CODE only - comments are stripped first. Scanning raw text flagged the block's own comment
# saying "prices are never taken from here", the same false positive that made `stamp.replace(`
# look like an order `place(` call earlier today.
code = "\n".join(ln.split("#", 1)[0] for ln in blk.splitlines()).lower()
for forbidden in ("price", "stake", "exposure", "filled", "balance"):
    assert forbidden not in code, \
        f"the strike cache block must not touch financial data - found {forbidden!r}"
CHECKS.append(("the cache carries identity only, never money", True, True))
# the trades list is still read live, before any cache use
ck("trades are read before the cache is consulted",
   src.index("get_trades") < i, True)

print(f"PASS  test_strike_cache.py  {len(CHECKS)} checks")
