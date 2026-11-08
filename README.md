# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T02:14:58Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7347 | 7197 | -1.61c | 23.7% | 3139 | -1.03c | 6882 | 3551-3331-0 | -256.84u | -3.7% |  |  | criteria not met (6882/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1655 | 1612 | -3.14c | 18.1% | 359 | -2.62c | 1520 | 782-738-0 | -122.91u | -8.1% |  |  | criteria not met (1520/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 123 | 121 | -0.98c | 28.9% | 113 | -0.01c | 120 | 53-67-0 | -7.77u | -6.5% |  |  | criteria not met (120/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 72 | 71 | -1.01c | 28.2% | 68 | -0.15c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 42 | 41 | -1.16c | 29.3% | 36 | -0.02c | 41 | 15-26-0 | -9.38u | -22.9% |  |  |  |
| M move-watch: gettable (sightings) | 335 | 322 | -0.62c | 33.5% | 321 | -0.6c | 303 | 154-145-4 | -7.72u | -2.5% | 0.21c | 26s | criteria not met (303/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 173 | 168 | -0.66c | 34.5% | 169 | -0.82c | 156 | 76-77-3 | -7.69u | -4.9% | -0.06c | 27s |  |
| M gettable, price moves | 162 | 154 | -0.57c | 32.5% | 152 | -0.35c | 147 | 78-68-1 | -0.03u | -0.0% | 0.5c | 24s |  |
| M control: not gettable | 1388 | 1080 | -0.84c | 35.4% | 1071 | -1.23c | 1033 | 505-509-19 | -65.34u | -6.3% | 1.75c | 182s |  |
| M all moves | 1723 | 1402 | -0.79c | 35.0% | 1392 | -1.09c | 1336 | 659-654-23 | -73.05u | -5.5% | 1.45c | 114s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1035 | 1030 | 2.73c | 27.1% | 222 | 2.91c | 998 | 438-560-0 | +263.39u | 26.4% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 75 | 73 | -0.12c | 33-40-0 | -3.88u | 49, -0.35c, -7.23u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.4c | 22-21-0 | +2.86u | 33, -0.7c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 189 | 164 | -0.65c | 78-84-2 | -10.13u | 96, -0.67c, -13.56u | negative |
| D1 B, unders (descriptive) | 22 | 21 | 0.4c | 13-8-0 | +5.89u | 20, 0.36c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 10 | 9 | 0.42c | 4-5-0 | +0.46u | 8, 0.42c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 60 | 53 | -0.34c | 29-22-2 | -3.11u | 28, -0.4c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1696 | 73 | 4.3% | -0.62c | 1.59c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1694 | 27 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4420 | 210 | 4.8% | -0.98c | 1.1c | 98-93-4 | +9.60u |  |
| MK prophetx fair-2c | 4394 | 68 | 1.6% | -0.57c | 2.04c | 31-32-0 | +1.63u |  |
| MK all fair-1c | 6116 | 283 | 4.7% | -0.89c | 1.24c | 135-128-4 | +12.69u | criteria not met (267/50 graded, CLV not positive) |
| MK all fair-2c | 6088 | 95 | 1.6% | -0.51c | 2.17c | 47-42-0 | +9.28u | criteria not met (89/50 graded, CLV not positive) |

A and B on the same side/line: 97.

## Odds API credits (100K/month plan)

Study: 644/day, projected 19324/30 days. All monitors on the key: 2185/day, projected 65555/30 days. Remaining 84260; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T02:11:24Z: 32 games (32 in 24h), quotes {'prophetx': 2330, 'novig': 664, 'kalshi': 2286, 'polymarket_us': 1688}, 974 unmatched (31 book-games; fuzzy-matched 2), 3854 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 0, maker posted 4 filled 2, credits used 8 left 84260, 214s
- 2026-11-08T02:01:30Z: 35 games (33 in 24h), quotes {'prophetx': 2414, 'novig': 654, 'kalshi': 2696, 'polymarket_us': 2030}, 890 unmatched (28 book-games; fuzzy-matched 2), 4387 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 41 B 0, maker posted 8 filled 0, credits used 12 left 84283, 362s
- 2026-11-08T01:51:09Z: 35 games (33 in 24h), quotes {'prophetx': 2482, 'novig': 664, 'kalshi': 2816, 'polymarket_us': 2642}, 919 unmatched (28 book-games; fuzzy-matched 2), 4829 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 8 filled 0, credits used 12 left 84314, 301s
- 2026-11-08T01:42:07Z: 36 games (34 in 24h), quotes {'prophetx': 2480, 'novig': 656, 'kalshi': 2822, 'polymarket_us': 1866}, 915 unmatched (27 book-games; fuzzy-matched 2), 4434 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 1, maker posted 24 filled 0, credits used 8 left 84352, 182s
- 2026-11-08T01:35:43Z: 36 games (34 in 24h), quotes {'prophetx': 2480, 'novig': 668, 'kalshi': 2938, 'polymarket_us': 2886}, 954 unmatched (27 book-games; fuzzy-matched 2), 5044 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 16 B 1, maker posted 24 filled 1, credits used 6 left 84364, 305s
- 2026-11-08T01:31:20Z: 36 games (34 in 24h), quotes {'prophetx': 2432, 'novig': 694, 'kalshi': 2404, 'polymarket_us': 1996}, 958 unmatched (27 book-games; fuzzy-matched 2), 4172 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 4 filled 3, credits used 6 left 84381, 184s
- 2026-11-08T01:21:29Z: 36 games (34 in 24h), quotes {'prophetx': 2478, 'novig': 686, 'kalshi': 2554, 'polymarket_us': 2038}, 1024 unmatched (28 book-games; fuzzy-matched 2), 4198 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 21 B 0, maker posted 12 filled 0, credits used 14 left 84400, 328s
- 2026-11-08T01:11:16Z: 37 games (34 in 24h), quotes {'prophetx': 2310, 'novig': 690, 'kalshi': 2124, 'polymarket_us': 1748}, 1031 unmatched (28 book-games; fuzzy-matched 2), 3776 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 20 filled 0, credits used 6 left 84440, 185s
- 2026-11-08T01:01:22Z: 42 games (37 in 24h), quotes {'prophetx': 2486, 'novig': 718, 'kalshi': 2768, 'polymarket_us': 1820}, 916 unmatched (25 book-games; fuzzy-matched 2), 4354 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 17 B 0, maker posted 8 filled 0, credits used 14 left 84467, 308s
- 2026-11-08T00:51:23Z: 43 games (38 in 24h), quotes {'prophetx': 2898, 'novig': 711, 'kalshi': 2152, 'polymarket_us': 1746}, 1005 unmatched (26 book-games; fuzzy-matched 2), 4269 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 11 B 0, maker posted 12 filled 0, credits used 6 left 84500, 192s
