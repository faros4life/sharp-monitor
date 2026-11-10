# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T04:44:11Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8539 | 8299 | -1.6c | 24.1% | 3641 | -1.03c | 8219 | 4245-3974-0 | -275.93u | -3.4% |  |  | criteria not met (8219/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1906 | 1827 | -3.11c | 18.7% | 401 | -2.68c | 1819 | 933-886-0 | -146.79u | -8.1% |  |  | criteria not met (1819/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 143 | 143 | -0.84c | 28.7% | 133 | 0.06c | 141 | 64-77-0 | -5.38u | -3.8% |  |  | criteria not met (141/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 12 | 7-5-0 | +2.63u | 21.9% |  |  |  |
| B ref age 1-5m | 81 | 81 | -1.01c | 27.2% | 77 | -0.1c | 81 | 37-44-0 | -2.25u | -2.8% |  |  |  |
| B ref age 5m+ | 49 | 49 | -0.77c | 30.6% | 43 | 0.01c | 48 | 20-28-0 | -5.76u | -12.0% |  |  |  |
| M move-watch: gettable (sightings) | 388 | 381 | -0.65c | 34.9% | 379 | -0.55c | 379 | 198-176-5 | +2.43u | 0.6% | 0.17c | 26s | criteria not met (379/50 graded, CLV not positive) |
| M gettable, line moves | 203 | 201 | -0.81c | 33.8% | 200 | -0.81c | 200 | 101-95-4 | -3.07u | -1.5% | -0.19c | 26s |  |
| M gettable, price moves | 185 | 180 | -0.48c | 36.1% | 179 | -0.25c | 179 | 97-81-1 | +5.51u | 3.1% | 0.57c | 24s |  |
| M control: not gettable | 1600 | 1281 | -0.77c | 36.3% | 1252 | -1.19c | 1294 | 639-634-21 | -70.04u | -5.4% | 1.9c | 184s |  |
| M all moves | 1988 | 1662 | -0.74c | 36.0% | 1631 | -1.04c | 1673 | 837-810-26 | -67.60u | -4.0% | 1.57c | 164s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1067 | 1057 | 2.6c | 27.0% | 224 | 2.85c | 1056 | 473-583-0 | +287.80u | 27.3% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 92 | 91 | -0.04c | 42-49-0 | -2.83u | 62, -0.22c, -7.51u | negative |
| J2 B, NBA | 63 | 62 | 0.05c | 29-33-0 | -1.36u | 38, -0.18c, -0.51u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 54 | 54 | -0.23c | 26-28-0 | +0.30u | 43, -0.5c, +0.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 226 | 224 | -0.64c | 113-108-3 | -2.23u | 131, -0.62c, -10.37u | negative |
| D1 B, unders (descriptive) | 29 | 28 | 0.49c | 17-11-0 | +7.39u | 26, 0.47c, +5.18u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 19 | -0.69c | 7-12-0 | -4.02u | 17, -0.85c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 13 | 12 | 0.6c | 6-6-0 | +1.79u | 11, 0.61c, +0.64u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 76 | 69 | -0.14c | 38-29-2 | -0.86u | 39, -0.17c, +0.39u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2138 | 89 | 4.2% | -0.62c | 1.58c | 47-42-0 | +6.98u |  |
| MK novig fair-2c | 2135 | 31 | 1.5% | -0.33c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5073 | 243 | 4.8% | -1.04c | 1.1c | 116-118-5 | +3.24u |  |
| MK prophetx fair-2c | 5036 | 81 | 1.6% | -0.66c | 2.04c | 39-40-0 | +2.30u |  |
| MK all fair-1c | 7211 | 332 | 4.6% | -0.93c | 1.24c | 163-160-5 | +10.22u | criteria not met (328/50 graded, CLV not positive) |
| MK all fair-2c | 7171 | 112 | 1.6% | -0.57c | 2.18c | 59-51-0 | +13.38u | criteria not met (110/50 graded, CLV not positive) |

A and B on the same side/line: 115.

## Odds API credits (100K/month plan)

Study: 649/day, projected 19469/30 days. All monitors on the key: 2398/day, projected 71945/30 days. Remaining 76815; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T04:41:10Z: 16 games (16 in 24h), quotes {'prophetx': 1028, 'novig': 699, 'kalshi': 820, 'polymarket_us': 1356}, 58 unmatched (3 book-games; fuzzy-matched 0), 2000 side/lines, polls [none_due], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 0 left 76815, 181s
- 2026-11-10T04:31:13Z: 16 games (16 in 24h), quotes {'prophetx': 1014, 'novig': 693, 'kalshi': 770, 'polymarket_us': 1356}, 64 unmatched (3 book-games; fuzzy-matched 0), 1978 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 76828, 181s
- 2026-11-10T04:21:50Z: 15 games (15 in 24h), quotes {'prophetx': 1014, 'novig': 697, 'kalshi': 786, 'polymarket_us': 1356}, 217 unmatched (6 book-games; fuzzy-matched 0), 1856 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 6 left 76846, 183s
- 2026-11-10T04:11:35Z: 15 games (15 in 24h), quotes {'prophetx': 970, 'novig': 693, 'kalshi': 814, 'polymarket_us': 1356}, 241 unmatched (7 book-games; fuzzy-matched 0), 1812 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 76861, 181s
- 2026-11-10T04:01:14Z: 15 games (14 in 24h), quotes {'prophetx': 970, 'novig': 699, 'kalshi': 850, 'polymarket_us': 1356}, 272 unmatched (7 book-games; fuzzy-matched 0), 1812 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 76874, 181s
- 2026-11-10T03:51:32Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 703, 'kalshi': 862, 'polymarket_us': 1228}, 283 unmatched (7 book-games; fuzzy-matched 0), 1716 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 76898, 184s
- 2026-11-10T03:41:53Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 695, 'kalshi': 922, 'polymarket_us': 1228}, 340 unmatched (9 book-games; fuzzy-matched 0), 1716 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 76907, 181s
- 2026-11-10T03:31:57Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 699, 'kalshi': 970, 'polymarket_us': 1228}, 388 unmatched (10 book-games; fuzzy-matched 0), 1704 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 76920, 184s
- 2026-11-10T03:21:32Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 691, 'kalshi': 996, 'polymarket_us': 1228}, 413 unmatched (10 book-games; fuzzy-matched 0), 1704 side/lines, polls [none_due], moves 0, new A 10 B 0, maker posted 0 filled 0, credits used 0 left 76954, 181s
- 2026-11-10T03:11:32Z: 15 games (14 in 24h), quotes {'prophetx': 762, 'novig': 695, 'kalshi': 1008, 'polymarket_us': 1226}, 427 unmatched (10 book-games; fuzzy-matched 0), 1605 side/lines, polls [NCAAF:slow], moves 2, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 76963, 183s
