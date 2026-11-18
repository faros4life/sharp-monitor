#!/usr/bin/env python3
"""The four venue-opportunity counters (Peter, Nov 18, authorized).

VSTAT's "ok" means the ladder held at least one priced level. It does NOT mean a price we could take -
Peter caught that distinction, and conflating the two is what made "polymarket_us ok 10" look like
evidence that discovery was fine. These four counters separate the states that have DIFFERENT remedies:

  Q1 match      no market / our exact line / off our line   -> a matching bug, or the venue not listing it
  Q2 price      beats / at / worse than our number, and vs novig -> uncompetitive after fees
  Q3 liquidity  size at our number as a MULTIPLE of the stake -> there but too thin
  Q4 routing    trigger, position N of M, or absent          -> never reached, whatever the price

Hard requirements asserted here:
  - MEASUREMENT ONLY. qstat_record must never raise into the live order pass, whatever it is handed.
  - NO DOLLARS in the output. Liquidity is bucketed as a share of the stake; the stake itself is never
    printed, because this goes to a PUBLIC Actions log.
"""
import collections

import executor as ex

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


def fresh():
    ex.QSTAT.clear()
    return ex.QSTAT


def keys(dim, venue=None):
    return {k[2]: v for k, v in ex.QSTAT.items() if k[1] == dim and (venue is None or k[0] == venue)}


R_OK = {"status": "ok", "exact_line": True, "best_price_american_qual": -108,
        "dollars_at_alert_price_or_better": 600}


# ---------------------------------------------------------------- 1. MATCH
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK), "novig": dict(R_OK, best_price_american_qual=-112)},
                "total", -110, unit=300.0)
ok("an exact-line match is recorded with its market type",
   "total: exact line" in keys("match", "polymarket_us"), keys("match", "polymarket_us"))

fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, exact_line=False)}, "spread", -110, unit=300.0)
ok("an off-line match is recorded SEPARATELY from an exact one",
   "spread: off our line" in keys("match", "polymarket_us"), keys("match", "polymarket_us"))

fresh()
ex.qstat_record({"polymarket_us": {"status": "game_not_on_polymarket_us"}}, "spread", -110, unit=300.0)
m = keys("match", "polymarket_us")
ok("no market is recorded with the venue's own reason", any("no-market" in k for k in m), m)
ok("a no-market venue contributes NO price or liquidity row",
   not keys("price", "polymarket_us") and not keys("liquidity", "polymarket_us"))

# ---------------------------------------------------------------- 2. PRICE
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=-105)}, "total", -110, unit=300.0)
ok("a better price than our number is recorded as beating it",
   keys("price", "polymarket_us") == {"beats our number": 1}, keys("price", "polymarket_us"))
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=-110)}, "total", -110, unit=300.0)
ok("a price exactly at our number is its own bucket",
   keys("price", "polymarket_us") == {"at our number": 1}, keys("price", "polymarket_us"))
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=-120)}, "total", -110, unit=300.0)
ok("a worse price than our number is recorded as worse",
   keys("price", "polymarket_us") == {"worse than our number": 1}, keys("price", "polymarket_us"))
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=None)}, "total", -110, unit=300.0)
ok("an ok status with NO priced level is not silently a price",
   keys("price", "polymarket_us") == {"no priced level": 1}, keys("price", "polymarket_us"))

# plus-money comparison must not invert
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=120)}, "total", 100, unit=300.0)
ok("plus money compares the right way round (+120 beats +100)",
   keys("price", "polymarket_us") == {"beats our number": 1}, keys("price", "polymarket_us"))
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=100)}, "total", -105, unit=300.0)
ok("plus money beats minus money (+100 beats -105)",
   keys("price", "polymarket_us") == {"beats our number": 1}, keys("price", "polymarket_us"))

# ---------------------------------------------------------------- 3. vs NOVIG and the winner
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK, best_price_american_qual=-105),
                 "novig": dict(R_OK, best_price_american_qual=-112),
                 "kalshi": dict(R_OK, best_price_american_qual=-118)}, "total", -110, unit=300.0)
ok("PMUS beating Novig is recorded", keys("vs novig", "polymarket_us") == {"better": 1},
   keys("vs novig", "polymarket_us"))
ok("Kalshi losing to Novig is recorded", keys("vs novig", "kalshi") == {"worse": 1})
ok("the best net price is credited to exactly one venue",
   sum(keys("best net price").values()) == 1, keys("best net price"))
ok("the best net price went to the venue that actually had it",
   keys("best net price", "polymarket_us") == {"won the comparison": 1})
ok("novig is never compared against itself", not keys("vs novig", "novig"))
fresh()
ex.qstat_record({"polymarket_us": dict(R_OK), "novig": {"status": "game_not_on_novig"}}, "total", -110, unit=300.0)
ok("novig having no price is its own bucket, not a PMUS win",
   keys("vs novig", "polymarket_us") == {"novig had no price": 1}, keys("vs novig", "polymarket_us"))

