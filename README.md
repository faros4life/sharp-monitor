# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T23:52:42Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5040 | 4850 | -1.95c | 22.6% | 1942 | -1.21c | 4850 | 2456-2394-0 | -270.18u | -5.6% |  |  | criteria not met (4850/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1269 | 1227 | -3.79c | 14.9% | 276 | -3.08c | 1227 | 635-592-0 | -87.05u | -7.1% |  |  | criteria not met (1227/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 81 | 78 | -0.79c | 32.1% | 74 | 0.04c | 78 | 32-46-0 | -9.85u | -12.6% |  |  | criteria not met (78/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 6 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 49 | 48 | -0.56c | 31.2% | 46 | 0.07c | 48 | 21-27-0 | -2.81u | -5.9% |  |  |  |
| B ref age 5m+ | 26 | 25 | -1.49c | 32.0% | 23 | -0.37c | 25 | 8-17-0 | -8.33u | -33.3% |  |  |  |
| M move-watch: gettable (sightings) | 203 | 177 | -0.71c | 32.8% | 174 | -0.68c | 177 | 90-86-1 | -3.89u | -2.2% | 0.06c | 26s | criteria not met (177/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 100 | 94 | -0.58c | 35.1% | 93 | -0.84c | 94 | 48-45-1 | -0.88u | -0.9% | -0.1c | 28s |  |
| M gettable, price moves | 103 | 83 | -0.87c | 30.1% | 81 | -0.49c | 83 | 42-41-0 | -3.01u | -3.6% | 0.25c | 22s |  |
| M control: not gettable | 764 | 593 | -0.91c | 34.2% | 583 | -1.31c | 609 | 318-280-11 | +1.20u | 0.2% | 1.82c | 28s |  |
| M all moves | 967 | 770 | -0.86c | 33.9% | 757 | -1.17c | 786 | 408-366-12 | -2.69u | -0.3% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 694 | 677 | 3.62c | 27.9% | 128 | 3.72c | 678 | 293-385-0 | +308.05u | 45.4% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 41 | 39 | 0.0c | 15-24-0 | -7.83u | 26, -0.17c, -3.16u | not enough yet |
| J2 B, NBA | 28 | 28 | -0.13c | 10-18-0 | -7.29u | 16, -0.43c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 26 | 25 | -0.01c | 11-14-0 | -2.13u | 18, -0.27c, +2.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 80 | 77 | -0.74c | 35-41-1 | -7.92u | 47, -0.92c, -5.27u | negative |
| D1 B, unders (descriptive) | 8 | 6 | 0.63c | 4-2-0 | +2.27u | 6, 0.63c, +2.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 2 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 37 | 14 | -0.49c | 8-6-0 | -1.50u | 9, -0.66c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 916 | 44 | 5.0% | -0.4c | 1.63c | 18-22-0 | -3.23u |  |
| MK novig fair-2c | 916 | 18 | 2.0% | -0.45c | 2.55c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2389 | 120 | 5.1% | -0.92c | 1.1c | 56-54-2 | +4.55u |  |
| MK prophetx fair-2c | 2371 | 36 | 1.5% | -0.6c | 2.04c | 15-20-0 | -3.70u |  |
| MK all fair-1c | 3305 | 164 | 5.1% | -0.78c | 1.23c | 74-76-2 | +1.32u | criteria not met (152/50 graded, CLV not positive) |
| MK all fair-2c | 3287 | 54 | 1.7% | -0.55c | 2.17c | 25-28-0 | -0.60u | criteria not met (53/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 68.

## Odds API credits (100K/month plan)

Study: 613/day, projected 18392/30 days. All monitors on the key: 2083/day, projected 62488/30 days. Remaining 93947; guard holds 75800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T23:50:42Z: 31 games (13 in 24h), quotes {'prophetx': 624, 'novig': 370, 'kalshi': 1424, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2074 side/lines, polls [NBA:slow; NCAAF:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 26 filled 4, credits used 6 left 93947, 121s
- 2026-11-03T23:40:42Z: 31 games (13 in 24h), quotes {'prophetx': 624, 'novig': 370, 'kalshi': 1422, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2072 side/lines, polls [none_due; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 5, new A 1 B 0, maker posted 5 filled 0, credits used 8 left 93955, 477s
- 2026-11-03T23:30:45Z: 31 games (13 in 24h), quotes {'prophetx': 624, 'novig': 372, 'kalshi': 1426, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2084 side/lines, polls [none_due; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 3, new A 0 B 0, maker posted 20 filled 1, credits used 8 left 93983, 417s
- 2026-11-03T23:20:54Z: 31 games (13 in 24h), quotes {'prophetx': 590, 'novig': 368, 'kalshi': 1436, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2080 side/lines, polls [NBA:slow; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 14 filled 1, credits used 10 left 94003, 407s
- 2026-11-03T23:10:34Z: 31 games (13 in 24h), quotes {'prophetx': 624, 'novig': 370, 'kalshi': 1438, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2098 side/lines, polls [none_due; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 4 filled 0, credits used 8 left 94022, 451s
- 2026-11-03T23:00:47Z: 31 games (13 in 24h), quotes {'prophetx': 492, 'novig': 370, 'kalshi': 1446, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2036 side/lines, polls [none_due; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 0 filled 0, credits used 8 left 94046, 404s
- 2026-11-03T22:50:51Z: 31 games (13 in 24h), quotes {'prophetx': 624, 'novig': 372, 'kalshi': 1444, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2102 side/lines, polls [NBA:slow; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 79 filled 0, credits used 10 left 94063, 400s
- 2026-11-03T22:40:45Z: 31 games (13 in 24h), quotes {'prophetx': 618, 'novig': 374, 'kalshi': 1424, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2082 side/lines, polls [none_due; NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 16 filled 0, credits used 8 left 94080, 415s
- 2026-11-03T22:30:48Z: 31 games (13 in 24h), quotes {'prophetx': 618, 'novig': 376, 'kalshi': 1450, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2072 side/lines, polls [NCAAF:fast,NBA:slow,NHL:fast; NCAAF:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 4 filled 0, credits used 10 left 94102, 301s
- 2026-11-03T22:20:48Z: 31 games (13 in 24h), quotes {'prophetx': 618, 'novig': 376, 'kalshi': 1446, 'polymarket_us': 660}, 0 unmatched (0 book-games; fuzzy-matched 0), 2068 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 21 filled 0, credits used 4 left 94127, 141s
