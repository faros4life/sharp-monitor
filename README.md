# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T15:17:39Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 838 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 309 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 5 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 18 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 126s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 7 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 91s |  |
| M gettable, price moves | 11 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 162s |  |
| M control: not gettable | 54 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 187s |  |
| M all moves | 72 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 187s |  |

A and B on the same side/line: 4.

## Odds API credits (100K/month plan)

Study: 386/day, projected 11572/30 days. All monitors on the key: 1869/day, projected 56079/30 days. Remaining 69673; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T15:14:37Z: 17 games (14 in 24h), quotes {'prophetx': 1420, 'novig': 691, 'kalshi': 1256, 'polymarket_us': 1310}, 176 unmatched, 2639 side/lines, polls [none_due], moves 0, new A 5 B 0, credits used 0 left 69673, 182s
- 2026-10-28T15:10:15Z: 17 games (14 in 24h), quotes {'prophetx': 1420, 'novig': 695, 'kalshi': 1250, 'polymarket_us': 1650}, 176 unmatched, 2782 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69673, 182s
- 2026-10-28T15:05:32Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 701, 'kalshi': 1250, 'polymarket_us': 1824}, 176 unmatched, 2858 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69683, 184s
- 2026-10-28T15:00:22Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 703, 'kalshi': 1248, 'polymarket_us': 1836}, 176 unmatched, 2852 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 5, new A 4 B 0, credits used 6 left 69687, 186s
- 2026-10-28T14:50:13Z: 17 games (14 in 24h), quotes {'prophetx': 1420, 'novig': 701, 'kalshi': 1248, 'polymarket_us': 1908}, 176 unmatched, 2874 side/lines, polls [none_due], moves 0, new A 6 B 0, credits used 0 left 69717, 184s
- 2026-10-28T14:40:12Z: 17 games (14 in 24h), quotes {'prophetx': 1420, 'novig': 693, 'kalshi': 1244, 'polymarket_us': 1908}, 176 unmatched, 2870 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69737, 182s
- 2026-10-28T14:30:16Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 699, 'kalshi': 1244, 'polymarket_us': 1522}, 176 unmatched, 2696 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 7, new A 1 B 0, credits used 6 left 69737, 184s
- 2026-10-28T14:24:18Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 691, 'kalshi': 1244, 'polymarket_us': 1906}, 176 unmatched, 2844 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69763, 182s
- 2026-10-28T14:20:12Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 693, 'kalshi': 1242, 'polymarket_us': 1880}, 176 unmatched, 2821 side/lines, polls [none_due], moves 0, new A 1 B 0, credits used 0 left 69763, 182s
- 2026-10-28T14:16:47Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1242, 'polymarket_us': 1728}, 176 unmatched, 2772 side/lines, polls [none_due], moves 0, new A 5 B 0, credits used 0 left 69763, 182s
