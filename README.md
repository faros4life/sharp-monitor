# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T17:02:18Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2461 | 2207 | -2.45c | 23.9% | 852 | -1.3c | 1881 | 941-940-0 | -117.27u | -6.2% |  |  | criteria not met (1881/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 649 | 550 | -5.04c | 16.2% | 120 | -3.63c | 397 | 194-203-0 | -31.33u | -7.9% |  |  | criteria not met (397/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 38 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 25 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 99 | 78 | -0.7c | 35.9% | 77 | -0.76c | 71 | 41-30-0 | +8.93u | 12.6% | 0.15c | 26s | criteria not met (71/50 graded, CLV not positive) |
| M gettable, line moves | 53 | 43 | -0.66c | 39.5% | 42 | -0.93c | 40 | 23-17-0 | +4.09u | 10.2% | 0.06c | 44s |  |
| M gettable, price moves | 46 | 35 | -0.75c | 31.4% | 35 | -0.55c | 31 | 18-13-0 | +4.84u | 15.6% | 0.26c | 20s |  |
| M control: not gettable | 381 | 224 | -0.64c | 34.8% | 224 | -1.14c | 189 | 97-89-3 | -3.24u | -1.7% | 1.81c | 28s |  |
| M all moves | 480 | 302 | -0.65c | 35.1% | 301 | -1.04c | 260 | 138-119-3 | +5.69u | 2.2% | 1.45c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 346 | 279 | 1.6c | 24.0% | 58 | 2.32c | 146 | 69-77-0 | +97.83u | 67.0% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J2 B, NBA | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 9 | 0 | -0.5c | 0-0-0 | +0.00u | 0, -0.5c, +0.00u | not enough yet |
| D1 B, unders (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 4 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 195 | 16 | 8.6% | -0.47c | 1.68c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 192 | 6 | 3.3% | -0.95c | 2.62c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 880 | 43 | 5.5% | -1.01c | 1.11c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 870 | 13 | 1.7% | -1.26c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 1075 | 59 | 6.1% | -0.85c | 1.25c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 1062 | 19 | 2.0% | -1.14c | 2.2c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 30.

## Odds API credits (100K/month plan)

Study: 517/day, projected 15523/30 days. All monitors on the key: 1966/day, projected 58971/30 days. Remaining 63557; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T16:57:53Z: 70 games (53 in 24h), quotes {'prophetx': 6366, 'novig': 664, 'kalshi': 2752, 'polymarket_us': 1952}, 4289 unmatched (126 book-games; fuzzy-matched 1), 5330 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 1 B 0, maker posted 74 filled 1, credits used 6 left 63557, 265s
- 2026-10-31T16:51:04Z: 70 games (53 in 24h), quotes {'prophetx': 3956, 'novig': 671, 'kalshi': 2744, 'polymarket_us': 2052}, 4528 unmatched (124 book-games; fuzzy-matched 1), 2792 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 13 B 0, maker posted 0 filled 0, credits used 6 left 63572, 307s
- 2026-10-31T16:47:37Z: 71 games (54 in 24h), quotes {'prophetx': 6366, 'novig': 671, 'kalshi': 3076, 'polymarket_us': 2334}, 4678 unmatched (128 book-games; fuzzy-matched 2), 5612 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 6 filled 0, credits used 6 left 63580, 184s
- 2026-10-31T16:40:22Z: 71 games (54 in 24h), quotes {'prophetx': 5838, 'novig': 677, 'kalshi': 3728, 'polymarket_us': 3796}, 5711 unmatched (143 book-games; fuzzy-matched 65), 5639 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 7 B 0, maker posted 9 filled 6, credits used 8 left 63595, 274s
- 2026-10-31T16:31:10Z: 72 games (55 in 24h), quotes {'prophetx': 6474, 'novig': 677, 'kalshi': 2724, 'polymarket_us': 1994}, 4229 unmatched (124 book-games; fuzzy-matched 1), 5547 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 16 filled 2, credits used 6 left 63614, 255s
- 2026-10-31T16:26:41Z: 72 games (55 in 24h), quotes {'prophetx': 6624, 'novig': 676, 'kalshi': 3648, 'polymarket_us': 3796}, 5467 unmatched (145 book-games; fuzzy-matched 2), 6213 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 0, maker posted 29 filled 0, credits used 6 left 63629, 248s
- 2026-10-31T16:20:41Z: 72 games (55 in 24h), quotes {'prophetx': 6624, 'novig': 678, 'kalshi': 2838, 'polymarket_us': 2238}, 4174 unmatched (127 book-games; fuzzy-matched 1), 5766 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 35 filled 0, credits used 6 left 63647, 337s
- 2026-10-31T16:16:20Z: 72 games (55 in 24h), quotes {'prophetx': 6014, 'novig': 681, 'kalshi': 2936, 'polymarket_us': 2282}, 4216 unmatched (127 book-games; fuzzy-matched 2), 5353 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 13 filled 1, credits used 8 left 63653, 243s
- 2026-10-31T16:10:22Z: 72 games (55 in 24h), quotes {'prophetx': 6598, 'novig': 671, 'kalshi': 2374, 'polymarket_us': 2096}, 3934 unmatched (123 book-games; fuzzy-matched 2), 5580 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 6 B 0, maker posted 9 filled 2, credits used 12 left 63670, 338s
- 2026-10-31T16:00:30Z: 78 games (61 in 24h), quotes {'prophetx': 6578, 'novig': 675, 'kalshi': 2728, 'polymarket_us': 1958}, 3582 unmatched (114 book-games; fuzzy-matched 1), 4987 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 30 B 0, maker posted 49 filled 1, credits used 6 left 63693, 186s
