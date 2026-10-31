# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T01:05:25Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2120 | 1792 | -2.61c | 25.7% | 684 | -1.26c | 1390 | 694-696-0 | -97.14u | -7.0% |  |  | criteria not met (1390/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 540 | 384 | -6.09c | 18.5% | 76 | -4.09c | 327 | 160-167-0 | -33.24u | -10.2% |  |  | criteria not met (327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 27 | 11-16-0 | -3.78u | -14.0% |  |  | criteria not met (27/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 18 | 8-10-0 | -1.08u | -6.0% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 7 | 2-5-0 | -2.81u | -40.2% |  |  |  |
| M move-watch: gettable (sightings) | 75 | 66 | -0.69c | 36.4% | 65 | -0.66c | 50 | 27-23-0 | +3.02u | 6.0% | 0.25c | 44s | criteria not met (50/50 graded, CLV not positive) |
| M gettable, line moves | 41 | 35 | -0.63c | 40.0% | 34 | -0.86c | 22 | 11-11-0 | -0.80u | -3.6% | 0.12c | 91s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 28 | 16-12-0 | +3.82u | 13.6% | 0.39c | 28s |  |
| M control: not gettable | 275 | 174 | -0.61c | 33.9% | 170 | -1.16c | 132 | 69-61-2 | -0.24u | -0.2% | 1.86c | 29s |  |
| M all moves | 350 | 240 | -0.64c | 34.6% | 235 | -1.02c | 182 | 96-84-2 | +2.77u | 1.5% | 1.49c | 36s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 256 | 137 | -0.71c | 21.9% | 17 | -2.85c | 121 | 58-63-0 | +79.41u | 65.6% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 173 | 14 | 8.3% | -0.47c | 1.7c | 4-2-0 | +2.16u |  |
| MK novig fair-2c | 172 | 6 | 3.6% | -0.95c | 2.63c | 1-1-0 | +0.08u |  |
| MK prophetx fair-1c | 409 | 19 | 4.8% | -0.91c | 1.1c | 5-2-0 | +3.24u |  |
| MK prophetx fair-2c | 404 | 5 | 1.3% | -1.98c | 2.07c | 1-1-0 | +0.05u |  |
| MK all fair-1c | 582 | 33 | 5.8% | -0.73c | 1.29c | 9-4-0 | +5.41u | criteria not met (13/50 graded, CLV not positive) |
| MK all fair-2c | 576 | 11 | 2.0% | -1.42c | 2.25c | 2-2-0 | +0.14u | criteria not met (4/50 graded, CLV not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 526/day, projected 15767/30 days. All monitors on the key: 2041/day, projected 61229/30 days. Remaining 64622; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T01:00:23Z: 55 games (52 in 24h), quotes {'prophetx': 6464, 'novig': 664, 'kalshi': 3960, 'polymarket_us': 2644}, 3734 unmatched, 5791 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 39 B 0, maker posted 16 filled 0, credits used 8 left 64622, 302s
- 2026-10-31T00:50:17Z: 55 games (52 in 24h), quotes {'prophetx': 6288, 'novig': 660, 'kalshi': 2752, 'polymarket_us': 1886}, 3360 unmatched, 5554 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 0 B 0, maker posted 4 filled 0, credits used 4 left 64637, 212s
- 2026-10-31T00:40:29Z: 54 games (51 in 24h), quotes {'prophetx': 2340, 'novig': 634, 'kalshi': 2730, 'polymarket_us': 1818}, 3000 unmatched, 2516 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 22 B 0, maker posted 0 filled 0, credits used 8 left 64648, 302s
- 2026-10-31T00:30:37Z: 53 games (50 in 24h), quotes {'prophetx': 6294, 'novig': 662, 'kalshi': 2630, 'polymarket_us': 1832}, 3265 unmatched, 5234 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 8 filled 0, credits used 4 left 64663, 283s
- 2026-10-31T00:26:10Z: 52 games (49 in 24h), quotes {'prophetx': 4302, 'novig': 660, 'kalshi': 2880, 'polymarket_us': 2116}, 3521 unmatched, 3958 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 4 left 64667, 250s
- 2026-10-31T00:20:19Z: 52 games (49 in 24h), quotes {'prophetx': 6262, 'novig': 658, 'kalshi': 3678, 'polymarket_us': 3360}, 3808 unmatched, 5695 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 86 B 0, maker posted 0 filled 0, credits used 8 left 64678, 337s
- 2026-10-31T00:10:19Z: 54 games (51 in 24h), quotes {'prophetx': 6258, 'novig': 658, 'kalshi': 3472, 'polymarket_us': 3356}, 3743 unmatched, 6506 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 10 B 0, maker posted 0 filled 0, credits used 4 left 64693, 244s
- 2026-10-31T00:00:41Z: 53 games (50 in 24h), quotes {'prophetx': 6258, 'novig': 682, 'kalshi': 3028, 'polymarket_us': 2136}, 3216 unmatched, 5890 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 64708, 292s
- 2026-10-30T23:55:38Z: 53 games (48 in 24h), quotes {'prophetx': 6372, 'novig': 679, 'kalshi': 3518, 'polymarket_us': 3326}, 3446 unmatched, 6583 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 22 B 0, maker posted 16 filled 0, credits used 4 left 64719, 285s
- 2026-10-30T23:50:20Z: 53 games (48 in 24h), quotes {'prophetx': 6380, 'novig': 683, 'kalshi': 2284, 'polymarket_us': 1546}, 1943 unmatched, 5799 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 3, new A 8 B 0, maker posted 4 filled 0, credits used 8 left 64727, 301s
