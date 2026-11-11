# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T02:48:21Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8949 | 8706 | -1.62c | 24.3% | 3800 | -1.05c | 8300 | 4291-4009-0 | -277.65u | -3.3% |  |  | criteria not met (8300/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2021 | 1931 | -3.12c | 19.1% | 424 | -2.68c | 1827 | 940-887-0 | -143.32u | -7.8% |  |  | criteria not met (1827/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 155 | 152 | -0.78c | 30.3% | 142 | 0.13c | 143 | 65-78-0 | -5.23u | -3.7% |  |  | criteria not met (143/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 13 | 7-6-0 | +1.63u | 12.5% |  |  |  |
| B ref age 1-5m | 88 | 87 | -0.85c | 29.9% | 83 | 0.05c | 81 | 37-44-0 | -2.25u | -2.8% |  |  |  |
| B ref age 5m+ | 53 | 51 | -0.84c | 31.4% | 45 | 0.0c | 49 | 21-28-0 | -4.61u | -9.4% |  |  |  |
| M move-watch: gettable (sightings) | 419 | 411 | -0.63c | 34.8% | 409 | -0.52c | 385 | 201-179-5 | +3.19u | 0.8% | 0.2c | 27s | criteria not met (385/50 graded, CLV not positive) |
| M gettable, line moves | 214 | 211 | -0.79c | 34.1% | 210 | -0.79c | 203 | 103-96-4 | -2.26u | -1.1% | -0.17c | 28s |  |
| M gettable, price moves | 205 | 200 | -0.46c | 35.5% | 199 | -0.24c | 182 | 98-83-1 | +5.45u | 3.0% | 0.6c | 26s |  |
| M control: not gettable | 1690 | 1338 | -0.79c | 35.9% | 1311 | -1.21c | 1317 | 656-640-21 | -60.41u | -4.6% | 1.91c | 184s |  |
| M all moves | 2109 | 1749 | -0.75c | 35.7% | 1720 | -1.05c | 1702 | 857-819-26 | -57.22u | -3.4% | 1.57c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1070 | 1066 | 2.52c | 26.8% | 227 | 2.64c | 1058 | 473-585-0 | +285.80u | 27.0% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 102 | 92 | 0.12c | 43-49-0 | -1.68u | 63, -0.07c, -6.36u | negative |
| J2 B, NBA | 70 | 63 | 0.22c | 30-33-0 | -0.21u | 39, -0.01c, +0.64u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 54 | -0.01c | 26-28-0 | +0.30u | 43, -0.31c, +0.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 242 | 226 | -0.6c | 115-108-3 | -0.42u | 133, -0.62c, -8.55u | negative |
| D1 B, unders (descriptive) | 33 | 29 | 0.45c | 18-11-0 | +8.54u | 27, 0.42c, +6.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 19 | -0.24c | 7-12-0 | -4.02u | 17, -0.33c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 14 | -0.39c | 8-5-1 | +0.03u | 10, -0.59c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 15 | 13 | 0.36c | 6-7-0 | +0.79u | 12, 0.35c, -0.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 91 | 73 | -0.19c | 39-32-2 | -1.92u | 41, -0.24c, -1.61u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2336 | 96 | 4.1% | -0.61c | 1.58c | 47-42-0 | +6.98u |  |
| MK novig fair-2c | 2331 | 37 | 1.6% | -0.16c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5331 | 255 | 4.8% | -1.05c | 1.1c | 116-122-5 | -0.76u |  |
| MK prophetx fair-2c | 5293 | 89 | 1.7% | -0.63c | 2.05c | 39-42-0 | +0.30u |  |
| MK all fair-1c | 7667 | 351 | 4.6% | -0.93c | 1.25c | 163-164-5 | +6.22u | criteria not met (332/50 graded, CLV not positive) |
| MK all fair-2c | 7624 | 126 | 1.7% | -0.49c | 2.19c | 59-53-0 | +11.38u | criteria not met (112/50 graded, CLV not positive) |

A and B on the same side/line: 125.

## Odds API credits (100K/month plan)

Study: 647/day, projected 19405/30 days. All monitors on the key: 2388/day, projected 71625/30 days. Remaining 74763; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T02:44:48Z: 18 games (16 in 24h), quotes {'prophetx': 1092, 'novig': 726, 'kalshi': 1256, 'polymarket_us': 1496}, 340 unmatched (10 book-games; fuzzy-matched 3), 2299 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 74763, 213s
- 2026-11-11T02:40:19Z: 18 games (16 in 24h), quotes {'prophetx': 1092, 'novig': 718, 'kalshi': 1276, 'polymarket_us': 1554}, 360 unmatched (11 book-games; fuzzy-matched 3), 2328 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 74782, 182s
- 2026-11-11T02:32:32Z: 17 games (13 in 24h), quotes {'prophetx': 1082, 'novig': 730, 'kalshi': 1306, 'polymarket_us': 1554}, 517 unmatched (14 book-games; fuzzy-matched 6), 2176 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 3, new A 8 B 0, maker posted 5 filled 0, credits used 10 left 74792, 301s
- 2026-11-11T02:21:51Z: 17 games (13 in 24h), quotes {'prophetx': 808, 'novig': 726, 'kalshi': 1344, 'polymarket_us': 1400}, 543 unmatched (15 book-games; fuzzy-matched 3), 2002 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 38 B 0, maker posted 15 filled 0, credits used 4 left 74826, 183s
- 2026-11-11T02:12:09Z: 17 games (13 in 24h), quotes {'prophetx': 912, 'novig': 724, 'kalshi': 1374, 'polymarket_us': 1244}, 577 unmatched (15 book-games; fuzzy-matched 3), 1952 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 8 left 74856, 302s
- 2026-11-11T02:01:58Z: 19 games (14 in 24h), quotes {'prophetx': 806, 'novig': 724, 'kalshi': 1412, 'polymarket_us': 1400}, 467 unmatched (13 book-games; fuzzy-matched 6), 2184 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 13 B 1, maker posted 4 filled 0, credits used 10 left 74884, 301s
- 2026-11-11T01:51:54Z: 19 games (14 in 24h), quotes {'prophetx': 1002, 'novig': 720, 'kalshi': 1412, 'polymarket_us': 1630}, 469 unmatched (13 book-games; fuzzy-matched 3), 2374 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 16 filled 0, credits used 4 left 74914, 182s
- 2026-11-11T01:42:12Z: 19 games (14 in 24h), quotes {'prophetx': 1002, 'novig': 722, 'kalshi': 1430, 'polymarket_us': 1630}, 493 unmatched (13 book-games; fuzzy-matched 3), 2370 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 8 left 74927, 322s
- 2026-11-11T01:32:11Z: 19 games (14 in 24h), quotes {'prophetx': 1002, 'novig': 726, 'kalshi': 1448, 'polymarket_us': 1630}, 505 unmatched (13 book-games; fuzzy-matched 3), 2373 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 5 filled 0, credits used 10 left 74944, 301s
- 2026-11-11T01:22:11Z: 19 games (14 in 24h), quotes {'prophetx': 940, 'novig': 718, 'kalshi': 1460, 'polymarket_us': 1630}, 519 unmatched (13 book-games; fuzzy-matched 3), 2371 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 11 B 2, maker posted 7 filled 0, credits used 8 left 74975, 301s
