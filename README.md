# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T03:53:18Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1543 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1337 | 668-669-0 | -95.45u | -7.1% |  |  | criteria not met (1337/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 368 | 327 | -6.26c | 19.6% | 63 | -4.52c | 325 | 158-167-0 | -35.37u | -10.9% |  |  | criteria not met (325/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 29 | 27 | -0.78c | 40.7% | 25 | -0.07c | 24 | 9-15-0 | -4.91u | -20.5% |  |  | criteria not met (24/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 18 | 18 | -0.68c | 33.3% | 17 | 0.05c | 17 | 8-9-0 | -0.08u | -0.4% |  |  |  |
| B ref age 5m+ | 9 | 7 | -2.01c | 42.9% | 6 | -1.23c | 6 | 1-5-0 | -3.83u | -63.9% |  |  |  |
| M move-watch: gettable (sightings) | 51 | 50 | -0.72c | 32.0% | 50 | -0.54c | 48 | 26-22-0 | +3.02u | 6.3% | 0.27c | 139s | criteria not met (48/50 graded, CLV not positive) |
| M gettable, line moves | 23 | 22 | -0.67c | 31.8% | 22 | -0.61c | 21 | 11-10-0 | +0.20u | 0.9% | 0.16c | 139s |  |
| M gettable, price moves | 28 | 28 | -0.76c | 32.1% | 28 | -0.49c | 27 | 15-12-0 | +2.82u | 10.4% | 0.36c | 105s |  |
| M control: not gettable | 161 | 129 | -0.71c | 32.6% | 124 | -1.23c | 123 | 64-57-2 | -0.69u | -0.6% | 1.76c | 29s |  |
| M all moves | 212 | 179 | -0.71c | 32.4% | 174 | -1.03c | 171 | 90-79-2 | +2.33u | 1.4% | 1.39c | 70s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 136 | 120 | -1.86c | 18.3% | 12 | -1.49c | 120 | 58-62-0 | +80.41u | 67.0% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 74 | 6 | 8.1% | -0.87c | 1.75c | 3-2-0 | +1.12u |  |
| MK novig fair-2c | 73 | 2 | 2.7% | -1.19c | 2.63c | 0-1-0 | -1.00u |  |
| MK prophetx fair-1c | 149 | 7 | 4.7% | -1.77c | 1.15c | 4-2-0 | +2.23u |  |
| MK prophetx fair-2c | 147 | 2 | 1.4% | -1.54c | 2.08c | 0-1-0 | -1.00u |  |
| MK all fair-1c | 223 | 13 | 5.8% | -1.35c | 1.34c | 7-4-0 | +3.35u | criteria not met (11/50 graded, CLV not positive) |
| MK all fair-2c | 220 | 4 | 1.8% | -1.37c | 2.26c | 0-2-0 | -2.00u | criteria not met (2/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 24.

## Odds API credits (100K/month plan)

Study: 561/day, projected 16841/30 days. All monitors on the key: 2152/day, projected 64561/30 days. Remaining 66163; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T03:50:15Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 668, 'kalshi': 1024, 'polymarket_us': 1898}, 268 unmatched, 2397 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 66163, 183s
- 2026-10-30T03:40:15Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 668, 'kalshi': 1034, 'polymarket_us': 1898}, 280 unmatched, 2397 side/lines, polls [NCAAF:slow,NBA:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 66170, 183s
- 2026-10-30T03:33:38Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 668, 'kalshi': 1036, 'polymarket_us': 1898}, 282 unmatched, 2395 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 66181, 181s
- 2026-10-30T03:30:20Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1040, 'polymarket_us': 1898}, 286 unmatched, 2394 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 66181, 183s
- 2026-10-30T03:20:57Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1072, 'polymarket_us': 1794}, 316 unmatched, 2339 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 66195, 182s
- 2026-10-30T03:17:34Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 672, 'kalshi': 1112, 'polymarket_us': 1862}, 354 unmatched, 2375 side/lines, polls [NCAAF:slow,NBA:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 66195, 184s
- 2026-10-30T03:10:14Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 668, 'kalshi': 1120, 'polymarket_us': 1840}, 362 unmatched, 2363 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 66214, 185s
- 2026-10-30T03:00:22Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 666, 'kalshi': 1136, 'polymarket_us': 1898}, 378 unmatched, 2398 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 66221, 183s
- 2026-10-30T02:56:10Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 664, 'kalshi': 1142, 'polymarket_us': 1704}, 386 unmatched, 2290 side/lines, polls [NCAAF:slow,NBA:slow], moves 4, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 66228, 183s
- 2026-10-30T02:50:15Z: 13 games (13 in 24h), quotes {'prophetx': 1382, 'novig': 670, 'kalshi': 1156, 'polymarket_us': 1898}, 400 unmatched, 2399 side/lines, polls [none_due], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 0 left 66239, 183s
