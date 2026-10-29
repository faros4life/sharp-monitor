# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T13:32:44Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1193 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 310 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 21 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 15 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 5 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 39 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 151s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 17 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 151s |  |
| M gettable, price moves | 22 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 105s |  |
| M control: not gettable | 127 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 28s |  |
| M all moves | 166 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 46s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 113 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

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

A and B on the same side/line: 18.

## Odds API credits (100K/month plan)

Study: 454/day, projected 13614/30 days. All monitors on the key: 1956/day, projected 58672/30 days. Remaining 67789; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T13:30:18Z: 9 games (6 in 24h), quotes {'prophetx': 654, 'novig': 575, 'kalshi': 628, 'polymarket_us': 948}, 95 unmatched, 1542 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 2, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 67789, 146s
- 2026-10-29T13:20:14Z: 9 games (6 in 24h), quotes {'prophetx': 654, 'novig': 573, 'kalshi': 626, 'polymarket_us': 948}, 91 unmatched, 1545 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 67813, 147s
- 2026-10-29T13:10:13Z: 9 games (6 in 24h), quotes {'prophetx': 654, 'novig': 574, 'kalshi': 626, 'polymarket_us': 948}, 94 unmatched, 1542 side/lines, polls [none_due], moves 0, new A 7 B 0, credits used 0 left 67822, 148s
- 2026-10-29T13:00:21Z: 9 games (6 in 24h), quotes {'prophetx': 654, 'novig': 574, 'kalshi': 626, 'polymarket_us': 948}, 94 unmatched, 1544 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 7, new A 10 B 0, credits used 6 left 67831, 148s
- 2026-10-29T12:55:12Z: outside read hours: closes/grades only
- 2026-10-29T12:50:15Z: outside read hours: closes/grades only
- 2026-10-29T12:40:13Z: outside read hours: closes/grades only
- 2026-10-29T12:33:57Z: outside read hours: closes/grades only
- 2026-10-29T12:30:17Z: outside read hours: closes/grades only
- 2026-10-29T12:20:13Z: outside read hours: closes/grades only
