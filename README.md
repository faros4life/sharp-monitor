# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T01:25:37Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1441 | 1337 | -2.97c | 25.7% | 478 | -1.45c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 350 | 325 | -6.3c | 19.4% | 61 | -4.69c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 27 | 24 | -1.11c | 33.3% | 22 | -0.35c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 18 | 17 | -0.79c | 29.4% | 16 | -0.03c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 7 | 6 | -2.85c | 33.3% | 5 | -2.05c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 51 | 48 | -0.7c | 33.3% | 48 | -0.54c | 35 | 21-14-0 | +6.12u | 17.5% | 0.3c | 139s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 23 | 21 | -0.64c | 33.3% | 21 | -0.61c | 14 | 9-5-0 | +3.31u | 23.7% | 0.19c | 139s |  |
| M gettable, price moves | 28 | 27 | -0.74c | 33.3% | 27 | -0.48c | 21 | 12-9-0 | +2.81u | 13.4% | 0.38c | 105s |  |
| M control: not gettable | 155 | 120 | -0.65c | 35.0% | 115 | -1.18c | 93 | 50-41-2 | +3.00u | 3.2% | 1.82c | 28s |  |
| M all moves | 206 | 168 | -0.66c | 34.5% | 163 | -0.99c | 128 | 71-55-2 | +9.13u | 7.1% | 1.44c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 130 | 119 | -1.85c | 18.5% | 12 | -1.49c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 72 | 6 | 8.5% | -1.11c | 1.77c | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 71 | 2 | 2.9% | -3.69c | 2.64c | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 143 | 7 | 5.0% | -2.0c | 1.17c | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 141 | 2 | 1.4% | -3.69c | 2.09c | 0-0-0 | +0.00u |  |
| MK all fair-1c | 215 | 13 | 6.2% | -1.59c | 1.37c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 212 | 4 | 1.9% | -3.69c | 2.27c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 23.

## Odds API credits (100K/month plan)

Study: 572/day, projected 17170/30 days. All monitors on the key: 2169/day, projected 65062/30 days. Remaining 66350; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T01:20:13Z: 14 games (11 in 24h), quotes {'prophetx': 1182, 'novig': 668, 'kalshi': 1330, 'polymarket_us': 1598}, 512 unmatched, 2104 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 7 B 1, maker posted 0 filled 4, credits used 6 left 66350, 324s
- 2026-10-30T01:10:13Z: 14 games (11 in 24h), quotes {'prophetx': 1182, 'novig': 664, 'kalshi': 1334, 'polymarket_us': 1596}, 512 unmatched, 2099 side/lines, polls [none_due; NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 66372, 181s
- 2026-10-30T01:00:32Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 664, 'kalshi': 1370, 'polymarket_us': 1596}, 528 unmatched, 2119 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 66381, 285s
- 2026-10-30T00:57:00Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 664, 'kalshi': 1396, 'polymarket_us': 1596}, 544 unmatched, 2128 side/lines, polls [none_due; NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 66390, 198s
- 2026-10-30T00:50:16Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 670, 'kalshi': 1398, 'polymarket_us': 1596}, 546 unmatched, 2130 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 66392, 301s
- 2026-10-30T00:40:16Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 672, 'kalshi': 1400, 'polymarket_us': 1596}, 548 unmatched, 2128 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 0 B 0, maker posted 12 filled 0, credits used 4 left 66405, 301s
- 2026-10-30T00:30:17Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 668, 'kalshi': 1428, 'polymarket_us': 1596}, 576 unmatched, 2126 side/lines, polls [none_due; NBA:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 2 left 66423, 283s
- 2026-10-30T00:25:15Z: 14 games (11 in 24h), quotes {'prophetx': 1180, 'novig': 664, 'kalshi': 1440, 'polymarket_us': 1596}, 588 unmatched, 2123 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 66434, 284s
- 2026-10-30T00:19:58Z: 14 games (11 in 24h), quotes {'prophetx': 990, 'novig': 668, 'kalshi': 1438, 'polymarket_us': 1596}, 586 unmatched, 2124 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 66438, 301s
- 2026-10-30T00:10:17Z: 17 games (14 in 24h), quotes {'prophetx': 1078, 'novig': 668, 'kalshi': 1442, 'polymarket_us': 1804}, 382 unmatched, 2473 side/lines, polls [none_due; NFL:fast,NBA:fast], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 4 left 66449, 274s
