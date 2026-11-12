# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T01:47:31Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9387 | 9300 | -1.63c | 24.3% | 4020 | -1.08c | 8796 | 4543-4253-0 | -326.07u | -3.7% |  |  | criteria not met (8796/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2107 | 2092 | -3.09c | 19.3% | 468 | -2.73c | 1954 | 1002-952-0 | -160.61u | -8.2% |  |  | criteria not met (1954/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 161 | 161 | -0.76c | 31.1% | 151 | 0.14c | 154 | 66-88-0 | -13.85u | -9.0% |  |  | criteria not met (154/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 15 | -0.15c | 26.7% | 15 | 1.01c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 89 | 89 | -0.82c | 31.5% | 85 | 0.05c | 88 | 38-50-0 | -6.87u | -7.8% |  |  |  |
| B ref age 5m+ | 57 | 57 | -0.83c | 31.6% | 51 | 0.04c | 52 | 21-31-0 | -7.61u | -14.6% |  |  |  |
| M move-watch: gettable (sightings) | 438 | 429 | -0.62c | 35.0% | 427 | -0.52c | 418 | 216-197-5 | +0.92u | 0.2% | 0.22c | 27s | criteria not met (418/50 graded, CLV not positive) |
| M gettable, line moves | 226 | 221 | -0.78c | 34.8% | 220 | -0.79c | 214 | 107-103-4 | -5.70u | -2.7% | -0.15c | 28s |  |
| M gettable, price moves | 212 | 208 | -0.44c | 35.1% | 207 | -0.24c | 204 | 109-94-1 | +6.62u | 3.2% | 0.61c | 26s |  |
| M control: not gettable | 1795 | 1418 | -0.84c | 35.5% | 1388 | -1.25c | 1396 | 696-677-23 | -62.99u | -4.5% | 1.87c | 184s |  |
| M all moves | 2233 | 1847 | -0.79c | 35.4% | 1815 | -1.07c | 1814 | 912-874-28 | -62.07u | -3.4% | 1.55c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1086 | 1083 | 2.45c | 27.1% | 232 | 2.44c | 1073 | 480-593-0 | +285.27u | 26.6% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 107 | 101 | 0.13c | 44-57-0 | -8.30u | 68, -0.08c, -11.36u | negative |
| J2 B, NBA | 75 | 70 | 0.3c | 31-39-0 | -4.82u | 43, 0.08c, -3.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 62 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.3c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 259 | 241 | -0.59c | 119-119-3 | -7.77u | 139, -0.62c, -10.71u | negative |
| D1 B, unders (descriptive) | 36 | 33 | 0.63c | 18-15-0 | +4.54u | 30, 0.63c, +3.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 16 | 15 | 0.34c | 6-9-0 | -1.21u | 14, 0.33c, -2.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 93 | 91 | -0.2c | 50-39-2 | +3.16u | 47, -0.24c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2465 | 108 | 4.4% | -0.56c | 1.58c | 51-45-0 | +8.23u |  |
| MK novig fair-2c | 2459 | 45 | 1.8% | -0.08c | 2.52c | 23-14-0 | +11.42u |  |
| MK prophetx fair-1c | 5627 | 272 | 4.8% | -1.04c | 1.1c | 123-128-5 | +0.49u |  |
| MK prophetx fair-2c | 5589 | 100 | 1.8% | -0.56c | 2.05c | 43-46-0 | +0.62u |  |
| MK all fair-1c | 8092 | 380 | 4.7% | -0.9c | 1.25c | 174-173-5 | +8.73u | criteria not met (352/50 graded, CLV not positive) |
| MK all fair-2c | 8048 | 145 | 1.8% | -0.41c | 2.19c | 66-60-0 | +12.04u | criteria not met (126/50 graded, CLV not positive) |

A and B on the same side/line: 131.

## Odds API credits (100K/month plan)

Study: 644/day, projected 19313/30 days. All monitors on the key: 2411/day, projected 72341/30 days. Remaining 72115; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T01:42:29Z: 23 games (19 in 24h), quotes {'prophetx': 754, 'novig': 714, 'kalshi': 1384, 'polymarket_us': 1400}, 878 unmatched (16 book-games; fuzzy-matched 1), 1770 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 38 filled 0, credits used 12 left 72115, 302s
- 2026-11-12T01:32:07Z: 23 games (19 in 24h), quotes {'prophetx': 896, 'novig': 720, 'kalshi': 1368, 'polymarket_us': 1400}, 918 unmatched (16 book-games; fuzzy-matched 1), 1747 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 8 filled 1, credits used 8 left 72173, 301s
- 2026-11-12T01:22:05Z: 23 games (19 in 24h), quotes {'prophetx': 926, 'novig': 712, 'kalshi': 1396, 'polymarket_us': 1400}, 949 unmatched (16 book-games; fuzzy-matched 1), 1759 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 9 filled 2, credits used 4 left 72227, 205s
- 2026-11-12T01:12:27Z: 22 games (18 in 24h), quotes {'prophetx': 654, 'novig': 638, 'kalshi': 1428, 'polymarket_us': 1260}, 958 unmatched (15 book-games; fuzzy-matched 2), 1498 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 3, new A 13 B 0, maker posted 5 filled 2, credits used 12 left 72247, 302s
- 2026-11-12T01:02:27Z: 26 games (21 in 24h), quotes {'prophetx': 686, 'novig': 722, 'kalshi': 1400, 'polymarket_us': 1260}, 648 unmatched (10 book-games; fuzzy-matched 1), 1916 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 20 B 1, maker posted 12 filled 4, credits used 4 left 72303, 184s
- 2026-11-12T00:52:50Z: 26 games (18 in 24h), quotes {'prophetx': 1066, 'novig': 714, 'kalshi': 1368, 'polymarket_us': 1460}, 674 unmatched (10 book-games; fuzzy-matched 1), 2139 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 16 filled 0, credits used 8 left 72336, 330s
- 2026-11-12T00:42:28Z: 28 games (21 in 24h), quotes {'prophetx': 1066, 'novig': 718, 'kalshi': 1378, 'polymarket_us': 1460}, 526 unmatched (7 book-games; fuzzy-matched 1), 2299 side/lines, polls [NFL:slow,NCAAF:fast; NBA:fast,NHL:fast], moves 3, new A 6 B 1, maker posted 1 filled 8, credits used 8 left 72367, 233s
- 2026-11-12T00:32:32Z: 28 games (21 in 24h), quotes {'prophetx': 1074, 'novig': 716, 'kalshi': 1390, 'polymarket_us': 1460}, 538 unmatched (7 book-games; fuzzy-matched 2), 2293 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 6 B 1, maker posted 59 filled 0, credits used 10 left 72411, 301s
- 2026-11-12T00:21:35Z: 29 games (22 in 24h), quotes {'prophetx': 1240, 'novig': 716, 'kalshi': 1404, 'polymarket_us': 1678}, 440 unmatched (6 book-games; fuzzy-matched 3), 2669 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 4 B 0, maker posted 10 filled 2, credits used 14 left 72472, 351s
- 2026-11-12T00:11:37Z: 32 games (25 in 24h), quotes {'prophetx': 1444, 'novig': 724, 'kalshi': 1408, 'polymarket_us': 1572}, 126 unmatched (2 book-games; fuzzy-matched 3), 2981 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 56 filled 2, credits used 6 left 72520, 184s
