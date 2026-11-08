# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T00:27:28Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7136 | 6942 | -1.63c | 24.0% | 3015 | -1.04c | 6768 | 3488-3280-0 | -245.67u | -3.6% |  |  | criteria not met (6768/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1609 | 1545 | -3.2c | 18.6% | 349 | -2.66c | 1468 | 757-711-0 | -107.55u | -7.3% |  |  | criteria not met (1468/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 121 | 120 | -0.98c | 29.2% | 112 | -0.02c | 120 | 53-67-0 | -7.77u | -6.5% |  |  | criteria not met (120/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 71 | 70 | -1.01c | 28.6% | 67 | -0.16c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 41 | 41 | -1.16c | 29.3% | 36 | -0.02c | 41 | 15-26-0 | -9.38u | -22.9% |  |  |  |
| M move-watch: gettable (sightings) | 334 | 305 | -0.65c | 33.8% | 303 | -0.63c | 301 | 153-144-4 | -7.57u | -2.5% | 0.16c | 26s | criteria not met (301/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 173 | 156 | -0.73c | 35.3% | 156 | -0.89c | 154 | 75-76-3 | -7.54u | -4.9% | -0.16c | 27s |  |
| M gettable, price moves | 161 | 149 | -0.58c | 32.2% | 147 | -0.36c | 147 | 78-68-1 | -0.03u | -0.0% | 0.49c | 24s |  |
| M control: not gettable | 1372 | 1020 | -0.83c | 35.2% | 1013 | -1.21c | 1001 | 488-494-19 | -65.31u | -6.5% | 1.77c | 183s |  |
| M all moves | 1706 | 1325 | -0.79c | 34.9% | 1316 | -1.07c | 1302 | 641-638-23 | -72.88u | -5.6% | 1.45c | 123s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1034 | 1029 | 2.74c | 27.1% | 221 | 2.94c | 981 | 435-546-0 | +275.02u | 28.0% | 1.03c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 74 | 73 | -0.12c | 33-40-0 | -3.88u | 49, -0.35c, -7.23u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.4c | 22-21-0 | +2.86u | 33, -0.7c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 189 | 162 | -0.71c | 77-83-2 | -9.98u | 94, -0.76c, -13.41u | negative |
| D1 B, unders (descriptive) | 21 | 21 | 0.4c | 13-8-0 | +5.89u | 20, 0.36c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 59 | 53 | -0.37c | 29-22-2 | -3.11u | 28, -0.49c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1647 | 72 | 4.4% | -0.62c | 1.59c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1645 | 26 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4358 | 208 | 4.9% | -0.95c | 1.1c | 98-92-4 | +10.60u |  |
| MK prophetx fair-2c | 4332 | 66 | 1.6% | -0.49c | 2.04c | 31-32-0 | +1.63u |  |
| MK all fair-1c | 6005 | 280 | 4.7% | -0.86c | 1.24c | 135-127-4 | +13.69u | criteria not met (266/50 graded, CLV not positive) |
| MK all fair-2c | 5977 | 92 | 1.6% | -0.46c | 2.18c | 47-42-0 | +9.28u | criteria not met (89/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 639/day, projected 19155/30 days. All monitors on the key: 2171/day, projected 65120/30 days. Remaining 84589; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T00:21:35Z: 51 games (46 in 24h), quotes {'prophetx': 3804, 'novig': 614, 'kalshi': 3218, 'polymarket_us': 2520}, 838 unmatched (28 book-games; fuzzy-matched 2), 6084 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 32 B 0, maker posted 8 filled 0, credits used 12 left 84589, 352s
- 2026-11-08T00:11:25Z: 54 games (49 in 24h), quotes {'prophetx': 3804, 'novig': 623, 'kalshi': 2162, 'polymarket_us': 1446}, 937 unmatched (31 book-games; fuzzy-matched 1), 5018 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 18 B 0, maker posted 32 filled 0, credits used 8 left 84646, 234s
- 2026-11-08T00:01:27Z: 55 games (47 in 24h), quotes {'prophetx': 3804, 'novig': 617, 'kalshi': 3248, 'polymarket_us': 2540}, 997 unmatched (31 book-games; fuzzy-matched 2), 5953 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 53 B 0, maker posted 58 filled 3, credits used 12 left 84671, 376s
- 2026-11-07T23:51:09Z: 55 games (47 in 24h), quotes {'prophetx': 4246, 'novig': 610, 'kalshi': 2454, 'polymarket_us': 1834}, 1891 unmatched (46 book-games; fuzzy-matched 2), 5206 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 9 B 0, maker posted 12 filled 0, credits used 14 left 84718, 380s
- 2026-11-07T23:40:54Z: 55 games (47 in 24h), quotes {'prophetx': 4246, 'novig': 597, 'kalshi': 2322, 'polymarket_us': 1824}, 1982 unmatched (49 book-games; fuzzy-matched 1), 5069 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 0, maker posted 48 filled 0, credits used 6 left 84760, 234s
- 2026-11-07T23:31:26Z: 55 games (47 in 24h), quotes {'prophetx': 4246, 'novig': 602, 'kalshi': 2654, 'polymarket_us': 2144}, 2212 unmatched (51 book-games; fuzzy-matched 1), 5276 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 7 B 0, maker posted 47 filled 0, credits used 12 left 84777, 331s
- 2026-11-07T23:21:21Z: 55 games (48 in 24h), quotes {'prophetx': 4246, 'novig': 604, 'kalshi': 3262, 'polymarket_us': 2746}, 2294 unmatched (56 book-games; fuzzy-matched 2), 5831 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 10 B 0, maker posted 4 filled 0, credits used 14 left 84808, 353s
- 2026-11-07T23:11:26Z: 55 games (48 in 24h), quotes {'prophetx': 4358, 'novig': 620, 'kalshi': 2224, 'polymarket_us': 1478}, 2131 unmatched (55 book-games; fuzzy-matched 0), 4901 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 84852, 184s
- 2026-11-07T23:05:35Z: 55 games (47 in 24h), quotes {'prophetx': 3934, 'novig': 618, 'kalshi': 2276, 'polymarket_us': 1794}, 2257 unmatched (56 book-games; fuzzy-matched 0), 4624 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 28 filled 0, credits used 6 left 84858, 262s
- 2026-11-07T23:01:00Z: 55 games (47 in 24h), quotes {'prophetx': 4242, 'novig': 622, 'kalshi': 2230, 'polymarket_us': 1496}, 2166 unmatched (55 book-games; fuzzy-matched 0), 4839 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 14 B 0, maker posted 39 filled 0, credits used 8 left 84879, 186s
