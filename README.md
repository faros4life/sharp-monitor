# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T16:32:55Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1279 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 315 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 23 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 16 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 6 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 41 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 162s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 18 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 158s |  |
| M gettable, price moves | 23 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 162s |  |
| M control: not gettable | 133 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 29s |  |
| M all moves | 174 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 116 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK all fair-1c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 0 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 19.

## Odds API credits (100K/month plan)

Study: 446/day, projected 13377/30 days. All monitors on the key: 1991/day, projected 59729/30 days. Remaining 67479; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T16:30:17Z: 18 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1240, 'polymarket_us': 948}, 96 unmatched, 2086 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 67479, 158s
- 2026-10-29T16:22:58Z: 17 games (6 in 24h), quotes {'prophetx': 668, 'novig': 625, 'kalshi': 1126, 'polymarket_us': 948}, 98 unmatched, 1970 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 67488, 159s
- 2026-10-29T16:20:04Z: 17 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1064, 'polymarket_us': 948}, 96 unmatched, 1908 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 67503, 158s
- 2026-10-29T16:17:10Z: 17 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 1018, 'polymarket_us': 948}, 96 unmatched, 1864 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 67503, 158s
- 2026-10-29T16:10:13Z: 17 games (6 in 24h), quotes {'prophetx': 668, 'novig': 622, 'kalshi': 1012, 'polymarket_us': 948}, 96 unmatched, 1861 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 67514, 158s
- 2026-10-29T16:00:20Z: 16 games (6 in 24h), quotes {'prophetx': 668, 'novig': 624, 'kalshi': 1002, 'polymarket_us': 948}, 97 unmatched, 1857 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 67525, 159s
- 2026-10-29T15:50:14Z: 16 games (6 in 24h), quotes {'prophetx': 668, 'novig': 624, 'kalshi': 1006, 'polymarket_us': 948}, 98 unmatched, 1860 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 67547, 158s
- 2026-10-29T15:40:16Z: 16 games (6 in 24h), quotes {'prophetx': 668, 'novig': 623, 'kalshi': 906, 'polymarket_us': 948}, 94 unmatched, 1760 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 67562, 158s
- 2026-10-29T15:30:51Z: 15 games (6 in 24h), quotes {'prophetx': 668, 'novig': 631, 'kalshi': 828, 'polymarket_us': 948}, 99 unmatched, 1680 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 67589, 159s
- 2026-10-29T15:27:56Z: 14 games (6 in 24h), quotes {'prophetx': 668, 'novig': 630, 'kalshi': 818, 'polymarket_us': 948}, 97 unmatched, 1668 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 67598, 159s
