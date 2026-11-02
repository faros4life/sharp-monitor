# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T00:07:27Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3936 | 3804 | -1.94c | 21.5% | 1546 | -1.16c | 3674 | 1838-1836-0 | -211.23u | -5.7% |  |  | criteria not met (3674/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 957 | 924 | -3.85c | 14.0% | 211 | -3.05c | 912 | 472-440-0 | -60.36u | -6.6% |  |  | criteria not met (912/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 60 | 59 | -0.68c | 32.2% | 57 | 0.08c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 38 | -0.65c | 28.9% | 37 | -0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 150 | 146 | -0.56c | 34.2% | 144 | -0.62c | 140 | 68-71-1 | -8.07u | -5.8% | 0.28c | 22s | criteria not met (140/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 80 | 79 | -0.58c | 36.7% | 78 | -0.82c | 77 | 36-40-1 | -7.01u | -9.1% | 0.01c | 27s |  |
| M gettable, price moves | 70 | 67 | -0.53c | 31.3% | 66 | -0.39c | 63 | 32-31-0 | -1.07u | -1.7% | 0.59c | 20s |  |
| M control: not gettable | 572 | 452 | -0.86c | 33.8% | 449 | -1.2c | 444 | 234-202-8 | +7.40u | 1.7% | 1.77c | 26s |  |
| M all moves | 722 | 598 | -0.79c | 33.9% | 593 | -1.06c | 584 | 302-273-9 | -0.67u | -0.1% | 1.46c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 615 | 605 | 4.31c | 28.6% | 118 | 3.6c | 590 | 263-327-0 | +257.66u | 43.7% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 21 | 20 | 0.09c | 9-11-0 | -1.24u | 16, -0.04c, -1.47u | not enough yet |
| J2 B, NBA | 10 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 15 | -0.24c | 7-8-0 | -0.40u | 12, -0.42c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 52 | 48 | -0.55c | 18-29-1 | -11.94u | 32, -0.62c, -9.61u | not enough yet |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 6 | -0.65c | 3-3-0 | -1.66u | 5, -0.66c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 573 | 29 | 5.2% | -0.37c | 1.63c | 15-12-0 | +3.52u |  |
| MK novig fair-2c | 573 | 11 | 2.0% | -0.51c | 2.55c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1877 | 91 | 4.9% | -0.93c | 1.1c | 41-45-2 | -2.28u |  |
| MK prophetx fair-2c | 1861 | 25 | 1.4% | -0.8c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2450 | 120 | 4.9% | -0.8c | 1.22c | 56-57-2 | +1.24u | criteria not met (115/50 graded, CLV not positive) |
| MK all fair-2c | 2434 | 36 | 1.5% | -0.71c | 2.15c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 50.

## Odds API credits (100K/month plan)

Study: 639/day, projected 19180/30 days. All monitors on the key: 2153/day, projected 64579/30 days. Remaining 97738; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T00:00:36Z: 19 games (4 in 24h), quotes {'prophetx': 354, 'novig': 358, 'kalshi': 962, 'polymarket_us': 684}, 128 unmatched (4 book-games; fuzzy-matched 0), 1409 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 0, maker posted 13 filled 0, credits used 12 left 97738, 411s
- 2026-11-01T23:50:29Z: 19 games (4 in 24h), quotes {'prophetx': 304, 'novig': 314, 'kalshi': 898, 'polymarket_us': 502}, 128 unmatched (4 book-games; fuzzy-matched 0), 1226 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 12 filled 0, credits used 12 left 97759, 417s
- 2026-11-01T23:40:30Z: 18 games (4 in 24h), quotes {'prophetx': 304, 'novig': 312, 'kalshi': 772, 'polymarket_us': 502}, 148 unmatched (5 book-games; fuzzy-matched 0), 1083 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 97782, 416s
- 2026-11-01T23:30:33Z: 14 games (4 in 24h), quotes {'prophetx': 304, 'novig': 314, 'kalshi': 708, 'polymarket_us': 502}, 188 unmatched (6 book-games; fuzzy-matched 0), 980 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 12 left 97812, 413s
- 2026-11-01T23:20:26Z: 12 games (4 in 24h), quotes {'prophetx': 304, 'novig': 312, 'kalshi': 616, 'polymarket_us': 500}, 194 unmatched (6 book-games; fuzzy-matched 0), 881 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 97833, 420s
- 2026-11-01T23:10:31Z: 10 games (4 in 24h), quotes {'prophetx': 304, 'novig': 312, 'kalshi': 574, 'polymarket_us': 500}, 206 unmatched (6 book-games; fuzzy-matched 25), 828 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 6 filled 0, credits used 12 left 97854, 414s
- 2026-11-01T23:00:37Z: 10 games (5 in 24h), quotes {'prophetx': 304, 'novig': 312, 'kalshi': 606, 'polymarket_us': 500}, 221 unmatched (7 book-games; fuzzy-matched 0), 842 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 5 filled 0, credits used 12 left 97875, 408s
- 2026-11-01T22:50:27Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 648, 'polymarket_us': 528}, 256 unmatched (7 book-games; fuzzy-matched 0), 877 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 4 B 0, maker posted 21 filled 0, credits used 12 left 97896, 450s
- 2026-11-01T22:40:30Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 670, 'polymarket_us': 528}, 272 unmatched (7 book-games; fuzzy-matched 0), 881 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 1, maker posted 20 filled 0, credits used 12 left 97917, 414s
- 2026-11-01T22:30:37Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 678, 'polymarket_us': 528}, 280 unmatched (7 book-games; fuzzy-matched 0), 881 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 97938, 407s
