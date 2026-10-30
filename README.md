# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T00:14:51Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1426 | 1288 | -3.08c | 25.0% | 452 | -1.54c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 348 | 322 | -6.35c | 19.3% | 61 | -4.69c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 26 | 23 | -1.17c | 30.4% | 21 | -0.42c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 18 | 17 | -0.79c | 29.4% | 16 | -0.03c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 7 | 5 | -3.47c | 20.0% | 4 | -2.84c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 51 | 45 | -0.73c | 33.3% | 45 | -0.57c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 139s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 23 | 19 | -0.65c | 36.8% | 19 | -0.62c | 14 | 9-5-0 | +3.31u | 23.7% | 0.25c | 139s |  |
| M gettable, price moves | 28 | 26 | -0.78c | 30.8% | 26 | -0.54c | 21 | 12-9-0 | +2.81u | 13.4% | 0.38c | 105s |  |
| M control: not gettable | 154 | 117 | -0.65c | 35.9% | 112 | -1.19c | 93 | 50-41-2 | +3.00u | 3.2% | 1.84c | 28s |  |
| M all moves | 205 | 162 | -0.67c | 35.2% | 157 | -1.01c | 128 | 71-55-2 | +9.13u | 7.1% | 1.47c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 127 | 114 | -3.68c | 15.8% | 12 | -1.49c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 70 | 5 | 7.8% | -1.11c | 1.86c | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 69 | 1 | 1.6% | -3.69c | 2.68c | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 139 | 6 | 4.6% | -2.0c | 1.19c | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 137 | 1 | 0.8% | -3.69c | 2.1c | 0-0-0 | +0.00u |  |
| MK all fair-1c | 209 | 11 | 5.6% | -1.59c | 1.39c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 206 | 2 | 1.0% | -3.69c | 2.28c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 22.

## Odds API credits (100K/month plan)

Study: 570/day, projected 17113/30 days. All monitors on the key: 2172/day, projected 65149/30 days. Remaining 66449; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T00:10:17Z: 17 games (14 in 24h), quotes {'prophetx': 1078, 'novig': 668, 'kalshi': 1442, 'polymarket_us': 1804}, 382 unmatched, 2473 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 4 left 66449, 274s
- 2026-10-30T00:06:47Z: 17 games (11 in 24h), quotes {'prophetx': 1078, 'novig': 670, 'kalshi': 1438, 'polymarket_us': 1804}, 386 unmatched, 2474 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 1, new A 13 B 0, maker posted 0 filled 0, credits used 4 left 66462, 190s
- 2026-10-30T00:00:20Z: 17 games (11 in 24h), quotes {'prophetx': 1078, 'novig': 672, 'kalshi': 1438, 'polymarket_us': 1804}, 384 unmatched, 2484 side/lines, polls [NCAAF:slow; NFL:fast,NBA:fast], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 66468, 184s
- 2026-10-29T23:53:07Z: 17 games (11 in 24h), quotes {'prophetx': 1108, 'novig': 666, 'kalshi': 1444, 'polymarket_us': 1684}, 392 unmatched, 2540 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 66483, 284s
- 2026-10-29T23:49:47Z: 17 games (11 in 24h), quotes {'prophetx': 928, 'novig': 670, 'kalshi': 1442, 'polymarket_us': 1684}, 388 unmatched, 2543 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 16 filled 0, credits used 4 left 66496, 184s
- 2026-10-29T23:40:37Z: 17 games (11 in 24h), quotes {'prophetx': 928, 'novig': 656, 'kalshi': 1450, 'polymarket_us': 1684}, 398 unmatched, 2544 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 12 filled 0, credits used 4 left 66500, 308s
- 2026-10-29T23:35:37Z: 19 games (9 in 24h), quotes {'prophetx': 928, 'novig': 666, 'kalshi': 1440, 'polymarket_us': 1684}, 252 unmatched, 2683 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 0, new A 5 B 0, maker posted 8 filled 0, credits used 4 left 66513, 285s
- 2026-10-29T23:30:20Z: 18 games (8 in 24h), quotes {'prophetx': 928, 'novig': 666, 'kalshi': 1454, 'polymarket_us': 1684}, 324 unmatched, 2625 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 13 B 0, maker posted 8 filled 2, credits used 12 left 66526, 302s
- 2026-10-29T23:20:15Z: 19 games (8 in 24h), quotes {'prophetx': 842, 'novig': 704, 'kalshi': 1450, 'polymarket_us': 1352}, 252 unmatched, 2508 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 7 filled 0, credits used 6 left 66557, 243s
- 2026-10-29T23:16:17Z: 19 games (8 in 24h), quotes {'prophetx': 802, 'novig': 700, 'kalshi': 1432, 'polymarket_us': 1352}, 254 unmatched, 2479 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 19 filled 1, credits used 6 left 66565, 181s
