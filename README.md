# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T19:34:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2763 | 2580 | -2.4c | 21.6% | 994 | -1.37c | 2048 | 1029-1019-0 | -123.68u | -6.0% |  |  | criteria not met (2048/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 778 | 708 | -4.51c | 13.6% | 164 | -3.34c | 475 | 236-239-0 | -30.84u | -6.5% |  |  | criteria not met (475/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 46 | 43 | -0.79c | 34.9% | 41 | 0.01c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 30 | 28 | -0.53c | 32.1% | 27 | 0.13c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 13 | 12 | -1.87c | 33.3% | 11 | -0.81c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 112 | 95 | -0.6c | 33.7% | 94 | -0.76c | 75 | 42-33-0 | +6.85u | 9.1% | 0.14c | 26s | criteria not met (75/50 graded, CLV not positive) |
| M gettable, line moves | 61 | 53 | -0.52c | 35.8% | 52 | -0.9c | 43 | 24-19-0 | +3.01u | 7.0% | 0.02c | 28s |  |
| M gettable, price moves | 51 | 42 | -0.71c | 31.0% | 42 | -0.58c | 32 | 18-14-0 | +3.84u | 12.0% | 0.28c | 20s |  |
| M control: not gettable | 440 | 284 | -0.77c | 34.5% | 284 | -1.25c | 209 | 112-94-3 | +4.76u | 2.3% | 1.84c | 28s |  |
| M all moves | 552 | 379 | -0.73c | 34.3% | 378 | -1.12c | 284 | 154-127-3 | +11.61u | 4.1% | 1.48c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 509 | 424 | 2.44c | 26.4% | 87 | 1.78c | 222 | 96-126-0 | +96.44u | 43.4% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 7 | 0 | -0.24c | 0-0-0 | +0.00u | 0, -0.31c, +0.00u | not enough yet |
| J2 B, NBA | 4 | 0 | -1.49c | 0-0-0 | +0.00u | 0, -3.03c, +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 5 | 0 | -0.26c | 0-0-0 | +0.00u | 0, -0.36c, +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 21 | 1 | -0.75c | 0-1-0 | -1.00u | 1, -1.16c, -1.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 | 0.76c | 0-0-0 | +0.00u | 0, 0.76c, +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 0 | 0.36c | 0-0-0 | +0.00u | 0, 0.36c, +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 0 | -1.47c | 0-0-0 | +0.00u | 0, -1.47c, +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 230 | 17 | 7.8% | -0.5c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 227 | 7 | 3.3% | -0.86c | 2.62c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1217 | 62 | 5.5% | -0.88c | 1.11c | 11-11-0 | +0.55u |  |
| MK prophetx fair-2c | 1206 | 16 | 1.4% | -0.64c | 2.05c | 1-5-0 | -3.95u |  |
| MK all fair-1c | 1447 | 79 | 5.9% | -0.79c | 1.22c | 19-17-0 | +2.79u | criteria not met (36/50 graded, CLV not positive) |
| MK all fair-2c | 1433 | 23 | 1.7% | -0.71c | 2.15c | 5-7-0 | -1.52u | criteria not met (12/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 35.

## Odds API credits (100K/month plan)

Study: 548/day, projected 16435/30 days. All monitors on the key: 2024/day, projected 60730/30 days. Remaining 63115; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T19:30:25Z: 57 games (49 in 24h), quotes {'prophetx': 4340, 'novig': 565, 'kalshi': 3666, 'polymarket_us': 3318}, 2749 unmatched (86 book-games; fuzzy-matched 2), 5966 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 68 B 0, maker posted 25 filled 1, credits used 8 left 63115, 248s
- 2026-10-31T19:24:00Z: 58 games (50 in 24h), quotes {'prophetx': 5476, 'novig': 656, 'kalshi': 2408, 'polymarket_us': 1751}, 1767 unmatched (74 book-games; fuzzy-matched 2), 5712 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 6 left 63136, 282s
- 2026-10-31T19:18:41Z: 58 games (50 in 24h), quotes {'prophetx': 5466, 'novig': 662, 'kalshi': 3548, 'polymarket_us': 3273}, 2503 unmatched (85 book-games; fuzzy-matched 4), 6358 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 98 B 0, maker posted 57 filled 2, credits used 12 left 63143, 301s
- 2026-10-31T19:10:22Z: 59 games (51 in 24h), quotes {'prophetx': 5598, 'novig': 650, 'kalshi': 2352, 'polymarket_us': 1729}, 2225 unmatched (83 book-games; fuzzy-matched 2), 5640 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 26 B 2, maker posted 93 filled 3, credits used 8 left 63169, 231s
- 2026-10-31T19:00:22Z: 62 games (54 in 24h), quotes {'prophetx': 5454, 'novig': 660, 'kalshi': 2516, 'polymarket_us': 1561}, 1799 unmatched (80 book-games; fuzzy-matched 4), 5318 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 39 B 0, maker posted 27 filled 1, credits used 12 left 63188, 303s
- 2026-10-31T18:50:21Z: 63 games (55 in 24h), quotes {'prophetx': 5620, 'novig': 653, 'kalshi': 3746, 'polymarket_us': 3327}, 3759 unmatched (120 book-games; fuzzy-matched 4), 6431 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 49 B 0, maker posted 24 filled 1, credits used 6 left 63232, 273s
- 2026-10-31T18:45:59Z: 63 games (55 in 24h), quotes {'prophetx': 6270, 'novig': 655, 'kalshi': 2950, 'polymarket_us': 2196}, 3647 unmatched (117 book-games; fuzzy-matched 4), 6022 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 1, maker posted 42 filled 1, credits used 8 left 63244, 185s
- 2026-10-31T18:39:03Z: 63 games (55 in 24h), quotes {'prophetx': 3430, 'novig': 651, 'kalshi': 2704, 'polymarket_us': 1880}, 3401 unmatched (108 book-games; fuzzy-matched 8), 3145 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 9, new A 13 B 0, maker posted 47 filled 1, credits used 12 left 63265, 392s
- 2026-10-31T18:30:20Z: 63 games (55 in 24h), quotes {'prophetx': 3952, 'novig': 663, 'kalshi': 2602, 'polymarket_us': 1612}, 3476 unmatched (106 book-games; fuzzy-matched 67), 3455 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 10 B 0, maker posted 12 filled 1, credits used 6 left 63288, 264s
- 2026-10-31T18:20:23Z: 63 games (55 in 24h), quotes {'prophetx': 6264, 'novig': 661, 'kalshi': 2312, 'polymarket_us': 1560}, 3568 unmatched (110 book-games; fuzzy-matched 3), 5381 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 27 filled 1, credits used 14 left 63314, 328s
