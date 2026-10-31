# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T19:14:14Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2649 | 2312 | -2.44c | 23.4% | 902 | -1.34c | 1924 | 964-960-0 | -117.67u | -6.1% |  |  | criteria not met (1924/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 739 | 589 | -4.88c | 15.6% | 131 | -3.59c | 415 | 201-214-0 | -35.95u | -8.7% |  |  | criteria not met (415/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 46 | 41 | -0.73c | 36.6% | 39 | -0.01c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 30 | 28 | -0.53c | 32.1% | 27 | 0.13c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 13 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 110 | 84 | -0.71c | 34.5% | 83 | -0.76c | 72 | 41-31-0 | +7.93u | 11.0% | 0.17c | 25s | criteria not met (72/50 graded, CLV not positive) |
| M gettable, line moves | 59 | 46 | -0.72c | 37.0% | 45 | -0.95c | 41 | 23-18-0 | +3.09u | 7.5% | 0.03c | 28s |  |
| M gettable, price moves | 51 | 38 | -0.69c | 31.6% | 38 | -0.53c | 31 | 18-13-0 | +4.84u | 15.6% | 0.33c | 20s |  |
| M control: not gettable | 429 | 249 | -0.72c | 34.1% | 250 | -1.17c | 197 | 103-91-3 | -0.04u | -0.0% | 1.84c | 28s |  |
| M all moves | 539 | 333 | -0.72c | 34.2% | 333 | -1.07c | 269 | 144-122-3 | +7.90u | 2.9% | 1.49c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 451 | 318 | 1.35c | 23.3% | 66 | 1.88c | 172 | 76-96-0 | +88.99u | 51.7% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 7 | 0 | -0.6c | 0-0-0 | +0.00u | 0, -0.92c, +0.00u | not enough yet |
| J2 B, NBA | 4 | 0 | -1.49c | 0-0-0 | +0.00u | 0, -3.03c, +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 5 | 0 | -0.6c | 0-0-0 | +0.00u | 0, -0.92c, +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 19 | 0 | -0.24c | 0-0-0 | +0.00u | 0, -0.25c, +0.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 0 | 0.36c | 0-0-0 | +0.00u | 0, 0.36c, +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 0 | -1.47c | 0-0-0 | +0.00u | 0, -1.47c, +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 214 | 17 | 8.3% | -0.45c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 211 | 6 | 3.0% | -0.95c | 2.61c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1179 | 60 | 5.7% | -1.1c | 1.14c | 10-11-0 | -0.51u |  |
| MK prophetx fair-2c | 1170 | 16 | 1.5% | -0.75c | 2.06c | 1-5-0 | -3.95u |  |
| MK all fair-1c | 1393 | 77 | 6.1% | -0.94c | 1.27c | 18-17-0 | +1.73u | criteria not met (35/50 graded, CLV not positive) |
| MK all fair-2c | 1381 | 22 | 1.8% | -0.81c | 2.18c | 5-7-0 | -1.52u | criteria not met (12/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 34.

## Odds API credits (100K/month plan)

Study: 543/day, projected 16297/30 days. All monitors on the key: 2018/day, projected 60535/30 days. Remaining 63169; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T19:10:22Z: 59 games (51 in 24h), quotes {'prophetx': 5598, 'novig': 650, 'kalshi': 2352, 'polymarket_us': 1729}, 2225 unmatched (83 book-games; fuzzy-matched 2), 5640 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 26 B 2, maker posted 93 filled 3, credits used 8 left 63169, 231s
- 2026-10-31T19:00:22Z: 62 games (54 in 24h), quotes {'prophetx': 5454, 'novig': 660, 'kalshi': 2516, 'polymarket_us': 1561}, 1799 unmatched (80 book-games; fuzzy-matched 4), 5318 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 39 B 0, maker posted 27 filled 1, credits used 12 left 63188, 303s
- 2026-10-31T18:50:21Z: 63 games (55 in 24h), quotes {'prophetx': 5620, 'novig': 653, 'kalshi': 3746, 'polymarket_us': 3327}, 3759 unmatched (120 book-games; fuzzy-matched 4), 6431 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 49 B 0, maker posted 24 filled 1, credits used 6 left 63232, 273s
- 2026-10-31T18:45:59Z: 63 games (55 in 24h), quotes {'prophetx': 6270, 'novig': 655, 'kalshi': 2950, 'polymarket_us': 2196}, 3647 unmatched (117 book-games; fuzzy-matched 4), 6022 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 1, maker posted 42 filled 1, credits used 8 left 63244, 185s
- 2026-10-31T18:39:03Z: 63 games (55 in 24h), quotes {'prophetx': 3430, 'novig': 651, 'kalshi': 2704, 'polymarket_us': 1880}, 3401 unmatched (108 book-games; fuzzy-matched 8), 3145 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 9, new A 13 B 0, maker posted 47 filled 1, credits used 12 left 63265, 392s
- 2026-10-31T18:30:20Z: 63 games (55 in 24h), quotes {'prophetx': 3952, 'novig': 663, 'kalshi': 2602, 'polymarket_us': 1612}, 3476 unmatched (106 book-games; fuzzy-matched 67), 3455 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 10 B 0, maker posted 12 filled 1, credits used 6 left 63288, 264s
- 2026-10-31T18:20:23Z: 63 games (55 in 24h), quotes {'prophetx': 6264, 'novig': 661, 'kalshi': 2312, 'polymarket_us': 1560}, 3568 unmatched (110 book-games; fuzzy-matched 3), 5381 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 27 filled 1, credits used 14 left 63314, 328s
- 2026-10-31T18:10:21Z: 63 games (55 in 24h), quotes {'prophetx': 6264, 'novig': 662, 'kalshi': 3674, 'polymarket_us': 3379}, 4052 unmatched (121 book-games; fuzzy-matched 4), 6076 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 71 B 0, maker posted 36 filled 2, credits used 6 left 63343, 277s
- 2026-10-31T18:04:42Z: 65 games (57 in 24h), quotes {'prophetx': 5612, 'novig': 652, 'kalshi': 2416, 'polymarket_us': 2020}, 3746 unmatched (110 book-games; fuzzy-matched 2), 4464 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 22 B 1, maker posted 43 filled 0, credits used 6 left 63364, 296s
- 2026-10-31T18:00:22Z: 67 games (59 in 24h), quotes {'prophetx': 6252, 'novig': 657, 'kalshi': 2844, 'polymarket_us': 2106}, 3724 unmatched (109 book-games; fuzzy-matched 3), 6005 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 13 B 0, maker posted 76 filled 0, credits used 6 left 63382, 236s
