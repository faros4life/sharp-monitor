#!/usr/bin/env python3
"""PEAK-HOUR SAMPLING STUDY (Peter, Nov 26: "Test actual price changes during peak hours and within 60 minutes of game
time. Compare 30-second, 60-second and 5-minute sampling. Measure how many actionable price changes our current
five-minute polling misses.")

Ground truth: every POLL_S (15 s) for MINUTES, the same books and markets the alert feed reads. Each poll is stamped
with receipt time. Coarser sampling is SIMULATED from that series (every 2nd, 4th, 20th poll), so all four rates see
the identical market. A "change" = any price or line difference between consecutive observations of one outcome.

ACTIONABLE (what our alerts act on): a Pinnacle LINE move (the point changes). For each one seen at 15 s:
  caught by a sampler   = the sampler sees the new number at some later sample
  missed                = the move reversed before the sampler's next look (it never sees it)
  detection delay       = time from the 15 s first-sight to the sampler's first-sight
Results split by minutes to start (<=60 / >60). Exchange price changes are counted the same way (execution research).
Cost ~1 credit per market per region-equivalent per poll. Log: counts and seconds only, no prices.
"""
import collections
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

KEY = os.environ["ODDS_API_KEY"]
SPORTS = (os.environ.get("PROBE_SPORTS") or "basketball_nba,basketball_ncaab,americanfootball_nfl").split(",")
BOOKS = "pinnacle,novig,prophetx,kalshi,polymarket_us,hardrockbet_fl"
POLL_S = int(os.environ.get("POLL_S") or "15")
MINUTES = int(os.environ.get("MINUTES") or "60")
MAX_CREDITS = int(os.environ.get("PROBE_MAX_CREDITS") or "3000")   # hard stop for this run (Peter, Nov 26: 6,000 for both)
OUT = os.environ.get("PROBE_OUT") or ""                            # gz file of the full 15 s series for toa_peak_analyze
RATES = {"15s": 1, "30s": 30 // POLL_S, "60s": 60 // POLL_S, "5min": 300 // POLL_S}

series = collections.defaultdict(list)   # (sport, ev, book, market, outcome) -> [(poll_i, t, (point, price))]
start_of = {}
names = {}
poll_t = []
credits = 0
i = 0
end = time.time() + MINUTES * 60
while time.time() < end and credits < MAX_CREDITS:
    poll_t.append(time.time())
    for sp in SPORTS:
        q = urllib.parse.urlencode({"apiKey": KEY, "bookmakers": BOOKS, "markets": "spreads,totals,h2h",
                                    "oddsFormat": "american"})
        try:
            with urllib.request.urlopen(f"https://api.the-odds-api.com/v4/sports/{sp}/odds?{q}", timeout=30) as r:
                data = json.loads(r.read().decode())
                credits += int(float(r.headers.get("x-requests-last") or 0))
        except Exception:
            continue
        now = time.time()
        for ev in data:
            st = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).timestamp()
            if st <= now:
                continue   # pre-game only
            start_of[ev["id"]] = st
            names[ev["id"]] = (sp, ev.get("home_team"), ev.get("away_team"))
            for bk in ev.get("bookmakers") or []:
                for m in bk.get("markets") or []:
                    for o in m.get("outcomes") or []:
                        series[(sp, ev["id"], bk["key"], m["key"], o["name"])].append(
                            (i, now, (o.get("point"), o.get("price"))))
    i += 1
    time.sleep(max(0, POLL_S - 1))


def changes(obs):
    """[(t_first_seen, previous, value)] each time the value differs from the previous observation."""
    out, prev = [], None
    for _i, t, v in obs:
        if v != prev:
            if prev is not None:
                out.append((t, prev, v))
            prev = v
    return out


tot = collections.Counter()
caught = collections.Counter()
delays = collections.defaultdict(list)
exch = collections.Counter()
for k, obs in series.items():
    sp, eid, book, mk, oc = k
    truth = changes(obs)
    if not truth:
        continue
    bucket = "<=60 min" if (start_of.get(eid, 0) - truth[0][0]) <= 3600 else ">60 min"
    is_pin_line = book == "pinnacle" and mk in ("spreads", "totals")
    for rate, step in RATES.items():
        sub = [x for x in obs if x[0] % step == 0]
        seen = changes(sub)
        if is_pin_line:
            line_moves = [(t, v) for t, pv, v in truth if pv[0] != v[0]]
            for t0, v in line_moves:
                tot[(rate, bucket)] += 1
                hit = next((t for t, _pv, vv in seen if vv[0] == v[0] and t >= t0), None)
                if hit is not None:
                    caught[(rate, bucket)] += 1
                    delays[(rate, bucket)].append(hit - t0)
        else:
            exch[(rate, bucket, "truth")] += len(truth)
            exch[(rate, bucket, "seen")] += len(seen)
if credits >= MAX_CREDITS:
    print(f"STOPPED at the credit cap {MAX_CREDITS}")
if OUT:
    import gzip
    with gzip.open(OUT, "wt") as fh:
        json.dump({"poll_s": POLL_S, "poll_t": poll_t, "start": start_of, "names": names,
                   "series": [[list(k), [[a, b, list(v)] for a, b, v in obs]] for k, obs in series.items()]}, fh)
print(f"polls {i} every {POLL_S}s over {MINUTES} min | sports {SPORTS} | events {len(start_of)} | credits {credits}")
print("PINNACLE LINE MOVES (what alerts act on): caught / total, median detection delay")
for bucket in ("<=60 min", ">60 min"):
    for rate in RATES:
        n, c = tot[(rate, bucket)], caught[(rate, bucket)]
        d = sorted(delays[(rate, bucket)])
        print(f"  {bucket:<9} {rate:>5}: caught {c}/{n} ({100 * c / n:.0f}%)" if n else f"  {bucket:<9} {rate:>5}: none",
              f"| median delay {round(d[len(d) // 2])}s" if d else "")
print("EXCHANGE / OTHER-BOOK PRICE CHANGES seen by each sampler (truth = 15 s)")
for bucket in ("<=60 min", ">60 min"):
    t = exch[("15s", bucket, "truth")]
    print(f"  {bucket:<9} truth {t} | " + " | ".join(f"{r} {exch[(r, bucket, 'seen')]}" for r in RATES))
