# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T04:54:30Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9090 | 8795 | -1.62c | 24.2% | 3831 | -1.04c | 8614 | 4438-4176-0 | -308.22u | -3.6% |  |  | criteria not met (8614/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2071 | 1954 | -3.1c | 19.1% | 429 | -2.64c | 1903 | 972-931-0 | -154.29u | -8.1% |  |  | criteria not met (1903/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 155 | 154 | -0.75c | 31.2% | 144 | 0.15c | 148 | 65-83-0 | -10.23u | -6.9% |  |  | criteria not met (148/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 13 | 7-6-0 | +1.63u | 12.5% |  |  |  |
| B ref age 1-5m | 88 | 88 | -0.84c | 30.7% | 84 | 0.04c | 84 | 37-47-0 | -5.25u | -6.3% |  |  |  |
| B ref age 5m+ | 53 | 52 | -0.79c | 32.7% | 46 | 0.07c | 51 | 21-30-0 | -6.61u | -13.0% |  |  |  |
| M move-watch: gettable (sightings) | 419 | 414 | -0.64c | 34.5% | 412 | -0.54c | 412 | 215-192-5 | +5.46u | 1.3% | 0.19c | 27s | criteria not met (412/50 graded, CLV not positive) |
| M gettable, line moves | 214 | 212 | -0.81c | 34.0% | 211 | -0.82c | 212 | 107-101-4 | -3.70u | -1.7% | -0.2c | 28s |  |
| M gettable, price moves | 205 | 202 | -0.46c | 35.1% | 201 | -0.24c | 200 | 108-91-1 | +9.16u | 4.6% | 0.6c | 26s |  |
| M control: not gettable | 1699 | 1358 | -0.81c | 35.8% | 1331 | -1.23c | 1360 | 675-662-23 | -65.75u | -4.8% | 1.89c | 184s |  |
| M all moves | 2118 | 1772 | -0.77c | 35.5% | 1743 | -1.07c | 1772 | 890-854-28 | -60.29u | -3.4% | 1.55c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1084 | 1072 | 2.51c | 27.0% | 227 | 2.64c | 1062 | 477-585-0 | +291.44u | 27.4% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 102 | 96 | 0.15c | 43-53-0 | -5.68u | 65, -0.02c, -8.36u | negative |
| J2 B, NBA | 70 | 65 | 0.26c | 30-35-0 | -2.21u | 40, 0.07c, -0.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 57 | -0.01c | 26-31-0 | -2.70u | 45, -0.31c, -1.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 242 | 236 | -0.62c | 119-114-3 | -2.77u | 137, -0.67c, -8.71u | negative |
| D1 B, unders (descriptive) | 33 | 32 | 0.45c | 18-14-0 | +5.54u | 29, 0.42c, +4.33u | descriptive only |
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

Study: 647/day, projected 19399/30 days. All monitors on the key: 2392/day, projected 71771/30 days. Remaining 74483; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T04:51:26Z: 17 games (17 in 24h), quotes {'prophetx': 1266, 'novig': 726, 'kalshi': 1072, 'polymarket_us': 1442}, 194 unmatched (5 book-games; fuzzy-matched 2), 2392 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 74483, 183s
- 2026-11-11T04:41:56Z: 17 games (17 in 24h), quotes {'prophetx': 1266, 'novig': 718, 'kalshi': 1110, 'polymarket_us': 1594}, 298 unmatched (8 book-games; fuzzy-matched 4), 2393 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 4, new A 6 B 0, maker posted 0 filled 0, credits used 6 left 74492, 182s
- 2026-11-11T04:31:28Z: 17 games (17 in 24h), quotes {'prophetx': 1228, 'novig': 720, 'kalshi': 1144, 'polymarket_us': 1584}, 312 unmatched (8 book-games; fuzzy-matched 2), 2392 side/lines, polls [none_due], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 0 left 74507, 182s
- 2026-11-11T04:21:53Z: 17 games (17 in 24h), quotes {'prophetx': 1082, 'novig': 722, 'kalshi': 1196, 'polymarket_us': 1708}, 440 unmatched (9 book-games; fuzzy-matched 4), 2322 side/lines, polls [NHL:slow], moves 2, new A 15 B 0, maker posted 0 filled 0, credits used 2 left 74525, 182s
- 2026-11-11T04:11:53Z: 18 games (18 in 24h), quotes {'prophetx': 1214, 'novig': 726, 'kalshi': 1198, 'polymarket_us': 1620}, 178 unmatched (5 book-games; fuzzy-matched 5), 2497 side/lines, polls [NCAAF:slow,NBA:fast], moves 0, new A 18 B 0, maker posted 0 filled 0, credits used 4 left 74536, 182s
- 2026-11-11T04:01:46Z: 18 games (18 in 24h), quotes {'prophetx': 1210, 'novig': 726, 'kalshi': 1158, 'polymarket_us': 1640}, 192 unmatched (5 book-games; fuzzy-matched 10), 2495 side/lines, polls [NBA:fast,NHL:slow; NBA:fast], moves 1, new A 13 B 0, maker posted 0 filled 0, credits used 6 left 74549, 301s
- 2026-11-11T03:51:25Z: 17 games (17 in 24h), quotes {'prophetx': 1282, 'novig': 728, 'kalshi': 1180, 'polymarket_us': 1520}, 212 unmatched (5 book-games; fuzzy-matched 4), 2442 side/lines, polls [none_due; NBA:fast], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 2 left 74577, 181s
- 2026-11-11T03:45:27Z: 17 games (17 in 24h), quotes {'prophetx': 1282, 'novig': 712, 'kalshi': 1184, 'polymarket_us': 1612}, 214 unmatched (6 book-games; fuzzy-matched 5), 2448 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 74591, 182s
- 2026-11-11T03:40:25Z: 17 games (17 in 24h), quotes {'prophetx': 1170, 'novig': 728, 'kalshi': 1164, 'polymarket_us': 1708}, 238 unmatched (6 book-games; fuzzy-matched 5), 2473 side/lines, polls [none_due; NBA:fast], moves 0, new A 10 B 0, maker posted 4 filled 0, credits used 2 left 74608, 183s
- 2026-11-11T03:32:17Z: 17 games (17 in 24h), quotes {'prophetx': 1170, 'novig': 726, 'kalshi': 1166, 'polymarket_us': 1708}, 268 unmatched (7 book-games; fuzzy-matched 10), 2472 side/lines, polls [NBA:fast,NHL:slow; NBA:fast], moves 1, new A 11 B 0, maker posted 4 filled 0, credits used 6 left 74623, 301s
