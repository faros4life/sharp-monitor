# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-06T02:43:42Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5875 | 5761 | -1.75c | 23.5% | 2493 | -1.08c | 5510 | 2805-2705-0 | -249.45u | -4.5% |  |  | criteria not met (5510/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1268 | 1238 | -3.72c | 16.2% | 276 | -2.92c | 1221 | 627-594-0 | -91.48u | -7.5% |  |  | criteria not met (1221/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 106 | 103 | -0.77c | 31.1% | 99 | 0.01c | 98 | 39-59-0 | -15.29u | -15.6% |  |  | criteria not met (98/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 61 | 60 | -0.73c | 30.0% | 58 | -0.09c | 57 | 24-33-0 | -5.62u | -9.9% |  |  |  |
| B ref age 5m+ | 36 | 34 | -1.08c | 32.4% | 32 | -0.1c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 260 | 255 | -0.69c | 32.2% | 253 | -0.69c | 237 | 122-112-3 | -4.17u | -1.8% | 0.08c | 26s | criteria not met (237/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 130 | 128 | -0.76c | 33.6% | 127 | -0.99c | 121 | 61-58-2 | -2.35u | -1.9% | -0.25c | 45s |  |
| M gettable, price moves | 130 | 127 | -0.63c | 30.7% | 126 | -0.39c | 116 | 61-54-1 | -1.82u | -1.6% | 0.42c | 22s |  |
| M control: not gettable | 962 | 771 | -0.88c | 34.0% | 767 | -1.26c | 744 | 378-352-14 | -18.58u | -2.5% | 1.76c | 107s |  |
| M all moves | 1222 | 1026 | -0.84c | 33.5% | 1020 | -1.12c | 981 | 500-464-17 | -22.75u | -2.3% | 1.4c | 48s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 927 | 916 | 2.32c | 23.1% | 190 | 1.97c | 913 | 403-510-0 | +262.23u | 28.7% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 61 | 54 | -0.11c | 20-34-0 | -12.40u | 37, -0.46c, -8.00u | negative |
| J2 B, NBA | 42 | 38 | 0.03c | 14-24-0 | -8.95u | 23, -0.42c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 36 | 32 | -0.34c | 14-18-0 | -2.97u | 25, -0.6c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 124 | 106 | -0.82c | 50-55-1 | -7.77u | 66, -0.92c, -4.82u | negative |
| D1 B, unders (descriptive) | 14 | 12 | 0.74c | 7-5-0 | +2.46u | 12, 0.74c, +2.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 12 | 10 | -1.04c | 1-9-0 | -7.81u | 8, -1.39c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 7 | 6 | 0.61c | 3-3-0 | +1.46u | 5, 0.64c, +0.31u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 50 | 45 | -0.45c | 25-18-2 | -1.93u | 21, -0.66c, -1.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1360 | 58 | 4.3% | -0.58c | 1.59c | 22-29-0 | -6.11u |  |
| MK novig fair-2c | 1360 | 22 | 1.6% | -0.46c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2961 | 148 | 5.0% | -0.86c | 1.1c | 71-61-2 | +13.30u |  |
| MK prophetx fair-2c | 2940 | 42 | 1.4% | -0.61c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 4321 | 206 | 4.8% | -0.78c | 1.25c | 93-90-2 | +7.20u | criteria not met (185/50 graded, CLV not positive) |
| MK all fair-2c | 4300 | 64 | 1.5% | -0.56c | 2.19c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 84.

## Odds API credits (100K/month plan)

Study: 628/day, projected 18843/30 days. All monitors on the key: 2131/day, projected 63917/30 days. Remaining 89093; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-06T02:40:42Z: 16 games (13 in 24h), quotes {'prophetx': 1068, 'novig': 714, 'kalshi': 1270, 'polymarket_us': 1504}, 399 unmatched (11 book-games; fuzzy-matched 0), 2127 side/lines, polls [none_due; NBA:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 2 left 89093, 181s
- 2026-11-06T02:34:19Z: 17 games (14 in 24h), quotes {'prophetx': 1068, 'novig': 724, 'kalshi': 1288, 'polymarket_us': 1504}, 402 unmatched (12 book-games; fuzzy-matched 0), 2145 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 89104, 231s
- 2026-11-06T02:30:08Z: 17 games (14 in 24h), quotes {'prophetx': 1068, 'novig': 716, 'kalshi': 1322, 'polymarket_us': 1504}, 434 unmatched (16 book-games; fuzzy-matched 0), 2143 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 6 left 89108, 205s
- 2026-11-06T02:20:55Z: 17 games (14 in 24h), quotes {'prophetx': 1074, 'novig': 714, 'kalshi': 1336, 'polymarket_us': 1532}, 448 unmatched (16 book-games; fuzzy-matched 0), 2157 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 11 filled 0, credits used 8 left 89125, 302s
- 2026-11-06T02:11:04Z: 17 games (14 in 24h), quotes {'prophetx': 1028, 'novig': 720, 'kalshi': 1372, 'polymarket_us': 1532}, 486 unmatched (16 book-games; fuzzy-matched 0), 2173 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 89151, 183s
- 2026-11-06T02:01:11Z: 18 games (15 in 24h), quotes {'prophetx': 1028, 'novig': 722, 'kalshi': 1390, 'polymarket_us': 1532}, 430 unmatched (15 book-games; fuzzy-matched 0), 2265 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 10 left 89164, 325s
- 2026-11-06T01:51:04Z: 18 games (14 in 24h), quotes {'prophetx': 896, 'novig': 724, 'kalshi': 1392, 'polymarket_us': 1528}, 432 unmatched (15 book-games; fuzzy-matched 0), 2211 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 7 B 0, maker posted 2 filled 1, credits used 8 left 89185, 301s
- 2026-11-06T01:40:42Z: 18 games (14 in 24h), quotes {'prophetx': 968, 'novig': 722, 'kalshi': 1398, 'polymarket_us': 1528}, 440 unmatched (15 book-games; fuzzy-matched 0), 2219 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 2, new A 9 B 0, maker posted 8 filled 1, credits used 4 left 89213, 204s
- 2026-11-06T01:31:05Z: 18 games (14 in 24h), quotes {'prophetx': 896, 'novig': 722, 'kalshi': 1426, 'polymarket_us': 1528}, 470 unmatched (15 book-games; fuzzy-matched 0), 2185 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 4 filled 0, credits used 10 left 89219, 301s
- 2026-11-06T01:20:54Z: 18 games (14 in 24h), quotes {'prophetx': 968, 'novig': 724, 'kalshi': 1412, 'polymarket_us': 1528}, 458 unmatched (15 book-games; fuzzy-matched 0), 2207 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 21 B 1, maker posted 8 filled 0, credits used 8 left 89250, 301s
