# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-06T04:04:10Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5939 | 5803 | -1.75c | 23.6% | 2512 | -1.08c | 5569 | 2840-2729-0 | -252.71u | -4.5% |  |  | criteria not met (5569/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1296 | 1242 | -3.71c | 16.3% | 277 | -2.91c | 1224 | 630-594-0 | -90.55u | -7.4% |  |  | criteria not met (1224/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 106 | 104 | -0.83c | 30.8% | 99 | 0.01c | 99 | 39-60-0 | -16.29u | -16.5% |  |  | criteria not met (99/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 61 | 60 | -0.73c | 30.0% | 58 | -0.09c | 57 | 24-33-0 | -5.62u | -9.9% |  |  |  |
| B ref age 5m+ | 36 | 35 | -1.23c | 31.4% | 32 | -0.1c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 261 | 256 | -0.69c | 32.0% | 254 | -0.69c | 242 | 125-114-3 | -3.88u | -1.6% | 0.09c | 26s | criteria not met (242/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 131 | 129 | -0.75c | 33.3% | 128 | -0.98c | 121 | 61-58-2 | -2.35u | -1.9% | -0.24c | 46s |  |
| M gettable, price moves | 130 | 127 | -0.63c | 30.7% | 126 | -0.39c | 121 | 64-56-1 | -1.53u | -1.3% | 0.42c | 22s |  |
| M control: not gettable | 963 | 778 | -0.9c | 34.1% | 772 | -1.27c | 766 | 385-367-14 | -27.34u | -3.6% | 1.76c | 107s |  |
| M all moves | 1224 | 1034 | -0.85c | 33.6% | 1026 | -1.12c | 1008 | 510-481-17 | -31.22u | -3.1% | 1.41c | 56s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 932 | 916 | 2.32c | 23.1% | 190 | 1.97c | 914 | 404-510-0 | +264.89u | 29.0% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 61 | 54 | -0.11c | 20-34-0 | -12.40u | 37, -0.46c, -8.00u | negative |
| J2 B, NBA | 42 | 38 | 0.03c | 14-24-0 | -8.95u | 23, -0.42c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 36 | 32 | -0.34c | 14-18-0 | -2.97u | 25, -0.6c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 125 | 106 | -0.8c | 50-55-1 | -7.77u | 66, -0.9c, -4.82u | negative |
| D1 B, unders (descriptive) | 14 | 12 | 0.74c | 7-5-0 | +2.46u | 12, 0.74c, +2.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 12 | 10 | -1.04c | 1-9-0 | -7.81u | 8, -1.39c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 7 | 7 | 0.61c | 3-4-0 | +0.46u | 6, 0.64c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 50 | 50 | -0.45c | 28-20-2 | -1.64u | 25, -0.66c, -1.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1362 | 59 | 4.3% | -0.61c | 1.59c | 23-29-0 | -5.66u |  |
| MK novig fair-2c | 1362 | 22 | 1.6% | -0.46c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2963 | 148 | 5.0% | -0.86c | 1.1c | 72-63-2 | +12.30u |  |
| MK prophetx fair-2c | 2942 | 42 | 1.4% | -0.61c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 4325 | 207 | 4.8% | -0.79c | 1.26c | 95-92-2 | +6.64u | criteria not met (189/50 graded, CLV not positive) |
| MK all fair-2c | 4304 | 64 | 1.5% | -0.56c | 2.19c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 85.

## Odds API credits (100K/month plan)

Study: 627/day, projected 18813/30 days. All monitors on the key: 2131/day, projected 63923/30 days. Remaining 88972; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-06T04:01:08Z: 16 games (16 in 24h), quotes {'prophetx': 1424, 'novig': 714, 'kalshi': 1164, 'polymarket_us': 1766}, 178 unmatched (7 book-games; fuzzy-matched 0), 2425 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 1, new A 8 B 0, maker posted 0 filled 0, credits used 6 left 88972, 181s
- 2026-11-06T03:50:51Z: 16 games (16 in 24h), quotes {'prophetx': 1392, 'novig': 720, 'kalshi': 1198, 'polymarket_us': 1766}, 214 unmatched (7 book-games; fuzzy-matched 0), 2411 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 88996, 183s
- 2026-11-06T03:41:03Z: 16 games (16 in 24h), quotes {'prophetx': 1296, 'novig': 722, 'kalshi': 1174, 'polymarket_us': 1466}, 230 unmatched (8 book-games; fuzzy-matched 0), 2165 side/lines, polls [NCAAF:slow], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 2 left 89007, 184s
- 2026-11-06T03:31:03Z: 15 games (15 in 24h), quotes {'prophetx': 1296, 'novig': 722, 'kalshi': 1194, 'polymarket_us': 1764}, 402 unmatched (9 book-games; fuzzy-matched 0), 2217 side/lines, polls [NBA:slow,NHL:slow], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 4 left 89020, 183s
- 2026-11-06T03:20:41Z: 15 games (15 in 24h), quotes {'prophetx': 1296, 'novig': 722, 'kalshi': 1206, 'polymarket_us': 1764}, 414 unmatched (9 book-games; fuzzy-matched 0), 2217 side/lines, polls [NCAAF:slow], moves 0, new A 15 B 0, maker posted 0 filled 0, credits used 2 left 89033, 183s
- 2026-11-06T03:11:00Z: 16 games (15 in 24h), quotes {'prophetx': 1030, 'novig': 718, 'kalshi': 1210, 'polymarket_us': 1632}, 348 unmatched (8 book-games; fuzzy-matched 0), 2157 side/lines, polls [NBA:fast; none_due], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 2 left 89044, 301s
- 2026-11-06T03:00:49Z: 16 games (13 in 24h), quotes {'prophetx': 1066, 'novig': 718, 'kalshi': 1224, 'polymarket_us': 1632}, 360 unmatched (8 book-games; fuzzy-matched 0), 2163 side/lines, polls [NHL:slow; NBA:fast], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 4 left 89055, 182s
- 2026-11-06T02:51:02Z: 16 games (13 in 24h), quotes {'prophetx': 1068, 'novig': 716, 'kalshi': 1250, 'polymarket_us': 1504}, 378 unmatched (8 book-games; fuzzy-matched 0), 2102 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 5 B 0, maker posted 8 filled 1, credits used 6 left 89069, 301s
- 2026-11-06T02:40:42Z: 16 games (13 in 24h), quotes {'prophetx': 1068, 'novig': 714, 'kalshi': 1270, 'polymarket_us': 1504}, 399 unmatched (11 book-games; fuzzy-matched 0), 2127 side/lines, polls [none_due; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 2 left 89093, 181s
- 2026-11-06T02:34:19Z: 17 games (14 in 24h), quotes {'prophetx': 1068, 'novig': 724, 'kalshi': 1288, 'polymarket_us': 1504}, 402 unmatched (12 book-games; fuzzy-matched 0), 2145 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 89104, 231s
