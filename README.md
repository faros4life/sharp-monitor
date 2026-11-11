# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T17:24:59Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9216 | 8795 | -1.62c | 24.2% | 3831 | -1.04c | 8796 | 4543-4253-0 | -326.07u | -3.7% |  |  | criteria not met (8796/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2087 | 1954 | -3.1c | 19.1% | 429 | -2.64c | 1954 | 1002-952-0 | -160.61u | -8.2% |  |  | criteria not met (1954/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 157 | 154 | -0.75c | 31.2% | 144 | 0.15c | 154 | 66-88-0 | -13.85u | -9.0% |  |  | criteria not met (154/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 88 | 88 | -0.84c | 30.7% | 84 | 0.04c | 88 | 38-50-0 | -6.87u | -7.8% |  |  |  |
| B ref age 5m+ | 55 | 52 | -0.79c | 32.7% | 46 | 0.07c | 52 | 21-31-0 | -7.61u | -14.6% |  |  |  |
| M move-watch: gettable (sightings) | 424 | 414 | -0.64c | 34.5% | 412 | -0.54c | 418 | 216-197-5 | +0.92u | 0.2% | 0.19c | 28s | criteria not met (418/50 graded, CLV not positive) |
| M gettable, line moves | 219 | 212 | -0.81c | 34.0% | 211 | -0.82c | 214 | 107-103-4 | -5.70u | -2.7% | -0.2c | 30s |  |
| M gettable, price moves | 205 | 202 | -0.46c | 35.1% | 201 | -0.24c | 204 | 109-94-1 | +6.62u | 3.2% | 0.6c | 26s |  |
| M control: not gettable | 1734 | 1358 | -0.81c | 35.8% | 1331 | -1.23c | 1396 | 696-677-23 | -62.99u | -4.5% | 1.89c | 185s |  |
| M all moves | 2158 | 1772 | -0.77c | 35.5% | 1743 | -1.07c | 1814 | 912-874-28 | -62.07u | -3.4% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1084 | 1072 | 2.51c | 27.0% | 227 | 2.64c | 1073 | 480-593-0 | +285.27u | 26.6% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 104 | 101 | 0.15c | 44-57-0 | -8.30u | 68, -0.02c, -11.36u | negative |
| J2 B, NBA | 72 | 70 | 0.26c | 31-39-0 | -4.82u | 43, 0.07c, -3.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.31c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 247 | 241 | -0.62c | 119-119-3 | -7.77u | 139, -0.67c, -10.71u | negative |
| D1 B, unders (descriptive) | 34 | 33 | 0.45c | 18-15-0 | +4.54u | 30, 0.42c, +3.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 15 | 15 | 0.33c | 6-9-0 | -1.21u | 14, 0.32c, -2.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 91 | 91 | -0.2c | 50-39-2 | +3.16u | 47, -0.24c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2338 | 96 | 4.1% | -0.61c | 1.58c | 51-45-0 | +8.23u |  |
| MK novig fair-2c | 2333 | 37 | 1.6% | -0.16c | 2.51c | 23-14-0 | +11.42u |  |
| MK prophetx fair-1c | 5338 | 256 | 4.8% | -1.04c | 1.1c | 123-128-5 | +0.49u |  |
| MK prophetx fair-2c | 5301 | 89 | 1.7% | -0.63c | 2.04c | 43-46-0 | +0.62u |  |
| MK all fair-1c | 7676 | 352 | 4.6% | -0.93c | 1.25c | 174-173-5 | +8.73u | criteria not met (352/50 graded, CLV not positive) |
| MK all fair-2c | 7634 | 126 | 1.7% | -0.49c | 2.19c | 66-60-0 | +12.04u | criteria not met (126/50 graded, CLV not positive) |

A and B on the same side/line: 127.

## Odds API credits (100K/month plan)

Study: 629/day, projected 18865/30 days. All monitors on the key: 2364/day, projected 70906/30 days. Remaining 73666; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T17:21:57Z: 33 games (20 in 24h), quotes {'prophetx': 1470, 'novig': 718, 'kalshi': 1408, 'polymarket_us': 1874}, 0 unmatched (0 book-games; fuzzy-matched 3), 3260 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 73666, 182s
- 2026-11-11T17:12:21Z: 33 games (20 in 24h), quotes {'prophetx': 428, 'novig': 718, 'kalshi': 1410, 'polymarket_us': 1832}, 0 unmatched (0 book-games; fuzzy-matched 3), 2656 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 8 left 73692, 212s
- 2026-11-11T17:01:35Z: 33 games (20 in 24h), quotes {'prophetx': 1328, 'novig': 720, 'kalshi': 1414, 'polymarket_us': 1786}, 0 unmatched (0 book-games; fuzzy-matched 3), 3158 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 73719, 182s
- 2026-11-11T16:51:59Z: 33 games (19 in 24h), quotes {'prophetx': 1544, 'novig': 722, 'kalshi': 1414, 'polymarket_us': 1630}, 0 unmatched (0 book-games; fuzzy-matched 6), 3220 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 4, new A 1 B 0, maker posted 0 filled 0, credits used 8 left 73747, 184s
- 2026-11-11T16:46:32Z: 33 games (19 in 24h), quotes {'prophetx': 1432, 'novig': 720, 'kalshi': 1408, 'polymarket_us': 1642}, 0 unmatched (0 book-games; fuzzy-matched 3), 3158 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 73763, 182s
- 2026-11-11T16:40:22Z: 33 games (19 in 24h), quotes {'prophetx': 1214, 'novig': 716, 'kalshi': 1408, 'polymarket_us': 1344}, 0 unmatched (0 book-games; fuzzy-matched 3), 2930 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 73776, 181s
- 2026-11-11T16:34:43Z: 33 games (19 in 24h), quotes {'prophetx': 620, 'novig': 726, 'kalshi': 1408, 'polymarket_us': 1586}, 0 unmatched (0 book-games; fuzzy-matched 3), 2644 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 73793, 185s
- 2026-11-11T16:29:52Z: 33 games (19 in 24h), quotes {'prophetx': 1196, 'novig': 716, 'kalshi': 1404, 'polymarket_us': 1434}, 0 unmatched (0 book-games; fuzzy-matched 6), 2952 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 6, new A 3 B 0, maker posted 0 filled 0, credits used 8 left 73810, 182s
- 2026-11-11T16:22:24Z: 33 games (19 in 24h), quotes {'prophetx': 1544, 'novig': 722, 'kalshi': 1404, 'polymarket_us': 1762}, 0 unmatched (0 book-games; fuzzy-matched 3), 3251 side/lines, polls [none_due], moves 0, new A 1 B 1, maker posted 0 filled 0, credits used 0 left 73838, 183s
- 2026-11-11T16:12:39Z: 33 games (19 in 24h), quotes {'prophetx': 750, 'novig': 728, 'kalshi': 1398, 'polymarket_us': 1844}, 0 unmatched (0 book-games; fuzzy-matched 3), 2815 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 73853, 184s
