# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T16:30:50Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2445 | 2142 | -2.48c | 24.0% | 827 | -1.29c | 1881 | 941-940-0 | -117.27u | -6.2% |  |  | criteria not met (1881/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 639 | 523 | -5.17c | 16.8% | 110 | -3.66c | 397 | 194-203-0 | -31.33u | -7.9% |  |  | criteria not met (397/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 38 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 25 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 95 | 78 | -0.7c | 35.9% | 77 | -0.76c | 71 | 41-30-0 | +8.93u | 12.6% | 0.15c | 28s | criteria not met (71/50 graded, CLV not positive) |
| M gettable, line moves | 52 | 43 | -0.66c | 39.5% | 42 | -0.93c | 40 | 23-17-0 | +4.09u | 10.2% | 0.06c | 54s |  |
| M gettable, price moves | 43 | 35 | -0.75c | 31.4% | 35 | -0.55c | 31 | 18-13-0 | +4.84u | 15.6% | 0.26c | 21s |  |
| M control: not gettable | 373 | 215 | -0.6c | 34.9% | 215 | -1.1c | 189 | 97-89-3 | -3.24u | -1.7% | 1.83c | 29s |  |
| M all moves | 468 | 293 | -0.62c | 35.2% | 292 | -1.01c | 260 | 138-119-3 | +5.69u | 2.2% | 1.45c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 336 | 250 | 1.47c | 24.8% | 48 | 3.2c | 146 | 69-77-0 | +97.83u | 67.0% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J2 B, NBA | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 6 | 0 | -0.5c | 0-0-0 | +0.00u | 0, -0.5c, +0.00u | not enough yet |
| D1 B, unders (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 3 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 193 | 14 | 7.9% | -0.47c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 192 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 829 | 38 | 5.3% | -0.95c | 1.11c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 818 | 11 | 1.5% | -1.38c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 1022 | 52 | 5.8% | -0.8c | 1.25c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 1010 | 17 | 1.9% | -1.18c | 2.2c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 30.

## Odds API credits (100K/month plan)

Study: 512/day, projected 15362/30 days. All monitors on the key: 1958/day, projected 58742/30 days. Remaining 63629; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T16:26:41Z: 72 games (55 in 24h), quotes {'prophetx': 6624, 'novig': 676, 'kalshi': 3648, 'polymarket_us': 3796}, 5467 unmatched (145 book-games; fuzzy-matched 2), 6213 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 0, maker posted 29 filled 0, credits used 6 left 63629, 248s
- 2026-10-31T16:20:41Z: 72 games (55 in 24h), quotes {'prophetx': 6624, 'novig': 678, 'kalshi': 2838, 'polymarket_us': 2238}, 4174 unmatched (127 book-games; fuzzy-matched 1), 5766 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 35 filled 0, credits used 6 left 63647, 337s
- 2026-10-31T16:16:20Z: 72 games (55 in 24h), quotes {'prophetx': 6014, 'novig': 681, 'kalshi': 2936, 'polymarket_us': 2282}, 4216 unmatched (127 book-games; fuzzy-matched 2), 5353 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 13 filled 1, credits used 8 left 63653, 243s
- 2026-10-31T16:10:22Z: 72 games (55 in 24h), quotes {'prophetx': 6598, 'novig': 671, 'kalshi': 2374, 'polymarket_us': 2096}, 3934 unmatched (123 book-games; fuzzy-matched 2), 5580 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 6 B 0, maker posted 9 filled 2, credits used 12 left 63670, 338s
- 2026-10-31T16:00:30Z: 78 games (61 in 24h), quotes {'prophetx': 6578, 'novig': 675, 'kalshi': 2728, 'polymarket_us': 1958}, 3582 unmatched (114 book-games; fuzzy-matched 1), 4987 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 30 B 0, maker posted 49 filled 1, credits used 6 left 63693, 186s
- 2026-10-31T15:55:33Z: 81 games (64 in 24h), quotes {'prophetx': 3890, 'novig': 647, 'kalshi': 3922, 'polymarket_us': 3554}, 3995 unmatched (124 book-games; fuzzy-matched 2), 4808 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 4 B 0, maker posted 1 filled 2, credits used 6 left 63714, 273s
- 2026-10-31T15:50:23Z: 81 games (64 in 24h), quotes {'prophetx': 7792, 'novig': 649, 'kalshi': 2718, 'polymarket_us': 1896}, 3510 unmatched (123 book-games; fuzzy-matched 1), 6451 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 7 B 0, maker posted 74 filled 2, credits used 8 left 63720, 214s
- 2026-10-31T15:45:27Z: 81 games (64 in 24h), quotes {'prophetx': 7772, 'novig': 650, 'kalshi': 2884, 'polymarket_us': 2172}, 3519 unmatched (124 book-games; fuzzy-matched 1), 5764 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 21 filled 2, credits used 6 left 63743, 185s
- 2026-10-31T15:40:20Z: 81 games (64 in 24h), quotes {'prophetx': 8008, 'novig': 648, 'kalshi': 3768, 'polymarket_us': 3568}, 4168 unmatched (137 book-games; fuzzy-matched 2), 6850 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 22 B 0, maker posted 1 filled 2, credits used 6 left 63750, 276s
- 2026-10-31T15:32:13Z: 81 games (64 in 24h), quotes {'prophetx': 8000, 'novig': 650, 'kalshi': 3622, 'polymarket_us': 3532}, 4124 unmatched (134 book-games; fuzzy-matched 2), 7165 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 9 filled 2, credits used 6 left 63767, 191s
