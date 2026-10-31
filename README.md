# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T02:23:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2177 | 1851 | -2.56c | 25.5% | 719 | -1.24c | 1437 | 714-723-0 | -105.43u | -7.3% |  |  | criteria not met (1437/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 391 | -6.0c | 18.7% | 79 | -3.91c | 336 | 164-172-0 | -32.54u | -9.7% |  |  | criteria not met (336/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 28 | 11-17-0 | -4.78u | -17.1% |  |  | criteria not met (28/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 19 | 8-11-0 | -2.08u | -10.9% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 78 | 68 | -0.71c | 35.3% | 67 | -0.67c | 52 | 28-24-0 | +2.92u | 5.6% | 0.22c | 28s | criteria not met (52/50 graded, CLV not positive) |
| M gettable, line moves | 44 | 37 | -0.67c | 37.8% | 36 | -0.87c | 24 | 12-12-0 | -0.90u | -3.7% | 0.08c | 54s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 28 | 16-12-0 | +3.82u | 13.6% | 0.39c | 28s |  |
| M control: not gettable | 277 | 182 | -0.66c | 32.4% | 178 | -1.18c | 134 | 71-61-2 | +1.55u | 1.2% | 1.81c | 29s |  |
| M all moves | 355 | 250 | -0.67c | 33.2% | 245 | -1.04c | 186 | 99-85-2 | +4.47u | 2.4% | 1.45c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 270 | 138 | -0.72c | 21.7% | 17 | -2.85c | 123 | 58-65-0 | +77.41u | 62.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 8.1% | -0.47c | 1.7c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 176 | 6 | 3.5% | -0.95c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 417 | 19 | 4.6% | -0.91c | 1.1c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 412 | 5 | 1.2% | -1.98c | 2.07c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 594 | 33 | 5.7% | -0.73c | 1.27c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 588 | 11 | 1.9% | -1.42c | 2.24c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 531/day, projected 15921/30 days. All monitors on the key: 2043/day, projected 61281/30 days. Remaining 64503; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T02:20:18Z: 54 games (52 in 24h), quotes {'prophetx': 6894, 'novig': 654, 'kalshi': 3664, 'polymarket_us': 3540}, 4016 unmatched, 6771 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 64503, 194s
- 2026-10-31T02:14:12Z: 54 games (52 in 24h), quotes {'prophetx': 5474, 'novig': 642, 'kalshi': 3628, 'polymarket_us': 3482}, 3972 unmatched, 5821 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 7 B 0, maker posted 8 filled 0, credits used 2 left 64512, 253s
- 2026-10-31T02:10:16Z: 55 games (53 in 24h), quotes {'prophetx': 6814, 'novig': 644, 'kalshi': 2744, 'polymarket_us': 2214}, 3562 unmatched, 5907 side/lines, polls [none_due; NCAAF:fast], moves 1, new A 0 B 0, maker posted 4 filled 0, credits used 2 left 64514, 216s
- 2026-10-31T02:00:23Z: 56 games (54 in 24h), quotes {'prophetx': 6814, 'novig': 658, 'kalshi': 3546, 'polymarket_us': 3424}, 3681 unmatched, 6809 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 23 B 0, maker posted 8 filled 0, credits used 8 left 64523, 308s
- 2026-10-31T01:50:16Z: 55 games (52 in 24h), quotes {'prophetx': 6862, 'novig': 660, 'kalshi': 2972, 'polymarket_us': 2136}, 3529 unmatched, 5916 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64540, 211s
- 2026-10-31T01:40:35Z: 55 games (52 in 24h), quotes {'prophetx': 5000, 'novig': 662, 'kalshi': 2872, 'polymarket_us': 2178}, 3343 unmatched, 4202 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64551, 284s
- 2026-10-31T01:35:37Z: 55 games (52 in 24h), quotes {'prophetx': 6854, 'novig': 664, 'kalshi': 3612, 'polymarket_us': 3372}, 3694 unmatched, 5996 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, maker posted 4 filled 0, credits used 4 left 64562, 282s
- 2026-10-31T01:30:38Z: 55 games (52 in 24h), quotes {'prophetx': 6854, 'novig': 666, 'kalshi': 2794, 'polymarket_us': 2116}, 3328 unmatched, 5093 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 64566, 281s
- 2026-10-31T01:26:04Z: 55 games (52 in 24h), quotes {'prophetx': 6862, 'novig': 666, 'kalshi': 2752, 'polymarket_us': 2046}, 3351 unmatched, 5290 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 64577, 255s
- 2026-10-31T01:20:18Z: 55 games (52 in 24h), quotes {'prophetx': 6858, 'novig': 664, 'kalshi': 3254, 'polymarket_us': 3020}, 3588 unmatched, 5766 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 14 B 0, maker posted 0 filled 0, credits used 8 left 64589, 327s
