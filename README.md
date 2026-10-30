# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T23:25:24Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1934 | 1474 | -2.86c | 26.1% | 539 | -1.34c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 469 | 344 | -6.31c | 19.8% | 67 | -4.08c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 36 | 29 | -0.88c | 37.9% | 27 | -0.13c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 23 | 19 | -0.83c | 31.6% | 18 | -0.11c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 11 | 8 | -1.9c | 37.5% | 7 | -0.91c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 74 | 54 | -0.73c | 33.3% | 54 | -0.61c | 50 | 27-23-0 | +3.02u | 6.0% | 0.19c | 46s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 41 | 26 | -0.7c | 34.6% | 26 | -0.74c | 22 | 11-11-0 | -0.80u | -3.6% | 0.02c | 91s |  |
| M gettable, price moves | 33 | 28 | -0.76c | 32.1% | 28 | -0.49c | 28 | 16-12-0 | +3.82u | 13.6% | 0.36c | 28s |  |
| M control: not gettable | 262 | 132 | -0.64c | 34.1% | 127 | -1.15c | 132 | 69-61-2 | -0.24u | -0.2% | 1.86c | 148s |  |
| M all moves | 336 | 186 | -0.67c | 33.9% | 181 | -0.99c | 182 | 96-84-2 | +2.77u | 1.5% | 1.44c | 64s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 197 | 127 | -1.08c | 20.5% | 13 | 2.04c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 163 | 13 | 8.6% | -0.61c | 1.7c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 162 | 6 | 3.9% | -1.19c | 2.6c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 381 | 19 | 5.6% | -1.26c | 1.12c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 376 | 5 | 1.5% | -1.54c | 2.06c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 544 | 32 | 6.5% | -0.98c | 1.32c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 538 | 11 | 2.2% | -1.37c | 2.25c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 28.

## Odds API credits (100K/month plan)

Study: 516/day, projected 15466/30 days. All monitors on the key: 2034/day, projected 61007/30 days. Remaining 64787; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T23:20:23Z: 58 games (48 in 24h), quotes {'prophetx': 5692, 'novig': 710, 'kalshi': 2346, 'polymarket_us': 1936}, 1371 unmatched, 5814 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 24 filled 1, credits used 8 left 64787, 301s
- 2026-10-30T23:10:25Z: 59 games (49 in 24h), quotes {'prophetx': 2814, 'novig': 720, 'kalshi': 2578, 'polymarket_us': 1716}, 963 unmatched, 4013 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 64813, 222s
- 2026-10-30T23:05:13Z: 59 games (49 in 24h), quotes {'prophetx': 6246, 'novig': 722, 'kalshi': 2322, 'polymarket_us': 1818}, 1110 unmatched, 6179 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 4 filled 0, credits used 4 left 64826, 261s
- 2026-10-30T22:59:26Z: 60 games (47 in 24h), quotes {'prophetx': 4888, 'novig': 664, 'kalshi': 2766, 'polymarket_us': 1846}, 1345 unmatched, 5202 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 2 B 0, maker posted 0 filled 1, credits used 4 left 64830, 327s
- 2026-10-30T22:55:59Z: 60 games (47 in 24h), quotes {'prophetx': 6212, 'novig': 662, 'kalshi': 2602, 'polymarket_us': 1974}, 1239 unmatched, 6274 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 16 filled 0, credits used 4 left 64850, 186s
- 2026-10-30T22:50:21Z: 60 games (47 in 24h), quotes {'prophetx': 6204, 'novig': 666, 'kalshi': 2950, 'polymarket_us': 2048}, 1484 unmatched, 6366 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 10 B 0, maker posted 41 filled 6, credits used 4 left 64854, 261s
- 2026-10-30T22:40:27Z: 60 games (47 in 24h), quotes {'prophetx': 0, 'novig': 668, 'kalshi': 3680, 'polymarket_us': 3258}, 2452 unmatched, 3692 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 4, new A 4 B 1, maker posted 5 filled 0, credits used 8 left 64869, 301s
- 2026-10-30T22:30:35Z: 60 games (47 in 24h), quotes {'prophetx': 6146, 'novig': 666, 'kalshi': 3672, 'polymarket_us': 3244}, 2882 unmatched, 6869 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 0 filled 2, credits used 4 left 64886, 311s
- 2026-10-30T22:26:05Z: 60 games (46 in 24h), quotes {'prophetx': 6042, 'novig': 664, 'kalshi': 3600, 'polymarket_us': 3040}, 2671 unmatched, 6779 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, maker posted 16 filled 0, credits used 4 left 64894, 254s
- 2026-10-30T22:20:18Z: 60 games (46 in 24h), quotes {'prophetx': 6026, 'novig': 656, 'kalshi': 3100, 'polymarket_us': 1988}, 1679 unmatched, 6450 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 5 B 0, maker posted 20 filled 0, credits used 8 left 64909, 329s
