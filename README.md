# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T04:04:42Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6398 | 6356 | -1.71c | 23.9% | 2775 | -1.07c | 6019 | 3080-2939-0 | -259.11u | -4.3% |  |  | criteria not met (6019/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1358 | 1351 | -3.61c | 16.7% | 306 | -2.92c | 1268 | 655-613-0 | -90.72u | -7.2% |  |  | criteria not met (1268/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 110 | 46-64-0 | -12.62u | -11.5% |  |  | criteria not met (110/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 65 | 29-36-0 | -3.11u | -4.8% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 36 | 12-24-0 | -10.90u | -30.3% |  |  |  |
| M move-watch: gettable (sightings) | 297 | 281 | -0.68c | 32.4% | 278 | -0.67c | 265 | 136-126-3 | -5.33u | -2.0% | 0.12c | 26s | criteria not met (265/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 152 | 143 | -0.76c | 33.6% | 142 | -0.92c | 134 | 66-66-2 | -5.77u | -4.3% | -0.21c | 28s |  |
| M gettable, price moves | 145 | 138 | -0.59c | 31.2% | 136 | -0.4c | 131 | 70-60-1 | +0.44u | 0.3% | 0.46c | 24s |  |
| M control: not gettable | 1133 | 886 | -0.89c | 34.9% | 876 | -1.27c | 833 | 408-411-14 | -51.30u | -6.2% | 1.76c | 166s |  |
| M all moves | 1430 | 1167 | -0.84c | 34.3% | 1154 | -1.12c | 1098 | 544-537-17 | -56.62u | -5.2% | 1.42c | 107s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 939 | 932 | 2.26c | 23.3% | 194 | 1.92c | 921 | 405-516-0 | +259.31u | 28.2% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 65 | -0.24c | 27-38-0 | -8.74u | 44, -0.54c, -8.81u | negative |
| J2 B, NBA | 50 | 46 | -0.2c | 19-27-0 | -6.47u | 28, -0.55c, -3.23u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 40 | -0.36c | 19-21-0 | -0.47u | 30, -0.66c, +1.07u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 157 | 128 | -0.75c | 61-66-1 | -8.22u | 74, -0.82c, -7.06u | negative |
| D1 B, unders (descriptive) | 20 | 15 | 0.53c | 9-6-0 | +3.62u | 15, 0.5c, +3.62u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 14 | -0.87c | 4-10-0 | -5.43u | 12, -1.1c, -3.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 7 | 0.44c | 3-4-0 | +0.46u | 6, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 51 | -0.46c | 28-21-2 | -2.64u | 26, -0.67c, -2.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1560 | 72 | 4.6% | -0.62c | 1.6c | 31-33-0 | -1.29u |  |
| MK novig fair-2c | 1557 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3260 | 165 | 5.1% | -0.95c | 1.11c | 85-66-2 | +23.12u |  |
| MK prophetx fair-2c | 3237 | 49 | 1.5% | -0.56c | 2.04c | 23-24-0 | +0.97u |  |
| MK all fair-1c | 4820 | 237 | 4.9% | -0.85c | 1.27c | 116-99-2 | +21.84u | criteria not met (217/50 graded, CLV not positive) |
| MK all fair-2c | 4794 | 75 | 1.6% | -0.49c | 2.19c | 39-34-0 | +8.62u | criteria not met (73/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 626/day, projected 18787/30 days. All monitors on the key: 2137/day, projected 64100/30 days. Remaining 86780; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T04:01:20Z: 70 games (70 in 24h), quotes {'prophetx': 4550, 'novig': 666, 'kalshi': 2456, 'polymarket_us': 1888}, 4900 unmatched (100 book-games; fuzzy-matched 1), 2302 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86780, 202s
- 2026-11-07T03:51:10Z: 70 games (70 in 24h), quotes {'prophetx': 8328, 'novig': 661, 'kalshi': 2824, 'polymarket_us': 2072}, 5774 unmatched (123 book-games; fuzzy-matched 2), 4371 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 86793, 185s
- 2026-11-07T03:41:03Z: 70 games (70 in 24h), quotes {'prophetx': 5880, 'novig': 663, 'kalshi': 2336, 'polymarket_us': 1924}, 5219 unmatched (108 book-games; fuzzy-matched 1), 2542 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 86810, 183s
- 2026-11-07T03:30:50Z: 70 games (70 in 24h), quotes {'prophetx': 6056, 'novig': 667, 'kalshi': 2678, 'polymarket_us': 2068}, 5521 unmatched (119 book-games; fuzzy-matched 0), 2728 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86821, 191s
- 2026-11-07T03:21:11Z: 72 games (70 in 24h), quotes {'prophetx': 0, 'novig': 662, 'kalshi': 3750, 'polymarket_us': 3486}, 4277 unmatched (88 book-games; fuzzy-matched 0), 2882 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NBA:fast], moves 3, new A 0 B 0, maker posted 0 filled 0, credits used 8 left 86830, 301s
- 2026-11-07T03:11:04Z: 73 games (71 in 24h), quotes {'prophetx': 2006, 'novig': 663, 'kalshi': 2318, 'polymarket_us': 1858}, 3288 unmatched (70 book-games; fuzzy-matched 1), 2246 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 86847, 200s
- 2026-11-07T03:01:18Z: 73 games (69 in 24h), quotes {'prophetx': 7072, 'novig': 708, 'kalshi': 2708, 'polymarket_us': 2072}, 5214 unmatched (115 book-games; fuzzy-matched 2), 3656 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, maker posted 9 filled 0, credits used 8 left 86860, 301s
- 2026-11-07T02:51:12Z: 73 games (69 in 24h), quotes {'prophetx': 9388, 'novig': 708, 'kalshi': 2852, 'polymarket_us': 2054}, 5517 unmatched (126 book-games; fuzzy-matched 1), 5066 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 10 left 86882, 301s
- 2026-11-07T02:40:48Z: 69 games (66 in 24h), quotes {'prophetx': 4790, 'novig': 704, 'kalshi': 3580, 'polymarket_us': 2484}, 4896 unmatched (112 book-games; fuzzy-matched 1), 3566 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 1 filled 0, credits used 8 left 86905, 326s
- 2026-11-07T02:31:06Z: 69 games (66 in 24h), quotes {'prophetx': 4206, 'novig': 694, 'kalshi': 2148, 'polymarket_us': 1876}, 4009 unmatched (90 book-games; fuzzy-matched 2), 2569 side/lines, polls [NHL:slow; NCAAF:fast,NBA:fast], moves 3, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 86936, 265s
