# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T16:51:09Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 869 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 312 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 6 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 4 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 21 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 186s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 8 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 138s |  |
| M gettable, price moves | 13 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 187s |  |
| M control: not gettable | 61 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 187s |  |
| M all moves | 82 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 187s |  |

A and B on the same side/line: 5.

## Odds API credits (100K/month plan)

Study: 385/day, projected 11536/30 days. All monitors on the key: 1920/day, projected 57613/30 days. Remaining 69507; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T16:48:04Z: 17 games (14 in 24h), quotes {'prophetx': 1420, 'novig': 695, 'kalshi': 1264, 'polymarket_us': 1634}, 178 unmatched, 2780 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 2, new A 5 B 1, credits used 6 left 69507, 184s
- 2026-10-28T16:40:12Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1266, 'polymarket_us': 1908}, 178 unmatched, 2891 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69523, 183s
- 2026-10-28T16:35:19Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1268, 'polymarket_us': 1708}, 178 unmatched, 2821 side/lines, polls [none_due], moves 0, new A 1 B 0, credits used 0 left 69533, 183s
- 2026-10-28T16:30:59Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 699, 'kalshi': 1268, 'polymarket_us': 1908}, 178 unmatched, 2892 side/lines, polls [none_due], moves 0, new A 4 B 0, credits used 0 left 69533, 181s
- 2026-10-28T16:20:14Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 699, 'kalshi': 1268, 'polymarket_us': 1908}, 178 unmatched, 2893 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 2, new A 2 B 0, credits used 6 left 69555, 185s
- 2026-10-28T16:10:13Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 695, 'kalshi': 1266, 'polymarket_us': 1908}, 178 unmatched, 2889 side/lines, polls [none_due], moves 0, new A 0 B 0, credits used 0 left 69575, 181s
- 2026-10-28T16:03:46Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 697, 'kalshi': 1270, 'polymarket_us': 1670}, 178 unmatched, 2813 side/lines, polls [none_due], moves 0, new A 0 B 0, credits used 0 left 69587, 181s
- 2026-10-28T16:00:27Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 703, 'kalshi': 1272, 'polymarket_us': 1390}, 178 unmatched, 2689 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 69587, 185s
- 2026-10-28T15:53:28Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 693, 'kalshi': 1270, 'polymarket_us': 1780}, 178 unmatched, 2830 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 3, new A 1 B 0, credits used 6 left 69609, 185s
- 2026-10-28T15:50:13Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 695, 'kalshi': 1268, 'polymarket_us': 1908}, 178 unmatched, 2887 side/lines, polls [none_due], moves 0, new A 3 B 0, credits used 0 left 69615, 183s
