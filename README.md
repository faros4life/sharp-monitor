# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T14:20:28Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1599 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 372 | 327 | -6.26c | 19.6% | 63 | -4.52c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 29 | 27 | -0.78c | 40.7% | 25 | -0.07c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 18 | 18 | -0.68c | 33.3% | 17 | 0.05c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 9 | 7 | -2.01c | 42.9% | 6 | -1.23c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 56 | 50 | -0.72c | 32.0% | 50 | -0.54c | 50 | 27-23-0 | +3.02u | 6.0% | 0.27c | 164s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 28 | 22 | -0.67c | 31.8% | 22 | -0.61c | 22 | 11-11-0 | -0.80u | -3.6% | 0.16c | 167s |  |
| M gettable, price moves | 28 | 28 | -0.76c | 32.1% | 28 | -0.49c | 28 | 16-12-0 | +3.82u | 13.6% | 0.36c | 105s |  |
| M control: not gettable | 182 | 129 | -0.71c | 32.6% | 124 | -1.23c | 132 | 69-61-2 | -0.24u | -0.2% | 1.76c | 164s |  |
| M all moves | 238 | 179 | -0.71c | 32.4% | 174 | -1.03c | 182 | 96-84-2 | +2.77u | 1.5% | 1.39c | 164s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 138 | 120 | -1.86c | 18.3% | 12 | -1.49c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 74 | 6 | 8.1% | -0.87c | 1.75c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 73 | 2 | 2.7% | -1.19c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 149 | 7 | 4.7% | -1.77c | 1.15c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 147 | 2 | 1.4% | -1.54c | 2.08c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 223 | 13 | 5.8% | -1.35c | 1.34c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 220 | 4 | 1.8% | -1.37c | 2.26c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 24.

## Odds API credits (100K/month plan)

Study: 479/day, projected 14366/30 days. All monitors on the key: 1933/day, projected 57993/30 days. Remaining 65832; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T14:17:22Z: 60 games (13 in 24h), quotes {'prophetx': 1256, 'novig': 670, 'kalshi': 2226, 'polymarket_us': 1732}, 657 unmatched, 3390 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 65832, 185s
- 2026-10-30T14:10:17Z: 60 games (13 in 24h), quotes {'prophetx': 1410, 'novig': 666, 'kalshi': 3940, 'polymarket_us': 1908}, 1487 unmatched, 4445 side/lines, polls [NCAAF:slow,NBA:slow], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 4 left 65839, 189s
- 2026-10-30T14:00:22Z: 60 games (13 in 24h), quotes {'prophetx': 1408, 'novig': 662, 'kalshi': 2916, 'polymarket_us': 1878}, 1147 unmatched, 3749 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 65852, 183s
- 2026-10-30T13:50:15Z: 60 games (13 in 24h), quotes {'prophetx': 1406, 'novig': 660, 'kalshi': 2650, 'polymarket_us': 1678}, 951 unmatched, 3591 side/lines, polls [NCAAF:slow,NBA:slow], moves 5, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 65861, 236s
- 2026-10-30T13:40:16Z: 60 games (13 in 24h), quotes {'prophetx': 1406, 'novig': 664, 'kalshi': 2746, 'polymarket_us': 1676}, 1016 unmatched, 3617 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 65885, 183s
- 2026-10-30T13:30:27Z: 60 games (13 in 24h), quotes {'prophetx': 1386, 'novig': 666, 'kalshi': 2360, 'polymarket_us': 1702}, 782 unmatched, 3464 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 65889, 184s
- 2026-10-30T13:27:04Z: 60 games (13 in 24h), quotes {'prophetx': 1280, 'novig': 670, 'kalshi': 3674, 'polymarket_us': 1908}, 1410 unmatched, 4218 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 65900, 186s
- 2026-10-30T13:23:38Z: 60 games (13 in 24h), quotes {'prophetx': 1386, 'novig': 664, 'kalshi': 3988, 'polymarket_us': 1908}, 1492 unmatched, 4489 side/lines, polls [NCAAF:slow,NBA:slow], moves 3, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 65907, 189s
- 2026-10-30T13:20:17Z: 60 games (13 in 24h), quotes {'prophetx': 1386, 'novig': 666, 'kalshi': 2558, 'polymarket_us': 1810}, 892 unmatched, 3609 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 65913, 183s
- 2026-10-30T13:10:16Z: 60 games (13 in 24h), quotes {'prophetx': 1386, 'novig': 666, 'kalshi': 3702, 'polymarket_us': 1908}, 1423 unmatched, 4267 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 65920, 185s
