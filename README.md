# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T15:44:56Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2399 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1881 | 941-940-0 | -117.27u | -6.2% |  |  | criteria not met (1881/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 625 | 397 | -5.93c | 18.6% | 79 | -3.91c | 397 | 194-203-0 | -31.33u | -7.9% |  |  | criteria not met (397/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 38 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 25 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 93 | 71 | -0.71c | 35.2% | 70 | -0.69c | 71 | 41-30-0 | +8.93u | 12.6% | 0.22c | 28s | criteria not met (71/50 graded, CLV not positive) |
| M gettable, line moves | 51 | 40 | -0.66c | 37.5% | 39 | -0.89c | 40 | 23-17-0 | +4.09u | 10.2% | 0.09c | 44s |  |
| M gettable, price moves | 42 | 31 | -0.76c | 32.3% | 31 | -0.44c | 31 | 18-13-0 | +4.84u | 15.6% | 0.39c | 21s |  |
| M control: not gettable | 356 | 184 | -0.64c | 33.2% | 180 | -1.17c | 189 | 97-89-3 | -3.24u | -1.7% | 1.82c | 148s |  |
| M all moves | 449 | 255 | -0.66c | 33.7% | 250 | -1.03c | 260 | 138-119-3 | +5.69u | 2.2% | 1.45c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 323 | 145 | -0.09c | 22.1% | 18 | -0.21c | 146 | 69-77-0 | +97.83u | 67.0% |  | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J2 B, NBA | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 5 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| D1 B, unders (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 2 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 7.9% | -0.47c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 176 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 729 | 31 | 5.1% | -0.91c | 1.09c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 719 | 8 | 1.4% | -1.98c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 906 | 45 | 5.8% | -0.73c | 1.26c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 895 | 14 | 1.8% | -1.42c | 2.23c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 30.

## Odds API credits (100K/month plan)

Study: 501/day, projected 15036/30 days. All monitors on the key: 1943/day, projected 58287/30 days. Remaining 63750; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T15:40:20Z: 81 games (64 in 24h), quotes {'prophetx': 8008, 'novig': 648, 'kalshi': 3768, 'polymarket_us': 3568}, 4168 unmatched (137 book-games; fuzzy-matched 2), 6850 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 22 B 0, maker posted 1 filled 2, credits used 6 left 63750, 276s
- 2026-10-31T15:32:13Z: 81 games (64 in 24h), quotes {'prophetx': 8000, 'novig': 650, 'kalshi': 3622, 'polymarket_us': 3532}, 4124 unmatched (134 book-games; fuzzy-matched 2), 7165 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 9 filled 2, credits used 6 left 63767, 191s
- 2026-10-31T15:26:29Z: 81 games (64 in 24h), quotes {'prophetx': 7968, 'novig': 648, 'kalshi': 2826, 'polymarket_us': 2210}, 3506 unmatched (124 book-games; fuzzy-matched 1), 5960 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 11 B 0, maker posted 20 filled 1, credits used 8 left 63773, 325s
- 2026-10-31T15:20:43Z: 81 games (64 in 24h), quotes {'prophetx': 7968, 'novig': 646, 'kalshi': 3740, 'polymarket_us': 2708}, 3669 unmatched (131 book-games; fuzzy-matched 2), 6523 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 0, maker posted 21 filled 1, credits used 6 left 63800, 330s
- 2026-10-31T15:17:16Z: 81 games (64 in 24h), quotes {'prophetx': 7692, 'novig': 644, 'kalshi': 3326, 'polymarket_us': 3132}, 3626 unmatched (126 book-games; fuzzy-matched 2), 6447 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 80 filled 0, credits used 6 left 63806, 187s
- 2026-10-31T15:10:20Z: 81 games (64 in 24h), quotes {'prophetx': 7974, 'novig': 645, 'kalshi': 3990, 'polymarket_us': 2808}, 3765 unmatched (132 book-games; fuzzy-matched 4), 6705 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 11, new A 36 B 0, maker posted 15 filled 1, credits used 12 left 63821, 395s
- 2026-10-31T15:01:58Z: 81 games (64 in 24h), quotes {'prophetx': 7974, 'novig': 652, 'kalshi': 2852, 'polymarket_us': 2164}, 3467 unmatched (124 book-games; fuzzy-matched 1), 5888 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 12 filled 2, credits used 8 left 63842, 204s
- 2026-10-31T14:56:13Z: 81 games (64 in 24h), quotes {'prophetx': 7960, 'novig': 646, 'kalshi': 3678, 'polymarket_us': 3562}, 4158 unmatched (136 book-games; fuzzy-matched 2), 7017 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 23 B 0, maker posted 17 filled 0, credits used 6 left 63863, 328s
- 2026-10-31T14:50:43Z: 79 games (64 in 24h), quotes {'prophetx': 3018, 'novig': 640, 'kalshi': 2356, 'polymarket_us': 1562}, 3345 unmatched (109 book-games; fuzzy-matched 1), 2533 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 63869, 309s
- 2026-10-31T14:46:05Z: 79 games (64 in 24h), quotes {'prophetx': 7912, 'novig': 647, 'kalshi': 2946, 'polymarket_us': 2216}, 3638 unmatched (124 book-games; fuzzy-matched 1), 6857 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 75 filled 0, credits used 6 left 63888, 256s
