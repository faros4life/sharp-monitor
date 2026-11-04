# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-04T01:15:43Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5139 | 5036 | -1.92c | 22.7% | 2053 | -1.18c | 4850 | 2456-2394-0 | -270.18u | -5.6% |  |  | criteria not met (4850/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1300 | 1269 | -3.76c | 15.1% | 289 | -3.08c | 1227 | 635-592-0 | -87.05u | -7.1% |  |  | criteria not met (1227/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 82 | 82 | -0.84c | 31.7% | 78 | -0.05c | 78 | 32-46-0 | -9.85u | -12.6% |  |  | criteria not met (78/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 6 | 6 | 0.73c | 50.0% | 6 | 1.64c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 50 | 50 | -0.67c | 30.0% | 48 | -0.1c | 48 | 21-27-0 | -2.81u | -5.9% |  |  |  |
| B ref age 5m+ | 26 | 26 | -1.52c | 30.8% | 24 | -0.37c | 25 | 8-17-0 | -8.33u | -33.3% |  |  |  |
| M move-watch: gettable (sightings) | 204 | 202 | -0.71c | 31.7% | 199 | -0.67c | 177 | 90-86-1 | -3.89u | -2.2% | 0.1c | 26s | criteria not met (177/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 100 | 99 | -0.61c | 35.4% | 98 | -0.85c | 94 | 48-45-1 | -0.88u | -0.9% | -0.09c | 28s |  |
| M gettable, price moves | 104 | 103 | -0.8c | 28.2% | 101 | -0.49c | 83 | 42-41-0 | -3.01u | -3.6% | 0.29c | 22s |  |
| M control: not gettable | 774 | 627 | -0.92c | 34.3% | 618 | -1.31c | 609 | 318-280-11 | +1.20u | 0.2% | 1.77c | 28s |  |
| M all moves | 978 | 829 | -0.87c | 33.7% | 817 | -1.15c | 786 | 408-366-12 | -2.69u | -0.3% | 1.43c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 702 | 693 | 3.69c | 28.0% | 130 | 3.61c | 678 | 293-385-0 | +308.05u | 45.4% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 41 | 39 | -0.17c | 15-24-0 | -7.83u | 26, -0.42c, -3.16u | not enough yet |
| J2 B, NBA | 28 | 28 | -0.13c | 10-18-0 | -7.29u | 16, -0.43c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 26 | 25 | -0.26c | 11-14-0 | -2.13u | 18, -0.61c, +2.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 80 | 77 | -0.78c | 35-41-1 | -7.92u | 47, -1.0c, -5.27u | negative |
| D1 B, unders (descriptive) | 8 | 6 | 0.61c | 4-2-0 | +2.27u | 6, 0.61c, +2.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 0 | -0.55c | 0-0-0 | +0.00u | 0, -0.88c, +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 3 | 1 | 0.11c | 1-0-0 | +2.33u | 1, 0.11c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 38 | 14 | -0.44c | 8-6-0 | -1.50u | 9, -0.88c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 922 | 44 | 4.8% | -0.48c | 1.61c | 18-22-0 | -3.23u |  |
| MK novig fair-2c | 923 | 18 | 2.0% | -0.45c | 2.54c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2397 | 120 | 5.0% | -0.93c | 1.1c | 56-54-2 | +4.55u |  |
| MK prophetx fair-2c | 2379 | 36 | 1.5% | -0.61c | 2.04c | 15-20-0 | -3.70u |  |
| MK all fair-1c | 3319 | 164 | 4.9% | -0.81c | 1.25c | 74-76-2 | +1.32u | criteria not met (152/50 graded, CLV not positive) |
| MK all fair-2c | 3302 | 54 | 1.6% | -0.56c | 2.18c | 25-28-0 | -0.60u | criteria not met (53/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 69.

## Odds API credits (100K/month plan)

Study: 616/day, projected 18491/30 days. All monitors on the key: 2091/day, projected 62743/30 days. Remaining 93770; guard holds 75800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-04T01:10:42Z: 23 games (15 in 24h), quotes {'prophetx': 1006, 'novig': 722, 'kalshi': 1604, 'polymarket_us': 1618}, 262 unmatched (11 book-games; fuzzy-matched 2), 2484 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 16 B 0, maker posted 0 filled 0, credits used 4 left 93770, 301s
- 2026-11-04T01:00:54Z: 24 games (14 in 24h), quotes {'prophetx': 1004, 'novig': 726, 'kalshi': 1610, 'polymarket_us': 1618}, 196 unmatched (10 book-games; fuzzy-matched 4), 2565 side/lines, polls [NBA:slow; NCAAF:fast,NHL:fast], moves 6, new A 9 B 0, maker posted 0 filled 0, credits used 6 left 93792, 236s
- 2026-11-04T00:54:42Z: 24 games (13 in 24h), quotes {'prophetx': 1022, 'novig': 702, 'kalshi': 1606, 'polymarket_us': 1446}, 192 unmatched (10 book-games; fuzzy-matched 2), 2556 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 3 B 1, maker posted 11 filled 0, credits used 4 left 93807, 249s
- 2026-11-04T00:50:48Z: 24 games (13 in 24h), quotes {'prophetx': 1022, 'novig': 698, 'kalshi': 1604, 'polymarket_us': 1446}, 194 unmatched (10 book-games; fuzzy-matched 2), 2535 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 11 B 0, maker posted 8 filled 0, credits used 4 left 93821, 183s
- 2026-11-04T00:40:50Z: 24 games (13 in 24h), quotes {'prophetx': 820, 'novig': 706, 'kalshi': 1574, 'polymarket_us': 1406}, 200 unmatched (10 book-games; fuzzy-matched 2), 2414 side/lines, polls [NCAAF:fast,NBA:slow,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 4 filled 0, credits used 10 left 93834, 301s
- 2026-11-04T00:30:53Z: 25 games (10 in 24h), quotes {'prophetx': 790, 'novig': 650, 'kalshi': 1554, 'polymarket_us': 1446}, 194 unmatched (9 book-games; fuzzy-matched 2), 2428 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 1, new A 19 B 0, maker posted 6 filled 0, credits used 4 left 93853, 196s
- 2026-11-04T00:21:48Z: 25 games (8 in 24h), quotes {'prophetx': 592, 'novig': 524, 'kalshi': 1494, 'polymarket_us': 860}, 202 unmatched (9 book-games; fuzzy-matched 2), 2014 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 93873, 249s
- 2026-11-04T00:16:49Z: 25 games (8 in 24h), quotes {'prophetx': 520, 'novig': 520, 'kalshi': 1446, 'polymarket_us': 860}, 196 unmatched (9 book-games; fuzzy-matched 2), 1979 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 93888, 248s
- 2026-11-04T00:10:56Z: 25 games (8 in 24h), quotes {'prophetx': 520, 'novig': 524, 'kalshi': 1440, 'polymarket_us': 860}, 212 unmatched (9 book-games; fuzzy-matched 2), 1959 side/lines, polls [NCAAF:fast,NBA:slow,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 10 left 93892, 301s
- 2026-11-04T00:00:55Z: 32 games (16 in 24h), quotes {'prophetx': 520, 'novig': 328, 'kalshi': 1432, 'polymarket_us': 860}, 0 unmatched (0 book-games; fuzzy-matched 4), 2154 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 4, new A 17 B 0, maker posted 0 filled 0, credits used 8 left 93922, 301s
