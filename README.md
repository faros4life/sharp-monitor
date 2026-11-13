# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-13T04:45:28Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 10154 | 9773 | -1.62c | 24.5% | 4232 | -1.09c | 9670 | 5033-4637-0 | -293.52u | -3.0% |  |  | criteria not met (9670/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2380 | 2197 | -3.1c | 19.5% | 495 | -2.84c | 2185 | 1121-1064-0 | -173.88u | -8.0% |  |  | criteria not met (2185/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 177 | 175 | -0.8c | 31.4% | 164 | 0.15c | 172 | 74-98-0 | -14.98u | -8.7% |  |  | criteria not met (172/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 16 | 16 | -0.11c | 31.2% | 16 | 1.04c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 98 | 96 | -0.86c | 32.3% | 91 | 0.08c | 95 | 43-52-0 | -3.31u | -3.5% |  |  |  |
| B ref age 5m+ | 63 | 63 | -0.9c | 30.2% | 57 | 0.02c | 62 | 24-38-0 | -11.29u | -18.2% |  |  |  |
| M move-watch: gettable (sightings) | 468 | 464 | -0.6c | 35.3% | 462 | -0.54c | 459 | 234-220-5 | -7.38u | -1.6% | 0.21c | 28s | criteria not met (459/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 241 | 239 | -0.74c | 35.6% | 238 | -0.78c | 237 | 115-118-4 | -13.44u | -5.7% | -0.14c | 28s |  |
| M gettable, price moves | 227 | 225 | -0.44c | 35.1% | 224 | -0.28c | 222 | 119-102-1 | +6.07u | 2.7% | 0.59c | 26s |  |
| M control: not gettable | 1864 | 1490 | -0.82c | 35.6% | 1461 | -1.24c | 1518 | 756-738-24 | -69.87u | -4.6% | 1.88c | 184s |  |
| M all moves | 2332 | 1954 | -0.76c | 35.6% | 1923 | -1.07c | 1977 | 990-958-29 | -77.25u | -3.9% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1118 | 1108 | 2.6c | 27.8% | 234 | 2.42c | 1096 | 494-602-0 | +305.17u | 27.8% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 120 | 116 | 0.12c | 50-66-0 | -10.55u | 76, -0.14c, -15.21u | negative |
| J2 B, NBA | 86 | 84 | 0.26c | 36-48-0 | -8.12u | 50, 0.01c, -8.26u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 70 | 66 | 0.04c | 30-36-0 | -2.89u | 50, -0.4c, -4.15u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 277 | 271 | -0.59c | 131-137-3 | -14.72u | 152, -0.68c, -14.12u | negative |
| D1 B, unders (descriptive) | 44 | 41 | 0.5c | 20-21-0 | +0.67u | 38, 0.45c, -0.54u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.3c | 9-5-1 | +0.53u | 11, -0.47c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 19 | 18 | 0.53c | 8-10-0 | -0.08u | 17, 0.53c, -1.23u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 105 | 102 | -0.29c | 56-44-2 | +1.82u | 54, -0.4c, -0.55u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2742 | 117 | 4.3% | -0.57c | 1.58c | 58-55-0 | +5.27u |  |
| MK novig fair-2c | 2731 | 48 | 1.8% | -0.08c | 2.52c | 26-20-0 | +8.76u |  |
| MK prophetx fair-1c | 5922 | 281 | 4.7% | -1.08c | 1.1c | 131-140-5 | -3.11u |  |
| MK prophetx fair-2c | 5882 | 103 | 1.8% | -0.57c | 2.04c | 49-53-0 | +0.22u |  |
| MK all fair-1c | 8664 | 398 | 4.6% | -0.93c | 1.25c | 189-195-5 | +2.16u | criteria not met (389/50 graded, CLV not positive) |
| MK all fair-2c | 8613 | 151 | 1.8% | -0.41c | 2.19c | 75-73-0 | +8.98u | criteria not met (148/50 graded, CLV not positive) |

A and B on the same side/line: 147.

## Odds API credits (100K/month plan)

Study: 653/day, projected 19591/30 days. All monitors on the key: 2445/day, projected 73359/30 days. Remaining 68847; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-13T04:42:24Z: 14 games (14 in 24h), quotes {'prophetx': 1476, 'novig': 728, 'kalshi': 976, 'polymarket_us': 1696}, 188 unmatched (6 book-games; fuzzy-matched 0), 2642 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 68847, 183s
- 2026-11-13T04:32:23Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 728, 'kalshi': 998, 'polymarket_us': 1696}, 206 unmatched (7 book-games; fuzzy-matched 0), 2638 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 68856, 183s
- 2026-11-13T04:22:46Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 724, 'kalshi': 1032, 'polymarket_us': 1694}, 240 unmatched (8 book-games; fuzzy-matched 0), 2638 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 68876, 181s
- 2026-11-13T04:12:21Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 718, 'kalshi': 1064, 'polymarket_us': 1434}, 272 unmatched (9 book-games; fuzzy-matched 0), 2512 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 68891, 183s
- 2026-11-13T04:02:10Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 720, 'kalshi': 1090, 'polymarket_us': 1694}, 296 unmatched (9 book-games; fuzzy-matched 0), 2638 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 68900, 182s
- 2026-11-13T03:52:42Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 726, 'kalshi': 1104, 'polymarket_us': 1678}, 310 unmatched (9 book-games; fuzzy-matched 0), 2599 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 3, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 68909, 183s
- 2026-11-13T03:42:52Z: 14 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 726, 'kalshi': 1112, 'polymarket_us': 1694}, 318 unmatched (9 book-games; fuzzy-matched 0), 2597 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 68933, 181s
- 2026-11-13T03:32:23Z: 14 games (13 in 24h), quotes {'prophetx': 1448, 'novig': 720, 'kalshi': 1136, 'polymarket_us': 1694}, 340 unmatched (10 book-games; fuzzy-matched 0), 2597 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 26 B 1, maker posted 0 filled 0, credits used 6 left 68946, 182s
- 2026-11-13T03:22:45Z: 14 games (13 in 24h), quotes {'prophetx': 1352, 'novig': 722, 'kalshi': 1152, 'polymarket_us': 1566}, 356 unmatched (11 book-games; fuzzy-matched 0), 2489 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 68978, 182s
- 2026-11-13T03:12:21Z: 14 games (12 in 24h), quotes {'prophetx': 1204, 'novig': 724, 'kalshi': 1192, 'polymarket_us': 1434}, 396 unmatched (13 book-games; fuzzy-matched 0), 2336 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 68987, 184s
