# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-09T00:34:06Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7837 | 7659 | -1.58c | 23.9% | 3367 | -1.02c | 7549 | 3887-3662-0 | -272.31u | -3.6% |  |  | criteria not met (7549/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1739 | 1673 | -3.07c | 18.5% | 366 | -2.6c | 1648 | 846-802-0 | -131.89u | -8.0% |  |  | criteria not met (1648/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 131 | 130 | -1.07c | 26.9% | 121 | -0.07c | 129 | 55-74-0 | -12.39u | -9.6% |  |  | criteria not met (129/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 77 | -1.11c | 26.0% | 73 | -0.17c | 76 | 34-42-0 | -3.54u | -4.7% |  |  |  |
| B ref age 5m+ | 44 | 44 | -1.23c | 27.3% | 39 | -0.15c | 44 | 16-28-0 | -10.25u | -23.3% |  |  |  |
| M move-watch: gettable (sightings) | 366 | 353 | -0.57c | 35.1% | 353 | -0.55c | 348 | 181-162-5 | -0.91u | -0.3% | 0.24c | 25s | criteria not met (348/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 191 | 182 | -0.66c | 34.6% | 183 | -0.81c | 179 | 89-86-4 | -5.13u | -2.9% | -0.06c | 26s |  |
| M gettable, price moves | 175 | 171 | -0.48c | 35.7% | 170 | -0.27c | 169 | 92-76-1 | +4.22u | 2.5% | 0.57c | 23s |  |
| M control: not gettable | 1489 | 1170 | -0.79c | 35.6% | 1154 | -1.19c | 1174 | 585-568-21 | -52.33u | -4.5% | 1.83c | 183s |  |
| M all moves | 1855 | 1523 | -0.74c | 35.5% | 1507 | -1.04c | 1522 | 766-730-26 | -53.24u | -3.5% | 1.52c | 121s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1039 | 1035 | 2.72c | 27.2% | 222 | 2.91c | 1033 | 457-576-0 | +280.96u | 27.2% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 82 | 80 | -0.22c | 34-46-0 | -8.75u | 55, -0.44c, -13.22u | negative |
| J2 B, NBA | 53 | 51 | -0.23c | 21-30-0 | -7.28u | 31, -0.59c, -6.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 47 | -0.43c | 22-25-0 | -1.14u | 37, -0.7c, +0.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 214 | 201 | -0.61c | 99-99-3 | -6.23u | 118, -0.63c, -10.80u | negative |
| D1 B, unders (descriptive) | 24 | 23 | 0.2c | 13-10-0 | +3.89u | 22, 0.15c, +2.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 61 | -0.21c | 35-24-2 | -0.20u | 35, -0.28c, -0.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2011 | 81 | 4.1% | -0.61c | 1.58c | 40-39-0 | +2.40u |  |
| MK novig fair-2c | 2007 | 30 | 1.5% | -0.35c | 2.52c | 18-11-0 | +8.82u |  |
| MK prophetx fair-1c | 4854 | 229 | 4.7% | -1.01c | 1.1c | 106-112-5 | -1.18u |  |
| MK prophetx fair-2c | 4820 | 76 | 1.6% | -0.59c | 2.04c | 35-39-0 | -1.12u |  |
| MK all fair-1c | 6865 | 310 | 4.5% | -0.91c | 1.24c | 146-151-5 | +1.21u | criteria not met (302/50 graded, CLV not positive) |
| MK all fair-2c | 6827 | 106 | 1.6% | -0.52c | 2.18c | 53-50-0 | +7.70u | criteria not met (103/50 graded, CLV not positive) |

A and B on the same side/line: 104.

## Odds API credits (100K/month plan)

Study: 654/day, projected 19605/30 days. All monitors on the key: 2396/day, projected 71866/30 days. Remaining 79661; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-09T00:31:34Z: 12 games (6 in 24h), quotes {'prophetx': 482, 'novig': 508, 'kalshi': 830, 'polymarket_us': 560}, 182 unmatched (6 book-games; fuzzy-matched 0), 1318 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 0, maker posted 8 filled 0, credits used 6 left 79661, 151s
- 2026-11-09T00:21:43Z: 12 games (6 in 24h), quotes {'prophetx': 602, 'novig': 500, 'kalshi': 848, 'polymarket_us': 692}, 196 unmatched (7 book-games; fuzzy-matched 0), 1456 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 12 left 79678, 301s
- 2026-11-09T00:11:43Z: 14 games (8 in 24h), quotes {'prophetx': 602, 'novig': 500, 'kalshi': 852, 'polymarket_us': 692}, 170 unmatched (5 book-games; fuzzy-matched 0), 1488 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 4 filled 0, credits used 12 left 79716, 301s
- 2026-11-09T00:03:43Z: 15 games (9 in 24h), quotes {'prophetx': 602, 'novig': 598, 'kalshi': 890, 'polymarket_us': 692}, 136 unmatched (6 book-games; fuzzy-matched 0), 1584 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 13 filled 0, credits used 6 left 79748, 157s
- 2026-11-08T23:57:41Z: 15 games (9 in 24h), quotes {'prophetx': 800, 'novig': 630, 'kalshi': 902, 'polymarket_us': 880}, 146 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 1 filled 1, credits used 6 left 79754, 242s
- 2026-11-08T23:51:19Z: 15 games (9 in 24h), quotes {'prophetx': 800, 'novig': 634, 'kalshi': 910, 'polymarket_us': 880}, 156 unmatched (6 book-games; fuzzy-matched 0), 1759 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 38 filled 0, credits used 12 left 79773, 301s
- 2026-11-08T23:41:28Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 922, 'polymarket_us': 880}, 172 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 16 filled 0, credits used 6 left 79804, 185s
- 2026-11-08T23:31:36Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 946, 'polymarket_us': 880}, 194 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 16 filled 0, credits used 12 left 79823, 301s
- 2026-11-08T23:20:59Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 976, 'polymarket_us': 880}, 224 unmatched (6 book-games; fuzzy-matched 0), 1763 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 16 filled 0, credits used 6 left 79857, 159s
- 2026-11-08T23:11:18Z: 15 games (9 in 24h), quotes {'prophetx': 802, 'novig': 634, 'kalshi': 992, 'polymarket_us': 880}, 232 unmatched (6 book-games; fuzzy-matched 0), 1766 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 4 B 0, maker posted 13 filled 1, credits used 12 left 79863, 349s
