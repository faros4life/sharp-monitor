# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T03:34:51Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9559 | 9405 | -1.62c | 24.4% | 4076 | -1.07c | 9004 | 4646-4358-0 | -344.86u | -3.8% |  |  | criteria not met (9004/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2159 | 2100 | -3.08c | 19.5% | 470 | -2.73c | 2006 | 1021-985-0 | -180.03u | -9.0% |  |  | criteria not met (2006/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 161 | 161 | -0.76c | 31.1% | 151 | 0.14c | 156 | 66-90-0 | -15.85u | -10.2% |  |  | criteria not met (156/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 15 | -0.15c | 26.7% | 15 | 1.01c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 89 | 89 | -0.82c | 31.5% | 85 | 0.05c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 57 | 57 | -0.83c | 31.6% | 51 | 0.04c | 53 | 21-32-0 | -8.61u | -16.2% |  |  |  |
| M move-watch: gettable (sightings) | 440 | 434 | -0.62c | 34.8% | 432 | -0.54c | 422 | 218-199-5 | +0.77u | 0.2% | 0.2c | 27s | criteria not met (422/50 graded, CLV not positive) |
| M gettable, line moves | 227 | 224 | -0.79c | 34.8% | 223 | -0.82c | 216 | 108-104-4 | -5.80u | -2.7% | -0.19c | 28s |  |
| M gettable, price moves | 213 | 210 | -0.45c | 34.8% | 209 | -0.24c | 206 | 110-95-1 | +6.56u | 3.2% | 0.61c | 25s |  |
| M control: not gettable | 1800 | 1445 | -0.83c | 35.5% | 1413 | -1.25c | 1419 | 711-685-23 | -57.80u | -4.1% | 1.87c | 184s |  |
| M all moves | 2240 | 1879 | -0.78c | 35.3% | 1845 | -1.08c | 1841 | 929-884-28 | -57.04u | -3.1% | 1.54c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1097 | 1083 | 2.45c | 27.1% | 232 | 2.44c | 1081 | 487-594-0 | +294.77u | 27.3% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 107 | 102 | 0.13c | 44-58-0 | -9.30u | 69, -0.08c, -12.36u | negative |
| J2 B, NBA | 75 | 71 | 0.3c | 31-40-0 | -5.82u | 44, 0.08c, -4.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 62 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.3c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 259 | 245 | -0.6c | 121-121-3 | -7.92u | 142, -0.65c, -9.86u | negative |
| D1 B, unders (descriptive) | 36 | 35 | 0.63c | 18-17-0 | +2.54u | 32, 0.63c, +1.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 16 | 16 | 0.34c | 6-10-0 | -2.21u | 15, 0.33c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 95 | 91 | -0.27c | 50-39-2 | +3.16u | 47, -0.36c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2472 | 108 | 4.4% | -0.57c | 1.58c | 52-49-0 | +5.27u |  |
| MK novig fair-2c | 2466 | 45 | 1.8% | -0.08c | 2.52c | 23-15-0 | +10.42u |  |
| MK prophetx fair-1c | 5633 | 272 | 4.8% | -1.05c | 1.1c | 124-133-5 | -3.48u |  |
| MK prophetx fair-2c | 5595 | 100 | 1.8% | -0.56c | 2.05c | 43-50-0 | -3.38u |  |
| MK all fair-1c | 8105 | 380 | 4.7% | -0.91c | 1.25c | 176-182-5 | +1.80u | criteria not met (363/50 graded, CLV not positive) |
| MK all fair-2c | 8061 | 145 | 1.8% | -0.41c | 2.19c | 66-65-0 | +7.04u | criteria not met (131/50 graded, CLV not positive) |

A and B on the same side/line: 131.

## Odds API credits (100K/month plan)

Study: 645/day, projected 19354/30 days. All monitors on the key: 2425/day, projected 72754/30 days. Remaining 71721; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T03:31:45Z: 17 games (17 in 24h), quotes {'prophetx': 858, 'novig': 685, 'kalshi': 898, 'polymarket_us': 1222}, 462 unmatched (13 book-games; fuzzy-matched 2), 1605 side/lines, polls [NBA:slow,NHL:slow], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 71721, 182s
- 2026-11-12T03:22:07Z: 17 games (17 in 24h), quotes {'prophetx': 856, 'novig': 693, 'kalshi': 966, 'polymarket_us': 1222}, 532 unmatched (15 book-games; fuzzy-matched 2), 1605 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 21 B 0, maker posted 0 filled 0, credits used 4 left 71748, 182s
- 2026-11-12T03:11:38Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1032, 'polymarket_us': 1222}, 528 unmatched (16 book-games; fuzzy-matched 2), 1677 side/lines, polls [NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 2 left 71767, 183s
- 2026-11-12T03:01:42Z: 20 games (20 in 24h), quotes {'prophetx': 816, 'novig': 710, 'kalshi': 1082, 'polymarket_us': 1222}, 544 unmatched (14 book-games; fuzzy-matched 2), 1714 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 0 filled 0, credits used 8 left 71788, 182s
- 2026-11-12T02:52:28Z: 20 games (19 in 24h), quotes {'prophetx': 896, 'novig': 716, 'kalshi': 1124, 'polymarket_us': 1376}, 580 unmatched (14 book-games; fuzzy-matched 2), 1839 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 6 filled 0, credits used 8 left 71827, 323s
- 2026-11-12T02:42:28Z: 22 games (21 in 24h), quotes {'prophetx': 812, 'novig': 687, 'kalshi': 1168, 'polymarket_us': 1376}, 536 unmatched (13 book-games; fuzzy-matched 2), 1866 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 13 B 0, maker posted 0 filled 0, credits used 4 left 71862, 183s
- 2026-11-12T02:32:31Z: 22 games (21 in 24h), quotes {'prophetx': 918, 'novig': 714, 'kalshi': 1246, 'polymarket_us': 1376}, 620 unmatched (15 book-games; fuzzy-matched 2), 1923 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 4 filled 0, credits used 12 left 71903, 301s
- 2026-11-12T02:22:04Z: 22 games (21 in 24h), quotes {'prophetx': 918, 'novig': 716, 'kalshi': 1292, 'polymarket_us': 1534}, 666 unmatched (15 book-games; fuzzy-matched 2), 1978 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 17 B 0, maker posted 0 filled 0, credits used 8 left 71958, 309s
- 2026-11-12T02:11:40Z: 22 games (21 in 24h), quotes {'prophetx': 980, 'novig': 722, 'kalshi': 1262, 'polymarket_us': 1478}, 702 unmatched (16 book-games; fuzzy-matched 4), 1950 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 2, new A 30 B 0, maker posted 12 filled 0, credits used 8 left 72006, 222s
- 2026-11-12T02:02:14Z: 23 games (21 in 24h), quotes {'prophetx': 952, 'novig': 724, 'kalshi': 1296, 'polymarket_us': 1532}, 790 unmatched (16 book-games; fuzzy-matched 4), 1958 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 39 B 0, maker posted 4 filled 0, credits used 8 left 72041, 302s
