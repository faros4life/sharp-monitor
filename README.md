# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T02:17:11Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1500 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 359 | 327 | -6.26c | 19.6% | 63 | -4.52c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 28 | 27 | -0.78c | 40.7% | 25 | -0.07c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 18 | 18 | -0.68c | 33.3% | 17 | 0.05c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 8 | 7 | -2.01c | 42.9% | 6 | -1.23c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 51 | 50 | -0.72c | 32.0% | 50 | -0.54c | 35 | 21-14-0 | +6.12u | 17.5% | 0.27c | 139s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 23 | 22 | -0.67c | 31.8% | 22 | -0.61c | 14 | 9-5-0 | +3.31u | 23.7% | 0.16c | 139s |  |
| M gettable, price moves | 28 | 28 | -0.76c | 32.1% | 28 | -0.49c | 21 | 12-9-0 | +2.81u | 13.4% | 0.36c | 105s |  |
| M control: not gettable | 156 | 129 | -0.71c | 32.6% | 124 | -1.23c | 93 | 50-41-2 | +3.00u | 3.2% | 1.76c | 28s |  |
| M all moves | 207 | 179 | -0.71c | 32.4% | 174 | -1.03c | 128 | 71-55-2 | +9.13u | 7.1% | 1.39c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 133 | 120 | -1.86c | 18.3% | 12 | -1.49c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 74 | 6 | 8.1% | -0.87c | 1.75c | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 73 | 2 | 2.7% | -1.19c | 2.63c | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 149 | 7 | 4.7% | -1.77c | 1.15c | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 147 | 2 | 1.4% | -1.54c | 2.08c | 0-0-0 | +0.00u |  |
| MK all fair-1c | 223 | 13 | 5.8% | -1.35c | 1.34c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 220 | 4 | 1.8% | -1.37c | 2.26c | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 23.

## Odds API credits (100K/month plan)

Study: 571/day, projected 17125/30 days. All monitors on the key: 2163/day, projected 64887/30 days. Remaining 66282; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T02:14:07Z: 13 games (12 in 24h), quotes {'prophetx': 1246, 'novig': 672, 'kalshi': 1266, 'polymarket_us': 1718}, 504 unmatched, 2160 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 66282, 184s
- 2026-10-30T02:10:13Z: 13 games (12 in 24h), quotes {'prophetx': 1246, 'novig': 660, 'kalshi': 1266, 'polymarket_us': 1484}, 502 unmatched, 2043 side/lines, polls [none_due], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 0 left 66284, 181s
- 2026-10-30T02:00:19Z: 14 games (11 in 24h), quotes {'prophetx': 1230, 'novig': 666, 'kalshi': 1312, 'polymarket_us': 1718}, 466 unmatched, 2219 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 4 left 66293, 183s
- 2026-10-30T01:52:18Z: 14 games (11 in 24h), quotes {'prophetx': 1206, 'novig': 670, 'kalshi': 1304, 'polymarket_us': 1598}, 482 unmatched, 2158 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 66304, 285s
- 2026-10-30T01:48:59Z: 14 games (11 in 24h), quotes {'prophetx': 1202, 'novig': 668, 'kalshi': 1316, 'polymarket_us': 1598}, 487 unmatched, 2162 side/lines, polls [none_due; NBA:fast], moves 0, new A 8 B 1, maker posted 8 filled 0, credits used 2 left 66313, 183s
- 2026-10-30T01:40:17Z: 14 games (11 in 24h), quotes {'prophetx': 1202, 'novig': 666, 'kalshi': 1316, 'polymarket_us': 1598}, 498 unmatched, 2155 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 7 B 0, maker posted 4 filled 0, credits used 6 left 66315, 301s
- 2026-10-30T01:30:30Z: 14 games (11 in 24h), quotes {'prophetx': 1202, 'novig': 662, 'kalshi': 1330, 'polymarket_us': 1598}, 510 unmatched, 2146 side/lines, polls [none_due; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 2 left 66335, 284s
- 2026-10-30T01:26:36Z: 14 games (11 in 24h), quotes {'prophetx': 1202, 'novig': 660, 'kalshi': 1328, 'polymarket_us': 1598}, 512 unmatched, 2152 side/lines, polls [none_due; NBA:fast], moves 0, new A 8 B 0, maker posted 4 filled 0, credits used 2 left 66339, 218s
- 2026-10-30T01:20:13Z: 14 games (11 in 24h), quotes {'prophetx': 1182, 'novig': 668, 'kalshi': 1330, 'polymarket_us': 1598}, 512 unmatched, 2104 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 7 B 1, maker posted 0 filled 4, credits used 6 left 66350, 324s
- 2026-10-30T01:10:13Z: 14 games (11 in 24h), quotes {'prophetx': 1182, 'novig': 664, 'kalshi': 1334, 'polymarket_us': 1596}, 512 unmatched, 2099 side/lines, polls [none_due; NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 66372, 181s
