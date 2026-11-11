# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T21:17:00Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9249 | 8795 | -1.62c | 24.2% | 3831 | -1.04c | 8796 | 4543-4253-0 | -326.07u | -3.7% |  |  | criteria not met (8796/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2087 | 1954 | -3.1c | 19.1% | 429 | -2.64c | 1954 | 1002-952-0 | -160.61u | -8.2% |  |  | criteria not met (1954/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 157 | 154 | -0.75c | 31.2% | 144 | 0.15c | 154 | 66-88-0 | -13.85u | -9.0% |  |  | criteria not met (154/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 88 | 88 | -0.84c | 30.7% | 84 | 0.04c | 88 | 38-50-0 | -6.87u | -7.8% |  |  |  |
| B ref age 5m+ | 55 | 52 | -0.79c | 32.7% | 46 | 0.07c | 52 | 21-31-0 | -7.61u | -14.6% |  |  |  |
| M move-watch: gettable (sightings) | 428 | 414 | -0.64c | 34.5% | 412 | -0.54c | 418 | 216-197-5 | +0.92u | 0.2% | 0.19c | 28s | criteria not met (418/50 graded, CLV not positive) |
| M gettable, line moves | 220 | 212 | -0.81c | 34.0% | 211 | -0.82c | 214 | 107-103-4 | -5.70u | -2.7% | -0.2c | 29s |  |
| M gettable, price moves | 208 | 202 | -0.46c | 35.1% | 201 | -0.24c | 204 | 109-94-1 | +6.62u | 3.2% | 0.6c | 27s |  |
| M control: not gettable | 1758 | 1358 | -0.81c | 35.8% | 1331 | -1.23c | 1396 | 696-677-23 | -62.99u | -4.5% | 1.89c | 185s |  |
| M all moves | 2186 | 1772 | -0.77c | 35.5% | 1743 | -1.07c | 1814 | 912-874-28 | -62.07u | -3.4% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1084 | 1072 | 2.51c | 27.0% | 227 | 2.64c | 1073 | 480-593-0 | +285.27u | 26.6% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 104 | 101 | 0.15c | 44-57-0 | -8.30u | 68, -0.02c, -11.36u | negative |
| J2 B, NBA | 72 | 70 | 0.26c | 31-39-0 | -4.82u | 43, 0.07c, -3.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.31c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 249 | 241 | -0.62c | 119-119-3 | -7.77u | 139, -0.67c, -10.71u | negative |
| D1 B, unders (descriptive) | 34 | 33 | 0.45c | 18-15-0 | +4.54u | 30, 0.42c, +3.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 15 | 15 | 0.33c | 6-9-0 | -1.21u | 14, 0.32c, -2.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 93 | 91 | -0.2c | 50-39-2 | +3.16u | 47, -0.24c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2372 | 96 | 4.1% | -0.61c | 1.58c | 51-45-0 | +8.23u |  |
| MK novig fair-2c | 2367 | 37 | 1.6% | -0.16c | 2.51c | 23-14-0 | +11.42u |  |
| MK prophetx fair-1c | 5442 | 258 | 4.8% | -1.04c | 1.1c | 123-128-5 | +0.49u |  |
| MK prophetx fair-2c | 5405 | 91 | 1.7% | -0.63c | 2.04c | 43-46-0 | +0.62u |  |
| MK all fair-1c | 7814 | 354 | 4.6% | -0.93c | 1.25c | 174-173-5 | +8.73u | criteria not met (352/50 graded, CLV not positive) |
| MK all fair-2c | 7772 | 128 | 1.7% | -0.49c | 2.19c | 66-60-0 | +12.04u | criteria not met (126/50 graded, CLV not positive) |

A and B on the same side/line: 127.

## Odds API credits (100K/month plan)

Study: 634/day, projected 19018/30 days. All monitors on the key: 2374/day, projected 71207/30 days. Remaining 73134; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T21:13:44Z: 33 games (20 in 24h), quotes {'prophetx': 518, 'novig': 720, 'kalshi': 1410, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 3), 2726 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 73134, 197s
- 2026-11-11T21:07:06Z: 33 games (20 in 24h), quotes {'prophetx': 684, 'novig': 724, 'kalshi': 1410, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 2), 2828 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 4 filled 0, credits used 6 left 73140, 245s
- 2026-11-11T20:59:27Z: 33 games (20 in 24h), quotes {'prophetx': 1562, 'novig': 720, 'kalshi': 1412, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 6), 3315 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 1 B 0, maker posted 108 filled 0, credits used 14 left 73155, 301s
- 2026-11-11T20:12:02Z: 33 games (20 in 24h), quotes {'prophetx': 546, 'novig': 726, 'kalshi': 1408, 'polymarket_us': 1778}, 0 unmatched (0 book-games; fuzzy-matched 66), 2700 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 73217, 216s
- 2026-11-11T20:02:10Z: 33 games (20 in 24h), quotes {'prophetx': 458, 'novig': 720, 'kalshi': 1400, 'polymarket_us': 1754}, 0 unmatched (0 book-games; fuzzy-matched 3), 2628 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 2 B 0, maker posted 4 filled 1, credits used 14 left 73236, 348s
- 2026-11-11T19:51:35Z: 33 games (20 in 24h), quotes {'prophetx': 1330, 'novig': 716, 'kalshi': 1402, 'polymarket_us': 1844}, 0 unmatched (0 book-games; fuzzy-matched 3), 3151 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 0 B 0, maker posted 4 filled 1, credits used 6 left 73284, 235s
- 2026-11-11T19:42:44Z: 33 games (20 in 24h), quotes {'prophetx': 1384, 'novig': 716, 'kalshi': 1402, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 6), 3215 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 44 filled 0, credits used 12 left 73303, 302s
- 2026-11-11T19:32:29Z: 33 games (20 in 24h), quotes {'prophetx': 940, 'novig': 720, 'kalshi': 1400, 'polymarket_us': 1634}, 0 unmatched (0 book-games; fuzzy-matched 3), 2853 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 8 filled 0, credits used 14 left 73332, 325s
- 2026-11-11T19:22:03Z: 33 games (20 in 24h), quotes {'prophetx': 0, 'novig': 718, 'kalshi': 1396, 'polymarket_us': 1810}, 0 unmatched (0 book-games; fuzzy-matched 2), 2428 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 5 B 0, maker posted 8 filled 0, credits used 12 left 73357, 340s
- 2026-11-11T19:12:25Z: 33 games (20 in 24h), quotes {'prophetx': 1540, 'novig': 714, 'kalshi': 1398, 'polymarket_us': 1706}, 0 unmatched (0 book-games; fuzzy-matched 3), 3243 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 24 filled 2, credits used 8 left 73382, 183s
