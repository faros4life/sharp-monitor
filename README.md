# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T02:05:31Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2168 | 1792 | -2.61c | 25.7% | 684 | -1.26c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 384 | -6.09c | 18.5% | 76 | -4.09c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 77 | 66 | -0.69c | 36.4% | 65 | -0.66c | 50 | 27-23-0 | +3.02u | 6.0% | 0.25c | 28s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 43 | 35 | -0.63c | 40.0% | 34 | -0.86c | 22 | 11-11-0 | -0.80u | -3.6% | 0.12c | 64s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 28 | 16-12-0 | +3.82u | 13.6% | 0.39c | 28s |  |
| M control: not gettable | 277 | 174 | -0.61c | 33.9% | 170 | -1.16c | 132 | 69-61-2 | -0.24u | -0.2% | 1.86c | 29s |  |
| M all moves | 354 | 240 | -0.64c | 34.6% | 235 | -1.02c | 182 | 96-84-2 | +2.77u | 1.5% | 1.49c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 268 | 137 | -0.71c | 21.9% | 17 | -2.85c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 175 | 14 | 8.2% | -0.47c | 1.7c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 174 | 6 | 3.5% | -0.95c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 413 | 19 | 4.7% | -0.91c | 1.1c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 408 | 5 | 1.3% | -1.98c | 2.07c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 588 | 33 | 5.7% | -0.73c | 1.29c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 582 | 11 | 1.9% | -1.42c | 2.25c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 531/day, projected 15933/30 days. All monitors on the key: 2045/day, projected 61357/30 days. Remaining 64523; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T02:00:23Z: 56 games (54 in 24h), quotes {'prophetx': 6814, 'novig': 658, 'kalshi': 3546, 'polymarket_us': 3424}, 3681 unmatched, 6809 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 23 B 0, maker posted 8 filled 0, credits used 8 left 64523, 308s
- 2026-10-31T01:50:16Z: 55 games (52 in 24h), quotes {'prophetx': 6862, 'novig': 660, 'kalshi': 2972, 'polymarket_us': 2136}, 3529 unmatched, 5916 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64540, 211s
- 2026-10-31T01:40:35Z: 55 games (52 in 24h), quotes {'prophetx': 5000, 'novig': 662, 'kalshi': 2872, 'polymarket_us': 2178}, 3343 unmatched, 4202 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64551, 284s
- 2026-10-31T01:35:37Z: 55 games (52 in 24h), quotes {'prophetx': 6854, 'novig': 664, 'kalshi': 3612, 'polymarket_us': 3372}, 3694 unmatched, 5996 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, maker posted 4 filled 0, credits used 4 left 64562, 282s
- 2026-10-31T01:30:38Z: 55 games (52 in 24h), quotes {'prophetx': 6854, 'novig': 666, 'kalshi': 2794, 'polymarket_us': 2116}, 3328 unmatched, 5093 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 64566, 281s
- 2026-10-31T01:26:04Z: 55 games (52 in 24h), quotes {'prophetx': 6862, 'novig': 666, 'kalshi': 2752, 'polymarket_us': 2046}, 3351 unmatched, 5290 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 64577, 255s
- 2026-10-31T01:20:18Z: 55 games (52 in 24h), quotes {'prophetx': 6858, 'novig': 664, 'kalshi': 3254, 'polymarket_us': 3020}, 3588 unmatched, 5766 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 14 B 0, maker posted 0 filled 0, credits used 8 left 64589, 327s
- 2026-10-31T01:10:19Z: 55 games (52 in 24h), quotes {'prophetx': 6786, 'novig': 666, 'kalshi': 2704, 'polymarket_us': 2054}, 3309 unmatched, 5024 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 64611, 191s
- 2026-10-31T01:00:23Z: 55 games (52 in 24h), quotes {'prophetx': 6464, 'novig': 664, 'kalshi': 3960, 'polymarket_us': 2644}, 3734 unmatched, 5791 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 39 B 0, maker posted 16 filled 0, credits used 8 left 64622, 302s
- 2026-10-31T00:50:17Z: 55 games (52 in 24h), quotes {'prophetx': 6288, 'novig': 660, 'kalshi': 2752, 'polymarket_us': 1886}, 3360 unmatched, 5554 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 0 B 0, maker posted 4 filled 0, credits used 4 left 64637, 212s
