# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T01:06:32Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6340 | 6063 | -1.71c | 23.9% | 2632 | -1.07c | 5803 | 2973-2830-0 | -238.73u | -4.1% |  |  | criteria not met (5803/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1353 | 1270 | -3.64c | 16.8% | 284 | -2.89c | 1242 | 640-602-0 | -91.87u | -7.4% |  |  | criteria not met (1242/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 112 | -0.92c | 30.4% | 106 | -0.01c | 104 | 42-62-0 | -15.00u | -14.4% |  |  | criteria not met (104/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 66 | -0.79c | 30.3% | 64 | -0.13c | 60 | 26-34-0 | -4.43u | -7.4% |  |  |  |
| B ref age 5m+ | 40 | 37 | -1.38c | 29.7% | 33 | -0.06c | 35 | 11-24-0 | -11.96u | -34.2% |  |  |  |
| M move-watch: gettable (sightings) | 293 | 268 | -0.69c | 32.1% | 265 | -0.69c | 257 | 133-121-3 | -3.14u | -1.2% | 0.12c | 26s | criteria not met (257/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 149 | 136 | -0.74c | 33.8% | 135 | -0.93c | 129 | 65-62-2 | -2.65u | -2.1% | -0.18c | 28s |  |
| M gettable, price moves | 144 | 132 | -0.65c | 30.3% | 130 | -0.44c | 128 | 68-59-1 | -0.48u | -0.4% | 0.43c | 23s |  |
| M control: not gettable | 1120 | 814 | -0.89c | 33.9% | 806 | -1.27c | 801 | 394-393-14 | -45.42u | -5.7% | 1.76c | 164s |  |
| M all moves | 1413 | 1082 | -0.84c | 33.5% | 1071 | -1.13c | 1058 | 527-514-17 | -48.56u | -4.6% | 1.41c | 107s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 939 | 920 | 2.31c | 23.4% | 190 | 1.97c | 917 | 404-513-0 | +261.89u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 59 | -0.12c | 23-36-0 | -11.12u | 41, -0.56c, -7.87u | negative |
| J2 B, NBA | 50 | 40 | -0.02c | 15-25-0 | -8.85u | 25, -0.57c, -2.29u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 35 | -0.36c | 16-19-0 | -1.78u | 27, -0.66c, +1.98u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 153 | 121 | -0.8c | 58-62-1 | -7.03u | 70, -0.86c, -6.91u | negative |
| D1 B, unders (descriptive) | 20 | 14 | 0.65c | 8-6-0 | +2.56u | 14, 0.62c, +2.56u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 11 | -0.87c | 2-9-0 | -6.66u | 9, -1.1c, -4.66u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 7 | 0.61c | 3-4-0 | +0.46u | 6, 0.64c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 50 | -0.47c | 28-20-2 | -1.64u | 25, -0.69c, -1.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1542 | 72 | 4.7% | -0.64c | 1.6c | 29-30-0 | -0.37u |  |
| MK novig fair-2c | 1539 | 26 | 1.7% | -0.37c | 2.52c | 14-8-0 | +7.49u |  |
| MK prophetx fair-1c | 3238 | 163 | 5.1% | -0.89c | 1.1c | 82-64-2 | +22.05u |  |
| MK prophetx fair-2c | 3216 | 49 | 1.5% | -0.56c | 2.04c | 20-22-0 | -0.22u |  |
| MK all fair-1c | 4780 | 235 | 5.0% | -0.82c | 1.26c | 111-94-2 | +21.68u | criteria not met (207/50 graded, CLV not positive) |
| MK all fair-2c | 4755 | 75 | 1.6% | -0.49c | 2.2c | 34-30-0 | +7.27u | criteria not met (64/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 623/day, projected 18688/30 days. All monitors on the key: 2128/day, projected 63853/30 days. Remaining 87131; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T01:01:30Z: 74 games (63 in 24h), quotes {'prophetx': 5146, 'novig': 722, 'kalshi': 2252, 'polymarket_us': 1490}, 2923 unmatched (68 book-games; fuzzy-matched 2), 3142 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 17 B 0, maker posted 17 filled 1, credits used 12 left 87131, 302s
- 2026-11-07T00:51:26Z: 74 games (62 in 24h), quotes {'prophetx': 2156, 'novig': 713, 'kalshi': 2398, 'polymarket_us': 1794}, 1559 unmatched (41 book-games; fuzzy-matched 1), 3257 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 11 B 0, maker posted 35 filled 1, credits used 12 left 87162, 376s
- 2026-11-07T00:40:50Z: 74 games (61 in 24h), quotes {'prophetx': 3688, 'novig': 713, 'kalshi': 2720, 'polymarket_us': 2002}, 2473 unmatched (60 book-games; fuzzy-matched 1), 3564 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 1, maker posted 0 filled 1, credits used 6 left 87190, 234s
- 2026-11-07T00:31:06Z: 76 games (63 in 24h), quotes {'prophetx': 1264, 'novig': 713, 'kalshi': 2616, 'polymarket_us': 1818}, 1521 unmatched (40 book-games; fuzzy-matched 0), 3104 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 12 B 0, maker posted 14 filled 0, credits used 12 left 87207, 302s
- 2026-11-07T00:21:13Z: 76 games (56 in 24h), quotes {'prophetx': 5422, 'novig': 719, 'kalshi': 3368, 'polymarket_us': 2872}, 3629 unmatched (89 book-games; fuzzy-matched 1), 4460 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 2 filled 2, credits used 6 left 87256, 187s
- 2026-11-07T00:11:29Z: 78 games (58 in 24h), quotes {'prophetx': 4572, 'novig': 709, 'kalshi': 2408, 'polymarket_us': 1756}, 1621 unmatched (46 book-games; fuzzy-matched 2), 4183 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 17 B 0, maker posted 29 filled 0, credits used 12 left 87266, 330s
- 2026-11-07T00:01:29Z: 80 games (57 in 24h), quotes {'prophetx': 5736, 'novig': 721, 'kalshi': 3228, 'polymarket_us': 2762}, 3380 unmatched (83 book-games; fuzzy-matched 2), 4635 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 16 B 0, maker posted 24 filled 0, credits used 12 left 87312, 301s
- 2026-11-06T23:51:05Z: 80 games (56 in 24h), quotes {'prophetx': 2164, 'novig': 709, 'kalshi': 2346, 'polymarket_us': 1742}, 537 unmatched (23 book-games; fuzzy-matched 0), 3976 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 4 B 1, maker posted 37 filled 0, credits used 12 left 87344, 377s
- 2026-11-06T23:41:03Z: 80 games (56 in 24h), quotes {'prophetx': 4290, 'novig': 715, 'kalshi': 3186, 'polymarket_us': 2826}, 2590 unmatched (63 book-games; fuzzy-matched 2), 4772 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 9 B 0, maker posted 36 filled 3, credits used 12 left 87370, 378s
- 2026-11-06T23:31:01Z: 80 games (56 in 24h), quotes {'prophetx': 3488, 'novig': 717, 'kalshi': 2798, 'polymarket_us': 1876}, 1171 unmatched (40 book-games; fuzzy-matched 62), 4503 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 10 B 1, maker posted 23 filled 1, credits used 6 left 87409, 276s
