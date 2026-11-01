# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T00:28:38Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3343 | 3187 | -2.15c | 21.0% | 1267 | -1.24c | 2719 | 1372-1347-0 | -158.38u | -5.8% |  |  | criteria not met (2719/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 870 | 849 | -4.06c | 13.8% | 201 | -3.03c | 767 | 393-374-0 | -50.29u | -6.6% |  |  | criteria not met (767/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 58 | 56 | -0.66c | 33.9% | 54 | 0.12c | 43 | 19-24-0 | -1.79u | -4.2% |  |  | criteria not met (43/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 3 | 2-1-0 | +1.23u | 41.1% |  |  |  |
| B ref age 1-5m | 37 | 36 | -0.62c | 30.6% | 35 | 0.05c | 28 | 13-15-0 | +0.60u | 2.2% |  |  |  |
| B ref age 5m+ | 16 | 15 | -1.17c | 40.0% | 14 | -0.28c | 12 | 4-8-0 | -3.63u | -30.3% |  |  |  |
| M move-watch: gettable (sightings) | 130 | 127 | -0.57c | 33.9% | 125 | -0.65c | 101 | 50-50-1 | -3.18u | -3.1% | 0.25c | 22s | criteria not met (101/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 70 | 69 | -0.48c | 37.7% | 68 | -0.74c | 56 | 28-27-1 | -1.30u | -2.3% | 0.07c | 26s |  |
| M gettable, price moves | 60 | 58 | -0.68c | 29.3% | 57 | -0.54c | 45 | 22-23-0 | -1.88u | -4.2% | 0.47c | 20s |  |
| M control: not gettable | 500 | 376 | -0.88c | 34.3% | 373 | -1.26c | 311 | 169-137-5 | +13.46u | 4.3% | 1.81c | 25s |  |
| M all moves | 630 | 503 | -0.8c | 34.2% | 498 | -1.11c | 412 | 219-187-6 | +10.28u | 2.5% | 1.48c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 569 | 555 | 3.68c | 27.9% | 109 | 2.75c | 487 | 222-265-0 | +215.81u | 44.3% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 19 | 5 | 0.2c | 2-3-0 | -0.78u | 4, 0.06c, +0.22u | not enough yet |
| J2 B, NBA | 9 | 2 | -0.28c | 1-1-0 | +0.10u | 1, -0.6c, +1.10u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 14 | 4 | -0.12c | 2-2-0 | +0.22u | 3, -0.3c, +1.22u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 38 | 17 | -0.57c | 4-12-1 | -8.23u | 13, -0.78c, -8.14u | not enough yet |
| D1 B, unders (descriptive) | 5 | 1 | 0.82c | 1-0-0 | +1.13u | 1, 0.82c, +1.13u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 0 | -0.8c | 0-0-0 | +0.00u | 0, -0.8c, +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 3 | -0.99c | 1-2-0 | -1.60u | 3, -1.02c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 329 | 24 | 7.5% | -0.54c | 1.68c | 9-8-0 | +1.10u |  |
| MK novig fair-2c | 328 | 10 | 3.2% | -0.45c | 2.6c | 4-3-0 | +1.42u |  |
| MK prophetx fair-1c | 1558 | 79 | 5.1% | -0.92c | 1.1c | 25-32-2 | -5.73u |  |
| MK prophetx fair-2c | 1545 | 21 | 1.4% | -0.89c | 2.04c | 5-10-0 | -4.57u |  |
| MK all fair-1c | 1887 | 103 | 5.5% | -0.84c | 1.2c | 34-40-2 | -4.63u | criteria not met (76/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1873 | 31 | 1.7% | -0.75c | 2.14c | 9-13-0 | -3.15u | criteria not met (22/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 48.

## Odds API credits (100K/month plan)

Study: 602/day, projected 18057/30 days. All monitors on the key: 2137/day, projected 64101/30 days. Remaining 99923; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T00:23:36Z: 22 games (20 in 24h), quotes {'prophetx': 1736, 'novig': 651, 'kalshi': 2234, 'polymarket_us': 1620}, 1287 unmatched (26 book-games; fuzzy-matched 0), 2825 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 12 B 0, maker posted 1 filled 0, credits used 6 left 99923, 302s
- 2026-11-01T00:20:12Z: 22 games (20 in 24h), quotes {'prophetx': 1736, 'novig': 648, 'kalshi': 1958, 'polymarket_us': 1862}, 1280 unmatched (26 book-games; fuzzy-matched 0), 2771 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 1, maker posted 7 filled 1, credits used 6 left 99948, 181s
- 2026-11-01T00:10:42Z: 25 games (23 in 24h), quotes {'prophetx': 1736, 'novig': 625, 'kalshi': 2202, 'polymarket_us': 1864}, 1087 unmatched (23 book-games; fuzzy-matched 0), 3116 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 0 filled 0, credits used 8 left 99965, 302s
- 2026-11-01T00:07:06Z: 26 games (24 in 24h), quotes {'prophetx': 1736, 'novig': 645, 'kalshi': 2204, 'polymarket_us': 1492}, 1128 unmatched (23 book-games; fuzzy-matched 0), 2930 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 25 B 0, maker posted 16 filled 0, credits used 6 left 99975, 195s
- 2026-11-01T00:01:35Z: 28 games (26 in 24h), quotes {'prophetx': 1736, 'novig': 672, 'kalshi': 2316, 'polymarket_us': 2048}, 984 unmatched (21 book-games; fuzzy-matched 0), 3486 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 46 B 0, maker posted 23 filled 1, credits used 6 left 99994, 306s
- 2026-10-31T23:55:53Z: 28 games (26 in 24h), quotes {'prophetx': 2410, 'novig': 705, 'kalshi': 2336, 'polymarket_us': 2956}, 1184 unmatched (25 book-games; fuzzy-matched 0), 4015 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 19 B 0, maker posted 9 filled 2, credits used 6 left 62303, 316s
- 2026-10-31T23:50:19Z: 28 games (26 in 24h), quotes {'prophetx': 2410, 'novig': 697, 'kalshi': 2362, 'polymarket_us': 1822}, 1207 unmatched (25 book-games; fuzzy-matched 0), 3522 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 20 B 2, maker posted 21 filled 0, credits used 14 left 62325, 302s
- 2026-10-31T23:40:22Z: 30 games (28 in 24h), quotes {'prophetx': 2542, 'novig': 687, 'kalshi': 1948, 'polymarket_us': 1976}, 1075 unmatched (23 book-games; fuzzy-matched 0), 3611 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 17 B 1, maker posted 3 filled 4, credits used 6 left 62368, 210s
- 2026-10-31T23:30:26Z: 33 games (31 in 24h), quotes {'prophetx': 2542, 'novig': 682, 'kalshi': 2426, 'polymarket_us': 2164}, 869 unmatched (20 book-games; fuzzy-matched 0), 4138 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 33 B 1, maker posted 44 filled 2, credits used 12 left 62385, 307s
- 2026-10-31T23:20:42Z: 32 games (30 in 24h), quotes {'prophetx': 3054, 'novig': 675, 'kalshi': 2500, 'polymarket_us': 2276}, 1367 unmatched (27 book-games; fuzzy-matched 0), 4273 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 13 B 2, maker posted 46 filled 4, credits used 8 left 62419, 184s
