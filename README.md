# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T19:25:39Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4638 | 3959 | -1.92c | 21.6% | 1602 | -1.15c | 3959 | 1997-1962-0 | -194.11u | -4.9% |  |  | criteria not met (3959/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1201 | 956 | -3.85c | 14.0% | 216 | -3.11c | 956 | 501-455-0 | -50.48u | -5.3% |  |  | criteria not met (956/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 66 | 61 | -0.66c | 32.8% | 59 | 0.13c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 42 | 39 | -0.62c | 30.8% | 38 | 0.01c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 19 | 17 | -1.11c | 35.3% | 16 | -0.09c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 169 | 154 | -0.57c | 32.5% | 152 | -0.59c | 154 | 78-75-1 | -3.15u | -2.0% | 0.29c | 25s | criteria not met (154/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 91 | 82 | -0.58c | 35.4% | 81 | -0.81c | 82 | 41-40-1 | -2.38u | -2.9% | 0.01c | 44s |  |
| M gettable, price moves | 78 | 72 | -0.56c | 29.2% | 71 | -0.34c | 72 | 37-35-0 | -0.77u | -1.1% | 0.61c | 21s |  |
| M control: not gettable | 663 | 470 | -0.87c | 34.0% | 466 | -1.22c | 482 | 253-221-8 | +4.51u | 0.9% | 1.76c | 28s |  |
| M all moves | 832 | 624 | -0.79c | 33.7% | 618 | -1.07c | 636 | 331-296-9 | +1.37u | 0.2% | 1.45c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 674 | 614 | 4.4c | 29.2% | 122 | 3.88c | 615 | 274-341-0 | +325.38u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 27 | 22 | 0.2c | 11-11-0 | +0.91u | 17, 0.0c, -0.36u | not enough yet |
| J2 B, NBA | 16 | 11 | 0.09c | 6-5-0 | +1.45u | 7, -0.25c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 19 | 16 | -0.17c | 8-8-0 | +0.70u | 13, -0.33c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 69 | 56 | -0.49c | 25-30-1 | -6.33u | 37, -0.58c, -6.91u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 3 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 12 | -0.58c | 6-6-0 | -2.35u | 8, -0.72c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 609 | 30 | 5.1% | -0.35c | 1.61c | 15-15-0 | +0.52u |  |
| MK novig fair-2c | 609 | 11 | 1.9% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1941 | 93 | 4.9% | -0.88c | 1.1c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 1924 | 25 | 1.3% | -0.69c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2550 | 123 | 4.9% | -0.75c | 1.22c | 60-61-2 | +1.31u | criteria not met (123/50 graded, CLV not positive) |
| MK all fair-2c | 2533 | 36 | 1.5% | -0.63c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 56.

## Odds API credits (100K/month plan)

Study: 600/day, projected 17991/30 days. All monitors on the key: 2088/day, projected 62652/30 days. Remaining 96388; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T19:20:38Z: 33 games (20 in 24h), quotes {'prophetx': 1882, 'novig': 718, 'kalshi': 1622, 'polymarket_us': 2266}, 0 unmatched (0 book-games; fuzzy-matched 0), 3795 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 6, new A 3 B 0, maker posted 24 filled 0, credits used 12 left 96388, 301s
- 2026-11-02T19:10:50Z: 33 games (20 in 24h), quotes {'prophetx': 1850, 'novig': 718, 'kalshi': 1618, 'polymarket_us': 1386}, 0 unmatched (0 book-games; fuzzy-matched 0), 3324 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 44 filled 0, credits used 4 left 96422, 183s
- 2026-11-02T19:00:51Z: 33 games (20 in 24h), quotes {'prophetx': 1726, 'novig': 720, 'kalshi': 1616, 'polymarket_us': 1622}, 0 unmatched (0 book-games; fuzzy-matched 0), 3391 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 7, new A 14 B 3, maker posted 0 filled 0, credits used 12 left 96439, 395s
- 2026-11-02T18:50:36Z: 33 games (20 in 24h), quotes {'prophetx': 1746, 'novig': 720, 'kalshi': 1616, 'polymarket_us': 2262}, 0 unmatched (0 book-games; fuzzy-matched 0), 3711 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 4, new A 6 B 0, maker posted 0 filled 0, credits used 8 left 96460, 301s
- 2026-11-02T18:40:27Z: 33 games (20 in 24h), quotes {'prophetx': 1722, 'novig': 720, 'kalshi': 1618, 'polymarket_us': 1678}, 0 unmatched (0 book-games; fuzzy-matched 0), 3381 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 52 filled 0, credits used 4 left 96487, 182s
- 2026-11-02T18:30:43Z: 33 games (20 in 24h), quotes {'prophetx': 1770, 'novig': 716, 'kalshi': 1620, 'polymarket_us': 2262}, 0 unmatched (0 book-games; fuzzy-matched 0), 3717 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 0 filled 0, credits used 12 left 96500, 353s
- 2026-11-02T18:20:28Z: 33 games (20 in 24h), quotes {'prophetx': 1522, 'novig': 726, 'kalshi': 1618, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 0), 3436 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 4, new A 12 B 0, maker posted 0 filled 0, credits used 4 left 96530, 259s
- 2026-11-02T18:10:37Z: 33 games (20 in 24h), quotes {'prophetx': 1766, 'novig': 724, 'kalshi': 1618, 'polymarket_us': 2258}, 0 unmatched (0 book-games; fuzzy-matched 0), 3718 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 6 B 0, maker posted 20 filled 0, credits used 12 left 96536, 301s
- 2026-11-02T18:00:35Z: 33 games (20 in 24h), quotes {'prophetx': 1798, 'novig': 726, 'kalshi': 1618, 'polymarket_us': 1358}, 0 unmatched (0 book-games; fuzzy-matched 0), 3318 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 96570, 184s
- 2026-11-02T17:50:33Z: 33 games (20 in 24h), quotes {'prophetx': 1658, 'novig': 720, 'kalshi': 1620, 'polymarket_us': 1880}, 0 unmatched (0 book-games; fuzzy-matched 0), 3550 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 1, new A 0 B 0, maker posted 0 filled 0, credits used 8 left 96579, 183s
