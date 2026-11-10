# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T02:43:32Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8433 | 8266 | -1.6c | 24.2% | 3622 | -1.04c | 7859 | 4053-3806-0 | -279.14u | -3.6% |  |  | criteria not met (7859/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1885 | 1825 | -3.1c | 18.7% | 401 | -2.68c | 1740 | 895-845-0 | -133.38u | -7.7% |  |  | criteria not met (1740/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 143 | 143 | -0.84c | 28.7% | 133 | 0.06c | 132 | 58-74-0 | -9.06u | -6.9% |  |  | criteria not met (132/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 81 | 81 | -1.01c | 27.2% | 77 | -0.1c | 78 | 36-42-0 | -1.33u | -1.7% |  |  |  |
| B ref age 5m+ | 49 | 49 | -0.77c | 30.6% | 43 | 0.01c | 45 | 17-28-0 | -9.12u | -20.3% |  |  |  |
| M move-watch: gettable (sightings) | 387 | 379 | -0.65c | 35.1% | 377 | -0.55c | 366 | 190-171-5 | -0.88u | -0.2% | 0.17c | 25s | criteria not met (366/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 203 | 200 | -0.81c | 34.0% | 199 | -0.81c | 191 | 96-91-4 | -3.71u | -1.9% | -0.19c | 26s |  |
| M gettable, price moves | 184 | 179 | -0.48c | 36.3% | 178 | -0.26c | 175 | 94-80-1 | +2.83u | 1.6% | 0.57c | 23s |  |
| M control: not gettable | 1595 | 1268 | -0.76c | 36.4% | 1242 | -1.2c | 1240 | 615-604-21 | -60.01u | -4.8% | 1.9c | 184s |  |
| M all moves | 1982 | 1647 | -0.74c | 36.1% | 1619 | -1.04c | 1606 | 805-775-26 | -60.88u | -3.8% | 1.56c | 163s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1061 | 1056 | 2.61c | 27.0% | 224 | 2.85c | 1039 | 461-578-0 | +281.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 92 | 83 | -0.04c | 37-46-0 | -5.42u | 57, -0.22c, -11.02u | negative |
| J2 B, NBA | 63 | 54 | 0.05c | 24-30-0 | -3.95u | 33, -0.18c, -4.02u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 54 | 49 | -0.23c | 24-25-0 | +1.07u | 39, -0.5c, +2.60u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 226 | 214 | -0.64c | 107-104-3 | -3.87u | 125, -0.62c, -10.14u | negative |
| D1 B, unders (descriptive) | 29 | 25 | 0.49c | 15-10-0 | +6.16u | 23, 0.47c, +3.95u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 17 | -0.69c | 5-12-0 | -6.30u | 15, -0.85c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 13 | 11 | 0.6c | 5-6-0 | +0.71u | 10, 0.61c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 75 | 66 | -0.14c | 36-28-2 | -2.54u | 38, -0.18c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2138 | 89 | 4.2% | -0.62c | 1.58c | 42-40-0 | +3.52u |  |
| MK novig fair-2c | 2135 | 31 | 1.5% | -0.33c | 2.51c | 19-11-0 | +9.90u |  |
| MK prophetx fair-1c | 5068 | 242 | 4.8% | -1.03c | 1.1c | 111-115-5 | +1.02u |  |
| MK prophetx fair-2c | 5032 | 81 | 1.6% | -0.6c | 2.04c | 37-39-0 | +1.11u |  |
| MK all fair-1c | 7206 | 331 | 4.6% | -0.92c | 1.24c | 153-155-5 | +4.54u | criteria not met (313/50 graded, CLV not positive) |
| MK all fair-2c | 7167 | 112 | 1.6% | -0.53c | 2.18c | 56-50-0 | +11.01u | criteria not met (106/50 graded, CLV not positive) |

A and B on the same side/line: 115.

## Odds API credits (100K/month plan)

Study: 650/day, projected 19506/30 days. All monitors on the key: 2398/day, projected 71931/30 days. Remaining 77023; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T02:40:04Z: 17 games (14 in 24h), quotes {'prophetx': 980, 'novig': 683, 'kalshi': 1092, 'polymarket_us': 1230}, 408 unmatched (9 book-games; fuzzy-matched 0), 1857 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 2, new A 2 B 0, maker posted 4 filled 0, credits used 4 left 77023, 209s
- 2026-11-10T02:31:56Z: 18 games (15 in 24h), quotes {'prophetx': 980, 'novig': 697, 'kalshi': 1126, 'polymarket_us': 1230}, 426 unmatched (8 book-games; fuzzy-matched 0), 1871 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 10 filled 0, credits used 8 left 77036, 301s
- 2026-11-10T02:21:49Z: 18 games (15 in 24h), quotes {'prophetx': 1014, 'novig': 693, 'kalshi': 1158, 'polymarket_us': 1258}, 458 unmatched (9 book-games; fuzzy-matched 0), 1899 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 42 B 1, maker posted 4 filled 0, credits used 10 left 77058, 314s
- 2026-11-10T02:11:11Z: 19 games (16 in 24h), quotes {'prophetx': 840, 'novig': 693, 'kalshi': 1234, 'polymarket_us': 1256}, 458 unmatched (9 book-games; fuzzy-matched 0), 1940 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 3, new A 8 B 0, maker posted 0 filled 0, credits used 8 left 77086, 301s
- 2026-11-10T02:01:37Z: 19 games (15 in 24h), quotes {'prophetx': 706, 'novig': 693, 'kalshi': 1268, 'polymarket_us': 1256}, 496 unmatched (9 book-games; fuzzy-matched 0), 1890 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 11 B 0, maker posted 0 filled 0, credits used 6 left 77112, 183s
- 2026-11-10T01:51:59Z: 19 games (15 in 24h), quotes {'prophetx': 920, 'novig': 691, 'kalshi': 1296, 'polymarket_us': 1136}, 396 unmatched (8 book-games; fuzzy-matched 0), 2002 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 8 filled 0, credits used 8 left 77131, 309s
- 2026-11-10T01:41:21Z: 19 games (15 in 24h), quotes {'prophetx': 754, 'novig': 689, 'kalshi': 1314, 'polymarket_us': 1136}, 416 unmatched (8 book-games; fuzzy-matched 0), 1918 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 4 filled 0, credits used 4 left 77152, 182s
- 2026-11-10T01:32:02Z: 20 games (16 in 24h), quotes {'prophetx': 916, 'novig': 720, 'kalshi': 1318, 'polymarket_us': 1136}, 360 unmatched (7 book-games; fuzzy-matched 0), 2096 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 16 B 0, maker posted 12 filled 0, credits used 10 left 77165, 307s
- 2026-11-10T01:21:15Z: 20 games (16 in 24h), quotes {'prophetx': 1008, 'novig': 708, 'kalshi': 1312, 'polymarket_us': 1266}, 378 unmatched (7 book-games; fuzzy-matched 0), 2166 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 1, new A 13 B 0, maker posted 22 filled 0, credits used 4 left 77206, 211s
- 2026-11-10T01:11:59Z: 21 games (17 in 24h), quotes {'prophetx': 1090, 'novig': 724, 'kalshi': 1320, 'polymarket_us': 1406}, 326 unmatched (6 book-games; fuzzy-matched 0), 2333 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 11 B 0, maker posted 8 filled 0, credits used 10 left 77210, 301s
