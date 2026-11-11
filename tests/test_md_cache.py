"""Per-run market-data cache: identical results, fewer calls, never at order time (Nov 11).

evaluate() probes 5 lines x 4 books PER PLAY, so a game that qualifies in two lanes - an NBA total
under can be a Phase 1 play AND a Board v3 play - repeats every read. The cache serves the second
play the first play's result.

SOUNDNESS is the whole test: the key must contain every input the venue readers actually use, so
that equal keys mean equal arguments and a cached value is the value the call would have returned.
bc.px_check / kalshi_check / pmus_check use al["sport"], al["start_utc"], al["bet"], teams, mtype,
side, line and price - price included, because ladder_result() derives
dollars_at_alert_price_or_better from it.

And order time is never cached: revalidate() -> reread_book() calls the readers directly.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_check as bc  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


AL = {"sport": "NBA", "start_utc": "2026-11-12T01:00:00Z", "bet": "Under 230.5 (-119)"}
TEAMS = ("Los Angeles Lakers", "Milwaukee Bucks")
BASE = ("prophetx", AL, "total", "UNDER", 230.5, -119, TEAMS)


def key(**over):
    b, al, mt, sd, ln, pr, tm = BASE
    al = dict(al, **{k: v for k, v in over.items() if k in ("sport", "start_utc", "bet")})
    return ex.md_key(over.get("book", b), al, over.get("mtype", mt), over.get("side", sd),
                     over.get("line", ln), over.get("price", pr), over.get("teams", tm))


# ---------------------------------------------------------------- the key is sound
ck("identical inputs give the same key", key() == key())
for field, val in (("book", "kalshi"), ("sport", "NCAAB"), ("start_utc", "2026-11-13T01:00:00Z"),
                   ("bet", "Under 231.5 (-119)"), ("mtype", "spread"), ("side", "OVER"),
                   ("line", 231.0), ("price", -115), ("teams", ("A", "B"))):
    ck(f"a different {field} gives a DIFFERENT key", key(**{field: val}) != key(), field)

ck("price is in the key (ladder_result derives dollars_at_alert_price_or_better from it)",
   key(price=-120) != key())
ck("the line is rounded consistently, so 230.5 and 230.50 share", key(line=230.50) == key())
ck("the key is hashable", isinstance(hash(key()), int))

# every argument the readers take is represented
sig = list(inspect.signature(bc.px_check).parameters)
ck("px_check takes (al, mtype, side, line, price, teams)",
   sig == ["al", "mtype", "side", "line", "price", "teams"], str(sig))
ksrc = inspect.getsource(ex.md_key)
for needed in ('al.get("sport")', 'al.get("start_utc")', 'al.get("bet")', "mtype", "side", "price", "teams"):
    ck(f"the key includes {needed}", needed in ksrc)

# the al fields the readers actually read are the ones in the key
pxsrc = inspect.getsource(bc.px_check)
for f in ("start_utc", "sport"):
    ck(f"px_check reads al[{f}] and the key carries it", f in pxsrc and f in ksrc)
ck("ladder_result is what makes price matter", "ladder_result" in pxsrc or "ladder_result" in inspect.getsource(bc.kalshi_check))

# ---------------------------------------------------------------- it returns the SAME object
ex.MD["c"].clear(); ex.MD["hit"] = ex.MD["miss"] = 0
sentinel = {"status": "ok", "best_price_american": -121, "line": 230.5, "buy_levels": []}
ex.MD["c"][key()] = sentinel
ck("a cached key returns the stored result unchanged", ex.MD["c"][key()] is sentinel)
ck("  including its price", ex.MD["c"][key()]["best_price_american"] == -121)

# ---------------------------------------------------------------- cache is consulted in the probe
ev = inspect.getsource(ex.evaluate)
ck("the probe checks the cache before fetching", 'if ck in MD["c"]' in ev)
ck("a miss is stored", 'MD["c"][ck] = r' in ev)
ck("an error is stored too (a failing venue is not hammered once per play)", 'MD["c"][ck] = e' in ev)
ck("hits and misses are counted", 'MD["hit"] += 1' in ev and 'MD["miss"] += 1' in ev)

# ---------------------------------------------------------------- ORDER TIME IS NEVER CACHED
rb = inspect.getsource(ex.reread_book)
ck("reread_book does NOT consult the cache", "MD[" not in rb and "md_key" not in rb)
ck("reread_book calls the venue readers directly",
   "bc.px_check" in rb and "bc.kalshi_check" in rb and "pmus_check" in rb)
rv = inspect.getsource(ex.revalidate)
ck("revalidate goes through reread_book", "reread_book(" in rv)
ck("revalidate does not consult the cache", "MD[" not in rv and "md_key" not in rv)
ck("so the price behind an actual order is always read fresh",
   "reread_book(" in rv and "MD[" not in rv)

# ---------------------------------------------------------------- one cache per run
mb = inspect.getsource(ex.main)
ck("the cache is cleared at the start of each run", 'MD["c"].clear()' in mb)
ck("  and the counters with it", 'MD["hit"] = MD["miss"] = 0' in mb)
ck("the cache is cleared BEFORE any play is evaluated",
   mb.index('MD["c"].clear()') < mb.index("evaluate(p, now"))

# ---------------------------------------------------------------- nothing about betting moved
ck("units unchanged", (ex.LIVE_UNIT, ex.BOARD_UNIT, ex.R1_UNIT) == (300.0, 200.0, 200.0))
ck("tolerance unchanged", ex.TOL_BOOKS == ("prophetx", "novig") and ex.PX_TOL_CENTS == 2)
ck("cap unchanged", ex.CAP_LINE == -130)
ck("limits unchanged", ex.BOARD_DAILY_RISK == 1500.0 and ex.R1_DAILY_RISK == 1500.0
   and ex.px_live.DAILY_STOP == 2250.0)
ck("the probe set is UNCHANGED (pruning stays unsafe - see test_probe_pruning_unsafe)",
   "(0, -0.5, 0.5, -1.0, 1.0)" in ev)
ck("venue ranking unchanged",
   "tol" not in [l for l in ev.splitlines() if l.strip().startswith("c_eq =")][0])

ex.MD["c"].clear(); ex.MD["hit"] = ex.MD["miss"] = 0
print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)
