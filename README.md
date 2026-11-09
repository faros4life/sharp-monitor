# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-09T22:56:39Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8213 | 7858 | -1.61c | 23.7% | 3453 | -1.03c | 7859 | 4053-3806-0 | -279.14u | -3.6% |  |  | criteria not met (7859/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1822 | 1740 | -3.1c | 18.3% | 384 | -2.64c | 1740 | 895-845-0 | -133.38u | -7.7% |  |  | criteria not met (1740/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 140 | 132 | -1.07c | 26.5% | 123 | -0.09c | 132 | 58-74-0 | -9.06u | -6.9% |  |  | criteria not met (132/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 11 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 80 | 78 | -1.13c | 25.6% | 74 | -0.19c | 78 | 36-42-0 | -1.33u | -1.7% |  |  |  |
| B ref age 5m+ | 49 | 45 | -1.21c | 26.7% | 40 | -0.15c | 45 | 17-28-0 | -9.12u | -20.3% |  |  |  |
| M move-watch: gettable (sightings) | 377 | 362 | -0.59c | 35.1% | 362 | -0.56c | 366 | 190-171-5 | -0.88u | -0.2% | 0.23c | 26s | criteria not met (366/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 199 | 189 | -0.69c | 34.4% | 190 | -0.82c | 191 | 96-91-4 | -3.71u | -1.9% | -0.08c | 27s |  |
| M gettable, price moves | 178 | 173 | -0.49c | 35.8% | 172 | -0.28c | 175 | 94-80-1 | +2.83u | 1.6% | 0.56c | 23s |  |
| M control: not gettable | 1561 | 1208 | -0.77c | 36.3% | 1190 | -1.18c | 1240 | 615-604-21 | -60.01u | -4.8% | 1.84c | 184s |  |
| M all moves | 1938 | 1570 | -0.73c | 36.0% | 1552 | -1.04c | 1606 | 805-775-26 | -60.88u | -3.8% | 1.52c | 163s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1057 | 1038 | 2.7c | 27.3% | 222 | 2.91c | 1039 | 461-578-0 | +281.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 90 | 83 | -0.24c | 37-46-0 | -5.42u | 57, -0.46c, -11.02u | negative |
| J2 B, NBA | 61 | 54 | -0.26c | 24-30-0 | -3.95u | 33, -0.63c, -4.02u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 52 | 49 | -0.46c | 24-25-0 | +1.07u | 39, -0.73c, +2.60u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 222 | 214 | -0.64c | 107-104-3 | -3.87u | 125, -0.65c, -10.14u | negative |
| D1 B, unders (descriptive) | 28 | 25 | 0.11c | 15-10-0 | +6.16u | 23, 0.06c, +3.95u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 12 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 69 | 66 | -0.21c | 36-28-2 | -2.54u | 38, -0.28c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2080 | 86 | 4.2% | -0.62c | 1.58c | 42-40-0 | +3.52u |  |
| MK novig fair-2c | 2077 | 30 | 1.5% | -0.35c | 2.51c | 19-11-0 | +9.90u |  |
| MK prophetx fair-1c | 4987 | 237 | 4.8% | -1.02c | 1.1c | 111-115-5 | +1.02u |  |
| MK prophetx fair-2c | 4954 | 80 | 1.6% | -0.59c | 2.04c | 37-39-0 | +1.11u |  |
| MK all fair-1c | 7067 | 323 | 4.6% | -0.92c | 1.24c | 153-155-5 | +4.54u | criteria not met (313/50 graded, CLV not positive) |
| MK all fair-2c | 7031 | 110 | 1.6% | -0.52c | 2.18c | 56-50-0 | +11.01u | criteria not met (106/50 graded, CLV not positive) |

A and B on the same side/line: 112.

## Odds API credits (100K/month plan)

Study: 642/day, projected 19253/30 days. All monitors on the key: 2372/day, projected 71148/30 days. Remaining 77745; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-09T22:52:03Z: 24 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 724, 'kalshi': 1212, 'polymarket_us': 1256}, 0 unmatched (0 book-games; fuzzy-matched 0), 2536 side/lines, polls [NCAAF:slow; NFL:fast,NBA:fast,NHL:fast], moves 6, new A 3 B 0, maker posted 1 filled 2, credits used 8 left 77745, 276s
- 2026-11-09T22:42:04Z: 24 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 722, 'kalshi': 1176, 'polymarket_us': 1254}, 0 unmatched (0 book-games; fuzzy-matched 0), 2508 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 1, maker posted 26 filled 2, credits used 12 left 77757, 302s
- 2026-11-09T22:31:51Z: 24 games (12 in 24h), quotes {'prophetx': 1036, 'novig': 726, 'kalshi': 1188, 'polymarket_us': 1254}, 0 unmatched (0 book-games; fuzzy-matched 0), 2507 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 2 B 2, maker posted 1 filled 3, credits used 14 left 77791, 329s
- 2026-11-09T22:21:12Z: 24 games (12 in 24h), quotes {'prophetx': 1036, 'novig': 722, 'kalshi': 1124, 'polymarket_us': 1252}, 0 unmatched (0 book-games; fuzzy-matched 0), 2447 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 16 filled 0, credits used 6 left 77815, 182s
- 2026-11-09T22:11:32Z: 23 games (12 in 24h), quotes {'prophetx': 1044, 'novig': 726, 'kalshi': 1130, 'polymarket_us': 1252}, 0 unmatched (0 book-games; fuzzy-matched 0), 2453 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 4 filled 0, credits used 12 left 77839, 302s
- 2026-11-09T22:01:56Z: 23 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 730, 'kalshi': 1130, 'polymarket_us': 1252}, 0 unmatched (0 book-games; fuzzy-matched 0), 2449 side/lines, polls [NCAAF:slow; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 22 filled 0, credits used 8 left 77868, 184s
- 2026-11-09T21:52:10Z: 23 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 726, 'kalshi': 1128, 'polymarket_us': 1252}, 0 unmatched (0 book-games; fuzzy-matched 0), 2453 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 2 B 0, maker posted 32 filled 4, credits used 12 left 77885, 301s
- 2026-11-09T21:41:39Z: 23 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 724, 'kalshi': 1132, 'polymarket_us': 1250}, 0 unmatched (0 book-games; fuzzy-matched 0), 2459 side/lines, polls [NFL:fast,NCAAF:slow,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 5 filled 0, credits used 14 left 77906, 301s
- 2026-11-09T21:31:45Z: 23 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 724, 'kalshi': 1136, 'polymarket_us': 1250}, 0 unmatched (0 book-games; fuzzy-matched 0), 2459 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 17 filled 0, credits used 6 left 77933, 184s
- 2026-11-09T21:22:02Z: 23 games (12 in 24h), quotes {'prophetx': 1052, 'novig': 724, 'kalshi': 1128, 'polymarket_us': 1250}, 0 unmatched (0 book-games; fuzzy-matched 0), 2453 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 12 left 77948, 301s
