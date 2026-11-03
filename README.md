# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T00:16:03Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4736 | 4043 | -1.93c | 21.6% | 1640 | -1.16c | 3959 | 1997-1962-0 | -194.11u | -4.9% |  |  | criteria not met (3959/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1237 | 987 | -3.85c | 13.7% | 224 | -3.2c | 956 | 501-455-0 | -50.48u | -5.3% |  |  | criteria not met (956/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 73 | 62 | -0.63c | 33.9% | 60 | 0.14c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 47 | 39 | -0.62c | 30.8% | 38 | 0.01c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 21 | 18 | -0.99c | 38.9% | 17 | -0.05c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 176 | 157 | -0.55c | 33.1% | 155 | -0.57c | 154 | 78-75-1 | -3.15u | -2.0% | 0.3c | 25s | criteria not met (154/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 93 | 83 | -0.55c | 36.1% | 82 | -0.78c | 82 | 41-40-1 | -2.38u | -2.9% | 0.04c | 28s |  |
| M gettable, price moves | 83 | 74 | -0.54c | 29.7% | 73 | -0.33c | 72 | 37-35-0 | -0.77u | -1.1% | 0.6c | 22s |  |
| M control: not gettable | 705 | 479 | -0.88c | 33.4% | 476 | -1.22c | 482 | 253-221-8 | +4.51u | 0.9% | 1.74c | 28s |  |
| M all moves | 881 | 636 | -0.8c | 33.3% | 631 | -1.06c | 636 | 331-296-9 | +1.37u | 0.2% | 1.44c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 680 | 616 | 4.38c | 29.1% | 122 | 3.88c | 615 | 274-341-0 | +325.38u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 34 | 22 | 0.23c | 11-11-0 | +0.91u | 17, 0.04c, -0.36u | not enough yet |
| J2 B, NBA | 23 | 11 | 0.14c | 6-5-0 | +1.45u | 7, -0.13c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 24 | 16 | -0.17c | 8-8-0 | +0.70u | 13, -0.33c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 76 | 56 | -0.46c | 25-30-1 | -6.33u | 37, -0.53c, -6.91u | negative |
| D1 B, unders (descriptive) | 6 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 4 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 12 | -0.49c | 6-6-0 | -2.35u | 8, -0.66c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 682 | 36 | 5.4% | -0.33c | 1.61c | 15-15-0 | +0.52u |  |
| MK novig fair-2c | 683 | 14 | 2.1% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 2191 | 106 | 5.0% | -0.91c | 1.1c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 2172 | 32 | 1.5% | -0.69c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2873 | 142 | 5.1% | -0.77c | 1.22c | 60-61-2 | +1.31u | criteria not met (123/50 graded, CLV not positive) |
| MK all fair-2c | 2855 | 46 | 1.7% | -0.63c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 61.

## Odds API credits (100K/month plan)

Study: 632/day, projected 18953/30 days. All monitors on the key: 2142/day, projected 64263/30 days. Remaining 95632; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T00:13:00Z: 30 games (26 in 24h), quotes {'prophetx': 2048, 'novig': 724, 'kalshi': 1612, 'polymarket_us': 2490}, 108 unmatched (3 book-games; fuzzy-matched 0), 3821 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 13 B 1, maker posted 31 filled 6, credits used 6 left 95632, 184s
- 2026-11-03T00:06:26Z: 33 games (21 in 24h), quotes {'prophetx': 2024, 'novig': 724, 'kalshi': 1612, 'polymarket_us': 2002}, 0 unmatched (0 book-games; fuzzy-matched 0), 3736 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 7, new A 6 B 0, maker posted 0 filled 0, credits used 6 left 95639, 351s
- 2026-11-03T00:00:43Z: 33 games (21 in 24h), quotes {'prophetx': 1914, 'novig': 720, 'kalshi': 1612, 'polymarket_us': 2490}, 0 unmatched (0 book-games; fuzzy-matched 0), 3923 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast; NHL:fast], moves 0, new A 14 B 0, maker posted 13 filled 2, credits used 14 left 95656, 303s
- 2026-11-02T23:50:34Z: 33 games (20 in 24h), quotes {'prophetx': 1862, 'novig': 712, 'kalshi': 1614, 'polymarket_us': 1902}, 0 unmatched (0 book-games; fuzzy-matched 0), 3774 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 3 B 0, maker posted 48 filled 3, credits used 12 left 95713, 359s
- 2026-11-02T23:40:41Z: 33 games (20 in 24h), quotes {'prophetx': 1766, 'novig': 720, 'kalshi': 1616, 'polymarket_us': 1420}, 0 unmatched (0 book-games; fuzzy-matched 0), 3460 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 2 B 2, maker posted 28 filled 1, credits used 6 left 95738, 235s
- 2026-11-02T23:30:49Z: 33 games (20 in 24h), quotes {'prophetx': 1730, 'novig': 720, 'kalshi': 1608, 'polymarket_us': 2274}, 0 unmatched (0 book-games; fuzzy-matched 0), 3907 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 25 filled 0, credits used 14 left 95759, 303s
- 2026-11-02T23:20:40Z: 33 games (20 in 24h), quotes {'prophetx': 1626, 'novig': 716, 'kalshi': 1610, 'polymarket_us': 1926}, 0 unmatched (0 book-games; fuzzy-matched 0), 3680 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 6 B 1, maker posted 24 filled 0, credits used 12 left 95823, 391s
- 2026-11-02T23:10:40Z: 33 games (20 in 24h), quotes {'prophetx': 1642, 'novig': 722, 'kalshi': 1610, 'polymarket_us': 2274}, 0 unmatched (0 book-games; fuzzy-matched 0), 3871 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 95856, 184s
- 2026-11-02T23:00:47Z: 33 games (20 in 24h), quotes {'prophetx': 1758, 'novig': 722, 'kalshi': 1610, 'polymarket_us': 2274}, 0 unmatched (0 book-games; fuzzy-matched 0), 3928 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 1 B 2, maker posted 3 filled 7, credits used 14 left 95873, 392s
- 2026-11-02T22:50:36Z: 33 games (20 in 24h), quotes {'prophetx': 1854, 'novig': 716, 'kalshi': 1620, 'polymarket_us': 2274}, 0 unmatched (0 book-games; fuzzy-matched 0), 3972 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 17 filled 0, credits used 12 left 95902, 329s
