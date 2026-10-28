# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T14:23:14Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 814 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 299 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 5 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 15 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 49s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 6 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 67s |  |
| M gettable, price moves | 9 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 49s |  |
| M control: not gettable | 45 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 29s |  |
| M all moves | 60 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 46s |  |

A and B on the same side/line: 4.

## Odds API credits (100K/month plan)

Study: 389/day, projected 11672/30 days. All monitors on the key: 1844/day, projected 55325/30 days. Remaining 69763; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T14:20:12Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 693, 'kalshi': 1242, 'polymarket_us': 1880}, 176 unmatched, 2821 side/lines, polls [none_due], moves 0, new A 1 B 0, credits used 0 left 69763, 182s
- 2026-10-28T14:16:47Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1242, 'polymarket_us': 1728}, 176 unmatched, 2772 side/lines, polls [none_due], moves 0, new A 5 B 0, credits used 0 left 69763, 182s
- 2026-10-28T14:10:14Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 691, 'kalshi': 1246, 'polymarket_us': 1650}, 176 unmatched, 2739 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 3, new A 8 B 1, credits used 6 left 69781, 184s
- 2026-10-28T14:00:19Z: 17 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 697, 'kalshi': 1246, 'polymarket_us': 1906}, 176 unmatched, 2849 side/lines, polls [none_due], moves 0, new A 13 B 1, credits used 0 left 69805, 182s
- 2026-10-28T13:50:13Z: 17 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 695, 'kalshi': 1248, 'polymarket_us': 1534}, 176 unmatched, 2713 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 4, new A 8 B 0, credits used 6 left 69823, 183s
- 2026-10-28T13:40:14Z: 17 games (14 in 24h), quotes {'prophetx': 1436, 'novig': 699, 'kalshi': 1248, 'polymarket_us': 1906}, 176 unmatched, 2853 side/lines, polls [none_due], moves 0, new A 7 B 0, credits used 0 left 69845, 184s
- 2026-10-28T13:32:08Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 693, 'kalshi': 1248, 'polymarket_us': 1396}, 176 unmatched, 2643 side/lines, polls [none_due], moves 0, new A 6 B 0, credits used 0 left 69857, 182s
- 2026-10-28T13:28:51Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 695, 'kalshi': 1250, 'polymarket_us': 1522}, 176 unmatched, 2700 side/lines, polls [none_due], moves 0, new A 11 B 0, credits used 0 left 69869, 182s
- 2026-10-28T13:24:21Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1248, 'polymarket_us': 1904}, 176 unmatched, 2851 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 4, new A 2 B 0, credits used 6 left 69873, 183s
- 2026-10-28T13:20:13Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 695, 'kalshi': 1244, 'polymarket_us': 1904}, 176 unmatched, 2851 side/lines, polls [none_due], moves 0, new A 13 B 0, credits used 0 left 69891, 182s
