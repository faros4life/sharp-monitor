# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T02:43:32Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4168 | 3959 | -1.92c | 21.6% | 1602 | -1.15c | 3804 | 1899-1905-0 | -229.54u | -6.0% |  |  | criteria not met (3804/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1038 | 956 | -3.85c | 14.0% | 216 | -3.11c | 924 | 481-443-0 | -58.31u | -6.3% |  |  | criteria not met (924/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 62 | 61 | -0.66c | 32.8% | 59 | 0.13c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 39 | -0.62c | 30.8% | 38 | 0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 18 | 17 | -1.11c | 35.3% | 16 | -0.09c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 154 | 154 | -0.57c | 32.5% | 152 | -0.59c | 146 | 72-73-1 | -6.76u | -4.6% | 0.29c | 22s | criteria not met (146/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 82 | 82 | -0.58c | 35.4% | 81 | -0.81c | 79 | 38-40-1 | -5.20u | -6.6% | 0.01c | 28s |  |
| M gettable, price moves | 72 | 72 | -0.56c | 29.2% | 71 | -0.34c | 67 | 34-33-0 | -1.55u | -2.3% | 0.61c | 20s |  |
| M control: not gettable | 584 | 470 | -0.87c | 34.0% | 466 | -1.22c | 464 | 246-210-8 | +9.49u | 2.0% | 1.76c | 25s |  |
| M all moves | 738 | 624 | -0.79c | 33.7% | 618 | -1.07c | 610 | 318-283-9 | +2.73u | 0.4% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 634 | 614 | 4.4c | 29.2% | 122 | 3.88c | 606 | 270-336-0 | +320.30u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 23 | 20 | 0.2c | 9-11-0 | -1.24u | 16, 0.0c, -1.47u | not enough yet |
| J2 B, NBA | 12 | 9 | 0.09c | 4-5-0 | -0.70u | 6, -0.25c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 15 | -0.17c | 7-8-0 | -0.40u | 12, -0.33c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 56 | 50 | -0.49c | 20-29-1 | -10.13u | 34, -0.58c, -7.81u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 10 | -0.58c | 5-5-0 | -2.15u | 7, -0.72c, -2.09u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 589 | 30 | 5.1% | -0.35c | 1.61c | 15-14-0 | +1.52u |  |
| MK novig fair-2c | 589 | 11 | 1.9% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1891 | 93 | 4.9% | -0.88c | 1.1c | 42-45-2 | -1.21u |  |
| MK prophetx fair-2c | 1874 | 25 | 1.3% | -0.69c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2480 | 123 | 5.0% | -0.75c | 1.22c | 57-59-2 | +0.31u | criteria not met (118/50 graded, CLV not positive) |
| MK all fair-2c | 2463 | 36 | 1.5% | -0.63c | 2.16c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 52.

## Odds API credits (100K/month plan)

Study: 645/day, projected 19345/30 days. All monitors on the key: 2162/day, projected 64874/30 days. Remaining 97447; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T02:40:30Z: 17 games (16 in 24h), quotes {'prophetx': 1300, 'novig': 718, 'kalshi': 1160, 'polymarket_us': 1864}, 312 unmatched (5 book-games; fuzzy-matched 0), 2191 side/lines, polls [none_due], moves 0, new A 3 B 1, maker posted 0 filled 0, credits used 0 left 97447, 181s
- 2026-11-02T02:30:34Z: 17 games (16 in 24h), quotes {'prophetx': 1054, 'novig': 718, 'kalshi': 1168, 'polymarket_us': 1864}, 320 unmatched (5 book-games; fuzzy-matched 0), 2150 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 3, new A 16 B 0, maker posted 0 filled 0, credits used 6 left 97456, 182s
- 2026-11-02T02:20:31Z: 17 games (16 in 24h), quotes {'prophetx': 1298, 'novig': 718, 'kalshi': 1162, 'polymarket_us': 1736}, 328 unmatched (5 book-games; fuzzy-matched 0), 2096 side/lines, polls [none_due], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 0 left 97471, 182s
- 2026-11-02T02:10:31Z: 17 games (16 in 24h), quotes {'prophetx': 632, 'novig': 722, 'kalshi': 1122, 'polymarket_us': 1864}, 334 unmatched (5 book-games; fuzzy-matched 0), 2093 side/lines, polls [NFL:slow,NHL:slow], moves 0, new A 13 B 0, maker posted 0 filled 0, credits used 4 left 97480, 181s
- 2026-11-02T02:00:33Z: 18 games (15 in 24h), quotes {'prophetx': 238, 'novig': 724, 'kalshi': 1130, 'polymarket_us': 1864}, 266 unmatched (4 book-games; fuzzy-matched 0), 2193 side/lines, polls [NBA:fast; NBA:fast], moves 1, new A 9 B 0, maker posted 0 filled 1, credits used 4 left 97493, 301s
- 2026-11-02T01:50:28Z: 17 games (15 in 24h), quotes {'prophetx': 318, 'novig': 712, 'kalshi': 1138, 'polymarket_us': 1700}, 274 unmatched (4 book-games; fuzzy-matched 0), 2125 side/lines, polls [none_due; NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 97515, 256s
- 2026-11-02T01:46:43Z: 17 games (15 in 24h), quotes {'prophetx': 346, 'novig': 718, 'kalshi': 1142, 'polymarket_us': 1836}, 276 unmatched (4 book-games; fuzzy-matched 0), 2213 side/lines, polls [NFL:slow,NHL:slow; NBA:fast], moves 0, new A 10 B 0, maker posted 4 filled 0, credits used 6 left 97517, 181s
- 2026-11-02T01:40:22Z: 18 games (16 in 24h), quotes {'prophetx': 346, 'novig': 724, 'kalshi': 1138, 'polymarket_us': 1836}, 200 unmatched (3 book-games; fuzzy-matched 24), 2282 side/lines, polls [none_due; NBA:fast], moves 2, new A 22 B 0, maker posted 0 filled 0, credits used 2 left 97532, 231s
- 2026-11-02T01:32:17Z: 18 games (14 in 24h), quotes {'prophetx': 344, 'novig': 726, 'kalshi': 1122, 'polymarket_us': 1708}, 206 unmatched (4 book-games; fuzzy-matched 0), 2243 side/lines, polls [none_due; NBA:fast], moves 0, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 97543, 194s
- 2026-11-02T01:26:32Z: 18 games (14 in 24h), quotes {'prophetx': 392, 'novig': 724, 'kalshi': 1092, 'polymarket_us': 1712}, 210 unmatched (4 book-games; fuzzy-matched 0), 2186 side/lines, polls [NHL:slow; NBA:fast], moves 3, new A 15 B 0, maker posted 5 filled 0, credits used 4 left 97545, 316s
