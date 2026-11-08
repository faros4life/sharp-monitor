# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T23:36:37Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7811 | 7620 | -1.58c | 23.9% | 3346 | -1.02c | 7444 | 3830-3614-0 | -272.04u | -3.7% |  |  | criteria not met (7444/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1738 | 1663 | -3.07c | 18.6% | 363 | -2.59c | 1634 | 838-796-0 | -128.42u | -7.9% |  |  | criteria not met (1634/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 131 | 130 | -1.07c | 26.9% | 121 | -0.07c | 127 | 55-72-0 | -10.39u | -8.2% |  |  | criteria not met (127/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 77 | -1.11c | 26.0% | 73 | -0.17c | 75 | 34-41-0 | -2.54u | -3.4% |  |  |  |
| B ref age 5m+ | 44 | 44 | -1.23c | 27.3% | 39 | -0.15c | 43 | 16-27-0 | -9.25u | -21.5% |  |  |  |
| M move-watch: gettable (sightings) | 363 | 349 | -0.57c | 35.5% | 349 | -0.55c | 345 | 179-161-5 | -3.17u | -0.9% | 0.25c | 24s | criteria not met (345/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 188 | 180 | -0.65c | 35.0% | 181 | -0.8c | 178 | 88-86-4 | -6.11u | -3.4% | -0.05c | 26s |  |
| M gettable, price moves | 175 | 169 | -0.49c | 36.1% | 168 | -0.27c | 167 | 91-75-1 | +2.95u | 1.8% | 0.57c | 23s |  |
| M control: not gettable | 1488 | 1154 | -0.78c | 35.9% | 1138 | -1.18c | 1156 | 577-558-21 | -50.59u | -4.4% | 1.83c | 183s |  |
| M all moves | 1851 | 1503 | -0.73c | 35.8% | 1487 | -1.03c | 1501 | 756-719-26 | -53.76u | -3.6% | 1.52c | 124s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1039 | 1032 | 2.73c | 27.1% | 222 | 2.91c | 1033 | 457-576-0 | +280.96u | 27.2% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 82 | 79 | -0.22c | 34-45-0 | -7.75u | 54, -0.44c, -12.22u | negative |
| J2 B, NBA | 53 | 50 | -0.23c | 21-29-0 | -6.28u | 30, -0.59c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 47 | -0.43c | 22-25-0 | -1.14u | 37, -0.7c, +0.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 211 | 199 | -0.61c | 98-98-3 | -6.21u | 116, -0.63c, -10.78u | negative |
| D1 B, unders (descriptive) | 24 | 23 | 0.2c | 13-10-0 | +3.89u | 22, 0.15c, +2.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 10 | 0.45c | 5-5-0 | +1.71u | 9, 0.44c, +0.56u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 60 | -0.22c | 34-24-2 | -2.48u | 34, -0.3c, -3.19u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1989 | 81 | 4.1% | -0.61c | 1.59c | 39-39-0 | +1.40u |  |
| MK novig fair-2c | 1985 | 30 | 1.5% | -0.35c | 2.52c | 17-11-0 | +7.78u |  |
| MK prophetx fair-1c | 4834 | 228 | 4.8% | -1.02c | 1.1c | 103-111-5 | -3.22u |  |
| MK prophetx fair-2c | 4800 | 76 | 1.6% | -0.59c | 2.04c | 33-38-0 | -2.16u |  |
| MK all fair-1c | 6823 | 309 | 4.6% | -0.92c | 1.24c | 142-150-5 | -1.82u | criteria not met (297/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 6785 | 106 | 1.6% | -0.52c | 2.18c | 50-49-0 | +5.62u | criteria not met (99/50 graded, CLV not positive) |

A and B on the same side/line: 104.

## Odds API credits (100K/month plan)

Study: 651/day, projected 19524/30 days. All monitors on the key: 2390/day, projected 71712/30 days. Remaining 79823; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T23:31:36Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 946, 'polymarket_us': 880}, 194 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 16 filled 0, credits used 12 left 79823, 301s
- 2026-11-08T23:20:59Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 976, 'polymarket_us': 880}, 224 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 16 filled 0, credits used 6 left 79857, 159s
- 2026-11-08T23:11:18Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 992, 'polymarket_us': 880}, 232 unmatched (6 book-games; fuzzy-matched 0), 1766 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 4 B 0, maker posted 13 filled 1, credits used 12 left 79863, 349s
- 2026-11-08T23:01:10Z: 17 games (11 in 24h), quotes {'prophetx': 730, 'novig': 728, 'kalshi': 994, 'polymarket_us': 880}, 158 unmatched (5 book-games; fuzzy-matched 0), 1834 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 5 B 0, maker posted 16 filled 0, credits used 12 left 79893, 302s
- 2026-11-08T22:52:11Z: 16 games (11 in 24h), quotes {'prophetx': 958, 'novig': 724, 'kalshi': 1004, 'polymarket_us': 1040}, 226 unmatched (6 book-games; fuzzy-matched 0), 1968 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 1 filled 0, credits used 6 left 79916, 202s
- 2026-11-08T22:47:30Z: 16 games (11 in 24h), quotes {'prophetx': 958, 'novig': 722, 'kalshi': 1030, 'polymarket_us': 1040}, 245 unmatched (7 book-games; fuzzy-matched 0), 1964 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 1, credits used 6 left 79933, 184s
- 2026-11-08T22:41:18Z: 17 games (11 in 24h), quotes {'prophetx': 824, 'novig': 718, 'kalshi': 1042, 'polymarket_us': 1040}, 206 unmatched (6 book-games; fuzzy-matched 0), 1960 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 79948, 189s
- 2026-11-08T22:31:39Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 718, 'kalshi': 1100, 'polymarket_us': 1040}, 254 unmatched (6 book-games; fuzzy-matched 0), 2037 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 44 filled 0, credits used 12 left 79965, 301s
- 2026-11-08T22:21:48Z: 17 games (11 in 24h), quotes {'prophetx': 926, 'novig': 730, 'kalshi': 1122, 'polymarket_us': 1040}, 268 unmatched (6 book-games; fuzzy-matched 0), 2031 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 12 filled 0, credits used 6 left 79999, 185s
- 2026-11-08T22:11:50Z: 17 games (11 in 24h), quotes {'prophetx': 956, 'novig': 720, 'kalshi': 1122, 'polymarket_us': 1040}, 270 unmatched (6 book-games; fuzzy-matched 0), 2048 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 12 filled 0, credits used 12 left 80018, 324s
