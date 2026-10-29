# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T20:12:18Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1316 | 1066 | -3.4c | 23.8% | 365 | -1.6c | 1066 | 528-538-0 | -76.18u | -7.1% |  |  | criteria not met (1066/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 320 | 283 | -6.82c | 17.0% | 49 | -5.12c | 283 | 137-146-0 | -29.96u | -10.6% |  |  | criteria not met (283/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 23 | 18 | -0.67c | 33.3% | 16 | 0.26c | 18 | 6-12-0 | -5.20u | -28.9% |  |  | criteria not met (18/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 16 | 15 | -0.9c | 26.7% | 14 | 0.01c | 15 | 6-9-0 | -2.20u | -14.7% |  |  |  |
| B ref age 5m+ | 6 | 2 | -1.25c | 50.0% | 1 | 1.04c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 44 | 35 | -0.69c | 31.4% | 35 | -0.58c | 35 | 21-14-0 | +6.12u | 17.5% | 0.33c | 164s | criteria not met (35/50 graded, CLV not positive) |
| M gettable, line moves | 20 | 14 | -0.61c | 35.7% | 14 | -0.74c | 14 | 9-5-0 | +3.31u | 23.7% | 0.05c | 158s |  |
| M gettable, price moves | 24 | 21 | -0.74c | 28.6% | 21 | -0.47c | 21 | 12-9-0 | +2.81u | 13.4% | 0.51c | 170s |  |
| M control: not gettable | 138 | 90 | -0.91c | 32.2% | 86 | -1.44c | 93 | 50-41-2 | +3.00u | 3.2% | 1.65c | 148s |  |
| M all moves | 182 | 125 | -0.85c | 32.0% | 121 | -1.19c | 128 | 71-55-2 | +9.13u | 7.1% | 1.33c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 117 | 93 | -6.36c | 10.8% | 9 | -6.81c | 94 | 45-49-0 | +44.99u | 47.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 20 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK novig fair-2c | 20 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-1c | 46 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK prophetx fair-2c | 46 | 0 | 0.0% |  |  | 0-0-0 | +0.00u |  |
| MK all fair-1c | 66 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 66 | 0 | 0.0% |  |  | 0-0-0 | +0.00u | criteria not met (0/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 19.

## Odds API credits (100K/month plan)

Study: 494/day, projected 14809/30 days. All monitors on the key: 2077/day, projected 62303/30 days. Remaining 67003; guard holds 10800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T20:09:35Z: 19 games (6 in 24h), quotes {'prophetx': 598, 'novig': 644, 'kalshi': 1366, 'polymarket_us': 1052}, 203 unmatched, 2173 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 67003, 163s
- 2026-10-29T20:00:20Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 644, 'kalshi': 1372, 'polymarket_us': 1052}, 209 unmatched, 2216 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 67020, 301s
- 2026-10-29T19:50:14Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 643, 'kalshi': 1368, 'polymarket_us': 1052}, 208 unmatched, 2214 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 4 filled 0, credits used 6 left 67052, 165s
- 2026-10-29T19:41:02Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 641, 'kalshi': 1372, 'polymarket_us': 1052}, 208 unmatched, 2213 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 24 filled 0, credits used 6 left 67058, 255s
- 2026-10-29T19:35:31Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 643, 'kalshi': 1368, 'polymarket_us': 1020}, 208 unmatched, 2184 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 67073, 315s
- 2026-10-29T19:30:31Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 645, 'kalshi': 1368, 'polymarket_us': 1052}, 208 unmatched, 2216 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 67092, 286s
- 2026-10-29T19:26:44Z: 19 games (6 in 24h), quotes {'prophetx': 670, 'novig': 645, 'kalshi': 1374, 'polymarket_us': 1052}, 209 unmatched, 2222 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 16 filled 0, credits used 6 left 67098, 213s
- 2026-10-29T19:20:15Z: 19 games (6 in 24h), quotes {'prophetx': 598, 'novig': 645, 'kalshi': 1376, 'polymarket_us': 1052}, 208 unmatched, 2184 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 0 B 0, maker posted 16 filled 0, credits used 12 left 67117, 301s
- 2026-10-29T19:10:15Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 645, 'kalshi': 1378, 'polymarket_us': 1052}, 210 unmatched, 2222 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 67153, 166s
- 2026-10-29T19:00:20Z: 19 games (6 in 24h), quotes {'prophetx': 662, 'novig': 645, 'kalshi': 1380, 'polymarket_us': 1052}, 209 unmatched, 2226 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast; NFL:fast,NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 67168, 301s
