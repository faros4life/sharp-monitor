# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T00:53:19Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 495 | 261 | -0.23c | 22.6% | 261 | -0.35c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 185 | 62 | 1.23c | 12.9% | 62 | 1.77c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| B Pinnacle (>= 3% EV) | 1 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 1 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 9 | 9 | -0.29c | 44.4% | 9 | -0.38c | 0 | 0-0-0 | +0.00u |  | 0.61c | 18s | criteria not met (0/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 4 | 4 | -0.38c | 50.0% | 4 | -0.69c | 0 | 0-0-0 | +0.00u |  | 0.29c | 31s |  |
| M gettable, price moves | 5 | 5 | -0.23c | 40.0% | 5 | -0.13c | 0 | 0-0-0 | +0.00u |  | 0.87c | 16s |  |
| M control: not gettable | 16 | 10 | -0.91c | 10.0% | 12 | -1.38c | 0 | 0-0-0 | +0.00u |  | 0.94c | 15s |  |
| M all moves | 25 | 19 | -0.62c | 26.3% | 21 | -0.95c | 0 | 0-0-0 | +0.00u |  | 0.8c | 16s |  |

A and B on the same side/line: 1.

## Odds API credits (100K/month plan)

Study: 1004/day, projected 30106/30 days. All monitors on the key: 3618/day, projected 108555/30 days. Remaining 70435; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T00:48:19Z: 15 games (12 in 24h), quotes {'prophetx': 228, 'novig': 706, 'kalshi': 1286, 'polymarket_us': 1638}, 476 unmatched, 2015 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 16 B 0, credits used 4 left 70435, 301s
- 2026-10-28T00:40:10Z: 15 games (12 in 24h), quotes {'prophetx': 228, 'novig': 698, 'kalshi': 1296, 'polymarket_us': 1638}, 488 unmatched, 2008 side/lines, polls [none_due; NBA:fast], moves 0, new A 21 B 0, credits used 2 left 70453, 181s
- 2026-10-28T00:30:13Z: 15 games (12 in 24h), quotes {'prophetx': 252, 'novig': 702, 'kalshi': 1290, 'polymarket_us': 1638}, 504 unmatched, 2013 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 0, new A 12 B 0, credits used 6 left 70463, 301s
- 2026-10-28T00:20:10Z: 15 games (12 in 24h), quotes {'prophetx': 228, 'novig': 694, 'kalshi': 1286, 'polymarket_us': 1638}, 512 unmatched, 1988 side/lines, polls [none_due; NBA:fast], moves 0, new A 12 B 0, credits used 2 left 70478, 184s
- 2026-10-28T00:13:25Z: 16 games (13 in 24h), quotes {'prophetx': 244, 'novig': 695, 'kalshi': 1288, 'polymarket_us': 1638}, 446 unmatched, 2074 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, credits used 2 left 70487, 289s
- 2026-10-28T00:10:11Z: 17 games (14 in 24h), quotes {'prophetx': 252, 'novig': 699, 'kalshi': 1280, 'polymarket_us': 1638}, 366 unmatched, 2149 side/lines, polls [none_due; NBA:fast], moves 0, new A 12 B 0, credits used 2 left 70489, 183s
- 2026-10-28T00:03:06Z: 18 games (11 in 24h), quotes {'prophetx': 236, 'novig': 703, 'kalshi': 1248, 'polymarket_us': 1638}, 294 unmatched, 2186 side/lines, polls [NCAAF:fast; NBA:fast; none_due], moves 1, new A 40 B 0, credits used 4 left 70498, 300s
- 2026-10-27T23:59:53Z: 17 games (10 in 24h), quotes {'prophetx': 460, 'novig': 693, 'kalshi': 1248, 'polymarket_us': 1378}, 122 unmatched, 2156 side/lines, polls [none_due; NBA:fast], moves 0, new A 19 B 0, credits used 2 left 70512, 181s
- 2026-10-27T23:50:25Z: 17 games (10 in 24h), quotes {'prophetx': 468, 'novig': 705, 'kalshi': 1216, 'polymarket_us': 1378}, 138 unmatched, 2086 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 9 B 0, credits used 4 left 70528, 313s
- 2026-10-27T23:45:24Z: 17 games (10 in 24h), quotes {'prophetx': 492, 'novig': 695, 'kalshi': 1228, 'polymarket_us': 1378}, 146 unmatched, 2102 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, credits used 4 left 70538, 290s
