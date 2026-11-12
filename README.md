# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T00:37:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9324 | 9083 | -1.61c | 24.3% | 3944 | -1.05c | 8796 | 4543-4253-0 | -326.07u | -3.7% |  |  | criteria not met (8796/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2098 | 2008 | -3.08c | 19.1% | 448 | -2.64c | 1954 | 1002-952-0 | -160.61u | -8.2% |  |  | criteria not met (1954/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 159 | 157 | -0.73c | 31.8% | 147 | 0.15c | 154 | 66-88-0 | -13.85u | -9.0% |  |  | criteria not met (154/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 14 | -0.1c | 28.6% | 14 | 1.06c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 89 | 89 | -0.82c | 31.5% | 85 | 0.05c | 88 | 38-50-0 | -6.87u | -7.8% |  |  |  |
| B ref age 5m+ | 55 | 54 | -0.74c | 33.3% | 48 | 0.06c | 52 | 21-31-0 | -7.61u | -14.6% |  |  |  |
| M move-watch: gettable (sightings) | 437 | 422 | -0.6c | 35.1% | 420 | -0.51c | 418 | 216-197-5 | +0.92u | 0.2% | 0.22c | 27s | criteria not met (418/50 graded, CLV not positive) |
| M gettable, line moves | 225 | 217 | -0.76c | 35.0% | 216 | -0.78c | 214 | 107-103-4 | -5.70u | -2.7% | -0.15c | 28s |  |
| M gettable, price moves | 212 | 205 | -0.44c | 35.1% | 204 | -0.23c | 204 | 109-94-1 | +6.62u | 3.2% | 0.62c | 26s |  |
| M control: not gettable | 1787 | 1388 | -0.82c | 35.7% | 1361 | -1.24c | 1396 | 696-677-23 | -62.99u | -4.5% | 1.87c | 184s |  |
| M all moves | 2224 | 1810 | -0.77c | 35.5% | 1781 | -1.07c | 1814 | 912-874-28 | -62.07u | -3.4% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1084 | 1080 | 2.47c | 26.9% | 230 | 2.5c | 1073 | 480-593-0 | +285.27u | 26.6% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 105 | 101 | 0.15c | 44-57-0 | -8.30u | 68, -0.02c, -11.36u | negative |
| J2 B, NBA | 73 | 70 | 0.33c | 31-39-0 | -4.82u | 43, 0.18c, -3.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 62 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.31c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 258 | 241 | -0.58c | 119-119-3 | -7.77u | 139, -0.63c, -10.71u | negative |
| D1 B, unders (descriptive) | 35 | 33 | 0.57c | 18-15-0 | +4.54u | 30, 0.55c, +3.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 16 | 15 | 0.34c | 6-9-0 | -1.21u | 14, 0.33c, -2.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 93 | 91 | -0.2c | 50-39-2 | +3.16u | 47, -0.24c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2444 | 103 | 4.3% | -0.59c | 1.58c | 51-45-0 | +8.23u |  |
| MK novig fair-2c | 2437 | 40 | 1.7% | -0.19c | 2.51c | 23-14-0 | +11.42u |  |
| MK prophetx fair-1c | 5605 | 268 | 4.8% | -1.04c | 1.1c | 123-128-5 | +0.49u |  |
| MK prophetx fair-2c | 5565 | 97 | 1.8% | -0.61c | 2.05c | 43-46-0 | +0.62u |  |
| MK all fair-1c | 8049 | 371 | 4.6% | -0.92c | 1.25c | 174-173-5 | +8.73u | criteria not met (352/50 graded, CLV not positive) |
| MK all fair-2c | 8002 | 137 | 1.7% | -0.48c | 2.19c | 66-60-0 | +12.04u | criteria not met (126/50 graded, CLV not positive) |

A and B on the same side/line: 129.

## Odds API credits (100K/month plan)

Study: 642/day, projected 19264/30 days. All monitors on the key: 2400/day, projected 71988/30 days. Remaining 72411; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T00:32:32Z: 28 games (21 in 24h), quotes {'prophetx': 1074, 'novig': 716, 'kalshi': 1390, 'polymarket_us': 1460}, 538 unmatched (7 book-games; fuzzy-matched 2), 2293 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 6 B 1, maker posted 59 filled 0, credits used 10 left 72411, 301s
- 2026-11-12T00:21:35Z: 29 games (22 in 24h), quotes {'prophetx': 1240, 'novig': 716, 'kalshi': 1404, 'polymarket_us': 1678}, 440 unmatched (6 book-games; fuzzy-matched 3), 2669 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 4 B 0, maker posted 10 filled 2, credits used 14 left 72472, 351s
- 2026-11-12T00:11:37Z: 32 games (25 in 24h), quotes {'prophetx': 1444, 'novig': 724, 'kalshi': 1408, 'polymarket_us': 1572}, 126 unmatched (2 book-games; fuzzy-matched 3), 2981 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 56 filled 2, credits used 6 left 72520, 184s
- 2026-11-12T00:02:33Z: 33 games (26 in 24h), quotes {'prophetx': 1444, 'novig': 716, 'kalshi': 1406, 'polymarket_us': 1856}, 252 unmatched (2 book-games; fuzzy-matched 6), 2997 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 14 filled 2, credits used 12 left 72553, 302s
- 2026-11-11T23:52:46Z: 33 games (20 in 24h), quotes {'prophetx': 1578, 'novig': 726, 'kalshi': 1412, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 3), 3302 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 4 B 0, maker posted 0 filled 0, credits used 8 left 72594, 257s
- 2026-11-11T23:47:11Z: 33 games (20 in 24h), quotes {'prophetx': 1578, 'novig': 726, 'kalshi': 1406, 'polymarket_us': 1868}, 0 unmatched (0 book-games; fuzzy-matched 3), 3304 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 1, maker posted 34 filled 5, credits used 6 left 72623, 184s
- 2026-11-11T23:40:48Z: 33 games (20 in 24h), quotes {'prophetx': 1312, 'novig': 726, 'kalshi': 1408, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 3), 3144 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 10 B 0, maker posted 0 filled 3, credits used 6 left 72637, 263s
- 2026-11-11T23:31:36Z: 33 games (20 in 24h), quotes {'prophetx': 1548, 'novig': 720, 'kalshi': 1410, 'polymarket_us': 1768}, 0 unmatched (0 book-games; fuzzy-matched 6), 3241 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 5 B 0, maker posted 24 filled 1, credits used 14 left 72674, 302s
- 2026-11-11T23:22:29Z: 33 games (20 in 24h), quotes {'prophetx': 1506, 'novig': 726, 'kalshi': 1414, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 3), 3271 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 72737, 252s
- 2026-11-11T23:16:54Z: 33 games (20 in 24h), quotes {'prophetx': 1578, 'novig': 724, 'kalshi': 1410, 'polymarket_us': 1876}, 0 unmatched (0 book-games; fuzzy-matched 3), 3311 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 6 left 72760, 183s
