# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T03:14:24Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6396 | 6319 | -1.71c | 23.8% | 2757 | -1.08c | 5903 | 3024-2879-0 | -245.91u | -4.2% |  |  | criteria not met (5903/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1356 | 1345 | -3.62c | 16.7% | 305 | -2.94c | 1257 | 651-606-0 | -85.67u | -6.8% |  |  | criteria not met (1257/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 108 | 44-64-0 | -14.77u | -13.7% |  |  | criteria not met (108/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 64 | 28-36-0 | -4.20u | -6.6% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 35 | 11-24-0 | -11.96u | -34.2% |  |  |  |
| M move-watch: gettable (sightings) | 297 | 280 | -0.68c | 32.5% | 277 | -0.67c | 260 | 135-122-3 | -2.29u | -0.9% | 0.12c | 26s | criteria not met (260/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 152 | 142 | -0.76c | 33.8% | 141 | -0.93c | 131 | 66-63-2 | -2.77u | -2.1% | -0.21c | 28s |  |
| M gettable, price moves | 145 | 138 | -0.59c | 31.2% | 136 | -0.4c | 129 | 69-59-1 | +0.48u | 0.4% | 0.46c | 24s |  |
| M control: not gettable | 1128 | 878 | -0.9c | 34.7% | 867 | -1.27c | 823 | 406-403-14 | -44.95u | -5.5% | 1.76c | 164s |  |
| M all moves | 1425 | 1158 | -0.84c | 34.2% | 1144 | -1.12c | 1083 | 541-525-17 | -47.24u | -4.4% | 1.41c | 106s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 939 | 930 | 2.26c | 23.3% | 194 | 1.92c | 918 | 405-513-0 | +262.31u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 63 | -0.24c | 25-38-0 | -10.88u | 43, -0.54c, -9.87u | negative |
| J2 B, NBA | 50 | 44 | -0.2c | 17-27-0 | -8.62u | 27, -0.55c, -4.29u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 39 | -0.36c | 18-21-0 | -1.55u | 29, -0.66c, -0.02u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 157 | 123 | -0.75c | 60-62-1 | -5.18u | 72, -0.83c, -5.06u | negative |
| D1 B, unders (descriptive) | 20 | 14 | 0.53c | 8-6-0 | +2.56u | 14, 0.5c, +2.56u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 13 | -0.87c | 3-10-0 | -6.51u | 11, -1.1c, -4.51u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 7 | 0.44c | 3-4-0 | +0.46u | 6, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 51 | -0.46c | 28-21-2 | -2.64u | 26, -0.67c, -2.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1560 | 72 | 4.6% | -0.62c | 1.6c | 31-33-0 | -1.29u |  |
| MK novig fair-2c | 1557 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3260 | 165 | 5.1% | -0.92c | 1.1c | 85-66-2 | +23.12u |  |
| MK prophetx fair-2c | 3237 | 49 | 1.5% | -0.56c | 2.04c | 23-24-0 | +0.97u |  |
| MK all fair-1c | 4820 | 237 | 4.9% | -0.83c | 1.26c | 116-99-2 | +21.84u | criteria not met (217/50 graded, CLV not positive) |
| MK all fair-2c | 4794 | 75 | 1.6% | -0.49c | 2.2c | 39-34-0 | +8.62u | criteria not met (73/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 627/day, projected 18810/30 days. All monitors on the key: 2137/day, projected 64122/30 days. Remaining 86847; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T03:11:04Z: 73 games (71 in 24h), quotes {'prophetx': 2006, 'novig': 663, 'kalshi': 2318, 'polymarket_us': 1858}, 3288 unmatched (70 book-games; fuzzy-matched 1), 2246 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 86847, 200s
- 2026-11-07T03:01:18Z: 73 games (69 in 24h), quotes {'prophetx': 7072, 'novig': 708, 'kalshi': 2708, 'polymarket_us': 2072}, 5214 unmatched (115 book-games; fuzzy-matched 2), 3656 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, maker posted 9 filled 0, credits used 8 left 86860, 301s
- 2026-11-07T02:51:12Z: 73 games (69 in 24h), quotes {'prophetx': 9388, 'novig': 708, 'kalshi': 2852, 'polymarket_us': 2054}, 5517 unmatched (126 book-games; fuzzy-matched 1), 5066 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 4 filled 0, credits used 10 left 86882, 301s
- 2026-11-07T02:40:48Z: 69 games (66 in 24h), quotes {'prophetx': 4790, 'novig': 704, 'kalshi': 3580, 'polymarket_us': 2484}, 4896 unmatched (112 book-games; fuzzy-matched 1), 3566 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 1 filled 0, credits used 8 left 86905, 326s
- 2026-11-07T02:31:06Z: 69 games (66 in 24h), quotes {'prophetx': 4206, 'novig': 694, 'kalshi': 2148, 'polymarket_us': 1876}, 4009 unmatched (90 book-games; fuzzy-matched 2), 2569 side/lines, polls [NHL:slow; NCAAF:fast,NBA:fast], moves 3, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 86936, 265s
- 2026-11-07T02:21:12Z: 69 games (63 in 24h), quotes {'prophetx': 1024, 'novig': 700, 'kalshi': 2268, 'polymarket_us': 1482}, 2641 unmatched (66 book-games; fuzzy-matched 1), 1844 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, maker posted 7 filled 0, credits used 8 left 86956, 302s
- 2026-11-07T02:11:12Z: 69 games (63 in 24h), quotes {'prophetx': 4108, 'novig': 708, 'kalshi': 2702, 'polymarket_us': 1992}, 4181 unmatched (97 book-games; fuzzy-matched 1), 2747 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 86979, 219s
- 2026-11-07T02:06:11Z: 69 games (60 in 24h), quotes {'prophetx': 3122, 'novig': 702, 'kalshi': 2946, 'polymarket_us': 2132}, 3955 unmatched (89 book-games; fuzzy-matched 1), 2734 side/lines, polls [NHL:slow; NCAAF:fast,NBA:fast], moves 0, new A 5 B 0, maker posted 11 filled 0, credits used 6 left 86992, 220s
- 2026-11-07T01:59:49Z: 70 games (61 in 24h), quotes {'prophetx': 6076, 'novig': 704, 'kalshi': 2652, 'polymarket_us': 1798}, 4487 unmatched (102 book-games; fuzzy-matched 2), 3175 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 6 B 0, maker posted 22 filled 1, credits used 8 left 87007, 302s
- 2026-11-07T01:51:14Z: 70 games (61 in 24h), quotes {'prophetx': 2616, 'novig': 704, 'kalshi': 3730, 'polymarket_us': 3174}, 3951 unmatched (95 book-games; fuzzy-matched 1), 3699 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 87028, 212s
