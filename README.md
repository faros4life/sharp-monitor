# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T03:24:00Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1538 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1164 | 582-582-0 | -82.84u | -7.1% |  |  | criteria not met (1164/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 368 | 327 | -6.26c | 19.6% | 63 | -4.52c | 294 | 144-150-0 | -30.48u | -10.4% |  |  | criteria not met (294/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 29 | 27 | -0.78c | 40.7% | 25 | -0.07c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 18 | 18 | -0.68c | 33.3% | 17 | 0.05c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 9 | 7 | -2.01c | 42.9% | 6 | -1.23c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 51 | 50 | -0.72c | 32.0% | 50 | -0.54c | 40 | 23-17-0 | +5.14u | 12.9% | 0.27c | 139s | criteria not met (40/50 graded, CLV not positive) |
| M gettable, line moves | 23 | 22 | -0.67c | 31.8% | 22 | -0.61c | 16 | 10-6-0 | +3.29u | 20.6% | 0.16c | 139s |  |
| M gettable, price moves | 28 | 28 | -0.76c | 32.1% | 28 | -0.49c | 24 | 13-11-0 | +1.85u | 7.7% | 0.36c | 105s |  |
| M control: not gettable | 161 | 129 | -0.71c | 32.6% | 124 | -1.23c | 103 | 54-47-2 | +0.54u | 0.5% | 1.76c | 29s |  |
| M all moves | 212 | 179 | -0.71c | 32.4% | 174 | -1.03c | 143 | 77-64-2 | +5.68u | 4.0% | 1.39c | 70s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 136 | 120 | -1.86c | 18.3% | 12 | -1.49c | 96 | 47-49-0 | +47.13u | 49.1% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 74 | 6 | 8.1% | -0.87c | 1.75c | 1-1-0 | +0.04u |  |
| MK novig fair-2c | 73 | 2 | 2.7% | -1.19c | 2.63c | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 149 | 7 | 4.7% | -1.77c | 1.15c | 2-1-0 | +1.10u |  |
| MK prophetx fair-2c | 147 | 2 | 1.4% | -1.54c | 2.08c | 0-0-0 | +0.00u |  |
| MK all fair-1c | 223 | 13 | 5.8% | -1.35c | 1.34c | 3-2-0 | +1.14u | criteria not met (5/50 graded, CLV not positive) |
| MK all fair-2c | 220 | 4 | 1.8% | -1.37c | 2.26c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 24.

## Odds API credits (100K/month plan)

Study: 565/day, projected 16937/30 days. All monitors on the key: 2157/day, projected 64714/30 days. Remaining 66195; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T03:20:57Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1072, 'polymarket_us': 1794}, 316 unmatched, 2339 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 66195, 182s
- 2026-10-30T03:17:34Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 672, 'kalshi': 1112, 'polymarket_us': 1862}, 354 unmatched, 2375 side/lines, polls [NCAAF:slow,NBA:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 66195, 184s
- 2026-10-30T03:10:14Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 668, 'kalshi': 1120, 'polymarket_us': 1840}, 362 unmatched, 2363 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 66214, 185s
- 2026-10-30T03:00:22Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 666, 'kalshi': 1136, 'polymarket_us': 1898}, 378 unmatched, 2398 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 66221, 183s
- 2026-10-30T02:56:10Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 664, 'kalshi': 1142, 'polymarket_us': 1704}, 386 unmatched, 2290 side/lines, polls [NCAAF:slow,NBA:slow], moves 4, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 66228, 183s
- 2026-10-30T02:50:15Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1156, 'polymarket_us': 1898}, 400 unmatched, 2399 side/lines, polls [none_due], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 0 left 66239, 183s
- 2026-10-30T02:40:16Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1164, 'polymarket_us': 1894}, 406 unmatched, 2388 side/lines, polls [none_due], moves 0, new A 3 B 1, maker posted 0 filled 0, credits used 0 left 66246, 183s
- 2026-10-30T02:33:45Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 662, 'kalshi': 1172, 'polymarket_us': 1894}, 410 unmatched, 2338 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 66253, 181s
- 2026-10-30T02:30:25Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1174, 'polymarket_us': 1894}, 414 unmatched, 2315 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 7 B 0, maker posted 0 filled 0, credits used 4 left 66253, 184s
- 2026-10-30T02:20:15Z: 13 games (12 in 24h), quotes {'prophetx': 1246, 'novig': 664, 'kalshi': 1224, 'polymarket_us': 1718}, 464 unmatched, 2163 side/lines, polls [none_due], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 0 left 66275, 182s
