# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T02:43:34Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2180 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1617 | 808-809-0 | -118.29u | -7.3% |  |  | criteria not met (1617/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 397 | -5.93c | 18.6% | 79 | -3.91c | 358 | 175-183-0 | -34.05u | -9.5% |  |  | criteria not met (358/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 33 | 15-18-0 | -1.43u | -4.3% |  |  | criteria not met (33/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 23 | 11-12-0 | +0.17u | 0.8% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 8 | 3-5-0 | -1.71u | -21.4% |  |  |  |
| M move-watch: gettable (sightings) | 78 | 71 | -0.71c | 35.2% | 70 | -0.69c | 59 | 34-25-0 | +7.62u | 12.9% | 0.22c | 28s | criteria not met (59/50 graded, CLV not positive) |
| M gettable, line moves | 44 | 40 | -0.66c | 37.5% | 39 | -0.89c | 29 | 16-13-0 | +1.78u | 6.1% | 0.09c | 54s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 30 | 18-12-0 | +5.84u | 19.5% | 0.39c | 28s |  |
| M control: not gettable | 277 | 184 | -0.64c | 33.2% | 180 | -1.17c | 153 | 82-69-2 | +3.52u | 2.3% | 1.82c | 29s |  |
| M all moves | 355 | 255 | -0.66c | 33.7% | 250 | -1.03c | 212 | 116-94-2 | +11.14u | 5.3% | 1.45c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 271 | 145 | -0.09c | 22.1% | 18 | -0.21c | 128 | 61-67-0 | +78.33u | 61.2% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 7.9% | -0.47c | 1.69c | 8-5-0 | +3.25u |  |
| MK novig fair-2c | 176 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 417 | 19 | 4.6% | -0.91c | 1.09c | 9-6-0 | +3.45u |  |
| MK prophetx fair-2c | 412 | 5 | 1.2% | -1.98c | 2.06c | 1-3-0 | -1.95u |  |
| MK all fair-1c | 594 | 33 | 5.6% | -0.73c | 1.26c | 17-11-0 | +6.69u | criteria not met (28/50 graded, CLV not positive) |
| MK all fair-2c | 588 | 11 | 1.9% | -1.42c | 2.23c | 5-5-0 | +0.48u | criteria not met (10/50 graded, CLV not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 530/day, projected 15908/30 days. All monitors on the key: 2041/day, projected 61223/30 days. Remaining 64481; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T02:40:20Z: 53 games (52 in 24h), quotes {'prophetx': 6922, 'novig': 642, 'kalshi': 2344, 'polymarket_us': 1534}, 3507 unmatched, 5523 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 64481, 193s
- 2026-10-31T02:30:30Z: 54 games (53 in 24h), quotes {'prophetx': 6922, 'novig': 638, 'kalshi': 2588, 'polymarket_us': 1782}, 3603 unmatched, 5730 side/lines, polls [NBA:slow; NCAAF:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 64488, 190s
- 2026-10-31T02:23:48Z: 54 games (52 in 24h), quotes {'prophetx': 6894, 'novig': 646, 'kalshi': 2928, 'polymarket_us': 2178}, 3608 unmatched, 5966 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 64501, 285s
- 2026-10-31T02:20:18Z: 54 games (52 in 24h), quotes {'prophetx': 6894, 'novig': 654, 'kalshi': 3664, 'polymarket_us': 3540}, 4016 unmatched, 6771 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 64503, 194s
- 2026-10-31T02:14:12Z: 54 games (52 in 24h), quotes {'prophetx': 5474, 'novig': 642, 'kalshi': 3628, 'polymarket_us': 3482}, 3972 unmatched, 5821 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 7 B 0, maker posted 8 filled 0, credits used 2 left 64512, 253s
- 2026-10-31T02:10:16Z: 55 games (53 in 24h), quotes {'prophetx': 6814, 'novig': 644, 'kalshi': 2744, 'polymarket_us': 2214}, 3562 unmatched, 5907 side/lines, polls [none_due; NCAAF:fast], moves 1, new A 0 B 0, maker posted 4 filled 0, credits used 2 left 64514, 216s
- 2026-10-31T02:00:23Z: 56 games (54 in 24h), quotes {'prophetx': 6814, 'novig': 658, 'kalshi': 3546, 'polymarket_us': 3424}, 3681 unmatched, 6809 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 23 B 0, maker posted 8 filled 0, credits used 8 left 64523, 308s
- 2026-10-31T01:50:16Z: 55 games (52 in 24h), quotes {'prophetx': 6862, 'novig': 660, 'kalshi': 2972, 'polymarket_us': 2136}, 3529 unmatched, 5916 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64540, 211s
- 2026-10-31T01:40:35Z: 55 games (52 in 24h), quotes {'prophetx': 5000, 'novig': 662, 'kalshi': 2872, 'polymarket_us': 2178}, 3343 unmatched, 4202 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64551, 284s
- 2026-10-31T01:35:37Z: 55 games (52 in 24h), quotes {'prophetx': 6854, 'novig': 664, 'kalshi': 3612, 'polymarket_us': 3372}, 3694 unmatched, 5996 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, maker posted 4 filled 0, credits used 4 left 64562, 282s
