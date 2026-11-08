# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T23:06:12Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7803 | 7561 | -1.57c | 23.9% | 3325 | -1.0c | 7444 | 3830-3614-0 | -272.04u | -3.7% |  |  | criteria not met (7444/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1737 | 1648 | -3.12c | 18.1% | 360 | -2.61c | 1634 | 838-796-0 | -128.42u | -7.9% |  |  | criteria not met (1634/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 131 | 129 | -1.02c | 27.1% | 121 | -0.07c | 127 | 55-72-0 | -10.39u | -8.2% |  |  | criteria not met (127/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 76 | -1.03c | 26.3% | 73 | -0.17c | 75 | 34-41-0 | -2.54u | -3.4% |  |  |  |
| B ref age 5m+ | 44 | 44 | -1.23c | 27.3% | 39 | -0.15c | 43 | 16-27-0 | -9.25u | -21.5% |  |  |  |
| M move-watch: gettable (sightings) | 363 | 345 | -0.58c | 35.1% | 345 | -0.56c | 345 | 179-161-5 | -3.17u | -0.9% | 0.24c | 24s | criteria not met (345/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 188 | 178 | -0.65c | 34.8% | 179 | -0.82c | 178 | 88-86-4 | -6.11u | -3.4% | -0.06c | 26s |  |
| M gettable, price moves | 175 | 167 | -0.51c | 35.3% | 166 | -0.29c | 167 | 91-75-1 | +2.95u | 1.8% | 0.56c | 23s |  |
| M control: not gettable | 1484 | 1143 | -0.81c | 35.6% | 1131 | -1.19c | 1156 | 577-558-21 | -50.59u | -4.4% | 1.79c | 183s |  |
| M all moves | 1847 | 1488 | -0.76c | 35.5% | 1476 | -1.05c | 1501 | 756-719-26 | -53.76u | -3.6% | 1.49c | 124s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1039 | 1032 | 2.73c | 27.1% | 222 | 2.91c | 1033 | 457-576-0 | +280.96u | 27.2% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 82 | 79 | -0.22c | 34-45-0 | -7.75u | 54, -0.44c, -12.22u | negative |
| J2 B, NBA | 53 | 50 | -0.23c | 21-29-0 | -6.28u | 30, -0.59c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 47 | -0.43c | 22-25-0 | -1.14u | 37, -0.7c, +0.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 211 | 199 | -0.6c | 98-98-3 | -6.21u | 116, -0.62c, -10.78u | negative |
| D1 B, unders (descriptive) | 24 | 23 | 0.2c | 13-10-0 | +3.89u | 22, 0.15c, +2.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 10 | 0.45c | 5-5-0 | +1.71u | 9, 0.44c, +0.56u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 60 | -0.31c | 34-24-2 | -2.48u | 34, -0.35c, -3.19u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1979 | 81 | 4.1% | -0.63c | 1.59c | 39-39-0 | +1.40u |  |
| MK novig fair-2c | 1975 | 30 | 1.5% | -0.35c | 2.52c | 17-11-0 | +7.78u |  |
| MK prophetx fair-1c | 4821 | 227 | 4.7% | -1.03c | 1.1c | 103-111-5 | -3.22u |  |
| MK prophetx fair-2c | 4788 | 76 | 1.6% | -0.59c | 2.04c | 33-38-0 | -2.16u |  |
| MK all fair-1c | 6800 | 308 | 4.6% | -0.92c | 1.24c | 142-150-5 | -1.82u | criteria not met (297/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 6763 | 106 | 1.6% | -0.52c | 2.18c | 50-49-0 | +5.62u | criteria not met (99/50 graded, CLV not positive) |

A and B on the same side/line: 104.

## Odds API credits (100K/month plan)

Study: 649/day, projected 19484/30 days. All monitors on the key: 2389/day, projected 71664/30 days. Remaining 79893; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T23:01:10Z: 17 games (11 in 24h), quotes {'prophetx': 730, 'novig': 728, 'kalshi': 994, 'polymarket_us': 880}, 158 unmatched (5 book-games; fuzzy-matched 0), 1834 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 5 B 0, maker posted 16 filled 0, credits used 12 left 79893, 302s
- 2026-11-08T22:52:11Z: 16 games (11 in 24h), quotes {'prophetx': 958, 'novig': 724, 'kalshi': 1004, 'polymarket_us': 1040}, 226 unmatched (6 book-games; fuzzy-matched 0), 1968 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 1 filled 0, credits used 6 left 79916, 202s
- 2026-11-08T22:47:30Z: 16 games (11 in 24h), quotes {'prophetx': 958, 'novig': 722, 'kalshi': 1030, 'polymarket_us': 1040}, 245 unmatched (7 book-games; fuzzy-matched 0), 1964 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 1, credits used 6 left 79933, 184s
- 2026-11-08T22:41:18Z: 17 games (11 in 24h), quotes {'prophetx': 824, 'novig': 718, 'kalshi': 1042, 'polymarket_us': 1040}, 206 unmatched (6 book-games; fuzzy-matched 0), 1960 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 79948, 189s
- 2026-11-08T22:31:39Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 718, 'kalshi': 1100, 'polymarket_us': 1040}, 254 unmatched (6 book-games; fuzzy-matched 0), 2037 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 44 filled 0, credits used 12 left 79965, 301s
- 2026-11-08T22:21:48Z: 17 games (11 in 24h), quotes {'prophetx': 926, 'novig': 730, 'kalshi': 1122, 'polymarket_us': 1040}, 268 unmatched (6 book-games; fuzzy-matched 0), 2031 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 12 filled 0, credits used 6 left 79999, 185s
- 2026-11-08T22:11:50Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 720, 'kalshi': 1122, 'polymarket_us': 1040}, 270 unmatched (6 book-games; fuzzy-matched 0), 2048 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 12 filled 0, credits used 12 left 80018, 324s
- 2026-11-08T22:01:47Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 730, 'kalshi': 1134, 'polymarket_us': 1040}, 284 unmatched (6 book-games; fuzzy-matched 0), 2046 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 5 B 0, maker posted 12 filled 0, credits used 12 left 80052, 302s
- 2026-11-08T21:51:41Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 730, 'kalshi': 1142, 'polymarket_us': 1040}, 292 unmatched (6 book-games; fuzzy-matched 0), 2049 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 12 filled 0, credits used 12 left 80081, 301s
- 2026-11-08T21:41:43Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 726, 'kalshi': 1138, 'polymarket_us': 1040}, 302 unmatched (6 book-games; fuzzy-matched 0), 2028 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 80108, 209s
