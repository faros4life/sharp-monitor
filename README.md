# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T17:46:07Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1748 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 422 | 327 | -6.26c | 19.6% | 63 | -4.52c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 32 | 27 | -0.78c | 40.7% | 25 | -0.07c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 20 | 18 | -0.68c | 33.3% | 17 | 0.05c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 10 | 7 | -2.01c | 42.9% | 6 | -1.23c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 61 | 50 | -0.72c | 32.0% | 50 | -0.54c | 50 | 27-23-0 | +3.02u | 6.0% | 0.27c | 166s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 33 | 22 | -0.67c | 31.8% | 22 | -0.61c | 22 | 11-11-0 | -0.80u | -3.6% | 0.16c | 169s |  |
| M gettable, price moves | 28 | 28 | -0.76c | 32.1% | 28 | -0.49c | 28 | 16-12-0 | +3.82u | 13.6% | 0.36c | 105s |  |
| M control: not gettable | 201 | 129 | -0.71c | 32.6% | 124 | -1.23c | 132 | 69-61-2 | -0.24u | -0.2% | 1.76c | 173s |  |
| M all moves | 262 | 179 | -0.71c | 32.4% | 174 | -1.03c | 182 | 96-84-2 | +2.77u | 1.5% | 1.39c | 170s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 173 | 120 | -1.86c | 18.3% | 12 | -1.49c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 87 | 6 | 8.1% | -0.87c | 1.75c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 87 | 2 | 2.7% | -1.19c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 171 | 7 | 4.7% | -1.77c | 1.15c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 169 | 2 | 1.4% | -1.54c | 2.08c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 258 | 13 | 5.8% | -1.35c | 1.34c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 256 | 4 | 1.8% | -1.37c | 2.26c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 25.

## Odds API credits (100K/month plan)

Study: 476/day, projected 14288/30 days. All monitors on the key: 1952/day, projected 58546/30 days. Remaining 65506; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T17:40:18Z: 60 games (25 in 24h), quotes {'prophetx': 3162, 'novig': 664, 'kalshi': 2792, 'polymarket_us': 1908}, 1154 unmatched, 4401 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, maker posted 44 filled 0, credits used 8 left 65506, 349s
- 2026-10-30T17:30:39Z: 60 games (25 in 24h), quotes {'prophetx': 3170, 'novig': 658, 'kalshi': 2348, 'polymarket_us': 1434}, 887 unmatched, 4039 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 3 B 0, maker posted 8 filled 0, credits used 4 left 65523, 358s
- 2026-10-30T17:25:40Z: 60 games (25 in 24h), quotes {'prophetx': 3170, 'novig': 662, 'kalshi': 2588, 'polymarket_us': 1926}, 1010 unmatched, 4364 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 65527, 278s
- 2026-10-30T17:20:18Z: 60 games (25 in 24h), quotes {'prophetx': 3150, 'novig': 670, 'kalshi': 3558, 'polymarket_us': 3070}, 2333 unmatched, 4994 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 16 B 0, maker posted 0 filled 0, credits used 8 left 65538, 301s
- 2026-10-30T17:10:17Z: 60 games (25 in 24h), quotes {'prophetx': 3042, 'novig': 670, 'kalshi': 3600, 'polymarket_us': 3242}, 2508 unmatched, 4995 side/lines, polls [NBA:fast; NCAAF:fast; NBA:fast], moves 1, new A 7 B 1, maker posted 8 filled 0, credits used 6 left 65557, 325s
- 2026-10-30T17:00:26Z: 60 games (25 in 24h), quotes {'prophetx': 2918, 'novig': 660, 'kalshi': 2890, 'polymarket_us': 1810}, 1167 unmatched, 4283 side/lines, polls [NCAAF:fast,NBA:slow; NCAAF:fast], moves 0, new A 11 B 0, maker posted 11 filled 0, credits used 6 left 65579, 304s
- 2026-10-30T16:51:03Z: 60 games (24 in 24h), quotes {'prophetx': 2878, 'novig': 666, 'kalshi': 3616, 'polymarket_us': 2238}, 1633 unmatched, 4926 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 65605, 186s
- 2026-10-30T16:47:40Z: 60 games (24 in 24h), quotes {'prophetx': 2924, 'novig': 660, 'kalshi': 2780, 'polymarket_us': 1502}, 1103 unmatched, 4218 side/lines, polls [none_due], moves 0, new A 11 B 0, maker posted 0 filled 0, credits used 0 left 65612, 184s
- 2026-10-30T16:44:13Z: 60 games (23 in 24h), quotes {'prophetx': 2792, 'novig': 668, 'kalshi': 2600, 'polymarket_us': 1732}, 979 unmatched, 4188 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 65612, 186s
- 2026-10-30T16:40:18Z: 60 games (23 in 24h), quotes {'prophetx': 2792, 'novig': 668, 'kalshi': 2584, 'polymarket_us': 1480}, 952 unmatched, 4092 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 65612, 216s
