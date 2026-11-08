# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T21:32:20Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7763 | 7561 | -1.57c | 23.9% | 3325 | -1.0c | 7391 | 3808-3583-0 | -255.71u | -3.5% |  |  | criteria not met (7391/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1733 | 1648 | -3.12c | 18.1% | 360 | -2.61c | 1628 | 836-792-0 | -125.20u | -7.7% |  |  | criteria not met (1628/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 131 | 129 | -1.02c | 27.1% | 121 | -0.07c | 125 | 54-71-0 | -10.52u | -8.4% |  |  | criteria not met (125/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 76 | -1.03c | 26.3% | 73 | -0.17c | 74 | 34-40-0 | -1.54u | -2.1% |  |  |  |
| B ref age 5m+ | 44 | 44 | -1.23c | 27.3% | 39 | -0.15c | 42 | 15-27-0 | -10.38u | -24.7% |  |  |  |
| M move-watch: gettable (sightings) | 358 | 345 | -0.58c | 35.1% | 345 | -0.56c | 340 | 174-161-5 | -7.41u | -2.2% | 0.24c | 25s | criteria not met (340/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 187 | 178 | -0.65c | 34.8% | 179 | -0.82c | 175 | 85-86-4 | -8.65u | -4.9% | -0.06c | 26s |  |
| M gettable, price moves | 171 | 167 | -0.51c | 35.3% | 166 | -0.29c | 165 | 89-75-1 | +1.24u | 0.8% | 0.56c | 23s |  |
| M control: not gettable | 1476 | 1143 | -0.81c | 35.6% | 1131 | -1.19c | 1150 | 574-555-21 | -50.27u | -4.4% | 1.79c | 183s |  |
| M all moves | 1834 | 1488 | -0.76c | 35.5% | 1476 | -1.05c | 1490 | 748-716-26 | -57.68u | -3.9% | 1.49c | 121s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1039 | 1032 | 2.73c | 27.1% | 222 | 2.91c | 1033 | 457-576-0 | +280.96u | 27.2% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 82 | 77 | -0.22c | 33-44-0 | -7.88u | 53, -0.44c, -11.22u | negative |
| J2 B, NBA | 53 | 50 | -0.23c | 21-29-0 | -6.28u | 30, -0.59c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 46 | -0.43c | 22-24-0 | -0.14u | 36, -0.7c, +1.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 210 | 194 | -0.6c | 93-98-3 | -10.46u | 114, -0.62c, -12.50u | negative |
| D1 B, unders (descriptive) | 24 | 22 | 0.2c | 13-9-0 | +4.89u | 21, 0.15c, +3.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 16 | -0.84c | 4-12-0 | -7.43u | 14, -1.04c, -5.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 10 | 0.45c | 5-5-0 | +1.71u | 9, 0.44c, +0.56u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 62 | 60 | -0.31c | 34-24-2 | -2.48u | 34, -0.35c, -3.19u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1943 | 81 | 4.2% | -0.63c | 1.59c | 37-37-0 | +1.09u |  |
| MK novig fair-2c | 1939 | 30 | 1.6% | -0.35c | 2.52c | 16-11-0 | +6.65u |  |
| MK prophetx fair-1c | 4768 | 226 | 4.8% | -1.03c | 1.1c | 103-109-5 | -1.22u |  |
| MK prophetx fair-2c | 4736 | 76 | 1.6% | -0.59c | 2.04c | 33-37-0 | -1.16u |  |
| MK all fair-1c | 6711 | 307 | 4.6% | -0.92c | 1.24c | 140-146-5 | -0.13u | criteria not met (291/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 6675 | 106 | 1.6% | -0.52c | 2.18c | 49-48-0 | +5.49u | criteria not met (97/50 graded, CLV not positive) |

A and B on the same side/line: 104.

## Odds API credits (100K/month plan)

Study: 645/day, projected 19349/30 days. All monitors on the key: 2382/day, projected 71459/30 days. Remaining 80129; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T21:28:34Z: 17 games (11 in 24h), quotes {'prophetx': 948, 'novig': 720, 'kalshi': 1208, 'polymarket_us': 1040}, 356 unmatched (8 book-games; fuzzy-matched 0), 2052 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 11 B 0, maker posted 28 filled 0, credits used 6 left 80129, 226s
- 2026-11-08T21:21:55Z: 20 games (14 in 24h), quotes {'prophetx': 1088, 'novig': 728, 'kalshi': 1206, 'polymarket_us': 1460}, 172 unmatched (5 book-games; fuzzy-matched 0), 2575 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 32 filled 0, credits used 12 left 80145, 301s
- 2026-11-08T21:11:30Z: 20 games (14 in 24h), quotes {'prophetx': 1292, 'novig': 724, 'kalshi': 1200, 'polymarket_us': 1460}, 176 unmatched (5 book-games; fuzzy-matched 0), 2660 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 0, maker posted 36 filled 0, credits used 6 left 80177, 227s
- 2026-11-08T21:01:32Z: 21 games (15 in 24h), quotes {'prophetx': 1396, 'novig': 720, 'kalshi': 1236, 'polymarket_us': 1442}, 150 unmatched (7 book-games; fuzzy-matched 0), 2738 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 9 filled 1, credits used 12 left 80196, 302s
- 2026-11-08T20:51:09Z: 21 games (15 in 24h), quotes {'prophetx': 1396, 'novig': 724, 'kalshi': 1328, 'polymarket_us': 1600}, 240 unmatched (9 book-games; fuzzy-matched 0), 2850 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 12 left 80219, 302s
- 2026-11-08T20:41:34Z: 21 games (15 in 24h), quotes {'prophetx': 1396, 'novig': 724, 'kalshi': 1376, 'polymarket_us': 1598}, 288 unmatched (10 book-games; fuzzy-matched 0), 2864 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 20 filled 0, credits used 6 left 80245, 221s
- 2026-11-08T20:31:50Z: 23 games (17 in 24h), quotes {'prophetx': 1396, 'novig': 728, 'kalshi': 1408, 'polymarket_us': 1598}, 226 unmatched (8 book-games; fuzzy-matched 0), 2968 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 42 filled 0, credits used 12 left 80262, 302s
- 2026-11-08T20:21:48Z: 23 games (17 in 24h), quotes {'prophetx': 1562, 'novig': 728, 'kalshi': 1418, 'polymarket_us': 1756}, 248 unmatched (8 book-games; fuzzy-matched 0), 3125 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 26 filled 0, credits used 12 left 80285, 301s
- 2026-11-08T20:11:18Z: 23 games (17 in 24h), quotes {'prophetx': 1562, 'novig': 720, 'kalshi': 1454, 'polymarket_us': 1752}, 278 unmatched (8 book-games; fuzzy-matched 0), 3145 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 50 filled 0, credits used 12 left 80317, 329s
- 2026-11-08T20:01:07Z: 23 games (17 in 24h), quotes {'prophetx': 1358, 'novig': 720, 'kalshi': 1474, 'polymarket_us': 1752}, 302 unmatched (8 book-games; fuzzy-matched 0), 3045 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 30 filled 0, credits used 6 left 80363, 182s
