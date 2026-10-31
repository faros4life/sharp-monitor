# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T23:14:35Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3123 | 2887 | -2.28c | 20.8% | 1126 | -1.31c | 2601 | 1309-1292-0 | -155.22u | -6.0% |  |  | criteria not met (2601/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 838 | 796 | -4.24c | 13.7% | 184 | -3.22c | 722 | 369-353-0 | -44.67u | -6.2% |  |  | criteria not met (722/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 49 | 46 | -0.79c | 34.8% | 44 | -0.03c | 43 | 19-24-0 | -1.79u | -4.2% |  |  | criteria not met (43/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 3 | 2-1-0 | +1.23u | 41.1% |  |  |  |
| B ref age 1-5m | 32 | 30 | -0.55c | 33.3% | 29 | 0.06c | 28 | 13-15-0 | +0.60u | 2.2% |  |  |  |
| B ref age 5m+ | 14 | 13 | -1.78c | 30.8% | 12 | -0.71c | 12 | 4-8-0 | -3.63u | -30.3% |  |  |  |
| M move-watch: gettable (sightings) | 125 | 110 | -0.61c | 32.7% | 109 | -0.75c | 96 | 49-46-1 | -0.04u | -0.0% | 0.17c | 22s | criteria not met (96/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 67 | 60 | -0.54c | 36.7% | 59 | -0.94c | 52 | 27-24-1 | +0.84u | 1.6% | 0.02c | 26s |  |
| M gettable, price moves | 58 | 50 | -0.69c | 28.0% | 50 | -0.54c | 44 | 22-22-0 | -0.88u | -2.0% | 0.35c | 20s |  |
| M control: not gettable | 481 | 331 | -0.76c | 34.7% | 330 | -1.24c | 291 | 158-128-5 | +12.23u | 4.2% | 1.81c | 26s |  |
| M all moves | 606 | 441 | -0.73c | 34.2% | 439 | -1.12c | 387 | 207-174-6 | +12.19u | 3.2% | 1.47c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 562 | 518 | 3.27c | 27.8% | 103 | 2.65c | 445 | 208-237-0 | +217.78u | 48.9% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 10 | 5 | -0.34c | 2-3-0 | -0.78u | 4, -0.39c, +0.22u | not enough yet |
| J2 B, NBA | 5 | 2 | -1.16c | 1-1-0 | +0.10u | 1, -1.55c, +1.10u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 7 | 4 | -0.49c | 2-2-0 | +0.22u | 3, -0.6c, +1.22u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 33 | 13 | -0.81c | 4-8-1 | -4.23u | 10, -1.1c, -5.14u | not enough yet |
| D1 B, unders (descriptive) | 1 | 1 | 0.76c | 1-0-0 | +1.13u | 1, 0.76c, +1.13u | descriptive only |
| D2 B, underdog spreads (descriptive) | 1 | 0 | 0.12c | 0-0-0 | +0.00u | 0, 0.12c, +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 3 | -1.22c | 1-2-0 | -1.60u | 3, -1.31c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 298 | 19 | 7.1% | -0.55c | 1.66c | 9-8-0 | +1.10u |  |
| MK novig fair-2c | 295 | 7 | 2.6% | -0.86c | 2.58c | 4-3-0 | +1.42u |  |
| MK prophetx fair-1c | 1494 | 72 | 5.0% | -0.92c | 1.11c | 23-30-2 | -5.73u |  |
| MK prophetx fair-2c | 1480 | 17 | 1.2% | -0.9c | 2.04c | 5-10-0 | -4.57u |  |
| MK all fair-1c | 1792 | 91 | 5.4% | -0.84c | 1.21c | 32-38-2 | -4.63u | criteria not met (72/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1775 | 24 | 1.4% | -0.89c | 2.14c | 9-13-0 | -3.15u | criteria not met (22/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 40.

## Odds API credits (100K/month plan)

Study: 589/day, projected 17675/30 days. All monitors on the key: 2108/day, projected 63246/30 days. Remaining 62461; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T23:08:44Z: 38 games (36 in 24h), quotes {'prophetx': 3054, 'novig': 664, 'kalshi': 2564, 'polymarket_us': 3138}, 738 unmatched (22 book-games; fuzzy-matched 0), 5183 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 26 B 0, maker posted 6 filled 0, credits used 12 left 62461, 350s
- 2026-10-31T23:00:30Z: 39 games (37 in 24h), quotes {'prophetx': 3054, 'novig': 663, 'kalshi': 2504, 'polymarket_us': 2118}, 746 unmatched (27 book-games; fuzzy-matched 0), 4495 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 38 B 0, maker posted 61 filled 0, credits used 8 left 62486, 210s
- 2026-10-31T22:54:36Z: 39 games (36 in 24h), quotes {'prophetx': 3554, 'novig': 691, 'kalshi': 2728, 'polymarket_us': 3268}, 1144 unmatched (34 book-games; fuzzy-matched 0), 5544 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 12 B 0, maker posted 5 filled 0, credits used 6 left 62505, 288s
- 2026-10-31T22:50:23Z: 39 games (36 in 24h), quotes {'prophetx': 3466, 'novig': 689, 'kalshi': 2422, 'polymarket_us': 1900}, 1096 unmatched (34 book-games; fuzzy-matched 0), 4709 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 15 filled 0, credits used 6 left 62511, 184s
- 2026-10-31T22:40:25Z: 39 games (36 in 24h), quotes {'prophetx': 3546, 'novig': 691, 'kalshi': 2338, 'polymarket_us': 1838}, 1176 unmatched (41 book-games; fuzzy-matched 0), 4677 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 7 B 1, maker posted 28 filled 1, credits used 14 left 62538, 330s
- 2026-10-31T22:30:54Z: 40 games (37 in 24h), quotes {'prophetx': 0, 'novig': 692, 'kalshi': 2616, 'polymarket_us': 1656}, 1153 unmatched (40 book-games; fuzzy-matched 0), 2689 side/lines, polls [none_due; NBA:fast,NHL:fast; NCAAF:fast], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 62569, 262s
- 2026-10-31T22:25:26Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 2800, 'polymarket_us': 2122}, 1338 unmatched (45 book-games; fuzzy-matched 0), 4995 side/lines, polls [none_due; NBA:fast,NHL:fast; NCAAF:fast], moves 4, new A 13 B 0, maker posted 20 filled 1, credits used 6 left 62589, 302s
- 2026-10-31T22:20:26Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 3166, 'polymarket_us': 3280}, 1497 unmatched (46 book-games; fuzzy-matched 0), 5437 side/lines, polls [none_due; NBA:fast,NHL:fast; NCAAF:fast], moves 0, new A 7 B 0, maker posted 8 filled 0, credits used 6 left 62614, 275s
- 2026-10-31T22:16:46Z: 40 games (37 in 24h), quotes {'prophetx': 3642, 'novig': 671, 'kalshi': 2276, 'polymarket_us': 1498}, 1337 unmatched (46 book-games; fuzzy-matched 0), 4201 side/lines, polls [NFL:slow; NBA:fast,NHL:fast; NCAAF:fast], moves 0, new A 22 B 0, maker posted 44 filled 2, credits used 8 left 62620, 195s
- 2026-10-31T22:10:00Z: 41 games (38 in 24h), quotes {'prophetx': 3642, 'novig': 670, 'kalshi': 3288, 'polymarket_us': 3278}, 1527 unmatched (52 book-games; fuzzy-matched 0), 5490 side/lines, polls [NCAAF:fast; NBA:fast,NHL:fast; NCAAF:fast], moves 6, new A 31 B 2, maker posted 21 filled 3, credits used 8 left 62641, 379s
