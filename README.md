# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-09T03:54:00Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8048 | 7858 | -1.61c | 23.7% | 3453 | -1.03c | 7692 | 3970-3722-0 | -260.52u | -3.4% |  |  | criteria not met (7692/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1795 | 1740 | -3.1c | 18.3% | 384 | -2.64c | 1680 | 862-818-0 | -136.34u | -8.1% |  |  | criteria not met (1680/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 135 | 132 | -1.07c | 26.5% | 123 | -0.09c | 130 | 56-74-0 | -11.33u | -8.7% |  |  | criteria not met (130/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 78 | -1.13c | 25.6% | 74 | -0.19c | 77 | 35-42-0 | -2.47u | -3.2% |  |  |  |
| B ref age 5m+ | 48 | 45 | -1.21c | 26.7% | 40 | -0.15c | 44 | 16-28-0 | -10.25u | -23.3% |  |  |  |
| M move-watch: gettable (sightings) | 366 | 362 | -0.59c | 35.1% | 362 | -0.56c | 359 | 185-169-5 | -3.48u | -1.0% | 0.23c | 25s | criteria not met (359/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 191 | 189 | -0.69c | 34.4% | 190 | -0.82c | 185 | 92-89-4 | -5.37u | -2.9% | -0.08c | 26s |  |
| M gettable, price moves | 175 | 173 | -0.49c | 35.8% | 172 | -0.28c | 174 | 93-80-1 | +1.89u | 1.1% | 0.56c | 23s |  |
| M control: not gettable | 1499 | 1208 | -0.77c | 36.3% | 1190 | -1.18c | 1207 | 599-587-21 | -58.31u | -4.8% | 1.84c | 183s |  |
| M all moves | 1865 | 1570 | -0.73c | 36.0% | 1552 | -1.04c | 1566 | 784-756-26 | -61.79u | -3.9% | 1.52c | 121s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1057 | 1038 | 2.7c | 27.3% | 222 | 2.91c | 1039 | 461-578-0 | +281.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 86 | 81 | -0.24c | 35-46-0 | -7.69u | 56, -0.46c, -12.16u | negative |
| J2 B, NBA | 57 | 52 | -0.26c | 22-30-0 | -6.22u | 32, -0.63c, -5.16u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 48 | -0.46c | 23-25-0 | -0.07u | 38, -0.73c, +1.46u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 214 | 207 | -0.64c | 102-102-3 | -6.47u | 122, -0.65c, -10.94u | negative |
| D1 B, unders (descriptive) | 27 | 23 | 0.11c | 13-10-0 | +3.89u | 22, 0.06c, +2.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 18 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 66 | -0.21c | 36-28-2 | -2.54u | 38, -0.28c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2023 | 82 | 4.1% | -0.62c | 1.58c | 41-40-0 | +2.44u |  |
| MK novig fair-2c | 2019 | 30 | 1.5% | -0.35c | 2.51c | 19-11-0 | +9.90u |  |
| MK prophetx fair-1c | 4873 | 231 | 4.7% | -1.02c | 1.1c | 109-114-5 | -0.11u |  |
| MK prophetx fair-2c | 4840 | 76 | 1.6% | -0.59c | 2.04c | 37-39-0 | +1.11u |  |
| MK all fair-1c | 6896 | 313 | 4.5% | -0.92c | 1.24c | 150-154-5 | +2.33u | criteria not met (309/50 graded, CLV not positive) |
| MK all fair-2c | 6859 | 106 | 1.5% | -0.52c | 2.18c | 56-50-0 | +11.01u | criteria not met (106/50 graded, CLV not positive) |

A and B on the same side/line: 107.

## Odds API credits (100K/month plan)

Study: 653/day, projected 19604/30 days. All monitors on the key: 2397/day, projected 71919/30 days. Remaining 79307; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-09T03:51:20Z: 11 games (11 in 24h), quotes {'prophetx': 936, 'novig': 642, 'kalshi': 726, 'polymarket_us': 1232}, 272 unmatched (5 book-games; fuzzy-matched 0), 1629 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 79307, 160s
- 2026-11-09T03:41:36Z: 11 games (11 in 24h), quotes {'prophetx': 614, 'novig': 685, 'kalshi': 630, 'polymarket_us': 1232}, 295 unmatched (5 book-games; fuzzy-matched 0), 1464 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 79318, 173s
- 2026-11-09T03:31:41Z: 10 games (10 in 24h), quotes {'prophetx': 622, 'novig': 679, 'kalshi': 644, 'polymarket_us': 1232}, 453 unmatched (8 book-games; fuzzy-matched 0), 1386 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 79327, 170s
- 2026-11-09T03:21:37Z: 9 games (9 in 24h), quotes {'prophetx': 516, 'novig': 628, 'kalshi': 648, 'polymarket_us': 1108}, 464 unmatched (8 book-games; fuzzy-matched 0), 1095 side/lines, polls [none_due], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 0 left 79343, 158s
- 2026-11-09T03:11:05Z: 9 games (9 in 24h), quotes {'prophetx': 622, 'novig': 610, 'kalshi': 676, 'polymarket_us': 1106}, 489 unmatched (9 book-games; fuzzy-matched 0), 1142 side/lines, polls [none_due], moves 0, new A 11 B 1, maker posted 0 filled 0, credits used 0 left 79352, 154s
- 2026-11-09T03:01:57Z: 9 games (9 in 24h), quotes {'prophetx': 428, 'novig': 560, 'kalshi': 700, 'polymarket_us': 1106}, 494 unmatched (9 book-games; fuzzy-matched 0), 1088 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 2, new A 29 B 0, maker posted 0 filled 0, credits used 6 left 79361, 139s
- 2026-11-09T02:51:03Z: 9 games (8 in 24h), quotes {'prophetx': 556, 'novig': 528, 'kalshi': 702, 'polymarket_us': 948}, 400 unmatched (8 book-games; fuzzy-matched 0), 1009 side/lines, polls [none_due], moves 0, new A 21 B 2, maker posted 0 filled 0, credits used 0 left 79378, 131s
- 2026-11-09T02:41:39Z: 8 games (7 in 24h), quotes {'prophetx': 600, 'novig': 512, 'kalshi': 718, 'polymarket_us': 948}, 636 unmatched (13 book-games; fuzzy-matched 0), 889 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 79396, 157s
- 2026-11-09T02:31:37Z: 8 games (7 in 24h), quotes {'prophetx': 508, 'novig': 526, 'kalshi': 754, 'polymarket_us': 948}, 672 unmatched (15 book-games; fuzzy-matched 0), 886 side/lines, polls [NFL:slow,NBA:slow,NHL:slow], moves 1, new A 42 B 0, maker posted 0 filled 0, credits used 6 left 79405, 132s
- 2026-11-09T02:21:20Z: 8 games (6 in 24h), quotes {'prophetx': 480, 'novig': 432, 'kalshi': 728, 'polymarket_us': 920}, 693 unmatched (15 book-games; fuzzy-matched 0), 813 side/lines, polls [none_due], moves 0, new A 13 B 0, maker posted 0 filled 0, credits used 0 left 79439, 111s
