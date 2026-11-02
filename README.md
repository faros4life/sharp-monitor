# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T01:49:44Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4123 | 3898 | -1.92c | 21.5% | 1583 | -1.14c | 3794 | 1894-1900-0 | -229.10u | -6.0% |  |  | criteria not met (3794/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1027 | 934 | -3.84c | 13.9% | 212 | -3.04c | 924 | 481-443-0 | -58.31u | -6.3% |  |  | criteria not met (924/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 61 | 61 | -0.66c | 32.8% | 59 | 0.13c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 39 | -0.62c | 30.8% | 38 | 0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 17 | 17 | -1.11c | 35.3% | 16 | -0.09c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 154 | 153 | -0.57c | 32.7% | 151 | -0.6c | 143 | 70-72-1 | -7.27u | -5.1% | 0.29c | 22s | criteria not met (143/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 82 | 82 | -0.58c | 35.4% | 81 | -0.81c | 79 | 38-40-1 | -5.20u | -6.6% | 0.01c | 28s |  |
| M gettable, price moves | 72 | 71 | -0.56c | 29.6% | 70 | -0.36c | 64 | 32-32-0 | -2.07u | -3.2% | 0.6c | 20s |  |
| M control: not gettable | 580 | 461 | -0.87c | 33.6% | 458 | -1.22c | 461 | 245-208-8 | +10.55u | 2.3% | 1.75c | 25s |  |
| M all moves | 734 | 614 | -0.79c | 33.4% | 609 | -1.06c | 604 | 315-280-9 | +3.28u | 0.5% | 1.44c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 625 | 607 | 4.47c | 28.8% | 119 | 3.98c | 606 | 270-336-0 | +320.30u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 22 | 20 | 0.2c | 9-11-0 | -1.24u | 16, 0.0c, -1.47u | not enough yet |
| J2 B, NBA | 11 | 9 | 0.09c | 4-5-0 | -0.70u | 6, -0.25c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 15 | -0.17c | 7-8-0 | -0.40u | 12, -0.33c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 56 | 50 | -0.51c | 20-29-1 | -10.13u | 34, -0.61c, -7.81u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 7 | -0.58c | 3-4-0 | -2.66u | 6, -0.72c, -3.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 589 | 29 | 5.0% | -0.37c | 1.61c | 15-14-0 | +1.52u |  |
| MK novig fair-2c | 589 | 11 | 1.9% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1891 | 93 | 4.9% | -0.88c | 1.1c | 42-45-2 | -1.21u |  |
| MK prophetx fair-2c | 1874 | 25 | 1.3% | -0.69c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2480 | 122 | 4.9% | -0.76c | 1.22c | 57-59-2 | +0.31u | criteria not met (118/50 graded, CLV not positive) |
| MK all fair-2c | 2463 | 36 | 1.5% | -0.63c | 2.15c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 51.

## Odds API credits (100K/month plan)

Study: 646/day, projected 19391/30 days. All monitors on the key: 2165/day, projected 64935/30 days. Remaining 97517; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T01:46:43Z: 17 games (15 in 24h), quotes {'prophetx': 346, 'novig': 718, 'kalshi': 1142, 'polymarket_us': 1836}, 276 unmatched (4 book-games; fuzzy-matched 0), 2213 side/lines, polls [NFL:slow,NHL:slow; NBA:fast], moves 0, new A 10 B 0, maker posted 4 filled 0, credits used 6 left 97517, 181s
- 2026-11-02T01:40:22Z: 18 games (16 in 24h), quotes {'prophetx': 346, 'novig': 724, 'kalshi': 1138, 'polymarket_us': 1836}, 200 unmatched (3 book-games; fuzzy-matched 24), 2282 side/lines, polls [none_due; NBA:fast], moves 2, new A 22 B 0, maker posted 0 filled 0, credits used 2 left 97532, 231s
- 2026-11-02T01:32:17Z: 18 games (14 in 24h), quotes {'prophetx': 344, 'novig': 726, 'kalshi': 1122, 'polymarket_us': 1708}, 206 unmatched (4 book-games; fuzzy-matched 0), 2243 side/lines, polls [none_due; NBA:fast], moves 0, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 97543, 194s
- 2026-11-02T01:26:32Z: 18 games (14 in 24h), quotes {'prophetx': 392, 'novig': 724, 'kalshi': 1092, 'polymarket_us': 1712}, 210 unmatched (4 book-games; fuzzy-matched 0), 2186 side/lines, polls [NHL:slow; NBA:fast], moves 3, new A 15 B 0, maker posted 5 filled 0, credits used 4 left 97545, 316s
- 2026-11-02T01:20:30Z: 19 games (15 in 24h), quotes {'prophetx': 388, 'novig': 730, 'kalshi': 1100, 'polymarket_us': 1712}, 150 unmatched (3 book-games; fuzzy-matched 0), 2258 side/lines, polls [NFL:fast,NBA:fast; NBA:fast], moves 0, new A 22 B 0, maker posted 2 filled 0, credits used 6 left 97560, 301s
- 2026-11-02T01:10:30Z: 18 games (13 in 24h), quotes {'prophetx': 408, 'novig': 730, 'kalshi': 1092, 'polymarket_us': 1712}, 280 unmatched (4 book-games; fuzzy-matched 0), 2130 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 1, new A 25 B 1, maker posted 11 filled 0, credits used 4 left 97584, 210s
- 2026-11-02T01:00:36Z: 19 games (11 in 24h), quotes {'prophetx': 366, 'novig': 724, 'kalshi': 1140, 'polymarket_us': 1712}, 266 unmatched (3 book-games; fuzzy-matched 0), 2162 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 33 B 0, maker posted 8 filled 0, credits used 12 left 97603, 301s
- 2026-11-02T00:50:29Z: 19 games (11 in 24h), quotes {'prophetx': 384, 'novig': 716, 'kalshi': 1136, 'polymarket_us': 1322}, 136 unmatched (2 book-games; fuzzy-matched 0), 2019 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 28 B 0, maker posted 1 filled 1, credits used 6 left 97637, 181s
- 2026-11-02T00:40:31Z: 19 games (11 in 24h), quotes {'prophetx': 382, 'novig': 724, 'kalshi': 1142, 'polymarket_us': 1322}, 146 unmatched (3 book-games; fuzzy-matched 0), 2003 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 12 B 0, maker posted 5 filled 1, credits used 12 left 97654, 329s
- 2026-11-02T00:30:30Z: 19 games (7 in 24h), quotes {'prophetx': 382, 'novig': 464, 'kalshi': 1174, 'polymarket_us': 1322}, 178 unmatched (4 book-games; fuzzy-matched 24), 1970 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 97675, 164s
