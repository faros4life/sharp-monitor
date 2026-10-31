# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T18:25:51Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2561 | 2244 | -2.44c | 23.6% | 870 | -1.31c | 1881 | 941-940-0 | -117.27u | -6.2% |  |  | criteria not met (1881/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 697 | 560 | -4.99c | 15.9% | 121 | -3.64c | 397 | 194-203-0 | -31.33u | -7.9% |  |  | criteria not met (397/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 43 | 38 | -0.71c | 36.8% | 36 | 0.04c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 29 | 25 | -0.46c | 32.0% | 24 | 0.23c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 107 | 81 | -0.72c | 35.8% | 80 | -0.78c | 71 | 41-30-0 | +8.93u | 12.6% | 0.14c | 25s | criteria not met (71/50 graded, CLV not positive) |
| M gettable, line moves | 57 | 44 | -0.73c | 38.6% | 43 | -0.97c | 40 | 23-17-0 | +4.09u | 10.2% | 0.01c | 28s |  |
| M gettable, price moves | 50 | 37 | -0.71c | 32.4% | 37 | -0.56c | 31 | 18-13-0 | +4.84u | 15.6% | 0.29c | 20s |  |
| M control: not gettable | 412 | 231 | -0.65c | 34.6% | 232 | -1.12c | 189 | 97-89-3 | -3.24u | -1.7% | 1.88c | 28s |  |
| M all moves | 519 | 312 | -0.67c | 34.9% | 312 | -1.03c | 260 | 138-119-3 | +5.69u | 2.2% | 1.5c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 397 | 288 | 1.47c | 23.3% | 60 | 2.22c | 146 | 69-77-0 | +97.83u | 67.0% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 4 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J2 B, NBA | 2 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 4 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 16 | 0 | -0.5c | 0-0-0 | +0.00u | 0, -0.5c, +0.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 0 | 0.36c | 0-0-0 | +0.00u | 0, 0.36c, +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 0 | -1.47c | 0-0-0 | +0.00u | 0, -1.47c, +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 201 | 16 | 8.0% | -0.45c | 1.7c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 198 | 6 | 3.0% | -0.95c | 2.61c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1069 | 53 | 5.8% | -1.35c | 1.14c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 1061 | 16 | 1.8% | -1.52c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 1270 | 69 | 6.2% | -1.09c | 1.28c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 1259 | 22 | 2.0% | -1.3c | 2.2c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 33.

## Odds API credits (100K/month plan)

Study: 535/day, projected 16044/30 days. All monitors on the key: 1999/day, projected 59964/30 days. Remaining 63314; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T18:20:23Z: 63 games (55 in 24h), quotes {'prophetx': 6264, 'novig': 661, 'kalshi': 2312, 'polymarket_us': 1560}, 3568 unmatched (110 book-games; fuzzy-matched 3), 5381 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 27 filled 1, credits used 14 left 63314, 328s
- 2026-10-31T18:10:21Z: 63 games (55 in 24h), quotes {'prophetx': 6264, 'novig': 662, 'kalshi': 3674, 'polymarket_us': 3379}, 4052 unmatched (121 book-games; fuzzy-matched 4), 6076 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 71 B 0, maker posted 36 filled 2, credits used 6 left 63343, 277s
- 2026-10-31T18:04:42Z: 65 games (57 in 24h), quotes {'prophetx': 5612, 'novig': 652, 'kalshi': 2416, 'polymarket_us': 2020}, 3746 unmatched (110 book-games; fuzzy-matched 2), 4464 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 22 B 1, maker posted 43 filled 0, credits used 6 left 63364, 296s
- 2026-10-31T18:00:22Z: 67 games (59 in 24h), quotes {'prophetx': 6252, 'novig': 657, 'kalshi': 2844, 'polymarket_us': 2106}, 3724 unmatched (109 book-games; fuzzy-matched 3), 6005 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 13 B 0, maker posted 76 filled 0, credits used 6 left 63382, 236s
- 2026-10-31T17:50:54Z: 67 games (50 in 24h), quotes {'prophetx': 5944, 'novig': 552, 'kalshi': 2886, 'polymarket_us': 2248}, 4371 unmatched (123 book-games; fuzzy-matched 17), 5196 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 1, maker posted 4 filled 0, credits used 8 left 63405, 308s
- 2026-10-31T17:47:21Z: 67 games (50 in 24h), quotes {'prophetx': 5232, 'novig': 549, 'kalshi': 2762, 'polymarket_us': 1926}, 4184 unmatched (120 book-games; fuzzy-matched 2), 4524 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 25 filled 2, credits used 6 left 63422, 187s
- 2026-10-31T17:41:42Z: 67 games (50 in 24h), quotes {'prophetx': 5942, 'novig': 548, 'kalshi': 2886, 'polymarket_us': 2246}, 4382 unmatched (123 book-games; fuzzy-matched 68), 5174 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 4 B 0, maker posted 13 filled 2, credits used 6 left 63441, 316s
- 2026-10-31T17:35:50Z: 67 games (50 in 24h), quotes {'prophetx': 5942, 'novig': 551, 'kalshi': 3042, 'polymarket_us': 2292}, 4472 unmatched (124 book-games; fuzzy-matched 2), 5216 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 2 B 0, maker posted 17 filled 1, credits used 6 left 63456, 330s
- 2026-10-31T17:30:26Z: 67 games (50 in 24h), quotes {'prophetx': 5944, 'novig': 641, 'kalshi': 3044, 'polymarket_us': 2298}, 4569 unmatched (124 book-games; fuzzy-matched 4), 5199 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 1, maker posted 69 filled 3, credits used 14 left 63473, 302s
- 2026-10-31T17:20:20Z: 67 games (50 in 24h), quotes {'prophetx': 5944, 'novig': 551, 'kalshi': 2748, 'polymarket_us': 1964}, 4357 unmatched (122 book-games; fuzzy-matched 2), 5371 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 14 filled 0, credits used 6 left 63501, 321s
