# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T04:53:37Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4268 | 3959 | -1.92c | 21.6% | 1602 | -1.15c | 3898 | 1959-1939-0 | -200.42u | -5.1% |  |  | criteria not met (3898/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1081 | 956 | -3.85c | 14.0% | 216 | -3.11c | 934 | 487-447-0 | -55.97u | -6.0% |  |  | criteria not met (934/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 62 | 61 | -0.66c | 32.8% | 59 | 0.13c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 39 | -0.62c | 30.8% | 38 | 0.01c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 18 | 17 | -1.11c | 35.3% | 16 | -0.09c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 154 | 154 | -0.57c | 32.5% | 152 | -0.59c | 153 | 78-74-1 | -2.15u | -1.4% | 0.29c | 22s | criteria not met (153/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 82 | 82 | -0.58c | 35.4% | 81 | -0.81c | 82 | 41-40-1 | -2.38u | -2.9% | 0.01c | 28s |  |
| M gettable, price moves | 72 | 72 | -0.56c | 29.2% | 71 | -0.34c | 71 | 37-34-0 | +0.23u | 0.3% | 0.61c | 20s |  |
| M control: not gettable | 592 | 470 | -0.87c | 34.0% | 466 | -1.22c | 473 | 250-215-8 | +7.96u | 1.7% | 1.76c | 26s |  |
| M all moves | 746 | 624 | -0.79c | 33.7% | 618 | -1.07c | 626 | 328-289-9 | +5.81u | 0.9% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 641 | 614 | 4.4c | 29.2% | 122 | 3.88c | 608 | 271-337-0 | +326.86u | 53.8% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 23 | 22 | 0.2c | 11-11-0 | +0.91u | 17, 0.0c, -0.36u | not enough yet |
| J2 B, NBA | 12 | 11 | 0.09c | 6-5-0 | +1.45u | 7, -0.25c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 16 | -0.17c | 8-8-0 | +0.70u | 13, -0.33c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 56 | 55 | -0.49c | 25-29-1 | -5.33u | 36, -0.58c, -5.91u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 12 | -0.58c | 6-6-0 | -2.35u | 8, -0.72c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 589 | 30 | 5.1% | -0.35c | 1.61c | 15-14-0 | +1.52u |  |
| MK novig fair-2c | 589 | 11 | 1.9% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1891 | 93 | 4.9% | -0.88c | 1.1c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 1874 | 25 | 1.3% | -0.69c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2480 | 123 | 5.0% | -0.75c | 1.22c | 60-60-2 | +2.31u | criteria not met (122/50 graded, CLV not positive) |
| MK all fair-2c | 2463 | 36 | 1.5% | -0.63c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 52.

## Odds API credits (100K/month plan)

Study: 640/day, projected 19187/30 days. All monitors on the key: 2159/day, projected 64760/30 days. Remaining 97272; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T04:50:35Z: 20 games (20 in 24h), quotes {'prophetx': 1570, 'novig': 724, 'kalshi': 1150, 'polymarket_us': 1676}, 0 unmatched (0 book-games; fuzzy-matched 0), 2424 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 1, new A 12 B 0, maker posted 0 filled 0, credits used 6 left 97272, 182s
- 2026-11-02T04:40:24Z: 20 games (20 in 24h), quotes {'prophetx': 1492, 'novig': 728, 'kalshi': 1088, 'polymarket_us': 1988}, 0 unmatched (0 book-games; fuzzy-matched 0), 2537 side/lines, polls [none_due], moves 0, new A 17 B 0, maker posted 0 filled 0, credits used 0 left 97287, 184s
- 2026-11-02T04:30:36Z: 18 games (18 in 24h), quotes {'prophetx': 1270, 'novig': 724, 'kalshi': 1096, 'polymarket_us': 1986}, 8 unmatched (1 book-games; fuzzy-matched 0), 2494 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 97298, 184s
- 2026-11-02T04:20:31Z: 18 games (18 in 24h), quotes {'prophetx': 1506, 'novig': 720, 'kalshi': 1100, 'polymarket_us': 2246}, 266 unmatched (3 book-games; fuzzy-matched 0), 2531 side/lines, polls [none_due], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 0 left 97325, 182s
- 2026-11-02T04:10:28Z: 18 games (18 in 24h), quotes {'prophetx': 1080, 'novig': 720, 'kalshi': 1134, 'polymarket_us': 1956}, 48 unmatched (2 book-games; fuzzy-matched 0), 2460 side/lines, polls [none_due], moves 0, new A 22 B 0, maker posted 0 filled 0, credits used 0 left 97336, 182s
- 2026-11-02T04:00:32Z: 18 games (18 in 24h), quotes {'prophetx': 1480, 'novig': 716, 'kalshi': 1140, 'polymarket_us': 1968}, 60 unmatched (2 book-games; fuzzy-matched 0), 2478 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 1, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 97345, 181s
- 2026-11-02T03:50:24Z: 18 games (18 in 24h), quotes {'prophetx': 1476, 'novig': 726, 'kalshi': 1172, 'polymarket_us': 1496}, 92 unmatched (3 book-games; fuzzy-matched 0), 2227 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 97362, 183s
- 2026-11-02T03:40:24Z: 18 games (18 in 24h), quotes {'prophetx': 1394, 'novig': 724, 'kalshi': 1194, 'polymarket_us': 1930}, 122 unmatched (4 book-games; fuzzy-matched 0), 2438 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 97373, 183s
- 2026-11-02T03:30:35Z: 18 games (18 in 24h), quotes {'prophetx': 1396, 'novig': 724, 'kalshi': 1170, 'polymarket_us': 2246}, 390 unmatched (6 book-games; fuzzy-matched 0), 2463 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 3, new A 4 B 0, maker posted 0 filled 0, credits used 6 left 97382, 183s
- 2026-11-02T03:20:31Z: 18 games (18 in 24h), quotes {'prophetx': 1236, 'novig': 724, 'kalshi': 1156, 'polymarket_us': 2244}, 406 unmatched (6 book-games; fuzzy-matched 0), 2436 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 97399, 183s
