# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T01:31:48Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4074 | 3845 | -1.92c | 21.6% | 1570 | -1.15c | 3794 | 1894-1900-0 | -229.10u | -6.0% |  |  | criteria not met (3794/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1018 | 924 | -3.85c | 14.0% | 211 | -3.05c | 924 | 481-443-0 | -58.31u | -6.3% |  |  | criteria not met (924/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 61 | 59 | -0.68c | 32.2% | 57 | 0.08c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 38 | -0.65c | 28.9% | 37 | -0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 17 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 154 | 149 | -0.56c | 33.6% | 147 | -0.62c | 143 | 70-72-1 | -7.27u | -5.1% | 0.28c | 22s | criteria not met (143/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 82 | 80 | -0.58c | 36.2% | 79 | -0.81c | 79 | 38-40-1 | -5.20u | -6.6% | 0.02c | 28s |  |
| M gettable, price moves | 72 | 69 | -0.52c | 30.4% | 68 | -0.39c | 64 | 32-32-0 | -2.07u | -3.2% | 0.59c | 20s |  |
| M control: not gettable | 578 | 453 | -0.86c | 34.0% | 450 | -1.2c | 461 | 245-208-8 | +10.55u | 2.3% | 1.77c | 25s |  |
| M all moves | 732 | 602 | -0.78c | 33.9% | 597 | -1.06c | 604 | 315-280-9 | +3.28u | 0.5% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 625 | 607 | 4.47c | 28.8% | 119 | 3.98c | 606 | 270-336-0 | +320.30u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 22 | 20 | 0.09c | 9-11-0 | -1.24u | 16, -0.04c, -1.47u | not enough yet |
| J2 B, NBA | 11 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 15 | -0.24c | 7-8-0 | -0.40u | 12, -0.42c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 56 | 50 | -0.55c | 20-29-1 | -10.13u | 34, -0.62c, -7.81u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 7 | -0.58c | 3-4-0 | -2.66u | 6, -0.72c, -3.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 587 | 29 | 5.0% | -0.37c | 1.62c | 15-14-0 | +1.52u |  |
| MK novig fair-2c | 587 | 11 | 1.9% | -0.51c | 2.55c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1891 | 93 | 4.9% | -0.93c | 1.1c | 42-45-2 | -1.21u |  |
| MK prophetx fair-2c | 1874 | 25 | 1.3% | -0.8c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2478 | 122 | 4.9% | -0.8c | 1.22c | 57-59-2 | +0.31u | criteria not met (118/50 graded, CLV not positive) |
| MK all fair-2c | 2461 | 36 | 1.5% | -0.71c | 2.15c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 51.

## Odds API credits (100K/month plan)

Study: 646/day, projected 19386/30 days. All monitors on the key: 2165/day, projected 64949/30 days. Remaining 97545; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T01:26:32Z: 18 games (14 in 24h), quotes {'prophetx': 392, 'novig': 724, 'kalshi': 1092, 'polymarket_us': 1712}, 210 unmatched (4 book-games; fuzzy-matched 0), 2186 side/lines, polls [NHL:slow; NBA:fast], moves 3, new A 15 B 0, maker posted 5 filled 0, credits used 4 left 97545, 316s
- 2026-11-02T01:20:30Z: 19 games (15 in 24h), quotes {'prophetx': 388, 'novig': 730, 'kalshi': 1100, 'polymarket_us': 1712}, 150 unmatched (3 book-games; fuzzy-matched 0), 2258 side/lines, polls [NFL:fast,NBA:fast; NBA:fast], moves 0, new A 22 B 0, maker posted 2 filled 0, credits used 6 left 97560, 301s
- 2026-11-02T01:10:30Z: 18 games (13 in 24h), quotes {'prophetx': 408, 'novig': 730, 'kalshi': 1092, 'polymarket_us': 1712}, 280 unmatched (4 book-games; fuzzy-matched 0), 2130 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 1, new A 25 B 1, maker posted 11 filled 0, credits used 4 left 97584, 210s
- 2026-11-02T01:00:36Z: 19 games (11 in 24h), quotes {'prophetx': 366, 'novig': 724, 'kalshi': 1140, 'polymarket_us': 1712}, 266 unmatched (3 book-games; fuzzy-matched 0), 2162 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 33 B 0, maker posted 8 filled 0, credits used 12 left 97603, 301s
- 2026-11-02T00:50:29Z: 19 games (11 in 24h), quotes {'prophetx': 384, 'novig': 716, 'kalshi': 1136, 'polymarket_us': 1322}, 136 unmatched (2 book-games; fuzzy-matched 0), 2019 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 28 B 0, maker posted 1 filled 1, credits used 6 left 97637, 181s
- 2026-11-02T00:40:31Z: 19 games (11 in 24h), quotes {'prophetx': 382, 'novig': 724, 'kalshi': 1142, 'polymarket_us': 1322}, 146 unmatched (3 book-games; fuzzy-matched 0), 2003 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 12 B 0, maker posted 5 filled 1, credits used 12 left 97654, 329s
- 2026-11-02T00:30:30Z: 19 games (7 in 24h), quotes {'prophetx': 382, 'novig': 464, 'kalshi': 1174, 'polymarket_us': 1322}, 178 unmatched (4 book-games; fuzzy-matched 24), 1970 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 97675, 164s
- 2026-11-02T00:20:28Z: 19 games (7 in 24h), quotes {'prophetx': 354, 'novig': 416, 'kalshi': 1196, 'polymarket_us': 684}, 68 unmatched (3 book-games; fuzzy-matched 0), 1673 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 10 filled 0, credits used 12 left 97692, 420s
- 2026-11-02T00:10:30Z: 19 games (7 in 24h), quotes {'prophetx': 354, 'novig': 436, 'kalshi': 934, 'polymarket_us': 684}, 96 unmatched (4 book-games; fuzzy-matched 0), 1437 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 13 filled 0, credits used 12 left 97715, 417s
- 2026-11-02T00:00:36Z: 19 games (4 in 24h), quotes {'prophetx': 354, 'novig': 358, 'kalshi': 962, 'polymarket_us': 684}, 128 unmatched (4 book-games; fuzzy-matched 0), 1409 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 0, maker posted 13 filled 0, credits used 12 left 97738, 411s
