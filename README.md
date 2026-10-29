# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T15:27:40Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1255 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 311 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
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

Study: 447/day, projected 13414/30 days. All monitors on the key: 1970/day, projected 59106/30 days. Remaining 67607; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T15:24:58Z: 13 games (6 in 24h), quotes {'prophetx': 668, 'novig': 631, 'kalshi': 834, 'polymarket_us': 948}, 100 unmatched, 1680 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 67607, 162s
- 2026-10-29T15:20:14Z: 12 games (6 in 24h), quotes {'prophetx': 668, 'novig': 631, 'kalshi': 842, 'polymarket_us': 948}, 100 unmatched, 1688 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 67607, 161s
- 2026-10-29T15:10:14Z: 11 games (6 in 24h), quotes {'prophetx': 668, 'novig': 631, 'kalshi': 786, 'polymarket_us': 948}, 99 unmatched, 1632 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 67626, 159s
- 2026-10-29T15:00:20Z: 11 games (6 in 24h), quotes {'prophetx': 660, 'novig': 631, 'kalshi': 702, 'polymarket_us': 948}, 98 unmatched, 1544 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 67637, 162s
- 2026-10-29T14:50:16Z: 9 games (6 in 24h), quotes {'prophetx': 660, 'novig': 627, 'kalshi': 702, 'polymarket_us': 948}, 98 unmatched, 1543 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 4, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 67659, 187s
- 2026-10-29T14:40:17Z: 9 games (6 in 24h), quotes {'prophetx': 660, 'novig': 629, 'kalshi': 702, 'polymarket_us': 948}, 97 unmatched, 1543 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 67678, 160s
- 2026-10-29T14:37:08Z: 9 games (6 in 24h), quotes {'prophetx': 660, 'novig': 631, 'kalshi': 702, 'polymarket_us': 948}, 98 unmatched, 1545 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 67687, 162s
- 2026-10-29T14:34:12Z: 9 games (6 in 24h), quotes {'prophetx': 660, 'novig': 631, 'kalshi': 702, 'polymarket_us': 948}, 99 unmatched, 1545 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 67687, 161s
- 2026-10-29T14:30:17Z: 9 games (6 in 24h), quotes {'prophetx': 668, 'novig': 633, 'kalshi': 702, 'polymarket_us': 948}, 98 unmatched, 1551 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow], moves 3, new A 11 B 0, maker posted 0 filled 0, credits used 6 left 67691, 161s
- 2026-10-29T14:20:15Z: 9 games (6 in 24h), quotes {'prophetx': 668, 'novig': 639, 'kalshi': 700, 'polymarket_us': 948}, 91 unmatched, 1551 side/lines, polls [none_due], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 0 left 67717, 164s
