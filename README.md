# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T21:54:03Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1336 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 320 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 23 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 16 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 6 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 46 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 157s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 20 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 158s |  |
| M gettable, price moves | 26 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 105s |  |
| M control: not gettable | 140 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 148s |  |
| M all moves | 186 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 117 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 36 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 36 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 80 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 80 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK all fair-1c | 116 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 116 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 19.

## Odds API credits (100K/month plan)

Study: 531/day, projected 15924/30 days. All monitors on the key: 2121/day, projected 63625/30 days. Remaining 66766; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T21:50:15Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 647, 'kalshi': 1384, 'polymarket_us': 0}, 106 unmatched, 1782 side/lines, polls [none_due; NBA:fast; NFL:fast,NCAAF:fast], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 66766, 228s
- 2026-10-29T21:44:47Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 645, 'kalshi': 1384, 'polymarket_us': 1052}, 210 unmatched, 2230 side/lines, polls [none_due; NBA:fast; NFL:fast,NCAAF:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 66772, 256s
- 2026-10-29T21:39:02Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 645, 'kalshi': 1380, 'polymarket_us': 1052}, 210 unmatched, 2216 side/lines, polls [NFL:fast,NCAAF:fast; NBA:fast; NFL:fast,NCAAF:fast], moves 1, new A 2 B 0, maker posted 8 filled 0, credits used 10 left 66789, 329s
- 2026-10-29T21:30:32Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 643, 'kalshi': 1388, 'polymarket_us': 1052}, 212 unmatched, 2228 side/lines, polls [none_due; NFL:fast,NCAAF:fast; NBA:fast], moves 0, new A 1 B 0, maker posted 8 filled 0, credits used 6 left 66808, 283s
- 2026-10-29T21:25:31Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 645, 'kalshi': 1390, 'polymarket_us': 1052}, 212 unmatched, 2232 side/lines, polls [none_due; NFL:fast,NCAAF:fast; NBA:fast], moves 0, new A 1 B 0, maker posted 8 filled 0, credits used 6 left 66821, 284s
- 2026-10-29T21:20:14Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 647, 'kalshi': 1388, 'polymarket_us': 1052}, 212 unmatched, 2232 side/lines, polls [NBA:fast; NFL:fast,NCAAF:fast; NBA:fast], moves 0, new A 2 B 0, maker posted 12 filled 0, credits used 8 left 66829, 301s
- 2026-10-29T21:10:16Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 647, 'kalshi': 1376, 'polymarket_us': 1052}, 210 unmatched, 2222 side/lines, polls [NFL:fast,NCAAF:fast; NBA:fast; NFL:fast,NCAAF:fast], moves 1, new A 1 B 0, maker posted 0 filled 0, credits used 10 left 66857, 330s
- 2026-10-29T21:00:34Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 639, 'kalshi': 1374, 'polymarket_us': 1052}, 208 unmatched, 2214 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 66878, 284s
- 2026-10-29T20:55:33Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 639, 'kalshi': 1368, 'polymarket_us': 1052}, 208 unmatched, 2208 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 6 left 66884, 285s
- 2026-10-29T20:50:16Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 642, 'kalshi': 1364, 'polymarket_us': 1052}, 209 unmatched, 2204 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 24 filled 0, credits used 12 left 66899, 302s
