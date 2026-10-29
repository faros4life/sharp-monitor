# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T00:23:23Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1172 | 977 | -3.58c | 22.3% | 978 | -3.92c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 391 | 307 | -6.82c | 14.3% | 308 | -7.3c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria not met (71/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 19 | 16 | -0.64c | 37.5% | 16 | -0.36c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 13 | -0.91c | 30.8% | 13 | -0.29c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 3 | 2 | -1.25c | 50.0% | 2 | -2.54c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 34 | 31 | -0.78c | 29.0% | 31 | -0.69c | 11 | 6-5-0 | +0.85u | 7.7% | 0.26c | 70s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 13 | 11 | -0.87c | 27.3% | 11 | -1.0c | 4 | 2-2-0 | -0.17u | -4.3% | -0.13c | 91s |  |
| M gettable, price moves | 21 | 20 | -0.74c | 30.0% | 20 | -0.52c | 7 | 4-3-0 | +1.02u | 14.6% | 0.48c | 49s |  |
| M control: not gettable | 114 | 66 | -1.02c | 30.3% | 69 | -1.29c | 15 | 9-6-0 | +2.19u | 14.6% | 1.54c | 28s |  |
| M all moves | 148 | 97 | -0.94c | 29.9% | 100 | -1.1c | 26 | 15-11-0 | +3.04u | 11.7% | 1.19c | 28s |  |

A and B on the same side/line: 16.

## Odds API credits (100K/month plan)

Study: 579/day, projected 17377/30 days. All monitors on the key: 2282/day, projected 68449/30 days. Remaining 68475; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T00:20:12Z: 8 games (7 in 24h), quotes {'prophetx': 662, 'novig': 608, 'kalshi': 1204, 'polymarket_us': 1204}, 845 unmatched, 1465 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 4 B 0, credits used 4 left 68475, 191s
- 2026-10-29T00:13:36Z: 7 games (5 in 24h), quotes {'prophetx': 578, 'novig': 517, 'kalshi': 1222, 'polymarket_us': 996}, 990 unmatched, 1190 side/lines, polls [none_due; NBA:fast], moves 2, new A 5 B 0, credits used 2 left 68488, 311s
- 2026-10-29T00:10:13Z: 9 games (7 in 24h), quotes {'prophetx': 578, 'novig': 517, 'kalshi': 1228, 'polymarket_us': 996}, 845 unmatched, 1342 side/lines, polls [none_due; NBA:fast], moves 0, new A 6 B 0, credits used 2 left 68498, 190s
- 2026-10-29T00:06:10Z: 11 games (9 in 24h), quotes {'prophetx': 578, 'novig': 517, 'kalshi': 1230, 'polymarket_us': 996}, 703 unmatched, 1494 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 15 B 0, credits used 4 left 68508, 133s
- 2026-10-29T00:00:19Z: 11 games (9 in 24h), quotes {'prophetx': 578, 'novig': 719, 'kalshi': 1242, 'polymarket_us': 996}, 711 unmatched, 1580 side/lines, polls [none_due; NBA:fast], moves 4, new A 28 B 0, credits used 2 left 68512, 274s
- 2026-10-28T23:50:35Z: 12 games (10 in 24h), quotes {'prophetx': 1102, 'novig': 701, 'kalshi': 1262, 'polymarket_us': 1442}, 567 unmatched, 2192 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 4 left 68526, 288s
- 2026-10-28T23:46:23Z: 12 games (10 in 24h), quotes {'prophetx': 1102, 'novig': 695, 'kalshi': 1274, 'polymarket_us': 1442}, 577 unmatched, 2192 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 9 B 0, credits used 4 left 68542, 239s
- 2026-10-28T23:40:33Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 702, 'kalshi': 1288, 'polymarket_us': 1442}, 513 unmatched, 2219 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 3, new A 10 B 2, credits used 6 left 68548, 338s
- 2026-10-28T23:35:34Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 698, 'kalshi': 1308, 'polymarket_us': 1442}, 527 unmatched, 2228 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 11 B 0, credits used 4 left 68564, 288s
- 2026-10-28T23:30:16Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 696, 'kalshi': 1314, 'polymarket_us': 1442}, 537 unmatched, 2241 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, credits used 8 left 68583, 306s
