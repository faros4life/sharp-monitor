# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T02:06:15Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3446 | 3265 | -2.11c | 21.3% | 1296 | -1.21c | 2785 | 1404-1381-0 | -171.06u | -6.1% |  |  | criteria not met (2785/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 886 | 855 | -4.03c | 14.2% | 203 | -3.0c | 783 | 402-381-0 | -52.44u | -6.7% |  |  | criteria not met (783/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 57 | -0.67c | 33.3% | 55 | 0.12c | 44 | 19-25-0 | -2.79u | -6.4% |  |  | criteria not met (44/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 3 | 2-1-0 | +1.23u | 41.1% |  |  |  |
| B ref age 1-5m | 38 | 36 | -0.62c | 30.6% | 35 | 0.05c | 29 | 13-16-0 | -0.40u | -1.4% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 12 | 4-8-0 | -3.63u | -30.3% |  |  |  |
| M move-watch: gettable (sightings) | 132 | 130 | -0.57c | 33.8% | 128 | -0.64c | 105 | 53-51-1 | -1.44u | -1.4% | 0.25c | 23s | criteria not met (105/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 71 | 70 | -0.54c | 37.1% | 69 | -0.77c | 59 | 30-28-1 | -0.53u | -0.9% | 0.03c | 26s |  |
| M gettable, price moves | 61 | 60 | -0.62c | 30.0% | 59 | -0.48c | 46 | 23-23-0 | -0.91u | -2.0% | 0.51c | 20s |  |
| M control: not gettable | 510 | 388 | -0.91c | 33.5% | 385 | -1.29c | 324 | 177-142-5 | +15.45u | 4.8% | 1.76c | 25s |  |
| M all moves | 642 | 518 | -0.83c | 33.6% | 513 | -1.12c | 429 | 230-193-6 | +14.01u | 3.3% | 1.44c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 576 | 557 | 3.65c | 27.8% | 109 | 2.75c | 495 | 225-270-0 | +216.27u | 43.7% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 6 | 0.21c | 2-4-0 | -1.78u | 5, 0.09c, -0.78u | not enough yet |
| J2 B, NBA | 9 | 3 | -0.19c | 1-2-0 | -0.90u | 2, -0.42c, +0.10u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 5 | -0.12c | 2-3-0 | -0.78u | 4, -0.3c, +0.22u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 40 | 20 | -0.54c | 7-12-1 | -5.49u | 15, -0.65c, -6.37u | not enough yet |
| D1 B, unders (descriptive) | 5 | 1 | 0.76c | 1-0-0 | +1.13u | 1, 0.76c, +1.13u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 0 | -0.8c | 0-0-0 | +0.00u | 0, -0.8c, +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 3 | -0.99c | 1-2-0 | -1.60u | 3, -1.02c, -1.60u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 336 | 24 | 7.3% | -0.5c | 1.68c | 10-8-0 | +2.14u |  |
| MK novig fair-2c | 337 | 11 | 3.3% | -0.45c | 2.6c | 4-3-0 | +1.42u |  |
| MK prophetx fair-1c | 1580 | 84 | 5.4% | -0.92c | 1.1c | 26-36-2 | -8.72u |  |
| MK prophetx fair-2c | 1566 | 24 | 1.5% | -0.83c | 2.04c | 5-11-0 | -5.57u |  |
| MK all fair-1c | 1916 | 108 | 5.7% | -0.82c | 1.2c | 36-44-2 | -6.58u | criteria not met (82/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1903 | 35 | 1.9% | -0.71c | 2.14c | 9-14-0 | -4.15u | criteria not met (23/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 612/day, projected 18349/30 days. All monitors on the key: 2160/day, projected 64787/30 days. Remaining 99682; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T02:00:25Z: 24 games (23 in 24h), quotes {'prophetx': 1706, 'novig': 688, 'kalshi': 1768, 'polymarket_us': 2044}, 594 unmatched (18 book-games; fuzzy-matched 0), 3062 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 3, new A 18 B 0, maker posted 2 filled 3, credits used 8 left 99682, 350s
- 2026-11-01T01:50:19Z: 24 games (23 in 24h), quotes {'prophetx': 1836, 'novig': 663, 'kalshi': 1728, 'polymarket_us': 1842}, 673 unmatched (20 book-games; fuzzy-matched 0), 3002 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 1 filled 1, credits used 4 left 99710, 186s
- 2026-11-01T01:43:49Z: 22 games (22 in 24h), quotes {'prophetx': 1836, 'novig': 671, 'kalshi': 1784, 'polymarket_us': 3290}, 868 unmatched (22 book-games; fuzzy-matched 0), 3621 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 4 filled 0, credits used 8 left 99727, 302s
- 2026-11-01T01:40:18Z: 21 games (21 in 24h), quotes {'prophetx': 1836, 'novig': 664, 'kalshi': 1802, 'polymarket_us': 2042}, 772 unmatched (23 book-games; fuzzy-matched 0), 3051 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 1, credits used 4 left 99743, 186s
- 2026-11-01T01:34:43Z: 21 games (21 in 24h), quotes {'prophetx': 1836, 'novig': 668, 'kalshi': 1848, 'polymarket_us': 2636}, 941 unmatched (25 book-games; fuzzy-matched 0), 3252 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 8 filled 1, credits used 4 left 99756, 222s
- 2026-11-01T01:30:21Z: 21 games (21 in 24h), quotes {'prophetx': 1836, 'novig': 654, 'kalshi': 1884, 'polymarket_us': 2048}, 840 unmatched (25 book-games; fuzzy-matched 0), 3068 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 2, new A 7 B 0, maker posted 7 filled 1, credits used 4 left 99771, 239s
- 2026-11-01T01:20:24Z: 21 games (21 in 24h), quotes {'prophetx': 1834, 'novig': 667, 'kalshi': 1928, 'polymarket_us': 3242}, 1135 unmatched (27 book-games; fuzzy-matched 0), 3472 side/lines, polls [NFL:slow,NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 2, new A 10 B 0, maker posted 1 filled 1, credits used 10 left 99786, 301s
- 2026-11-01T01:10:19Z: 21 games (20 in 24h), quotes {'prophetx': 1646, 'novig': 662, 'kalshi': 1974, 'polymarket_us': 2058}, 918 unmatched (23 book-games; fuzzy-matched 0), 2993 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 27 filled 0, credits used 4 left 99811, 182s
- 2026-11-01T01:00:23Z: 21 games (20 in 24h), quotes {'prophetx': 1646, 'novig': 666, 'kalshi': 2036, 'polymarket_us': 1958}, 980 unmatched (23 book-games; fuzzy-matched 0), 2925 side/lines, polls [NFL:slow,NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 2, new A 22 B 1, maker posted 3 filled 0, credits used 10 left 99824, 302s
- 2026-11-01T00:50:24Z: 21 games (19 in 24h), quotes {'prophetx': 1620, 'novig': 664, 'kalshi': 2088, 'polymarket_us': 2140}, 1032 unmatched (23 book-games; fuzzy-matched 0), 3013 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 1 filled 0, credits used 8 left 99849, 301s
