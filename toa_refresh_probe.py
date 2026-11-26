#!/usr/bin/env python3
"""Measure The Odds API's real pre-game refresh rate before any polling change (Peter, Nov 26: "Verify actual
provider refresh rates before expanding polling frequency"). Polls ONE sport's Pinnacle + exchange spreads every
POLL_S seconds for MINUTES minutes (1 credit per call) and reports, per bookmaker, how often a poll saw a real PRICE
OR LINE change. Nov 26 correction: the first version counted last_update timestamps, which advance every ~15 s
whether or not a price moved - it measured the provider's heartbeat, not the market. Counts and seconds only."""
import collections
import json
import os
import time
import urllib.parse
import urllib.request

KEY = os.environ["ODDS_API_KEY"]
SPORT = os.environ.get("PROBE_SPORT") or "basketball_ncaab"
BOOKS = os.environ.get("PROBE_BOOKS") or "pinnacle,novig,prophetx,kalshi,polymarket_us,hardrockbet_fl"
POLL_S = int(os.environ.get("POLL_S") or "15")
MINUTES = int(os.environ.get("MINUTES") or "10")
seen = {}
new = collections.Counter()
polls = 0
credits = 0
gaps = collections.defaultdict(list)
end = time.time() + MINUTES * 60
while time.time() < end:
    q = urllib.parse.urlencode({"apiKey": KEY, "bookmakers": BOOKS, "markets": "spreads", "oddsFormat": "american"})
    with urllib.request.urlopen(f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds?{q}", timeout=30) as r:
        data = json.loads(r.read().decode())
        credits += int(float(r.headers.get("x-requests-last") or 0))
    polls += 1
    for ev in data:
        for bk in ev.get("bookmakers") or []:
            for m in bk.get("markets") or []:
                k = (ev["id"], bk["key"])
                lu = tuple(sorted((o.get("name"), o.get("price"), o.get("point")) for o in m.get("outcomes") or []))
                if k in seen and seen[k][0] != lu:
                    new[bk["key"]] += 1
                    gaps[bk["key"]].append(time.time() - seen[k][1])
                if k not in seen or seen[k][0] != lu:
                    seen[k] = (lu, time.time())
    time.sleep(POLL_S)
print(f"sport {SPORT} | polls {polls} every {POLL_S}s over {MINUTES} min | credits {credits}")
for bk in sorted({k[1] for k in seen}):
    n_mk = sum(1 for k in seen if k[1] == bk)
    g = sorted(gaps[bk])
    med = g[len(g) // 2] if g else None
    print(f"  {bk:<16} markets {n_mk:>4} | price changes {new[bk]:>4} | changes per market per minute "
          f"{new[bk] / max(n_mk, 1) / MINUTES:.3f} | median seconds between changes {med and round(med)}")
