# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-30T20:05:55Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1822 | 1390 | -2.87c | 25.8% | 502 | -1.4c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 446 | 327 | -6.26c | 19.6% | 63 | -4.52c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 34 | 27 | -0.78c | 40.7% | 25 | -0.07c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 21 | 18 | -0.68c | 33.3% | 17 | 0.05c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 11 | 7 | -2.01c | 42.9% | 6 | -1.23c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 65 | 50 | -0.72c | 32.0% | 50 | -0.54c | 50 | 27-23-0 | +3.02u | 6.0% | 0.27c | 151s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 36 | 22 | -0.67c | 31.8% | 22 | -0.61c | 22 | 11-11-0 | -0.80u | -3.6% | 0.16c | 158s |  |
| M gettable, price moves | 29 | 28 | -0.76c | 32.1% | 28 | -0.49c | 28 | 16-12-0 | +3.82u | 13.6% | 0.36c | 49s |  |
| M control: not gettable | 229 | 129 | -0.71c | 32.6% | 124 | -1.23c | 132 | 69-61-2 | -0.24u | -0.2% | 1.76c | 164s |  |
| M all moves | 294 | 179 | -0.71c | 32.4% | 174 | -1.03c | 182 | 96-84-2 | +2.77u | 1.5% | 1.39c | 163s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 185 | 120 | -1.86c | 18.3% | 12 | -1.49c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 117 | 8 | 7.9% | -0.87c | 1.75c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 117 | 3 | 3.0% | -1.19c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 244 | 11 | 5.2% | -1.77c | 1.15c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 241 | 2 | 1.0% | -1.54c | 2.08c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 361 | 19 | 6.1% | -1.35c | 1.34c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 358 | 5 | 1.6% | -1.37c | 2.26c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 26.

## Odds API credits (100K/month plan)

Study: 493/day, projected 14784/30 days. All monitors on the key: 1968/day, projected 59026/30 days. Remaining 65268; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-30T20:00:24Z: 60 games (43 in 24h), quotes {'prophetx': 5586, 'novig': 658, 'kalshi': 2904, 'polymarket_us': 1858}, 1502 unmatched, 6073 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 3 B 0, maker posted 8 filled 1, credits used 8 left 65268, 332s
- 2026-10-30T19:50:17Z: 60 games (42 in 24h), quotes {'prophetx': 5356, 'novig': 664, 'kalshi': 3378, 'polymarket_us': 2768}, 2308 unmatched, 6266 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, maker posted 24 filled 1, credits used 4 left 65296, 238s
- 2026-10-30T19:40:19Z: 60 games (40 in 24h), quotes {'prophetx': 5104, 'novig': 660, 'kalshi': 3656, 'polymarket_us': 2890}, 2451 unmatched, 6162 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 9 filled 0, credits used 8 left 65306, 301s
- 2026-10-30T19:31:00Z: 60 games (40 in 24h), quotes {'prophetx': 5106, 'novig': 664, 'kalshi': 3696, 'polymarket_us': 3134}, 2686 unmatched, 6151 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 7, new A 17 B 0, maker posted 8 filled 1, credits used 4 left 65330, 364s
- 2026-10-30T19:26:06Z: 60 games (31 in 24h), quotes {'prophetx': 4016, 'novig': 658, 'kalshi': 3358, 'polymarket_us': 2700}, 2227 unmatched, 5146 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 9 B 0, maker posted 9 filled 0, credits used 4 left 65334, 277s
- 2026-10-30T19:20:17Z: 60 games (31 in 24h), quotes {'prophetx': 4008, 'novig': 668, 'kalshi': 3682, 'polymarket_us': 2286}, 1993 unmatched, 5296 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 7, new A 17 B 0, maker posted 24 filled 1, credits used 8 left 65345, 301s
- 2026-10-30T19:10:18Z: 60 games (30 in 24h), quotes {'prophetx': 3876, 'novig': 666, 'kalshi': 2878, 'polymarket_us': 1910}, 1463 unmatched, 4714 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 0 B 1, maker posted 12 filled 0, credits used 4 left 65362, 186s
- 2026-10-30T19:00:22Z: 60 games (30 in 24h), quotes {'prophetx': 3874, 'novig': 650, 'kalshi': 2366, 'polymarket_us': 1910}, 1118 unmatched, 4592 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 7, new A 3 B 0, maker posted 6 filled 0, credits used 8 left 65373, 393s
- 2026-10-30T18:50:15Z: 60 games (27 in 24h), quotes {'prophetx': 3458, 'novig': 656, 'kalshi': 2932, 'polymarket_us': 1910}, 1330 unmatched, 4545 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 3 B 0, maker posted 4 filled 0, credits used 4 left 65388, 234s
- 2026-10-30T18:43:44Z: 60 games (27 in 24h), quotes {'prophetx': 3194, 'novig': 658, 'kalshi': 2780, 'polymarket_us': 1724}, 1201 unmatched, 4278 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 1 B 0, maker posted 35 filled 0, credits used 4 left 65399, 300s
