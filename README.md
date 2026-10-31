# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T21:16:12Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2897 | 2719 | -2.36c | 21.0% | 1048 | -1.37c | 2223 | 1118-1105-0 | -123.30u | -5.5% |  |  | criteria not met (2223/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 808 | 767 | -4.34c | 13.7% | 177 | -3.28c | 550 | 275-275-0 | -35.85u | -6.5% |  |  | criteria not met (550/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 46 | 43 | -0.79c | 34.9% | 41 | 0.01c | 38 | 17-21-0 | -1.02u | -2.7% |  |  | criteria not met (38/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 30 | 28 | -0.53c | 32.1% | 27 | 0.13c | 25 | 12-13-0 | +1.51u | 6.0% |  |  |  |
| B ref age 5m+ | 13 | 12 | -1.87c | 33.3% | 11 | -0.81c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 117 | 101 | -0.65c | 32.7% | 100 | -0.77c | 81 | 45-36-0 | +6.19u | 7.6% | 0.15c | 24s | criteria not met (81/50 graded, CLV not positive) |
| M gettable, line moves | 63 | 56 | -0.56c | 35.7% | 55 | -0.91c | 44 | 24-20-0 | +2.01u | 4.6% | 0.04c | 28s |  |
| M gettable, price moves | 54 | 45 | -0.77c | 28.9% | 45 | -0.59c | 37 | 21-16-0 | +4.18u | 11.3% | 0.28c | 20s |  |
| M control: not gettable | 455 | 301 | -0.8c | 33.6% | 301 | -1.26c | 240 | 132-105-3 | +12.22u | 5.1% | 1.82c | 27s |  |
| M all moves | 572 | 402 | -0.76c | 33.3% | 401 | -1.14c | 321 | 177-141-3 | +18.41u | 5.7% | 1.46c | 26s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 543 | 486 | 2.95c | 28.0% | 103 | 2.65c | 280 | 127-153-0 | +138.98u | 49.6% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 7 | 0 | -0.24c | 0-0-0 | +0.00u | 0, -0.31c, +0.00u | not enough yet |
| J2 B, NBA | 4 | 0 | -1.49c | 0-0-0 | +0.00u | 0, -3.03c, +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 5 | 0 | -0.26c | 0-0-0 | +0.00u | 0, -0.36c, +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 26 | 2 | -0.84c | 0-2-0 | -2.00u | 2, -1.15c, -2.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 | 0.76c | 0-0-0 | +0.00u | 0, 0.76c, +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 3 | -1.47c | 1-2-0 | -1.60u | 3, -1.47c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 262 | 18 | 7.3% | -0.5c | 1.67c | 9-7-0 | +2.10u |  |
| MK novig fair-2c | 259 | 7 | 2.9% | -0.86c | 2.6c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1353 | 65 | 5.1% | -0.81c | 1.1c | 16-21-0 | -4.21u |  |
| MK prophetx fair-2c | 1340 | 16 | 1.3% | -0.64c | 2.04c | 3-7-0 | -3.81u |  |
| MK all fair-1c | 1615 | 83 | 5.5% | -0.75c | 1.2c | 25-28-0 | -2.12u | criteria not met (53/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1599 | 23 | 1.5% | -0.71c | 2.14c | 7-9-0 | -1.39u | criteria not met (16/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 36.

## Odds API credits (100K/month plan)

Study: 567/day, projected 17012/30 days. All monitors on the key: 2063/day, projected 61903/30 days. Remaining 62816; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T21:10:18Z: 41 games (36 in 24h), quotes {'prophetx': 3498, 'novig': 672, 'kalshi': 2772, 'polymarket_us': 2100}, 2014 unmatched (63 book-games; fuzzy-matched 0), 4499 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 10 B 0, maker posted 34 filled 2, credits used 12 left 62816, 353s
- 2026-10-31T21:00:29Z: 41 games (35 in 24h), quotes {'prophetx': 3394, 'novig': 668, 'kalshi': 2142, 'polymarket_us': 1482}, 2053 unmatched (62 book-games; fuzzy-matched 0), 3837 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 8 B 0, maker posted 16 filled 0, credits used 8 left 62852, 211s
- 2026-10-31T20:53:43Z: 41 games (34 in 24h), quotes {'prophetx': 3420, 'novig': 655, 'kalshi': 3020, 'polymarket_us': 2662}, 2474 unmatched (70 book-games; fuzzy-matched 0), 4547 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 37 filled 0, credits used 6 left 62871, 277s
- 2026-10-31T20:50:18Z: 41 games (34 in 24h), quotes {'prophetx': 3420, 'novig': 647, 'kalshi': 2256, 'polymarket_us': 1886}, 2360 unmatched (67 book-games; fuzzy-matched 0), 3870 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 4 filled 0, credits used 6 left 62888, 182s
- 2026-10-31T20:40:22Z: 41 games (34 in 24h), quotes {'prophetx': 3420, 'novig': 645, 'kalshi': 3258, 'polymarket_us': 2946}, 2588 unmatched (70 book-games; fuzzy-matched 0), 4652 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 18 B 0, maker posted 8 filled 0, credits used 14 left 62907, 301s
- 2026-10-31T20:30:20Z: 41 games (34 in 24h), quotes {'prophetx': 3394, 'novig': 651, 'kalshi': 2780, 'polymarket_us': 2030}, 2550 unmatched (69 book-games; fuzzy-matched 1), 4035 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 13 B 0, maker posted 27 filled 0, credits used 6 left 62943, 249s
- 2026-10-31T20:21:12Z: 41 games (33 in 24h), quotes {'prophetx': 3394, 'novig': 650, 'kalshi': 2252, 'polymarket_us': 1502}, 2533 unmatched (69 book-games; fuzzy-matched 1), 3627 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 8 B 0, maker posted 36 filled 0, credits used 6 left 62953, 300s
- 2026-10-31T20:17:09Z: 42 games (34 in 24h), quotes {'prophetx': 3390, 'novig': 653, 'kalshi': 2712, 'polymarket_us': 2032}, 2563 unmatched (68 book-games; fuzzy-matched 1), 4052 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 20 filled 0, credits used 8 left 62970, 217s
- 2026-10-31T20:11:35Z: 44 games (36 in 24h), quotes {'prophetx': 3742, 'novig': 649, 'kalshi': 2250, 'polymarket_us': 1468}, 2333 unmatched (67 book-games; fuzzy-matched 1), 3970 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 24 filled 0, credits used 6 left 62991, 277s
- 2026-10-31T20:07:44Z: 46 games (38 in 24h), quotes {'prophetx': 3622, 'novig': 641, 'kalshi': 2964, 'polymarket_us': 2076}, 2373 unmatched (65 book-games; fuzzy-matched 1), 4452 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 16 B 0, maker posted 1 filled 1, credits used 6 left 63008, 205s
