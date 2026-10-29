# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T23:03:42Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1355 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 324 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 24 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 16 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 7 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 49 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 151s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 21 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 151s |  |
| M gettable, price moves | 28 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 105s |  |
| M control: not gettable | 148 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 28s |  |
| M all moves | 197 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 91s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 121 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 50 | 2 | 5.4% |  |  | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 50 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 111 | 2 | 2.4% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 110 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK all fair-1c | 161 | 4 | 3.4% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 160 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 20.

## Odds API credits (100K/month plan)

Study: 553/day, projected 16578/30 days. All monitors on the key: 2149/day, projected 64482/30 days. Remaining 66603; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T22:59:35Z: 19 games (6 in 24h), quotes {'prophetx': 700, 'novig': 652, 'kalshi': 1422, 'polymarket_us': 1052}, 220 unmatched, 2255 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, maker posted 0 filled 1, credits used 6 left 66603, 247s
- 2026-10-29T22:50:15Z: 19 games (6 in 24h), quotes {'prophetx': 700, 'novig': 659, 'kalshi': 1424, 'polymarket_us': 1052}, 239 unmatched, 2253 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 66631, 285s
- 2026-10-29T22:45:21Z: 19 games (6 in 24h), quotes {'prophetx': 700, 'novig': 659, 'kalshi': 1424, 'polymarket_us': 1052}, 239 unmatched, 2253 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 4 filled 1, credits used 6 left 66637, 279s
- 2026-10-29T22:39:59Z: 19 games (6 in 24h), quotes {'prophetx': 700, 'novig': 661, 'kalshi': 1422, 'polymarket_us': 1052}, 246 unmatched, 2253 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 2, new A 0 B 0, maker posted 16 filled 0, credits used 12 left 66654, 301s
- 2026-10-29T22:30:20Z: 19 games (6 in 24h), quotes {'prophetx': 636, 'novig': 636, 'kalshi': 1420, 'polymarket_us': 1052}, 210 unmatched, 2249 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 1 B 0, maker posted 17 filled 0, credits used 6 left 66677, 194s
- 2026-10-29T22:21:33Z: 19 games (6 in 24h), quotes {'prophetx': 636, 'novig': 642, 'kalshi': 1424, 'polymarket_us': 1052}, 211 unmatched, 2249 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 2, new A 0 B 0, maker posted 9 filled 0, credits used 6 left 66692, 307s
- 2026-10-29T22:18:30Z: 19 games (6 in 24h), quotes {'prophetx': 640, 'novig': 647, 'kalshi': 1426, 'polymarket_us': 1052}, 212 unmatched, 2256 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 10 B 0, maker posted 7 filled 1, credits used 6 left 66698, 168s
- 2026-10-29T22:10:58Z: 19 games (6 in 24h), quotes {'prophetx': 640, 'novig': 645, 'kalshi': 1424, 'polymarket_us': 1052}, 212 unmatched, 2255 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 4 filled 0, credits used 6 left 66715, 289s
- 2026-10-29T22:05:36Z: 19 games (6 in 24h), quotes {'prophetx': 640, 'novig': 647, 'kalshi': 1424, 'polymarket_us': 1052}, 212 unmatched, 2257 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 66721, 307s
- 2026-10-29T22:00:18Z: 19 games (6 in 24h), quotes {'prophetx': 626, 'novig': 649, 'kalshi': 1424, 'polymarket_us': 1052}, 213 unmatched, 2258 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 32 filled 1, credits used 12 left 66736, 301s
