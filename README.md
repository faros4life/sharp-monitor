# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T18:45:29Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3824 | 3619 | -1.97c | 21.8% | 1453 | -1.15c | 3326 | 1663-1663-0 | -211.71u | -6.4% |  |  | criteria not met (3326/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 945 | 895 | -3.89c | 14.3% | 206 | -3.01c | 865 | 451-414-0 | -50.81u | -5.9% |  |  | criteria not met (865/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 59 | -0.68c | 32.2% | 57 | 0.08c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 38 | 38 | -0.65c | 28.9% | 37 | -0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 144 | 138 | -0.53c | 35.5% | 136 | -0.61c | 131 | 65-65-1 | -4.82u | -3.7% | 0.3c | 23s | criteria not met (131/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 78 | 75 | -0.5c | 38.7% | 74 | -0.77c | 70 | 33-36-1 | -5.75u | -8.2% | 0.06c | 28s |  |
| M gettable, price moves | 66 | 63 | -0.57c | 31.7% | 62 | -0.41c | 61 | 32-29-0 | +0.93u | 1.5% | 0.58c | 20s |  |
| M control: not gettable | 559 | 417 | -0.89c | 34.3% | 414 | -1.26c | 418 | 225-187-6 | +13.00u | 3.1% | 1.77c | 26s |  |
| M all moves | 703 | 555 | -0.8c | 34.6% | 550 | -1.1c | 549 | 290-252-7 | +8.18u | 1.5% | 1.46c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 614 | 575 | 4.24c | 29.0% | 110 | 3.07c | 568 | 255-313-0 | +255.27u | 44.9% | 1.17c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 20 | 0.09c | 9-11-0 | -1.24u | 16, -0.04c, -1.47u | not enough yet |
| J2 B, NBA | 9 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 15 | -0.24c | 7-8-0 | -0.40u | 12, -0.42c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 49 | 39 | -0.46c | 15-23-1 | -8.68u | 26, -0.56c, -7.44u | not enough yet |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 9 | 6 | -0.99c | 3-3-0 | -1.66u | 5, -1.02c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 466 | 26 | 5.9% | -0.45c | 1.64c | 13-11-0 | +2.35u |  |
| MK novig fair-2c | 467 | 11 | 2.5% | -0.51c | 2.56c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1772 | 89 | 5.1% | -0.95c | 1.1c | 38-44-2 | -4.54u |  |
| MK prophetx fair-2c | 1756 | 24 | 1.4% | -0.8c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2238 | 115 | 5.3% | -0.84c | 1.21c | 51-55-2 | -2.19u | criteria not met (108/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 2223 | 35 | 1.6% | -0.71c | 2.15c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 595/day, projected 17860/30 days. All monitors on the key: 2100/day, projected 63013/30 days. Remaining 98475; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T18:40:27Z: 17 games (12 in 24h), quotes {'prophetx': 912, 'novig': 724, 'kalshi': 1214, 'polymarket_us': 1462}, 454 unmatched (9 book-games; fuzzy-matched 0), 2091 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 4 filled 0, credits used 12 left 98475, 302s
- 2026-11-01T18:30:34Z: 17 games (12 in 24h), quotes {'prophetx': 912, 'novig': 724, 'kalshi': 1222, 'polymarket_us': 1462}, 464 unmatched (9 book-games; fuzzy-matched 0), 2069 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 2 filled 2, credits used 6 left 98505, 183s
- 2026-11-01T18:21:19Z: 17 games (12 in 24h), quotes {'prophetx': 920, 'novig': 720, 'kalshi': 1224, 'polymarket_us': 1462}, 466 unmatched (9 book-games; fuzzy-matched 0), 2090 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 98520, 276s
- 2026-11-01T18:16:24Z: 17 games (12 in 24h), quotes {'prophetx': 920, 'novig': 722, 'kalshi': 1254, 'polymarket_us': 1462}, 496 unmatched (9 book-games; fuzzy-matched 0), 2085 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 4 filled 0, credits used 6 left 98535, 270s
- 2026-11-01T18:11:45Z: 17 games (12 in 24h), quotes {'prophetx': 920, 'novig': 728, 'kalshi': 1238, 'polymarket_us': 1462}, 478 unmatched (9 book-games; fuzzy-matched 0), 2086 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 98550, 249s
- 2026-11-01T18:07:52Z: 18 games (13 in 24h), quotes {'prophetx': 920, 'novig': 722, 'kalshi': 1254, 'polymarket_us': 1462}, 482 unmatched (8 book-games; fuzzy-matched 1), 2101 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 7 B 0, maker posted 4 filled 0, credits used 6 left 98556, 206s
- 2026-11-01T18:00:34Z: 26 games (21 in 24h), quotes {'prophetx': 920, 'novig': 718, 'kalshi': 1258, 'polymarket_us': 1462}, 0 unmatched (0 book-games; fuzzy-matched 0), 2561 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 34 B 0, maker posted 44 filled 0, credits used 12 left 98571, 302s
- 2026-11-01T17:50:33Z: 26 games (21 in 24h), quotes {'prophetx': 1736, 'novig': 714, 'kalshi': 1262, 'polymarket_us': 1910}, 0 unmatched (0 book-games; fuzzy-matched 0), 3258 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 3 filled 0, credits used 6 left 98607, 183s
- 2026-11-01T17:45:17Z: 26 games (21 in 24h), quotes {'prophetx': 1736, 'novig': 714, 'kalshi': 1260, 'polymarket_us': 1940}, 0 unmatched (0 book-games; fuzzy-matched 0), 3132 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 16 filled 0, credits used 6 left 98617, 198s
- 2026-11-01T17:40:31Z: 26 games (21 in 24h), quotes {'prophetx': 1728, 'novig': 722, 'kalshi': 1262, 'polymarket_us': 2158}, 0 unmatched (0 book-games; fuzzy-matched 0), 3305 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 3, new A 3 B 0, maker posted 16 filled 1, credits used 6 left 98632, 256s
