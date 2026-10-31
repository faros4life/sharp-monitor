# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T03:09:19Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2182 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1699 | 843-856-0 | -129.75u | -7.6% |  |  | criteria not met (1699/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 397 | -5.93c | 18.6% | 79 | -3.91c | 372 | 181-191-0 | -34.70u | -9.3% |  |  | criteria not met (372/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 35 | 15-20-0 | -3.43u | -9.8% |  |  | criteria not met (35/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 23 | 11-12-0 | +0.17u | 0.8% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 10 | 3-7-0 | -3.71u | -37.1% |  |  |  |
| M move-watch: gettable (sightings) | 78 | 71 | -0.71c | 35.2% | 70 | -0.69c | 64 | 38-26-0 | +10.24u | 16.0% | 0.22c | 28s | criteria not met (64/50 graded, CLV not positive) |
| M gettable, line moves | 44 | 40 | -0.66c | 37.5% | 39 | -0.89c | 34 | 20-14-0 | +4.40u | 12.9% | 0.09c | 54s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 30 | 18-12-0 | +5.84u | 19.5% | 0.39c | 28s |  |
| M control: not gettable | 279 | 184 | -0.64c | 33.2% | 180 | -1.17c | 156 | 85-69-2 | +6.18u | 4.0% | 1.82c | 29s |  |
| M all moves | 357 | 255 | -0.66c | 33.7% | 250 | -1.03c | 220 | 123-95-2 | +16.42u | 7.5% | 1.45c | 29s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 273 | 145 | -0.09c | 22.1% | 18 | -0.21c | 137 | 66-71-0 | +97.20u | 70.9% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 7.9% | -0.47c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 176 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 417 | 19 | 4.6% | -0.91c | 1.09c | 9-8-0 | +1.45u |  |
| MK prophetx fair-2c | 412 | 5 | 1.2% | -1.98c | 2.06c | 1-3-0 | -1.95u |  |
| MK all fair-1c | 594 | 33 | 5.6% | -0.73c | 1.26c | 17-14-0 | +3.69u | criteria not met (31/50 graded, CLV not positive) |
| MK all fair-2c | 588 | 11 | 1.9% | -1.42c | 2.23c | 5-5-0 | +0.48u | criteria not met (10/50 graded, CLV not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 529/day, projected 15858/30 days. All monitors on the key: 2037/day, projected 61118/30 days. Remaining 64456; guard holds 8200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T03:06:07Z: 53 games (53 in 24h), quotes {'prophetx': 7030, 'novig': 640, 'kalshi': 3576, 'polymarket_us': 3586}, 4278 unmatched, 6885 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 64456, 192s
- 2026-10-31T03:00:31Z: 53 games (53 in 24h), quotes {'prophetx': 7030, 'novig': 637, 'kalshi': 2630, 'polymarket_us': 1782}, 3654 unmatched, 5871 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 64456, 186s
- 2026-10-31T02:53:51Z: 53 games (52 in 24h), quotes {'prophetx': 1590, 'novig': 635, 'kalshi': 2698, 'polymarket_us': 2190}, 3395 unmatched, 2423 side/lines, polls [NCAAF:slow,NBA:slow], moves 2, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 64470, 193s
- 2026-10-31T02:50:19Z: 53 games (52 in 24h), quotes {'prophetx': 6928, 'novig': 633, 'kalshi': 2368, 'polymarket_us': 2082}, 3491 unmatched, 5825 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 64474, 191s
- 2026-10-31T02:40:20Z: 53 games (52 in 24h), quotes {'prophetx': 6922, 'novig': 642, 'kalshi': 2344, 'polymarket_us': 1534}, 3507 unmatched, 5523 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 64481, 193s
- 2026-10-31T02:30:30Z: 54 games (53 in 24h), quotes {'prophetx': 6922, 'novig': 638, 'kalshi': 2588, 'polymarket_us': 1782}, 3603 unmatched, 5730 side/lines, polls [NBA:slow; NCAAF:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 64488, 190s
- 2026-10-31T02:23:48Z: 54 games (52 in 24h), quotes {'prophetx': 6894, 'novig': 646, 'kalshi': 2928, 'polymarket_us': 2178}, 3608 unmatched, 5966 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 64501, 285s
- 2026-10-31T02:20:18Z: 54 games (52 in 24h), quotes {'prophetx': 6894, 'novig': 654, 'kalshi': 3664, 'polymarket_us': 3540}, 4016 unmatched, 6771 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 2 left 64503, 194s
- 2026-10-31T02:14:12Z: 54 games (52 in 24h), quotes {'prophetx': 5474, 'novig': 642, 'kalshi': 3628, 'polymarket_us': 3482}, 3972 unmatched, 5821 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 7 B 0, maker posted 8 filled 0, credits used 2 left 64512, 253s
- 2026-10-31T02:10:16Z: 55 games (53 in 24h), quotes {'prophetx': 6814, 'novig': 644, 'kalshi': 2744, 'polymarket_us': 2214}, 3562 unmatched, 5907 side/lines, polls [none_due; NCAAF:fast], moves 1, new A 0 B 0, maker posted 4 filled 0, credits used 2 left 64514, 216s
