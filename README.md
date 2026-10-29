# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T18:15:15Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1302 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 317 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 23 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 16 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 6 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 43 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 166s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 19 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 166s |  |
| M gettable, price moves | 24 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 170s |  |
| M control: not gettable | 138 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 148s |  |
| M all moves | 181 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 116 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 6 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 6 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 16 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 16 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK all fair-1c | 22 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 22 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 19.

## Odds API credits (100K/month plan)

Study: 453/day, projected 13580/30 days. All monitors on the key: 2017/day, projected 60502/30 days. Remaining 67291; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T18:10:15Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 633, 'kalshi': 1316, 'polymarket_us': 1052}, 212 unmatched, 2158 side/lines, polls [NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 24 filled 0, credits used 10 left 67291, 301s
- 2026-10-29T18:00:32Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 633, 'kalshi': 1300, 'polymarket_us': 1052}, 212 unmatched, 2142 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 2 left 67312, 283s
- 2026-10-29T17:55:32Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 633, 'kalshi': 1278, 'polymarket_us': 1052}, 212 unmatched, 2120 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 67323, 283s
- 2026-10-29T17:50:14Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 627, 'kalshi': 1306, 'polymarket_us': 1052}, 206 unmatched, 2148 side/lines, polls [NCAAF:fast; NCAAF:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 67329, 301s
- 2026-10-29T17:40:15Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 625, 'kalshi': 1316, 'polymarket_us': 1052}, 207 unmatched, 2161 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 2 left 67357, 158s
- 2026-10-29T17:30:17Z: 19 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1314, 'polymarket_us': 1052}, 204 unmatched, 2161 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow; NCAAF:fast], moves 1, new A 2 B 0, maker posted 20 filled 0, credits used 8 left 67370, 301s
- 2026-10-29T17:20:17Z: 19 games (6 in 24h), quotes {'prophetx': 668, 'novig': 627, 'kalshi': 1314, 'polymarket_us': 1052}, 205 unmatched, 2161 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 67400, 159s
- 2026-10-29T17:14:17Z: 19 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1312, 'polymarket_us': 1052}, 202 unmatched, 2157 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 67411, 158s
- 2026-10-29T17:10:15Z: 19 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1316, 'polymarket_us': 1052}, 203 unmatched, 2159 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 2, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 67411, 157s
- 2026-10-29T17:06:29Z: 19 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1316, 'polymarket_us': 1052}, 202 unmatched, 2159 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 67432, 158s
