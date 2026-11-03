# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T03:52:26Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4926 | 4850 | -1.95c | 22.6% | 1942 | -1.21c | 4405 | 2224-2181-0 | -244.44u | -5.5% |  |  | criteria not met (4405/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1262 | 1227 | -3.79c | 14.9% | 276 | -3.08c | 1103 | 560-543-0 | -97.56u | -8.8% |  |  | criteria not met (1103/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 78 | 78 | -0.79c | 32.1% | 74 | 0.04c | 67 | 29-38-0 | -5.05u | -7.5% |  |  | criteria not met (67/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 48 | 48 | -0.56c | 31.2% | 46 | 0.07c | 42 | 19-23-0 | -0.92u | -2.2% |  |  |  |
| B ref age 5m+ | 25 | 25 | -1.49c | 32.0% | 23 | -0.37c | 20 | 7-13-0 | -5.42u | -27.1% |  |  |  |
| M move-watch: gettable (sightings) | 177 | 177 | -0.71c | 32.8% | 174 | -0.68c | 171 | 86-84-1 | -5.58u | -3.3% | 0.06c | 25s | criteria not met (171/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 94 | 94 | -0.58c | 35.1% | 93 | -0.84c | 90 | 45-44-1 | -2.60u | -2.9% | -0.1c | 28s |  |
| M gettable, price moves | 83 | 83 | -0.87c | 30.1% | 81 | -0.49c | 81 | 41-40-0 | -2.98u | -3.7% | 0.25c | 22s |  |
| M control: not gettable | 731 | 593 | -0.91c | 34.2% | 583 | -1.31c | 535 | 276-249-10 | -3.49u | -0.7% | 1.82c | 28s |  |
| M all moves | 908 | 770 | -0.86c | 33.9% | 757 | -1.17c | 706 | 362-333-11 | -9.07u | -1.3% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 686 | 677 | 3.62c | 27.9% | 128 | 3.72c | 644 | 281-363-0 | +314.30u | 48.8% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 39 | 28 | 0.0c | 12-16-0 | -3.03u | 21, -0.17c, -4.36u | not enough yet |
| J2 B, NBA | 28 | 17 | -0.13c | 7-10-0 | -2.49u | 11, -0.43c, -2.74u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 25 | 19 | -0.01c | 9-10-0 | -0.24u | 15, -0.27c, +1.68u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 77 | 71 | -0.74c | 31-39-1 | -9.61u | 43, -0.92c, -5.08u | negative |
| D1 B, unders (descriptive) | 6 | 6 | 0.63c | 4-2-0 | +2.27u | 6, 0.63c, +2.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 4 | -1.14c | 0-4-0 | -4.00u | 4, -1.69c, -4.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 14 | -0.49c | 8-6-0 | -1.50u | 9, -0.66c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 736 | 40 | 5.4% | -0.4c | 1.63c | 18-19-0 | -0.23u |  |
| MK novig fair-2c | 738 | 18 | 2.4% | -0.45c | 2.55c | 10-6-0 | +5.10u |  |
| MK prophetx fair-1c | 2225 | 112 | 5.0% | -0.92c | 1.1c | 50-49-2 | +3.11u |  |
| MK prophetx fair-2c | 2209 | 35 | 1.6% | -0.6c | 2.04c | 12-18-0 | -5.04u |  |
| MK all fair-1c | 2961 | 152 | 5.1% | -0.78c | 1.23c | 68-68-2 | +2.88u | criteria not met (138/50 graded, CLV not positive) |
| MK all fair-2c | 2947 | 53 | 1.8% | -0.55c | 2.17c | 22-24-0 | +0.06u | criteria not met (46/50 graded, CLV not positive) |

A and B on the same side/line: 66.

## Odds API credits (100K/month plan)

Study: 638/day, projected 19145/30 days. All monitors on the key: 2160/day, projected 64794/30 days. Remaining 95196; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T03:50:39Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 666, 'polymarket_us': 660}, 332 unmatched (8 book-games; fuzzy-matched 0), 872 side/lines, polls [NCAAF:slow,NHL:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 95196, 107s
- 2026-11-03T03:40:40Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 403, 'kalshi': 722, 'polymarket_us': 660}, 390 unmatched (9 book-games; fuzzy-matched 0), 872 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 95214, 106s
- 2026-11-03T03:30:33Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 748, 'polymarket_us': 660}, 416 unmatched (10 book-games; fuzzy-matched 0), 872 side/lines, polls [NCAAF:slow,NHL:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 95221, 105s
- 2026-11-03T03:20:38Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 820, 'polymarket_us': 660}, 487 unmatched (12 book-games; fuzzy-matched 0), 874 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 95232, 106s
- 2026-11-03T03:10:37Z: 16 games (16 in 24h), quotes {'prophetx': 552, 'novig': 397, 'kalshi': 896, 'polymarket_us': 660}, 342 unmatched (9 book-games; fuzzy-matched 0), 1096 side/lines, polls [none_due; NBA:fast; none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 95239, 404s
- 2026-11-03T03:00:53Z: 16 games (16 in 24h), quotes {'prophetx': 552, 'novig': 689, 'kalshi': 942, 'polymarket_us': 660}, 387 unmatched (11 book-games; fuzzy-matched 0), 1166 side/lines, polls [NCAAF:slow,NBA:fast,NHL:slow; NBA:fast], moves 1, new A 18 B 0, maker posted 0 filled 0, credits used 8 left 95252, 301s
- 2026-11-03T02:50:36Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 697, 'kalshi': 1062, 'polymarket_us': 1044}, 507 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 2, new A 2 B 1, maker posted 0 filled 2, credits used 2 left 95275, 231s
- 2026-11-03T02:42:02Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 699, 'kalshi': 1102, 'polymarket_us': 1044}, 545 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 2 left 95288, 259s
- 2026-11-03T02:38:20Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1146, 'polymarket_us': 1044}, 590 unmatched (14 book-games; fuzzy-matched 0), 1490 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, maker posted 1 filled 0, credits used 2 left 95290, 181s
- 2026-11-03T02:30:42Z: 16 games (16 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1200, 'polymarket_us': 1044}, 644 unmatched (15 book-games; fuzzy-matched 0), 1491 side/lines, polls [NCAAF:slow,NBA:fast,NHL:slow; NBA:fast], moves 0, new A 4 B 0, maker posted 12 filled 1, credits used 8 left 95305, 301s
