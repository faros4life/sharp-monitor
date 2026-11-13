# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-13T02:47:58Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 10057 | 9769 | -1.62c | 24.4% | 4229 | -1.09c | 9410 | 4896-4514-0 | -289.07u | -3.1% |  |  | criteria not met (9410/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2338 | 2197 | -3.1c | 19.5% | 495 | -2.84c | 2100 | 1085-1015-0 | -162.54u | -7.7% |  |  | criteria not met (2100/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 175 | 175 | -0.8c | 31.4% | 164 | 0.15c | 161 | 67-94-0 | -18.81u | -11.7% |  |  | criteria not met (161/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 16 | 16 | -0.11c | 31.2% | 16 | 1.04c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 96 | 96 | -0.86c | 32.3% | 91 | 0.08c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 63 | 63 | -0.9c | 30.2% | 57 | 0.02c | 57 | 22-35-0 | -10.57u | -18.5% |  |  |  |
| M move-watch: gettable (sightings) | 468 | 464 | -0.6c | 35.3% | 462 | -0.54c | 439 | 223-211-5 | -7.21u | -1.6% | 0.21c | 28s | criteria not met (439/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 241 | 239 | -0.74c | 35.6% | 238 | -0.78c | 226 | 108-114-4 | -15.80u | -7.0% | -0.14c | 28s |  |
| M gettable, price moves | 227 | 225 | -0.44c | 35.1% | 224 | -0.28c | 213 | 115-97-1 | +8.59u | 4.0% | 0.59c | 26s |  |
| M control: not gettable | 1856 | 1490 | -0.82c | 35.6% | 1461 | -1.24c | 1484 | 740-720-24 | -64.98u | -4.4% | 1.88c | 184s |  |
| M all moves | 2324 | 1954 | -0.76c | 35.6% | 1923 | -1.07c | 1923 | 963-931-29 | -72.19u | -3.8% | 1.54c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1118 | 1108 | 2.6c | 27.8% | 234 | 2.42c | 1084 | 488-596-0 | +293.23u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 118 | 107 | 0.12c | 45-62-0 | -12.26u | 73, -0.14c, -14.32u | negative |
| J2 B, NBA | 84 | 75 | 0.26c | 31-44-0 | -9.82u | 47, 0.01c, -7.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 68 | 62 | 0.04c | 27-35-0 | -5.32u | 48, -0.4c, -4.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 277 | 258 | -0.59c | 123-132-3 | -17.00u | 148, -0.68c, -13.93u | negative |
| D1 B, unders (descriptive) | 43 | 36 | 0.5c | 18-18-0 | +1.54u | 33, 0.45c, +0.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.3c | 9-5-1 | +0.53u | 11, -0.47c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 19 | 16 | 0.53c | 6-10-0 | -2.21u | 15, 0.53c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 105 | 95 | -0.29c | 53-40-2 | +4.26u | 50, -0.4c, +0.46u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2742 | 117 | 4.3% | -0.57c | 1.58c | 54-54-0 | +2.40u |  |
| MK novig fair-2c | 2731 | 48 | 1.8% | -0.08c | 2.52c | 25-20-0 | +7.63u |  |
| MK prophetx fair-1c | 5922 | 281 | 4.7% | -1.08c | 1.1c | 129-138-5 | -3.19u |  |
| MK prophetx fair-2c | 5882 | 103 | 1.8% | -0.57c | 2.04c | 47-53-0 | -2.00u |  |
| MK all fair-1c | 8664 | 398 | 4.6% | -0.93c | 1.25c | 183-192-5 | -0.79u | criteria not met (380/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8613 | 151 | 1.8% | -0.41c | 2.19c | 72-73-0 | +5.63u | criteria not met (145/50 graded, CLV not positive) |

A and B on the same side/line: 145.

## Odds API credits (100K/month plan)

Study: 654/day, projected 19632/30 days. All monitors on the key: 2447/day, projected 73399/30 days. Remaining 69028; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-13T02:42:56Z: 15 games (11 in 24h), quotes {'prophetx': 1070, 'novig': 722, 'kalshi': 1232, 'polymarket_us': 1202}, 296 unmatched (11 book-games; fuzzy-matched 0), 2193 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 3 B 0, maker posted 4 filled 0, credits used 4 left 69028, 302s
- 2026-11-13T02:34:36Z: 15 games (10 in 24h), quotes {'prophetx': 1070, 'novig': 724, 'kalshi': 1270, 'polymarket_us': 1202}, 336 unmatched (16 book-games; fuzzy-matched 0), 2184 side/lines, polls [none_due; NHL:fast], moves 0, new A 38 B 0, maker posted 0 filled 0, credits used 2 left 69050, 182s
- 2026-11-13T02:28:43Z: 15 games (10 in 24h), quotes {'prophetx': 942, 'novig': 724, 'kalshi': 1322, 'polymarket_us': 1076}, 388 unmatched (16 book-games; fuzzy-matched 0), 2080 side/lines, polls [NCAAF:slow,NBA:slow; NHL:fast], moves 0, new A 2 B 0, maker posted 4 filled 0, credits used 6 left 69052, 182s
- 2026-11-13T02:20:48Z: 15 games (10 in 24h), quotes {'prophetx': 942, 'novig': 726, 'kalshi': 1362, 'polymarket_us': 1076}, 426 unmatched (17 book-games; fuzzy-matched 0), 2069 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 4 left 69068, 301s
- 2026-11-13T02:12:20Z: 15 games (10 in 24h), quotes {'prophetx': 938, 'novig': 720, 'kalshi': 1378, 'polymarket_us': 1076}, 444 unmatched (17 book-games; fuzzy-matched 0), 2066 side/lines, polls [none_due; NHL:fast], moves 0, new A 25 B 0, maker posted 0 filled 0, credits used 2 left 69090, 181s
- 2026-11-13T02:02:53Z: 18 games (12 in 24h), quotes {'prophetx': 938, 'novig': 726, 'kalshi': 1424, 'polymarket_us': 1076}, 366 unmatched (14 book-games; fuzzy-matched 2), 2219 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 31 B 0, maker posted 0 filled 1, credits used 10 left 69110, 301s
- 2026-11-13T01:52:47Z: 18 games (11 in 24h), quotes {'prophetx': 1038, 'novig': 701, 'kalshi': 1432, 'polymarket_us': 1206}, 378 unmatched (14 book-games; fuzzy-matched 2), 2362 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 13 B 0, maker posted 12 filled 1, credits used 12 left 69129, 301s
- 2026-11-13T01:42:42Z: 18 games (11 in 24h), quotes {'prophetx': 934, 'novig': 701, 'kalshi': 1446, 'polymarket_us': 1206}, 390 unmatched (14 book-games; fuzzy-matched 4), 2325 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 15 B 0, maker posted 20 filled 2, credits used 12 left 69150, 329s
- 2026-11-13T01:32:22Z: 18 games (10 in 24h), quotes {'prophetx': 934, 'novig': 699, 'kalshi': 1480, 'polymarket_us': 1206}, 430 unmatched (14 book-games; fuzzy-matched 2), 2294 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 12 B 0, maker posted 0 filled 0, credits used 6 left 69171, 240s
- 2026-11-13T01:26:02Z: 18 games (10 in 24h), quotes {'prophetx': 918, 'novig': 701, 'kalshi': 1492, 'polymarket_us': 1080}, 446 unmatched (14 book-games; fuzzy-matched 2), 2218 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 21 B 0, maker posted 0 filled 0, credits used 6 left 69190, 184s
