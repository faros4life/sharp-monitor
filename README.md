# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T05:30:32Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9618 | 9405 | -1.62c | 24.4% | 4076 | -1.07c | 9331 | 4851-4480-0 | -286.02u | -3.1% |  |  | criteria not met (9331/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2180 | 2100 | -3.08c | 19.5% | 470 | -2.73c | 2092 | 1078-1014-0 | -164.52u | -7.9% |  |  | criteria not met (2092/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 164 | 161 | -0.76c | 31.1% | 151 | 0.14c | 161 | 67-94-0 | -18.81u | -11.7% |  |  | criteria not met (161/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 15 | -0.15c | 26.7% | 15 | 1.01c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 91 | 89 | -0.82c | 31.5% | 85 | 0.05c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 58 | 57 | -0.83c | 31.6% | 51 | 0.04c | 57 | 22-35-0 | -10.57u | -18.5% |  |  |  |
| M move-watch: gettable (sightings) | 440 | 434 | -0.62c | 34.8% | 432 | -0.54c | 435 | 221-209-5 | -6.63u | -1.5% | 0.2c | 27s | criteria not met (435/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 227 | 224 | -0.79c | 34.8% | 223 | -0.82c | 224 | 108-112-4 | -13.80u | -6.2% | -0.19c | 28s |  |
| M gettable, price moves | 213 | 210 | -0.45c | 34.8% | 209 | -0.24c | 211 | 113-97-1 | +7.17u | 3.4% | 0.61c | 25s |  |
| M control: not gettable | 1805 | 1445 | -0.83c | 35.5% | 1413 | -1.25c | 1465 | 730-712-23 | -68.16u | -4.7% | 1.87c | 184s |  |
| M all moves | 2245 | 1879 | -0.78c | 35.3% | 1845 | -1.08c | 1900 | 951-921-28 | -74.78u | -3.9% | 1.54c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1102 | 1083 | 2.45c | 27.1% | 232 | 2.44c | 1084 | 488-596-0 | +293.23u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 110 | 107 | 0.13c | 45-62-0 | -12.26u | 73, -0.08c, -14.32u | negative |
| J2 B, NBA | 78 | 75 | 0.3c | 31-44-0 | -9.82u | 47, 0.08c, -7.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 64 | 62 | -0.01c | 27-35-0 | -5.32u | 48, -0.3c, -4.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 259 | 257 | -0.6c | 123-131-3 | -16.00u | 147, -0.65c, -12.93u | negative |
| D1 B, unders (descriptive) | 37 | 36 | 0.63c | 18-18-0 | +1.54u | 33, 0.63c, +0.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 16 | 16 | 0.34c | 6-10-0 | -2.21u | 15, 0.33c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 95 | 92 | -0.27c | 51-39-2 | +3.84u | 48, -0.36c, +0.55u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2472 | 108 | 4.4% | -0.57c | 1.58c | 54-54-0 | +2.40u |  |
| MK novig fair-2c | 2466 | 45 | 1.8% | -0.08c | 2.52c | 25-20-0 | +7.63u |  |
| MK prophetx fair-1c | 5633 | 272 | 4.8% | -1.05c | 1.1c | 129-138-5 | -3.19u |  |
| MK prophetx fair-2c | 5595 | 100 | 1.8% | -0.56c | 2.05c | 46-53-0 | -3.10u |  |
| MK all fair-1c | 8105 | 380 | 4.7% | -0.91c | 1.25c | 183-192-5 | -0.79u | criteria not met (380/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8061 | 145 | 1.8% | -0.41c | 2.19c | 71-73-0 | +4.53u | criteria not met (144/50 graded, CLV not positive) |

A and B on the same side/line: 134.

## Odds API credits (100K/month plan)

Study: 643/day, projected 19297/30 days. All monitors on the key: 2422/day, projected 72666/30 days. Remaining 71566; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T05:30:32Z: outside read hours: closes/grades only
- 2026-11-12T05:22:32Z: outside read hours: closes/grades only
- 2026-11-12T05:12:28Z: outside read hours: closes/grades only
- 2026-11-12T05:02:35Z: outside read hours: closes/grades only
- 2026-11-12T04:52:27Z: 18 games (18 in 24h), quotes {'prophetx': 1068, 'novig': 695, 'kalshi': 762, 'polymarket_us': 1224}, 112 unmatched (5 book-games; fuzzy-matched 2), 1909 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 71566, 181s
- 2026-11-12T04:42:08Z: 18 games (18 in 24h), quotes {'prophetx': 1070, 'novig': 697, 'kalshi': 774, 'polymarket_us': 1224}, 124 unmatched (5 book-games; fuzzy-matched 4), 1888 side/lines, polls [NBA:slow,NHL:slow], moves 2, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 71577, 183s
- 2026-11-12T04:32:32Z: 18 games (18 in 24h), quotes {'prophetx': 1070, 'novig': 697, 'kalshi': 778, 'polymarket_us': 1224}, 132 unmatched (6 book-games; fuzzy-matched 2), 1893 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 71592, 183s
- 2026-11-12T04:26:20Z: 18 games (18 in 24h), quotes {'prophetx': 1064, 'novig': 693, 'kalshi': 794, 'polymarket_us': 1222}, 150 unmatched (7 book-games; fuzzy-matched 2), 1877 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 71607, 182s
- 2026-11-12T04:21:07Z: 18 games (18 in 24h), quotes {'prophetx': 1034, 'novig': 695, 'kalshi': 816, 'polymarket_us': 1222}, 170 unmatched (7 book-games; fuzzy-matched 2), 1863 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 71631, 182s
- 2026-11-12T04:15:53Z: 18 games (18 in 24h), quotes {'prophetx': 1064, 'novig': 701, 'kalshi': 842, 'polymarket_us': 1222}, 192 unmatched (7 book-games; fuzzy-matched 4), 1869 side/lines, polls [NBA:slow,NHL:slow], moves 3, new A 22 B 2, maker posted 0 filled 0, credits used 4 left 71642, 184s
