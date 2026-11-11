# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T01:05:43Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8813 | 8533 | -1.6c | 24.4% | 3735 | -1.04c | 8300 | 4291-4009-0 | -277.65u | -3.3% |  |  | criteria not met (8300/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1978 | 1877 | -3.1c | 19.0% | 410 | -2.7c | 1827 | 940-887-0 | -143.32u | -7.8% |  |  | criteria not met (1827/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 152 | 148 | -0.82c | 29.7% | 138 | 0.1c | 143 | 65-78-0 | -5.23u | -3.7% |  |  | criteria not met (143/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 13 | 7-6-0 | +1.63u | 12.5% |  |  |  |
| B ref age 1-5m | 87 | 84 | -0.93c | 28.6% | 80 | -0.01c | 81 | 37-44-0 | -2.25u | -2.8% |  |  |  |
| B ref age 5m+ | 52 | 51 | -0.84c | 31.4% | 45 | 0.0c | 49 | 21-28-0 | -4.61u | -9.4% |  |  |  |
| M move-watch: gettable (sightings) | 417 | 406 | -0.63c | 35.0% | 404 | -0.53c | 385 | 201-179-5 | +3.19u | 0.8% | 0.2c | 27s | criteria not met (385/50 graded, CLV not positive) |
| M gettable, line moves | 213 | 208 | -0.8c | 34.1% | 207 | -0.81c | 203 | 103-96-4 | -2.26u | -1.1% | -0.18c | 28s |  |
| M gettable, price moves | 204 | 198 | -0.45c | 35.9% | 197 | -0.24c | 182 | 98-83-1 | +5.45u | 3.0% | 0.6c | 26s |  |
| M control: not gettable | 1684 | 1316 | -0.76c | 36.2% | 1287 | -1.19c | 1317 | 656-640-21 | -60.41u | -4.6% | 1.91c | 184s |  |
| M all moves | 2101 | 1722 | -0.73c | 35.9% | 1691 | -1.03c | 1702 | 857-819-26 | -57.22u | -3.4% | 1.57c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1069 | 1061 | 2.58c | 27.0% | 224 | 2.85c | 1058 | 473-585-0 | +285.80u | 27.0% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 100 | 92 | 0.07c | 43-49-0 | -1.68u | 63, -0.08c, -6.36u | negative |
| J2 B, NBA | 69 | 63 | 0.16c | 30-33-0 | -0.21u | 39, -0.03c, +0.64u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 60 | 54 | -0.1c | 26-28-0 | +0.30u | 43, -0.34c, +0.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 241 | 226 | -0.62c | 115-108-3 | -0.42u | 133, -0.62c, -8.55u | negative |
| D1 B, unders (descriptive) | 32 | 29 | 0.46c | 18-11-0 | +8.54u | 27, 0.44c, +6.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 19 | -0.41c | 7-12-0 | -4.02u | 17, -0.52c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 14 | -0.39c | 8-5-1 | +0.03u | 10, -0.59c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 14 | 13 | 0.36c | 6-7-0 | +0.79u | 12, 0.35c, -0.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 90 | 73 | -0.19c | 39-32-2 | -1.92u | 41, -0.24c, -1.61u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2312 | 96 | 4.2% | -0.57c | 1.58c | 47-42-0 | +6.98u |  |
| MK novig fair-2c | 2307 | 37 | 1.6% | -0.09c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5313 | 255 | 4.8% | -1.03c | 1.1c | 116-122-5 | -0.76u |  |
| MK prophetx fair-2c | 5275 | 88 | 1.7% | -0.58c | 2.04c | 39-42-0 | +0.30u |  |
| MK all fair-1c | 7625 | 351 | 4.6% | -0.9c | 1.25c | 163-164-5 | +6.22u | criteria not met (332/50 graded, CLV not positive) |
| MK all fair-2c | 7582 | 125 | 1.7% | -0.44c | 2.18c | 59-53-0 | +11.38u | criteria not met (112/50 graded, CLV not positive) |

A and B on the same side/line: 122.

## Odds API credits (100K/month plan)

Study: 645/day, projected 19338/30 days. All monitors on the key: 2381/day, projected 71428/30 days. Remaining 75027; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T01:01:53Z: 22 games (14 in 24h), quotes {'prophetx': 844, 'novig': 724, 'kalshi': 1498, 'polymarket_us': 1630}, 391 unmatched (10 book-games; fuzzy-matched 3), 2522 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 47 B 0, maker posted 1 filled 2, credits used 6 left 75027, 230s
- 2026-11-11T00:56:50Z: 22 games (14 in 24h), quotes {'prophetx': 1020, 'novig': 696, 'kalshi': 1500, 'polymarket_us': 1534}, 401 unmatched (10 book-games; fuzzy-matched 3), 2520 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 1, maker posted 13 filled 5, credits used 6 left 75045, 184s
- 2026-11-11T00:51:51Z: 22 games (14 in 24h), quotes {'prophetx': 852, 'novig': 698, 'kalshi': 1504, 'polymarket_us': 1534}, 405 unmatched (10 book-games; fuzzy-matched 3), 2431 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 1 filled 0, credits used 6 left 75062, 184s
- 2026-11-11T00:42:13Z: 23 games (14 in 24h), quotes {'prophetx': 1020, 'novig': 698, 'kalshi': 1484, 'polymarket_us': 1532}, 405 unmatched (10 book-games; fuzzy-matched 2), 2543 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 8 B 0, maker posted 37 filled 0, credits used 12 left 75070, 325s
- 2026-11-11T00:32:13Z: 25 games (15 in 24h), quotes {'prophetx': 924, 'novig': 695, 'kalshi': 1488, 'polymarket_us': 1532}, 322 unmatched (7 book-games; fuzzy-matched 2), 2587 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 11 B 0, maker posted 1 filled 1, credits used 12 left 75104, 328s
- 2026-11-11T00:22:00Z: 26 games (13 in 24h), quotes {'prophetx': 830, 'novig': 697, 'kalshi': 1474, 'polymarket_us': 1266}, 312 unmatched (6 book-games; fuzzy-matched 0), 2387 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 8 B 1, maker posted 4 filled 3, credits used 6 left 75143, 186s
- 2026-11-11T00:16:59Z: 26 games (13 in 24h), quotes {'prophetx': 830, 'novig': 701, 'kalshi': 1474, 'polymarket_us': 1266}, 308 unmatched (6 book-games; fuzzy-matched 0), 2380 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 10 B 1, maker posted 4 filled 3, credits used 6 left 75167, 213s
- 2026-11-11T00:12:02Z: 28 games (15 in 24h), quotes {'prophetx': 830, 'novig': 699, 'kalshi': 1482, 'polymarket_us': 1266}, 274 unmatched (4 book-games; fuzzy-matched 0), 2417 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 7 filled 0, credits used 6 left 75184, 183s
- 2026-11-11T00:02:18Z: 29 games (14 in 24h), quotes {'prophetx': 830, 'novig': 683, 'kalshi': 1454, 'polymarket_us': 1266}, 264 unmatched (3 book-games; fuzzy-matched 0), 2395 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 17 B 0, maker posted 24 filled 0, credits used 12 left 75201, 301s
- 2026-11-10T23:51:49Z: 31 games (16 in 24h), quotes {'prophetx': 1064, 'novig': 693, 'kalshi': 1448, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2790 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 3 B 0, maker posted 64 filled 4, credits used 12 left 75228, 301s
