# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T22:35:46Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1905 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 466 | 327 | -6.26c | 19.6% | 63 | -4.52c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 35 | 27 | -0.78c | 40.7% | 25 | -0.07c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 22 | 18 | -0.68c | 33.3% | 17 | 0.05c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 11 | 7 | -2.01c | 42.9% | 6 | -1.23c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 72 | 50 | -0.72c | 32.0% | 50 | -0.54c | 50 | 27-23-0 | +3.02u | 6.0% | 0.27c | 56s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 39 | 22 | -0.67c | 31.8% | 22 | -0.61c | 22 | 11-11-0 | -0.80u | -3.6% | 0.16c | 139s |  |
| M gettable, price moves | 33 | 28 | -0.76c | 32.1% | 28 | -0.49c | 28 | 16-12-0 | +3.82u | 13.6% | 0.36c | 28s |  |
| M control: not gettable | 251 | 129 | -0.71c | 32.6% | 124 | -1.23c | 132 | 69-61-2 | -0.24u | -0.2% | 1.76c | 148s |  |
| M all moves | 323 | 179 | -0.71c | 32.4% | 174 | -1.03c | 182 | 96-84-2 | +2.77u | 1.5% | 1.39c | 91s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 194 | 120 | -1.86c | 18.3% | 12 | -1.49c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 149 | 12 | 8.7% | -0.87c | 1.75c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 150 | 6 | 4.3% | -1.19c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 348 | 14 | 4.7% | -1.77c | 1.15c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 345 | 3 | 1.0% | -1.54c | 2.08c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 497 | 26 | 5.9% | -1.35c | 1.34c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 495 | 9 | 2.1% | -1.37c | 2.26c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 27.

## Odds API credits (100K/month plan)

Study: 510/day, projected 15291/30 days. All monitors on the key: 2024/day, projected 60730/30 days. Remaining 64886; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T22:30:35Z: 60 games (47 in 24h), quotes {'prophetx': 6146, 'novig': 666, 'kalshi': 3672, 'polymarket_us': 3244}, 2882 unmatched, 6869 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 0 filled 2, credits used 4 left 64886, 311s
- 2026-10-30T22:26:05Z: 60 games (46 in 24h), quotes {'prophetx': 6042, 'novig': 664, 'kalshi': 3600, 'polymarket_us': 3040}, 2671 unmatched, 6779 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 16 filled 0, credits used 4 left 64894, 254s
- 2026-10-30T22:20:18Z: 60 games (46 in 24h), quotes {'prophetx': 6026, 'novig': 656, 'kalshi': 3100, 'polymarket_us': 1988}, 1679 unmatched, 6450 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 5 B 0, maker posted 20 filled 0, credits used 8 left 64909, 329s
- 2026-10-30T22:10:15Z: 60 games (46 in 24h), quotes {'prophetx': 6026, 'novig': 662, 'kalshi': 2792, 'polymarket_us': 1950}, 1469 unmatched, 6369 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 3 B 0, maker posted 28 filled 0, credits used 8 left 64930, 301s
- 2026-10-30T22:00:24Z: 60 games (46 in 24h), quotes {'prophetx': 6034, 'novig': 658, 'kalshi': 2780, 'polymarket_us': 1886}, 1454 unmatched, 6330 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 4 left 64956, 209s
- 2026-10-30T21:52:36Z: 60 games (46 in 24h), quotes {'prophetx': 6030, 'novig': 664, 'kalshi': 3086, 'polymarket_us': 0}, 1576 unmatched, 5540 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, maker posted 8 filled 0, credits used 4 left 64968, 231s
- 2026-10-30T21:48:21Z: 60 games (46 in 24h), quotes {'prophetx': 1988, 'novig': 658, 'kalshi': 3274, 'polymarket_us': 2758}, 1991 unmatched, 4309 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 5 B 0, maker posted 4 filled 0, credits used 4 left 64979, 237s
- 2026-10-30T21:40:18Z: 60 games (46 in 24h), quotes {'prophetx': 3804, 'novig': 660, 'kalshi': 2790, 'polymarket_us': 1760}, 1405 unmatched, 4557 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 3 B 0, maker posted 44 filled 0, credits used 8 left 64992, 301s
- 2026-10-30T21:30:22Z: 60 games (46 in 24h), quotes {'prophetx': 5042, 'novig': 658, 'kalshi': 2356, 'polymarket_us': 1484}, 1178 unmatched, 5304 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 65009, 245s
- 2026-10-30T21:24:23Z: 60 games (46 in 24h), quotes {'prophetx': 6018, 'novig': 664, 'kalshi': 2588, 'polymarket_us': 2000}, 1317 unmatched, 6370 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 12 filled 0, credits used 4 left 65024, 255s
