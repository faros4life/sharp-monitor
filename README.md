# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-04T03:23:47Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5192 | 5045 | -1.92c | 22.7% | 2059 | -1.18c | 4909 | 2486-2423-0 | -264.03u | -5.4% |  |  | criteria not met (4909/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1309 | 1269 | -3.76c | 15.1% | 289 | -3.08c | 1228 | 635-593-0 | -88.05u | -7.2% |  |  | criteria not met (1228/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 82 | 82 | -0.84c | 31.7% | 78 | -0.05c | 79 | 32-47-0 | -10.85u | -13.7% |  |  | criteria not met (79/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 6 | 6 | 0.73c | 50.0% | 6 | 1.64c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 50 | 50 | -0.67c | 30.0% | 48 | -0.1c | 48 | 21-27-0 | -2.81u | -5.9% |  |  |  |
| B ref age 5m+ | 26 | 26 | -1.52c | 30.8% | 24 | -0.37c | 25 | 8-17-0 | -8.33u | -33.3% |  |  |  |
| M move-watch: gettable (sightings) | 205 | 204 | -0.68c | 32.4% | 201 | -0.67c | 198 | 101-94-3 | -4.13u | -2.1% | 0.11c | 26s | criteria not met (198/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 100 | 100 | -0.59c | 36.0% | 99 | -0.88c | 98 | 50-46-2 | -0.19u | -0.2% | -0.11c | 28s |  |
| M gettable, price moves | 105 | 104 | -0.77c | 28.8% | 102 | -0.46c | 100 | 51-48-1 | -3.94u | -3.9% | 0.32c | 22s |  |
| M control: not gettable | 780 | 628 | -0.91c | 34.2% | 619 | -1.3c | 624 | 323-288-13 | -2.01u | -0.3% | 1.78c | 28s |  |
| M all moves | 985 | 832 | -0.86c | 33.8% | 820 | -1.15c | 822 | 424-382-16 | -6.14u | -0.7% | 1.43c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 703 | 693 | 3.69c | 28.0% | 130 | 3.61c | 678 | 293-385-0 | +308.05u | 45.4% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 41 | 39 | -0.17c | 15-24-0 | -7.83u | 26, -0.42c, -3.16u | not enough yet |
| J2 B, NBA | 28 | 28 | -0.13c | 10-18-0 | -7.29u | 16, -0.43c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 26 | 25 | -0.26c | 11-14-0 | -2.13u | 18, -0.61c, +2.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 81 | 77 | -0.78c | 35-41-1 | -7.92u | 47, -1.0c, -5.27u | negative |
| D1 B, unders (descriptive) | 8 | 7 | 0.61c | 4-3-0 | +1.27u | 7, 0.61c, +1.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 12 | -0.33c | 7-4-1 | +0.08u | 8, -0.53c, +1.23u | descriptive only |
| D4 B, NHL (descriptive) | 3 | 2 | 0.11c | 1-1-0 | +1.33u | 2, 0.11c, +1.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 38 | 35 | -0.44c | 19-14-2 | -1.74u | 17, -0.7c, -0.48u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 922 | 44 | 4.8% | -0.48c | 1.61c | 18-24-0 | -5.23u |  |
| MK novig fair-2c | 923 | 18 | 2.0% | -0.45c | 2.53c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2397 | 120 | 5.0% | -0.93c | 1.1c | 56-54-2 | +4.55u |  |
| MK prophetx fair-2c | 2379 | 36 | 1.5% | -0.61c | 2.04c | 15-20-0 | -3.70u |  |
| MK all fair-1c | 3319 | 164 | 4.9% | -0.81c | 1.25c | 74-78-2 | -0.68u | criteria not met (154/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 3302 | 54 | 1.6% | -0.56c | 2.18c | 25-28-0 | -0.60u | criteria not met (53/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 69.

## Odds API credits (100K/month plan)

Study: 614/day, projected 18427/30 days. All monitors on the key: 2092/day, projected 62760/30 days. Remaining 93577; guard holds 75800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-04T03:20:43Z: 21 games (20 in 24h), quotes {'prophetx': 1752, 'novig': 722, 'kalshi': 1376, 'polymarket_us': 1742}, 74 unmatched (3 book-games; fuzzy-matched 2), 2991 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 93577, 183s
- 2026-11-04T03:10:45Z: 21 games (20 in 24h), quotes {'prophetx': 1678, 'novig': 722, 'kalshi': 1402, 'polymarket_us': 2208}, 100 unmatched (4 book-games; fuzzy-matched 4), 3227 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 4 left 93586, 182s
- 2026-11-04T03:01:12Z: 21 games (17 in 24h), quotes {'prophetx': 1672, 'novig': 722, 'kalshi': 1424, 'polymarket_us': 2286}, 118 unmatched (4 book-games; fuzzy-matched 2), 3271 side/lines, polls [NHL:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 93599, 182s
- 2026-11-04T02:50:31Z: 21 games (17 in 24h), quotes {'prophetx': 1476, 'novig': 726, 'kalshi': 1420, 'polymarket_us': 1470}, 114 unmatched (6 book-games; fuzzy-matched 4), 2813 side/lines, polls [NCAAF:slow,NBA:slow], moves 2, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 93612, 201s
- 2026-11-04T02:40:47Z: 21 games (17 in 24h), quotes {'prophetx': 1474, 'novig': 726, 'kalshi': 1432, 'polymarket_us': 1524}, 126 unmatched (7 book-games; fuzzy-matched 2), 2800 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 93638, 183s
- 2026-11-04T02:30:48Z: 21 games (17 in 24h), quotes {'prophetx': 1472, 'novig': 722, 'kalshi': 1490, 'polymarket_us': 2102}, 184 unmatched (13 book-games; fuzzy-matched 2), 3081 side/lines, polls [NHL:slow], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 93647, 182s
- 2026-11-04T02:20:48Z: 21 games (16 in 24h), quotes {'prophetx': 1414, 'novig': 728, 'kalshi': 1500, 'polymarket_us': 1720}, 198 unmatched (13 book-games; fuzzy-matched 4), 2862 side/lines, polls [NCAAF:slow,NBA:slow], moves 2, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 93673, 200s
- 2026-11-04T02:10:34Z: 21 games (16 in 24h), quotes {'prophetx': 1338, 'novig': 720, 'kalshi': 1528, 'polymarket_us': 1468}, 222 unmatched (13 book-games; fuzzy-matched 2), 2755 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 93688, 183s
- 2026-11-04T02:00:44Z: 22 games (17 in 24h), quotes {'prophetx': 1338, 'novig': 720, 'kalshi': 1544, 'polymarket_us': 1836}, 220 unmatched (12 book-games; fuzzy-matched 2), 2801 side/lines, polls [none_due; NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 93699, 182s
- 2026-11-04T01:50:47Z: 22 games (15 in 24h), quotes {'prophetx': 1280, 'novig': 728, 'kalshi': 1560, 'polymarket_us': 1748}, 232 unmatched (12 book-games; fuzzy-matched 2), 2719 side/lines, polls [NCAAF:slow,NBA:slow,NHL:fast; NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 8 left 93701, 301s
