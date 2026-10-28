# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T00:02:54Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 379 | 154 | 0.2c | 24.0% | 154 | -0.04c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| A qualifying (>= 3c) | 114 | 51 | 1.92c | 13.7% | 51 | 2.44c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| B Pinnacle (>= 3% EV) | 1 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 1 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 9 | 8 | -0.41c | 37.5% | 8 | -0.33c | 0 | 0-0-0 | +0.00u |  | 0.74c | 18s | criteria not met (0/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 4 | 3 | -0.71c | 33.3% | 3 | -0.68c | 0 | 0-0-0 | +0.00u |  | 0.51c | 31s |  |
| M gettable, price moves | 5 | 5 | -0.23c | 40.0% | 5 | -0.13c | 0 | 0-0-0 | +0.00u |  | 0.87c | 16s |  |
| M control: not gettable | 15 | 9 | -0.9c | 11.1% | 10 | -1.4c | 0 | 0-0-0 | +0.00u |  | 0.89c | 16s |  |
| M all moves | 24 | 17 | -0.67c | 23.5% | 18 | -0.93c | 0 | 0-0-0 | +0.00u |  | 0.82c | 17s |  |

A and B on the same side/line: 1.

## Odds API credits (100K/month plan)

Study: 1071/day, projected 32137/30 days. All monitors on the key: 3876/day, projected 116279/30 days. Remaining 70512; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-27T23:59:53Z: 17 games (10 in 24h), quotes {'prophetx': 460, 'novig': 693, 'kalshi': 1248, 'polymarket_us': 1378}, 122 unmatched, 2156 side/lines, polls [none_due; NBA:fast], moves 0, new A 19 B 0, credits used 2 left 70512, 181s
- 2026-10-27T23:50:25Z: 17 games (10 in 24h), quotes {'prophetx': 468, 'novig': 705, 'kalshi': 1216, 'polymarket_us': 1378}, 138 unmatched, 2086 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 9 B 0, credits used 4 left 70528, 313s
- 2026-10-27T23:45:24Z: 17 games (10 in 24h), quotes {'prophetx': 492, 'novig': 695, 'kalshi': 1228, 'polymarket_us': 1378}, 146 unmatched, 2102 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, credits used 4 left 70538, 290s
- 2026-10-27T23:40:48Z: 18 games (11 in 24h), quotes {'prophetx': 468, 'novig': 703, 'kalshi': 1206, 'polymarket_us': 1378}, 70 unmatched, 2147 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, credits used 4 left 70553, 266s
- 2026-10-27T23:35:25Z: 17 games (10 in 24h), quotes {'prophetx': 464, 'novig': 697, 'kalshi': 1204, 'polymarket_us': 1378}, 66 unmatched, 2139 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 7 B 0, credits used 4 left 70574, 312s
- 2026-10-27T23:30:12Z: 17 games (10 in 24h), quotes {'prophetx': 476, 'novig': 699, 'kalshi': 1176, 'polymarket_us': 1378}, 66 unmatched, 2133 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 26 B 0, credits used 8 left 70578, 301s
- 2026-10-27T23:20:10Z: 17 games (10 in 24h), quotes {'prophetx': 608, 'novig': 700, 'kalshi': 1124, 'polymarket_us': 1384}, 76 unmatched, 2153 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 5, new A 5 B 0, credits used 4 left 70618, 355s
- 2026-10-27T23:16:32Z: 17 games (10 in 24h), quotes {'prophetx': 616, 'novig': 694, 'kalshi': 1112, 'polymarket_us': 1384}, 74 unmatched, 2153 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 70632, 181s
- 2026-10-27T23:10:11Z: 16 games (10 in 24h), quotes {'prophetx': 592, 'novig': 691, 'kalshi': 1100, 'polymarket_us': 1384}, 72 unmatched, 2135 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 8 B 0, credits used 4 left 70642, 257s
- 2026-10-27T23:00:27Z: 16 games (7 in 24h), quotes {'prophetx': 624, 'novig': 561, 'kalshi': 1110, 'polymarket_us': 1384}, 0 unmatched, 2219 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 26 B 0, credits used 4 left 70746, 289s
