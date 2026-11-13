# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-13T04:05:12Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 10142 | 9773 | -1.62c | 24.5% | 4232 | -1.09c | 9569 | 4980-4589-0 | -283.12u | -3.0% |  |  | criteria not met (9569/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2379 | 2197 | -3.1c | 19.5% | 495 | -2.84c | 2155 | 1111-1044-0 | -158.56u | -7.4% |  |  | criteria not met (2155/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 177 | 175 | -0.8c | 31.4% | 164 | 0.15c | 169 | 73-96-0 | -14.08u | -8.3% |  |  | criteria not met (169/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 16 | 16 | -0.11c | 31.2% | 16 | 1.04c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 98 | 96 | -0.86c | 32.3% | 91 | 0.08c | 94 | 42-52-0 | -4.42u | -4.7% |  |  |  |
| B ref age 5m+ | 63 | 63 | -0.9c | 30.2% | 57 | 0.02c | 60 | 24-36-0 | -9.29u | -15.5% |  |  |  |
| M move-watch: gettable (sightings) | 468 | 464 | -0.6c | 35.3% | 462 | -0.54c | 453 | 230-218-5 | -8.34u | -1.8% | 0.21c | 28s | criteria not met (453/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 241 | 239 | -0.74c | 35.6% | 238 | -0.78c | 233 | 113-116-4 | -13.25u | -5.7% | -0.14c | 28s |  |
| M gettable, price moves | 227 | 225 | -0.44c | 35.1% | 224 | -0.28c | 220 | 117-102-1 | +4.92u | 2.2% | 0.59c | 26s |  |
| M control: not gettable | 1864 | 1490 | -0.82c | 35.6% | 1461 | -1.24c | 1509 | 749-736-24 | -73.74u | -4.9% | 1.88c | 184s |  |
| M all moves | 2332 | 1954 | -0.76c | 35.6% | 1923 | -1.07c | 1962 | 979-954-29 | -82.08u | -4.2% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1118 | 1108 | 2.6c | 27.8% | 234 | 2.42c | 1093 | 493-600-0 | +292.40u | 26.8% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 120 | 114 | 0.12c | 50-64-0 | -8.55u | 75, -0.14c, -14.21u | negative |
| J2 B, NBA | 86 | 82 | 0.26c | 36-46-0 | -6.12u | 49, 0.01c, -7.26u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 70 | 66 | 0.04c | 30-36-0 | -2.89u | 50, -0.4c, -4.15u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 277 | 267 | -0.59c | 129-135-3 | -14.53u | 150, -0.68c, -14.03u | negative |
| D1 B, unders (descriptive) | 44 | 39 | 0.5c | 19-20-0 | +0.56u | 36, 0.45c, -0.65u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.3c | 9-5-1 | +0.53u | 11, -0.47c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 19 | 17 | 0.53c | 7-10-0 | -1.19u | 16, 0.53c, -2.34u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 105 | 100 | -0.29c | 54-44-2 | +0.67u | 53, -0.4c, -1.14u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2742 | 117 | 4.3% | -0.57c | 1.58c | 56-55-0 | +3.15u |  |
| MK novig fair-2c | 2731 | 48 | 1.8% | -0.08c | 2.52c | 25-20-0 | +7.63u |  |
| MK prophetx fair-1c | 5922 | 281 | 4.7% | -1.08c | 1.1c | 129-140-5 | -5.19u |  |
| MK prophetx fair-2c | 5882 | 103 | 1.8% | -0.57c | 2.04c | 49-53-0 | +0.22u |  |
| MK all fair-1c | 8664 | 398 | 4.6% | -0.93c | 1.25c | 185-195-5 | -2.04u | criteria not met (385/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8613 | 151 | 1.8% | -0.41c | 2.19c | 74-73-0 | +7.85u | criteria not met (147/50 graded, CLV not positive) |

A and B on the same side/line: 147.

## Odds API credits (100K/month plan)

Study: 654/day, projected 19613/30 days. All monitors on the key: 2446/day, projected 73387/30 days. Remaining 68900; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-13T04:02:10Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 720, 'kalshi': 1090, 'polymarket_us': 1694}, 296 unmatched (9 book-games; fuzzy-matched 0), 2638 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 68900, 182s
- 2026-11-13T03:52:42Z: 14 games (14 in 24h), quotes {'prophetx': 1472, 'novig': 726, 'kalshi': 1104, 'polymarket_us': 1678}, 310 unmatched (9 book-games; fuzzy-matched 0), 2599 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 3, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 68909, 183s
- 2026-11-13T03:42:52Z: 14 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 726, 'kalshi': 1112, 'polymarket_us': 1694}, 318 unmatched (9 book-games; fuzzy-matched 0), 2597 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 68933, 181s
- 2026-11-13T03:32:23Z: 14 games (13 in 24h), quotes {'prophetx': 1448, 'novig': 720, 'kalshi': 1136, 'polymarket_us': 1694}, 340 unmatched (10 book-games; fuzzy-matched 0), 2597 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 26 B 1, maker posted 0 filled 0, credits used 6 left 68946, 182s
- 2026-11-13T03:22:45Z: 14 games (13 in 24h), quotes {'prophetx': 1352, 'novig': 722, 'kalshi': 1152, 'polymarket_us': 1566}, 356 unmatched (11 book-games; fuzzy-matched 0), 2489 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 68978, 182s
- 2026-11-13T03:12:21Z: 14 games (12 in 24h), quotes {'prophetx': 1204, 'novig': 724, 'kalshi': 1192, 'polymarket_us': 1434}, 396 unmatched (13 book-games; fuzzy-matched 0), 2336 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 68987, 184s
- 2026-11-13T03:04:56Z: 15 games (11 in 24h), quotes {'prophetx': 1204, 'novig': 722, 'kalshi': 1218, 'polymarket_us': 1434}, 402 unmatched (13 book-games; fuzzy-matched 0), 2347 side/lines, polls [none_due; NHL:fast], moves 1, new A 18 B 0, maker posted 0 filled 0, credits used 2 left 68996, 188s
- 2026-11-13T02:59:04Z: 15 games (11 in 24h), quotes {'prophetx': 1074, 'novig': 728, 'kalshi': 1228, 'polymarket_us': 1202}, 290 unmatched (10 book-games; fuzzy-matched 0), 2216 side/lines, polls [none_due; NHL:fast], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 2 left 69002, 181s
- 2026-11-13T02:52:08Z: 15 games (11 in 24h), quotes {'prophetx': 1074, 'novig': 720, 'kalshi': 1222, 'polymarket_us': 1202}, 284 unmatched (11 book-games; fuzzy-matched 0), 2217 side/lines, polls [NCAAF:slow,NBA:slow; NHL:fast], moves 3, new A 7 B 1, maker posted 0 filled 0, credits used 6 left 69013, 230s
- 2026-11-13T02:42:56Z: 15 games (11 in 24h), quotes {'prophetx': 1070, 'novig': 722, 'kalshi': 1232, 'polymarket_us': 1202}, 296 unmatched (11 book-games; fuzzy-matched 0), 2193 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 3 B 0, maker posted 4 filled 0, credits used 4 left 69028, 302s
