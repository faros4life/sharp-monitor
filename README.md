# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T01:07:22Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8308 | 8063 | -1.61c | 23.8% | 3532 | -1.03c | 7859 | 4053-3806-0 | -279.14u | -3.6% |  |  | criteria not met (7859/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1848 | 1789 | -3.12c | 18.3% | 391 | -2.62c | 1740 | 895-845-0 | -133.38u | -7.7% |  |  | criteria not met (1740/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 142 | 139 | -0.96c | 27.3% | 129 | -0.06c | 132 | 58-74-0 | -9.06u | -6.9% |  |  | criteria not met (132/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 12 | 12 | 0.01c | 33.3% | 12 | 1.13c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 81 | 79 | -1.12c | 25.3% | 75 | -0.2c | 78 | 36-42-0 | -1.33u | -1.7% |  |  |  |
| B ref age 5m+ | 49 | 48 | -0.95c | 29.2% | 42 | -0.16c | 45 | 17-28-0 | -9.12u | -20.3% |  |  |  |
| M move-watch: gettable (sightings) | 383 | 369 | -0.61c | 35.2% | 368 | -0.56c | 366 | 190-171-5 | -0.88u | -0.2% | 0.2c | 26s | criteria not met (366/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 202 | 195 | -0.73c | 34.4% | 195 | -0.81c | 191 | 96-91-4 | -3.71u | -1.9% | -0.13c | 26s |  |
| M gettable, price moves | 181 | 174 | -0.48c | 36.2% | 173 | -0.27c | 175 | 94-80-1 | +2.83u | 1.6% | 0.57c | 23s |  |
| M control: not gettable | 1588 | 1238 | -0.8c | 35.9% | 1220 | -1.21c | 1240 | 615-604-21 | -60.01u | -4.8% | 1.85c | 184s |  |
| M all moves | 1971 | 1607 | -0.76c | 35.7% | 1588 | -1.05c | 1606 | 805-775-26 | -60.88u | -3.8% | 1.53c | 163s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1058 | 1054 | 2.62c | 27.0% | 224 | 2.85c | 1039 | 461-578-0 | +281.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 92 | 83 | -0.19c | 37-46-0 | -5.42u | 57, -0.46c, -11.02u | negative |
| J2 B, NBA | 63 | 54 | -0.18c | 24-30-0 | -3.95u | 33, -0.6c, -4.02u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 54 | 49 | -0.35c | 24-25-0 | +1.07u | 39, -0.65c, +2.60u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 225 | 214 | -0.62c | 107-104-3 | -3.87u | 125, -0.59c, -10.14u | negative |
| D1 B, unders (descriptive) | 29 | 25 | 0.18c | 15-10-0 | +6.16u | 23, 0.14c, +3.95u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 17 | -0.69c | 5-12-0 | -6.30u | 15, -0.85c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 12 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 72 | 66 | -0.21c | 36-28-2 | -2.54u | 38, -0.28c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2120 | 89 | 4.2% | -0.62c | 1.58c | 42-40-0 | +3.52u |  |
| MK novig fair-2c | 2117 | 31 | 1.5% | -0.33c | 2.51c | 19-11-0 | +9.90u |  |
| MK prophetx fair-1c | 5050 | 242 | 4.8% | -1.03c | 1.1c | 111-115-5 | +1.02u |  |
| MK prophetx fair-2c | 5014 | 81 | 1.6% | -0.6c | 2.04c | 37-39-0 | +1.11u |  |
| MK all fair-1c | 7170 | 331 | 4.6% | -0.92c | 1.24c | 153-155-5 | +4.54u | criteria not met (313/50 graded, CLV not positive) |
| MK all fair-2c | 7131 | 112 | 1.6% | -0.53c | 2.18c | 56-50-0 | +11.01u | criteria not met (106/50 graded, CLV not positive) |

A and B on the same side/line: 114.

## Odds API credits (100K/month plan)

Study: 648/day, projected 19444/30 days. All monitors on the key: 2393/day, projected 71798/30 days. Remaining 77245; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T01:01:55Z: 23 games (17 in 24h), quotes {'prophetx': 910, 'novig': 716, 'kalshi': 1270, 'polymarket_us': 1406}, 246 unmatched (4 book-games; fuzzy-matched 0), 2300 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 27 B 0, maker posted 0 filled 0, credits used 14 left 77245, 326s
- 2026-11-10T00:51:52Z: 23 games (16 in 24h), quotes {'prophetx': 1026, 'novig': 724, 'kalshi': 1234, 'polymarket_us': 1280}, 254 unmatched (4 book-games; fuzzy-matched 0), 2279 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 8 filled 0, credits used 12 left 77278, 301s
- 2026-11-10T00:41:49Z: 24 games (17 in 24h), quotes {'prophetx': 930, 'novig': 678, 'kalshi': 1260, 'polymarket_us': 1278}, 204 unmatched (3 book-games; fuzzy-matched 0), 2308 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 4, new A 8 B 0, maker posted 2 filled 0, credits used 14 left 77312, 301s
- 2026-11-10T00:31:28Z: 23 games (15 in 24h), quotes {'prophetx': 864, 'novig': 722, 'kalshi': 1276, 'polymarket_us': 1278}, 210 unmatched (3 book-games; fuzzy-matched 0), 2300 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 11 filled 1, credits used 6 left 77401, 183s
- 2026-11-10T00:21:32Z: 23 games (15 in 24h), quotes {'prophetx': 990, 'novig': 718, 'kalshi': 1280, 'polymarket_us': 1254}, 220 unmatched (3 book-games; fuzzy-matched 0), 2298 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 11 B 0, maker posted 20 filled 0, credits used 14 left 77433, 310s
- 2026-11-10T00:11:21Z: 23 games (15 in 24h), quotes {'prophetx': 990, 'novig': 714, 'kalshi': 1288, 'polymarket_us': 1252}, 226 unmatched (3 book-games; fuzzy-matched 0), 2260 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 10 B 0, maker posted 34 filled 0, credits used 6 left 77467, 192s
- 2026-11-10T00:02:12Z: 25 games (14 in 24h), quotes {'prophetx': 1062, 'novig': 724, 'kalshi': 1282, 'polymarket_us': 1252}, 0 unmatched (0 book-games; fuzzy-matched 0), 2588 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 5, new A 9 B 0, maker posted 0 filled 0, credits used 12 left 77488, 325s
- 2026-11-09T23:52:05Z: 25 games (12 in 24h), quotes {'prophetx': 1048, 'novig': 728, 'kalshi': 1290, 'polymarket_us': 1258}, 0 unmatched (0 book-games; fuzzy-matched 0), 2591 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 0, maker posted 18 filled 2, credits used 14 left 77523, 301s
- 2026-11-09T23:41:21Z: 25 games (12 in 24h), quotes {'prophetx': 1048, 'novig': 728, 'kalshi': 1242, 'polymarket_us': 1258}, 0 unmatched (0 book-games; fuzzy-matched 0), 2560 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 6, new A 2 B 1, maker posted 17 filled 3, credits used 12 left 77555, 301s
- 2026-11-09T23:31:22Z: 25 games (12 in 24h), quotes {'prophetx': 1060, 'novig': 728, 'kalshi': 1212, 'polymarket_us': 1258}, 0 unmatched (0 book-games; fuzzy-matched 0), 2531 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 77586, 184s
