# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-04T02:43:50Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5183 | 5045 | -1.92c | 22.7% | 2059 | -1.18c | 4850 | 2456-2394-0 | -270.18u | -5.6% |  |  | criteria not met (4850/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1307 | 1269 | -3.76c | 15.1% | 289 | -3.08c | 1227 | 635-592-0 | -87.05u | -7.1% |  |  | criteria not met (1227/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 82 | 82 | -0.84c | 31.7% | 78 | -0.05c | 78 | 32-46-0 | -9.85u | -12.6% |  |  | criteria not met (78/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 6 | 6 | 0.73c | 50.0% | 6 | 1.64c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 50 | 50 | -0.67c | 30.0% | 48 | -0.1c | 48 | 21-27-0 | -2.81u | -5.9% |  |  |  |
| B ref age 5m+ | 26 | 26 | -1.52c | 30.8% | 24 | -0.37c | 25 | 8-17-0 | -8.33u | -33.3% |  |  |  |
| M move-watch: gettable (sightings) | 204 | 204 | -0.68c | 32.4% | 201 | -0.67c | 177 | 90-86-1 | -3.89u | -2.2% | 0.11c | 26s | criteria not met (177/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 100 | 100 | -0.59c | 36.0% | 99 | -0.88c | 94 | 48-45-1 | -0.88u | -0.9% | -0.11c | 28s |  |
| M gettable, price moves | 104 | 104 | -0.77c | 28.8% | 102 | -0.46c | 83 | 42-41-0 | -3.01u | -3.6% | 0.32c | 22s |  |
| M control: not gettable | 778 | 628 | -0.91c | 34.2% | 619 | -1.3c | 609 | 318-280-11 | +1.20u | 0.2% | 1.78c | 28s |  |
| M all moves | 982 | 832 | -0.86c | 33.8% | 820 | -1.15c | 786 | 408-366-12 | -2.69u | -0.3% | 1.43c | 28s |  |
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
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 0 | -0.33c | 0-0-0 | +0.00u | 0, -0.53c, +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 3 | 1 | 0.11c | 1-0-0 | +2.33u | 1, 0.11c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 38 | 14 | -0.44c | 8-6-0 | -1.50u | 9, -0.7c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 922 | 44 | 4.8% | -0.48c | 1.61c | 18-22-0 | -3.23u |  |
| MK novig fair-2c | 923 | 18 | 2.0% | -0.45c | 2.53c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2397 | 120 | 5.0% | -0.93c | 1.1c | 56-54-2 | +4.55u |  |
| MK prophetx fair-2c | 2379 | 36 | 1.5% | -0.61c | 2.04c | 15-20-0 | -3.70u |  |
| MK all fair-1c | 3319 | 164 | 4.9% | -0.81c | 1.25c | 74-76-2 | +1.32u | criteria not met (152/50 graded, CLV not positive) |
| MK all fair-2c | 3302 | 54 | 1.6% | -0.56c | 2.18c | 25-28-0 | -0.60u | criteria not met (53/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 69.

## Odds API credits (100K/month plan)

Study: 615/day, projected 18456/30 days. All monitors on the key: 2092/day, projected 62748/30 days. Remaining 93638; guard holds 75800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-04T02:40:47Z: 21 games (17 in 24h), quotes {'prophetx': 1474, 'novig': 726, 'kalshi': 1432, 'polymarket_us': 1524}, 126 unmatched (7 book-games; fuzzy-matched 2), 2800 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 93638, 183s
- 2026-11-04T02:30:48Z: 21 games (17 in 24h), quotes {'prophetx': 1472, 'novig': 722, 'kalshi': 1490, 'polymarket_us': 2102}, 184 unmatched (13 book-games; fuzzy-matched 2), 3081 side/lines, polls [NHL:slow], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 93647, 182s
- 2026-11-04T02:20:48Z: 21 games (16 in 24h), quotes {'prophetx': 1414, 'novig': 728, 'kalshi': 1500, 'polymarket_us': 1720}, 198 unmatched (13 book-games; fuzzy-matched 4), 2862 side/lines, polls [NCAAF:slow,NBA:slow], moves 2, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 93673, 200s
- 2026-11-04T02:10:34Z: 21 games (16 in 24h), quotes {'prophetx': 1338, 'novig': 720, 'kalshi': 1528, 'polymarket_us': 1468}, 222 unmatched (13 book-games; fuzzy-matched 2), 2755 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 93688, 183s
- 2026-11-04T02:00:44Z: 22 games (17 in 24h), quotes {'prophetx': 1338, 'novig': 720, 'kalshi': 1544, 'polymarket_us': 1836}, 220 unmatched (12 book-games; fuzzy-matched 2), 2801 side/lines, polls [none_due; NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 93699, 182s
- 2026-11-04T01:50:47Z: 22 games (15 in 24h), quotes {'prophetx': 1280, 'novig': 728, 'kalshi': 1560, 'polymarket_us': 1748}, 232 unmatched (12 book-games; fuzzy-matched 2), 2719 side/lines, polls [NCAAF:slow,NBA:slow,NHL:fast; NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 8 left 93701, 301s
- 2026-11-04T01:40:32Z: 22 games (15 in 24h), quotes {'prophetx': 1220, 'novig': 712, 'kalshi': 1568, 'polymarket_us': 1748}, 234 unmatched (12 book-games; fuzzy-matched 2), 2728 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 93729, 301s
- 2026-11-04T01:30:46Z: 22 games (15 in 24h), quotes {'prophetx': 1088, 'novig': 722, 'kalshi': 1578, 'polymarket_us': 1748}, 248 unmatched (12 book-games; fuzzy-matched 2), 2662 side/lines, polls [NCAAF:slow; NHL:fast], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 4 left 93742, 182s
- 2026-11-04T01:20:54Z: 22 games (14 in 24h), quotes {'prophetx': 1156, 'novig': 726, 'kalshi': 1600, 'polymarket_us': 1618}, 274 unmatched (12 book-games; fuzzy-matched 4), 2478 side/lines, polls [NBA:slow,NHL:fast; NHL:fast], moves 2, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 93755, 301s
- 2026-11-04T01:10:42Z: 23 games (15 in 24h), quotes {'prophetx': 1006, 'novig': 722, 'kalshi': 1604, 'polymarket_us': 1618}, 262 unmatched (11 book-games; fuzzy-matched 2), 2484 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 16 B 0, maker posted 0 filled 0, credits used 4 left 93770, 301s
