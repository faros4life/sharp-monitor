# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T04:04:16Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8505 | 8299 | -1.6c | 24.1% | 3641 | -1.03c | 8064 | 4166-3898-0 | -269.36u | -3.3% |  |  | criteria not met (8064/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1895 | 1827 | -3.11c | 18.7% | 401 | -2.68c | 1789 | 914-875-0 | -152.22u | -8.5% |  |  | criteria not met (1789/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 143 | 143 | -0.84c | 28.7% | 133 | 0.06c | 139 | 63-76-0 | -5.47u | -3.9% |  |  | criteria not met (139/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 12 | 7-5-0 | +2.63u | 21.9% |  |  |  |
| B ref age 1-5m | 81 | 81 | -1.01c | 27.2% | 77 | -0.1c | 79 | 36-43-0 | -2.33u | -3.0% |  |  |  |
| B ref age 5m+ | 49 | 49 | -0.77c | 30.6% | 43 | 0.01c | 48 | 20-28-0 | -5.76u | -12.0% |  |  |  |
| M move-watch: gettable (sightings) | 388 | 381 | -0.65c | 34.9% | 379 | -0.55c | 373 | 193-175-5 | -1.97u | -0.5% | 0.17c | 26s | criteria not met (373/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 203 | 201 | -0.81c | 33.8% | 200 | -0.81c | 197 | 98-95-4 | -5.81u | -2.9% | -0.19c | 26s |  |
| M gettable, price moves | 185 | 180 | -0.48c | 36.1% | 179 | -0.25c | 176 | 95-80-1 | +3.83u | 2.2% | 0.57c | 24s |  |
| M control: not gettable | 1600 | 1281 | -0.77c | 36.3% | 1252 | -1.19c | 1273 | 631-621-21 | -63.67u | -5.0% | 1.9c | 184s |  |
| M all moves | 1988 | 1662 | -0.74c | 36.0% | 1631 | -1.04c | 1646 | 824-796-26 | -65.64u | -4.0% | 1.57c | 164s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1064 | 1057 | 2.6c | 27.0% | 224 | 2.85c | 1055 | 472-583-0 | +285.57u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 92 | 90 | -0.04c | 42-48-0 | -1.83u | 61, -0.22c, -6.51u | negative |
| J2 B, NBA | 63 | 61 | 0.05c | 29-32-0 | -0.36u | 37, -0.18c, +0.49u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 54 | 53 | -0.23c | 26-27-0 | +1.30u | 42, -0.5c, +1.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 226 | 221 | -0.64c | 110-108-3 | -4.96u | 129, -0.62c, -12.18u | negative |
| D1 B, unders (descriptive) | 29 | 27 | 0.49c | 16-11-0 | +6.31u | 25, 0.47c, +4.10u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 19 | -0.69c | 7-12-0 | -4.02u | 17, -0.85c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 13 | 11 | 0.6c | 5-6-0 | +0.71u | 10, 0.61c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 76 | 66 | -0.14c | 36-28-2 | -2.54u | 38, -0.17c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2138 | 89 | 4.2% | -0.62c | 1.58c | 45-42-0 | +4.86u |  |
| MK novig fair-2c | 2135 | 31 | 1.5% | -0.33c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5073 | 243 | 4.8% | -1.04c | 1.1c | 115-118-5 | +2.19u |  |
| MK prophetx fair-2c | 5036 | 81 | 1.6% | -0.66c | 2.04c | 39-40-0 | +2.30u |  |
| MK all fair-1c | 7211 | 332 | 4.6% | -0.93c | 1.24c | 160-160-5 | +7.05u | criteria not met (325/50 graded, CLV not positive) |
| MK all fair-2c | 7171 | 112 | 1.6% | -0.57c | 2.18c | 59-51-0 | +13.38u | criteria not met (110/50 graded, CLV not positive) |

A and B on the same side/line: 115.

## Odds API credits (100K/month plan)

Study: 650/day, projected 19496/30 days. All monitors on the key: 2399/day, projected 71962/30 days. Remaining 76874; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T04:01:14Z: 15 games (14 in 24h), quotes {'prophetx': 970, 'novig': 699, 'kalshi': 850, 'polymarket_us': 1356}, 272 unmatched (7 book-games; fuzzy-matched 0), 1812 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 76874, 181s
- 2026-11-10T03:51:32Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 703, 'kalshi': 862, 'polymarket_us': 1228}, 283 unmatched (7 book-games; fuzzy-matched 0), 1716 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 76898, 184s
- 2026-11-10T03:41:53Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 695, 'kalshi': 922, 'polymarket_us': 1228}, 340 unmatched (9 book-games; fuzzy-matched 0), 1716 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 76907, 181s
- 2026-11-10T03:31:57Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 699, 'kalshi': 970, 'polymarket_us': 1228}, 388 unmatched (10 book-games; fuzzy-matched 0), 1704 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 7 B 0, maker posted 0 filled 0, credits used 6 left 76920, 184s
- 2026-11-10T03:21:32Z: 15 games (14 in 24h), quotes {'prophetx': 934, 'novig': 691, 'kalshi': 996, 'polymarket_us': 1228}, 413 unmatched (10 book-games; fuzzy-matched 0), 1704 side/lines, polls [none_due], moves 0, new A 10 B 0, maker posted 0 filled 0, credits used 0 left 76954, 181s
- 2026-11-10T03:11:32Z: 15 games (14 in 24h), quotes {'prophetx': 762, 'novig': 695, 'kalshi': 1008, 'polymarket_us': 1226}, 427 unmatched (10 book-games; fuzzy-matched 0), 1605 side/lines, polls [NCAAF:slow], moves 2, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 76963, 183s
- 2026-11-10T03:01:53Z: 17 games (14 in 24h), quotes {'prophetx': 894, 'novig': 691, 'kalshi': 1030, 'polymarket_us': 1226}, 346 unmatched (7 book-games; fuzzy-matched 0), 1779 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 0 filled 0, credits used 4 left 76974, 199s
- 2026-11-10T02:56:47Z: 17 games (14 in 24h), quotes {'prophetx': 980, 'novig': 693, 'kalshi': 1038, 'polymarket_us': 1230}, 354 unmatched (7 book-games; fuzzy-matched 0), 1862 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 1 filled 0, credits used 4 left 76989, 204s
- 2026-11-10T02:52:07Z: 17 games (14 in 24h), quotes {'prophetx': 980, 'novig': 699, 'kalshi': 1052, 'polymarket_us': 1230}, 370 unmatched (8 book-games; fuzzy-matched 0), 1860 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 0 filled 1, credits used 4 left 76995, 184s
- 2026-11-10T02:45:27Z: 17 games (14 in 24h), quotes {'prophetx': 980, 'novig': 697, 'kalshi': 1074, 'polymarket_us': 1230}, 392 unmatched (8 book-games; fuzzy-matched 0), 1857 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 8 filled 0, credits used 6 left 77008, 184s
