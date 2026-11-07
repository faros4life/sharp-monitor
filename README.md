# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T05:51:02Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6407 | 6356 | -1.71c | 23.9% | 2775 | -1.07c | 6252 | 3211-3041-0 | -253.65u | -4.1% |  |  | criteria not met (6252/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1359 | 1351 | -3.61c | 16.7% | 306 | -2.92c | 1330 | 684-646-0 | -107.13u | -8.1% |  |  | criteria not met (1330/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 297 | 281 | -0.68c | 32.4% | 278 | -0.67c | 280 | 145-131-4 | -2.07u | -0.7% | 0.12c | 26s | criteria not met (280/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 152 | 143 | -0.76c | 33.6% | 142 | -0.92c | 142 | 70-69-3 | -5.00u | -3.5% | -0.21c | 28s |  |
| M gettable, price moves | 145 | 138 | -0.59c | 31.2% | 136 | -0.4c | 138 | 75-62-1 | +2.93u | 2.1% | 0.46c | 24s |  |
| M control: not gettable | 1141 | 886 | -0.89c | 34.9% | 876 | -1.27c | 884 | 426-443-15 | -67.93u | -7.7% | 1.76c | 174s |  |
| M all moves | 1438 | 1167 | -0.84c | 34.3% | 1154 | -1.12c | 1164 | 571-574-19 | -70.00u | -6.0% | 1.42c | 108s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 944 | 932 | 2.26c | 23.3% | 194 | 1.92c | 930 | 409-521-0 | +265.84u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 71 | -0.24c | 31-40-0 | -6.38u | 47, -0.54c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 42 | -0.36c | 21-21-0 | +1.76u | 32, -0.66c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 157 | 142 | -0.75c | 69-71-2 | -5.49u | 80, -0.82c, -7.22u | negative |
| D1 B, unders (descriptive) | 20 | 20 | 0.53c | 12-8-0 | +4.79u | 19, 0.5c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 52 | -0.46c | 29-21-2 | -2.11u | 27, -0.67c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1560 | 72 | 4.6% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1557 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3260 | 165 | 5.1% | -0.95c | 1.11c | 89-69-2 | +24.41u |  |
| MK prophetx fair-2c | 3237 | 49 | 1.5% | -0.56c | 2.04c | 25-24-0 | +3.17u |  |
| MK all fair-1c | 4820 | 237 | 4.9% | -0.85c | 1.27c | 126-104-2 | +27.50u | criteria not met (232/50 graded, CLV not positive) |
| MK all fair-2c | 4794 | 75 | 1.6% | -0.49c | 2.19c | 41-34-0 | +10.82u | criteria not met (75/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 623/day, projected 18684/30 days. All monitors on the key: 2128/day, projected 63833/30 days. Remaining 86710; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T05:51:02Z: outside read hours: closes/grades only
- 2026-11-07T05:41:07Z: outside read hours: closes/grades only
- 2026-11-07T05:31:17Z: outside read hours: closes/grades only
- 2026-11-07T05:21:02Z: outside read hours: closes/grades only
- 2026-11-07T05:10:49Z: outside read hours: closes/grades only
- 2026-11-07T05:01:31Z: outside read hours: closes/grades only
- 2026-11-07T04:51:01Z: 70 games (70 in 24h), quotes {'prophetx': 3184, 'novig': 672, 'kalshi': 3734, 'polymarket_us': 3562}, 5250 unmatched (104 book-games; fuzzy-matched 1), 3647 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 86710, 184s
- 2026-11-07T04:41:17Z: 70 games (70 in 24h), quotes {'prophetx': 6392, 'novig': 671, 'kalshi': 2770, 'polymarket_us': 2022}, 5381 unmatched (116 book-games; fuzzy-matched 2), 2934 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 3, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 86719, 183s
- 2026-11-07T04:31:06Z: 70 games (70 in 24h), quotes {'prophetx': 4838, 'novig': 667, 'kalshi': 3322, 'polymarket_us': 3096}, 5646 unmatched (113 book-games; fuzzy-matched 1), 3318 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 86736, 208s
- 2026-11-07T04:21:03Z: 70 games (70 in 24h), quotes {'prophetx': 9778, 'novig': 669, 'kalshi': 3604, 'polymarket_us': 3530}, 6957 unmatched (140 book-games; fuzzy-matched 2), 5577 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 5, new A 13 B 0, maker posted 0 filled 0, credits used 6 left 86756, 185s
