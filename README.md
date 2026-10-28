# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T23:23:17Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1065 | 661 | -2.33c | 25.0% | 662 | -2.51c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 357 | 181 | -3.66c | 19.9% | 182 | -3.65c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria not met (71/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 17 | 11 | -1.22c | 27.3% | 11 | -1.0c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 13 | 10 | -1.04c | 30.0% | 10 | -0.49c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 3 | 1 | -3.0c | 0.0% | 1 | -6.12c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 33 | 21 | -0.2c | 38.1% | 21 | -0.14c | 11 | 6-5-0 | +0.85u | 7.7% | 0.72c | 91s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 12 | 7 | -0.51c | 28.6% | 7 | -0.63c | 4 | 2-2-0 | -0.17u | -4.3% | 0.09c | 137s |  |
| M gettable, price moves | 21 | 14 | -0.05c | 42.9% | 14 | 0.11c | 7 | 4-3-0 | +1.02u | 14.6% | 1.03c | 49s |  |
| M control: not gettable | 104 | 32 | -0.6c | 31.2% | 34 | -0.93c | 15 | 9-6-0 | +2.19u | 14.6% | 1.71c | 28s |  |
| M all moves | 137 | 53 | -0.44c | 34.0% | 55 | -0.63c | 26 | 15-11-0 | +3.04u | 11.7% | 1.38c | 28s |  |

A and B on the same side/line: 14.

## Odds API credits (100K/month plan)

Study: 565/day, projected 16962/30 days. All monitors on the key: 2243/day, projected 67298/30 days. Remaining 68614; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T23:20:13Z: 13 games (9 in 24h), quotes {'prophetx': 942, 'novig': 704, 'kalshi': 1324, 'polymarket_us': 1216}, 551 unmatched, 2013 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, credits used 6 left 68614, 184s
- 2026-10-28T23:13:26Z: 13 games (9 in 24h), quotes {'prophetx': 934, 'novig': 697, 'kalshi': 1330, 'polymarket_us': 1216}, 558 unmatched, 2016 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 10 B 1, credits used 4 left 68622, 380s
- 2026-10-28T23:10:12Z: 17 games (13 in 24h), quotes {'prophetx': 934, 'novig': 695, 'kalshi': 1328, 'polymarket_us': 1216}, 254 unmatched, 2312 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 24 B 0, credits used 4 left 68636, 182s
- 2026-10-28T23:02:13Z: 17 games (13 in 24h), quotes {'prophetx': 934, 'novig': 693, 'kalshi': 1332, 'polymarket_us': 1216}, 256 unmatched, 2380 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, credits used 4 left 68652, 216s
- 2026-10-28T22:57:46Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 695, 'kalshi': 1346, 'polymarket_us': 1918}, 182 unmatched, 2993 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, credits used 6 left 68656, 256s
- 2026-10-28T22:50:11Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 701, 'kalshi': 1350, 'polymarket_us': 1918}, 184 unmatched, 2981 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, credits used 8 left 68674, 301s
- 2026-10-28T22:40:12Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1340, 'polymarket_us': 1918}, 182 unmatched, 2995 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 68702, 210s
- 2026-10-28T22:35:40Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 694, 'kalshi': 1340, 'polymarket_us': 1918}, 182 unmatched, 2990 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, credits used 4 left 68723, 182s
- 2026-10-28T22:30:13Z: 18 games (14 in 24h), quotes {'prophetx': 1328, 'novig': 700, 'kalshi': 1338, 'polymarket_us': 1918}, 180 unmatched, 2916 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 2, new A 3 B 0, credits used 6 left 68733, 233s
- 2026-10-28T22:21:33Z: 18 games (14 in 24h), quotes {'prophetx': 1460, 'novig': 698, 'kalshi': 1338, 'polymarket_us': 1918}, 184 unmatched, 3012 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68751, 262s
