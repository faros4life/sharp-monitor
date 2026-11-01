# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T22:47:24Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3917 | 3794 | -1.94c | 21.5% | 1537 | -1.17c | 3619 | 1810-1809-0 | -204.51u | -5.7% |  |  | criteria not met (3619/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 952 | 924 | -3.85c | 14.0% | 211 | -3.05c | 895 | 463-432-0 | -57.74u | -6.5% |  |  | criteria not met (895/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 60 | 59 | -0.68c | 32.2% | 57 | 0.08c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 38 | -0.65c | 28.9% | 37 | -0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 148 | 143 | -0.58c | 34.3% | 141 | -0.64c | 138 | 66-71-1 | -9.92u | -7.2% | 0.26c | 22s | criteria not met (138/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 79 | 79 | -0.58c | 36.7% | 78 | -0.82c | 75 | 34-40-1 | -8.85u | -11.8% | 0.01c | 28s |  |
| M gettable, price moves | 69 | 64 | -0.57c | 31.2% | 63 | -0.42c | 63 | 32-31-0 | -1.07u | -1.7% | 0.57c | 20s |  |
| M control: not gettable | 569 | 449 | -0.86c | 34.1% | 446 | -1.2c | 429 | 228-195-6 | +7.80u | 1.8% | 1.77c | 26s |  |
| M all moves | 717 | 592 | -0.79c | 34.1% | 587 | -1.07c | 567 | 294-266-7 | -2.12u | -0.4% | 1.46c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 615 | 605 | 4.31c | 28.6% | 118 | 3.6c | 576 | 258-318-0 | +259.12u | 45.0% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 21 | 20 | 0.09c | 9-11-0 | -1.24u | 16, -0.04c, -1.47u | not enough yet |
| J2 B, NBA | 10 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 15 | -0.24c | 7-8-0 | -0.40u | 12, -0.42c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 50 | 46 | -0.55c | 16-29-1 | -13.78u | 31, -0.62c, -10.54u | not enough yet |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 6 | -0.99c | 3-3-0 | -1.66u | 5, -1.01c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 559 | 29 | 5.3% | -0.37c | 1.64c | 14-11-0 | +3.48u |  |
| MK novig fair-2c | 559 | 11 | 2.0% | -0.51c | 2.55c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1861 | 91 | 4.9% | -0.93c | 1.1c | 40-44-2 | -2.35u |  |
| MK prophetx fair-2c | 1844 | 25 | 1.4% | -0.8c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2420 | 120 | 5.0% | -0.8c | 1.21c | 54-55-2 | +1.13u | criteria not met (111/50 graded, CLV not positive) |
| MK all fair-2c | 2403 | 36 | 1.5% | -0.71c | 2.15c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 50.

## Odds API credits (100K/month plan)

Study: 628/day, projected 18826/30 days. All monitors on the key: 2141/day, projected 64232/30 days. Remaining 97917; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T22:40:30Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 670, 'polymarket_us': 528}, 272 unmatched (7 book-games; fuzzy-matched 0), 881 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 1, maker posted 20 filled 0, credits used 12 left 97917, 414s
- 2026-11-01T22:30:37Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 678, 'polymarket_us': 528}, 280 unmatched (7 book-games; fuzzy-matched 0), 881 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 97938, 407s
- 2026-11-01T22:23:14Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 690, 'polymarket_us': 528}, 292 unmatched (7 book-games; fuzzy-matched 0), 883 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 4 filled 0, credits used 6 left 97961, 249s
- 2026-11-01T22:20:23Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 694, 'polymarket_us': 528}, 296 unmatched (7 book-games; fuzzy-matched 0), 883 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 97967, 121s
- 2026-11-01T22:12:55Z: 10 games (5 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 704, 'polymarket_us': 528}, 306 unmatched (7 book-games; fuzzy-matched 0), 883 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 97982, 269s
- 2026-11-01T22:07:54Z: 11 games (6 in 24h), quotes {'prophetx': 338, 'novig': 330, 'kalshi': 706, 'polymarket_us': 528}, 236 unmatched (6 book-games; fuzzy-matched 0), 957 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 97988, 269s
- 2026-11-01T22:00:36Z: 11 games (6 in 24h), quotes {'prophetx': 338, 'novig': 426, 'kalshi': 720, 'polymarket_us': 528}, 250 unmatched (6 book-games; fuzzy-matched 0), 979 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 10 filled 0, credits used 12 left 98005, 407s
- 2026-11-01T21:50:30Z: 11 games (6 in 24h), quotes {'prophetx': 426, 'novig': 426, 'kalshi': 722, 'polymarket_us': 654}, 254 unmatched (6 book-games; fuzzy-matched 25), 1093 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 6 filled 1, credits used 12 left 98026, 441s
- 2026-11-01T21:40:31Z: 11 games (6 in 24h), quotes {'prophetx': 426, 'novig': 426, 'kalshi': 736, 'polymarket_us': 654}, 262 unmatched (7 book-games; fuzzy-matched 0), 1095 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 17 filled 0, credits used 12 left 98047, 407s
- 2026-11-01T21:30:33Z: 11 games (6 in 24h), quotes {'prophetx': 418, 'novig': 424, 'kalshi': 768, 'polymarket_us': 654}, 296 unmatched (8 book-games; fuzzy-matched 0), 1091 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 23 filled 0, credits used 12 left 98068, 301s
