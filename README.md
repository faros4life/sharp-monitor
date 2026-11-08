# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T18:16:27Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7676 | 7443 | -1.58c | 23.8% | 3271 | -1.02c | 7308 | 3767-3541-0 | -255.14u | -3.5% |  |  | criteria not met (7308/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1728 | 1634 | -3.12c | 18.2% | 360 | -2.61c | 1625 | 835-790-0 | -123.55u | -7.6% |  |  | criteria not met (1625/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 130 | 127 | -1.02c | 27.6% | 119 | -0.07c | 123 | 54-69-0 | -8.52u | -6.9% |  |  | criteria not met (123/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 75 | -1.03c | 26.7% | 72 | -0.18c | 72 | 34-38-0 | +0.46u | 0.6% |  |  |  |
| B ref age 5m+ | 43 | 43 | -1.23c | 27.9% | 38 | -0.12c | 42 | 15-27-0 | -10.38u | -24.7% |  |  |  |
| M move-watch: gettable (sightings) | 349 | 341 | -0.59c | 34.9% | 341 | -0.57c | 334 | 170-159-5 | -9.09u | -2.7% | 0.24c | 26s | criteria not met (334/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 181 | 176 | -0.65c | 34.7% | 177 | -0.82c | 173 | 84-85-4 | -8.52u | -4.9% | -0.05c | 27s |  |
| M gettable, price moves | 168 | 165 | -0.52c | 35.2% | 164 | -0.3c | 161 | 86-74-1 | -0.57u | -0.4% | 0.55c | 23s |  |
| M control: not gettable | 1455 | 1125 | -0.8c | 35.7% | 1113 | -1.18c | 1140 | 565-554-21 | -58.38u | -5.1% | 1.8c | 183s |  |
| M all moves | 1804 | 1466 | -0.75c | 35.5% | 1454 | -1.04c | 1474 | 735-713-26 | -67.46u | -4.6% | 1.49c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1039 | 1032 | 2.73c | 27.1% | 222 | 2.91c | 1032 | 457-575-0 | +281.96u | 27.3% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 81 | 75 | -0.2c | 33-42-0 | -5.88u | 51, -0.41c, -9.22u | negative |
| J2 B, NBA | 52 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 44 | -0.43c | 22-22-0 | +1.86u | 34, -0.7c, +3.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 202 | 188 | -0.6c | 89-96-3 | -12.13u | 109, -0.63c, -13.21u | negative |
| D1 B, unders (descriptive) | 24 | 22 | 0.2c | 13-9-0 | +4.89u | 21, 0.15c, +3.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 15 | -0.84c | 4-11-0 | -6.43u | 13, -1.04c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 10 | 0.42c | 5-5-0 | +1.71u | 9, 0.42c, +0.56u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 61 | 60 | -0.33c | 34-24-2 | -2.48u | 34, -0.39c, -3.19u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1854 | 79 | 4.3% | -0.66c | 1.59c | 37-36-0 | +2.09u |  |
| MK novig fair-2c | 1850 | 29 | 1.6% | -0.45c | 2.52c | 16-11-0 | +6.65u |  |
| MK prophetx fair-1c | 4617 | 220 | 4.8% | -1.05c | 1.1c | 103-104-5 | +3.78u |  |
| MK prophetx fair-2c | 4586 | 72 | 1.6% | -0.65c | 2.04c | 33-35-0 | +0.84u |  |
| MK all fair-1c | 6471 | 299 | 4.7% | -0.95c | 1.24c | 140-140-5 | +5.87u | criteria not met (285/50 graded, CLV not positive) |
| MK all fair-2c | 6436 | 101 | 1.6% | -0.59c | 2.18c | 49-46-0 | +7.49u | criteria not met (95/50 graded, CLV not positive) |

A and B on the same side/line: 103.

## Odds API credits (100K/month plan)

Study: 636/day, projected 19089/30 days. All monitors on the key: 2368/day, projected 71052/30 days. Remaining 80617; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T18:11:25Z: 21 games (17 in 24h), quotes {'prophetx': 1546, 'novig': 722, 'kalshi': 1476, 'polymarket_us': 1750}, 440 unmatched (8 book-games; fuzzy-matched 0), 2987 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 1, maker posted 48 filled 2, credits used 12 left 80617, 302s
- 2026-11-08T18:01:11Z: 28 games (24 in 24h), quotes {'prophetx': 1450, 'novig': 720, 'kalshi': 1486, 'polymarket_us': 1748}, 64 unmatched (1 book-games; fuzzy-matched 0), 3336 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 22 B 0, maker posted 36 filled 0, credits used 6 left 80638, 182s
- 2026-11-08T17:51:29Z: 29 games (25 in 24h), quotes {'prophetx': 2268, 'novig': 714, 'kalshi': 1484, 'polymarket_us': 1794}, 0 unmatched (0 book-games; fuzzy-matched 0), 3933 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 0, maker posted 26 filled 2, credits used 12 left 80659, 350s
- 2026-11-08T17:41:34Z: 29 games (25 in 24h), quotes {'prophetx': 2276, 'novig': 718, 'kalshi': 1478, 'polymarket_us': 1474}, 0 unmatched (0 book-games; fuzzy-matched 0), 3771 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 2 B 0, maker posted 31 filled 2, credits used 6 left 80702, 273s
- 2026-11-08T17:31:47Z: 29 games (25 in 24h), quotes {'prophetx': 2276, 'novig': 714, 'kalshi': 1476, 'polymarket_us': 1454}, 0 unmatched (0 book-games; fuzzy-matched 0), 3755 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 8, new A 10 B 0, maker posted 33 filled 2, credits used 12 left 80736, 302s
- 2026-11-08T17:21:30Z: 29 games (25 in 24h), quotes {'prophetx': 2276, 'novig': 722, 'kalshi': 1492, 'polymarket_us': 2758}, 14 unmatched (1 book-games; fuzzy-matched 0), 4429 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 1, maker posted 13 filled 1, credits used 6 left 80778, 192s
- 2026-11-08T17:16:40Z: 29 games (25 in 24h), quotes {'prophetx': 2268, 'novig': 714, 'kalshi': 1500, 'polymarket_us': 2638}, 22 unmatched (1 book-games; fuzzy-matched 0), 4353 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 42 filled 1, credits used 6 left 80788, 182s
- 2026-11-08T17:11:17Z: 29 games (25 in 24h), quotes {'prophetx': 2268, 'novig': 716, 'kalshi': 1500, 'polymarket_us': 1726}, 24 unmatched (1 book-games; fuzzy-matched 0), 3892 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 7 B 1, maker posted 10 filled 3, credits used 6 left 80805, 228s
- 2026-11-08T17:01:39Z: 29 games (25 in 24h), quotes {'prophetx': 2152, 'novig': 712, 'kalshi': 1508, 'polymarket_us': 1458}, 28 unmatched (1 book-games; fuzzy-matched 0), 3702 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 19 filled 0, credits used 12 left 80822, 302s
- 2026-11-08T16:51:40Z: 29 games (25 in 24h), quotes {'prophetx': 2264, 'novig': 720, 'kalshi': 1510, 'polymarket_us': 1854}, 34 unmatched (1 book-games; fuzzy-matched 0), 3953 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 6 B 0, maker posted 0 filled 0, credits used 12 left 80851, 332s
