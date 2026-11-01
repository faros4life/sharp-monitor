# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T16:53:23Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3725 | 3326 | -2.08c | 21.5% | 1323 | -1.19c | 3326 | 1663-1663-0 | -211.71u | -6.4% |  |  | criteria not met (3326/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 939 | 865 | -3.99c | 14.2% | 204 | -2.98c | 865 | 451-414-0 | -50.81u | -5.9% |  |  | criteria not met (865/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 59 | -0.68c | 32.2% | 57 | 0.08c | 59 | 26-33-0 | -3.25u | -5.5% |  |  | criteria not met (59/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 38 | 38 | -0.65c | 28.9% | 37 | -0.01c | 38 | 17-21-0 | -1.08u | -2.9% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 140 | 131 | -0.58c | 33.6% | 129 | -0.64c | 131 | 65-65-1 | -4.82u | -3.7% | 0.25c | 22s | criteria not met (131/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 74 | 70 | -0.54c | 37.1% | 69 | -0.77c | 70 | 33-36-1 | -5.75u | -8.2% | 0.03c | 26s |  |
| M gettable, price moves | 66 | 61 | -0.63c | 29.5% | 60 | -0.49c | 61 | 32-29-0 | +0.93u | 1.5% | 0.5c | 20s |  |
| M control: not gettable | 547 | 406 | -0.91c | 33.5% | 403 | -1.29c | 418 | 225-187-6 | +13.00u | 3.1% | 1.76c | 26s |  |
| M all moves | 687 | 537 | -0.83c | 33.5% | 532 | -1.13c | 549 | 290-252-7 | +8.18u | 1.5% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 608 | 567 | 4.12c | 28.9% | 110 | 3.07c | 568 | 255-313-0 | +255.27u | 44.9% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 20 | 0.09c | 9-11-0 | -1.24u | 16, -0.04c, -1.47u | not enough yet |
| J2 B, NBA | 9 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 15 | -0.24c | 7-8-0 | -0.40u | 12, -0.42c, +0.51u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 45 | 39 | -0.55c | 15-23-1 | -8.68u | 26, -0.66c, -7.44u | not enough yet |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 9 | 6 | -0.99c | 3-3-0 | -1.66u | 5, -1.02c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 420 | 24 | 6.2% | -0.5c | 1.69c | 13-11-0 | +2.35u |  |
| MK novig fair-2c | 421 | 11 | 2.8% | -0.51c | 2.59c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1707 | 85 | 5.1% | -0.97c | 1.11c | 38-44-2 | -4.54u |  |
| MK prophetx fair-2c | 1692 | 24 | 1.5% | -0.8c | 2.04c | 9-15-0 | -5.31u |  |
| MK all fair-1c | 2127 | 109 | 5.3% | -0.87c | 1.21c | 51-55-2 | -2.19u | criteria not met (108/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 2113 | 35 | 1.7% | -0.71c | 2.14c | 16-19-0 | -1.55u | criteria not met (35/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 581/day, projected 17439/30 days. All monitors on the key: 2072/day, projected 62174/30 days. Remaining 98772; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T16:50:21Z: 22 games (21 in 24h), quotes {'prophetx': 1724, 'novig': 716, 'kalshi': 1218, 'polymarket_us': 2080}, 34 unmatched (4 book-games; fuzzy-matched 0), 3093 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 98772, 182s
- 2026-11-01T16:43:46Z: 22 games (21 in 24h), quotes {'prophetx': 1690, 'novig': 720, 'kalshi': 1222, 'polymarket_us': 1876}, 36 unmatched (4 book-games; fuzzy-matched 0), 2966 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 16 filled 0, credits used 6 left 98778, 250s
- 2026-11-01T16:39:54Z: 22 games (21 in 24h), quotes {'prophetx': 1724, 'novig': 722, 'kalshi': 1222, 'polymarket_us': 2116}, 36 unmatched (4 book-games; fuzzy-matched 0), 3125 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 21 filled 1, credits used 6 left 98799, 204s
- 2026-11-01T16:30:29Z: 22 games (21 in 24h), quotes {'prophetx': 1724, 'novig': 720, 'kalshi': 1220, 'polymarket_us': 2084}, 34 unmatched (4 book-games; fuzzy-matched 0), 3190 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 4, new A 10 B 0, maker posted 4 filled 0, credits used 12 left 98814, 303s
- 2026-11-01T16:20:30Z: 22 games (21 in 24h), quotes {'prophetx': 1724, 'novig': 722, 'kalshi': 1220, 'polymarket_us': 1548}, 34 unmatched (4 book-games; fuzzy-matched 0), 2943 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 98845, 184s
- 2026-11-01T16:12:28Z: 22 games (21 in 24h), quotes {'prophetx': 1724, 'novig': 716, 'kalshi': 1216, 'polymarket_us': 1650}, 32 unmatched (4 book-games; fuzzy-matched 0), 2989 side/lines, polls [none_due; NFL:fast; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 37 filled 0, credits used 6 left 98851, 210s
- 2026-11-01T16:07:02Z: 22 games (21 in 24h), quotes {'prophetx': 1716, 'novig': 722, 'kalshi': 1212, 'polymarket_us': 2612}, 30 unmatched (4 book-games; fuzzy-matched 0), 3448 side/lines, polls [none_due; NFL:fast; NBA:fast,NHL:fast], moves 4, new A 6 B 0, maker posted 71 filled 0, credits used 6 left 98868, 294s
- 2026-11-01T16:00:35Z: 22 games (21 in 24h), quotes {'prophetx': 1716, 'novig': 714, 'kalshi': 1212, 'polymarket_us': 2344}, 30 unmatched (4 book-games; fuzzy-matched 0), 3388 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast; NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 12 left 98883, 308s
- 2026-11-01T15:50:30Z: 22 games (21 in 24h), quotes {'prophetx': 1716, 'novig': 716, 'kalshi': 1218, 'polymarket_us': 2084}, 36 unmatched (4 book-games; fuzzy-matched 0), 3188 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 4 filled 0, credits used 12 left 98910, 310s
- 2026-11-01T15:41:44Z: 22 games (21 in 24h), quotes {'prophetx': 1716, 'novig': 712, 'kalshi': 1214, 'polymarket_us': 1976}, 32 unmatched (4 book-games; fuzzy-matched 0), 3146 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 12 filled 0, credits used 6 left 98933, 228s
