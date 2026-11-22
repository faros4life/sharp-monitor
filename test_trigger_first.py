#!/usr/bin/env python3
"""Nov 17 (Peter): the triggering venue gets the order first, balance to Novig, then the rest; no price change."""
import sys

import executor as ex

BAD = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    BAD.append(n) if not c else None


def C(b, am=-105):
    return {"book": b, "am": am, "shown": am, "line": 220.5, "avail": 500, "thr": 0.5, "buy": 0.5, "ids": {}}


best = [C("novig", -102), C("prophetx", -104), C("kalshi", -106)]          # existing best-price order
r = {"lcs": list(best), "lc": best[0]}
ex.trigger_first(r, {"book_key": "kalshi"})
check("Kalshi trigger: Kalshi first, then Novig, then the rest", [c["book"] for c in r["lcs"]] == ["kalshi", "novig", "prophetx"])
check("the first live venue is the trigger venue", r["lc"]["book"] == "kalshi")
r = {"lcs": [C("novig"), C("prophetx")], "lc": None}
ex.trigger_first(r, {"book_key": "kalshi"})
check("trigger venue off the alert price -> Novig first", r["lc"]["book"] == "novig" and "Novig first" in r["route"]["rule"])
r = {"lcs": [C("prophetx"), C("novig"), C("kalshi")], "lc": None}
ex.trigger_first(r, {"book_key": "prophetx"})
check("ProphetX trigger: ProphetX, Novig, then Kalshi", [c["book"] for c in r["lcs"]] == ["prophetx", "novig", "kalshi"])
r = {"lcs": [C("novig"), C("kalshi")], "lc": None}
ex.trigger_first(r, {"book_key": "novig.us"})
check("Novig trigger stays first, no duplicate", [c["book"] for c in r["lcs"]] == ["novig", "kalshi"])
r = {"lcs": list(best), "lc": best[0]}
ex.trigger_first(r, {"book_key": "pinnacle"})
check("a non-exchange trigger keeps the best-price order", [c["book"] for c in r["lcs"]] == ["novig", "prophetx", "kalshi"] and r["lc"]["book"] == "novig")
r = {"lcs": list(best), "lc": best[0]}
ex.trigger_first(r, {"book_key": "polymarket"})
check("Polymarket GLOBAL is never a trigger venue (not US-tradeable)", r["lcs"][0]["book"] == "novig")
r = {"lcs": [C("kalshi", -106)], "lc": None}
ex.trigger_first(r, {"book_key": "kalshi"})
check("no price is changed - only the order", r["lcs"][0]["am"] == -106)
r = {"lcs": [], "lc": None}
ex.trigger_first(r, {"book_key": "kalshi"})
check("no live venue -> nothing chosen", r["lc"] is None)
src = open("executor.py").read()
# Nov 22: four lanes now - board, r1, ncs and the phase-1 branch. Every lane that can place must
# call trigger_first, or its order skips the trigger-venue ordering entirely.
check("applied in all four live lanes", src.count("                trigger_first(r, ent)\n") == 4)
print("ALL PASS" if not BAD else f"{len(BAD)} FAILED")
sys.exit(1 if BAD else 0)
