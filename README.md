# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T23:02:02Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1017 | 375 | -0.3c | 25.6% | 375 | -0.26c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 343 | 89 | 1.08c | 18.0% | 89 | 2.13c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 16 | 2 | -2.56c | 0.0% | 2 | -3.31c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 12 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 3 | 1 | -3.0c | 0.0% | 1 | -6.12c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 32 | 14 | -0.35c | 35.7% | 14 | -0.37c | 11 | 6-5-0 | +0.85u | 7.7% | 0.65c | 126s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 12 | 5 | -0.44c | 40.0% | 5 | -0.62c | 4 | 2-2-0 | -0.17u | -4.3% | 0.47c | 137s |  |
| M gettable, price moves | 20 | 9 | -0.29c | 33.3% | 9 | -0.24c | 7 | 4-3-0 | +1.02u | 14.6% | 0.75c | 105s |  |
| M control: not gettable | 101 | 15 | -0.93c | 20.0% | 17 | -1.22c | 15 | 9-6-0 | +2.19u | 14.6% | 1.37c | 28s |  |
| M all moves | 133 | 29 | -0.65c | 27.6% | 31 | -0.84c | 26 | 15-11-0 | +3.04u | 11.7% | 1.09c | 29s |  |

A and B on the same side/line: 13.

## Odds API credits (100K/month plan)

Study: 557/day, projected 16718/30 days. All monitors on the key: 2237/day, projected 67112/30 days. Remaining 68656; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T22:57:46Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 695, 'kalshi': 1346, 'polymarket_us': 1918}, 182 unmatched, 2993 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, credits used 6 left 68656, 256s
- 2026-10-28T22:50:11Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 701, 'kalshi': 1350, 'polymarket_us': 1918}, 184 unmatched, 2981 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, credits used 8 left 68674, 301s
- 2026-10-28T22:40:12Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1340, 'polymarket_us': 1918}, 182 unmatched, 2995 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 68702, 210s
- 2026-10-28T22:35:40Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 694, 'kalshi': 1340, 'polymarket_us': 1918}, 182 unmatched, 2990 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, credits used 4 left 68723, 182s
- 2026-10-28T22:30:13Z: 18 games (14 in 24h), quotes {'prophetx': 1328, 'novig': 700, 'kalshi': 1338, 'polymarket_us': 1918}, 180 unmatched, 2916 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 2, new A 3 B 0, credits used 6 left 68733, 233s
- 2026-10-28T22:21:33Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1338, 'polymarket_us': 1918}, 184 unmatched, 3012 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68751, 262s
- 2026-10-28T22:17:53Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 702, 'kalshi': 1336, 'polymarket_us': 1918}, 184 unmatched, 3013 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 4 B 0, credits used 4 left 68761, 209s
- 2026-10-28T22:10:12Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1344, 'polymarket_us': 1916}, 184 unmatched, 3009 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, credits used 4 left 68777, 358s
- 2026-10-28T22:04:50Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1344, 'polymarket_us': 1916}, 184 unmatched, 3014 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 6 left 68795, 288s
- 2026-10-28T21:59:36Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 693, 'kalshi': 1340, 'polymarket_us': 1872}, 184 unmatched, 2977 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 8 left 68801, 301s
