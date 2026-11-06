# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-06T00:44:03Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5809 | 5613 | -1.78c | 23.3% | 2433 | -1.09c | 5510 | 2805-2705-0 | -249.45u | -4.5% |  |  | criteria not met (5510/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1242 | 1229 | -3.74c | 16.3% | 273 | -2.96c | 1221 | 627-594-0 | -91.48u | -7.5% |  |  | criteria not met (1221/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 105 | 101 | -0.79c | 30.7% | 97 | -0.01c | 98 | 39-59-0 | -15.29u | -15.6% |  |  | criteria not met (98/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 60 | 59 | -0.75c | 28.8% | 57 | -0.11c | 57 | 24-33-0 | -5.62u | -9.9% |  |  |  |
| B ref age 5m+ | 36 | 33 | -1.1c | 33.3% | 31 | -0.13c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 259 | 246 | -0.74c | 30.9% | 244 | -0.71c | 237 | 122-112-3 | -4.17u | -1.8% | 0.06c | 26s | criteria not met (237/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 129 | 123 | -0.82c | 32.5% | 122 | -1.02c | 121 | 61-58-2 | -2.35u | -1.9% | -0.28c | 46s |  |
| M gettable, price moves | 130 | 123 | -0.66c | 29.3% | 122 | -0.4c | 116 | 61-54-1 | -1.82u | -1.6% | 0.39c | 22s |  |
| M control: not gettable | 951 | 750 | -0.88c | 34.1% | 746 | -1.26c | 744 | 378-352-14 | -18.58u | -2.5% | 1.77c | 107s |  |
| M all moves | 1210 | 996 | -0.84c | 33.3% | 990 | -1.12c | 981 | 500-464-17 | -22.75u | -2.3% | 1.41c | 48s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 919 | 914 | 2.33c | 23.1% | 190 | 1.97c | 913 | 403-510-0 | +262.23u | 28.7% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 60 | 54 | -0.14c | 20-34-0 | -12.40u | 37, -0.53c, -8.00u | negative |
| J2 B, NBA | 41 | 38 | 0.01c | 14-24-0 | -8.95u | 23, -0.47c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 35 | 32 | -0.37c | 14-18-0 | -2.97u | 25, -0.65c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 123 | 106 | -0.86c | 50-55-1 | -7.77u | 66, -1.01c, -4.82u | negative |
| D1 B, unders (descriptive) | 14 | 12 | 0.71c | 7-5-0 | +2.46u | 12, 0.71c, +2.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 12 | 10 | -1.04c | 1-9-0 | -7.81u | 8, -1.39c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 7 | 6 | 0.61c | 3-3-0 | +1.46u | 5, 0.64c, +0.31u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 50 | 45 | -0.45c | 25-18-2 | -1.93u | 21, -0.66c, -1.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1344 | 57 | 4.3% | -0.53c | 1.59c | 22-29-0 | -6.11u |  |
| MK novig fair-2c | 1344 | 22 | 1.7% | -0.4c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2951 | 146 | 5.0% | -0.83c | 1.1c | 71-61-2 | +13.30u |  |
| MK prophetx fair-2c | 2930 | 42 | 1.4% | -0.57c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 4295 | 203 | 4.8% | -0.75c | 1.25c | 93-90-2 | +7.20u | criteria not met (185/50 graded, CLV not positive) |
| MK all fair-2c | 4274 | 64 | 1.5% | -0.51c | 2.19c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 84.

## Odds API credits (100K/month plan)

Study: 623/day, projected 18680/30 days. All monitors on the key: 2120/day, projected 63598/30 days. Remaining 89368; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-06T00:41:04Z: 21 games (10 in 24h), quotes {'prophetx': 794, 'novig': 710, 'kalshi': 1472, 'polymarket_us': 1126}, 374 unmatched (12 book-games; fuzzy-matched 0), 2248 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 8 left 89368, 179s
- 2026-11-06T00:35:52Z: 21 games (9 in 24h), quotes {'prophetx': 730, 'novig': 702, 'kalshi': 1476, 'polymarket_us': 1126}, 376 unmatched (12 book-games; fuzzy-matched 0), 2252 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 3 filled 0, credits used 8 left 89389, 181s
- 2026-11-06T00:31:10Z: 22 games (10 in 24h), quotes {'prophetx': 730, 'novig': 652, 'kalshi': 1476, 'polymarket_us': 1126}, 296 unmatched (11 book-games; fuzzy-matched 0), 2331 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 6 B 1, maker posted 4 filled 0, credits used 8 left 89397, 206s
- 2026-11-06T00:21:10Z: 22 games (9 in 24h), quotes {'prophetx': 784, 'novig': 683, 'kalshi': 1486, 'polymarket_us': 1104}, 523 unmatched (14 book-games; fuzzy-matched 0), 2206 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 2 B 0, maker posted 17 filled 1, credits used 16 left 89425, 302s
- 2026-11-06T00:10:46Z: 24 games (11 in 24h), quotes {'prophetx': 872, 'novig': 683, 'kalshi': 1404, 'polymarket_us': 1104}, 491 unmatched (12 book-games; fuzzy-matched 0), 2179 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 13 filled 0, credits used 8 left 89452, 178s
- 2026-11-06T00:01:14Z: 31 games (17 in 24h), quotes {'prophetx': 844, 'novig': 687, 'kalshi': 1344, 'polymarket_us': 1104}, 367 unmatched (5 book-games; fuzzy-matched 0), 2243 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 8 B 0, maker posted 17 filled 0, credits used 16 left 89475, 315s
- 2026-11-05T23:51:01Z: 29 games (16 in 24h), quotes {'prophetx': 1046, 'novig': 697, 'kalshi': 1288, 'polymarket_us': 1072}, 245 unmatched (4 book-games; fuzzy-matched 0), 2311 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 0 B 0, maker posted 16 filled 1, credits used 16 left 89506, 302s
- 2026-11-05T23:41:01Z: 28 games (16 in 24h), quotes {'prophetx': 1046, 'novig': 696, 'kalshi': 1286, 'polymarket_us': 1072}, 243 unmatched (4 book-games; fuzzy-matched 0), 2311 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 8 left 89541, 182s
- 2026-11-05T23:31:14Z: 28 games (16 in 24h), quotes {'prophetx': 1046, 'novig': 698, 'kalshi': 1290, 'polymarket_us': 1072}, 245 unmatched (4 book-games; fuzzy-matched 0), 2313 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 5 filled 0, credits used 16 left 89564, 302s
- 2026-11-05T23:20:59Z: 28 games (16 in 24h), quotes {'prophetx': 1046, 'novig': 698, 'kalshi': 1290, 'polymarket_us': 1072}, 254 unmatched (4 book-games; fuzzy-matched 0), 2309 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 4 B 0, maker posted 10 filled 0, credits used 16 left 89608, 302s
