# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T03:54:26Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9033 | 8745 | -1.61c | 24.3% | 3818 | -1.05c | 8492 | 4385-4107-0 | -281.25u | -3.3% |  |  | criteria not met (8492/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2049 | 1934 | -3.11c | 19.1% | 425 | -2.67c | 1874 | 961-913-0 | -147.43u | -7.9% |  |  | criteria not met (1874/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 155 | 154 | -0.75c | 31.2% | 144 | 0.15c | 146 | 65-81-0 | -8.23u | -5.6% |  |  | criteria not met (146/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 13 | 7-6-0 | +1.63u | 12.5% |  |  |  |
| B ref age 1-5m | 88 | 88 | -0.84c | 30.7% | 84 | 0.04c | 83 | 37-46-0 | -4.25u | -5.1% |  |  |  |
| B ref age 5m+ | 53 | 52 | -0.79c | 32.7% | 46 | 0.07c | 50 | 21-29-0 | -5.61u | -11.2% |  |  |  |
| M move-watch: gettable (sightings) | 419 | 412 | -0.63c | 34.7% | 410 | -0.52c | 408 | 215-188-5 | +9.46u | 2.3% | 0.2c | 27s | criteria not met (408/50 graded, CLV not positive) |
| M gettable, line moves | 214 | 211 | -0.79c | 34.1% | 210 | -0.79c | 209 | 107-98-4 | -0.70u | -0.3% | -0.17c | 28s |  |
| M gettable, price moves | 205 | 201 | -0.46c | 35.3% | 200 | -0.24c | 199 | 108-90-1 | +10.16u | 5.1% | 0.6c | 26s |  |
| M control: not gettable | 1692 | 1349 | -0.8c | 35.7% | 1322 | -1.22c | 1349 | 670-656-23 | -64.07u | -4.7% | 1.89c | 184s |  |
| M all moves | 2111 | 1761 | -0.76c | 35.5% | 1732 | -1.06c | 1757 | 885-844-28 | -54.61u | -3.1% | 1.56c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1076 | 1067 | 2.52c | 26.8% | 227 | 2.64c | 1062 | 477-585-0 | +291.44u | 27.4% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 102 | 94 | 0.15c | 43-51-0 | -3.68u | 64, -0.02c, -7.36u | negative |
| J2 B, NBA | 70 | 65 | 0.26c | 30-35-0 | -2.21u | 40, 0.07c, -0.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 56 | -0.01c | 26-30-0 | -1.70u | 44, -0.31c, -0.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 242 | 232 | -0.6c | 119-110-3 | +1.23u | 135, -0.62c, -6.71u | negative |
| D1 B, unders (descriptive) | 33 | 30 | 0.45c | 18-12-0 | +7.54u | 28, 0.42c, +5.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 20 | -0.24c | 7-13-0 | -5.02u | 18, -0.33c, -3.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 15 | 14 | 0.33c | 6-8-0 | -0.21u | 13, 0.32c, -1.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 91 | 90 | -0.2c | 49-39-2 | +2.70u | 46, -0.24c, -0.59u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2338 | 96 | 4.1% | -0.61c | 1.58c | 50-44-0 | +8.19u |  |
| MK novig fair-2c | 2333 | 37 | 1.6% | -0.16c | 2.51c | 22-13-0 | +11.34u |  |
| MK prophetx fair-1c | 5338 | 256 | 4.8% | -1.04c | 1.1c | 119-126-5 | -1.63u |  |
| MK prophetx fair-2c | 5301 | 89 | 1.7% | -0.63c | 2.04c | 40-44-0 | -0.55u |  |
| MK all fair-1c | 7676 | 352 | 4.6% | -0.93c | 1.25c | 169-170-5 | +6.56u | criteria not met (344/50 graded, CLV not positive) |
| MK all fair-2c | 7634 | 126 | 1.7% | -0.49c | 2.19c | 62-57-0 | +10.79u | criteria not met (119/50 graded, CLV not positive) |

A and B on the same side/line: 125.

## Odds API credits (100K/month plan)

Study: 647/day, projected 19418/30 days. All monitors on the key: 2393/day, projected 71783/30 days. Remaining 74577; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T03:51:25Z: 17 games (17 in 24h), quotes {'prophetx': 1282, 'novig': 728, 'kalshi': 1180, 'polymarket_us': 1520}, 212 unmatched (5 book-games; fuzzy-matched 4), 2442 side/lines, polls [none_due; NBA:fast], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 2 left 74577, 181s
- 2026-11-11T03:45:27Z: 17 games (17 in 24h), quotes {'prophetx': 1282, 'novig': 712, 'kalshi': 1184, 'polymarket_us': 1612}, 214 unmatched (6 book-games; fuzzy-matched 5), 2448 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 74591, 182s
- 2026-11-11T03:40:25Z: 17 games (17 in 24h), quotes {'prophetx': 1170, 'novig': 728, 'kalshi': 1164, 'polymarket_us': 1708}, 238 unmatched (6 book-games; fuzzy-matched 5), 2473 side/lines, polls [none_due; NBA:fast], moves 0, new A 10 B 0, maker posted 4 filled 0, credits used 2 left 74608, 183s
- 2026-11-11T03:32:17Z: 17 games (17 in 24h), quotes {'prophetx': 1170, 'novig': 726, 'kalshi': 1166, 'polymarket_us': 1708}, 268 unmatched (7 book-games; fuzzy-matched 10), 2472 side/lines, polls [NBA:fast,NHL:slow; NBA:fast], moves 1, new A 11 B 0, maker posted 4 filled 0, credits used 6 left 74623, 301s
- 2026-11-11T03:21:26Z: 17 games (17 in 24h), quotes {'prophetx': 1164, 'novig': 730, 'kalshi': 1190, 'polymarket_us': 1412}, 292 unmatched (8 book-games; fuzzy-matched 5), 2252 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 4 left 74661, 185s
- 2026-11-11T03:11:47Z: 16 games (16 in 24h), quotes {'prophetx': 1164, 'novig': 728, 'kalshi': 1216, 'polymarket_us': 1582}, 318 unmatched (8 book-games; fuzzy-matched 5), 2252 side/lines, polls [NBA:fast; NBA:fast], moves 1, new A 19 B 0, maker posted 0 filled 0, credits used 4 left 74673, 323s
- 2026-11-11T03:01:31Z: 18 games (16 in 24h), quotes {'prophetx': 1016, 'novig': 722, 'kalshi': 1224, 'polymarket_us': 1540}, 252 unmatched (7 book-games; fuzzy-matched 5), 2270 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 11 B 0, maker posted 0 filled 0, credits used 4 left 74711, 182s
- 2026-11-11T02:55:55Z: 18 games (16 in 24h), quotes {'prophetx': 1062, 'novig': 726, 'kalshi': 1240, 'polymarket_us': 0}, 270 unmatched (7 book-games; fuzzy-matched 3), 1622 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 11 filled 1, credits used 6 left 74728, 183s
- 2026-11-11T02:50:35Z: 18 games (16 in 24h), quotes {'prophetx': 1092, 'novig': 724, 'kalshi': 1280, 'polymarket_us': 1250}, 326 unmatched (9 book-games; fuzzy-matched 3), 2177 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 4 left 74751, 183s
- 2026-11-11T02:44:48Z: 18 games (16 in 24h), quotes {'prophetx': 1092, 'novig': 726, 'kalshi': 1256, 'polymarket_us': 1496}, 340 unmatched (10 book-games; fuzzy-matched 3), 2299 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 74763, 213s
