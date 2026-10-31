# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T23:55:21Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3227 | 3016 | -2.22c | 21.0% | 1185 | -1.27c | 2712 | 1369-1343-0 | -159.00u | -5.9% |  |  | criteria not met (2712/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 853 | 825 | -4.15c | 13.6% | 194 | -3.12c | 765 | 392-373-0 | -50.21u | -6.6% |  |  | criteria not met (765/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 57 | 50 | -0.76c | 32.0% | 48 | 0.02c | 43 | 19-24-0 | -1.79u | -4.2% |  |  | criteria not met (43/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 4 | 0.84c | 50.0% | 4 | 1.73c | 3 | 2-1-0 | +1.23u | 41.1% |  |  |  |
| B ref age 1-5m | 37 | 33 | -0.55c | 30.3% | 32 | 0.08c | 28 | 13-15-0 | +0.60u | 2.2% |  |  |  |
| B ref age 5m+ | 15 | 13 | -1.78c | 30.8% | 12 | -0.71c | 12 | 4-8-0 | -3.63u | -30.3% |  |  |  |
| M move-watch: gettable (sightings) | 128 | 117 | -0.69c | 32.5% | 116 | -0.81c | 100 | 50-49-1 | -2.18u | -2.2% | 0.11c | 22s | criteria not met (100/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 69 | 63 | -0.62c | 36.5% | 62 | -0.98c | 56 | 28-27-1 | -1.30u | -2.3% | -0.05c | 26s |  |
| M gettable, price moves | 59 | 54 | -0.77c | 27.8% | 54 | -0.6c | 44 | 22-22-0 | -0.88u | -2.0% | 0.3c | 20s |  |
| M control: not gettable | 492 | 346 | -0.76c | 35.3% | 346 | -1.21c | 309 | 168-136-5 | +13.54u | 4.4% | 1.81c | 25s |  |
| M all moves | 620 | 463 | -0.75c | 34.6% | 462 | -1.11c | 409 | 218-185-6 | +11.36u | 2.8% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 564 | 550 | 3.63c | 28.0% | 109 | 2.75c | 483 | 220-263-0 | +214.30u | 44.4% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 18 | 5 | -0.05c | 2-3-0 | -0.78u | 4, -0.24c, +0.22u | not enough yet |
| J2 B, NBA | 8 | 2 | -1.16c | 1-1-0 | +0.10u | 1, -1.55c, +1.10u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 14 | 4 | -0.08c | 2-2-0 | +0.22u | 3, -0.33c, +1.22u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 36 | 16 | -1.02c | 4-11-1 | -7.23u | 12, -1.25c, -7.14u | not enough yet |
| D1 B, unders (descriptive) | 4 | 1 | 1.02c | 1-0-0 | +1.13u | 1, 1.02c, +1.13u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 0 | -0.8c | 0-0-0 | +0.00u | 0, -0.8c, +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 3 | -1.22c | 1-2-0 | -1.60u | 3, -1.31c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 317 | 23 | 7.7% | -0.6c | 1.68c | 9-8-0 | +1.10u |  |
| MK novig fair-2c | 316 | 9 | 3.0% | -0.78c | 2.59c | 4-3-0 | +1.42u |  |
| MK prophetx fair-1c | 1542 | 78 | 5.2% | -0.91c | 1.1c | 25-31-2 | -4.73u |  |
| MK prophetx fair-2c | 1529 | 20 | 1.3% | -0.88c | 2.04c | 5-10-0 | -4.57u |  |
| MK all fair-1c | 1859 | 101 | 5.6% | -0.84c | 1.21c | 34-39-2 | -3.63u | criteria not met (75/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1845 | 29 | 1.6% | -0.85c | 2.14c | 9-13-0 | -3.15u | criteria not met (22/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 45.

## Odds API credits (100K/month plan)

Study: 596/day, projected 17883/30 days. All monitors on the key: 2126/day, projected 63787/30 days. Remaining 62325; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T23:50:19Z: 28 games (26 in 24h), quotes {'prophetx': 2410, 'novig': 697, 'kalshi': 2362, 'polymarket_us': 1822}, 1207 unmatched (25 book-games; fuzzy-matched 0), 3522 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 20 B 2, maker posted 21 filled 0, credits used 14 left 62325, 302s
- 2026-10-31T23:40:22Z: 30 games (28 in 24h), quotes {'prophetx': 2542, 'novig': 687, 'kalshi': 1948, 'polymarket_us': 1976}, 1075 unmatched (23 book-games; fuzzy-matched 0), 3611 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 17 B 1, maker posted 3 filled 4, credits used 6 left 62368, 210s
- 2026-10-31T23:30:26Z: 33 games (31 in 24h), quotes {'prophetx': 2542, 'novig': 682, 'kalshi': 2426, 'polymarket_us': 2164}, 869 unmatched (20 book-games; fuzzy-matched 0), 4138 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 33 B 1, maker posted 44 filled 2, credits used 12 left 62385, 307s
- 2026-10-31T23:20:42Z: 32 games (30 in 24h), quotes {'prophetx': 3054, 'novig': 675, 'kalshi': 2500, 'polymarket_us': 2276}, 1367 unmatched (27 book-games; fuzzy-matched 0), 4273 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 13 B 2, maker posted 46 filled 4, credits used 8 left 62419, 184s
- 2026-10-31T23:15:02Z: 34 games (32 in 24h), quotes {'prophetx': 3054, 'novig': 667, 'kalshi': 2520, 'polymarket_us': 1648}, 827 unmatched (21 book-games; fuzzy-matched 0), 4321 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 23 B 2, maker posted 23 filled 5, credits used 6 left 62444, 314s
- 2026-10-31T23:08:44Z: 38 games (36 in 24h), quotes {'prophetx': 3054, 'novig': 664, 'kalshi': 2564, 'polymarket_us': 3138}, 738 unmatched (22 book-games; fuzzy-matched 0), 5183 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 26 B 0, maker posted 6 filled 0, credits used 12 left 62461, 350s
- 2026-10-31T23:00:30Z: 39 games (37 in 24h), quotes {'prophetx': 3054, 'novig': 663, 'kalshi': 2504, 'polymarket_us': 2118}, 746 unmatched (27 book-games; fuzzy-matched 0), 4495 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 38 B 0, maker posted 61 filled 0, credits used 8 left 62486, 210s
- 2026-10-31T22:54:36Z: 39 games (36 in 24h), quotes {'prophetx': 3554, 'novig': 691, 'kalshi': 2728, 'polymarket_us': 3268}, 1144 unmatched (34 book-games; fuzzy-matched 0), 5544 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 12 B 0, maker posted 5 filled 0, credits used 6 left 62505, 288s
- 2026-10-31T22:50:23Z: 39 games (36 in 24h), quotes {'prophetx': 3466, 'novig': 689, 'kalshi': 2422, 'polymarket_us': 1900}, 1096 unmatched (34 book-games; fuzzy-matched 0), 4709 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 15 filled 0, credits used 6 left 62511, 184s
- 2026-10-31T22:40:25Z: 39 games (36 in 24h), quotes {'prophetx': 3546, 'novig': 691, 'kalshi': 2338, 'polymarket_us': 1838}, 1176 unmatched (41 book-games; fuzzy-matched 0), 4677 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 7 B 1, maker posted 28 filled 1, credits used 14 left 62538, 330s
