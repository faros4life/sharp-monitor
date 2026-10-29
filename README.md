# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T01:35:16Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1207 | 1029 | -3.61c | 22.5% | 1030 | -3.95c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 398 | 329 | -6.91c | 14.6% | 330 | -7.44c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria not met (71/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 20 | 16 | -0.64c | 37.5% | 16 | -0.36c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 13 | -0.91c | 30.8% | 13 | -0.29c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 4 | 2 | -1.25c | 50.0% | 2 | -2.54c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 37 | 31 | -0.78c | 29.0% | 31 | -0.69c | 11 | 6-5-0 | +0.85u | 7.7% | 0.26c | 139s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 15 | 11 | -0.87c | 27.3% | 11 | -1.0c | 4 | 2-2-0 | -0.17u | -4.3% | -0.13c | 139s |  |
| M gettable, price moves | 22 | 20 | -0.74c | 30.0% | 20 | -0.52c | 7 | 4-3-0 | +1.02u | 14.6% | 0.48c | 105s |  |
| M control: not gettable | 117 | 75 | -1.0c | 32.0% | 78 | -1.29c | 15 | 9-6-0 | +2.19u | 14.6% | 1.52c | 28s |  |
| M all moves | 154 | 106 | -0.94c | 31.1% | 109 | -1.12c | 26 | 15-11-0 | +3.04u | 11.7% | 1.2c | 28s |  |

A and B on the same side/line: 17.

## Odds API credits (100K/month plan)

Study: 586/day, projected 17567/30 days. All monitors on the key: 2312/day, projected 69347/30 days. Remaining 68327; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T01:30:15Z: 7 games (6 in 24h), quotes {'prophetx': 358, 'novig': 541, 'kalshi': 976, 'polymarket_us': 948}, 624 unmatched, 1186 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 3 B 0, credits used 6 left 68327, 301s
- 2026-10-29T01:20:12Z: 7 games (6 in 24h), quotes {'prophetx': 538, 'novig': 546, 'kalshi': 1032, 'polymarket_us': 1078}, 680 unmatched, 1315 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, credits used 2 left 68353, 139s
- 2026-10-29T01:10:35Z: 7 games (6 in 24h), quotes {'prophetx': 538, 'novig': 554, 'kalshi': 1084, 'polymarket_us': 1078}, 740 unmatched, 1317 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68364, 284s
- 2026-10-29T01:05:35Z: 8 games (7 in 24h), quotes {'prophetx': 538, 'novig': 547, 'kalshi': 1120, 'polymarket_us': 1078}, 701 unmatched, 1393 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, credits used 2 left 68377, 284s
- 2026-10-29T01:00:55Z: 8 games (7 in 24h), quotes {'prophetx': 538, 'novig': 631, 'kalshi': 1144, 'polymarket_us': 1078}, 708 unmatched, 1422 side/lines, polls [NCAAF:slow; NBA:fast], moves 1, new A 6 B 1, credits used 4 left 68388, 264s
- 2026-10-29T00:55:32Z: 8 games (7 in 24h), quotes {'prophetx': 670, 'novig': 623, 'kalshi': 1184, 'polymarket_us': 1206}, 746 unmatched, 1521 side/lines, polls [none_due; NBA:fast], moves 1, new A 2 B 0, credits used 2 left 68394, 310s
- 2026-10-29T00:50:17Z: 8 games (7 in 24h), quotes {'prophetx': 670, 'novig': 649, 'kalshi': 1204, 'polymarket_us': 1206}, 781 unmatched, 1521 side/lines, polls [NFL:slow,NBA:fast; NBA:fast], moves 2, new A 3 B 0, credits used 6 left 68406, 301s
- 2026-10-29T00:40:11Z: 8 games (7 in 24h), quotes {'prophetx': 670, 'novig': 611, 'kalshi': 1170, 'polymarket_us': 1206}, 786 unmatched, 1479 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 9 B 0, credits used 4 left 68434, 154s
- 2026-10-29T00:30:15Z: 8 games (7 in 24h), quotes {'prophetx': 670, 'novig': 610, 'kalshi': 1176, 'polymarket_us': 1206}, 814 unmatched, 1472 side/lines, polls [NFL:slow,NBA:fast; NBA:fast], moves 1, new A 9 B 0, credits used 6 left 68449, 301s
- 2026-10-29T00:20:12Z: 8 games (7 in 24h), quotes {'prophetx': 662, 'novig': 608, 'kalshi': 1204, 'polymarket_us': 1204}, 845 unmatched, 1465 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 4 B 0, credits used 4 left 68475, 191s
