# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T04:24:08Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6406 | 6356 | -1.71c | 23.9% | 2775 | -1.07c | 6194 | 3175-3019-0 | -270.99u | -4.4% |  |  | criteria not met (6194/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1359 | 1351 | -3.61c | 16.7% | 306 | -2.92c | 1327 | 681-646-0 | -111.07u | -8.4% |  |  | criteria not met (1327/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 116 | 49-67-0 | -12.43u | -10.7% |  |  | criteria not met (116/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 68 | 31-37-0 | -1.97u | -2.9% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 39 | 13-26-0 | -11.85u | -30.4% |  |  |  |
| M move-watch: gettable (sightings) | 297 | 281 | -0.68c | 32.4% | 278 | -0.67c | 273 | 140-129-4 | -4.92u | -1.8% | 0.12c | 26s | criteria not met (273/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 152 | 143 | -0.76c | 33.6% | 142 | -0.92c | 138 | 68-67-3 | -4.86u | -3.5% | -0.21c | 28s |  |
| M gettable, price moves | 145 | 138 | -0.59c | 31.2% | 136 | -0.4c | 135 | 72-62-1 | -0.05u | -0.0% | 0.46c | 24s |  |
| M control: not gettable | 1138 | 886 | -0.89c | 34.9% | 876 | -1.27c | 877 | 426-436-15 | -60.93u | -6.9% | 1.76c | 173s |  |
| M all moves | 1435 | 1167 | -0.84c | 34.3% | 1154 | -1.12c | 1150 | 566-565-19 | -65.84u | -5.7% | 1.42c | 108s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 944 | 932 | 2.26c | 23.3% | 194 | 1.92c | 930 | 409-521-0 | +265.84u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 69 | -0.24c | 29-40-0 | -8.54u | 46, -0.54c, -10.81u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 41 | -0.36c | 20-21-0 | +0.67u | 31, -0.66c, +2.21u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 157 | 135 | -0.75c | 64-69-2 | -8.33u | 78, -0.82c, -9.10u | negative |
| D1 B, unders (descriptive) | 20 | 18 | 0.53c | 10-8-0 | +2.62u | 18, 0.5c, +2.62u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 52 | -0.46c | 29-21-2 | -2.11u | 27, -0.67c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1560 | 72 | 4.6% | -0.62c | 1.6c | 33-35-0 | -1.20u |  |
| MK novig fair-2c | 1557 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3260 | 165 | 5.1% | -0.95c | 1.11c | 86-69-2 | +21.17u |  |
| MK prophetx fair-2c | 3237 | 49 | 1.5% | -0.56c | 2.04c | 23-24-0 | +0.97u |  |
| MK all fair-1c | 4820 | 237 | 4.9% | -0.85c | 1.27c | 119-104-2 | +19.97u | criteria not met (225/50 graded, CLV not positive) |
| MK all fair-2c | 4794 | 75 | 1.6% | -0.49c | 2.19c | 39-34-0 | +8.62u | criteria not met (73/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 626/day, projected 18779/30 days. All monitors on the key: 2136/day, projected 64085/30 days. Remaining 86756; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T04:21:03Z: 70 games (70 in 24h), quotes {'prophetx': 9778, 'novig': 669, 'kalshi': 3604, 'polymarket_us': 3530}, 6957 unmatched (140 book-games; fuzzy-matched 2), 5577 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 5, new A 13 B 0, maker posted 0 filled 0, credits used 6 left 86756, 185s
- 2026-11-07T04:10:49Z: 70 games (70 in 24h), quotes {'prophetx': 6376, 'novig': 665, 'kalshi': 2788, 'polymarket_us': 2072}, 5572 unmatched (118 book-games; fuzzy-matched 0), 2907 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86771, 182s
- 2026-11-07T04:01:20Z: 70 games (70 in 24h), quotes {'prophetx': 4550, 'novig': 666, 'kalshi': 2456, 'polymarket_us': 1888}, 4900 unmatched (100 book-games; fuzzy-matched 1), 2302 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86780, 202s
- 2026-11-07T03:51:10Z: 70 games (70 in 24h), quotes {'prophetx': 8328, 'novig': 661, 'kalshi': 2824, 'polymarket_us': 2072}, 5774 unmatched (123 book-games; fuzzy-matched 2), 4371 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 86793, 185s
- 2026-11-07T03:41:03Z: 70 games (70 in 24h), quotes {'prophetx': 5880, 'novig': 663, 'kalshi': 2336, 'polymarket_us': 1924}, 5219 unmatched (108 book-games; fuzzy-matched 1), 2542 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 86810, 183s
- 2026-11-07T03:30:50Z: 70 games (70 in 24h), quotes {'prophetx': 6056, 'novig': 667, 'kalshi': 2678, 'polymarket_us': 2068}, 5521 unmatched (119 book-games; fuzzy-matched 0), 2728 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86821, 191s
- 2026-11-07T03:21:11Z: 72 games (70 in 24h), quotes {'prophetx': 0, 'novig': 662, 'kalshi': 3750, 'polymarket_us': 3486}, 4277 unmatched (88 book-games; fuzzy-matched 0), 2882 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NBA:fast], moves 3, new A 0 B 0, maker posted 0 filled 0, credits used 8 left 86830, 301s
- 2026-11-07T03:11:04Z: 73 games (71 in 24h), quotes {'prophetx': 2006, 'novig': 663, 'kalshi': 2318, 'polymarket_us': 1858}, 3288 unmatched (70 book-games; fuzzy-matched 1), 2246 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 86847, 200s
- 2026-11-07T03:01:18Z: 73 games (69 in 24h), quotes {'prophetx': 7072, 'novig': 708, 'kalshi': 2708, 'polymarket_us': 2072}, 5214 unmatched (115 book-games; fuzzy-matched 2), 3656 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, maker posted 9 filled 0, credits used 8 left 86860, 301s
- 2026-11-07T02:51:12Z: 73 games (69 in 24h), quotes {'prophetx': 9388, 'novig': 708, 'kalshi': 2852, 'polymarket_us': 2054}, 5517 unmatched (126 book-games; fuzzy-matched 1), 5066 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 10 left 86882, 301s