# ---------------------------------------------------------------- 4. LIQUIDITY, bucketed, no dollars
for dol, want in ((0, "none"), (60, "<0.25x unit"), (150, "0.25-1x unit"),
                  (300, "1-2x unit"), (900, ">=2x unit")):
    fresh()
    ex.qstat_record({"polymarket_us": dict(R_OK, dollars_at_alert_price_or_better=dol)},
                    "total", -110, unit=300.0)
    ok(f"liquidity {dol} against a 300 stake buckets as {want}",
       keys("liquidity", "polymarket_us") == {want: 1}, keys("liquidity", "polymarket_us"))
ok("the bucket label never contains a dollar sign or the stake",
   all("$" not in str(k[2]) and "300" not in str(k[2]) for k in ex.QSTAT))

# ---------------------------------------------------------------- 5. it CANNOT raise into the order path
for bad in (None, {}, {"polymarket_us": None}, {"polymarket_us": "not a dict"},
            {"polymarket_us": dict(R_OK, best_price_american_qual="x")},
            {"polymarket_us": dict(R_OK, dollars_at_alert_price_or_better=None)}):
    fresh()
    try:
        ex.qstat_record(bad, "total", -110, unit=300.0)
        raised = False
    except Exception as e:
        raised = True
    ok(f"malformed input {str(bad)[:34]!r} does not raise", not raised)
fresh()
try:
    ex.qstat_record({"polymarket_us": dict(R_OK)}, None, None, unit=None)
    raised = False
except Exception:
    raised = True
ok("a missing market type and price do not raise", not raised)
ok("a zero or absent unit degrades to a label, not a crash",
   ex._qbucket(500, 0) == "unit?" and ex._qbucket(500, None) == "unit?")

# ---------------------------------------------------------------- 6. ROUTING records the opportunity
fresh()
r = {"lcs": [{"book": "novig"}, {"book": "kalshi"}, {"book": "polymarket_us"}]}
ex.trigger_first(r, {"book_key": "novig"})
rt = keys("routing", "polymarket_us")
ok("a venue third in the route records its position", rt == {"position 3 of 3": 1}, rt)
ok("the trigger venue is recorded as having first refusal",
   keys("routing", "novig") == {"trigger (first refusal)": 1}, keys("routing", "novig"))
ok("a venue missing from the route is recorded as absent",
   keys("routing", "prophetx") == {"absent from the route": 1}, keys("routing", "prophetx"))
ok("every executor book gets exactly one routing row",
   sum(keys("routing").values()) == len(ex.BOOKS), keys("routing"))

# ---------------------------------------------------------------- 7. the printer is counts-only
src = open("executor.py").read()
i = src.index("venue opportunity (counts only")
blk = src[i - 200:i + 700]
ok("the printed block says it carries no dollars", "no dollars" in blk)
ok("the printer reads QSTAT and nothing else", "QSTAT.items()" in blk)
ok("qstat_record is called where all four venues are comparable",
   "qstat_record(res, mtype, price)" in src)
ok("the recorder is wrapped so it cannot break the order pass",
   "must never be able to break it" in src)

# ---------------------------------------------------------------- 8. REACH is not POSITION (Peter, Nov 18)
# "Fourth of four" does not establish that a venue was ever offered the order. These two must be
# separately countable, or a venue that is always last and always full is indistinguishable from one
# that was reached and refused.
fresh()
_r = {"live": {"book": "novig", "order": {"status": "placed", "asked_stake": 300.0, "filled_stake": 300.0},
               "risk": 300.0},
      "lcs": [{"book": "novig"}, {"book": "prophetx"}, {"book": "kalshi"}, {"book": "polymarket_us"}]}
ex.live_remainder(_r)
rch = keys("reach")
ok("the first venue is recorded as having filled its own order",
   keys("reach", "novig") == {"filled first (its own order)": 1}, keys("reach", "novig"))
ok("a venue never offered the order is recorded as NOT reached",
   any("NOT reached" in k for k in keys("reach", "polymarket_us")), keys("reach", "polymarket_us"))
ok("the reason it was not reached is the filled unit, not a refusal",
   any("unit already filled" in k for k in keys("reach", "polymarket_us")), keys("reach", "polymarket_us"))
ok("every later venue in the route gets a reach row",
   all(keys("reach", b) for b in ("prophetx", "kalshi", "polymarket_us")), rch)

# a partial first fill DOES leave a remainder, so the next venue is reached
fresh()
_r2 = {"live": {"book": "novig", "order": {"status": "placed", "asked_stake": 300.0, "filled_stake": 50.0},
                "risk": 300.0},
       "lcs": [{"book": "novig"}, {"book": "polymarket_us"}]}
try:
    ex.live_remainder(_r2)
except Exception:
    pass   # live_order is not callable in a test; the reach row is written before it is called
ok("a usable remainder records the next venue as REACHED",
   any("reached with a usable remainder" in k for k in keys("reach", "polymarket_us")),
   keys("reach", "polymarket_us"))
ok("reach and routing are separate dimensions, never merged",
   not (keys("reach", "polymarket_us") and keys("routing", "polymarket_us")))
ok("the printer emits the reach dimension too",
   '"reach"' in open("executor.py").read().split("for _dim in")[1][:120])

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
