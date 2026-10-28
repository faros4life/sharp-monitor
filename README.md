# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T22:25:55Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 999 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 339 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 15 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 12 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 2 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 30 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 173s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 12 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 137s |  |
| M gettable, price moves | 18 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 174s |  |
| M control: not gettable | 97 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 29s |  |
| M all moves | 127 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 91s |  |

A and B on the same side/line: 12.

## Odds API credits (100K/month plan)

Study: 545/day, projected 16339/30 days. All monitors on the key: 2202/day, projected 66061/30 days. Remaining 68751; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T22:21:33Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1338, 'polymarket_us': 1918}, 184 unmatched, 3012 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68751, 262s
- 2026-10-28T22:17:53Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 702, 'kalshi': 1336, 'polymarket_us': 1918}, 184 unmatched, 3013 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 4 B 0, credits used 4 left 68761, 209s
- 2026-10-28T22:10:12Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1344, 'polymarket_us': 1916}, 184 unmatched, 3009 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, credits used 4 left 68777, 358s
- 2026-10-28T22:04:50Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1344, 'polymarket_us': 1916}, 184 unmatched, 3014 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 6 left 68795, 288s
- 2026-10-28T21:59:36Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 693, 'kalshi': 1340, 'polymarket_us': 1872}, 184 unmatched, 2977 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 8 left 68801, 301s
- 2026-10-28T21:50:11Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 695, 'kalshi': 1340, 'polymarket_us': 1916}, 184 unmatched, 2998 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 1, credits used 4 left 68835, 198s
- 2026-10-28T21:43:41Z: 18 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 697, 'kalshi': 1306, 'polymarket_us': 1916}, 180 unmatched, 2967 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 1, new A 2 B 0, credits used 6 left 68849, 314s
- 2026-10-28T21:38:28Z: 18 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 697, 'kalshi': 1306, 'polymarket_us': 1398}, 178 unmatched, 2761 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 3 B 1, credits used 8 left 68859, 301s
- 2026-10-28T21:30:17Z: 18 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 691, 'kalshi': 1306, 'polymarket_us': 1696}, 178 unmatched, 2891 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 68881, 183s
- 2026-10-28T21:23:32Z: 18 games (14 in 24h), quotes {'prophetx': 1444, 'novig': 693, 'kalshi': 1270, 'polymarket_us': 1916}, 178 unmatched, 2933 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 0 B 0, credits used 4 left 68895, 282s
