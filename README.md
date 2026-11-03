# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T01:53:43Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4885 | 4692 | -1.97c | 22.7% | 1876 | -1.22c | 3959 | 1997-1962-0 | -194.11u | -4.9% |  |  | criteria not met (3959/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1258 | 1191 | -3.81c | 15.0% | 271 | -3.09c | 956 | 501-455-0 | -50.48u | -5.3% |  |  | criteria not met (956/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 76 | 75 | -0.82c | 32.0% | 71 | 0.02c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 47 | 46 | -0.67c | 30.4% | 44 | -0.02c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 24 | 24 | -1.41c | 33.3% | 22 | -0.3c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 176 | 176 | -0.72c | 33.0% | 173 | -0.68c | 154 | 78-75-1 | -3.15u | -2.0% | 0.07c | 25s | criteria not met (154/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 93 | 93 | -0.58c | 35.5% | 92 | -0.84c | 82 | 41-40-1 | -2.38u | -2.9% | -0.1c | 28s |  |
| M gettable, price moves | 83 | 83 | -0.87c | 30.1% | 81 | -0.49c | 72 | 37-35-0 | -0.77u | -1.1% | 0.25c | 22s |  |
| M control: not gettable | 726 | 571 | -0.85c | 34.7% | 561 | -1.27c | 482 | 253-221-8 | +4.51u | 0.9% | 1.85c | 28s |  |
| M all moves | 902 | 747 | -0.82c | 34.3% | 734 | -1.13c | 636 | 331-296-9 | +1.37u | 0.2% | 1.49c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 684 | 668 | 3.71c | 28.3% | 128 | 3.72c | 615 | 274-341-0 | +325.38u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 37 | 22 | -0.05c | 11-11-0 | +0.91u | 17, -0.35c, -0.36u | not enough yet |
| J2 B, NBA | 26 | 11 | -0.23c | 6-5-0 | +1.45u | 7, -0.75c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 24 | 16 | -0.18c | 8-8-0 | +0.70u | 13, -0.53c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 76 | 56 | -0.73c | 25-30-1 | -6.33u | 37, -0.91c, -6.91u | negative |
| D1 B, unders (descriptive) | 6 | 5 | 0.63c | 3-2-0 | +1.21u | 5, 0.63c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 6 | 2 | -1.17c | 0-2-0 | -2.00u | 2, -1.62c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 12 | -0.49c | 6-6-0 | -2.35u | 8, -0.66c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 725 | 38 | 5.4% | -0.34c | 1.62c | 15-15-0 | +0.52u |  |
| MK novig fair-2c | 726 | 17 | 2.4% | -0.38c | 2.55c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 2221 | 111 | 5.0% | -0.91c | 1.11c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 2205 | 35 | 1.6% | -0.6c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2946 | 149 | 5.1% | -0.77c | 1.23c | 60-61-2 | +1.31u | criteria not met (123/50 graded, CLV not positive) |
| MK all fair-2c | 2931 | 52 | 1.8% | -0.53c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 64.

## Odds API credits (100K/month plan)

Study: 639/day, projected 19160/30 days. All monitors on the key: 2157/day, projected 64707/30 days. Remaining 95394; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T01:50:42Z: 18 games (17 in 24h), quotes {'prophetx': 920, 'novig': 722, 'kalshi': 1402, 'polymarket_us': 1174}, 748 unmatched (15 book-games; fuzzy-matched 0), 1711 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 22 filled 0, credits used 4 left 95394, 181s
- 2026-11-03T01:40:46Z: 19 games (18 in 24h), quotes {'prophetx': 920, 'novig': 716, 'kalshi': 1426, 'polymarket_us': 1174}, 696 unmatched (14 book-games; fuzzy-matched 0), 1799 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 26 B 0, maker posted 0 filled 0, credits used 10 left 95407, 302s
- 2026-11-03T01:30:40Z: 20 games (19 in 24h), quotes {'prophetx': 920, 'novig': 722, 'kalshi': 1466, 'polymarket_us': 1174}, 662 unmatched (13 book-games; fuzzy-matched 0), 1917 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 18 B 0, maker posted 3 filled 0, credits used 8 left 95426, 301s
- 2026-11-03T01:20:37Z: 20 games (19 in 24h), quotes {'prophetx': 1052, 'novig': 722, 'kalshi': 1504, 'polymarket_us': 1438}, 698 unmatched (13 book-games; fuzzy-matched 0), 2126 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 2, new A 15 B 1, maker posted 5 filled 4, credits used 6 left 95462, 232s
- 2026-11-03T01:10:41Z: 23 games (22 in 24h), quotes {'prophetx': 1236, 'novig': 724, 'kalshi': 1538, 'polymarket_us': 1646}, 510 unmatched (10 book-games; fuzzy-matched 0), 2429 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 17 B 0, maker posted 23 filled 0, credits used 12 left 95468, 301s
- 2026-11-03T01:00:31Z: 25 games (23 in 24h), quotes {'prophetx': 1112, 'novig': 720, 'kalshi': 1556, 'polymarket_us': 1646}, 438 unmatched (8 book-games; fuzzy-matched 0), 2542 side/lines, polls [NCAAF:slow; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 0 filled 0, credits used 8 left 95505, 184s
- 2026-11-03T00:50:37Z: 25 games (22 in 24h), quotes {'prophetx': 1488, 'novig': 716, 'kalshi': 1574, 'polymarket_us': 1866}, 456 unmatched (8 book-games; fuzzy-matched 0), 2784 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 14 B 0, maker posted 35 filled 1, credits used 12 left 95517, 355s
- 2026-11-03T00:40:39Z: 30 games (27 in 24h), quotes {'prophetx': 1488, 'novig': 722, 'kalshi': 1586, 'polymarket_us': 1438}, 98 unmatched (3 book-games; fuzzy-matched 0), 2981 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 4, new A 29 B 1, maker posted 55 filled 2, credits used 6 left 95546, 259s
- 2026-11-03T00:30:44Z: 30 games (26 in 24h), quotes {'prophetx': 1208, 'novig': 714, 'kalshi': 1590, 'polymarket_us': 1866}, 100 unmatched (3 book-games; fuzzy-matched 0), 3137 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast; NHL:fast], moves 0, new A 11 B 0, maker posted 6 filled 2, credits used 14 left 95565, 303s
- 2026-11-03T00:20:38Z: 30 games (26 in 24h), quotes {'prophetx': 1820, 'novig': 720, 'kalshi': 1612, 'polymarket_us': 1284}, 110 unmatched (3 book-games; fuzzy-matched 0), 3141 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 10, new A 3 B 1, maker posted 0 filled 4, credits used 6 left 95613, 274s
