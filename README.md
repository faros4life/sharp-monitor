# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T03:22:24Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4923 | 4850 | -1.95c | 22.6% | 1942 | -1.21c | 4043 | 2045-1998-0 | -198.78u | -4.9% |  |  | criteria not met (4043/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1262 | 1227 | -3.79c | 14.9% | 276 | -3.08c | 987 | 518-469-0 | -56.40u | -5.7% |  |  | criteria not met (987/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 78 | 78 | -0.79c | 32.1% | 74 | 0.04c | 62 | 28-34-0 | -2.11u | -3.4% |  |  | criteria not met (62/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 48 | 48 | -0.56c | 31.2% | 46 | 0.07c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 25 | 25 | -1.49c | 32.0% | 23 | -0.37c | 18 | 7-11-0 | -3.42u | -19.0% |  |  |  |
| M move-watch: gettable (sightings) | 177 | 177 | -0.71c | 32.8% | 174 | -0.68c | 157 | 81-75-1 | -1.38u | -0.9% | 0.06c | 25s | criteria not met (157/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 94 | 94 | -0.58c | 35.1% | 93 | -0.84c | 83 | 42-40-1 | -1.45u | -1.8% | -0.1c | 28s |  |
| M gettable, price moves | 83 | 83 | -0.87c | 30.1% | 81 | -0.49c | 74 | 39-35-0 | +0.08u | 0.1% | 0.25c | 22s |  |
| M control: not gettable | 731 | 593 | -0.91c | 34.2% | 583 | -1.31c | 492 | 256-226-10 | +2.14u | 0.4% | 1.82c | 28s |  |
| M all moves | 908 | 770 | -0.86c | 33.9% | 757 | -1.17c | 649 | 337-301-11 | +0.76u | 0.1% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 686 | 677 | 3.62c | 27.9% | 128 | 3.72c | 617 | 274-343-0 | +323.38u | 52.4% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 39 | 23 | 0.0c | 11-12-0 | -0.09u | 18, -0.17c, -1.36u | not enough yet |
| J2 B, NBA | 28 | 12 | -0.13c | 6-6-0 | +0.45u | 8, -0.43c, +0.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 25 | 16 | -0.01c | 8-8-0 | +0.70u | 13, -0.27c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 77 | 57 | -0.74c | 26-30-1 | -5.40u | 38, -0.92c, -5.98u | negative |
| D1 B, unders (descriptive) | 6 | 5 | 0.63c | 3-2-0 | +1.21u | 5, 0.63c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 2 | -1.14c | 0-2-0 | -2.00u | 2, -1.69c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 14 | -0.49c | 8-6-0 | -1.50u | 9, -0.66c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 736 | 40 | 5.4% | -0.4c | 1.63c | 15-16-0 | -0.48u |  |
| MK novig fair-2c | 738 | 18 | 2.4% | -0.45c | 2.55c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 2225 | 112 | 5.0% | -0.92c | 1.1c | 46-46-2 | +1.94u |  |
| MK prophetx fair-2c | 2209 | 35 | 1.6% | -0.6c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2961 | 152 | 5.1% | -0.78c | 1.23c | 61-62-2 | +1.46u | criteria not met (125/50 graded, CLV not positive) |
| MK all fair-2c | 2947 | 53 | 1.8% | -0.55c | 2.17c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 66.

## Odds API credits (100K/month plan)

Study: 639/day, projected 19170/30 days. All monitors on the key: 2161/day, projected 64837/30 days. Remaining 95232; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T03:20:38Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 820, 'polymarket_us': 660}, 487 unmatched (12 book-games; fuzzy-matched 0), 874 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 95232, 106s
- 2026-11-03T03:10:37Z: 16 games (16 in 24h), quotes {'prophetx': 552, 'novig': 397, 'kalshi': 896, 'polymarket_us': 660}, 342 unmatched (9 book-games; fuzzy-matched 0), 1096 side/lines, polls [none_due; NBA:fast; none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 95239, 404s
- 2026-11-03T03:00:53Z: 16 games (16 in 24h), quotes {'prophetx': 552, 'novig': 689, 'kalshi': 942, 'polymarket_us': 660}, 387 unmatched (11 book-games; fuzzy-matched 0), 1166 side/lines, polls [NCAAF:slow,NBA:fast,NHL:slow; NBA:fast], moves 1, new A 18 B 0, maker posted 0 filled 0, credits used 8 left 95252, 301s
- 2026-11-03T02:50:36Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 697, 'kalshi': 1062, 'polymarket_us': 1044}, 507 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 2, new A 2 B 1, maker posted 0 filled 2, credits used 2 left 95275, 231s
- 2026-11-03T02:42:02Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 699, 'kalshi': 1102, 'polymarket_us': 1044}, 545 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 2 left 95288, 259s
- 2026-11-03T02:38:20Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1146, 'polymarket_us': 1044}, 590 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, maker posted 1 filled 0, credits used 2 left 95290, 181s
- 2026-11-03T02:30:42Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1200, 'polymarket_us': 1044}, 644 unmatched (15 book-games; fuzzy-matched 0), 1491 side/lines, polls [NCAAF:slow,NBA:fast,NHL:slow; NBA:fast], moves 0, new A 4 B 0, maker posted 12 filled 1, credits used 8 left 95305, 301s
- 2026-11-03T02:20:34Z: 16 games (16 in 24h), quotes {'prophetx': 808, 'novig': 695, 'kalshi': 1254, 'polymarket_us': 1044}, 698 unmatched (17 book-games; fuzzy-matched 0), 1478 side/lines, polls [none_due; NBA:fast], moves 2, new A 2 B 1, maker posted 14 filled 1, credits used 2 left 95341, 233s
- 2026-11-03T02:10:38Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 703, 'kalshi': 1328, 'polymarket_us': 1044}, 682 unmatched (15 book-games; fuzzy-matched 0), 1570 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 8 left 95347, 301s
- 2026-11-03T02:00:34Z: 18 games (17 in 24h), quotes {'prophetx': 790, 'novig': 728, 'kalshi': 1370, 'polymarket_us': 1044}, 720 unmatched (15 book-games; fuzzy-matched 0), 1599 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 4 filled 0, credits used 8 left 95375, 302s
