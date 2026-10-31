# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T20:16:13Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2829 | 2719 | -2.36c | 21.0% | 1048 | -1.37c | 2194 | 1105-1089-0 | -125.91u | -5.7% |  |  | criteria not met (2194/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 799 | 767 | -4.34c | 13.7% | 177 | -3.28c | 538 | 271-267-0 | -35.53u | -6.6% |  |  | criteria not met (538/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 46 | 43 | -0.79c | 34.9% | 41 | 0.01c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 30 | 28 | -0.53c | 32.1% | 27 | 0.13c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 13 | 12 | -1.87c | 33.3% | 11 | -0.81c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 115 | 101 | -0.65c | 32.7% | 100 | -0.77c | 80 | 45-35-0 | +7.19u | 9.0% | 0.15c | 25s | criteria not met (80/50 graded, CLV not positive) |
| M gettable, line moves | 62 | 56 | -0.56c | 35.7% | 55 | -0.91c | 44 | 24-20-0 | +2.01u | 4.6% | 0.04c | 28s |  |
| M gettable, price moves | 53 | 45 | -0.77c | 28.9% | 45 | -0.59c | 36 | 21-15-0 | +5.18u | 14.4% | 0.28c | 20s |  |
| M control: not gettable | 446 | 301 | -0.8c | 33.6% | 301 | -1.26c | 233 | 126-104-3 | +6.78u | 2.9% | 1.82c | 28s |  |
| M all moves | 561 | 402 | -0.76c | 33.3% | 401 | -1.14c | 313 | 171-139-3 | +13.97u | 4.5% | 1.46c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 524 | 486 | 2.95c | 28.0% | 103 | 2.65c | 264 | 114-150-0 | +112.25u | 42.5% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 7 | 0 | -0.24c | 0-0-0 | +0.00u | 0, -0.31c, +0.00u | not enough yet |
| J2 B, NBA | 4 | 0 | -1.49c | 0-0-0 | +0.00u | 0, -3.03c, +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 5 | 0 | -0.26c | 0-0-0 | +0.00u | 0, -0.36c, +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 24 | 2 | -0.84c | 0-2-0 | -2.00u | 2, -1.15c, -2.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 | 0.76c | 0-0-0 | +0.00u | 0, 0.76c, +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 0 | 0.36c | 0-0-0 | +0.00u | 0, 0.36c, +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 2 | -1.47c | 1-1-0 | -0.60u | 2, -1.47c, -0.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 247 | 17 | 7.3% | -0.5c | 1.68c | 9-7-0 | +2.10u |  |
| MK novig fair-2c | 244 | 7 | 3.1% | -0.86c | 2.6c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1277 | 64 | 5.4% | -0.81c | 1.1c | 15-18-0 | -2.23u |  |
| MK prophetx fair-2c | 1264 | 16 | 1.4% | -0.64c | 2.04c | 2-7-0 | -4.86u |  |
| MK all fair-1c | 1524 | 81 | 5.7% | -0.75c | 1.2c | 24-25-0 | -0.13u | criteria not met (49/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1508 | 23 | 1.6% | -0.71c | 2.14c | 6-9-0 | -2.44u | criteria not met (15/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 35.

## Odds API credits (100K/month plan)

Study: 556/day, projected 16692/30 days. All monitors on the key: 2041/day, projected 61224/30 days. Remaining 62991; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T20:11:35Z: 44 games (36 in 24h), quotes {'prophetx': 3742, 'novig': 649, 'kalshi': 2250, 'polymarket_us': 1468}, 2333 unmatched (67 book-games; fuzzy-matched 1), 3970 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 24 filled 0, credits used 6 left 62991, 277s
- 2026-10-31T20:07:44Z: 46 games (38 in 24h), quotes {'prophetx': 3622, 'novig': 641, 'kalshi': 2964, 'polymarket_us': 2076}, 2373 unmatched (65 book-games; fuzzy-matched 1), 4452 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 16 B 0, maker posted 1 filled 1, credits used 6 left 63008, 205s
- 2026-10-31T20:01:15Z: 47 games (39 in 24h), quotes {'prophetx': 3732, 'novig': 637, 'kalshi': 2328, 'polymarket_us': 1572}, 2290 unmatched (64 book-games; fuzzy-matched 1), 4097 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 38 filled 0, credits used 6 left 63027, 248s
- 2026-10-31T19:56:06Z: 47 games (39 in 24h), quotes {'prophetx': 4088, 'novig': 574, 'kalshi': 2750, 'polymarket_us': 2144}, 3155 unmatched (84 book-games; fuzzy-matched 1), 4290 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 11 B 0, maker posted 8 filled 0, credits used 8 left 63033, 284s
- 2026-10-31T19:50:21Z: 47 games (39 in 24h), quotes {'prophetx': 3970, 'novig': 569, 'kalshi': 2522, 'polymarket_us': 1902}, 2973 unmatched (85 book-games; fuzzy-matched 1), 4066 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 19 B 0, maker posted 53 filled 0, credits used 12 left 63052, 326s
- 2026-10-31T19:40:21Z: 50 games (42 in 24h), quotes {'prophetx': 4336, 'novig': 568, 'kalshi': 3700, 'polymarket_us': 3332}, 3127 unmatched (89 book-games; fuzzy-matched 2), 5550 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 15 B 0, maker posted 28 filled 1, credits used 12 left 63076, 377s
- 2026-10-31T19:30:25Z: 57 games (49 in 24h), quotes {'prophetx': 4340, 'novig': 565, 'kalshi': 3666, 'polymarket_us': 3318}, 2749 unmatched (86 book-games; fuzzy-matched 2), 5966 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 68 B 0, maker posted 25 filled 1, credits used 8 left 63115, 248s
- 2026-10-31T19:24:00Z: 58 games (50 in 24h), quotes {'prophetx': 5476, 'novig': 656, 'kalshi': 2408, 'polymarket_us': 1751}, 1767 unmatched (74 book-games; fuzzy-matched 2), 5712 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 6 left 63136, 282s
- 2026-10-31T19:18:41Z: 58 games (50 in 24h), quotes {'prophetx': 5466, 'novig': 662, 'kalshi': 3548, 'polymarket_us': 3273}, 2503 unmatched (85 book-games; fuzzy-matched 4), 6358 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 98 B 0, maker posted 57 filled 2, credits used 12 left 63143, 301s
- 2026-10-31T19:10:22Z: 59 games (51 in 24h), quotes {'prophetx': 5598, 'novig': 650, 'kalshi': 2352, 'polymarket_us': 1729}, 2225 unmatched (83 book-games; fuzzy-matched 2), 5640 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 26 B 2, maker posted 93 filled 3, credits used 8 left 63169, 231s
