# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T22:30:29Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3037 | 2784 | -2.33c | 21.2% | 1071 | -1.36c | 2312 | 1168-1144-0 | -125.21u | -5.4% |  |  | criteria not met (2312/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 828 | 783 | -4.28c | 13.8% | 180 | -3.27c | 589 | 302-287-0 | -30.88u | -5.2% |  |  | criteria not met (589/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 48 | 44 | -0.83c | 34.1% | 42 | -0.04c | 41 | 18-23-0 | -1.92u | -4.7% |  |  | criteria not met (41/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 31 | 29 | -0.6c | 31.0% | 28 | 0.06c | 28 | 13-15-0 | +0.60u | 2.2% |  |  |  |
| B ref age 5m+ | 14 | 12 | -1.87c | 33.3% | 11 | -0.81c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 123 | 104 | -0.65c | 32.7% | 103 | -0.79c | 84 | 47-37-0 | +7.05u | 8.4% | 0.13c | 23s | criteria not met (84/50 graded, CLV not positive) |
| M gettable, line moves | 66 | 59 | -0.56c | 35.6% | 58 | -0.94c | 46 | 25-21-0 | +1.93u | 4.2% | 0.01c | 27s |  |
| M gettable, price moves | 57 | 45 | -0.77c | 28.9% | 45 | -0.59c | 38 | 22-16-0 | +5.12u | 13.5% | 0.28c | 20s |  |
| M control: not gettable | 471 | 313 | -0.75c | 34.5% | 312 | -1.24c | 259 | 141-115-3 | +10.25u | 4.0% | 1.84c | 26s |  |
| M all moves | 594 | 417 | -0.73c | 34.1% | 415 | -1.13c | 343 | 188-152-3 | +17.30u | 5.0% | 1.48c | 26s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 551 | 494 | 2.99c | 27.9% | 103 | 2.65c | 319 | 143-176-0 | +139.22u | 43.6% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 9 | 3 | -0.54c | 1-2-0 | -0.90u | 2, -0.65c, +0.10u | not enough yet |
| J2 B, NBA | 5 | 2 | -1.67c | 1-1-0 | +0.10u | 1, -2.52c, +1.10u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 6 | 3 | -0.61c | 1-2-0 | -0.90u | 2, -0.77c, +0.10u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 31 | 5 | -1.01c | 2-3-0 | -1.14u | 4, -1.33c, -0.14u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 | 0.76c | 0-0-0 | +0.00u | 0, 0.76c, +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 1 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 3 | -1.47c | 1-2-0 | -1.60u | 3, -1.47c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 280 | 19 | 7.2% | -0.56c | 1.67c | 9-7-0 | +2.10u |  |
| MK novig fair-2c | 277 | 7 | 2.7% | -0.86c | 2.59c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1455 | 71 | 5.2% | -0.92c | 1.12c | 20-26-0 | -5.04u |  |
| MK prophetx fair-2c | 1440 | 17 | 1.2% | -0.9c | 2.05c | 4-10-0 | -5.71u |  |
| MK all fair-1c | 1735 | 90 | 5.5% | -0.85c | 1.21c | 29-33-0 | -2.95u | criteria not met (62/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1717 | 24 | 1.5% | -0.89c | 2.14c | 8-12-0 | -3.28u | criteria not met (20/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 38.

## Odds API credits (100K/month plan)

Study: 581/day, projected 17424/30 days. All monitors on the key: 2092/day, projected 62774/30 days. Remaining 62589; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T22:25:26Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 2800, 'polymarket_us': 2122}, 1338 unmatched (45 book-games; fuzzy-matched 0), 4995 side/lines, polls [none_due; NBA:fast,NHL:fast; NCAAF:fast], moves 4, new A 13 B 0, maker posted 20 filled 1, credits used 6 left 62589, 302s
- 2026-10-31T22:20:26Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 3166, 'polymarket_us': 3280}, 1497 unmatched (46 book-games; fuzzy-matched 0), 5437 side/lines, polls [none_due; NBA:fast,NHL:fast; NCAAF:fast], moves 0, new A 7 B 0, maker posted 8 filled 0, credits used 6 left 62614, 275s
- 2026-10-31T22:16:46Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 2276, 'polymarket_us': 1498}, 1337 unmatched (46 book-games; fuzzy-matched 0), 4201 side/lines, polls [NFL:slow; NBA:fast,NHL:fast; NCAAF:fast], moves 0, new A 22 B 0, maker posted 44 filled 2, credits used 8 left 62620, 195s
- 2026-10-31T22:10:00Z: 41 games (38 in 24h), quotes {'prophetx': 3642, 'novig': 670, 'kalshi': 3288, 'polymarket_us': 3278}, 1527 unmatched (52 book-games; fuzzy-matched 0), 5490 side/lines, polls [NCAAF:fast; NBA:fast,NHL:fast; NCAAF:fast], moves 6, new A 31 B 2, maker posted 21 filled 3, credits used 8 left 62641, 379s
- 2026-10-31T22:01:01Z: 41 games (38 in 24h), quotes {'prophetx': 3642, 'novig': 670, 'kalshi': 2520, 'polymarket_us': 1886}, 1434 unmatched (53 book-games; fuzzy-matched 0), 4641 side/lines, polls [none_due; NCAAF:fast; NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 62666, 260s
- 2026-10-31T21:56:07Z: 41 games (38 in 24h), quotes {'prophetx': 3714, 'novig': 668, 'kalshi': 2244, 'polymarket_us': 1512}, 1464 unmatched (51 book-games; fuzzy-matched 0), 4315 side/lines, polls [none_due; NCAAF:fast; NBA:fast,NHL:fast], moves 1, new A 5 B 0, maker posted 37 filled 0, credits used 6 left 62672, 271s
- 2026-10-31T21:50:19Z: 41 games (38 in 24h), quotes {'prophetx': 3722, 'novig': 672, 'kalshi': 3498, 'polymarket_us': 3256}, 1747 unmatched (56 book-games; fuzzy-matched 0), 5648 side/lines, polls [NFL:slow,NBA:fast,NHL:fast; NCAAF:fast; NBA:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 17 filled 1, credits used 12 left 62694, 325s
- 2026-10-31T21:40:25Z: 41 games (38 in 24h), quotes {'prophetx': 3590, 'novig': 666, 'kalshi': 2402, 'polymarket_us': 1826}, 1613 unmatched (53 book-games; fuzzy-matched 0), 4360 side/lines, polls [NCAAF:fast; NBA:fast,NHL:fast; NCAAF:fast], moves 3, new A 8 B 0, maker posted 19 filled 0, credits used 8 left 62719, 325s
- 2026-10-31T21:30:26Z: 41 games (38 in 24h), quotes {'prophetx': 3722, 'novig': 670, 'kalshi': 3520, 'polymarket_us': 2534}, 1876 unmatched (58 book-games; fuzzy-matched 0), 5352 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 10 B 0, maker posted 32 filled 0, credits used 12 left 62760, 326s
- 2026-10-31T21:20:43Z: 41 games (36 in 24h), quotes {'prophetx': 3534, 'novig': 674, 'kalshi': 3684, 'polymarket_us': 3262}, 2090 unmatched (61 book-games; fuzzy-matched 0), 5498 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 27 B 0, maker posted 20 filled 0, credits used 8 left 62789, 300s
