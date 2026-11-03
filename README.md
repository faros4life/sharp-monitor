# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T00:44:58Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4777 | 4405 | -1.97c | 22.4% | 1753 | -1.19c | 3959 | 1997-1962-0 | -194.11u | -4.9% |  |  | criteria not met (3959/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1243 | 1103 | -3.93c | 14.1% | 245 | -3.23c | 956 | 501-455-0 | -50.48u | -5.3% |  |  | criteria not met (956/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 75 | 67 | -0.68c | 32.8% | 64 | 0.1c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 47 | 42 | -0.58c | 31.0% | 40 | 0.08c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 23 | 20 | -1.2c | 35.0% | 19 | -0.27c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 176 | 171 | -0.64c | 33.3% | 168 | -0.59c | 154 | 78-75-1 | -3.15u | -2.0% | 0.14c | 25s | criteria not met (154/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 93 | 90 | -0.51c | 35.6% | 89 | -0.75c | 82 | 41-40-1 | -2.38u | -2.9% | -0.02c | 28s |  |
| M gettable, price moves | 83 | 81 | -0.78c | 30.9% | 79 | -0.41c | 72 | 37-35-0 | -0.77u | -1.1% | 0.32c | 22s |  |
| M control: not gettable | 719 | 521 | -0.82c | 34.5% | 514 | -1.24c | 482 | 253-221-8 | +4.51u | 0.9% | 1.82c | 28s |  |
| M all moves | 895 | 692 | -0.77c | 34.2% | 682 | -1.08c | 636 | 331-296-9 | +1.37u | 0.2% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 682 | 643 | 4.01c | 28.5% | 123 | 3.86c | 615 | 274-341-0 | +325.38u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 36 | 22 | 0.14c | 11-11-0 | +0.91u | 17, -0.18c, -0.36u | not enough yet |
| J2 B, NBA | 25 | 11 | 0.01c | 6-5-0 | +1.45u | 7, -0.54c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 24 | 16 | 0.0c | 8-8-0 | +0.70u | 13, -0.3c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 76 | 56 | -0.53c | 25-30-1 | -6.33u | 37, -0.6c, -6.91u | negative |
| D1 B, unders (descriptive) | 6 | 5 | 0.63c | 3-2-0 | +1.21u | 5, 0.63c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 6 | 2 | -1.49c | 0-2-0 | -2.00u | 2, -1.49c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 12 | -0.49c | 6-6-0 | -2.35u | 8, -0.66c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 705 | 37 | 5.4% | -0.32c | 1.62c | 15-15-0 | +0.52u |  |
| MK novig fair-2c | 706 | 16 | 2.3% | -0.4c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 2198 | 109 | 5.0% | -0.9c | 1.1c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 2180 | 34 | 1.6% | -0.62c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2903 | 146 | 5.1% | -0.75c | 1.23c | 60-61-2 | +1.31u | criteria not met (123/50 graded, CLV not positive) |
| MK all fair-2c | 2886 | 50 | 1.8% | -0.54c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 63.

## Odds API credits (100K/month plan)

Study: 634/day, projected 19020/30 days. All monitors on the key: 2149/day, projected 64480/30 days. Remaining 95546; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T00:40:39Z: 30 games (27 in 24h), quotes {'prophetx': 1488, 'novig': 722, 'kalshi': 1586, 'polymarket_us': 1438}, 98 unmatched (3 book-games; fuzzy-matched 0), 2981 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 4, new A 29 B 1, maker posted 55 filled 2, credits used 6 left 95546, 259s
- 2026-11-03T00:30:44Z: 30 games (26 in 24h), quotes {'prophetx': 1208, 'novig': 714, 'kalshi': 1590, 'polymarket_us': 1866}, 100 unmatched (3 book-games; fuzzy-matched 0), 3137 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast; NHL:fast], moves 0, new A 11 B 0, maker posted 6 filled 2, credits used 14 left 95565, 303s
- 2026-11-03T00:20:38Z: 30 games (26 in 24h), quotes {'prophetx': 1820, 'novig': 720, 'kalshi': 1612, 'polymarket_us': 1284}, 110 unmatched (3 book-games; fuzzy-matched 0), 3141 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 10, new A 3 B 1, maker posted 0 filled 4, credits used 6 left 95613, 274s
- 2026-11-03T00:13:00Z: 30 games (26 in 24h), quotes {'prophetx': 2048, 'novig': 724, 'kalshi': 1612, 'polymarket_us': 2490}, 108 unmatched (3 book-games; fuzzy-matched 0), 3821 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 13 B 1, maker posted 31 filled 6, credits used 6 left 95632, 184s
- 2026-11-03T00:06:26Z: 33 games (21 in 24h), quotes {'prophetx': 2024, 'novig': 724, 'kalshi': 1612, 'polymarket_us': 2002}, 0 unmatched (0 book-games; fuzzy-matched 0), 3736 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 7, new A 6 B 0, maker posted 0 filled 0, credits used 6 left 95639, 351s
- 2026-11-03T00:00:43Z: 33 games (21 in 24h), quotes {'prophetx': 1914, 'novig': 720, 'kalshi': 1612, 'polymarket_us': 2490}, 0 unmatched (0 book-games; fuzzy-matched 0), 3923 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast; NHL:fast], moves 0, new A 14 B 0, maker posted 13 filled 2, credits used 14 left 95656, 303s
- 2026-11-02T23:50:34Z: 33 games (20 in 24h), quotes {'prophetx': 1862, 'novig': 712, 'kalshi': 1614, 'polymarket_us': 1902}, 0 unmatched (0 book-games; fuzzy-matched 0), 3774 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 3 B 0, maker posted 48 filled 3, credits used 12 left 95713, 359s
- 2026-11-02T23:40:41Z: 33 games (20 in 24h), quotes {'prophetx': 1766, 'novig': 720, 'kalshi': 1616, 'polymarket_us': 1420}, 0 unmatched (0 book-games; fuzzy-matched 0), 3460 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 2 B 2, maker posted 28 filled 1, credits used 6 left 95738, 235s
- 2026-11-02T23:30:49Z: 33 games (20 in 24h), quotes {'prophetx': 1730, 'novig': 720, 'kalshi': 1608, 'polymarket_us': 2274}, 0 unmatched (0 book-games; fuzzy-matched 0), 3907 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 25 filled 0, credits used 14 left 95759, 303s
- 2026-11-02T23:20:40Z: 33 games (20 in 24h), quotes {'prophetx': 1626, 'novig': 716, 'kalshi': 1610, 'polymarket_us': 1926}, 0 unmatched (0 book-games; fuzzy-matched 0), 3680 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 6 B 1, maker posted 24 filled 0, credits used 12 left 95823, 391s
