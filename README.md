# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-27T23:50:14Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 351 | 99 | -0.37c | 23.2% | 99 | -0.97c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 96 | 26 | 0.79c | 11.5% | 26 | -0.22c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| B Pinnacle (>= 3% EV) | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 9 | 2 | -0.2c | 0.0% | 2 | 0.67c | 0 | 0-0-0 | +0.00u |  | 1.23c | 18s | criteria not met (0/50 graded, record not positive) |
| M gettable, line moves | 4 | 1 | -0.25c | 0.0% | 1 | 0.96c | 0 | 0-0-0 | +0.00u |  | 1.3c | 31s |  |
| M gettable, price moves | 5 | 1 | -0.14c | 0.0% | 1 | 0.37c | 0 | 0-0-0 | +0.00u |  | 1.15c | 16s |  |
| M control: not gettable | 14 | 5 | -1.16c | 0.0% | 6 | -1.52c | 0 | 0-0-0 | +0.00u |  | 0.71c | 19s |  |
| M all moves | 23 | 7 | -0.88c | 0.0% | 8 | -0.97c | 0 | 0-0-0 | +0.00u |  | 0.84c | 18s |  |

A and B on the same side/line: 1.

## Odds API credits (100K/month plan)

Study: 1100/day, projected 33012/30 days. All monitors on the key: 3955/day, projected 118660/30 days. Remaining 70538; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-27T23:45:24Z: 17 games (10 in 24h), quotes {'prophetx': 492, 'novig': 695, 'kalshi': 1228, 'polymarket_us': 1378}, 146 unmatched, 2102 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, credits used 4 left 70538, 290s
- 2026-10-27T23:40:48Z: 18 games (11 in 24h), quotes {'prophetx': 468, 'novig': 703, 'kalshi': 1206, 'polymarket_us': 1378}, 70 unmatched, 2147 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, credits used 4 left 70553, 266s
- 2026-10-27T23:35:25Z: 17 games (10 in 24h), quotes {'prophetx': 464, 'novig': 697, 'kalshi': 1204, 'polymarket_us': 1378}, 66 unmatched, 2139 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 7 B 0, credits used 4 left 70574, 312s
- 2026-10-27T23:30:12Z: 17 games (10 in 24h), quotes {'prophetx': 476, 'novig': 699, 'kalshi': 1176, 'polymarket_us': 1378}, 66 unmatched, 2133 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 26 B 0, credits used 8 left 70578, 301s
- 2026-10-27T23:20:10Z: 17 games (10 in 24h), quotes {'prophetx': 608, 'novig': 700, 'kalshi': 1124, 'polymarket_us': 1384}, 76 unmatched, 2153 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 5, new A 5 B 0, credits used 4 left 70618, 355s
- 2026-10-27T23:16:32Z: 17 games (10 in 24h), quotes {'prophetx': 616, 'novig': 694, 'kalshi': 1112, 'polymarket_us': 1384}, 74 unmatched, 2153 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 70632, 181s
- 2026-10-27T23:10:11Z: 16 games (10 in 24h), quotes {'prophetx': 592, 'novig': 691, 'kalshi': 1100, 'polymarket_us': 1384}, 72 unmatched, 2135 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 8 B 0, credits used 4 left 70642, 257s
- 2026-10-27T23:00:27Z: 16 games (7 in 24h), quotes {'prophetx': 624, 'novig': 561, 'kalshi': 1110, 'polymarket_us': 1384}, 0 unmatched, 2219 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 26 B 0, credits used 4 left 70746, 289s
- 2026-10-27T22:56:43Z: 15 games (6 in 24h), quotes {'prophetx': 616, 'novig': 565, 'kalshi': 1024, 'polymarket_us': 870}, 0 unmatched, 1814 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 4 left 70762, 213s
- 2026-10-27T22:50:14Z: 15 games (6 in 24h), quotes {'prophetx': 644, 'novig': 567, 'kalshi': 1022, 'polymarket_us': 870}, 0 unmatched, 1803 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 3, new A 6 B 0, credits used 8 left 70766, 377s
